# -*- coding:gbk -*-
import os
import sys
import time
import csv
import commFuncs as cF
import commFuncs_kcbp as cF_kcbp
import gl
import zhlc
import threading
import datetime
import signal
import copy
from collections import OrderedDict
from gl import GlobalLogging as Logging
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy
import functools
import db_data_compare
import scanOracleDB
import json
import MySQLdb
import pyodbc
from ftpClient import XFer
import threading
import cx_Oracle
import pika
import redis_client
from lxml import etree

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
# from task import task
# 控制线程退出的标识
is_exit = False
table_data = []
count = 0


def async(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.start()

    return wrapper


class MQServer(threading.Thread):
    """MessageClient"""

    def __init__(self):
        self.mq_connect_closed = False

        #
        self._clients_dict = {}  # 保存client，并且相关状态
        #
        self._request_timeout = 3000
        self._retries_left = 100  # 最大重连100次
        self._timeout_count = {}  # client队列发送收到应答超时计数
        self._last_msg_dict = {}  # 最后一次client发送的消息，用于重发
        threading.Thread.__init__(self)

        self._setting = json.loads(open("settings.json", "r").read())

        # 启用RPC
        self.rpcserver = SimpleXMLRPCServer(('', 15555))

        self.rpcserver.register_function(self.interface_data_changes)
        # self.rpcserver.register_function(self.register_client)
        self.rpcserver.register_function(self.client_heart_beat)
        # self.rpcserver.register_function(self.tell_case_result)
        # self.rpcserver.register_function(self.tell_script_update_result)
        # self.rpcserver.register_function(self.tell_env_init_result)
        self.rpcserver.register_function(self.asyncupdate_account_group_info)
        self.rpcserver.register_function(self.update_T2_interfaceDetail)
        self.rpcserver.register_function(self.scan_db_info)
        # self.rpcserver.register_function(self.run_test)
        self.rpcserver.register_function(self.rpc_get_system_db_info)
        self.rpcserver.register_function(self.rpc_generate_xml)
        self.rpcserver.register_function(self.compare_chage_data)
        self.rpcserver.register_function(self.get_change_data)
        self.rpcserver.register_function(self.get_sx_cases_collection_detail_info)
        self.rpcserver.register_function(self.get_test_system_info)

        self._rpc_thread = threading.Thread(target=self.rpc_thread)
        self._rpc_thread.start()

        # WEB 端两个接口都涉及后台异步调用，设计3类状态
        self._STATE_INIT = 0  # 初始状态
        self._STATE_EXECUTING = 1  # 执行状态
        self._STATE_FINISH = 2  # 上一次执行完成状态
        self._STATE_ERROR = 3  # 有错状态
        self._system_account_group = json.loads(open("account_setting.json", "r").read())
        # 提供给WEB端两个接口的状态，避免重复调用
        self._compare_task_data_change_state = self._STATE_INIT

        # 与系统有关，需要按照系统来分类
        self._scan_db_info_state_dict = OrderedDict()

        # 系统相关数据库信息
        self._system_db_info = OrderedDict()

        # 系统相关数据库disableflag 信息，用于数据对比时使用
        self._system_db_table_column_disable_info = OrderedDict()

        # 用例数据库类型
        self._case_db_type = "MYSQL"  # 默认MYSQL
        # 用例数据库信息
        self._case_db_info = OrderedDict()

        # 获取用例数据库信息
        self.get_casedb_info()
        # 更新系统数据库信息,当系统数据库有更新时，需要再次调用
        self.get_system_database_info()
        # 更新数据库表、字段信息
        self.update_table_column_disableflag_info()

        # FTP 地址
        # self._ftp_ip = "127.0.0.1"
        # self._ftp_port = 2121

        self.update_system_db_table_column_disable_info_to_ftp()

        # ================== 启用Redis ===================================================
        self._redis_client = redis_client.RedisClient(self._setting["RedisServer"]["IP"],
                                                      self._setting["RedisServer"]["PORT"])
        # ================== 启用RabbitMQ 消息队列 =========================================
        self._channel_dict = {}  # {queue_name:channel}
        self._task_agent_dict = {}  # {task_id:[agent_id]}

        credentials = pika.PlainCredentials('timesvc', 'timesvc')
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self._setting["RabbitMQServer"]["IP"], credentials=credentials, heartbeat=0))

        self._rpc_channel = self._connection.channel()

        self._rpc_channel.queue_declare(queue='server_rpc_queue')

        self._rpc_channel.basic_qos(prefetch_count=1)
        self._rpc_channel.basic_consume(self.rpc_process, queue='server_rpc_queue')

        # print(" [x] Awaiting RPC requests")
        # self._rpc_channel.start_consuming()
        self.rebuild_agent_info()

        self.start_consuming()

    """
    1. rpc初始化
    2. rpc函数注册
    3. 状态字段定义
    4. redis初始化
    5. rabbitmq初始化
    """

    @async
    def start_consuming(self):

        self._rpc_channel.start_consuming()

    def rebuild_agent_info(self):
        """
        Agent重启的时候，根据Redis信息重建通道和任务信息
        :return:
        """
        Logging.getLog().debug("rebuild_agent_info")
        self._task_agent_dict = self._redis_client.rebuild_agent_info()
        Logging.getLog().debug("rebuild_agent_info %s" % str(self._task_agent_dict))

    def rpc_process(self, ch, method, props, body):
        try:
            msg_dict = json.loads(body)
            return_dict = OrderedDict()

            if msg_dict["func_param"] == "":
                func_call = "self.%s()" % msg_dict["func"]
            else:
                func_call = "self.%s(%s)" % (
                msg_dict["func"], ','.join("'%s'" % str(i) for i in msg_dict["func_param"]))

            Logging.getLog().debug(func_call)
            ret, ret_info = eval(func_call)
            # ret, ret_info = eval("self.%s" % msg_dict["func"])tuple(msg_dict["func_param"])
            return_dict["return"] = ret
            return_dict["return_info"] = ret_info

            Logging.getLog().debug("reply_to %s with id =%s" % (props.reply_to, props.correlation_id))
            ch.basic_publish(exchange='',
                             routing_key=props.reply_to,
                             properties=pika.BasicProperties(correlation_id= \
                                                                 props.correlation_id),
                             body=json.dumps(return_dict, ensure_ascii=False))
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            self.mq_connect_closed = True

    def register_client(self, id, ip, port):
        try:
            Logging.getLog().debug("receive register_client(%s,%s,%s" % (id, ip, port))
            agent_id = str(id)
            agent_ip = str(ip)
            agent_port = str(port)

            self._clients_dict[agent_id] = OrderedDict()
            self._clients_dict[agent_id]["ip"] = agent_ip
            self._clients_dict[agent_id]["port"] = agent_port
            self._clients_dict[agent_id]["state"] = gl.CLIENT_STATE_REGISTER
            self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_REGISTER
            self._clients_dict[agent_id]["last_alive"] = datetime.datetime.now()
            sql = "select agent_id from sx_agent_info where agent_code='%s'" % str(agent_id)
            ds = cF.executeCaseSQL(sql)
            if len(ds) > 0:
                sql = "update sx_agent_info set state='STATE_REGISTER',LAST_ALIVE='%s',DEPLOY_IP='%s',DEPLOY_PORT='%s' where agent_code = '%s'" % (
                    str(datetime.datetime.now()), agent_ip, agent_port, str(agent_id))
                Logging.getLog().debug(sql)
                cF.executeCaseSQL(sql)
            else:
                sql = "insert into sx_agent_info (AGENT_CODE, AGENT_NAME, state, last_alive, DEPLOY_IP, DEPLOY_PORT) values('%s','%s', 'STATE_REGISTER','%s','%s','%s')" % (
                    str(agent_id), "TestAgent%d" % int(agent_id), str(datetime.datetime.now()), agent_ip, agent_port)
                Logging.getLog().debug(sql)
                cF.executeCaseSQL(sql)

            # self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_UPDATESCRIPT
            # self.trigger_script_update(agent_id)

            ######################
            # 创建一个队列
            new_queue_name = "cmd_queue_%s" % str(id)
            # if new_queue_name not in self._channel_dict.keys():
            #     channel = self._connection.channel()
            #     channel.queue_declare(queue=new_queue_name)
            #     self._channel_dict[new_queue_name] = channel

            # 通知更新脚本
            # cmd_dict = OrderedDict()
            # cmd_dict["func"] = "processScriptUpdate"
            # cmd_dict["func_param"] = ""
            update_script_msg = copy.copy(gl.update_script_msg)
            try:
                self.send_msg_to_queue(json.dumps(update_script_msg, ensure_ascii=False), new_queue_name)
            except:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().error(exc_info)
            # channel = self._channel_dict[new_queue_name]
            # channel.basic_publish(exchange='',
            #                       routing_key=new_queue_name,
            #                       body=json.dumps(update_script_msg, ensure_ascii=False))
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def send_msg_to_queue(self, msg_str, queue_name):
        try:
            # Logging.getLog().info("execute msg_str: %s, queue_name:%s" % (str(msg_str),str(queue_name)))
            if queue_name not in self._channel_dict.keys():
                channel = self._connection.channel()
                channel.queue_declare(queue=queue_name)
                self._channel_dict[queue_name] = channel

            update_script_msg = copy.copy(gl.update_script_msg)

            channel = self._channel_dict[queue_name]
            channel.basic_publish(exchange='',
                                  routing_key=queue_name,
                                  body=msg_str)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            self.mq_connect_closed = True
            return '-1', exc_info

    def get_test_system_info(self, system_id, test_system_id):
        try:
            Logging.getLog().info("system_id:%s, test_system_id:%s"%(system_id, test_system_id))
            self.asy_get_test_system_info(system_id, test_system_id)
            return '0'
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return '-1'

    def asy_get_test_system_info(self, system_id, test_system_id):
        try:
            cF.updateZHLCAutoTestSettingXml(system_id, "", test_system_id)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def update_T2_interfaceDetail(self, system_id):
        try:
            self.asyncupdateT2file(system_id)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    @async
    def asyncupdateT2file(self, system_id):
        try:
            sign = 1
            Logging.getLog().info(u"启动消息服务器成功")
            self.UpdateT2InterfaceDetailFile(sign, system_id)
            Logging.getLog().debug(u'%sT2文件已经成功上传到FTP' % system_id)
            Logging.getLog().debug(u'T2文件更新成功')
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def UpdateT2InterfaceDetailFile(self, sign, system_id):
        '''
        #TODO chenbaoshuai
        从数据库中抽取T2Interface内容的文件，调用TestAgent ProcessFileSendingMsg 函数写入相应位置
        :param client_id: TestAgent ID 号
        :param system_id: 系统ID号
        :return: 一个元组(ret,msg)
            ret: 0代表成功，-1代表失败
            msg：详细信息
        '''
        if os.path.exists("settings.json"):
            _setting = json.loads(open("settings.json", "r").read())
            gl.g_testcaseDBDict["DBType"] = _setting["casedb"]["DBType"]
            gl.g_testcaseDBDict["casedb"] = _setting["casedb"][gl.g_testcaseDBDict["DBType"]]
        print 'enter >>>>>>>>>>>UpdateT2InterfaceDetailFile'
        sql = "SELECT i.FUNCID,i.INTERFACE_NAME, i.FUNCID_DESC, i.TIMEOUT,i.NEED_LOG,d.INPUT_TYPE,d.PARAM_NAME,d.PARAM_TYPE," \
              "d.PARAM_DESC,d.DISABLEFLAG,d.PARAM_INDEX FROM sx_interface_info i LEFT JOIN " \
              "sx_interface_detail_info d ON i.ID=d.INTERFACE_ID WHERE i.SYSTEM_ID='%s' AND i.funcid != '' " \
              "AND d.INTERFACE_ID IS NOT NULL ORDER BY i.ID" % (system_id)
        ds = cF.executeCaseSQL(sql)
        detail_dict = OrderedDict()
        for i, rec in enumerate(ds):
            detail_dict[i] = rec
        if detail_dict.keys() != []:
            ret, msg = self.update_t2_interface_detail_file(system_id, detail_dict)
            print ret, msg
            if ret < 0:
                Logging.getLog().error(msg)
                return -1, msg
        return 0, ""

    def interface_data_changes(self, interface_id):
        try:
            self.order_by_interface_id_to_update_cases_detail_param_data(interface_id)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    @async
    def order_by_interface_id_to_update_cases_detail_param_data(self, interface_id):
        try:
            new_param_data = OrderedDict()
            sql = "select PARAM_NAME from SX_INTERFACE_DETAIL_INFO where INTERFACE_ID in (select " \
                  "ID from SX_INTERFACE_INFO where ID=%s ) and INPUT_TYPE = 'IN' order by PARAM_INDEX" % interface_id
            rs1 = cF.executeCaseSQL_DB2(sql)
            PARAM_NAMES = [i['PARAM_NAME'] for i in rs1]
            # PARAM_NAMES = list(set(PARAM_NAMES))
            INPUT_STRING = "=#".join(PARAM_NAMES)
            sql = "update SX_CASES_DETAIL set INPUT_STRING='%s' where PARAM_ID=%s" % (INPUT_STRING, interface_id)
            Logging.getLog().debug(sql)
            cF.executeCaseSQL_DB2(sql)
            sql = "select CASES_DETAIL_ID from SX_CASES_DETAIL where PARAM_ID=%s and IS_DELETE='0'" % interface_id
            Logging.getLog().debug(sql)
            rs2 = cF.executeCaseSQL_DB2(sql)
            CASES_DETAIL_IDS = [i['CASES_DETAIL_ID'] for i in rs2]
            if CASES_DETAIL_IDS:
                for CASES_DETAIL_ID in CASES_DETAIL_IDS:
                    sql = "select PARAM_DATA from SX_CASES_DETAIL_PARAM_DATA where CASES_DETAIL_ID =%s" % CASES_DETAIL_ID
                    Logging.getLog().debug(sql)
                    rs3 = cF.executeCaseSQL_DB2(sql)
                    for i in rs3:
                        old_param_data = {}
                        PARAM_DATA = i["PARAM_DATA"]
                        if PARAM_DATA:
                            PARAM_DATAS = PARAM_DATA.split("#")
                            for PARAM in PARAM_DATAS:
                                key, value = PARAM.split("=")
                                old_param_data[key] = value
                            for PARAM_NAME in PARAM_NAMES:
                                if PARAM_NAME in old_param_data.keys():
                                    new_param_data[PARAM_NAME] = old_param_data[PARAM_NAME]
                                else:
                                    new_param_data[PARAM_NAME] = ""
                    if new_param_data:
                        # params = []
                        # for param in new_param_data:
                        #     param = param + "=" + new_param_data[param]
                        #     params.append(param)
                        # PARAM_DATA = "#".join(params)
                        params = [param + "=" + new_param_data[param] for param in new_param_data]
                        PARAM_DATA = "#".join(params)
                        sql = "update SX_CASES_DETAIL_PARAM_DATA set PARAM_DATA='%s' where CASES_DETAIL_ID =%s" % (
                        PARAM_DATA, CASES_DETAIL_ID)
                        Logging.getLog().debug(sql)
                        cF.executeCaseSQL_DB2(sql)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def rpc_generate_xml(self, system_id):
        try:
            self.asyncrpc_generate_xml(system_id)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    @async
    def asyncrpc_generate_xml(self, system_id):
        try:
            sign = 1
            Logging.getLog().info(u"启动消息服务器成功")
            self.generate_account_group_xml(system_id, sign)
            Logging.getLog().debug(u'%s系统账户组xml已经成功上传到FTP' % system_id)
            Logging.getLog().debug(u'账户组信息更新成功')
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def generate_account_group_xml(self, system_id, sign):
        '''数据库查询账户信息'''
        # if sign != 0:
        #     _setting = json.loads(open("settings.json", "r").read())
        #     gl.conntion_db2 = _setting
        #     gl.sign = sign
        if os.path.exists("settings.json"):
            _setting = json.loads(open("settings.json", "r").read())
            gl.g_testcaseDBDict["DBType"] = _setting["casedb"]["DBType"]
            gl.g_testcaseDBDict["casedb"] = _setting["casedb"][gl.g_testcaseDBDict["DBType"]]
        sql = "select * from SX_ACCOUNT_GROUP_INFO where SYSTEM_ID='%s'" % system_id
        ds = cF.executeCaseSQL_DB2(sql)
        detail_dict = OrderedDict()
        #SERVERID 判断是否是带核心用户
        SERVERIDS = []
        WHETHER_SERVERID_FLAG = False
        for i, rec in enumerate(ds):
            SERVERIDS.append(rec['SERVERID'])
            detail_dict[i] = rec
        SERVERIDS = list(set(SERVERIDS))
        if "" in SERVERIDS:
            WHETHER_SERVERID_FLAG = True
        elif "null" in SERVERIDS:
            WHETHER_SERVERID_FLAG = True
        elif None in SERVERIDS:
            WHETHER_SERVERID_FLAG = True
        elif "(null)" in SERVERIDS:
            WHETHER_SERVERID_FLAG = True
        else:
            pass
        ret, core_data_msg = cF.get_kcbp_core(system_id, [])
        if ret < 0:
            Logging.getLog().error(core_data_msg)
            return -1, core_data_msg
        # sql = "select system_id from sx_test_system where sys_id = '%s'" % system_id
        # ds = cF.executeCaseSQL_DB2(sql)
        # core_data = {}
        # for i in ds:
        #     sys_test_id = i["SYSTEM_ID"]
        #     sql_info = "select SETTING_TYPE, SETTING_VALUE from sx_system_setting where sys_test_id =%s and " \
        #                "setting_type in ('KCBP_IP', 'KCBP_CORE', 'KCBP_TYPE', 'KCBP_DESC', 'dbip')" % sys_test_id
        #     ds_2 = cF.executeCaseSQL_DB2(sql_info)
        #     if ds_2:
        #         children_dict = {}
        #         for tmp in ds_2:
        #             SETTING_TYPE = tmp['SETTING_TYPE']
        #             SETTING_VALUE = tmp['SETTING_VALUE']
        #             children_dict[SETTING_TYPE] = SETTING_VALUE
        #         KCBP_CORE = children_dict['KCBP_CORE']
        #         core_data[str(KCBP_CORE)] = children_dict
        # print core_data
        if detail_dict.keys() != []:
            ret, msg = self.generate_account_group_xml_orderby_system_id(system_id, detail_dict, core_data_msg, WHETHER_SERVERID_FLAG)
            print ret, msg
            if ret < 0:
                Logging.getLog().error(msg)
                return -1, msg
        return 0, ""

    def rpc_thread(self):
        print "rpc_thread"
        # self.rpcserver.serve_forever()
        while (gl.is_exit_all_thread != True):
            # print "handle request"
            self.rpcserver.handle_request()
            # print "another handle"
        Logging.getLog().debug("Exit rpc thread")

    def update_table_column_disableflag_info(self):
        """
        在全数据库扫描完毕之后，保存所有数据库、表，字段的disableflag信息
        :return:
        """
        # 清空原有的
        self._system_db_table_column_disable_info = OrderedDict()

        try:
            sql = "  SELECT DISTINCT(system_id) FROM sx_database_info"
            ret, ds = self.execute_case_sql(sql)
            if ret < 0:
                return ret, ds

            for rec in ds:
                ret, self._system_db_table_column_disable_info[rec["SYSTEM_ID"]] = scanOracleDB.getTableColumnInfo(
                    rec["SYSTEM_ID"])
                if ret < 0:
                    return ret, self._system_db_table_column_disable_info[rec["SYSTEM_ID"]]
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    # def readSystemConfigFile(self, system_id=""):
    #     '''读取和系统相关的XML系统配置文件 '''
    #     try:
    #         if getattr(sys, 'frozen', False):
    #             application_path = os.path.dirname(sys.executable)
    #         elif __file__:
    #             application_path = os.path.dirname(__file__)
    #         Logging.getLog().debug("application_path = %s" % application_path)
    #
    #         Logging.getLog().debug('try to switch cwd to %s' % application_path)
    #         # os.chdir(application_path)
    #
    #         if system_id == "":
    #             Logging.getLog().critical(u"未提供系统ID信息")
    #             return -1
    #         homedir = os.getcwd()
    #
    #         if system_id == '142891263425277DZ1':  # FIXME 需要修改为上线时实际的system_id
    #             tree = ET.parse("%s\\init\\%s\\JZ_JZJY_AutoTestSetting.xml" % (homedir, system_id))
    #         else:
    #             tree = ET.parse("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id))
    #         root = tree.getroot()
    #         if os.path.exists("%s\\init\\%s\\T2InterfaceDetails.xml" % (homedir, system_id)):
    #             gl.g_interfaceDetailTree = ET.parse("%s\\init\\%s\\T2InterfaceDetails.xml" % (homedir, system_id))
    #         else:
    #             Logging.getLog().debug(u'系统不存在该接口配置文件T2InterfaceDetails.xml')
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().critical(exc_info)
    #         strerror = u"无法解析配置文件AutoTestSetting.xml 原因：%s" % (ex)
    #         # wx.MessageBox(strerror,u"提示")
    #         Logging.getLog().critical(strerror)
    #         return -1
    #     try:
    #         # 解析帐号信息
    #         # 帐号信息格式为以类型为键值的字典类型 {type1:value1,type2:value2 ……}
    #         if system_id == "142891263425277DZ1":  # FIXME
    #             # 解析买入股票允许的误差百分比
    #             deviationPCT = root.find("deviation")
    #             for elem in deviationPCT:
    #                 gl.g_deviationPCT = elem.text
    #
    #             # 解析集中交易数据库信息
    #             # SqlServerElem = root.find("ConnectSqlServerSetting")
    #             # for serverElem in SqlServerElem:
    #             #     gl.g_connectSqlServerSetting[serverElem.attrib["servertype"]] = {}
    #             #     for elem in serverElem:
    #             #         gl.g_connectSqlServerSetting[serverElem.attrib["servertype"]][elem.tag] = elem.text
    #             SqlServerElem = root.find("ConnectSqlServerSetting")
    #             for serverElem in SqlServerElem:
    #                 gl.g_connectSqlServerSetting[serverElem.attrib["core"]] = {}
    #                 for elem in serverElem:
    #                     gl.g_connectSqlServerSetting[serverElem.attrib["core"]][elem.tag] = elem.text
    #             JZJYSystemSettingElem = root.find("JZJYSystemSetting")
    #             for ServerSettingElem in JZJYSystemSettingElem:
    #                 if ServerSettingElem.tag == "DisableDBCompare":
    #                     gl.g_JZJYSystemSetting[ServerSettingElem.tag] = ServerSettingElem.text
    #                     continue
    #                 if ServerSettingElem.tag == "DisableExportHtml":
    #                     gl.g_JZJYSystemSetting[ServerSettingElem.tag] = ServerSettingElem.text
    #                     continue
    #                 gl.g_JZJYSystemSetting[ServerSettingElem.attrib["id"]] = ServerSettingElem
    #                 AccountGroupDict = {}
    #                 for AccountGroupElem in ServerSettingElem:
    #                     paramDict = {}
    #                     for elem in AccountGroupElem:
    #                         paramDict[elem.tag] = elem.text
    #                     AccountGroupDict[AccountGroupElem.attrib["id"]] = paramDict
    #                 gl.g_paramInfoDict[ServerSettingElem.attrib["id"]] = AccountGroupDict
    #         else:
    #             accountmessage = {}
    #             # AccountInfoElem = root.find("AccountInfo")
    #             # account_group_id = tree.findall('.//AccountInfo')
    #             # dist = {}
    #             # accountDict = OrderedDict()
    #             # for elem in account_group_id:
    #             #     for xx in elem.getchildren():
    #             #         tx = xx.text.replace(',', '&comma&')
    #             #         dist[xx.tag] = tx
    #             #     accountDict[elem.attrib["id"]] = dist
    #             #     dist = {}
    #             # gl.g_accountDict = accountDict
    #             cF.readNewAccountInfo(system_id)
    #             # 解析案例数据库信息
    #             # testcaseDBElem = root.find("TestCaseDataBase")
    #             # for elem in testcaseDBElem:
    #             #     gl.g_testcaseDBDict[elem.tag] = elem.text
    #
    #             # 解析BeyondCompare程序路径
    #             # ByondCmpElem = root.find("BeyondComparePath/path")
    #             # gl.g_bcmppath = ByondCmpElem.text
    #
    #             # 解析集中交易数据库信息
    #         SqlServerElem = root.find("ConnectSqlServerSetting")
    #         for serverElem in SqlServerElem:
    #             gl.g_connectSqlServerSetting[serverElem.attrib["core"]] = {}
    #             for elem in serverElem:
    #                 gl.g_connectSqlServerSetting[serverElem.attrib["core"]][elem.tag] = elem.text
    #         # SqlServerElem = root.find("ConnectSqlServerSetting")
    #         # if SqlServerElem != None:
    #         #     for serverElem in SqlServerElem:
    #         #         # 查找该服务器的servertype
    #         #         # servertype = 'p'
    #         #         # for elem in serverElem:
    #         #         #    if elem.tag == "servertype":
    #         #         #        servertype = elem.text
    #         #         #        break
    #         #         gl.g_connectSqlServerSetting[serverElem.attrib["servertype"]] = {}
    #         #         for elem in serverElem:
    #         #             gl.g_connectSqlServerSetting[serverElem.attrib["servertype"]][elem.tag] = elem.text
    #
    #         # 解析综合理财数据库信息
    #         OracleElem = root.find("ConnectOracleSetting")
    #         if OracleElem != None:
    #             for serverElem in OracleElem:
    #                 gl.g_connectOracleSetting[serverElem.attrib["core"]] = {}
    #                 for elem in serverElem:
    #                     gl.g_connectOracleSetting[serverElem.attrib["core"]][elem.tag] = elem.text
    #
    #         # 解析综合理财系统信息
    #         ZHLCSystemSettingElem = root.find("ZHLCSystemSetting")
    #         if ZHLCSystemSettingElem != None:
    #             for elem in ZHLCSystemSettingElem:
    #                 gl.g_ZHLCSystemSetting[elem.tag] = elem.text
    #
    #         # 解析需要修改运行时间的服务器列表
    #         TimeSyncServerSettingElem = root.find("TimeSyncServerSetting")
    #         if TimeSyncServerSettingElem != None:
    #             gl.g_timeSyncServerSettingList = []
    #             for elem in TimeSyncServerSettingElem:
    #                 gl.g_timeSyncServerSettingList.append(elem.attrib["ip"])
    #                 # cF.loadSYSCases()
    #         CasesSleepTimeElem = root.find("OtherSetting/CasesSleepTime")
    #         if CasesSleepTimeElem != None:
    #             gl.g_cases_sleep_time = float(CasesSleepTimeElem.text)
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         strerror = u"解析配置文件AutoTestSetting.xml 出现异常。原因：%s" % (exc_info)
    #         Logging.getLog().critical(strerror)
    #         return -1
    #     Logging.getLog().info(u"解析配置文件AutoTestSetting.xml 完毕")
    #     return 0

    def createFTPClient(self):
        try:
            f = XFer(self._ftp_ip, gl.gl_ftp_info['FTPServer']['USER'], gl.gl_ftp_info['FTPServer']['PASSWORD'], '.', self._ftp_port)
            f.login()
            return 0, f
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def get_casedb_info(self):
        try:
            _setting = json.loads(open("settings.json", "r").read())
            self._case_db_type = _setting["casedb"]["DBType"]
            self._case_db_info = _setting["casedb"][self._case_db_type]
            self._ftp_ip = _setting["FTPServer"]["IP"]
            self._ftp_port = int(_setting["FTPServer"]["PORT"])


        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return

    def deal_with_T2_dataset_list(self, dataset_list):
        """
        处理T2协议返回值
        :param dataset_list:
        :return:
        """
        try:
            data = {'message': ''}
            column = dataset_list[0][0]
            data['field'] = column
            values_list = []
            for i in dataset_list[0][1:]:
                # 生产上sx_run_record的额外信息超过10万报错， fixme
                i_new = []
                for j in i:
                    i_new.append(j.replace("'", "''"))
                if len(str(values_list).replace(' ', '')) <= 90000:
                    values_list.append(i_new)
            data['values_list'] = values_list
            return 0, data
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    # def paremReplace(self,cmdstring,dync_dict,system_id,account_group_id):
    #    """

    #    :param dync_dict:
    #    :return:
    #    """
    #    if not dync_dict.has_key(system_id):
    #        return cmdstring
    #    if not dync_dict[system_id].has_key(str(account_group_id)):
    #        return cmdstring
    #    for key in dync_dict[system_id][str(account_group_id)].keys():
    #        cmdstring = cmdstring.replace("@%s@" % key, dync_dict[system_id][str(account_group_id)][key])
    #    return cmdstring
    def connect_to_case_db(self):
        if self._case_db_type == "MYSQL":
            conn = MySQLdb.connect(host=self._case_db_info["casedbip"],
                                   user=self._case_db_info["casedbuser"],
                                   passwd=self._case_db_info["casedbpwd"],
                                   port=int(self._case_db_info["casedbport"]),
                                   db=self._case_db_info["casedbname"],
                                   charset='gbk')
            return conn
        elif self._case_db_info == "DB2":
            # fixme 待实现
            dbstring = "driver={IBM DB2 ODBC DRIVER};database=%s;hostname=%s;port=%s;protocol=tcpip;uid=%s;pwd=%s;" % (
                self._case_db_info["casedbname"], self._case_db_info["casedbip"], self._case_db_info["casedbport"],
                self._case_db_info["casedbuser"], self._case_db_info["casedbpwd"])
            conn = pyodbc.connect(dbstring)
            return conn

    def execute_case_sql(self, sql):
        """
        执行一条单独的SQL语句，完成连接数据库，执行，返回结果等全过程
        :param sql:
        :return:
        """
        try:
            ds = []
            conn = self.connect_to_case_db()
            if self._case_db_type == "MYSQL":
                crs = conn.cursor(MySQLdb.cursors.DictCursor)
                row_number = crs.execute(sql)
                if row_number > 0:
                    ds = list(crs.fetchall())
                crs.close()
                conn.commit()
                conn.close()
                return 0, ds
            return 0, ds
        except:
            crs.close()
            conn.rollback()
            conn.close()
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def client_heart_beat(self, agent_id, agent_state):
        try:
            last_alive = datetime.datetime.now()
            if agent_id not in self._clients_dict.keys():
                return 0, ""
            self._clients_dict[agent_id]["state"] = agent_state
            self._clients_dict[agent_id]["last_alive"] = last_alive

            sql = "update sx_agent_info set state='%s',LAST_ALIVE='%s' where agent_id = %d" % (
                agent_state, str(last_alive), int(agent_id))
            Logging.getLog().debug(sql)
            cF.executeCaseSQL(sql)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1, exc_info

    def eval_json_data(self, msg_dict):
        Logging.getLog().debug("反序列化时间戳 dict:%s" % str(time.time()))
        try:
            if not isinstance(msg_dict, dict):
                msg_dict = json.loads(msg_dict)
                if not isinstance(msg_dict, dict):
                    self.eval_json_data(msg_dict)
                else:
                    return msg_dict
            return msg_dict
        except:
            exc_info = cF.getExceptionInfo()
            # print exc_info
            return eval(msg_dict)

    # def tell_case_result(self, agent_id, msg_info):
    #     try:
    #         # Logging.getLog().debug("start deal with msg_info %s" % str(time.time()))
    #         msg_info = self.eval_json_data(msg_info)
    #         # Logging.getLog().debug("end deal with msg_info %s" % str(time.time()))
    #         ret, msg = self._task.processCasesResultMsg(msg_info)
    #         Logging.getLog().debug("success processCasesResultMsg %s" % str(time.time()))
    #         self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_FREE
    #         if ret < 0:
    #             Logging.getLog().error(msg)
    #         return ret, msg
    #     except:
    #         Logging.getLog().debug("tell_case_result %s" % msg_info)
    #         self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_FREE
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         return -1, exc_info

    # def tell_script_update_result(self, agent_id):
    #     try:
    #         self._clients_dict[agent_id]["state"] = gl.CLIENT_STATE_FREE
    #         self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_FREE
    #         return 0, ""
    #     except:
    #         self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_FREE
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         return -1, exc_info
    #     pass

    # def tell_env_init_result(self, agent_id, runtaskid, result):
    #     try:
    #         runtaskid = int(runtaskid)
    #         if runtaskid in self._task._cases_task_dict.keys():
    #             self._task._cases_task_dict[runtaskid]['init_state'] = result
    #             Logging.getLog().debug("switch %s task init_state to %s" % (str(runtaskid), result))
    #         sql = "update sx_cases_collection_run_task set init_state = '%s' where collection_run_task_id = %d " % (
    #             result, int(runtaskid))
    #         Logging.getLog().debug(sql)
    #         cF.executeCaseSQL(sql)
    #         self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_FREE
    #         return 0, ""
    #     except:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         self._clients_dict[agent_id]["task_state"] = gl.CLIENT_TASK_STATE_FREE
    #         return -1, exc_info

    def compare_task_data_change(self, left_task_id, right_task_id, force_recompare_flag):
        '''
        提供给WEB端的接口函数，采用RPC方式，触发比较两个任务之间的数据变动对比的函数。
        
        :param left_task_id: int类型，对比时位于左侧的任务ID号
        :param right_task_id: int类型，对比时位于右侧的任务ID号
        :param force_recompare_flag: int类型, 是否需要强制重新对比。0代表不需要强制重新对比，1代表需要强制重新对比
        :return:
            "1": 比较正在进行中
            "0"：比较已经完成，可以读取相关数据
            "-1": 有错误，提醒用户"查看TestAgentServer"日志信息以便查找原因
        '''
        if self._compare_task_data_change_state == self._STATE_EXECUTING:
            return "1"
        elif self._compare_task_data_change_state == self._STATE_ERROR:
            self._compare_task_data_change_state = self._STATE_INIT  # 只提醒一次
            return "-1"

        if force_recompare_flag == 1:
            self._compare_task_data_change_state = self._STATE_EXECUTING
            self.async_compare_task_data_change(left_task_id, right_task_id)
            return "1"
        else:
            sql = "SELECT  compare_result_info  FROM sx_run_task_data_compare WHERE left_run_task_id = %s AND right_run_task_id = %s" % (
                str(left_task_id), str(right_task_id))
            ds = cF.executeCaseSQL(sql)
            if len(ds) > 0:
                return "0"
            else:
                self._compare_task_data_change_state = self._STATE_EXECUTING
                self.async_compare_task_data_change(left_task_id, right_task_id)
                return "1"

    @async
    def async_compare_task_data_change(self, left_task_id, right_task_id):
        ret, msg = db_data_compare.compare_two_task_data_change(left_task_id, right_task_id)
        if ret == 0:
            self._compare_task_data_change_state = self._STATE_INIT
        else:
            self._compare_task_data_change_state = self._STATE_ERROR
        return

    def scan_db_info(self, system_id, data_compare_flag):
        '''
        提供给WEB端的接口函数，采用RPC方式，触发比较两个任务之间的数据变动对比的函数。
        
        查看数据库是否已经有了现成的数据，如果有，就直接返回0，否则就是执行比较的后台异步操作
        
        :param system_id: string类型, 需要扫描的字符串信息
        :param data_compare_flag: int类型，是否启用数据对比模式，如果启用就扫描完数据库后，直接创建触发器。0代表不需要启用，1代表需要启用。
        :return:
            "1": 扫描正在进行中
            "0"：扫描已经完成，可以读取相关数据
            "-1": 有错误，提醒用户"查看TestAgentServer"日志信息以便查找原因
        '''

        if self._scan_db_info_state_dict.has_key(system_id):
            if self._scan_db_info_state_dict[system_id] == self._STATE_EXECUTING:
                return "1"
            elif self._scan_db_info_state_dict[system_id] == self._STATE_ERROR:
                self._scan_db_info_state_dict[system_id] = self._STATE_INIT  # 只提醒一次
                return "-1"
            elif self._scan_db_info_state_dict[system_id] == self._STATE_FINISH:  # 只提醒一次
                self._scan_db_info_state_dict[system_id] = self._STATE_INIT
                return "0"
        else:
            self._scan_db_info_state_dict[system_id] = self._STATE_INIT

        self._scan_db_info_state_dict[system_id] = self._STATE_EXECUTING
        self.async_scan_db_info(system_id, data_compare_flag)

        return "1"

    def connection(self, connection_info):
        dbstring = ""
        if connection_info["DB_TYPE"].strip() == "SQLServer":
            dbstring = 'DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;' \
                       'autocommit=True' % (connection_info['DB_IP'], connection_info['DB_SCHEMA'],
                                            connection_info["DB_USERNAME"], connection_info["DB_PASSWORD"])

        return pyodbc.connect(dbstring)

    def getOldTableColumnInfos(self, conntioninfo):
        """
        获取表和字段信息
        :return:
        """
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor()
        col_info = {}
        try:
            sql = """SELECT t.tablename as tablename, t.disableflag as table_dis_flag, c.columnname as columnname,
            c.is_exclude as is_exclude FROM sx_table_info t INNER JOIN sx_column_info c
            ON(t.table_id = c.table_id) WHERE t.db_id = %s""" % conntioninfo["DB_ID"]
            ds = cF.executeCaseSQL_DB2(sql)
            for row in ds:
                tablename = row["TABLENAME"]
                table_dis_flag = row["TABLE_DIS_FLAG"]
                columnname = row["COLUMNNAME"].strip()
                is_exclude = row["IS_EXCLUDE"]
                # tablename, table_dis_flag, columnname, is_exclude = row
                if str(table_dis_flag) == "1":
                    continue
                if is_exclude != 1 and columnname != "":
                    keys = col_info.keys()
                    if str(tablename) in keys:
                        col_info[str(tablename)].append(str(columnname))
                    else:
                        col_info.update({str(tablename): [str(columnname)]})
            return col_info
        except Exception as e:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
            print -1, exc_info
            # finally:
            #     crs.close()
            #     conn.close()

    def get_sx_database_info(self, system_id):
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        sql = "select * from sx_database_info where db_type='SQLServer' and system_id='%s'" % system_id
        ds = cF.executeCaseSQL_DB2(sql)
        # crs.execute(sql, system_id)
        # ds = crs.fetchall()
        # crs.close()
        # conn.close()
        return list(ds)

    def createTrigger(self, system_id):
        '''
        SQL Server 数据库创建触发器
        '''
        error_table = []
        database_info = self.get_sx_database_info(system_id)
        try:
            for i in database_info:
                Logging.getLog().info("开始获取表数据")
                col_info = self.getOldTableColumnInfos(i)
                Logging.getLog().info("获取表数据成功")
                conn = self.connection(i)
                crs = conn.cursor()
                # 创建新触发器
                sql = """SELECT name FROM sysobjects WHERE xtype='TR'"""
                crs.execute(sql)
                ds = crs.fetchall()
                Logging.getLog().info("开始删除触发器")
                for rec in ds:
                    sql = "drop trigger %s" % (rec[0])
                    crs.execute(sql)
                    conn.commit()
                    Logging.getLog().info(sql)
                Logging.getLog().info("删除触发器成功")
                for key, value in col_info.items():
                    try:
                        table_name = key
                        print table_name
                        if table_name == "TMP_AUTOTEST_TRIGGER":
                            continue
                        # ['updzy_debts', 'tbldb2mdb', 'sumcrdtreport', 'TMP_AUTOTEST_TRIGGER', 'bjhgagentcust', 'szhk_sjsdz']
                        col_name = value
                        if 'by' in col_name:
                            col_name.remove("by")
                            col_name.append("[by]")
                        if 'BY' in col_name:
                            col_name.remove("BY")
                            col_name.append("[BY]")
                        flag = True
                        if len(col_name) >= 100:
                            flag = False
                        if flag:
                            if len(col_name) <= 1:
                                col_name.append("''")
                            col_name = ",'&',".join(col_name)
                            sql = """create trigger tgr_%s_update on %s for update as DECLARE @olddata VARCHAR(MAX),
                            @newdata VARCHAR(MAX), @data VARCHAR(MAX) select @olddata=concat(%s)
                            from deleted select @newdata=concat(%s) from inserted set
                            @data = '{"old":"' + @olddata + '","new":"' +@newdata + '"}'
                            insert into TMP_AUTOTEST_TRIGGER(tablename, operation, change_content) values('%s', 1, @data)""" % (
                                table_name, table_name, col_name, col_name, table_name)
                            crs.execute(sql)
                            sql = """create trigger tgr_%s_delete on %s for delete as DECLARE @data VARCHAR(MAX)
                            select @data=concat(%s) from deleted
                            insert into TMP_AUTOTEST_TRIGGER(tablename, operation, change_content) values('%s', 2, @data)""" % (
                                table_name, table_name, col_name, table_name)
                            crs.execute(sql)
                            sql = """create trigger tgr_%s_insert on %s for insert as DECLARE @data VARCHAR(MAX)
                            select @data=concat(%s) from INSERTED
                            insert into TMP_AUTOTEST_TRIGGER(tablename, operation, change_content) values('%s', 0, @data)""" % (
                                table_name, table_name, col_name, table_name)
                            crs.execute(sql)
                        else:
                            median = int(len(col_name) / 2)
                            args1 = col_name[:median]
                            args2 = col_name[median:]
                            col_name_args1 = ",'&',".join(args1)
                            col_name_args2 = ",'&',".join(args2)
                            sql = """create trigger tgr_%s_update on %s for update as DECLARE @olddata1 VARCHAR(MAX),
                                    @olddata2 VARCHAR(MAX), @newdata1 VARCHAR(MAX), @newdata2 VARCHAR(MAX), @data VARCHAR(MAX)
                                    select @olddata1=concat(%s), @olddata2=concat(%s) from deleted select @newdata1=concat(%s)
                                     ,@newdata2=concat(%s)from inserted set
                                    @data = '{"old":"' + @olddata1+ '&' + @olddata2 + '","new":"' +@newdata1 +'&'+@newdata2+ '"}'
                                    insert into TMP_AUTOTEST_TRIGGER(tablename, operation, change_content) values('%s', 1, @data)""" % (
                                table_name, table_name, col_name_args1, col_name_args2, col_name_args1, col_name_args2,
                                table_name)
                            crs.execute(sql)
                            sql = """create trigger tgr_%s_delete on %s for delete as DECLARE @data VARCHAR(MAX),
                                     @data1 VARCHAR(MAX),@data2 VARCHAR(MAX)
                                     select @data1=concat(%s), @data2=concat(%s) from deleted
                                     set @data = @data1 +'&'+ @data2
                                     insert into TMP_AUTOTEST_TRIGGER(tablename, operation, change_content) values('%s', 2, @data)""" % (
                                table_name, table_name, col_name_args1, col_name_args2, table_name)
                            crs.execute(sql)
                            sql = """create trigger tgr_%s_insert on %s for insert as DECLARE @data VARCHAR(MAX),
                                     @data1 VARCHAR(MAX),@data2 VARCHAR(MAX)
                                     select @data1=concat(%s), @data2=concat(%s) from INSERTED
                                     set @data = @data1 +'&' + @data2
                                     insert into TMP_AUTOTEST_TRIGGER(tablename, operation, change_content) values('%s', 0, @data)""" % (
                                table_name, table_name, col_name_args1, col_name_args2, table_name)
                            crs.execute(sql)
                    except Exception as e:
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().critical(exc_info)
                        gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
                        return -1, exc_info
            return 0, ''
        except Exception as e:
            crs.close()
            conn.rollback()
            conn.close()
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
            return -1, exc_info
        finally:
            crs.close()
            conn.commit()
            conn.close()

    def get_table_name(self, system_id):
        # table_data = []
        database_info = self.get_sx_database_info(system_id)
        for i in database_info:
            conn = self.connection(i)
            crs = conn.cursor()
            sql = "select * from sysobjects WHERE xtype='U' order by Name"
            crs.execute(sql)
            ds = crs.fetchall()
            old_table_info, old_col_info, table_ids = self.getOldTableColumnInfo(i)
            Logging.getLog().info("获取表数据ok")
            table_name_list = []
            for rec in ds:
                table_name_list.append(rec[0])
                self.get_table_syscolumns(i, rec[0])
                # print rec[0]
                # if rec[0] == "AUTO_D_DDAinfo":
                #     break
            # if table_name_list:
            #     print len(table_name_list)
            #     self.order_by_threading_get_table_data(i, table_name_list)
            #     # table_data = self.get_table_syscolumns(table_data, i, rec[0])
            #     # table_data = self.get_table_syscolumns(i, rec[0])
            global table_data
            # 删除表数据
            self.delete_sx_table_info_data(i)
            self.delete_sx_column_info_data(i, table_ids)
            for table_args in table_data:
                Logging.getLog().info("保存表数据")
                self.sava_sx_table_info(old_table_info, old_col_info, table_args)

        crs.close()
        conn.close()

    def MainRange(self, connection, table_name_list):
        for table_name in table_name_list:
            print table_name
            self.get_table_syscolumns(connection, table_name)

    def order_by_threading_get_table_data(self, connection, table_name_list):
        # 多线程部分
        one_fifth = int(len(table_name_list) / 30)
        threads = []
        for i in range(0, 30):
            t_args = ""
            if i == 29:
                t_args = table_name_list[one_fifth * i:]
            else:
                t_args = table_name_list[one_fifth * i:one_fifth * (i + 1)]
            t = threading.Thread(target=self.MainRange, args=(connection, t_args))
            threads.append(t)
        for t in threads:
            t.setDaemon(True)
            t.start()
        for t in threads:
            t.join()
        print "ok"

    def delete_sx_table_info_data(self, conntioninfo):
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # cursor = conn.cursor()
        sql = "delete from sx_table_info WHERE db_id=%s" % conntioninfo["DB_ID"]
        cF.executeCaseSQL_DB2(sql)
        # cursor.execute(sql)
        # conn.commit()
        # cursor.close()
        # conn.close()

    def delete_sx_column_info_data(self, conntioninfo, table_ids):
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor()
        if table_ids:
            table_ids = ",".join(table_ids)
            sql = "delete from sx_column_info WHERE table_id in (" + table_ids + ")"
            cF.executeCaseSQL_DB2(sql)
            # conn.commit()
            # crs.close()
            # conn.close()

    def getOldTableColumnInfo(self, conntioninfo):
        """
        获取表和字段信息
        :return:
        """
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor()
        table_info = []
        col_info = {}
        table_ids = []
        Logging.getLog().info("获取表数据")
        try:
            sql = """SELECT t.tablename as TABLENAME, t.disableflag as TABLE_DIS_FLAG, c.columnname as COLUMNNAME,
            c.disableflag as COLUMN_DIS_FLAG, c.table_id as TABLE_ID FROM sx_table_info t INNER JOIN sx_column_info c
            ON(t.table_id = c.table_id) WHERE t.db_id = %s""" % conntioninfo["DB_ID"]
            # crs.execute(sql)
            ds = cF.executeCaseSQL_DB2(sql)
            # for row in crs.fetchall():
            for row in ds:
                tablename = row["TABLENAME"]
                table_dis_flag = row["TABLE_DIS_FLAG"]
                columnname = row["COLUMNNAME"]
                column_dis_flag = row["COLUMN_DIS_FLAG"]
                table_id = row["TABLE_ID"]
                # tablename, table_dis_flag, columnname, column_dis_flag, table_id = row
                table_ids.append(str(table_id))
                if table_dis_flag == 1:
                    table_info.append(str(tablename))
                if column_dis_flag == 1:
                    keys = col_info.keys()
                    if str(tablename) in keys:
                        col_info[str(tablename)].append(str(columnname))
                    else:
                        col_info.update({str(tablename): [str(columnname)]})
            return table_info, col_info, table_ids
        except Exception as e:
            raise e
            # finally:
            #     crs.close()
            #     conn.close()

    def get_table_syscolumns(self, connection_info, table_name):
        global table_data
        types = ['binary', 'varbinary', 'image']
        PK = self.get_keys(connection_info, table_name)
        table_columns_info = {}
        table_args = dict(connection_info=connection_info, table_name=table_name, PK=PK)
        table_columns_info.update({"table": table_args})
        conn = self.connection(connection_info)
        crs = conn.cursor()
        sql = "sp_columns @table_name = '%s'" % table_name
        crs.execute(sql)
        ds = crs.fetchall()
        index_column = 0
        columns_info = []
        for rec in ds:
            # print rec
            index_column += 1
            is_exclude = ''
            if rec[5] in types:
                is_exclude = 1
            columns_args = dict(index_column=index_column, connection_info=connection_info, rec=rec,
                                is_exclude=is_exclude)
            columns_info.append(columns_args)
        table_columns_info.update({"columns": columns_info})
        table_data.append(table_columns_info)
        crs.close()
        conn.close()
        return table_data

    def sava_sx_column_info(self, table_args, table_id, table_name, old_col_info):
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor()
        for i in table_args:
            old_table_name = old_col_info.keys()
            disableflag = 0
            if table_name in old_table_name:
                col_list = old_col_info[str(table_name)]
                if i["rec"][3] in col_list:
                    disableflag = 1

            sql = ""
            # print i
            if i["is_exclude"]:
                sql = "insert into sx_column_info(table_id, idx, columnname, is_exclude, disableflag)values" \
                      "(%s, %s, '%s', %s, %s)" % (
                          int(table_id), int(i["index_column"]), str(i["rec"][3]).strip(), i["is_exclude"], disableflag)
            else:
                sql = "insert into sx_column_info(table_id, idx, columnname, disableflag)values" \
                      "(%s, %s, '%s', %s)" % (
                          int(table_id), int(i["index_column"]), str(i["rec"][3]).strip(), disableflag)
            cF.executeCaseSQL_DB2(sql)
            # conn.commit()
            # crs.close()
            # conn.close()

    def sava_sx_table_info(self, old_table_info, old_col_info, table_args):
        global count
        count += 1
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor()
        table_name = table_args["table"]['table_name']  # connection_info, table_name, PK
        disableflag = 0
        print table_name
        if table_name in old_table_info:
            disableflag = 1

        sql = "insert into sx_table_info(db_id, db_schema, tablename, pk, disableflag)values" \
              "(%s, '%s', '%s', '%s',%s)" % (int(table_args["table"]["connection_info"]["DB_ID"]),
                                             table_args["table"]["connection_info"]["DB_SCHEMA"],
                                             table_name, table_args["table"]["PK"], disableflag)
        cF.executeCaseSQL_DB2(sql)
        table_id = ""
        sql = "select max(TABLE_ID) as TABLE_ID from SX_TABLE_INFO"
        ds = cF.executeCaseSQL_DB2(sql)
        if ds:
            table_id = ds[0]["TABLE_ID"]
        # conn.commit()
        # crs.close()
        # conn.close()
        self.sava_sx_column_info(table_args["columns"], table_id, table_name, old_col_info)

    def get_keys(self, connection_info, table_name):
        conn = self.connection(connection_info)
        crs = conn.cursor()
        sql = "EXEC sp_pkeys @table_name='%s'" % table_name
        crs.execute(sql)
        ds = crs.fetchall()
        PK = []
        PK_str = ""
        try:
            if ds:
                for i in ds:
                    PK.append(i[3])
                PK_str = ",".join(PK)
        except Exception as e:
            print e
        crs.close()
        conn.close()
        return PK_str

    def compare_chage_data(self, id):
        try:
            if not id:
                Logging.getLog().info("需要传入客户号 身份证号 或 cif账号")
            DB2_DATA = []
            str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info"
            rst_temp = cF.executeCaseSQL_DB2(str_MySQL_SQL)
            for item in rst_temp:
                DB2_DATA.append(item)

            homedir = os.getcwd()
            path = homedir + "\\case_change_data"
            for root, dirs, files in os.walk(path):
                if len(dirs) <= 2:
                    Logging.getLog().info("请先执行两遍开户")
                    return
                _dirs = dirs[-2:]
                # for dir in dirs:
                sqlserver_tables = {}
                oracle_tables = {}
                # 第一次开户数据
                dir_1 = _dirs[0]
                path_dir_1 = path + "\\%s" % dir_1
                for root, dirs, files in os.walk(path_dir_1):
                    if files:
                        for filename in files:
                            if "QRTZ_SCHEDULER_STATE" in filename:
                                continue
                            if "delete" in filename:
                                continue
                            elif "update_before" in filename:
                                continue
                            elif filename.startswith("run."):
                                str_db_schema = filename.split(".")[1]
                                table_name = filename.split(".")[2]
                                if sqlserver_tables:
                                    if str_db_schema in sqlserver_tables.keys():
                                        if table_name in sqlserver_tables[str_db_schema].keys():
                                            sqlserver_tables[str_db_schema][table_name].append(filename)
                                        else:
                                            sqlserver_tables[str_db_schema][table_name] = [filename]
                                    else:
                                        sqlserver_tables[str_db_schema] = {table_name: [filename]}
                                else:
                                    sqlserver_tables[str_db_schema] = {table_name: [filename]}
                            elif filename.startswith("0.") or filename.startswith("1."):
                                str_db_schema = filename.split(".")[1]
                                table_name = filename.split(".")[2]
                                if oracle_tables:
                                    if str_db_schema in oracle_tables.keys():
                                        if table_name in oracle_tables[str_db_schema].keys():
                                            oracle_tables[str_db_schema][table_name].append(filename)
                                        else:
                                            oracle_tables[str_db_schema][table_name] = [filename]
                                    else:
                                        oracle_tables[str_db_schema] = {table_name: [filename]}
                                else:
                                    oracle_tables[str_db_schema] = {table_name: [filename]}
                            else:
                                pass
                        if sqlserver_tables:
                            for str_db_schema in sqlserver_tables:
                                for table_name in sqlserver_tables[str_db_schema]:
                                    insert_flag = False
                                    update_flag = False
                                    filter_table = []
                                    for table in sqlserver_tables[str_db_schema][table_name]:
                                        if 'insert' in table:
                                            insert_flag = True

                                        if "update" in table:
                                            update_flag = True
                                    if insert_flag == True and update_flag == True:
                                        for table in sqlserver_tables[str_db_schema][table_name]:
                                            if "update" in table:
                                                filter_table.append(table)
                                    if filter_table:
                                        sqlserver_tables[str_db_schema][table_name] = filter_table
                                    if len(sqlserver_tables[str_db_schema][table_name]) >= 2:
                                        nums = [int(table.replace('.csv', '')[-1]) for table in
                                                sqlserver_tables[str_db_schema][table_name]]
                                        max_num = str(max(nums))
                                        for table in sqlserver_tables[str_db_schema][table_name]:
                                            if table.replace('.csv', '').endswith(max_num):
                                                sqlserver_tables[str_db_schema][table_name] = [table]
                                                break
                        if oracle_tables:
                            for str_db_schema in oracle_tables:
                                for table_name in oracle_tables[str_db_schema]:
                                    insert_flag = False
                                    update_flag = False
                                    filter_table = []
                                    for table in oracle_tables[str_db_schema][table_name]:
                                        if 'insert' in table:
                                            insert_flag = True

                                        if "update" in table:
                                            update_flag = True
                                    if insert_flag == True and update_flag == True:
                                        for table in oracle_tables[str_db_schema][table_name]:
                                            if "update" in table:
                                                filter_table.append(table)
                                    if filter_table:
                                        oracle_tables[str_db_schema][table_name] = filter_table
                                    if len(oracle_tables[str_db_schema][table_name]) >= 2:
                                        nums = [int(table.replace('.csv', '')[-1]) for table in
                                                oracle_tables[str_db_schema][table_name]]
                                        max_num = str(max(nums))
                                        for table in oracle_tables[str_db_schema][table_name]:
                                            if table.replace('.csv', '').endswith(max_num):
                                                oracle_tables[str_db_schema][table_name] = [table]
                                                break
                # 第1次开户数据和第二次开户数据作对比
                dir_2 = _dirs[1]
                path_dir_2 = path + "\\%s" % dir_2
                for root, dirs, files in os.walk(path_dir_2):
                    # 对比sqlserver_tables的数据
                    try:
                        for str_db_schema in sqlserver_tables:
                            str_db_ip, db_schema, str_db_username, str_db_password, conn, cursor = "", "", "", "", "", ""
                            for item in DB2_DATA:
                                db_schema = item['DB_SCHEMA']
                                if str_db_schema == db_schema:
                                    str_db_type = item['DB_TYPE']
                                    str_db_ip = item['DB_IP']
                                    str_db_username = item['DB_USERNAME']
                                    str_db_password = item['DB_PASSWORD']
                                    if str_db_type == "SQLServer":
                                        dbstring = ""
                                        if str_db_type.strip() == "SQLServer":
                                            dbstring = 'DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;' \
                                                       'autocommit=True' % (
                                                           str_db_ip, db_schema, str_db_username, str_db_password)
                                        conn = pyodbc.connect(dbstring)
                                        cursor = conn.cursor()
                                        break
                            for table_name in sqlserver_tables[str_db_schema]:
                                for file_name in sqlserver_tables[str_db_schema][table_name]:
                                    if file_name in files:
                                        Logging.getLog().info(file_name)
                                        # 先获取第一次开户对应的表数据
                                        path_file_1 = path_dir_1 + "\\%s" % file_name
                                        tabledata1 = self.analysis_csv_file(path_file_1, file_name)
                                        # 先获取第2次开户对应的表数据
                                        path_file_2 = path_dir_2 + "\\%s" % file_name
                                        tabledata2 = self.analysis_csv_file(path_file_2, file_name)
                                        same_field_value = set(tabledata1.items()) & set(tabledata2.items())
                                        field_str = ""
                                        sql = "select PK from SX_TABLE_INFO where DB_SCHEMA='%s' and TABLENAME='%s'" % (
                                            db_schema, table_name)
                                        rs = cF.executeCaseSQL_DB2(sql)
                                        if not rs:
                                            Logging.getLog().error(
                                                "%s---没有查找表的主键------%s" % (str_db_schema, table_name))
                                            return
                                        else:
                                            PK = rs[0]["PK"]
                                            if ',' in PK:
                                                Logging.getLog().error(
                                                    "%s---表含有多个主键------%s" % (str_db_schema, table_name))
                                                return
                                            if not PK:
                                                Logging.getLog().error(
                                                    "%s---没有查找表的主键------%s" % (str_db_schema, table_name))
                                                continue
                                            for fields in list(same_field_value):
                                                if str(fields[0]) == str(PK):
                                                    continue
                                                field = fields[0] + "='%s'," % fields[1]
                                                field_str += field
                                            field_str = field_str[:-1]
                                            SQL = "update " + table_name + " set " + field_str + " where %s='%s'" % (
                                                PK, id)
                                            cursor.execute(SQL)
                            if conn:
                                pass
                                # conn.commit()
                                # cursor.close()
                                # conn.close()
                    except Exception as e:
                        raise e
                    try:
                        # 对比oracle_tables的数据
                        for str_db_schema in oracle_tables:
                            str_db_ip, db_schema, str_db_username, str_db_password, conn, cursor = "", "", "", "", "", ""
                            for item in DB2_DATA:
                                db_schema = item['DB_SCHEMA']
                                if str_db_schema == db_schema:
                                    str_db_username = item['DB_USERNAME']
                                    str_db_password = item['DB_PASSWORD']
                                    str_db_servicename = item['DB_SERVICENAME']
                                    con = cx_Oracle.connect(str_db_username, str_db_password, str_db_servicename)
                                    cursor = con.cursor()
                                    break
                            for table_name in oracle_tables[str_db_schema]:
                                for file_name in oracle_tables[str_db_schema][table_name]:
                                    if file_name in files:
                                        Logging.getLog().info(file_name)
                                        # 先获取第一次开户对应的表数据
                                        path_file_1 = path_dir_1 + "\\%s" % file_name
                                        tabledata1 = self.analysis_csv_file(path_file_1, file_name)
                                        # 先获取第2次开户对应的表数据
                                        path_file_2 = path_dir_2 + "\\%s" % file_name
                                        tabledata2 = self.analysis_csv_file(path_file_2, file_name)
                                        same_field_value = set(tabledata1.items()) & set(tabledata2.items())
                                        field_str = ""
                                        sql = "select PK from SX_TABLE_INFO where DB_SCHEMA='%s' and TABLENAME='%s'" % (
                                            db_schema, table_name)
                                        rs = cF.executeCaseSQL_DB2(sql)
                                        if not rs:
                                            Logging.getLog().error(
                                                "%s---没有查找表的主键------%s" % (str_db_schema, table_name))
                                            return
                                        else:
                                            PK = rs[0]["PK"]
                                            if ',' in PK:
                                                Logging.getLog().error(
                                                    "%s---表含有多个主键------%s" % (str_db_schema, table_name))
                                                return
                                            if not PK:
                                                Logging.getLog().error(
                                                    "%s---没有查找表的主键------%s" % (str_db_schema, table_name))
                                                continue
                                            for fields in list(same_field_value):
                                                if str(fields[0]) == str(PK):
                                                    continue
                                                field = fields[0] + "='%s'," % fields[1]
                                                field_str += field
                                            field_str = field_str[:-1]
                                            SQL = "update " + table_name + " set " + field_str + " where %s='%s'" % (
                                                PK, id)
                                            Logging.getLog().error(SQL)
                                            cursor.execute(SQL)
                            if conn:
                                pass
                                # conn.commit()
                                # cursor.close()
                                # conn.close()
                    except Exception as e:
                        raise e
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def analysis_csv_file(self, path_file, file_name):
        try:
            table_data = []
            csvfile = open(path_file, 'r')
            reader = csv.reader(csvfile)
            for item in reader:
                table_data.append(item)
            if not table_data:
                Logging.getLog().error("表数据有误-------%s" % file_name)
                return 0, ''
            if len(table_data) == 1:
                Logging.getLog().error("表数据为空-------%s" % file_name)
                return 0, ''
            if len(table_data) > 2:
                Logging.getLog().error("表数据不要存在多行数据, 请核对-------%s" % file_name)
                return 0, ''
            tabledata = dict(zip(table_data[0], table_data[1]))
            return tabledata
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def get_sx_cases_collection_detail_info(self, task_id):
        try:
            result = []
            CASES_ID_LIST = []
            sql = "select CASES_ID, COLLECTION_ID from SX_CASES_COLLECTION_DETAIL where COLLECTION_ID in (select " \
                  "COLLECTION_ID from SX_CASES_COLLECTION_RUN_TASK where COLLECTION_RUN_TASK_ID = %s)" % task_id
            rs = cF.executeCaseSQL_DB2(sql)
            if rs:
                CASES_ID_LIST = [str(line['CASES_ID']) for line in rs]
            if not CASES_ID_LIST:
                return 0, ""
            CASES_ID_LIST = [CASES_ID_LIST[i:i + 2000] for i in range(0, len(CASES_ID_LIST), 2000)]
            for child_cases_id_list in CASES_ID_LIST:
                cases_ids_str = ",".join(child_cases_id_list)
                # Logging.getLog().debug(cases_ids_str)
                # Logging.getLog().debug(u"查询数据库时间%s" % str(time.time()))
                sql = "select sx.CASE_NAME ,detail.CASES_ID,detail.CASES_DETAIL_ID,detail.PARAM_ID, detail.FUNCID,DETAIL_PARAM_DATA.PARAM_DATA_ID " \
                      ",DETAIL_PARAM_DATA.PARAM_DATA from sx_cases as sx, sx_cases_detail as detail, SX_CASES_DETAIL_PARAM_DATA as DETAIL_PARAM_DATA " \
                      "where sx.CASES_ID = detail.CASES_ID and detail.CASES_DETAIL_ID =DETAIL_PARAM_DATA.CASES_DETAIL_ID and  detail.ADAPTER_TYPE = 'SPLX_SELENIUM' AND detail.IS_DELETE = '0' AND detail.CASES_ID IN (%s) order by detail.FUNCID" % cases_ids_str
                rs = cF.executeCaseSQL_DB2(sql)
                if rs:
                    result.extend(rs)
            Logging.getLog().debug(u"SPLX_SELENIUM 数据量：%s" % (len(result)))
            # Logging.getLog().debug(u"查询数据库时间戳%s" % str(time.time()))
            return 0, result
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def get_change_data(self, flag):
        try:
            if flag == 1:
                scanOracleDB.delete_change_data_oracle_or_slqserver()
            else:
                scanOracleDB.get_change_data_oracle_or_slqserver()
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    @async
    def async_scan_db_info(self, system_id, data_compare_flag):
        try:
            # print '创建sqlserver触发器'
            # self.get_table_name(system_id)
            # ret, msg = self.createTrigger(system_id)
            # if ret != 0:
            #     self._scan_db_info_state_dict[system_id] = self._STATE_ERROR
            #     return
            # print '删除ORACLE触发器'
            # ret, msg = scanOracleDB.dropOracleTrigger(system_id)
            # if ret != 0:
            #     self._scan_db_info_state_dict[system_id] = self._STATE_ERROR
            #     return
            # print '获取oracle表结构信息'
            # ret, msg = scanOracleDB.scanOracleDB(system_id)
            # if ret != 0:
            #     self._scan_db_info_state_dict[system_id] = self._STATE_ERROR
            #     return
            # print '更新二进制类型字段的状态为1(RAW,LONG RAW,BLOB,BFILE,NROWID)'
            # ret, msg = scanOracleDB.update_sx_column_info_disableflag()
            # if ret != 0:
            #     self._scan_db_info_state_dict[system_id] = self._STATE_ERROR
            #     return
            # print '创建oracle触发器'
            # ret, msg = scanOracleDB.createOracleTrigger(system_id)
            # if ret != 0:
            #     self._scan_db_info_state_dict[system_id] = self._STATE_ERROR
            #     return
            # self._scan_db_info_state_dict[system_id] = self._STATE_FINISH
            # print '触发器 ok'
            #
            # # 加载所有的数据库表，字段，disableflag信息
            # self.update_table_column_disableflag_info()
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            self._scan_db_info_state_dict[system_id] = self._STATE_ERROR
            return -1, exc_info

    # @async
    # def trigger_script_update(self, agent_id):
    #
    #     # 发送更新脚本信息
    #     Logging.getLog().debug("call trigger_script_update(%s)" % agent_id)
    #     update_script_msg = copy.copy(gl.update_script_msg)
    #     ServerUrl = "http://%s:%s" % (self._clients_dict[agent_id]["ip"], self._clients_dict[agent_id]["port"])
    #     Logging.getLog().debug(ServerUrl)
    #     s = ServerProxy(ServerUrl)
    #
    #     retry_count = 0
    #     while retry_count < gl.SERVER_MAX_RETRY_COUNT:
    #         try:
    #             # 先更新系统数据库信息
    #
    #             ret, msg = s.UpdateSystemDBInfo(json.dumps(self._system_db_info))
    #             if ret < 0:
    #                 Logging.getLog().error(msg)
    #
    #             if ret < 0:
    #                 Logging.getLog().error("fail to upload file")
    #             # 执行脚本更新
    #             ret, msg = s.processScriptUpdate(update_script_msg)
    #             if ret < 0:
    #                 Logging.getLog().error(msg)
    #             else:
    #                 self._clients_dict[agent_id]["state"] = gl.CLIENT_STATE_UPDATE  # 手工修改，避免状态同步不畅导致的冲突
    #             if ret < 0:
    #                 Logging.getLog().error(msg)
    #             else:
    #                 self._clients_dict[agent_id]["state"] = gl.CLIENT_STATE_UPDATE  # 手工修改，避免状态同步不畅导致的冲突
    #             return ret, msg
    #         except BaseException, ex:
    #             Logging.getLog().error("%s" % ex)
    #             # Logging.critical("%s" %ex)
    #             retry_count += 1
    #             time.sleep(3)
    #             # gl.is_exit_all_thread = True
    #
    #     return -1, ex

    def registerTaskThread(self, task):
        self._task = task

    def update_system_db_table_column_disable_info_to_ftp(self):
        """
        
        :return:
        """
        fp = file('system_db_table.json', 'w')
        json.dump(self._system_db_table_column_disable_info, fp)
        fp.close()

        # 上传到FTP
        ret, f = self.createFTPClient()
        if ret < 0:
            return ret, f
        f.upload_file_ex('system_db_table.json', "./Script")
        # f.close()

    def processHeartBeatMsg(self, msg):
        try:
            agent_id = msg["msg_body"]["agent_id"]
            agent_state = msg["msg_body"]["agent_state"]
            last_alive = datetime.datetime.now()
            if agent_id not in self._clients_dict.keys():
                return 0, ""
            self._clients_dict[agent_id]["state"] = agent_state
            self._clients_dict[agent_id]["last_alive"] = last_alive

            sql = "update sx_agent_info set state='%s',LAST_ALIVE='%s' where agent_id = %d" % (
                agent_state, str(last_alive), int(agent_id))
            Logging.getLog().debug(sql)
            cF.executeCaseSQL(sql)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1, exc_info

    def asyncupdate_account_group_info(self, system_id, data, account_id, case_adapter_type):
        try:
            ret, msg = self.update_account_group_info(system_id, data, account_id, case_adapter_type)
            if ret < 0:
                Logging.getLog().error(msg)
            return ret, msg
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            self._client_state = gl.CLIENT_STATE_FREE
            return -1, exc_info

    @async
    def update_account_group_info(self, system_id, data, account_id, case_adapter_type):
        """
        保存Agent传递过来的用户组信息
        :param system_id:
        :param data:
        :return:
        """
        try:
            sql = "select GROUP_DESC from sx_account_group_info where SYSTEM_ID='%s' and GROUP_ID=%s" % (
                system_id, int(account_id))
            GROUP_DESC = ""
            ds = cF.executeCaseSQL(sql)
            if ds:
                GROUP_DESC = ds[0]['GROUP_DESC']
            print "GROUP_DESC===%s" % GROUP_DESC
            if case_adapter_type == "SPLX_SELENIUM":
                for key, value in data.items():
                    sql = "select count(*) as NUM from sx_account_group_info where SYSTEM_ID='%s' and FILELD_NAME='%s' and GROUP_ID=%s" % (
                        system_id, key, int(account_id))
                    ds = cF.executeCaseSQL(sql)
                    print ds
                    num = ds[0]['NUM']
                    if num == 0:
                        args = (int(account_id), system_id, key, value, GROUP_DESC)
                        sql = "insert into sx_account_group_info(GROUP_ID, SYSTEM_ID, FILELD_NAME,  FIELD_VALUE, GROUP_DESC) values(%s,'%s','%s','%s', '%s')" % args
                        Logging.getLog().debug(sql)
                        cF.executeCaseSQL(sql)
                    else:
                        sql = "update sx_account_group_info set FIELD_VALUE='%s' where SYSTEM_ID='%s' and FILELD_NAME='%s' and GROUP_ID=%s" % (
                            value, system_id, key, int(account_id))
                        Logging.getLog().debug(sql)
                        cF.executeCaseSQL(sql)
            else:
                for child_data in data:
                    for account_id in child_data:
                        if 'update' in child_data[str(account_id)].keys():
                            for FILELD_NAME, FIELD_VALUE in child_data[str(account_id)]['update'].items():
                                if FIELD_VALUE and FILELD_NAME:
                                    if not str(FIELD_VALUE).endswith("|") and FILELD_NAME == 'paper_answer':
                                        FIELD_VALUE = FIELD_VALUE + "|"
                                if FIELD_VALUE:
                                    FIELD_VALUE = FIELD_VALUE.replace("'", "''").lower()
                                sql = "update sx_account_group_info set FIELD_VALUE='%s' where SYSTEM_ID='%s' and lower(FILELD_NAME)='%s' and GROUP_ID=%s" % (
                                    FIELD_VALUE, system_id, FILELD_NAME, int(account_id))
                                Logging.getLog().debug(sql)
                                cF.executeCaseSQL(sql)
                        if 'insert' in child_data[str(account_id)].keys():
                            insert_data = []
                            for FILELD_NAME, FIELD_VALUE in child_data[str(account_id)]['insert'].items():
                                if FIELD_VALUE and FILELD_NAME:
                                    if not str(FIELD_VALUE).endswith("|") and FILELD_NAME == 'paper_answer':
                                        FIELD_VALUE = FIELD_VALUE + "|"
                                if FIELD_VALUE:
                                    FIELD_VALUE = FIELD_VALUE.replace("'", "''").lower()
                                args = (int(account_id), system_id, FILELD_NAME, FIELD_VALUE, GROUP_DESC)
                                insert_data.append("(%s,'%s','%s','%s','%s')" % args)
                            sql = "insert into sx_account_group_info(GROUP_ID, SYSTEM_ID, FILELD_NAME,  FIELD_VALUE, GROUP_DESC) values %s" % (
                            ','.join(insert_data))
                            Logging.getLog().debug(sql)
                            cF.executeCaseSQL(sql)
            sql = "update SX_ACCOUNT_GROUP_INFO set GROUP_DESC='' where SYSTEM_ID = '%s'  and GROUP_DESC is null" % system_id
            Logging.getLog().debug(sql)
            cF.executeCaseSQL(sql)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1, exc_info

    def generate_account_group_xml_orderby_system_id(self, SYSTEM_ID, data, core_data, WHETHER_SERVERID_FLAG):
        try:
            suffix = cF.get_suffix(SYSTEM_ID)
            root = etree.Element("%sAutoTestSetting" % (suffix))
            if WHETHER_SERVERID_FLAG == False:
                JZJYSystemSetting = etree.SubElement(root, "JZJYSystemSetting")
                result = {}
                SERVERIDS = []
                for i in data.values():
                    if int(i["SERVERID"]) in SERVERIDS:
                        result[str(i["SERVERID"])].append(i)
                    else:
                        SERVERIDS.append(int(i["SERVERID"]))
                        result[str(i["SERVERID"])] = []
                        result[str(i["SERVERID"])].append(i)
                SERVERIDS.sort()
                SERVERIDS = list(set(SERVERIDS))
                if SERVERIDS:
                    for SERVERID in SERVERIDS:
                        type = ''
                        ip = ''
                        description = ''
                        dbip = ''
                        if str(SERVERID) in core_data.keys():
                            type = core_data[str(SERVERID)]['KCBP_TYPE']
                            ip = core_data[str(SERVERID)]['KCBP_IP']
                            description = core_data[str(SERVERID)]['KCBP_DESC']
                            dbip = core_data[str(SERVERID)]['dbip']
                        ServerSetting = etree.SubElement(JZJYSystemSetting, "ServerSetting", id=str(SERVERID),
                                                         type=type, ip=ip, description=description, dbip=dbip)
                        account_data = result[str(SERVERID)]
                        group_ids = []
                        group_data = {}
                        for account in account_data:
                            if account["GROUP_ID"] in group_ids:
                                group_data[str(account["GROUP_ID"])].append(account)
                            else:
                                group_ids.append(int(account["GROUP_ID"]))
                                group_data[str(account["GROUP_ID"])] = []
                                group_data[str(account["GROUP_ID"])].append(account)
                        group_ids.sort()
                        group_ids = list(set(group_ids))
                        if group_ids:
                            for group_id in group_ids:
                                AccountGroup = etree.SubElement(ServerSetting, "AccountGroup", id=str(group_id))
                                for group in group_data[str(group_id)]:
                                    FILELD_NAME = etree.SubElement(AccountGroup, str(group['FILELD_NAME']).lower())
                                    FILELD_NAME.text = group['FIELD_VALUE']
            else:
                group_ids = []
                group_data = {}
                for i in data.values():
                    if i["GROUP_ID"] in group_ids:
                        group_data[str(i["GROUP_ID"])].append(i)
                    else:
                        group_ids.append(int(i["GROUP_ID"]))
                        group_data[str(i["GROUP_ID"])] = []
                        group_data[str(i["GROUP_ID"])].append(i)
                group_ids.sort()
                group_ids = list(set(group_ids))
                if group_ids:
                    for group_id in group_ids:
                        AccountGroup = etree.SubElement(root, "AccountInfo", id=str(group_id))
                        for group in group_data[str(group_id)]:
                            try:
                                FILELD_NAME = etree.SubElement(AccountGroup, str(group['FILELD_NAME']).lower())
                                if 'paper_answer' == FILELD_NAME:
                                    pass
                                FILELD_NAME.text = group['FIELD_VALUE'].replace("&amp;", "&")
                            except Exception as e:
                                print group
                                Logging.getLog().error(str(group))
                                pass
            homedir = os.getcwd()
            print '<<<<<<<创建目录'
            if not os.path.exists("%s\init\%s" % (homedir, SYSTEM_ID)):
                os.makedirs("%s\init\%s" % (homedir, SYSTEM_ID))
                print '已创建'
            path = '%s\init\%s\%sAccountGroupSetting.xml' % (homedir, SYSTEM_ID, suffix)
            doc = etree.ElementTree(root)
            doc.write(path, pretty_print=True, xml_declaration=True, encoding='utf-8')
            print "%sAccountGroupSetting.xml 文件已生成" % suffix
            file_name = "%sAccountGroupSetting.xml" % suffix
            self.upload_To_Ftp(SYSTEM_ID, file_name)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def upload_To_Ftp(self, SYSTEM_ID, file_name):
        """
        将appium的截屏改名后按照原有的改名方式
        :param runtaskid:
        :param run_record_id:
        :param filename:
        :return:
        """
        try:
            f = XFer(gl.gl_ftp_info['FTPServer']['IP'], gl.gl_ftp_info['FTPServer']['USER'], gl.gl_ftp_info['FTPServer']['PASSWORD'], '.', int(gl.gl_ftp_info['FTPServer']['PORT']))
            f.login()
            f.upload_file_ex('./init/%s/%s' % (SYSTEM_ID, file_name), './init/%s' % SYSTEM_ID)
            print 'ftp ok'
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def update_t2_interface_detail_file(self, SYSTEM_ID, data):
        """
        AgentServer 读取对应的数据库数据，通过本函数下发到Agent，
        通过解析数据，导出为T2InterfaceDetail.xml文件
        param system_id: 系统ID
        param data: 数据信息
        return: 一个元祖（ret,msg):
            ret:0代表成功，-1代表失败
            msg：详细信息
        """
        try:
            print 'enter update_t2_interface_detail_file'
            result = OrderedDict()
            FUNCIDs = []
            for i in data.values():
                if i["FUNCID"]:
                    if i["FUNCID"] in FUNCIDs:
                        if i["INPUT_TYPE"] == 'IN':
                            result[i["FUNCID"]]["in"].append(i)
                        else:
                            result[i["FUNCID"]]["out"].append(i)
                    else:
                        FUNCIDs.append(i["FUNCID"])
                        result[i["FUNCID"]] = {'in': [], "out": [], 'attribute': i}
                        if i["INPUT_TYPE"] == 'IN':
                            result[i["FUNCID"]]["in"].append(i)
                        else:
                            result[i["FUNCID"]]["out"].append(i)
            T2InterfaceDetail_content = result
            root = etree.Element("InterfaceDetails")
            for key, content in T2InterfaceDetail_content.items():
                if not content['attribute']['INTERFACE_NAME'] or content['attribute']['INTERFACE_NAME'] == 'null':
                    content['attribute']['INTERFACE_NAME'] = ""
                if not content['attribute']['TIMEOUT'] or content['attribute']['TIMEOUT'] == 'null':
                    content['attribute']['TIMEOUT'] = ""
                if not content['attribute']['NEED_LOG'] or content['attribute']['NEED_LOG'] == 'null':
                    content['attribute']['NEED_LOG'] = ""
                if not content['attribute']['FUNCID_DESC'] or content['attribute']['FUNCID_DESC'] == 'null':
                    content['attribute']['FUNCID_DESC'] = ""
                Interface_elem = etree.SubElement(root, "Interface", funcid=str(key),
                                                  funcname=content['attribute']['INTERFACE_NAME'], returnRecord='',
                                                  englishname='', timeout=str(content["attribute"]["TIMEOUT"]),
                                                  need_log=str(content["attribute"]["NEED_LOG"]),
                                                  funcdesc=content['attribute']['FUNCID_DESC'])
                InputParams_elem = etree.SubElement(Interface_elem, "InputParams")
                OutParams_elem = etree.SubElement(Interface_elem, "OutParams")
                for i in content["in"]:
                    In_elem = etree.SubElement(InputParams_elem, "in")
                    if not i["PARAM_NAME"] or i["PARAM_NAME"] == 'null':
                        i["PARAM_NAME"] = ""
                    if not i["PARAM_DESC"] or i["PARAM_DESC"] == 'null':
                        i["PARAM_DESC"] = ""
                    if not i["PARAM_TYPE"] or i["PARAM_TYPE"] == 'null':
                        i["PARAM_TYPE"] = ""
                    In_elem.attrib["name"] = i["PARAM_NAME"]
                    In_elem.attrib["desc"] = i["PARAM_DESC"]
                    In_elem.attrib["type"] = i["PARAM_TYPE"]
                    In_elem.attrib["musttype"] = u''
                for i in content["out"]:
                    if not i["PARAM_NAME"] or i["PARAM_NAME"] == 'null':
                        i["PARAM_NAME"] = ""
                    if not i["PARAM_DESC"] or i["PARAM_DESC"] == 'null':
                        i["PARAM_DESC"] = ""
                    if not i["PARAM_TYPE"] or i["PARAM_TYPE"] == 'null':
                        i["PARAM_TYPE"] = ""
                    if not i["DISABLEFLAG"] or i["DISABLEFLAG"] == 'null':
                        i["DISABLEFLAG"] = ""
                    Out_elem = etree.SubElement(OutParams_elem, "out", name=i["PARAM_NAME"], type=i["PARAM_TYPE"],
                                                desc=i["PARAM_DESC"], musttype=u'')
                    Out_elem.attrib["name"] = i["PARAM_NAME"]
                    Out_elem.attrib["desc"] = i["PARAM_DESC"]
                    Out_elem.attrib["type"] = i["PARAM_TYPE"]
                    Out_elem.attrib["musttype"] = u''
                    Out_elem.attrib["disableflag"] = str(i["DISABLEFLAG"])
            homedir = os.getcwd()
            print '<<<<<<<创建目录'
            if not os.path.exists("%s\init\%s" % (homedir, SYSTEM_ID)):
                os.makedirs("%s\init\%s" % (homedir, SYSTEM_ID))
                print '已创建'
            print '<<<<<<<创建目录'
            path = '%s\init\%s\T2InterfaceDetails.xml' % (homedir, SYSTEM_ID)
            doc = etree.ElementTree(root)
            doc.write(path, pretty_print=True, xml_declaration=True, encoding='utf-8')
            print "T2InterfaceDetails.xml 已生成"
            file_name = "T2InterfaceDetails.xml"
            self.upload_To_Ftp(SYSTEM_ID, file_name)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def get_system_database_info(self):
        try:
            sql = "select * from sx_database_info order by system_id,db_id"
            ds = cF.executeCaseSQL(sql)
            # 先清空原来的
            self._system_db_info = OrderedDict()

            for rec in ds:
                if not self._system_db_info.has_key(rec["SYSTEM_ID"]):
                    self._system_db_info[rec["SYSTEM_ID"]] = OrderedDict()
                if not self._system_db_info[rec["SYSTEM_ID"]].has_key(rec["DB_ID"]):
                    self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]] = OrderedDict()
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["id"] = rec["DB_ID"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["ip"] = rec["DB_IP"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["port"] = rec["DB_PORT"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["dbtype"] = rec["DB_TYPE"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["username"] = rec["DB_USERNAME"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["password"] = rec["DB_PASSWORD"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["servicename"] = rec["DB_SERVICENAME"]
                self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["alias"] = rec["DB_ALIAS"]
                if not self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]].has_key("UserList"):
                    self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["UserList"] = rec["DB_SCHEMA"]
                else:
                    self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["UserList"] = \
                        self._system_db_info[rec["SYSTEM_ID"]][rec["DB_ID"]]["UserList"] + ",%s" % rec["DB_SCHEMA"]
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def rpc_get_system_db_info(self):
        """
        供Agent执行任务之前调用获取最新的系统数据库信息
        :return:
        """
        return json.dumps(self._system_db_info), json.dumps(self._system_db_table_column_disable_info)

    def run(self):
        last_time = datetime.datetime.now()
        last_task_monitor_time = datetime.datetime.now()
        try:
            while True:
                if (gl.is_exit_all_thread == True):
                    break

        except KeyboardInterrupt:
            Logging.getLog().debug("KeyboardInterrupt")
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)


def processTerm(signum, frame):
    gl.is_exit_all_thread = True


def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)
    server = MQServer()
    server.setDaemon(True)
    server.start()

    self._taskThread = task.task(self._mqserver)
    self._taskThread.setDaemon(True)
    self._taskThread.start()
    while True:
        if server.isAlive() == False:
            server.rpcserver.server_close()
            break;


if __name__ == "__main__":
    MQServer = MQServer()
    # MQServer.async_scan_db_info('ZHLC', 1)
    MQServer.run_test(
        '[{"system_id":"142891090059622AV2","pre_action":"","pro_action":"","funcid":"10211585","account_group_id":0,"serverid":0,"cmdstring":"menu_id=143002#function_id=10211585#op_password=@op_password_encr@#user_type=1#operator_no=@operator_no@#op_station=@op_station@#op_entrust_way=4#op_branch_no=@op_branch_no@#cif_account=@cif_account@","accessory_id":0,"param_id":"3399","step_id":"1","case_name":"一户通账号生成zzp","step_name":"一户通账号生成","expect_ret":0}]')
