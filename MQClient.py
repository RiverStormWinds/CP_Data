# -*- coding:gbk -*-
import sys
import json
import glob
import GlobalDict
import zhlc
import commFuncs as cF
import commFuncs_kcbp as cF_kcbp

import threading
import gl
import signal
import os
from ftpClient import XFer
# from executionEngine import executionEngine
import executionEngine
import time
import datetime
import shutil
from gl import GlobalLogging as Logging
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy
import functools
from collections import OrderedDict
import hradapter
# from bizmod import exec_sql
import uuid
import copy

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import cx_Oracle
import pyodbc
import subprocess
import pika
import redis_client
import huarui_dys


def async(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        # my_thread.setDaemon(True)
        my_thread.start()
        # my_thread.join()

    return wrapper


class MQClient(threading.Thread):
    """MessageClient"""

    def __init__(self, setting):
        self._setting = setting
        GlobalDict.set_value("MQClient", self)
        if self._setting.has_key('CMD_SPLX_SILKTEST'):
            cmd_str = self._setting['CMD_SPLX_SILKTEST']
            if cmd_str:
                gl.CMD_SPLX_SILKTEST = cmd_str
        self._agent_id = setting["AgentID"]
        print "_agent_id = %s" % self._agent_id
        self._registered = False
        self.mq_connect_closed = False
        self.corr_id = None
        # agent的状态，默认为注册状态,'STATE_REGISTER','STATE_UPDATE','STATE_RUNNING','STATE_FREE','STATE_UNKNOWN'
        self._client_state = gl.CLIENT_STATE_REGISTER
        self._server = 0
        # 最近一次执行的任务编号，用来区分一个新任务的开始
        # 对于接口类的测试任务，可以使用这个来判断一个新任务的开始，去做一些初始化动作
        self._last_task_id = -1
        self._request_timeout = 3000
        self._retries_left = 10  # 最大重连10次
        threading.Thread.__init__(self)
        self._executionEngine = executionEngine.executionEngine(self)
        # 启用RPC
        self.rpcserver = SimpleXMLRPCServer(('', int(self._setting["AgentInfo"]["PORT"])))
        self.rpcserver.register_function(self.database_operation)
        # 需要成为RPC函数的，在这里列出
        # self.rpcserver.register_function(self.processCaseDistribution)
        # self.rpcserver.register_function(self.processEnvInit)
        # self.rpcserver.register_function(self.processScriptUpdate)
        # self.rpcserver.register_function(self.UpdateSystemDBInfo)
        self.rpcserver.register_function(self.fast_database_operation)
        self.rpcserver.register_function(self.run_test)
        self.rpcserver.register_function(self.pre_action_func)
        self._rpc_thread = threading.Thread(target=self.rpc_thread)
        self._rpc_thread.start()
        self._system_account_group = json.loads(open("account_setting.json", "r").read())
        self._server_proxy = ServerProxy("http://%s:%s" % (self._setting["AgentServer"]["IP"],
                                                           self._setting["AgentServer"]["PORT"]))
        # fixme
        gl.g_server_proxy = self._server_proxy
        self._system_db_info = OrderedDict()  # 系统数据库信息，从AgentServer下发
        self._system_db_table_column_disable_info = OrderedDict()  # 系统数据库、表，字段的disableflag信息，从AgentServer下发
        self._appium_path = ""
        self._appium_is_started = False
        # if os.path.exists("settings.json"):
        #     _setting = json.loads(open("settings.json", "r").read())
        #     if "APPIUM_PATH" in _setting.keys():
        #         self._appium_path = _setting["APPIUM_PATH"]
        if "APPIUM_PATH" in self._setting.keys():
            self._appium_path = self._setting["APPIUM_PATH"]
        self.rpc_channel = None
        self._rpc_connection = None
        self.create_mq()

    def close_all(self):
        self.rpcserver.server_close()
        if not self.rpc_channel is None:
            try:
                self.rpc_channel.close()
            except BaseException as e:
                print e
            time.sleep(1)
            self.rpc_channel = None
        try:
            if not (self._rpc_connection is None):
                self._rpc_connection.close()
                self._rpc_connection = None
                time.sleep(1)
        except BaseException as e:
            print e
            pass
        self._redis_client = None

    def create_mq(self):
        # 连接到RabbitMQ
        credentials = pika.PlainCredentials(self._setting["RabbitMQServer"]["USER"],
                                            self._setting["RabbitMQServer"]["PWD"])
        self._rpc_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self._setting["RabbitMQServer"]["IP"], credentials=credentials, heartbeat=0))
        if self._rpc_connection is None:
            Logging.getLog().error("_rpc_connection is None")
            return

        self.rpc_channel = self._rpc_connection.channel()

        result = self.rpc_channel.queue_declare(queue="rpc_queue_callback_%s" % self._agent_id, exclusive=False)
        self.callback_queue = result.method.queue

        self.rpc_channel.basic_consume(self.on_response, no_ack=True,
                                       queue=self.callback_queue)

        self.result_dict = {}  # 记录RPC结果
        self._channel_dict = {}  ##该客户端需要读取的队列列表 {queue_name:channel}
        self._task_queue_dict = OrderedDict()  # 保存任务号和queue的对应关系 {task_id:{"queue_name":queue_name, "state":""}}

        self._redis_client = redis_client.RedisClient(self._setting["RedisServer"]["IP"],
                                                      self._setting["RedisServer"]["PORT"])

        self.rebuild_task_info()

    def pre_action_func(self, rabbit_test):  # 测试用方法，统一执行前置
        print 'rabbit_test --> ', rabbit_test
        try:
            for i in rabbit_test:
                system_id = i['system_id']
                account_group_id = i['account_group_id']
                pres = i['pre_action']
                cmdstring = i['cmdstring']
                funcid = i['funcid']
                step = i['step']  # 案例步骤
                step_name = i['step_name']
                case_name = i['case_name']
                run_record_id = i['run_record_id']
                homedir = os.getcwd()
                system_id = system_id.upper()
                suffix = cF.get_suffix(system_id)
                if os.path.exists("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix)):
                    os.remove("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix))
                try:  # fixme
                    f = XFer(self._setting['FTPServer']['IP'], gl.gl_ftp_info['FTPServer']['USER'],
                             gl.gl_ftp_info['FTPServer']['PASSWORD'], '.',
                             int(self._setting['FTPServer']['PORT']))
                    f.login()
                    homedir = os.getcwd()
                    system_id = system_id.upper()
                    f.download_files(r'%s\init\%s' % (homedir, system_id), r'.\init\%s' % system_id)
                except Exception, ex:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
                    return -1, u"前置提前执行异常"
                cF.readSystemConfigFile(system_id)
                cF.add_tnsnames_info()
                group_variable_dict = {}
                pres = cF.GlobalParameterReplace(pres, account_group_id)
                pres = cF.GroupParameterReplace(pres, group_variable_dict)
                cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                ret, msg_info = cF.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                  account_group_id)
                if ret != 0:
                    testResult = {}
                    Logging.getLog().critical("测试数据%s 前置动作提前执行失败！%s" % (step, str(msg_info)))
                    testResult["result"] = "STATE_FAIL"
                    testResult["step"] = step
                    testResult["case_name"] = case_name
                    testResult["funcid"] = funcid
                    testResult["msg"] = u"批量执行前置时，此步骤前置动作执行失败!!!%s" % str(msg_info)
                    testResult["log"] = u"步骤前置动作执行失败！%s" % str(msg_info)
                    testResult["cmdstring"] = cmdstring
                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    testResult['run_record_id'] = run_record_id
                    testResult['step_name'] = step_name
                    return -1, testResult
            return 0, u"前置已经提前执行成功"
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, u"前置提前执行异常"

    def rebuild_task_info(self):
        """
        Agent重启的时候，根据Redis信息重建通道和任务信息
        :return:
        """
        rebuild_task_info = self._redis_client.rebuild_task_info(self._agent_id)
        if rebuild_task_info:
            for task_id in rebuild_task_info:
                agent_list = rebuild_task_info[task_id]["agent_list"]
                agent_list.sort()
                queue_name = "task_distribute_queue[%s]" % ",".join(agent_list)

                task_queue_info = {}
                task_queue_info["queue_name"] = queue_name
                task_queue_info["env_init_state"] = ""
                task_queue_info["cancel_flag"] = rebuild_task_info[task_id]["cancel_flag"]

                self._task_queue_dict[task_id] = task_queue_info

                if queue_name not in self._channel_dict.keys():
                    channel = self._rpc_connection.channel()
                    self._channel_dict[queue_name] = channel
                    channel.queue_declare(queue=queue_name)
                Logging.getLog().debug("rebuild task info id=%s" % str(task_id))

    def get_agent_id(self):
        return self._agent_id

    def register_client(self):
        """
        注册客户端
        :return:
        """
        try:
            Logging.getLog().debug("ready to register... waiting for response.")
            func_body = OrderedDict()
            func_body["func"] = "register_client"

            func_body["func_param"] = [self._agent_id, self._setting["AgentInfo"]["IP"],
                                       self._setting["AgentInfo"]["PORT"]]

            ret, msg = self.call_server_rpc(func_body)
            if ret < 0:
                Logging.getLog().error(msg)
                return -1, msg

            new_queue_name = "cmd_queue_%s" % self._agent_id
            if new_queue_name not in self._channel_dict.keys():
                channel = self._rpc_connection.channel()
                channel.queue_declare(queue=new_queue_name)
                self._channel_dict[new_queue_name] = channel

            # 启动一个线程去拉命令队列
            # self.listen_cmd_queue_thread()
            # self._cmd_thread = threading.Thread(target=self.listen_cmd_queue_thread)
            # self._cmd_thread.start()
            # 启动一个线程去侦听任务队列
            self._task_thread = threading.Thread(target=self.listen_task_queue)
            self._task_thread.start()

            return 0, ""
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, ""

    def on_response(self, ch, method, props, body):
        if props.correlation_id in self.result_dict.keys():
            self.result_dict[props.correlation_id] = body
            Logging.getLog().debug("get response corr_id = %s" % props.correlation_id)
        else:
            Logging.getLog().error("get an unknown corr_id = %s" % props.correlation_id)

    def read_cmd_queue_info(self):
        """
        
        :return:
        :   ret ：返回状态0 成功 -1 失败
        ：   count：队列中剩余的消息数量（处理后），失败时为错误信息
        """
        cmd_queue_name = "cmd_queue_%s" % self._agent_id
        cmd_channel = self._channel_dict[cmd_queue_name]
        # print " read_cmd_queue_info gl.is_exit_all_thread :%s" % gl.is_exit_all_thread
        method_frame, header_frame, body = cmd_channel.basic_get(cmd_queue_name)
        if method_frame:
            try:
                msg_dict = json.loads(body)
                Logging.getLog().debug(" [x] Received %s" % msg_dict["msg_desc"])
                msg_id = msg_dict["msg_id"]
                if msg_id == gl.PUBLIC_NEW_TASK_ID:
                    self.process_new_task_msg(msg_dict)

                elif msg_id == gl.CANCEL_A_TASK_ID:
                    task_id = str(msg_dict["msg_body"]["task_id"])
                    if task_id in self._task_queue_dict.keys():
                        self._task_queue_dict[task_id]["cancel_flag"] = 1
                        Logging.getLog().debug("cancel %d task" % int(task_id))
                    else:
                        Logging.getLog().debug("cancel %d task couldn't find" % int(task_id))

                elif msg_id == gl.UPDATE_SCRIPT_MSG_ID:
                    ret, msg = self.ProcessScriptUpdateMsg()
                    if ret < 0:
                        Logging.getLog().error(msg)
                    else:
                        Logging.getLog().debug("ScriptUpdate Finish")
                    self._client_state = gl.CLIENT_STATE_FREE
                cmd_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                return 0, method_frame.message_count - 1

            except:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().error(exc_info)
                return -1, exc_info

        return 0, 0

    # def cmd_queue_callback(self, ch, method, properties, body):
    #     """
    #     命令队列的回调函数
    #     这个里面可以慢慢的一个一个消化消息
    #     :param ch:
    #     :param method:
    #     :param properties:
    #     :param body:
    #     :return:
    #     """
    #     try:
    #         msg_dict = json.loads(body)
    #
    #         Logging.getLog().debug(" [x] Received %s" % msg_dict["msg_desc"])
    #         # Logging.getLog().debug("acquire Lock")
    #         self.check_sync_lock(release=False)
    #
    #         msg_id = msg_dict["msg_id"]
    #         # if msg_id == gl.CASE_DISTRIBUTE_MSG_ID:
    #         #     self.processCaseDistribution(msg_dict)
    #         if msg_id == gl.PUBLIC_NEW_TASK_ID:
    #             self.process_new_task_msg(msg_dict)
    #         # elif msg_id == gl.INIT_ENV_MSG_ID:
    #         #     self.processEnvInit(msg_dict)
    #         elif msg_id == gl.CANCEL_A_TASK_ID:
    #             task_id = str(msg_dict["msg_body"]["task_id"])
    #             self._task_queue_dict[task_id]["cancel_flag"] = 1
    #             Logging.getLog().debug("cancel %d task" % int(task_id))
    #         elif msg_id == gl.UPDATE_SCRIPT_MSG_ID:
    #             ret, msg = self.ProcessScriptUpdateMsg()
    #             if ret < 0:
    #                 Logging.getLog().error(msg)
    #             else:
    #                 Logging.getLog().debug("ScriptUpdate Finish")
    #             self._client_state = gl.CLIENT_STATE_FREE
    #
    #         ch.basic_ack(delivery_tag=method.delivery_tag)
    #         # Logging.getLog().debug("release Lock")
    #         self.check_sync_lock(release=True)
    #         return 0, ""
    #     except Exception, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         # TODO 增加错误返回码
    #         ch.basic_ack(delivery_tag=method.delivery_tag)
    #         # Logging.getLog().debug("release Lock")
    #         self.check_sync_lock(release=True)
    #         return -1, exc_info
    #
    # @async
    # def listen_cmd_queue_thread(self):
    #     credentials = pika.PlainCredentials(self._setting["RabbitMQServer"]["USER"], self._setting["RabbitMQServer"]["PWD"])
    #     self._cmd_connection = pika.BlockingConnection(pika.ConnectionParameters(
    #         host=self._setting["RabbitMQServer"]["IP"], credentials=credentials, heartbeat=0))
    #
    #     new_queue_name = "cmd_queue_%s" % self._agent_id
    #     if new_queue_name not in self._channel_dict.keys():
    #         channel = self._cmd_connection.channel()
    #         channel.queue_declare(queue=new_queue_name)
    #         self._channel_dict[new_queue_name] = channel
    #
    #     channel = self._channel_dict[new_queue_name]
    #     channel.basic_qos(prefetch_count=1)
    #     channel.basic_consume(self.cmd_queue_callback,
    #                           queue=new_queue_name)
    #     # thread = threading.current_thread()
    #     # print "curr thread is %s" % thread.getName()
    #     channel.start_consuming()

    @async
    def listen_task_queue(self):
        """


        每个任务都有一个环境初始化，需要等环境初始化完成后，才能执行用例.

        在实际的调试过程中，发现因为队列下发比较慢，导致读到空队列的情况，
        所以当读到空时，给与适当的延迟，才能断定任务确实执行完毕了
        :param channel: 这里的channel是命令队列
        :param queue_name:
        :return:
        """
        # 当队列中存在多个消息的时候，可以不休息，以增加性能。
        # 优先处理命令队列里的消息

        msg_count_dict = {}

        thread = threading.current_thread()

        max_allow_read_nothing_count = 20  # 最大允许读到空的次数

        print "listen_task_queue curr thread is %s" % thread.getName()

        cmd_queue_name = "cmd_queue_%s" % self._agent_id

        ack_flag = False  # 用来控制异常状态下的消息确认
        # print "gl.is_exit_all_thread :%s"%gl.is_exit_all_thread
        while gl.is_exit_all_thread != True:
            try:

                ## 尝试优先读取命令队列的信息
                task_list = self._task_queue_dict.keys()
                if task_list != []:
                    task_list.sort()  # 从最小的开始处理
                    curr_task_id = task_list[0]

                    task_queue_name = self._task_queue_dict[curr_task_id]["queue_name"]
                    env_init_state = self._task_queue_dict[curr_task_id]["env_init_state"]
                    cancel_flag = self._task_queue_dict[curr_task_id]["cancel_flag"]

                    # 环境必须初始化成功以后才能进行用例的执行

                    task_channel = self._channel_dict[task_queue_name]

                    # 上次读取的时候，队列中还有多少个消息
                    if msg_count_dict.get(task_queue_name, 0) == 0 and msg_count_dict.get(cmd_queue_name, 0) == 0:
                        time.sleep(1)

                    ret, left_count = self.read_cmd_queue_info()
                    if ret < 0:
                        continue
                    else:
                        msg_count_dict[cmd_queue_name] = left_count

                    method_frame, header_frame, body = task_channel.basic_get(task_queue_name)
                    if method_frame:
                        try:
                            ack_flag = False
                            max_allow_read_nothing_count = 20  # 恢复初始值

                            # self.check_sync_lock(False)

                            msg_count_dict[task_queue_name] = method_frame.message_count - 1
                            # 判断这个消息所属的任务是否和当前需要执行的任务一致，一致就处理，不一致就先退回，按照任务顺序来执行其他任务
                            msg_dict = OrderedDict()
                            try:
                                msg_dict = json.loads(body)
                            except BaseException, ex:
                                exc_info = cF.getExceptionInfo()
                                Logging.getLog().critical(exc_info)
                                Logging.getLog().error(body)
                                task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
                                ack_flag = True
                                continue

                            if msg_dict["msg_id"] == gl.CASE_DISTRIBUTE_MSG_ID:  # 用例下发消息

                                run_task_id = str(msg_dict["msg_body"]["runTaskid"])
                                serial_no = msg_dict["msg_serialno"]

                                if run_task_id == curr_task_id:
                                    if cancel_flag == 1:  # 该任务取消了
                                        self._task_queue_dict.pop(curr_task_id)
                                        Logging.getLog().debug(
                                            "reject(cancel) a msg for queue:%s no=%s" % (task_queue_name, serial_no))
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
                                        ack_flag = True
                                        # self.check_sync_lock(True)
                                        continue

                                    if env_init_state == "" or env_init_state == "STATE_UNINIT":
                                        # 读取状态
                                        ret, state = self._redis_client.read_task_env_init_state(curr_task_id)
                                        if ret == 0:
                                            self._task_queue_dict[curr_task_id]["env_init_state"] = state
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag)
                                        ack_flag = True
                                        time.sleep(1)
                                        # self.check_sync_lock(True)
                                        continue
                                    elif env_init_state == "STATE_FAIL":
                                        Logging.getLog().error(
                                            "task %s env fail, waiting for task cancel" % str(curr_task_id))
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag)
                                        ack_flag = True
                                        time.sleep(1)
                                        # self.check_sync_lock(True)
                                        continue

                                    # 运行用例
                                    self._client_state = gl.CLIENT_STATE_RUNNING
                                    if "server_ids" not in msg_dict.keys():
                                        msg_dict['server_ids'] = ""
                                    server_ids = msg_dict['server_ids']
                                    if server_ids:
                                        if gl.g_thread_flag == 0:
                                            gl.g_thread_flag = 1
                                            self.distributed_task(msg_dict, server_ids)
                                            # self._executionEngine.return_case_result_msg()
                                            while True:
                                                if gl.g_thread_flag == 0:
                                                    break
                                            system_sleep_times = gl.g_cases_sleep_time
                                            time.sleep(system_sleep_times)

                                            self._client_state = gl.CLIENT_STATE_FREE

                                            Logging.getLog().debug(
                                                "ack a msg for queue:%s no=%s" % (task_queue_name, serial_no))
                                            task_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                                            ack_flag = True
                                            # gl.g_thread_flag = 0
                                    else:
                                        msg_dict['server_ids'] = ""
                                        ret, msg = self._executionEngine.processCaseDistrubtionMsg(msg_dict)
                                        system_sleep_times = gl.g_cases_sleep_time
                                        time.sleep(system_sleep_times)
                                        self._client_state = gl.CLIENT_STATE_FREE

                                        Logging.getLog().debug(
                                            "ack a msg for queue:%s no=%s" % (task_queue_name, serial_no))
                                        task_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                                        ack_flag = True

                                else:
                                    # 已经读到了其他任务了，暂时放弃
                                    if run_task_id > curr_task_id:
                                        self._task_queue_dict.pop(curr_task_id)
                                    if run_task_id not in self._task_queue_dict.keys():
                                        Logging.getLog().debug(
                                            "queue:%s read another task (curr:%s,read:%s), seems curr task finished.remove this task from TaskAgent and reject this message no=%s" % (
                                                task_queue_name, str(curr_task_id), str(run_task_id), serial_no))
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)

                                    else:
                                        Logging.getLog().debug(
                                            "queue:%s read another task (curr:%s,read:%s), seems curr task finished.remove this task from TaskAgent and return this message no=%s" % (
                                                task_queue_name, str(curr_task_id), str(run_task_id), serial_no))

                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag)
                            elif msg_dict["msg_id"] == gl.INIT_ENV_MSG_ID:
                                run_task_id = msg_dict["msg_body"]["task_id"]
                                serial_no = msg_dict["msg_serialno"]
                                if run_task_id == curr_task_id:
                                    if cancel_flag == 1:  # 该任务取消了
                                        Logging.getLog().debug(
                                            "reject(cancel) a INIT_ENV_MSG_ID msg for queue:%s no=%s" % (
                                                task_queue_name, serial_no))
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
                                        ack_flag = True
                                        # self.check_sync_lock(True)
                                        continue

                                    # now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    # self._redis_client.modify_task_info(run_task_id, run_start_time=now)
                                    ret, msg = self.processEnvInitMsg(msg_dict)
                                    if msg == 'STATE_PASS':
                                        self._redis_client.send_env_init_result_back_to_redis(self._agent_id,
                                                                                              run_task_id,
                                                                                              result='STATE_PASS')
                                    else:
                                        self._redis_client.send_env_init_result_back_to_redis(self._agent_id,
                                                                                              run_task_id,
                                                                                              result='STATE_FAIL')

                                    task_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                                    ack_flag = True
                                else:
                                    if run_task_id not in self._task_queue_dict.keys():
                                        Logging.getLog().debug(
                                            "queue:%s read another task (curr:%s,read:%s), seems curr task finished.remove this task from TaskAgent and reject this message no=%s" % (
                                                task_queue_name, str(curr_task_id), str(run_task_id), serial_no))
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
                                        ack_flag = True
                                    else:
                                        Logging.getLog().debug(
                                            "queue:%s read another task (curr:%s,read:%s), seems curr task finished.remove this task from TaskAgent and return this message no=%s" % (
                                                task_queue_name, str(curr_task_id), str(run_task_id), serial_no))
                                        self._task_queue_dict.pop(curr_task_id)
                                        task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=True)
                                        ack_flag = True

                                        # self.check_sync_lock(True)
                        except:
                            exc_info = cF.getExceptionInfo()
                            Logging.getLog().critical("task_channel process message exception %s" % exc_info)
                            if ack_flag == False:
                                task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)

                    else:

                        if max_allow_read_nothing_count > 0:
                            # 因为任务是一次性下发到队列的，所以如果该队列为空，可以认为该任务已经处理完毕了
                            Logging.getLog().debug(
                                "queue:%s read nothing, seems this task finished.just hold on" % task_queue_name)
                            time.sleep(1)
                            max_allow_read_nothing_count = max_allow_read_nothing_count - 1

                        else:
                            self._task_queue_dict.pop(curr_task_id)
                            if curr_task_id:
                                curr_task_id = ''
                            Logging.getLog().debug(
                                "queue:%s read nothing, seems this task finished.remove this task from TaskAgent" % task_queue_name)
                            max_allow_read_nothing_count = 20


                else:
                    ret, left_count = self.read_cmd_queue_info()
                    if ret < 0:
                        continue
                    else:
                        msg_count_dict[cmd_queue_name] = left_count
                        if left_count > 0:
                            continue
                    time.sleep(1)
            except:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().critical(exc_info)

                self.mq_connect_closed = True
                break

    # def check_sync_lock(self, release=False):
    #     if release == False:
    #         gl.g_sync_Lock.acquire()
    #     else:
    #         gl.g_sync_Lock.release()
    # self._heartbeat_thread = threading.Thread(target=self.SendHeartBeatMessage)
    # self._heartbeat_thread.start()
    def distributed_task(self, msg_dict, server_ids):
        try:
            gl.execute_many_row = {}
            gl.g_server_ids = []
            gl.all_core = {}
            system_id = msg_dict["msg_body"]["system_id"]
            thread_list = []
            server_ids = server_ids.split(",")
            if "create_account" in str(msg_dict):
                server_ids = server_ids[0]
            gl.server_result_info = {"testResultList": []}
            for server_id in server_ids:
                gl.all_core[str(server_id)] = 0
            for server_id in server_ids:  # 将即将运行的线程放入线程列表中
                gl.g_server_id = server_id
                gl.g_server_ids.append(server_id)
                cF.readSystemConfigFile(system_id)
                new_msg_dict = copy.deepcopy(msg_dict)
                new_msg_dict["server_ids"] = server_id
                t = threading.Thread(target=self._executionEngine.processCaseDistrubtionMsg, args=(new_msg_dict,))
                thread_list.append(t)
                # t.start()
            #while not gl.threadQueueTask.empty():  # 清空队列
            #gl.threadQueueTask.get()
            for t in thread_list:
                t.setDaemon(True)
                t.start()  # 启动线程
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, ""

    def call_server_rpc(self, func_body_dict):
        try:
            self.corr_id = str(uuid.uuid4())
            self.result_dict[self.corr_id] = None

            Logging.getLog().debug("call_server_rpc %s, %s" % (self.callback_queue, str(self.corr_id)))

            self.rpc_channel.basic_publish(exchange='',
                                           routing_key='server_rpc_queue',
                                           properties=pika.BasicProperties(
                                               reply_to=self.callback_queue,
                                               correlation_id=self.corr_id,
                                           ),
                                           body=json.dumps(func_body_dict, ensure_ascii=False))
            try:
                now_time = datetime.datetime.now()
                while self.result_dict[self.corr_id] is None and gl.is_exit_all_thread == False:
                    self._rpc_connection.process_data_events()
                    if (datetime.datetime.now() - now_time).seconds > 5:
                        break
                if gl.is_exit_all_thread == True:
                    Logging.getLog().debug("exit call_server_rpc")
                    return -1, "exit call_server_rpc"
                else:
                    ret = self.result_dict[self.corr_id]
                    self.result_dict.pop(self.corr_id)
                    Logging.getLog().debug("call %s return %s" % (func_body_dict["func"], ret))
                    return 0, ret
            except KeyboardInterrupt:
                Logging.getLog().debug("get KeyboardInterrupt")
                return -1, "KeyboardInterrupt"
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, ""

    def process_new_task_msg(self, msg_dict):
        """
        看队列是否已经创建，否则创建channel和queue
        :param msg_dict:
        :return:
        """
        try:
            task_id = str(msg_dict["msg_body"]["task_id"])
            queue_name = msg_dict["msg_body"]["queue_name"]
            if queue_name not in self._channel_dict.keys():
                Logging.getLog().debug(u"开启队列%s" % queue_name)
                channel = self._rpc_connection.channel()
                self._channel_dict[queue_name] = channel
                channel.queue_declare(queue=queue_name)
            task_info = {}
            task_info["queue_name"] = queue_name
            task_info["env_init_state"] = ""
            task_info["cancel_flag"] = 0
            self._task_queue_dict[task_id] = task_info
            # self._task_queue_dict[task_id] = queue_name
            # self._task_queue_dict.setdefault(task_id, {}).setdefault("queue_name", queue_name).setdefault("state", "")
            return 0, ""
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def fast_database_operation(self, params):
        """ params:
                {
                     "sql":"sql",#sql
                     "database_login_info":
                     {
                          "oracle":
                                    {
                                       "ip":"ip",
                                       "db_port":"db_port",
                                       "servicename":"servicename",
                                       "username":"username", #用户名
                                       "password":"password",#密码
                                       "db_alias":"db_alias"#数据库别名
                                    },
                          "sqlserver":
                                   {
                                       "ip":"ip,port", #ip地址
                                       "database":"database",#数据库
                                       "username":"username"#用户名
                                       "password":"password"#密码
                                    }
                     }
                     "type":"type" #数据库类型  oracle, sqlserver
                  }
        """
        try:
            Logging.getLog().debug(u'database_operation---params:%s' % str(params))
            params = eval(params)
            sql = params["sql"]
            if not sql:
                return -1, u"sql为空,请输入正确的sql!"
            database_login_info = params["database_login_info"]
            type = params["type"]
            if not type:
                return -1, u"数据库类型为空,请输入正确的数据库类型!"
            else:
                if type not in ["oracle", "sqlserver"]:
                    return -1, u"请输入正确的数据库类型, 暂支持oracle,sqlserver!"
            if type == "oracle":
                # 更新oracle信息
                gl.g_connectOracleSetting["0"] = {
                    "DB_ALIAS": database_login_info["oracle"]["db_alias"],
                    "ServiceName": database_login_info["oracle"]["servicename"],
                    "IP": database_login_info["oracle"]["ip"],
                    "DB_PORT": database_login_info["oracle"]["db_port"]}
                cF.add_tnsnames_info()
                ret, result = cF.exeRunSQLOracle(sql, database_login_info["oracle"])
                Logging.getLog().debug("result : %s" % json.dumps(result, encoding='gbk'))
                if ret != 0:
                    return -1, u"sql执行失败, 请检查sql、数据库应用类型和测试环境是否输入正确!error_info:%s" % result
                return 0, json.dumps(result, encoding='gbk')

            if type == "sqlserver":
                ret, result = cF.exeRunSqlserver(sql, database_login_info["sqlserver"])
                Logging.getLog().debug("result : %s" % json.dumps(result, encoding='gbk'))
                if ret != 0:
                    return -1, u"sql执行失败, 请检查sql、数据库应用类型和测试环境是否输入正确!  error_info:%s" % result
                return 0, json.dumps(result, encoding='gbk')
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def database_operation(self, params):  # system_id, servertype, sql
        """ params:
                {
                     "system_id":"system_id",
                     "servertype":"servertype",
                     "sql":"sql",
                     "adapter_type":"adapter_type",
                     "serverid":"serverid"
                  }
        """
        try:
            Logging.getLog().debug(u'database_operation---params:%s' % str(params))
            params = eval(params)
            servertype = params["servertype"].strip()
            system_id = params["system_id"].strip()
            sql = u"%s" % params["sql"].strip()
            adapter_type = params["adapter_type"].strip()
            serverid = params["serverid"].strip()
            Logging.getLog().debug("system_id:%s " % system_id)
            Logging.getLog().debug("servertype:%s " % servertype)
            Logging.getLog().debug("sql:%s " % sql)
            Logging.getLog().debug("adapter_type:%s " % adapter_type)
            Logging.getLog().debug("serverid:%s " % serverid)
            homedir = os.getcwd()
            system_id = str(system_id).upper()
            if not os.path.exists("%s\init\%s" % (homedir, system_id)):
                os.makedirs("%s\init\%s" % (homedir, system_id))
                print '已创建 %s文件夹' % system_id
            suffix = cF.get_suffix(system_id)
            # 删除原有账户组信息
            if os.path.exists("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix)):
                os.remove("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix))

            if adapter_type == 'SPLX_KCBP':
                gl.g_server_id = serverid
                if os.path.exists("%s\init\%s\ZHLCAutoTestSetting_%s" % (homedir, system_id, serverid)):
                    os.remove("%s\init\%s\ZHLCAutoTestSetting_%s" % (homedir, system_id, serverid))
            else:
                if os.path.exists("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id)):
                    os.remove("%s\init\%s\%s" % (homedir, system_id, 'ZHLCAutoTestSetting.xml'))

            # 下载对应系统下的文件
            f = XFer(self._setting['FTPServer']['IP'], gl.gl_ftp_info['FTPServer']['USER'],
                     gl.gl_ftp_info['FTPServer']['PASSWORD'], '.',
                     int(self._setting['FTPServer']['PORT']))
            f.login()
            homedir = os.getcwd()
            system_id = str(system_id).upper()
            f.download_files(r'%s\init\%s' % (homedir, system_id), r'.\init\%s' % system_id)
            Logging.getLog().debug(u'>>>>>>>>下载:' + u'%s\init\%s 路径下的配置文件' % (homedir, system_id))

            # 读取最新的配置文件
            cF.readSystemConfigFile(system_id)
            # 更新oracle信息
            cF.add_tnsnames_info()

            if serverid == "" or serverid == None or serverid == "null":
                serverid = cF.get_core(servertype)
            print "serverid:%s" % serverid
            if serverid != -1:
                zero_flag = False
                if "zero" in sql:
                    sql = sql.replace("zero", "").strip()
                    zero_flag = True
                result = cF.executeRunSQL(sql, serverid)
                if not result and zero_flag == True:
                    if "SELECT" in sql.upper() and "FROM" in sql.upper():
                        sql1 = sql.upper()
                        index1 = sql1.find("FROM")
                        index2 = sql1.find("SELECT")
                        field = sql1[index2 + 6:index1].strip()
                        if "as" in field.lower():
                            field = field.lower().split("as")[1].strip()
                        else:
                            field = field.lower().replace("max(", "").replace(")", "")
                        result = [{field: "0"}]
                Logging.getLog().debug("result : %s" % json.dumps(result, encoding='gbk'))
                if result == -1:
                    return -1, u"sql执行失败, 请检查sql、数据库应用类型和测试环境是否输入正确!"
                return 0, json.dumps(result, encoding='gbk')
            else:
                ret, result = cF.executeRunSQL_oracle(sql, servertype)
                Logging.getLog().debug("result : %s" % json.dumps(result, encoding='gbk'))
                if ret != 0:
                    return -1, u"sql执行失败, 请检查sql、数据库应用类型和测试环境是否输入正确!"
                return 0, json.dumps(result, encoding='gbk')
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def rpc_thread(self):
        while (gl.is_exit_all_thread != True):
            print("handle_request")
            self.rpcserver.handle_request()
        Logging.getLog().debug("Exit rpc thread")

    # def processCaseDistribution(self, msg_info):
    #     try:
    #         json_msg = json.loads(msg_info)
    #         self._client_state = gl.CLIENT_STATE_RUNNING
    #         self.asyCaseDistribution(json_msg)
    #         return 0, ""
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         return -1, exc_info
    #
    #
    # def asyCaseDistribution(self, json_msg):
    #     try:
    #         ret, msg = self._executionEngine.processCaseDistrubtionMsg(json_msg)
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         if ret < 0:
    #             Logging.getLog().error(msg)
    #         return ret, msg
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         return -1, exc_info

    # def processEnvInit(self, msg_info):
    #     self._client_state = gl.CLIENT_STATE_RUNNING
    #     ret, msg = self.processEnvInitMsg(msg_info)
    #     self._client_state = gl.CLIENT_STATE_FREE
    #     return ret, msg

    # # @async
    # def asyEnvInit(self, json_msg):
    #     try:
    #         ret, msg = self.processEnvInitMsg(json_msg)
    #         if ret < 0:
    #             Logging.getLog().error(msg)
    #         else:
    #             Logging.getLog().debug("processEnvInitMsg finished")
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         return ret, msg
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         return -1, 'STATE_FAIL'

    def paremReplace(self, cmdstring, dync_dict, system_id, account_group_id):
        """

        :param dync_dict:
        :return:
        """
        if not dync_dict.has_key(system_id):
            return cmdstring
        if not dync_dict[system_id].has_key(str(account_group_id)):
            return cmdstring
        for key in dync_dict[system_id][str(account_group_id)].keys():
            cmdstring = cmdstring.replace("@%s@" % key, dync_dict[system_id][str(account_group_id)][key])
        return cmdstring

    # def processScriptUpdate(self, msg_info):
    #     try:
    #         self._client_state = gl.CLIENT_STATE_UPDATE
    #         # json_msg = json.loads(msg_info)
    #         # message.pub(gl.MSG_PROCESS_ENV_INIT,msg_info) #发起一个消息去执行用例
    #         self.asyScriptUpdate()
    #         return 0, ""
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         return -1, exc_info
    #
    # @async
    # def asyScriptUpdate(self):
    #     try:
    #         ret, msg = self.ProcessScriptUpdateMsg()
    #         if ret < 0:
    #             Logging.getLog().error(msg)
    #         else:
    #             Logging.getLog().debug("ScriptUpdate Finish")
    #         self._client_state = gl.CLIENT_STATE_FREE
    #
    #         retry_count = 0
    #         while (gl.is_exit_all_thread == False):
    #             try:
    #                 gl.g_rpc_Lock.acquire()
    #                 ret, msg = self._server_proxy.tell_script_update_result(self._agent_id)
    #                 gl.g_rpc_Lock.release()
    #                 if ret < 0:
    #                     Logging.getLog().error("tell_script_update_result fail, msg=%s" % (msg))
    #                 else:
    #                     Logging.getLog().debug("tell_script_update_result successful")
    #                 break
    #             except BaseException, ex:
    #                 gl.g_rpc_Lock.release()
    #                 Logging.getLog().critical(
    #                     "tell_script_update_result exception retry_count=%d ex=%s" % (retry_count, ex))
    #                 retry_count = retry_count + 1
    #                 time.sleep(3)
    #                 continue
    #
    #         return ret, msg
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         self._client_state = gl.CLIENT_STATE_FREE
    #         retry_count = 0
    #         while (gl.is_exit_all_thread == False):
    #             try:
    #                 ret, msg = self._server_proxy.tell_script_update_result(self._agent_id)
    #                 if ret < 0:
    #                     Logging.getLog().error("tell_script_update_result fail, msg=%s" % (msg))
    #                 else:
    #                     Logging.getLog().debug("tell_script_update_result successful")
    #                 break
    #             except BaseException, ex:
    #                 Logging.getLog().critical(
    #                     "tell_script_update_result exception retry_count=%d ex=%s" % (retry_count, ex))
    #                 retry_count = retry_count + 1
    #                 time.sleep(3)
    #                 continue
    #
    #         return -1, exc_info

    def SendHeartBeatMessage(self):
        while (gl.is_exit_all_thread != True and not self._redis_client is None):
            try:
                last_alive = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # print "self._client_state %s"%self._client_state
                if gl.case_state:
                    self._client_state = "STATE_RUNNING"
                self._redis_client.set_heartbeat_info(self._agent_id, self._client_state, last_alive)
                # Logging.getLog().debug("client_heart_beat(%s,%s)" %(self._agent_id,self._client_state))
                # Logging.getLog().debug("1")
                # gl.g_rpc_Lock.acquire()
                # Logging.getLog().debug("2")
                # ret, msg = self._server_proxy.client_heart_beat(self._agent_id, self._client_state)
                # Logging.getLog().debug("3")
                # gl.g_rpc_Lock.release()
                # Logging.getLog().debug("4")

                # if ret < 0:
                #     Logging.getLog().error(msg)
                # else:
                # Logging.getLog().debug("SendHeartBeatMessage OK")
            except BaseException, ex:
                Logging.getLog().critical("ex=%s" % ex)
                # gl.g_rpc_Lock.release()

            time.sleep(5)

    def deal_with_T2_dataset_list(self, dataset_list):
        """
        处理T2协议返回值
        :param dataset_list:
        :return:
        """
        try:
            data = {"message": ""}
            column = dataset_list[0][0]
            data["field"] = column
            values_list = []
            for i in dataset_list[0][1:]:
                values_list.append(i)
            data["values_list"] = values_list
            return 0, data
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def deal_with_UFX_dataset_list(self, dataset_list):
        """
        处理UFX协议返回值
        UFX 可能会返回两个数据集，一个是通用信息，一个是数据结果集
        :param dataset_list:
        :return:
        """
        try:
            if len(dataset_list) == 1:  # 只返回通用信息
                data = {'message': '--'.join(dataset_list[0][1])}
                column = dataset_list[0][0]
                data['field'] = column
                values_list = []
                for i in dataset_list[0][1:]:
                    i_new = []
                    for j in i:
                        i_new.append(j.replace("'", "''"))
                    if len(str(values_list).replace(' ', '')) <= 90000:
                        values_list.append(i_new)
                data['values_list'] = values_list
            else:
                data = {'message': '--'.join(dataset_list[0][1])}
                column = dataset_list[1][0]
                data['field'] = column
                values_list = []
                for i in dataset_list[1][1:]:
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

    def processEnvInitMsg(self, json_msg):
        '''
        处理环境初始化消息
        '''
        Logging.getLog().debug("processEnvInitMsg")
        env = json_msg["msg_body"]["env"]
        task_id = json_msg["msg_body"]["task_id"]
        type = json_msg["msg_body"]["type"]
        Logging.getLog().debug("json_msg:%s" % str(json_msg))
        # ADAPTER_TYPE = json_msg["msg_body"]["cases"]["ADAPTER_TYPE"]

        Logging.getLog().debug("env = %s" % env)

        init_result = True
        try:
            # if ADAPTER_TYPE in ["SPLX_SILKTEST", "SPLX_SIKULI"]:  # fixme 以后需要修改
            if env == "1481879345901LDJNJ":  # fixme 以后需要修改
                self._executionEngine.down_load_file(env)
                cF.readSystemConfigFile(env)
                if type == "0":
                    file = "init\\%s\\initialize.ini" % env
                    ret, msg = cF.RunInitScriptEx(file)
                    if ret < 0:
                        init_result = False
                        Logging.getLog().error(msg)
                else:
                    file = "init\\%s\\deinitialize.ini" % env
                    ret, msg = cF.RunInitScriptEx(file)
                    if ret < 0:
                        init_result = False
                        Logging.getLog().error(msg)
            # 消息返回
            if init_result == True:
                init_state = "STATE_PASS"
            else:
                init_state = "STATE_FAIL"

            return 0, init_state
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, "STATE_FAIL"

    def createFTPClient(self):
        try:
            f = XFer(str(self._setting["FTPServer"]["IP"]), gl.gl_ftp_info['FTPServer']['USER'],
                     gl.gl_ftp_info['FTPServer']['PASSWORD'], '.',
                     int(self._setting["FTPServer"]["PORT"]))
            f.login()
            return 0, f
        except:
            exc_info = cF.getExceptionInfo()
            return -1, exc_info

    def ProcessInitUpdateMsg(self, system_id, file_name):
        '''
        处理脚本更新消息
        '''
        try:
            self._client_state = gl.CLIENT_STATE_UPDATE

            # 登录FTP同步文件  fixme 这里默认全部更新，需要后期分析目录结构保持同步，xiaorz
            if not os.path.exists(r'.\init\%s' % system_id):
                os.mkdir('init\%s' % system_id)
            ret, f = self.createFTPClient()
            if ret < 0:
                return ret, f
            f.download_files_init(r'.\init\%s' % system_id, r'.\init\%s' % system_id, file_name)

            updated_file_list = f.get_updated_file_list()
            for file in updated_file_list:  # 只处理一层目录 fixme xiaorz
                filename = file[file.rfind('\\') + 1:-4]

                if os.path.exists(os.path.join(r'.\init\%s' % system_id, filename)):
                    shutil.rmtree(os.path.join(r'.\init\%s' % system_id, filename))
                    # shutil.copy(file, r".\init\zhlc")

            self._client_state = gl.CLIENT_STATE_FREE
            return 0, ""

        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            self._client_state = gl.CLIENT_STATE_FREE

            return -1, exc_info

    def ProcessScriptUpdateMsg(self):
        '''
        处理脚本更新消息
        '''
        try:
            self._client_state = gl.CLIENT_STATE_UPDATE

            # 登录FTP同步文件  fixme 这里默认全部更新，需要后期分析目录结构保持同步，xiaorz
            if not os.path.exists(r'.\ScriptRcv'):
                os.mkdir('ScriptRcv')
            if not os.path.exists(r'.\Script'):
                os.mkdir('Script')

            ret, f = self.createFTPClient()
            if ret < 0:
                return ret, f
            f.download_files(r'.\ScriptRcv', r'.\Script')

            updated_file_list = f.get_updated_file_list()
            for file in updated_file_list:  # 只处理一层目录 fixme xiaorz
                filename = file[file.rfind('\\') + 1:-4]

                if os.path.exists(os.path.join(r'.\Script', filename)):
                    shutil.rmtree(os.path.join(r'.\Script', filename))
                    # os.mkdir(os.path.join(r'.\Script',filename))
                # cF.unzip_file(file,os.path.join(r'.\Script',filename))
                if file[-4:] == ".zip":
                    # if it is the sikuli script
                    print "begin to upzip %s" % (file)
                    cF.unzip_file(file, r'.\Script')
                elif file[-4:] == ".jar":
                    # if it is the appium script
                    print "copy %s to .\\Script"
                    shutil.copy(file, r".\Script")
                else:
                    print "copy %s to .\\Script"
                    shutil.copy(file, r".\Script")

            self._client_state = gl.CLIENT_STATE_FREE

            self._system_db_table_column_disable_info = json.loads(
                open(".\\ScriptRcv\\system_db_table.json", "r").read())
            return 0, ""

        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            self._client_state = gl.CLIENT_STATE_FREE

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

    #         if system_id == "":
    #             Logging.getLog().critical(u"未提供系统ID信息")
    #             return -1
    #         homedir = os.getcwd()
    #
    #         if system_id == '142891263425277DZ1':  # FIXME 需要修改为上线时实际的system_id
    #             tree = ET.parse("%s\\init\\%s\\ZHLCAutoTestSetting_%s.xml" % (homedir, system_id, gl.g_server_id))
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
    #             if deviationPCT:
    #                 for elem in deviationPCT:
    #                     gl.g_deviationPCT = elem.text
    #         self.readNewAccountInfo(system_id)
    #         # 解析集中交易数据库信息
    #         SqlServerElem = root.find("ConnectSqlServerSetting")
    #         for serverElem in SqlServerElem:
    #             gl.g_connectSqlServerSetting[serverElem.attrib["core"]] = {}
    #             for elem in serverElem:
    #                 gl.g_connectSqlServerSetting[serverElem.attrib["core"]][elem.tag] = elem.text
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
    #         gl.g_allows_error_dict = {}
    #         AllowErrorsElem = root.find("OtherSetting/AllowErrors")
    #         if AllowErrorsElem != None:
    #             for FuncidErrorElem in AllowErrorsElem:
    #                 gl.g_allows_error_dict.setdefault(FuncidErrorElem.attrib["funcid"], [])
    #                 for errorElem in FuncidErrorElem:
    #                     text = errorElem.text
    #                     texts = text.split(",")
    #                     gl.g_allows_error_dict[FuncidErrorElem.attrib["funcid"]].extend(texts)
    #     except BaseException, ex:
    #         exc_info = cF.getExceptionInfo()
    #         strerror = u"解析配置文件AutoTestSetting.xml 出现异常。原因：%s" % (exc_info)
    #         Logging.getLog().critical(strerror)
    #         return -1
    #     Logging.getLog().info(u"解析配置文件AutoTestSetting.xml 完毕")
    #     return 0
    #
    # def readNewAccountInfo(self, system_id=""):
    #     try:
    #         system_id = system_id.upper()
    #         homedir = os.getcwd()
    #         suffix = cF.get_suffix(system_id)
    #         tree = ""
    #         if os.path.exists("%s\\init\\%s\\%sAccountGroupSetting.xml" % (homedir, system_id, suffix)):
    #             tree = ET.parse("%s\\init\\%s\\%sAccountGroupSetting.xml" % (homedir, system_id, suffix))
    #         if not tree:
    #             Logging.getLog().debug(u"未读取系统%s账户组的配置文件" % system_id)
    #         root = tree.getroot()
    #         if system_id.upper() == "142891263425277DZ1":
    #             JZJYSystemSettingElem = root.find("JZJYSystemSetting")
    #             for ServerSettingElem in JZJYSystemSettingElem:
    #                 gl.g_JZJYSystemSetting[ServerSettingElem.attrib["id"]] = ServerSettingElem
    #                 AccountGroupDict = {}
    #                 for AccountGroupElem in ServerSettingElem:
    #                     paramDict = {}
    #                     for elem in AccountGroupElem:
    #                         paramDict[elem.tag] = elem.text
    #                     AccountGroupDict[AccountGroupElem.attrib["id"]] = paramDict
    #                 gl.g_paramInfoDict[ServerSettingElem.attrib["id"]] = AccountGroupDict
    #         else:
    #             account_group_id = tree.findall('.//AccountInfo')
    #             dist = {}
    #             accountDict = OrderedDict()
    #             for elem in account_group_id:
    #                 for xx in elem.getchildren():
    #                     if not xx.text:
    #                         continue
    #                     tx = xx.text.replace(',', '&comma&')
    #                     dist[xx.tag] = tx
    #                 accountDict[elem.attrib["id"]] = dist
    #                 dist = {}
    #             gl.g_accountDict = accountDict
    #
    #             # if system_id.upper() == "142891090059622AV2":
    #             #     #zhlc初始化账户获取最新的账户信息
    #             #     if os.path.exists("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id)):
    #             #         tree = ET.parse("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id))
    #             #         if tree:
    #             #             account_group_id = tree.findall('.//AccountInfo')
    #             #             dist = {}
    #             #             for elem in account_group_id:
    #             #                 if elem.attrib["id"] == '0':
    #             #                     for xx in elem.getchildren():
    #             #                         tx = xx.text.replace(',', '&comma&')
    #             #                         gl.g_accountDict['0'][xx.tag] = tx
    #             #                 break
    #
    #     except:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         return -1, exc_info

    def scan_sqlserver_db_change_info(self, system_id, dbid, table_change_dict):
        """
        扫描SQLServer的变动信息
        :param system_id: 系统ID
        :param dbid:数据库ID
        :param table_change_dict: 数据库变动字典表信息
        :return:
            table_change_dict: 数据库变动字典表信息
        """
        try:
            ret, conn = self.connect_to_sqlserver_db(system_id, dbid)
            if ret < 0:
                return ret, conn
            crs = conn.cursor()
            sql = "select * from TMP_AUTOTEST_TRIGGER"
            Logging.getLog().debug(sql)
            crs.execute(sql)
            ds = crs.fetchall()
            for rec in ds:
                username = self._system_db_info[system_id][dbid]["UserList"]  # 保持和Oracle的格式一致
                id, tablename, operation, change_content = rec
                # change_content = change_content.decode('gbk')
                # to_local_params.append((task_id, run_record_id, dbid, username, tablename, operation, change_content))

                # begin transfer to json format
                if not table_change_dict.has_key(dbid):
                    table_change_dict[dbid] = OrderedDict()
                if not table_change_dict[dbid].has_key(username):
                    table_change_dict[dbid][username] = OrderedDict()
                if not table_change_dict[dbid][username].has_key(tablename):
                    table_change_dict[dbid][username][tablename] = OrderedDict()
                    table_change_dict[dbid][username][tablename]["dbid"] = dbid
                    table_change_dict[dbid][username][tablename]["schema"] = username
                    table_change_dict[dbid][username][tablename]["tablename"] = tablename
                    table_change_dict[dbid][username][tablename]["field"] = \
                        self._system_db_table_column_disable_info[system_id][dbid][username][tablename][
                            "column_list"].keys()

                if operation == 0:  # add
                    if not table_change_dict[dbid][username][tablename].has_key('add'):
                        table_change_dict[dbid][username][tablename]["add"] = []
                    table_change_dict[dbid][username][tablename]["add"].append(change_content.split('&'))
                elif operation == 1:  # update
                    if not table_change_dict[dbid][username][tablename].has_key('update'):
                        table_change_dict[dbid][username][tablename]["update"] = OrderedDict()
                    if not table_change_dict[dbid][username][tablename]['update'].has_key('old'):
                        table_change_dict[dbid][username][tablename]["update"]["old"] = []
                    if not table_change_dict[dbid][username][tablename]['update'].has_key('new'):
                        table_change_dict[dbid][username][tablename]["update"]["new"] = []
                    if not table_change_dict[dbid][username][tablename]['update'].has_key('diff_flag'):
                        table_change_dict[dbid][username][tablename]["update"]["diff_flag"] = []

                    change_json = json.loads(change_content)

                    old_list = change_json["old"].split('&')
                    new_list = change_json["new"].split('&')

                    table_change_dict[dbid][username][tablename]["update"]["old"].append(old_list)
                    table_change_dict[dbid][username][tablename]["update"]["new"].append(new_list)

                    # 先行进行比较
                    diff_list = []
                    for i in xrange(len(old_list)):
                        if old_list[i] == new_list[i]:
                            diff_list.append(1)
                        else:
                            diff_list.append(0)
                    table_change_dict[dbid][username][tablename]["update"]["diff_flag"].append(diff_list)
                elif operation == 2:  # del
                    if not table_change_dict[dbid][username][tablename].has_key('del'):
                        table_change_dict[dbid][username][tablename]["del"] = []
                    table_change_dict[dbid][username][tablename]["del"].append(change_content.split('&'))
            return 0, table_change_dict
        except BaseException:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def scan_oracle_db_change_info(self, system_id, dbid, table_change_dict):
        """
        扫描Oracle的变动信息
        :param system_id: 系统ID
        :param dbid:数据库ID
        :param table_change_dict: 数据库变动字典表信息
        :return:
            table_change_dict: 数据库变动字典表信息
        """
        try:

            ret, conn = self.connect_to_oracle_db(system_id, dbid)
            if ret < 0:
                return ret, conn
            crs = conn.cursor()
            sql = "select username,tablename,operation,change_content from SYSTEM.TMP_AUTOTEST_TRIGGER"
            Logging.getLog().debug(sql)
            crs.execute(sql)
            ds = crs.fetchall()
            for rec in ds:
                username, tablename, operation, change_content = rec
                change_content = change_content.decode('gbk')
                # to_local_params.append((task_id, run_record_id, dbid, username, tablename, operation, change_content))

                # begin transfer to json format
                if not table_change_dict.has_key(dbid):
                    table_change_dict[dbid] = OrderedDict()
                if not table_change_dict[dbid].has_key(username):
                    table_change_dict[dbid][username] = OrderedDict()
                if not table_change_dict[dbid][username].has_key(tablename):
                    table_change_dict[dbid][username][tablename] = OrderedDict()
                    table_change_dict[dbid][username][tablename]["dbid"] = dbid
                    table_change_dict[dbid][username][tablename]["schema"] = username
                    table_change_dict[dbid][username][tablename]["tablename"] = tablename
                    table_change_dict[dbid][username][tablename]["field"] = \
                        self._system_db_table_column_disable_info[system_id][str(dbid)][username][tablename][
                            "column_list"].keys()

                if operation == 0:  # add
                    if not table_change_dict[dbid][username][tablename].has_key('add'):
                        table_change_dict[dbid][username][tablename]["add"] = []
                    table_change_dict[dbid][username][tablename]["add"].append(change_content.strip(',').split('&amp;'))
                elif operation == 1:  # update
                    if not table_change_dict[dbid][username][tablename].has_key('update'):
                        table_change_dict[dbid][username][tablename]["update"] = OrderedDict()
                    if not table_change_dict[dbid][username][tablename]['update'].has_key('old'):
                        table_change_dict[dbid][username][tablename]["update"]["old"] = []
                    if not table_change_dict[dbid][username][tablename]['update'].has_key('new'):
                        table_change_dict[dbid][username][tablename]["update"]["new"] = []
                    if not table_change_dict[dbid][username][tablename]['update'].has_key('diff_flag'):
                        table_change_dict[dbid][username][tablename]["update"]["diff_flag"] = []

                    change_json = json.loads(change_content)

                    # 为了避免原有的字段值里面有逗号，在这里先用&amp;符号予以替换，在转换完毕后再替换回来
                    old_list = change_json["old"].strip(',').split('&amp;')
                    new_list = change_json["new"].strip(',').split('&amp;')

                    table_change_dict[dbid][username][tablename]["update"]["old"].append(old_list)
                    table_change_dict[dbid][username][tablename]["update"]["new"].append(new_list)
                    diff_list = []
                    for i in xrange(len(old_list)):
                        if old_list[i] == new_list[i]:
                            diff_list.append(1)
                        else:
                            diff_list.append(0)
                    table_change_dict[dbid][username][tablename]["update"]["diff_flag"].append(diff_list)
                elif operation == 2:  # del
                    if not table_change_dict[dbid][username][tablename].has_key('del'):
                        table_change_dict[dbid][username][tablename]["del"] = []
                    table_change_dict[dbid][username][tablename]["del"].append(change_content.strip(',').split('&amp;'))
            return 0, table_change_dict
        except BaseException:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def createResultJSON(self, system_id, task_id, CASE_NAME):
        """
        扫描数据库变动信息，转化为json格式，同时清空变动表
        :return:
        """
        # return 0,"" #fixme
        str_data_change_dict = ""
        table_change_dict = OrderedDict()  # {dbid：schema：table：……}
        ret = 0
        info = None

        try:
            system_id = str(system_id).strip().upper()
            if system_id not in self._system_db_info.keys():
                return 0, ""
            for dbid in self._system_db_info[system_id].keys():
                if self._system_db_info[system_id][dbid]["dbtype"] == "ORACLE":
                    ret = -1
                    # fix zzp
                    # ret,info = self.scan_oracle_db_change_info(system_id,dbid,table_change_dict)

                elif self._system_db_info[system_id][dbid]["dbtype"] == "SQLServer":
                    ret = -1
                    # fix zzp
                    # ret,info = self.scan_sqlserver_db_change_info(system_id,dbid,table_change_dict)
                if ret < 0:
                    # 如果处理某个数据库有问题，跳过即可，有日志信息以供排查
                    continue
                else:
                    # table_change_dict = info
                    pass

            if len(table_change_dict.keys()) > 0:
                # 仅用于测试，该表可以不用存在
                # sql = "insert into sx_run_task_original_data_change ( run_task_id,run_record_id,db_id,username,tablename,operation,change_content ) values( %s,%s,%s,%s,%s,%s,%s )"
                # Logging.getLog().debug(sql)
                # cF.executeCaseManySQL(sql, to_local_params)

                # dump to json string
                data_change_dict = OrderedDict()
                data_change_dict["data_change_info"] = table_change_dict
                str_data_change_dict = json.dumps(data_change_dict, ensure_ascii=False, indent=4, encoding='utf-8')
                # sql = "update sx_run_record set data_change_info = '%s' where run_record_id=%s" % (str_data_change_dict, run_record_id)
                # Logging.getLog().debug(sql)
                # cF.executeCaseSQL(sql)
                # fix zzp
                # self.clear_data_change_table(system_id)

            return 0, str_data_change_dict
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def clear_data_change_table(self, system_id):
        """
        清除目标数据库的数据变动信息
        :return:
        """
        try:
            Logging.getLog().debug("self_system_db_info = %s" % self._system_db_info)

            if system_id not in self._system_db_info.keys():
                return 0, ""
            for dbid in self._system_db_info[system_id].keys():
                ret, conn, sql = "", "", ""
                if self._system_db_info[system_id][dbid]['dbtype'] == 'ORACLE':
                    ret, conn = self.connect_to_oracle_db(system_id, dbid)
                    sql = "truncate table SYSTEM.TMP_AUTOTEST_TRIGGER"
                else:
                    ret, conn = self.connect_to_sqlserver_db(system_id, dbid)
                    sql = "if exists (select * from sysobjects where id = object_id(N'run.TMP_AUTOTEST_TRIGGER') and OBJECTPROPERTY(id, N'IsUserTable') = 1) truncate table run.TMP_AUTOTEST_TRIGGER"
                if ret < 0:
                    return ret, conn
                if sql:
                    crs = conn.cursor()
                    crs.execute(sql)
                    conn.commit()
                    crs.close()
                    conn.close()
            return 0, ""
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def connect_to_oracle_db(self, system_id, dbid):
        if not self._system_db_info.has_key(system_id):
            Logging.getLog().error(u"fail to find the system_id = %s" % str(system_id))
            return -1, u"fail to find the system_id = %s" % str(system_id)
        if not self._system_db_info[system_id].has_key(dbid):
            Logging.getLog().error(u"fail to find the dbid = %s" % str(dbid))
            return -1, u"fail to find the dbid = %s" % str(dbid)
        username = self._system_db_info[system_id][dbid]['username']
        password = self._system_db_info[system_id][dbid]['password']
        servicename = self._system_db_info[system_id][dbid]['servicename']
        try:
            Logging.getLog().debug("connect_to_oracle_db %s,%s,%s" % (username, password, servicename))
            Oracle_conn = cx_Oracle.connect(username, password, servicename)
            return 0, Oracle_conn
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def connect_to_sqlserver_db(self, system_id, dbid):
        if not self._system_db_info.has_key(system_id):
            Logging.getLog().error(u"fail to find the system_id = %s" % str(system_id))
            return -1, u"fail to find the system_id = %s" % str(system_id)
        if not self._system_db_info[system_id].has_key(dbid):
            Logging.getLog().error(u"fail to find the dbid = %s" % str(dbid))
            return -1, u"fail to find the dbid = %s" % str(dbid)

        try:
            ip = self._system_db_info[system_id][dbid]["ip"]
            dbname = self._system_db_info[system_id][dbid]["UserList"]  # for sqlserver this field stand for dbname
            username = self._system_db_info[system_id][dbid]["username"]
            password = self._system_db_info[system_id][dbid]["password"]

            dbstring = "DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;autocommit=False" % (
                ip, dbname, username, password)
            conn = pyodbc.connect(dbstring)
            return 0, conn

        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def execute_sqlserver_sql(self, conn, sqlstr):
        try:
            crs = conn.cursor()

            crs.execute(sqlstr)
            rows = crs.fetchall()  # row objects are a tuple-like objects which returned by Cursor fetch function,as specified in the DB API.
            ds = []
            for row in rows:
                rec = {}
                for i, desc in enumerate(row.cursor_description):
                    rec[desc[0]] = row[i]
                ds.append(rec)
            crs.close()
            return 0, ds
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def execute_oracle_sql(self, conn, sqlstr):
        try:
            crs = conn.cursor()
            Logging.getLog().debug(sqlstr)
            crs.execute(sqlstr)
            ds = crs.fetchall()
            crs.close()
            return 0, ds
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def start_appium_server(self):
        '''
        启动appium server 需要使用线程启动，以避免阻塞
        :return:
        '''
        if self._appium_path == "":
            Logging.getLog().debug(u"未找到appium_path")
            return 0
        # 移除日志文件
        if os.path.exists("appium.log"):
            # print "remove appium.log"
            os.remove("appium.log")

        today = datetime.datetime.now().strftime('%Y%m%d')
        f = open('.\\logs\\appium_server_%s.log' % today, "a")
        Logging.getLog().debug("begin to start appium server")
        cmd_str = 'node "%s" --log-level=info >>appium.log 2>&1' % self._appium_path
        si = subprocess.STARTUPINFO
        si.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        # proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        proc = subprocess.Popen(cmd_str, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        while proc.poll() is None:  # 检测后台进程是否终止
            if self._appium_is_started == False:
                if os.path.exists("appium.log"):
                    f = open("appium.log", "r")
                    buf = f.readlines()
                    for line in buf:
                        if line.__contains__("Appium REST http interface listener started"):
                            print line
                            self._appium_is_started = True
                    f.close()
                    # line = proc.stdout.readline()
                    # f.write(line)
                    # print line
                    # if self._appium_is_started == False:
                    #     if line.__contains__("Appium REST http interface listener started"):
                    #         self._appium_is_started = True
        # f.close()
        self._appium_is_started = False
        exit_code = proc.returncode
        Logging.getLog().debug("appium server exit with %s" % exit_code)

    def stop_appium_server(self):
        cmd_str = 'taskkill /F /IM node.exe'
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        proc.wait()
        pass

    def run(self):

        if self.register_client() < 0:
            Logging.getLog().error("register_client fail, Exiting")
            return -1
        Logging.getLog().info("register_client success")
        self._client_state = gl.CLIENT_STATE_FREE
        self._heartbeat_thread = threading.Thread(target=self.SendHeartBeatMessage)
        self._heartbeat_thread.start()

        timeout_count = 0

        _last_heart_beat_response = datetime.datetime.now()  # 用来查看服务器down掉的情况，如果超过30秒钟hearteat没有能够收到响应，那么就认为服务器挂了，重新尝试连接。

        _alive_time = datetime.datetime.now()
        _alive_time_dict = {}
        _alive_time_dict["last_alive"] = _alive_time.strftime("%Y-%m-%d %H:%M:%S")

        alive_file = 'TestAgent_Alive.json'

        # Agent为了减少重新登录的麻烦，采用了记录最近一次登录信息的方法；
        # 但是，由于Agent是没有状态的，在案例集和案例集之间，或者Server重启的过程中，
        # 记录的最近登录信息和富易客户端的登录状态可能并不一致，
        # 所以，考虑到案例集的案例通常是连续执行，所以我们采用一种超时机制，在空闲状态一段时间后，就让最近登录信息失效。
        _remember_last_username_time = datetime.datetime.now()

        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        alive_file_path = os.path.join(application_path, alive_file)

        open(alive_file_path, 'w').write(json.dumps(_alive_time_dict, indent=4, ensure_ascii=False, encoding="utf8"))
        try:
            while (True):
                if (gl.is_exit_all_thread == True):
                    break

                if (datetime.datetime.now() - _alive_time).seconds > 30:
                    # 每30秒写入一次，代表存活状态，否则将会被守护进程杀掉并重新启动
                    _alive_time_dict["last_alive"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    open(alive_file_path, 'w').write(
                        json.dumps(_alive_time_dict, indent=4, ensure_ascii=False, encoding="utf8"))
                    _alive_time = datetime.datetime.now()

                # 在空闲状态一段时间后，就让最近登录信息失效
                if self._client_state == 'STATE_FREE' and self._executionEngine._last_username != "":
                    if (datetime.datetime.now() - _remember_last_username_time).seconds > 30:
                        self._executionEngine._last_username = ""
                else:
                    _remember_last_username_time = datetime.datetime.now()

                    # if self._registered == False:
                    #     Logging.getLog().debug("send register info")
                    #
                    #     retry_count = 0
                    #     while (gl.is_exit_all_thread == False):
                    #         try:
                    #             ret, msg = self._server_proxy.register_client(self._agent_id,
                    #                                                           self._setting["AgentInfo"]["IP"],
                    #                                                           self._setting["AgentInfo"]["PORT"])
                    #             break
                    #         except:
                    #             Logging.getLog().error("call register client exception")
                    #             time.sleep(3)
                    #             continue
                    #     if ret < 0:
                    #         Logging.getLog().error(msg)
                    #         gl.is_exit_all_thread = True
                    #     else:
                    #         Logging.getLog().debug("client register sucessfullly")
                    #         self._registered = True
                    #         self._client_state = gl.CLIENT_STATE_FREE
                    #         self._heartbeat_thread = threading.Thread(target=self.SendHeartBeatMessage)
                    #         self._heartbeat_thread.start()

            Logging.getLog().info(u"Exit")
        except:
            msg = cF.getExceptionInfo()
            # print u"下面是异常信息"
            Logging.getLog().error(msg)
        finally:
            Logging.getLog().info(u"TestAgent finally Exit")
            gl.is_exit_all_thread = True

    def run_test(self, run_test_json_str):
        '''
        提供给WEB端的接口函数，采用RPC方式，触发T2接口的案例试运行的函数。
        :param system_id: string类型, 需要扫描的字符串信息
        :patam funcid:string类型，功能号
        :param cmdstring: string类型，接口如参信息命令串
        :return:
            一个元组（ret，msg）：
            ret : 0 表示 成功，-1 表示 失败
            msg : 对应信息
            log_info : 日志信息
            dataset_list: 中间件的返回值列表，用于后续动作的一个参数
            return_json_string: 中间件返回值的json字符串，返回给TestAgentServer，并写入数据库
            data_change_info_json_string:数据库变动的json字符串，返回给TestAgentServer，并写入数据库

        '''
        try:
            #初始化SQLserver和oracle 的信息
            gl.g_connectOracleSetting = {}
            gl.g_connectSqlServerSetting = {}

            hr_quant_handle = gl.hr_quant_handle
            if hr_quant_handle:
                print "已经连接hr_quant_handle"
            hr_csm_handle = gl.hr_csm_handle
            if hr_csm_handle:
                print "已经连接hr_csm_handle"
            Logging.getLog().debug(u'run_test_json_str---%s' % run_test_json_str)
            now = datetime.datetime.now()
            run_start_time = now.strftime("%Y-%m-%d %H:%M:%S")

            return_json_list = []
            try:
                run_test_json_list = eval(run_test_json_str)
            except:
                run_test_json_list = json.loads(run_test_json_str, encoding='gbk')
            group_variable_dict = {}
            # 案例步骤跳过处理
            skip_left_steps = False
            skip_left_steps_cases_param_data_id = -1
            dataset_list = []
            for step, run_test_json in enumerate(run_test_json_list):
                system_id = run_test_json["system_id"]
                cmdstring = run_test_json["cmdstring"]
                step_id = run_test_json["step_id"]
                ADAPTER_TYPE = run_test_json["adapter_type"]
                case_name = run_test_json["cases_name"].decode('utf8')
                step_name = run_test_json["step_name"].decode('utf8')
                gl.current_system_id = system_id
                serverid = run_test_json["serverid"]
                interface_info = ""
                if "interface_field" in run_test_json.keys():
                    interface_info = run_test_json["interface_field"]
                print "serverid:%s" % serverid
                gl.g_server_id = serverid
                if step == 0:
                    homedir = os.getcwd()
                    system_id = str(system_id).upper()
                    if not os.path.exists("%s\init\%s" % (homedir, system_id)):
                        os.makedirs("%s\init\%s" % (homedir, system_id))
                        print '已创建 %s文件夹' % system_id
                    suffix = cF.get_suffix(system_id)
                    # 删除原有账户组信息
                    if os.path.exists("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix)):
                        os.remove("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix))
                    if os.path.exists("%s\init\%s\%s" % (homedir, system_id, 'T2InterfaceDetails.xml')):
                        os.remove("%s\init\%s\%s" % (homedir, system_id, 'T2InterfaceDetails.xml'))
                    f = glob.glob('%s\\init\\%s\\*.xml' % (homedir, system_id))
                    for file in f:
                        if file and "ZHLCAutoTestSetting" in file:
                            os.remove(file)
                    # 下载对应系统下的文件
                    f = XFer(self._setting['FTPServer']['IP'], gl.gl_ftp_info['FTPServer']['USER'],
                             gl.gl_ftp_info['FTPServer']['PASSWORD'], '.',
                             int(self._setting['FTPServer']['PORT']))
                    f.login()
                    homedir = os.getcwd()
                    system_id = str(system_id).upper()
                    f.download_files(r'%s\init\%s' % (homedir, system_id), r'.\init\%s' % system_id)
                    Logging.getLog().debug(u'>>>>>>>>下载:' + u'%s\init\%s 路径下的配置文件' % (homedir, system_id))
                    cF.readSystemConfigFile(system_id)
                    # 更新oracle信息
                    cF.add_tnsnames_info()
                funcid = run_test_json["funcid"]
                print "cbs"
                print type(run_test_json["pre_action"])

                # if isinstance(obj, int):
                if isinstance(run_test_json["pre_action"], list):
                    pres = json.dumps(run_test_json["pre_action"]).decode('utf8')
                    # pres = run_test_json["pre_action"]
                else:
                    pres = run_test_json["pre_action"].decode('utf8')

                if "ha_exit" in pres:
                    if hr_quant_handle != None:
                        hr_quant_handle.ha_exit()
                        hr_quant_handle = None
                    if hr_csm_handle != None:
                        hr_csm_handle.ha_exit()
                        hr_csm_handle = None
                    Logging.getLog().critical(u"量化关闭连接成功")
                print type(run_test_json["pro_action"])

                if isinstance(run_test_json["pro_action"], list):
                    pros = json.dumps(run_test_json["pro_action"]).decode('utf8')
                else:
                    pros = run_test_json["pro_action"].decode('utf8')

                cmdstring = run_test_json["cmdstring"].decode('utf8')
                account_group_id = run_test_json["account_group_id"]
                expect_ret = run_test_json["expect_ret"]
                if pres == None:
                    pres = ""
                if pros == None:
                    pros = ""
                # 执行前置动作
                if ADAPTER_TYPE == "SPLX_KCBP":
                    # serverid = cF_kcbp.GetServeridByServerType(server_type)
                    pres = cF_kcbp.GlobalParameterReplace(pres, serverid)
                    # print "gl.g_paramInfoDict:%s"%str(gl.g_paramInfoDict)
                    if str(serverid) in gl.g_paramInfoDict.keys():
                        if str(account_group_id) in gl.g_paramInfoDict.get(serverid).keys():
                            account_dict = gl.g_paramInfoDict.get(serverid).get(str(account_group_id))
                            # KCBP接口的用户组信息是加载在组变量中进行替换的
                            group_variable_dict.update(account_dict.items())
                            pres = cF_kcbp.GroupParameterReplace(pres, group_variable_dict)
                else:
                    pres = cF.GlobalParameterReplace(pres, account_group_id)
                    pres = cF.GroupParameterReplace(pres, group_variable_dict)
                ret, msg_info = 0, ""
                if ADAPTER_TYPE in ["SPLX_T2", "SPLX_HUARUI", "SPLX_HTTP", "SPLX_UFX", 'SPLX_HUARUI_DYS']:
                    cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    ret, msg_info = cF.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                      account_group_id)
                    # 有些值需要在执行原语后替换
                    cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                elif ADAPTER_TYPE == "SPLX_KCBP":
                    if pres and str(pres) != '[]':
                        cmdstring = cF_kcbp.GlobalParameterReplace(cmdstring, serverid)
                        cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
                        ret, msg_info = cF_kcbp.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                               serverid)
                    else:
                        ret = 0
                        msg_info = ""
                else:
                    now = datetime.datetime.now()
                    run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    # return -1,u"暂不支持的适配器"
                    return_json_list.append(
                        {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                         "succ_flag": -1, "msg": "", "log_info": u"暂不支持的适配器", "return_json_string": "",
                         "run_start_time": run_start_time, "run_end_time": run_end_time})
                if ret != 0:
                    now = datetime.datetime.now()
                    run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    Logging.getLog().critical("测试数据%s 前置动作执行失败！%s" % (str(step + 1), str(msg_info)))
                    return_json_list.append(
                        {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                         "succ_flag": -1, "msg": "", "log_info": msg_info, "return_json_string": "",
                         "run_start_time": run_start_time, "run_end_time": run_end_time})
                    continue
                sdk = None
                if ADAPTER_TYPE == "SPLX_HUARUI":
                    if funcid[:2] != '82':
                        if hr_quant_handle:
                            pass
                        else:
                            hr_quant_handle = hradapter.HRAdapter()
                            gl.hr_quant_handle = hr_quant_handle
                            sdk = hr_quant_handle
                            Logging.getLog().debug(gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"])
                            l = gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"].find(":")
                            quant_gateway_addr = gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"][:l]
                            quant_gateway_port = gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"][l + 1:]
                            ret, msg = hr_quant_handle.ha_init(quant_gateway_addr, int(quant_gateway_port))
                            if ret != 0:
                                now = datetime.datetime.now()
                                msg_sdk = str(msg)
                                run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                                Logging.getLog().critical(u"连接量化服务器失败，原因:%s" % (msg_sdk))
                                # return -1, msg_sdk, u"连接T2服务器失败，原因:%s" % (msg_sdk)
                                return_json_list.append(
                                    {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                     "step_id": step_id,
                                     "succ_flag": -1, "msg": "", "log_info": u"连接量化服务器失败，原因:%s" % (msg_sdk),
                                     "return_json_string": "", "run_start_time": run_start_time,
                                     "run_end_time": run_end_time})
                                continue
                    else:
                        if hr_csm_handle:
                            pass
                        else:
                            hr_csm_handle = hradapter.HRAdapter()
                            gl.hr_csm_handle = hr_csm_handle
                            sdk = hr_csm_handle
                            Logging.getLog().debug(gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"])
                            l = gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"].find(":")
                            csm_gateway_addr = gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"][:l]
                            csm_gateway_port = gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"][l + 1:]
                            ret, msg = hr_csm_handle.ha_init(csm_gateway_addr, int(csm_gateway_port))
                            if ret != 0:
                                msg_sdk = str(msg)
                                now = datetime.datetime.now()
                                run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                                Logging.getLog().critical(u"连接云网服务器失败，原因:%s" % (msg_sdk))
                                # return -1, msg_sdk, u"连接T2服务器失败，原因:%s" % (msg_sdk)
                                return_json_list.append(
                                    {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                     "step_id": step_id,
                                     "succ_flag": -1, "msg": "", "log_info": u"连接云网服务器失败，原因:%s" % (msg_sdk),
                                     "return_json_string": "", "run_start_time": run_start_time,
                                     "run_end_time": run_end_time})
                                continue

                elif ADAPTER_TYPE == "SPLX_T2":
                    # 连接T2服务
                    Logging.getLog().debug(gl.g_ZHLCSystemSetting["T2Server"])
                    sdk, msg_sdk = cF.connectT2(gl.g_ZHLCSystemSetting["T2Server"], "license.dat")
                    if sdk == None:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        Logging.getLog().critical(u"连接T2服务器失败，原因:%s" % (msg_sdk))
                        # return -1, msg_sdk, u"连接T2服务器失败，原因:%s" % (msg_sdk)
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": "", "log_info": u"连接T2服务器失败，原因:%s" % (msg_sdk),
                             "return_json_string": "", "run_start_time": run_start_time, "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE == "SPLX_UFX":
                    # Logging.getLog().debug(gl.g_ZHLCSystemSetting["T2Server"])
                    sdk, msg = cF.connectUFX(gl.g_ZHLCSystemSetting["T2Server"], "license_o32.dat")
                    if sdk == None:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        Logging.getLog().critical(u"连接SPLX_UFX服务器失败，原因:%s" % (msg))
                        # return -1, msg_sdk, u"连接T2服务器失败，原因:%s" % (msg_sdk)
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": "", "log_info": u"连接SPLX_UFX服务器失败，原因:%s" % (msg),
                             "return_json_string": "", "run_start_time": run_start_time, "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE == "SPLX_HUARUI_DYS":
                    Logging.getLog().debug(gl.g_ZHLCSystemSetting["HuaRuiDysServer"])
                    userDys = 'user3'
                    if "HuaRuiDysUsername" in gl.g_ZHLCSystemSetting.keys():
                        userDys = gl.g_ZHLCSystemSetting["HuaRuiDysUsername"]
                    passwordDys = 'password3'
                    if "HuaRuiDysPassword" in gl.g_ZHLCSystemSetting.keys():
                        passwordDys = gl.g_ZHLCSystemSetting["HuaRuiDysPassword"]
                    portDys = 32001
                    if "HuaRuiDysPort" in gl.g_ZHLCSystemSetting.keys():
                        portDys = int(gl.g_ZHLCSystemSetting["HuaRuiDysPort"])
                    sdk, msg = huarui_dys.ConnectGw(gl.g_ZHLCSystemSetting["HuaRuiDysServer"], portDys, userDys,
                                                    passwordDys)
                    if sdk == None:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        Logging.getLog().critical(u"连接SPLX_HUARUI_DYS服务器失败，原因:%s" % (msg))
                        # return -1, msg_sdk, u"连接T2服务器失败，原因:%s" % (msg_sdk)
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": "", "log_info": u"连接SPLX_UFX服务器失败，原因:%s" % (msg),
                             "return_json_string": "", "run_start_time": run_start_time, "run_end_time": run_end_time})
                        continue
                else:
                    pass
                Logging.getLog().debug('funcid_cmdstring:' + funcid + cmdstring)
                succ_flag = False
                msg = ""
                log_info = ""
                return_json_string = ""
                dataset = []
                # data_change_info_json_string = ""
                if ADAPTER_TYPE in ["SPLX_T2"]:
                    # 试运行综合理财/用户中心的案例
                    try:
                        dataset_list = []
                        ret, msg = cF.ExecuteOneTestCase(sdk, funcid, cmdstring)
                        Logging.getLog().debug("ret:%s, msg:%s" % (ret, msg))
                        rtn, timeout = zhlc.GetASYCfunctionTimeout(funcid)
                        if timeout == "":
                            timeout = 0
                        if ret == 0 or ret == 1:
                            dataset_list = cF.GetReturnRows(sdk)
                            if timeout != 0:
                                Logging.getLog().debug("等待异步返回结果，timeout = %s 秒" % timeout)
                                time.sleep(int(timeout))

                            # if gl.g_ZHLCSystemSetting["DisableDBCompare"] == "True": #fixme
                            #    #TODO 获取数据库变动值，包括Oracle和SQL Server变动值
                            #    data_chanret, data_change_info_json_string = self._mqclient.createResultJSON(system_id, runtaskid, run_record_id)
                            #    if data_chanret < 0:
                            #        Logging.getLog().error(data_change_info_json_string)
                            #        data_change_info_json_string = ""

                            # TODO 拼接中间件返回值和数据库变动值为一个JSON字符串，传递回TestAgentServer
                            if funcid == "12008317":
                                dataset_list[0] = dataset_list[0][:100]
                            r, return_json_string = self.deal_with_T2_dataset_list(dataset_list)
                            if r < 0:
                                # Logging.getLog().error(return_json_string)
                                return_json_string = ""

                            if ret == 0:
                                # 这里有一个假设，当返回0的时候，不会出现error_no的字段，那么如果expect_id为非零值时，就判定案例失败
                                if int(expect_ret) != 0:
                                    # TODO 判定失败
                                    succ_flag = False
                                else:
                                    # TODO 判定成功
                                    succ_flag = True
                            else:  # ret == 1
                                msg = cF.GetErrorInfoFromReturnRows(dataset_list)
                                rows_list = dataset_list[0]
                                error_no = ''
                                index_error_no = ""
                                if "error_no" in rows_list[0]:
                                    index_error_no = rows_list[0].index("error_no")
                                    error_no = rows_list[1][index_error_no]
                                Logging.getLog().debug(u"index_error_no:%s，error_no:%s, expect_ret:%s" % (
                                    index_error_no, error_no, expect_ret))
                                # if rows_list[0][1] == "error_no":  # 确认是error_no 字段
                                #     error_no = rows_list[1][1]
                                if error_no == '':  # 无法正确提取error_no
                                    # TODO 判定失败
                                    succ_flag = False
                                else:
                                    if int(error_no) == int(expect_ret):  # 符合预期，判定成功
                                        # TODO 判定成功
                                        succ_flag = True
                                    else:
                                        # TODO 判定失败
                                        succ_flag = False

                        else:
                            # TODO 判定失败
                            succ_flag = False
                        if sdk:
                            # 关闭T2Server 连接
                            sdk.Close()
                            sdk.DeInitInterface()
                        if succ_flag == True:
                            pass
                            # return_json_list.append({"succ_flag":0,"msg":msg,"log_info":log_info,"return_json_string":return_json_string})
                        else:
                            now = datetime.datetime.now()
                            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                            try:
                                msg = msg.decode("utf-8")
                            except Exception as e:
                                try:
                                    msg = msg.decode("gbk")
                                except Exception as e:
                                    msg = msg
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                                 "log_info": msg.replace('\r', '').replace('\n', ''),
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue

                    except BaseException, ex:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().critical(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
                        # return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info), log_info,[],return_json_string
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                             "log_info": u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info),
                             "return_json_string": return_json_string, "run_start_time": run_start_time,
                             "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE in ["SPLX_UFX"]:
                    # 试运行综合理财/用户中心的案例
                    try:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        # print gl.g_accountDict[str(account_group_id)].keys()
                        error_info = ""
                        error_flag = False
                        if str(account_group_id) not in gl.g_accountDict.keys():
                            error_info = u"该账户组不存在,请检查:%s" % account_group_id
                            error_flag = True
                        if error_flag == False and 'user_token' not in gl.g_accountDict[str(account_group_id)].keys():
                            error_info = u"账户组%s未获取user_token, 请检查对应的账户组信息" % account_group_id
                            error_flag = True
                        if error_flag:
                            Logging.getLog().error(u"未能获得user_token")
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1, "msg": u"未能获得user_token",
                                 "log_info": u"未能获得user_token",
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue
                        if gl.g_accountDict[str(account_group_id)]["user_token"] == "@user_token@":
                            ret, user_token = cF.getUserToken(sdk, str(account_group_id))
                            if ret < 0:
                                Logging.getLog().error(u"未能获得user_token")
                                return_json_list.append(
                                    {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                     "step_id": step_id, "succ_flag": -1, "msg": u"未能获得user_token",
                                     "log_info": u"未能获得user_token",
                                     "return_json_string": return_json_string, "run_start_time": run_start_time,
                                     "run_end_time": run_end_time})
                                continue
                            else:
                                Logging.getLog().info("new user_token is %s" % user_token)
                            gl.g_accountDict[str(account_group_id)]["user_token"] = user_token
                            if str(account_group_id) in gl.lh_account_info.keys() and "user_token" in \
                                    gl.lh_account_info[
                                        str(account_group_id)]:
                                gl.lh_account_info[str(account_group_id)]["user_token"] = user_token

                        cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                        cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))

                        cmdstring = cmdstring.replace("&colon&", ":").replace('amp;amp;', 'amp;')
                        # if gl.openprice_field:
                        #     openprice_key_index = cmdstring.find(gl.openprice_field)
                        #     key_value = cmdstring[openprice_key_index:].split("#")[0]
                        #     cmdstring = cmdstring.replace(key_value, gl.openprice_field + gl.openprice_zhlc)
                        # cmdstring = cmdstring.replace(" ", "")
                        Logging.getLog().info(u"------exe cmdstring:%s------" % cmdstring)

                        # system_id, cmdstring, "", "", case_name, group_variable_dict, expect_ret
                        ret, msg, log_info, dataset_list, return_json_string, data_change_info_json_string = self._executionEngine.RunUFXScript(
                            sdk, system_id, funcid, cmdstring, "", 0, expect_ret)
                        if ret == 0:
                            pass
                            # return_json_list.append({"succ_flag":0,"msg":msg,"log_info":log_info,"return_json_string":return_json_string})
                        else:
                            now = datetime.datetime.now()
                            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                            try:
                                msg = msg.decode("utf-8")
                            except Exception as e:
                                try:
                                    msg = msg.decode("gbk")
                                except Exception as e:
                                    msg = msg
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                                 "log_info": msg.replace('\r', '').replace('\n', ''),
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue

                    except BaseException, ex:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().critical(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
                        # return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info), log_info,[],return_json_string
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                             "log_info": u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info),
                             "return_json_string": return_json_string, "run_start_time": run_start_time,
                             "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE in ["SPLX_HTTP"]:
                    # 试运行综合理财/用户中心的案例
                    try:
                        ret, msg, log_info, dataset_list, return_json_string, data_change_info_json_string = self._executionEngine.RunHttpScript(
                            system_id, cmdstring, "", "", case_name, group_variable_dict, expect_ret, interface_info)
                        if ret == 0:
                            pass
                            # return_json_list.append({"succ_flag":0,"msg":msg,"log_info":log_info,"return_json_string":return_json_string})
                        else:
                            now = datetime.datetime.now()
                            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                            try:
                                msg = msg.decode("utf-8")
                            except Exception as e:
                                try:
                                    msg = msg.decode("gbk")
                                except Exception as e:
                                    msg = msg
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                                 "log_info": msg.replace('\r', '').replace('\n', ''),
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue

                    except BaseException, ex:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().critical(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
                        # return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info), log_info,[],return_json_string
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                             "log_info": u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info),
                             "return_json_string": return_json_string, "run_start_time": run_start_time,
                             "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE in ["SPLX_HUARUI_DYS"]:
                    # 试运行综合理财/用户中心的案例
                    try:
                        cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                        cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                        ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = huarui_dys.RunScript(
                            "", system_id, funcid, cmdstring, "", "", expect_ret)
                        if ret == 0:
                            pass
                            # return_json_list.append({"succ_flag":0,"msg":msg,"log_info":log_info,"return_json_string":return_json_string})
                        else:
                            now = datetime.datetime.now()
                            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                            try:
                                msg = msg.decode("utf-8")
                            except Exception as e:
                                try:
                                    msg = msg.decode("gbk")
                                except Exception as e:
                                    msg = msg
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                                 "log_info": msg.replace('\r', '').replace('\n', ''),
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue
                        huarui_dys.DeInitInterface()
                    except BaseException, ex:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().critical(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
                        # return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info), log_info,[],return_json_string
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                             "log_info": u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info),
                             "return_json_string": return_json_string, "run_start_time": run_start_time,
                             "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE == "SPLX_KCBP":
                    msg_info, log_info = "", ""
                    try:
                        cmdstring = cF_kcbp.GlobalParameterReplace(cmdstring, serverid)
                        cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
                        ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self._executionEngine.RunKCBPScirpt(
                            system_id, serverid, funcid, cmdstring, "",
                            "",
                            expect_ret)
                        if ret == 0:
                            pass
                            # return_json_list.append({"succ_flag":0,"msg":msg,"log_info":log_info,"return_json_string":return_json_string})
                        else:
                            if pros and str(pros) != '[]':
                                pros = cF_kcbp.GlobalParameterReplace(pros, serverid)
                                pros = self.paremReplace(pros, self._system_account_group, system_id, account_group_id)
                                pros = cF_kcbp.GroupParameterReplace(pros, group_variable_dict)

                                ret, pros_msg_info = cF_kcbp.action_process(pros, group_variable_dict,
                                                                                 dataset_list,
                                                                                 funcid, cmdstring, serverid)

                            now = datetime.datetime.now()
                            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1, "msg": msg_info.replace('\r', '').replace('\n', ''),
                                 "log_info": log_info.replace('\r', '').replace('\n', ''),
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue
                    except BaseException, ex:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().error(exc_info)
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": exc_info, "log_info": log_info,
                             "return_json_string": return_json_string, "run_start_time": run_start_time,
                             "run_end_time": run_end_time})
                        continue
                elif ADAPTER_TYPE == "SPLX_HUARUI":
                    try:
                        if funcid[:2] == '82':
                            ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self._executionEngine.RunHuaRuiScript(
                                hr_csm_handle, run_test_json["system_id"], funcid, cmdstring, "", "", expect_ret)
                        else:
                            ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self._executionEngine.RunHuaRuiScript(
                                hr_quant_handle, run_test_json["system_id"], funcid, cmdstring, "", "", expect_ret)
                        if isinstance(return_json_string['message'], (str, unicode)):
                            try:
                                return_json_string['message'] = return_json_string['message'].encode("gbk")
                            except Exception as e:
                                return_json_string['message'] = return_json_string['message'].decode("gbk")
                        for j in return_json_string['values_list']:
                            for index, i in enumerate(j):
                                if isinstance(i, unicode):
                                    print 'unicode'
                                    try:
                                        j[index] = i.encode("gbk").decode("utf-8").encode('gbk')
                                    except Exception as e:
                                        j[index] = i
                                if isinstance(i, str):
                                    print 'str'
                                    j[index] = i.encode("gbk")
                        print "ret == %s" % ret
                        if ret != 0:
                            succ_flag = False
                        else:
                            succ_flag = True
                        print succ_flag
                        if succ_flag == True:
                            pass
                            # return_json_list.append({"succ_flag":0,"msg":msg,"log_info":log_info,"return_json_string":return_json_string})
                        else:
                            now = datetime.datetime.now()
                            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                            return_json_list.append(
                                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring,
                                 "step_id": step_id, "succ_flag": -1,
                                 "msg": msg_info.replace('\r', '').replace('\n', ''),
                                 "log_info": log_info.replace('\r', '').replace('\n', ''),
                                 "return_json_string": return_json_string, "run_start_time": run_start_time,
                                 "run_end_time": run_end_time})
                            continue

                    except BaseException, ex:
                        now = datetime.datetime.now()
                        run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().critical(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
                        # return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info), log_info,[],return_json_string
                        return_json_list.append(
                            {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                             "succ_flag": -1, "msg": msg.replace('\r', '').replace('\n', ''),
                             "log_info": u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info),
                             "return_json_string": return_json_string, "run_start_time": run_start_time,
                             "run_end_time": run_end_time})
                        continue
                else:
                    return -1, u"暂不支持的适配器"
                # 案例成功执行数据后续动作
                if ADAPTER_TYPE == "SPLX_KCBP":
                    if pros and str(pros) != '[]':
                        pros = cF_kcbp.GlobalParameterReplace(pros, serverid)
                        pros = self.paremReplace(pros, self._system_account_group, system_id, account_group_id)
                        pros = cF_kcbp.GroupParameterReplace(pros, group_variable_dict)

                        ret, pros_msg_info = cF_kcbp.action_process(pros, group_variable_dict, dataset_list,
                                                                    funcid, cmdstring, serverid)
                    else:
                        ret, pros_msg_info = 0, 0
                if ADAPTER_TYPE == "SPLX_HUARUI":
                    pass
                else:
                    pros = cF.GlobalParameterReplace(pros, account_group_id)
                    pros = self.paremReplace(pros, self._system_account_group, system_id, account_group_id)
                    pros = cF.GroupParameterReplace(pros, group_variable_dict)
                if ADAPTER_TYPE in ["SPLX_T2", "SPLX_HUARUI", "SPLX_HTTP", "SPLX_UFX", "SPLX_HUARUI_DYS"]:
                    datasetlist = ""
                    if ADAPTER_TYPE in ["SPLX_UFX"]:
                        datasetlist = dataset_list[1]
                    elif ADAPTER_TYPE in ["SPLX_HUARUI", "SPLX_HUARUI_DYS"]:
                        datasetlist = dataset_list
                    else:
                        datasetlist = dataset_list[0]
                    ret, pros_msg_info = cF.action_process(pros, group_variable_dict, datasetlist, funcid,
                                                           cmdstring, account_group_id)

                    # print group_variable_dict
                if ret != 0:
                    Logging.getLog().critical(u"测试数据%s 后续动作执行失败！%s" % (str(step_id), str(pros_msg_info)))
                    msg = u"数据后续动作执行失败！%s" % pros_msg_info
                    log_info = u"数据后续动作执行失败！%s" % pros_msg_info
                    now = datetime.datetime.now()
                    run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    return_json_list.append(
                        {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                         "succ_flag": -1, "msg": msg, "log_info": log_info, "return_json_string": return_json_string,
                         "run_start_time": run_start_time, "run_end_time": run_end_time})
                    continue
                else:
                    now = datetime.datetime.now()
                    run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    return_json_list.append(
                        {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                         "succ_flag": 0, "msg": msg, "log_info": log_info, "return_json_string": return_json_string,
                         "run_start_time": run_start_time, "run_end_time": run_end_time})

            for i in return_json_list:
                msg = i["msg"]
                try:
                    msg = msg.decode("utf-8")
                except Exception as e:
                    try:
                        msg = msg.decode("gbk")
                    except Exception as e:
                        msg = msg
                i["msg"] = msg
                log_info = i["log_info"]
                try:
                    log_info = log_info.decode("utf-8")
                except Exception as e:
                    try:
                        log_info = log_info.decode("gbk")
                    except Exception as e:
                        log_info = log_info
                i["log_info"] = log_info
            return_json_str = ""
            try:
                return_json_str = json.dumps(return_json_list, sort_keys=True, ensure_ascii=False, encoding="gbk",
                                             separators=(',', ':'))
            except:
                return_json_str = str(return_json_list).encode('gbk')

            print "result _ run _ test :%s" % return_json_str
            return return_json_str
        except:
            now = datetime.datetime.now()
            run_end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            # return -1,exc_info
            return_json_list.append(
                {"case_name": case_name, "step_name": step_name, "cmdstring": cmdstring, "step_id": step_id,
                 "succ_flag": 0, "msg": msg, "log_info": exc_info, "return_json_string": return_json_string,
                 "run_start_time": run_start_time, "run_end_time": run_end_time})
            return_json_str = json.dumps(return_json_list, sort_keys=True, indent=4, ensure_ascii=False, encoding="gbk",
                                         separators=(',', ':'))
            return return_json_str


def processTerm(signum, frame):
    Logging.getLog().debug("receive Term signal")
    gl.is_exit_all_thread = True


def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)
    Logging.getLog().info(u'''
    时溪自动化测试平台-Test Agent v2.0 2019.03.05 alpha-7
    (上海时溪信息技术有限公司）
    ''')
    config_name = 'TestAgent.ini'
    # cF.readConfigFile()

    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)

    config_path = os.path.join(application_path, config_name)

    setting_string = open(config_path, "r").read()
    try:
        mqclient_setting = json.loads(setting_string)
        gl.gl_ftp_info = mqclient_setting
    except:
        mqclient_setting = eval(setting_string)
        gl.gl_ftp_info = mqclient_setting

    # mqclient.start_appium_server()
    while True:
        mqclient = MQClient(mqclient_setting)
        mqclient.setDaemon(True)
        mqclient.start()
        while True:
            if mqclient.isAlive() == False:
                mqclient.rpcserver.server_close()
                Logging.getLog().debug("mqclient.rpcserver.server_close")
                return
            if mqclient.mq_connect_closed == True:
                mqclient.mq_connect_closed = False
                gl.is_exit_all_thread = True

                time.sleep(15)

                mqclient.close_all()
                gl.is_exit_all_thread = False
                Logging.getLog().debug("mqclient close")
                break


if __name__ == "__main__":
    main()
    # a = json.loads(open(".\\init\\tdx\\user_account.json", "r").read())
    # pass
