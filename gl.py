# -*- coding:gbk -*-
import wx
import logging
import threading
from collections import OrderedDict
from enum import IntEnum

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import Queue
import time
import os
import sys

g_traceback_template = '''Traceback (most recent call last):  File "%(filename)s", line %(lineno)s, in %(name)s %(type)s: %(message)s %(more_info)s\n'''  # Skipping the "actual line" item


class NullHandler(logging.Handler):
    def emit(self, record): pass


class GlobalLogging:
    log = None
    root_hundlers = 0
    ch_handler = ""
    fh_handler = ""

    @staticmethod
    def getLog():
        # global log_flag
        # global log_init_flag
        # if int(time.strftime("%H", time.localtime())) == 1:
        #     # log_flag = False
        #     log_init_flag += 1
        #     GlobalLogging.log == None
        # else:
        #     log_init_flag = 0
        # if log_flag == False and log_init_flag <= 1:
        #     if GlobalLogging.log == None:
        #         GlobalLogging.log = GlobalLogging()
        #     log_flag = True
        homepath = os.getcwd()
        log_path = os.path.join(homepath, "logs")
        if not os.path.isdir(log_path):
            os.mkdir(log_path)
        date = time.strftime("%Y%m%d", time.localtime())
        log_path = os.path.join(log_path, "TEST_AGENT_%s.log" % date)
        if GlobalLogging.log != None:
            if not os.path.exists(log_path):
                GlobalLogging.root_hundlers = 1
                GlobalLogging.log = None
        if GlobalLogging.log == None:
            GlobalLogging.log = GlobalLogging()

        return GlobalLogging.log

    # def getLog():
    #     if GlobalLogging.log == None:
    #         GlobalLogging.log = GlobalLogging()
    #     return GlobalLogging.log

    def __init__(self):
        self.logger = None
        self.handler = None
        self.level = logging.DEBUG
        self.logger = logging.getLogger("GlobalLogging")
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        h = NullHandler()
        self.logger.addHandler(h)

        # fixme
        self.setLoggingLevel(self.level)  # 必须设置，否则出不来
        self.setLoggingToConsole()

        date = time.strftime("%Y%m%d", time.localtime())

        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        log_path = os.path.join(application_path, "logs")
        if not os.path.isdir(log_path):
            os.mkdir(log_path)
        log_path = os.path.join(log_path, "TEST_AGENT_%s.log" % date)

        self.setLoggingToFile(log_path)

        self.lock = threading.Lock()

    def setLoggingToFile(self, file):
        if GlobalLogging.root_hundlers == 1:
            self.logger.removeHandler(GlobalLogging.fh_handler)
        fh = logging.FileHandler(file)
        GlobalLogging.fh_handler = fh
        fh.setFormatter(self.formatter)
        fh.setLevel(self.level)
        self.logger.addHandler(fh)

    def setLoggingToConsole(self):
        if GlobalLogging.root_hundlers == 1:
            self.logger.removeHandler(GlobalLogging.ch_handler)
        ch = logging.StreamHandler()
        GlobalLogging.ch_handler = ch
        ch.setFormatter(self.formatter)
        ch.setLevel(self.level)
        self.logger.addHandler(ch)

    def setLoggingToHandler(self, handler):
        self.handler = handler

    def setLoggingLevel(self, level):
        self.level = level
        self.logger.setLevel(level)

    def debug(self, s):
        self.lock.acquire()
        s = "%s:%s " % (sys._getframe().f_back.f_code.co_name, sys._getframe().f_back.f_lineno) + s
        self.logger.debug(s)
        if not self.handler == None and self.level <= logging.DEBUG:
            self.handler('-DEBUG-:' + s)
        self.lock.release()

    def info(self, s):
        self.lock.acquire()
        s = "%s:%s " % (sys._getframe().f_back.f_code.co_name, sys._getframe().f_back.f_lineno) + s
        self.logger.info(s)
        if not self.handler == None and self.level <= logging.INFO:
            self.handler('-INFO-:' + s)
        self.lock.release()

    def warn(self, s):
        self.lock.acquire()
        s = "%s:%s " % (sys._getframe().f_back.f_code.co_name, sys._getframe().f_back.f_lineno) + s
        self.logger.warn(s)
        if not self.handler == None and self.level <= logging.WARNING:
            self.handler('-WARN-:' + s)
        self.lock.release()

    def error(self, s):
        self.lock.acquire()
        s = "%s:%s " % (sys._getframe().f_back.f_code.co_name, sys._getframe().f_back.f_lineno) + s
        self.logger.error(s)
        if not self.handler == None and self.level <= logging.ERROR:
            self.handler('-ERROR-:' + s)
        self.lock.release()

    def critical(self, s):
        self.lock.acquire()
        s = "%s:%s" % (sys._getframe().f_back.f_code.co_name, sys._getframe().f_back.f_lineno) + s
        self.logger.critical(s)
        if not self.handler == None and self.level <= logging.CRITICAL:
            self.handler('-CRITICAL-:' + s)
        self.lock.release()


# for FUYIAutoTest fixme 以后从配置文件中读取
g_sikuli_script_dir = ".\\Script\\"
g_sikuli_path = "C:\\sikuli\\runsikulix.cmd"

CMD_SPLX_SILKTEST = 'stw -dsn SilkTest -u admin -p admin -r "GTJA_POC" '
# 消息队列定义
CLIENT_REGISTER_MSG_ID = "1"
RESPONSE_MSG_ID = "2"
HEARTBEAT_MSG_ID = "3"
CASE_DISTRIBUTE_MSG_ID = "4"
CASE_RESULT_MSG_ID = "5"
UPDATE_SCRIPT_MSG_ID = "6"
FILE_SENDING_MSG_ID = "7"
INIT_ENV_MSG_ID = "8"
INIT_ENV_REP_MSG_ID = "9"
PUBLIC_NEW_TASK_ID = "10"
CANCEL_A_TASK_ID = "11"
RESTORE_TASK_MSG_ID = "12"  # 考虑任务重建的时候使用

register_msg = {
    "msg_id": CLIENT_REGISTER_MSG_ID,
    "msg_desc": "register",
    "msg_serialno": "1",
    "msg_body":
        {
            "agent_id": "1",
            "agent_ip": "127.0.0.1",
            "agent_port": "16001"
        }
}
response_msg = {
    "msg_id": RESPONSE_MSG_ID,
    "msg_desc": "answer",
    "msg_serialno": "",
    "msg_body":
        {
            "ack_serialno": "1"
        }
}
heartbeat_msg = {
    "msg_id": HEARTBEAT_MSG_ID,
    "msg_desc": "heartbeat",
    "msg_serialno": "1",
    "msg_body":
        {
            "agent_id": "1",
            "agent_state": "STATE_REGISTER"
        }
}
case_distribute_msg = {
    "msg_id": CASE_DISTRIBUTE_MSG_ID,
    "msg_desc": "casesDistribute",
    "msg_serialno": "1",
    "msg_body": {}
}
case_result_msg = {
    "msg_id": CASE_RESULT_MSG_ID,
    "msg_desc": "caseResultReturn",
    "msg_serialno": "1",
    "msg_body":
        {
            "client_id": "",
            "result": {}
        }
}
update_script_msg = {
    "msg_id": UPDATE_SCRIPT_MSG_ID,
    "msg_desc": "updateScript",
    "msg_serialno": "1",
    "msg_body":
        {
            "file_path": ".\\Script"
        }
}
file_sending_msg = {
    "msg_id": FILE_SENDING_MSG_ID,
    "msg_desc": "fileSending",
    "msg_serialno": "1",
    "msg_body":
        {
            "file_path": "",
            "file_content": ""
        }
}
init_env_msg = {
    "msg_id": INIT_ENV_MSG_ID,
    "msg_desc": "InitEvn",
    "msg_serialno": "1",
    "msg_body":
        {
            "task_id": "",
            "env": "1481879345901LDJNJ",
            "type": ""
        }
}  # type=0为初始化消息，type=1为恢复初始化消息
init_env_rep_msg = {
    "msg_id": INIT_ENV_REP_MSG_ID,
    "msg_desc": "InitEnvRep",
    "msg_serialno": "1",
    "msg_body":
        {
            "task_id": "",
            "env": "",
            "type": "",
            "result": ""
        }
}
public_new_task_msg = {
    "msg_id": PUBLIC_NEW_TASK_ID,
    "msg_desc": "publish_new_task_msg",
    "msg_serialno": "1",
    "msg_body":
        {
            "task_id": "",
            "queue_name": "",
        }
}

cancel_a_task_msg = {
    "msg_id": CANCEL_A_TASK_ID,
    "msg_desc": "cancel_a_task_msg",
    "msg_serialno": "1",
    "msg_body":
        {
            "task_id": "",
        }
}
restore_task_msg = {  # 用于TestAgent重启的时候，恢复任务信息，在客户端注册后，由Serve根据数据库中未执行完毕的任务发送给客户端
    "msg_id": RESTORE_TASK_MSG_ID,
    "msg_desc": "restore_task",
    "msg_serialno": "1",
    "msg_body":
        [
            # "{task_id}":[{agent_id_list}]
        ]
}
# set_agent_init_state_msg = {"msg_id":SET_AGENT_INIT_STATE_ID,"msg_desc":u"TestAgent状态初始化","msg_serialno":"1","msg_body":{}}


# 初始配置

RECEIVE_DATA_EVENT = 'RECEIVE_DATA_EVENT'
# EVENT_PROCESS_BUSI_MESSAGE = 'EVENT_PROCESS_BUSI_MESSAGE'
# EVENT_SEND_DEINIT_ENV_MSG = 'EVENT_SEND_DEINIT_ENV_MSG'

# 消息机制

# MSG_TRIGGER_SCRIPT_UPDATE = "MSG_TRIGGER_SCRIPT_UPDATE"
# MSG_PROCESS_CASE_DISTRIBUTION = "MSG_PROCESS_CASE_DISTRIBUTION"
# MSG_PROCESS_ENV_INIT = "MSG_PROCESS_ENV_INIT"
# MSG_PROCESS_SCRIPT_UPDATE = "MSG_PROCESS_SCRIPT_UPDATE"


g_SysRunFlag = False
g_MySQLConn = None
all_core = {}
g_thread_flag = 0
# Agent状态
CLIENT_STATE_REGISTER = "STATE_REGISTER"  # 注册中
CLIENT_STATE_UPDATE = "STATE_UPDATE"  # 更新中
CLIENT_STATE_FREE = "STATE_FREE"  # 空闲中
CLIENT_STATE_RUNNING = "STATE_RUNNING"  # 执行中
CLIENT_STATE_UNKNOWN = "STATE_UNKNOWN"  # 失联中

# Agent 任务状态
# 每个Agent都要做一些事情，而且必须要按照顺序，光采用Agent的状态会存在延迟的状态，会导致一些错乱，所以在服务器端增加一个任务状态来控制
CLIENT_TASK_STATE_REGISTER = "CLIENT_TASK_STATE_REGISTER"
CLIENT_TASK_STATE_UPDATESCRIPT = "CLIENT_TASK_STATE_UPDATESCRIPT"
CLIENT_TASK_STATE_ENIV_INIT = "CLIENT_TASK_STATE_ENIV_INIT"
CLIENT_TASK_STATE_EXECUTE_CASE = "CLIENT_TASK_STATE_EXECUTE_CASE"
CLIENT_TASK_STATE_FREE = "CLIENT_TASK_STATE_FREE"

TASK_STATE_START = "STATE_START"
TASK_STATE_PREPARE = "STATE_PREPARE"
TASK_STATE_RUNNING = "STATE_RUNNING"
TASK_STATE_FINISH = "STATE_FINISH"

threadQueue = Queue.Queue()
threadQueueTask = Queue.Queue()
conntion_db2 = []
sign = 0
# 配置文件信息
g_accountDict = {}
g_testcaseDBDict = {}
g_connectSqlServerSetting = {}
g_connectOracleSetting = {}
g_timeSyncServerSettingList = []  # 需要修改时间的服务器列表
g_ZHLCSystemSetting = {}
g_interfaceTree = None  # 保存接口树
g_interfaceDetailTree = None  # 保存细节树
g_accountDict = {}  # 账号组信息
g_SysCasesList = {}  # 用于产生未覆盖功能号报表
g_sdk = None
g_engine = None
current_system_id = '14288901937052FXJA'  # 当前系统id默认为综合理财
# current_system_id = '142891090059622AV2'  # 当前系统id默认为综合理财
# current_system_id = '1428908551835S0NXP'  # 当前系统id默认为综合理财
is_exit_all_thread = False

SERVER_MAX_RETRY_COUNT = 3

g_rpc_Lock = threading.Lock()
g_sync_Lock = threading.Lock()  # 控制命令队列和任务队列同步的锁

g_dzh_param_dict = OrderedDict()  # 保存大智慧的参数信息

g_servcename_to_dbid = {}

# g_table_column_disable_info = OrderedDict()
"""
{
    "[db_id]":{
        "[schema]":{
            "[tablename]":{
                "column_list":{
                    "[column1]":{
                        "disableflag":[0,1],
                        "column_id":["column_id"],
                        "idx":["idx"],
                        "is_exclude":0
                    }
                },
                "disableflag":0,
                "pk":"primary_key_string_list"
            }
        }
    }
}
"""
g_task_id = 0
g_current_task_id = 0
g_sno_case_name = OrderedDict()  # {sno:(menuprompt)-(grouname)-(funcname)}
g_field_chn_dict = OrderedDict()  # {field_id:chn_name}

# 临时保存TestAgentServer的RPC 服务，用于原语的调用
g_server_proxy = None

# 增加对KCBP接口的支持
g_paramInfoDict = {}  # 保存和入参相关的信息 {serverid:{type1:value1 ……}｝
g_JZJYSystemSetting = {}  # 保存每一个KCXP/KCBP服务器信息

# 迁移表数据客户号
g_clients = []

# 初始化账号案例名称
INIT_CASENAME = u"账户初始化-周边"

# 综合理财获取价格openprice
openprice_zhlc = ""
openprice_field = ""
carry_out_system_id = ""
# 该功能号下的该字段类型改为int
HsBranchNo_char_to_int = False
# 集中营运，更新账户组id和数据
account_id = 0
account_info = {}
hr_quant_handle = None
hr_csm_handle = None
random_args = {}
# 量化出参账户组信息
lh_account_info = {}
funcids_list = ['12000000', '12000005', '12000010', '12000022', '12000023', '12000030', '12000031', '12000032',
                '12000033', '12000034', '12000035', '12000037', '12000038', '12000040', '12000051', '12000101',
                '12000102', '12000105', '12000106', '12000300', '12000301', '12000302', '12000304', '12000308',
                '12000310', '12000311', '12000313', '12000319', '12000320', '12000322', '12000323', '12000325',
                '12000327', '12000328', '12000330', '12000331', '12000333', '12000335', '12000352', '12000501',
                '12000502', '12000503', '12000504', '12000505', '12000506', '12001001', '12001002', '12001006',
                '12001007', '12005001', '12005002', '12005003', '12005006', '12005007', '12005010', '12005011',
                '12005012', '12005013', '12005014', '12005015', '12005016', '12005017', '12005020', '12005021',
                '12005023', '12005024', '12005030', '12005031', '12005032', '12005033', '12006001', '12006002',
                '12006003', '12006004', '12006005', '12006006', '12006007', '12006008', '12006009', '12006010',
                '12006021', '12007128', '12007129', '12007130', '12007135', '12007136', '12007139', '12007143',
                '12007144', '12007146', '12007147', '12007148', '12007149', '12007151', '12007201', '12007202',
                '12007203', '12007204', '12007206', '12007207', '12007208', '12007209', '12007210', '12007211',
                '12007215', '12008111', '12008112', '12008115', '12008116', '12008118', '12008131', '12008132',
                '12008133', '12008134', '12008136', '12008137', '12008139', '12008305', '12008308', '12008311',
                '12008312', '12010101', '12011001', '12011002', '12011003', '12011004', '12011005', '12011006',
                '12011007', '12011008', '12016301', '12016304', '12016305', '12016306', '12016307', '12016308',
                '12016310', '12016311', '12016312', '12016314', '12017101', '12017103', '12017105', '12017106',
                '12017150', '12017151']

# 更新账户组信息内容，需回传账户
return_account_update = {}
return_account_insert = {}

# 综合理财获取生日
birthday_zhlc = ""
check_data = OrderedDict()
return_check_data = {}
running_agent_id = ""
# case_state = "STATE_RUNNING"
case_state = ""
# 032 循环执行案例表示
o32_for_field = {}
o32_for_flag = False
o32_for_running_flag = False
o32_pro_disableflag = False

select_result_key = ""
server_result_info = {"testResultList": []}
execute_many_row = {}
restart_execute_many_row = {"220105": [], "220205": [], "220120": []}
all_group_dict = {}
g_server_id = ""
# 一起读取列表
g_server_ids = []
g_cases_sleep_time = 0
g_allows_error_dict = {}
g_deviationPCT = None  # 买入股票允许的误差百分比
g_KcxpDataElemDict = {}  # 保存KCXP的账户信息
g_case_adapter_type = ""  # 全局适配类型
g_default_account_info = {}

g_flag = False  # 只允许一次调用
g_account_id = ''
g_create_account_info = {}

# kxbp读取队列的名称
SendQName = "req_zb"
ReceiveQName = "ans_ab"
g_core_ip_port_info = {}
g_origin_agent_info = {}

# 富易的对比函数，把程序返回的other信息和数据库的结果信息保存于此。防止中文乱码
compare_list_group_list = {}
gl_ftp_info = {}
run_test_ftp_flag = False
