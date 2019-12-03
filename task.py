# -*- coding:gbk -*-
import math
import re
import HandleAccountGroup
import commFuncs as cF
import xml.dom.minidom
from collections import OrderedDict
from ftpClient import XFer
import threading
import gl
import shutil
from gl import GlobalLogging as Logging
import datetime
import time
from datetime import timedelta
import copy
import MySQLdb
import json
import signal
from MQServer import MQServer
import sys
import os
import message
from xmlrpclib import ServerProxy
import tree_directory_class as tdc
import export_excel
from lxml import etree

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import xml


class task(threading.Thread):
    def __init__(self, mqserver):
        # 保存每个正在进行的任务的相关信息，以runtaskid 作为关键值。相关信息也为一个字典结构，
        # 包括"runtaskid","collection_id","agent_id","run_status","case_num","run_case_num","run_case_num_success","run_case_num_fail",
        # "run_start_time","run_end_time"等信息
        self._cases_task_dict = OrderedDict()

        # 进行下发，但是尚未收到确认应答的队列，
        self._cases_task_send_uncomfirm_dict = OrderedDict()
        self._mqserver = mqserver
        self._mqserver.registerTaskThread(self)
        # message.sub(gl.EVENT_SEND_DEINIT_ENV_MSG,self.sendDeInitEnvMsg)
        threading.Thread.__init__(self)
        self._tdc = tdc.tree_directory_class()

        pass

    def getLeftCasesCount(self, runtaskid):
        '''
        根据运行任务id获得剩下的案例个数
        '''
        if runtaskid in self._cases_task_dict.keys():
            return len(self._cases_task_dict[runtaskid]['cases_list'])
        else:
            return 0

    def getUnConfirmResultCasesCount(self, runtaskid):
        '''
        获得已经下发，但是没有回传结果的案例个数
        '''
        if runtaskid in self._cases_task_send_uncomfirm_dict.keys():
            return len(self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'])
        else:
            return -1

    def AddCasesRunningResult(self, runtaskid, result):
        '''
        写入接口日志信息
        '''
        try:
            if not os.path.exists('.\\logs\\%s' % runtaskid):
                os.makedirs('.\\logs\\%s' % runtaskid)

            logfilename = '%s.log' % (result["case_name"])
            logform = open('.\\logs\\%s\\%s.log' % (runtaskid, runtaskid), 'a+')
            log_info_1 = u"步骤编号:%d,案例名称:%s,功能号:%s,执行结果:%s \n" % (
                result["step"], result["case_name"], result["funcid"], result["log"])
            log_info_2 = u"入参:%s \n" % (result["cmdstring"])
            log_info_3 = ""
            if result['return_message'] != u"":
                log_info_3 = u"出参:%s \n" % (','.join(result["return_message"]["field"]))
            logform.write(log_info_1)
            logform.write(log_info_2)
            logform.write(log_info_3)
            if result['return_message'] != u"":
                for data_x in result["return_message"]["values_list"]:
                    log_info_x = ','.join(data_x) + "\n"
                    logform.write(log_info_x)
            logform.close()
            # 上传至FTP
            # eczip = zf.ZipFile('.\\logs\\%s.zip'%(runtaskid),'w')
            # ret, f = self._mqclient.createFTPClient()
            # if ret < 0:
            #    print f
            #    return ret, f
            # f.upload_file_ex('./logs/%s/%s' %(runtaskid, logfilename), '/Log/%s' % runtaskid)
        except:
            exc_info = cF.getExceptionInfo()
            erro_info = u"接口日志写入失败:%s" % exc_info
            Logging.getLog().critical(erro_info)

    def confirmCasesResult(self, runtaskid, RUN_RECORD_ID):
        '''
        确认案例的测试结果,将对应的列表数据删除
        '''
        if runtaskid not in self._cases_task_send_uncomfirm_dict.keys():
            return -1, u"未找到"

        index = -1
        for i, case in enumerate(self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list']):
            if case['RUN_RECORD_ID'] == RUN_RECORD_ID:
                index = i
                break
        if index == -1:
            return -1, u"未找到要删除的值"
        self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].pop(index)
        return 0, ""

    def distributeCasesToAgent(self, runtaskid, client_id, count=0):
        '''
        往指定的agent 下发count个用例,0表示全部下发
        '''
        next_case_idx = 0
        try:
            Logging.getLog().debug(
                "===============createCasesDistributeMsg ready get a case to distribute======================")
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            case_to_send_list = []
            debug_last_run_record_id = 0
            if count == 0:
                # 全部案例一次性下发
                # self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'] = self.cases_task_dict[runtaskid]['cases_list']
                # self._cases_task_dict[runtaskid]['cases_list'] = []
                for case in self.cases_task_dict[runtaskid]['cases_list']:
                    case['RUN_START_TIME'] = now
                    case_to_send_list.append(case)
            else:
                for i in xrange(count):
                    if len(self._cases_task_dict[runtaskid]['cases_list']) > 0:
                        case = self._cases_task_dict[runtaskid]['cases_list'][next_case_idx]
                        if case["ADAPTER_TYPE"] == 'SPLX_APPIUM':
                            ret, case = self._tdc.pre_process_test_case(case)
                            if ret < 0:
                                return ret, case
                        # Logging.getLog().debug("select cases %s" % case)
                        case['RUN_START_TIME'] = now
                        # self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].append(case)
                        case_to_send_list.append(case)
                        debug_last_run_record_id = case['RUN_RECORD_ID']
                        # 判断这个案例是否有其他步骤
                        # 判定方法为，如果两个用例有相同的CASES_PARAM_DATA_ID值
                        for i in range(1, len(self._cases_task_dict[runtaskid]['cases_list'])):
                            if self._cases_task_dict[runtaskid]['cases_list'][i]['CASES_PARAM_DATA_ID'] == case[
                                'CASES_PARAM_DATA_ID']:
                                Logging.getLog().debug("multi steps")
                                next_case_idx += 1
                                case = self._cases_task_dict[runtaskid]['cases_list'][next_case_idx]

                                if case["ADAPTER_TYPE"] == 'SPLX_APPIUM':
                                    ret, case = self._tdc.pre_process_test_case(case)
                                    if ret < 0:
                                        return ret, case

                                case['RUN_START_TIME'] = now
                                case_log = json.dumps(case, ensure_ascii=False, encoding="gbk")
                                # case_log = json.dumps(case, ensure_ascii=False, encoding="gbk")
                                # Logging.getLog().debug("get next step %s" % case_log)
                                case_to_send_list.append(case)
                                debug_last_run_record_id = case['RUN_RECORD_ID']
                            else:
                                break
                    else:
                        return -1, u"队列空了"  # fixme

            case_distribute_msg = copy.copy(gl.case_distribute_msg)
            case_distribute_msg["msg_body"]["runTaskid"] = runtaskid
            case_distribute_msg["msg_body"]["system_id"] = self._cases_task_dict[runtaskid]["system_id"]
            case_distribute_msg["msg_body"]["cases"] = case_to_send_list
            # open('case_distribute_%s.json' %str(debug_last_run_record_id),'w').write(json.dumps(case_distribute_msg,indent=4,ensure_ascii=False,encoding="utf8"))
            # if self._cases_task_dict[runtaskid]["system_id"] == '14774643386617P4VW':
            ret, rs = self._mqserver.get_sx_cases_collection_detail_info(runtaskid)
            if ret == 0:
                case_distribute_msg["excel_data"] = rs
            # 发送给Agent
            s = ServerProxy("http://%s:%s" % (
                self._mqserver._clients_dict[client_id]["ip"], self._mqserver._clients_dict[client_id]["port"]))
            msg_info = json.dumps(case_distribute_msg, ensure_ascii=False)

            retry_count = 0
            while retry_count < gl.SERVER_MAX_RETRY_COUNT:
                try:
                    ret, msg = s.processCaseDistribution(msg_info.decode('gbk'))
                    if ret < 0:
                        Logging.getLog().error(msg)
                    else:
                        Logging.getLog().debug("processCaseDistribution to agent %s " % str(client_id))
                    break
                except BaseException, ex:
                    Logging.getLog().critical("processCaseDistribution exception ex=%s" % ex)
                    retry_count += 1
                    time.sleep(3)

            if retry_count >= gl.SERVER_MAX_RETRY_COUNT:
                # 重试超时
                Logging.getLog().error("processCaseDistribution exception for %d times, exit" % retry_count)
                return -1, "processCaseDistribution exception for %d times, exit" % retry_count
            else:
                self._mqserver._clients_dict[client_id]["task_state"] = gl.CLIENT_TASK_STATE_EXECUTE_CASE
                self._mqserver._clients_dict[client_id]["state"] = gl.CLIENT_STATE_RUNNING
                for case in case_to_send_list:
                    sql = "update sx_run_record set RUN_START_TIME='%s' where run_record_id=%d" % (
                        now, case['RUN_RECORD_ID'])
                    Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)

                for i in xrange(next_case_idx + 1):
                    self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].append(
                        self._cases_task_dict[runtaskid]['cases_list'].pop(0))
            return 0, ""

        except:
            exc_info = cF.getExceptionInfo()
            return -1, exc_info

    def createCasesDistributeMsg(self, runtaskid, count=0):
        '''
        从案例列表中，创建案例分发消息
        '''
        try:
            Logging.getLog().debug(
                "===============createCasesDistributeMsg ready get a case to distribute======================")
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            case_to_send_list = []
            debug_last_run_record_id = 0
            if count == 0:
                # 全部案例一次性下发
                self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'] = self.cases_task_dict[runtaskid][
                    'cases_list']
                self._cases_task_dict[runtaskid]['cases_list'] = []
                for case in self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list']:
                    case['RUN_START_TIME'] = now
                    case_to_send_list.append(case)
            else:
                for i in xrange(count):
                    if len(self._cases_task_dict[runtaskid]['cases_list']) > 0:
                        case = self._cases_task_dict[runtaskid]['cases_list'].pop(0)
                        Logging.getLog().debug("select cases %s" % case)
                        case['RUN_START_TIME'] = now
                        self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].append(case)
                        case_to_send_list.append(case)
                        debug_last_run_record_id = case['RUN_RECORD_ID']
                        # 判断这个案例是否有其他步骤
                        while len(self._cases_task_dict[runtaskid]['cases_list']) > 0 and \
                                        self._cases_task_dict[runtaskid]['cases_list'][0]['CASES_PARAM_DATA_ID'] == \
                                        case['CASES_PARAM_DATA_ID']:
                            Logging.getLog().debug("multi steps")
                            case = self._cases_task_dict[runtaskid]['cases_list'].pop(0)
                            case['RUN_START_TIME'] = now
                            Logging.getLog().debug("get next step %s" % case)
                            self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].append(case)
                            case_to_send_list.append(case)
                            debug_last_run_record_id = case['RUN_RECORD_ID']
                    else:
                        return -1, u"队列空了"  # fixme

            case_distribute_msg = copy.copy(gl.case_distribute_msg)
            case_distribute_msg["msg_body"]["runTaskid"] = runtaskid
            case_distribute_msg["msg_body"]["cases"] = case_to_send_list
            # open('case_distribute_%s.json' %str(debug_last_run_record_id),'w').write(json.dumps(case_distribute_msg,indent=4,ensure_ascii=False,encoding="utf8"))
            for case in case_to_send_list:
                sql = "update sx_run_record set RUN_START_TIME='%s' where run_record_id=%d" % (
                    now, case['RUN_RECORD_ID'])
                Logging.getLog().debug(sql)
                cF.executeCaseSQL(sql)

            return 0, case_distribute_msg

        except:
            exc_info = cF.getExceptionInfo()
            return -1, exc_info

    def processInitEnvRepMsg(self, msg):
        '''
        处理初始化脚本回传结果
        '''
        try:
            # Logging.getLog().debug(msg)
            Logging.getLog().debug("processInitEnvRepMsg")
            runtaskid = int(msg["msg_body"]["task_id"])
            result = msg["msg_body"]["result"]
            type = msg["msg_body"]["type"]

            if type == "1":  # 如果是恢复初始化环境消息，这里就不做处理了。
                return 0, ""
            self._cases_task_dict[runtaskid]['init_state'] = result
            Logging.getLog().debug("switch %s task init_state to %s" % (str(runtaskid), result))
            sql = "update sx_cases_collection_run_task set init_state = '%s' where collection_run_task_id = %d " % (
                result, int(runtaskid))
            Logging.getLog().debug(sql)
            cF.executeCaseSQL(sql)

            # 查验是否需要告警
            if result == 'STATE_PASS':
                return 0, ""

            warning_dict = self._cases_task_dict[runtaskid]['warning_info']
            if warning_dict.has_key(1):  # 有初始化告警信息

                warning_type = 'EMAIL'
                if warning_dict[1]['warning_type'] == '2':
                    warning_type = 'MOBILE'

                sql = '''insert into sx_warning_info 
                        (
                        TASK_ID, 
                        COLLECTION_ID, 
                        WARNING_ID, 
                        WARNING_MSG, 
                        WARNING_WAY, 
                        SEND_STATE, 
                        EMAIL_LIST, 
                        MOBILE_LIST
                        )
                        values
                        (
                        %d, 
                        %d, 
                        1, 
                        '%s', 
                        '%s', 
                        'STATE_UNSEND', 
                        '%s', 
                        '%s'
                        );
                      ''' % (int(runtaskid), self._cases_task_dict[runtaskid]['collection_id'],
                             u"自动化任务%d初始化失败，请做相关处理" % int(runtaskid), warning_type,
                             MySQLdb.escape_string(warning_dict[1]['warning_email']), warning_dict[1]['warning_tel'])
                cF.executeCaseSQL(sql)
                warning_dict.pop(1)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def eval_json_data(self, msg_dict):
        # Logging.getLog().debug("反序列化时间戳 dict:%s"%str(time.time()))
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
            # Logging.getLog().error(exc_info)
            return eval(msg_dict)

    # def processCasesResultMsg(self, msg):
    #     '''
    #     处理案例回传结果
    #     '''
    #     try:
    #         Logging.getLog().debug("begin to processCasesResultMsg %s" % msg)
    #
    #         now = datetime.datetime.now()
    #         msg_dict = self.eval_json_data(msg)
    #         if not isinstance(msg_dict, dict):
    #             msg_dict = self.eval_json_data(msg)
    #         case_result_dict = OrderedDict()
    #         if not isinstance(msg_dict, dict):
    #             Logging.getLog().debug(u"执行案例有误")
    #             Logging.getLog().debug("begin to processCasesResultMsg %s" % msg)
    #             return 0, ""
    #         #更新数据库账户组信息
    #         if "account_system_id" in msg_dict.keys():
    #             account_system_id = msg_dict['account_system_id']
    #             account_data = msg_dict['account_data']
    #             account_id = msg_dict['account_id']
    #             self._mqserver.asyncupdate_account_group_info(account_system_id, account_data, account_id)
    #         runtaskid = msg_dict["msg_body"]["result"]["runTaskid"]
    #         test_result_list = msg_dict["msg_body"]["result"]["testResult"]
    #         client_id = msg_dict["msg_body"]["client_id"]
    #         system_id = msg_dict["msg_body"]["result"]["system_id"]
    #         cF.readSystemConfigFile(system_id)
    #         if runtaskid not in self._cases_task_dict.keys() or self._cases_task_dict[runtaskid][
    #             'run_status'] == 'STATE_FINISH':  # 如果任务已经是结束状态，就不需要处理了，比如取消任务
    #             return 0, ""
    #
    #         for result in test_result_list:
    #             return_json_string = result["return_message"]
    #             data_change_info_json_string = result["data_change_info"]
    #             # 开始写入接口日志
    #             if system_id in (
    #                     "142891090059622AV2", "142890425731984KH9", "1428908551835S0NXP", "142891263425277DZ1"):
    #                 self.AddCasesRunningResult(runtaskid, result)
    #             # if gl.g_ZHLCSystemSetting['TestCaseDBType'] == 'DB2':
    #             if self._mqserver._case_db_type == 'DB2':
    #                 try:
    #                     # f = open("sx_run_record_log.txt", 'a')
    #                     sql = "update sx_run_record set RESULT= ? ,CMDSTRING=? ,RESULT_MESSAGE=? ,RUN_USER=?,ATTACHMENT=?, RUN_END_TIME = ?,EXT_MESSAGE=?,DATA_CHANGE_INFO=? where RUN_RECORD_ID = ?"
    #                     Logging.getLog().debug(sql)
    #                     # f.write(sql)
    #                     # cF.executeCaseSQL(sql)
    #                     conn = cF.ConnectCaseDB('DB2')
    #                     crs = conn.cursor()
    #                     return_json_string_str = ""
    #                     try:
    #                         if system_id == "1490844074559VS0IY":
    #                             return_json_string['message'] = return_json_string['message'].encode("gbk")
    #                             for j in return_json_string['values_list']:
    #                                 for index, i in enumerate(j):
    #                                     if isinstance(i, unicode):
    #                                         print 'enter'
    #                                         j[index] = i.encode("gbk")
    #                             return_json_string_str = json.dumps(return_json_string)
    #                         else:
    #                             return_json_string_str = json.dumps(return_json_string, encoding="gbk")
    #                             # return_json_string_str = json.dumps(return_json_string, sort_keys=True, indent=4,
    #                             #                                     ensure_ascii=False, encoding="gbk",
    #                             #                                     separators=(',', ':'))
    #                     except BaseException, ex:
    #                         return_json_string_str = str(return_json_string).encode("gbk")
    #                     try:
    #                         param = (result['result'], MySQLdb.escape_string(
    #                             result['cmdstring'].replace("&bfb&", "#").replace("&bft&", "=")),
    #                                  result['log'].replace("'", "''"), str(result['run_user']),
    #                                  result['attachment'], now.strftime("%Y-%m-%d %H:%M:%S"),
    #                                  return_json_string_str.replace('\n', '').replace(' ', ''),
    #                                  data_change_info_json_string.replace("'", "''"), int(result['RUN_RECORD_ID']))
    #                         Logging.getLog().debug(str(param))
    #                         crs.execute(sql, param)
    #                         crs.commit()
    #                         crs.close()
    #                         conn.close()
    #                     except BaseException, ex:
    #                         param = (result['result'], MySQLdb.escape_string(
    #                             result['cmdstring'].replace("&bfb&", "#").replace("&bft&", "=")),
    #                                  "", str(result['run_user']),
    #                                  result['attachment'], now.strftime("%Y-%m-%d %H:%M:%S"),
    #                                  return_json_string_str.replace('\n', '').replace(' ', ''),
    #                                  data_change_info_json_string.replace("'", "''"), int(result['RUN_RECORD_ID']))
    #                         Logging.getLog().debug(str(param))
    #                         crs.execute(sql, param)
    #                         crs.commit()
    #                         crs.close()
    #                         conn.close()
    #                 except BaseException, ex:
    #                     exc_info = cF.getExceptionInfo()
    #                     Logging.getLog().error(exc_info)
    #                     return -1, exc_info
    #             else:
    #                 sql = "update sx_run_record set result='%s',result_message='%s' ,RUN_USER='%s',ATTACHMENT='%s', RUN_END_TIME = '%s', EXT_MESSAGE='%s',DATA_CHANGE_INFO='%s' where RUN_RECORD_ID = %d" % (
    #                     result['result'], MySQLdb.escape_string(result['log']), str(result['run_user']),
    #                     result['attachment'], now.strftime("%Y-%m-%d %H:%M:%S"), return_json_string,
    #                     data_change_info_json_string, int(result['RUN_RECORD_ID']))
    #                 Logging.getLog().debug(sql)
    #                 cF.executeCaseSQL(sql)
    #             self.confirmCasesResult(runtaskid, result['RUN_RECORD_ID'])
    #
    #         # 处理一下多步骤问题
    #         sql = "select CASES_PARAM_DATA_ID, RESULT from sx_run_record where TASK_ID = %d " % runtaskid
    #         ds = cF.executeCaseSQL(sql)
    #         for rec in ds:
    #             if case_result_dict.has_key(rec['CASES_PARAM_DATA_ID']):
    #                 if rec['RESULT'] == 'STATE_FAIL' or rec['RESULT'] == 'STATE_SKIP':
    #                     case_result_dict[rec['CASES_PARAM_DATA_ID']] = 'STATE_FAIL'
    #             else:
    #                 case_result_dict[rec['CASES_PARAM_DATA_ID']] = rec['RESULT']
    #
    #         pass_count = 0
    #         fail_count = 0
    #         untest_count = 0
    #         for key in case_result_dict.keys():
    #             if case_result_dict[key] == 'STATE_PASS':
    #                 pass_count += 1
    #             elif case_result_dict[key] == 'STATE_FAIL' or case_result_dict[key] == 'STATE_SKIP':
    #                 fail_count += 1
    #             else:
    #                 untest_count += 1
    #
    #         self._cases_task_dict[runtaskid]["run_case_num_success"] = pass_count
    #         self._cases_task_dict[runtaskid]["run_case_num_fail"] = fail_count
    #         self._cases_task_dict[runtaskid]["run_case_num"] = pass_count + fail_count
    #         sql4 = "select SYSTEM_VERSION from SX_COLLECTION_TEST_REPORT where COLLECTION_RUN_TASK_ID=%d" % runtaskid
    #         ds4 = cF.executeCaseSQL(sql4)
    #         # 写入数据库
    #         sql = "update sx_cases_collection_run_task set run_case_num=%d,run_case_num_success=%d,run_case_num_fail=%d where collection_run_task_id=%d" % (
    #             self._cases_task_dict[runtaskid]["run_case_num"],
    #             self._cases_task_dict[runtaskid]["run_case_num_success"],
    #             self._cases_task_dict[runtaskid]["run_case_num_fail"], runtaskid)
    #         Logging.getLog().debug(sql)
    #         cF.executeCaseSQL(sql)
    #         sql1 = '''SELECT
    #                       sx_cases_collection.COLLECTION_NAME,
    #                       sx_cases_collection_run_task.TASK_ID,
    #                       sx_cases_collection_run_task.RUN_START_TIME
    #                   FROM
    #                       sx_cases_collection
    #                   INNER JOIN sx_cases_collection_run_task
    #                      ON (sx_cases_collection.COLLECTION_ID = sx_cases_collection_run_task.COLLECTION_ID)
    #                   WHERE sx_cases_collection_run_task.collection_run_task_id=%d;''' % (runtaskid)
    #         ds1 = cF.executeCaseSQL(sql1)
    #         # 判断是否为定时任务
    #         # if (ds1[0]['TASK_ID'] == "null" or ds1[0]['TASK_ID'] == "" or ds1[0]['TASK_ID'] == None) and len(ds4) != 0:
    #         if (ds1[0]['TASK_ID'] == "null" or not ds1[0]['TASK_ID']) and len(ds4) != 0:
    #             sql2 = "update sx_collection_test_report set REPORT_TITLE='%s',REPORT_TIME='%s' where COLLECTION_RUN_TASK_ID=%d" % (
    #                 u"报告/%s/%s/%d/%d/手动/%s" % (
    #                     ds1[0]['COLLECTION_NAME'], ds4[0]['SYSTEM_VERSION'],
    #                     self._cases_task_dict[runtaskid]["run_case_num_success"],
    #                     self._cases_task_dict[runtaskid]["run_case_num_fail"], ds1[0]['RUN_START_TIME']),
    #                 ds1[0]['RUN_START_TIME'], runtaskid)
    #         else:
    #             sql2 = "update sx_collection_test_report set REPORT_TITLE='%s',REPORT_TIME='%s' where COLLECTION_RUN_TASK_ID=%d" % (
    #                 u"报告/%s//%d/%d/自动/%s" % (
    #                     ds1[0]['COLLECTION_NAME'], self._cases_task_dict[runtaskid]["run_case_num_success"],
    #                     self._cases_task_dict[runtaskid]["run_case_num_fail"], ds1[0]['RUN_START_TIME']),
    #                 ds1[0]['RUN_START_TIME'], runtaskid)
    #         Logging.getLog().debug(sql2)
    #         cF.executeCaseSQL(sql2)
    #
    #         # 查看是否需要报警
    #         warning_dict = self._cases_task_dict[runtaskid]['warning_info']
    #         if warning_dict.has_key(2):  # 是否有案例运行比例告警
    #             if (pass_count + fail_count >= int(gl.g_ZHLCSystemSetting["WarningInfoMinCasesNum"])):
    #                 # 总的执行数量超过了最低限制
    #                 fail_ratio = int(fail_count * 100 / (pass_count + fail_count))
    #                 if fail_ratio >= int(warning_dict[2]['warning_val']):
    #                     warning_type = 'EMAIL'
    #                     if warning_dict[1]['warning_type'] == '2':
    #                         warning_type = 'MOBILE'
    #
    #                     sql = '''insert into sx_warning_info
    #                             (
    #                             TASK_ID,
    #                             COLLECTION_ID,
    #                             WARNING_ID,
    #                             WARNING_MSG,
    #                             WARNING_WAY,
    #                             SEND_STATE,
    #                             EMAIL_LIST,
    #                             MOBILE_LIST
    #                             )
    #                             values
    #                             (
    #                             %d,
    #                             %d,
    #                             1,
    #                             '%s',
    #                             '%s',
    #                             'STATE_UNSEND',
    #                             '%s',
    #                             '%s'
    #                             );
    #                           ''' % (int(runtaskid), self._cases_task_dict[runtaskid]['collection_id'],
    #                                  u"自动化任务%d案例失败率超过百分之%d，请做相关处理" % (
    #                                                                        int(runtaskid),
    #                                                                        int(warning_dict[2]['warning_val'])),
    #                                  warning_type, MySQLdb.escape_string(warning_dict[1]['warning_email']),
    #                                  warning_dict[1]['warning_tel'])
    #                     Logging.getLog().debug(sql)
    #                     cF.executeCaseSQL(sql)
    #                     warning_dict.pop(2)  # 移除告警，报警一次即可
    #
    #         if self._cases_task_dict[runtaskid]["case_num"] == self._cases_task_dict[runtaskid][
    #             "run_case_num"]:  # 全部执行完毕
    #             f = XFer('127.0.0.1', 'agent', '123456', '.', 2121)
    #             f.login()
    #             if system_id in ("14774643386617P4VW", "1481879345901LDJNJ"):
    #                 f.download_files('.\\logs\\%s' % (runtaskid), r'.\\Log\\%s' % runtaskid)
    #             if os.path.exists('.\\logs\\%s' % runtaskid):
    #                 shutil.make_archive('.\\logs\\%s' % (runtaskid), 'zip', r'.\\logs\\%s' % runtaskid)
    #             f.upload_file_ex('./logs/%s.zip' % runtaskid, '/Log')
    #
    #             self._cases_task_dict[runtaskid]['run_end_time'] = datetime.datetime.now().strftime(
    #                 "%Y-%m-%d %H:%M:%S")
    #
    #             # 计算RUN_RESULT
    #             run_result = ""
    #             if self._cases_task_dict[runtaskid]["case_num"] == self._cases_task_dict[runtaskid][
    #                 "run_case_num_success"]:
    #                 run_result = "RESULT_ALL_PASS"
    #             elif self._cases_task_dict[runtaskid]["case_num"] == self._cases_task_dict[runtaskid][
    #                 "run_case_num_fail"]:
    #                 run_result = "RESULT_ALL_FAIL"
    #             elif self._cases_task_dict[runtaskid]["case_num"] > self._cases_task_dict[runtaskid][
    #                 "run_case_num_success"]:
    #                 run_result = "RESULT_PARTIAL_PASS"
    #             sql = "update sx_cases_collection_run_task set run_status='STATE_FINISH',run_result='%s',run_start_time='%s',run_end_time='%s',run_during_time='%s' where collection_run_task_id=%d" % (
    #                 run_result, self._cases_task_dict[runtaskid]['run_start_time'],
    #                 self._cases_task_dict[runtaskid]['run_end_time'], str(
    #                     datetime.datetime.strptime(self._cases_task_dict[runtaskid]['run_end_time'],
    #                                                '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
    #                         self._cases_task_dict[runtaskid]['run_start_time'], '%Y-%m-%d %H:%M:%S')),
    #                 int(runtaskid))
    #             Logging.getLog().debug(sql)
    #             cF.executeCaseSQL(sql)
    #
    #             self._cases_task_dict[runtaskid]['run_status'] = 'STATE_FINISH'
    #
    #             if warning_dict.has_key(5):  # 是否有案例全部运行完毕提示
    #                 warning_type = 'EMAIL'
    #                 if warning_dict[5]['warning_type'] == '2':
    #                     warning_type = 'MOBILE'
    #                 sql = '''insert into sx_warning_info
    #                         (
    #                         TASK_ID,
    #                         COLLECTION_ID,
    #                         WARNING_ID,
    #                         WARNING_MSG,
    #                         WARNING_WAY,
    #                         SEND_STATE,
    #                         EMAIL_LIST,
    #                         MOBILE_LIST
    #                         )
    #                         values
    #                         (
    #                         %d,
    #                         %d,
    #                         5,
    #                         '%s',
    #                         '%s',
    #                         'STATE_UNSEND',
    #                         '%s',
    #                         '%s'
    #                         );
    #                         ''' % (int(runtaskid), self._cases_task_dict[runtaskid]['collection_id'],
    #                                u"自动化任务%s执行完毕，任务状态：%s，案例总数：%s，总执行数：%s，案例成功数：%s，案例失败数%s。请予以关注，谢谢！" % (
    #                                                                  u"[" + self._cases_task_dict[runtaskid][
    #                                                                      "collection_name"] + u"(" + u"系统ID:" +
    #                                                                  self._cases_task_dict[runtaskid][
    #                                                                      "system_id"] + "," + u"任务ID:" + str(
    #                                                                      runtaskid) + u")" + u"]",
    #                                                                  u"执行完毕" + u"(" + "STATE_FINISH" + u")",
    #                                                                  str(self._cases_task_dict[runtaskid][
    #                                                                          "case_num"]),
    #                                                                  str(self._cases_task_dict[runtaskid][
    #                                                                          "run_case_num"]),
    #                                                                  str(self._cases_task_dict[runtaskid][
    #                                                                          "run_case_num_success"]),
    #                                                                  str(self._cases_task_dict[runtaskid][
    #                                                                          "run_case_num_fail"])),
    #                                warning_type, MySQLdb.escape_string(warning_dict[5]['warning_email']),
    #                                warning_dict[5]['warning_tel'])
    #                 Logging.getLog().debug(sql)
    #                 cF.executeCaseSQL(sql)
    #                 warning_dict.pop(5)  # 移除告警，报警一次即可
    #         elif self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'] == [] and \
    #                         self._cases_task_dict[runtaskid]['cases_list'] == []:  # 没执行完，又空了，应该就是被取消了
    #             f = XFer('127.0.0.1', 'agent', '123456', '.', 2121)
    #             f.login()
    #             f.download_files('.\\logs\\%s' % (runtaskid), r'.\\Log\\%s' % runtaskid)
    #             if os.path.exists('.\\logs\\%s' % runtaskid):
    #                 shutil.make_archive('.\\logs\\%s' % (runtaskid), 'zip', r'.\\logs\\%s' % runtaskid)
    #             f.upload_file_ex('./logs/%s.zip' % runtaskid, '/Log')
    #
    #             self._cases_task_dict[runtaskid]['run_end_time'] = datetime.datetime.now().strftime(
    #                 "%Y-%m-%d %H:%M:%S")
    #
    #             # 计算RUN_RESULT
    #             run_result = "RESULT_CANCEL"
    #             sql = "update sx_cases_collection_run_task set run_status='STATE_FINISH',run_result='%s',run_start_time='%s',run_end_time='%s',run_during_time='%s' where collection_run_task_id=%d" % (
    #                 run_result, self._cases_task_dict[runtaskid]['run_start_time'],
    #                 self._cases_task_dict[runtaskid]['run_end_time'], str(
    #                     datetime.datetime.strptime(self._cases_task_dict[runtaskid]['run_end_time'],
    #                                                '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
    #                         self._cases_task_dict[runtaskid]['run_start_time'], '%Y-%m-%d %H:%M:%S')),
    #                 int(runtaskid))
    #             Logging.getLog().debug(sql)
    #             cF.executeCaseSQL(sql)
    #
    #             self._cases_task_dict[runtaskid]['run_status'] = 'STATE_FINISH'
    #
    #             # 删除容易导致同步问题，fixme
    #             # del self._cases_task_dict[runtaskid]
    #             # del self._cases_task_send_uncomfirm_dict[runtaskid]
    #             # init_env_msg = copy.copy(gl.init_env_msg)
    #             # init_env_msg["msg_body"]["task_id"] = str(runtaskid)
    #             # init_env_msg["msg_body"]["env"] = 'fuyi' #fixme 以后需要根据任务表中的测试环境的信息加以变更
    #             # init_env_msg["msg_body"]["type"] = "1" # deinitialize
    #             # Logging.getLog().debug("send init_env_msg to %d" %int(client_id))
    #
    #             # ret,msg = self._mqserver.SendMessage(client_id,init_env_msg)
    #             # if ret<0:
    #             #    Logging.getLog().error(msg)
    #         return 0, ""
    #     except:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         return -1, exc_info

    def getScriptNameFromInputString(self, input_string):
        script_name = ''
        if input_string == None:
            return ""
        input_string = input_string.strip('#')

        l = input_string.find('path=')
        if l < 0:
            return script_name
        r = input_string.find('#')
        if r < 0:
            script_name = input_string[l + 5:]
        else:
            script_name = input_string[l + 5:r]
        return script_name

    def rename_error_cases_picture(self, sx_run_record_info, log_path, runtaskid):
        try:
            special_byte = ['\\', '/', ':', "'", '<', '>', '|']
            if not os.path.exists(log_path):
                return -1, "not find log path %s" % log_path
            for filename in os.listdir(log_path):
                file_name, sufix = filename.split(".")
                pathname = os.path.join(log_path, filename)
                if os.path.isfile(pathname):
                    if ".jpg" in filename and file_name in sx_run_record_info.keys():
                        CASE_NAME = sx_run_record_info[file_name]["CASE_NAME"]
                        STEP = sx_run_record_info[file_name]["STEP"]
                        STEP_NAME = sx_run_record_info[file_name]["STEP_NAME"]
                        if CASE_NAME:
                            for i in special_byte:
                                if i in filename:
                                    filename = filename.replace(i, "")
                            CASE_NAME_PATH = log_path + '\\' + str(runtaskid) + "\\" + CASE_NAME
                            if not os.path.isdir(CASE_NAME_PATH):
                                os.makedirs(CASE_NAME_PATH)
                            dstfile = CASE_NAME_PATH + "\\%s_%s.jpg" % (STEP, STEP_NAME)
                            self.mycopyfile(pathname, dstfile)
                            logpath = log_path + "/%s.log" % file_name
                            newlogpath = CASE_NAME_PATH + "\\%s_%s.log" % (STEP, STEP_NAME)
                            if os.path.exists(logpath):
                                self.mycopyfile(logpath, newlogpath)
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def mycopyfile(self, srcfile, dstfile):
        try:
            if not os.path.isfile(srcfile):
                print "%s not exist!" % (srcfile)
            else:
                fpath, fname = os.path.split(dstfile)  # 分离文件名和路径
                if not os.path.exists(fpath):
                    os.makedirs(fpath)  # 创建路径
                shutil.copyfile(srcfile, dstfile)  # 复制文件
                print "copy %s -> %s" % (srcfile, dstfile)
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1, exc_info

    def processUnFinishedCases(self):
        '''
        因为各种原因导致的TestAgentServer中断，需要启动的时候去扫描任务和运行记录，将未完成的继续完成。
        '''
        try:
            Logging.getLog().debug("processUnFinishedCases")
            sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_PREPARE'"
            Logging.getLog().debug(sql)
            ds = cF.executeCaseSQL(sql)
            if len(ds) <= 0:
                # Logging.getLog().debug(sql)
                return 0, u"没有需要继续的任务"
            cases_list = []
            for rec in ds:
                collection_id = rec['COLLECTION_ID']
                runtask_id = rec['COLLECTION_RUN_TASK_ID']
                c = self._cases_task_dict[runtask_id] = OrderedDict()
                c['runtask_id'] = runtask_id
                c['collection_id'] = collection_id
                c['agent_id'] = rec['AGENT_ID'].split(',')
                c['distribution_strategy_id'] = rec["DISTRIBUTION_STRATEGY_ID"]
                c['run_status'] = rec['RUN_STATUS']
                c['init_state'] = rec['INIT_STATE']
                c['case_num'] = rec['CASE_NUM']

                c['run_case_num'] = rec['RUN_CASE_NUM']
                c['run_case_num_success'] = rec['RUN_CASE_NUM_SUCCESS']
                c['run_case_num_fail'] = rec['RUN_CASE_NUM_FAIL']
                c['run_start_time'] = rec['RUN_START_TIME']
                c['run_end_time'] = rec['RUN_END_TIME']

                # 获取待测系统的编号
                sql = """
                    SELECT
                        sx_cases_collection.SYSTEM_ID
                       ,sx_cases_collection.COLLECTION_NAME
                    FROM
                        sx_cases_collection
                        INNER JOIN sx_cases_collection_run_task 
                        ON (sx_cases_collection.COLLECTION_ID = sx_cases_collection_run_task.COLLECTION_ID)
                    WHERE
                        sx_cases_collection_run_task.COLLECTION_RUN_TASK_ID = %d
                         
                """ % int(runtask_id)
                ds1 = cF.executeCaseSQL(sql)
                Logging.getLog().debug("processUnFinishedCases:%s" % sql)
                Logging.getLog().debug("ds1: %s" % str(ds1))
                if (len(ds1) <= 0):
                    Logging.getLog().critical("Fail to find the cmdb system_id")
                    return -1, "Fail to find the cmdb system_id"

                c["system_id"] = ds1[0]['SYSTEM_ID']
                c["collection_name"] = ds1[0]['COLLECTION_NAME']
                Logging.getLog().debug("SYSTEM_ID IS %s" % c["system_id"])

                # 获取告警信息
                # sx_cases_collection_run_task 通过TASK_ID字段是否为空来判断是定时任务还是立即执行任务
                # 如果是定时任务，需要根据TASK_ID 来获取告警信息
                # 如果是非定时任务，需要根据案例集号来获取告警信息
                # if rec['TASK_ID'] == None or rec['TASK_ID'] == "":  # 为立即执行任务
                if not rec['TASK_ID']:  # 为立即执行任务
                    sql = ''' SELECT
                                sx_task_warning_detail.WARNING_ID
                                , sx_task_warning_detail.WARNING_VAL
                                , sx_task_warning.WARNING_TYPE
                                , sx_task_warning.WARNING_EMAIL
                                , sx_task_warning.WARNING_TEL
                            FROM
                                sx_task_warning
                                INNER JOIN sx_task_warning_detail 
                                    ON (sx_task_warning.TASK_WARNING_ID = sx_task_warning_detail.TASK_WARNING_ID)
                            WHERE
                                sx_task_warning_detail.IS_WARNING = '1' AND sx_task_warning.COLLECTION_ID = %d
                            ORDER BY sx_task_warning_detail.WARNING_ID
                          ''' % (collection_id)
                else:
                    sql = ''' SELECT
                                sx_task_warning_detail.WARNING_ID
                                , sx_task_warning_detail.WARNING_VAL
                                , sx_task_warning.WARNING_TYPE
                                , sx_task_warning.WARNING_EMAIL
                                , sx_task_warning.WARNING_TEL
                            FROM
                                sx_task_warning
                                INNER JOIN sx_task_warning_detail 
                                    ON (sx_task_warning.TASK_WARNING_ID = sx_task_warning_detail.TASK_WARNING_ID)
                            WHERE
                                sx_task_warning_detail.IS_WARNING = '1' AND sx_task_warning.TASK_ID = %d
                            ORDER BY sx_task_warning_detail.WARNING_ID
                          ''' % (int(rec['TASK_ID']))

                c['warning_info'] = OrderedDict()
                ds1 = cF.executeCaseSQL(sql)
                for rec1 in ds1:
                    info_dict = OrderedDict()
                    info_dict['warning_val'] = rec1['WARNING_VAL']
                    info_dict['warning_type'] = rec1['WARNING_TYPE']
                    info_dict['warning_email'] = rec1['WARNING_EMAIL']
                    info_dict['warning_tel'] = rec1['WARNING_TEL']
                    c['warning_info'][rec1['WARNING_ID']] = info_dict

                self._cases_task_send_uncomfirm_dict[runtask_id] = OrderedDict()
                self._cases_task_send_uncomfirm_dict[runtask_id]["cases_list"] = []

                # 建立内存数据结构

                sql = '''
                       SELECT
                            sx_run_record.RUN_RECORD_ID
                            , sx_run_record.TASK_ID
                            , sx_run_record.COLLECTION_ID
                            , sx_run_record.COLLECTION_DETAIL_ID
                            , sx_run_record.CASES_ID
                            , sx_run_record.PARAM_DATA_ID
                            , sx_run_record.CASES_PARAM_DATA_ID
                            , sx_run_record.STEP
                            , sx_run_record.FUNCID
                            , sx_run_record.CMDSTRING
                            , sx_run_record.ACCOUNT_GROUP_ID
                            , sx_run_record.EXPECTED_VALUE
                            , sx_run_record.SCRIPT_NAME
                            , sx_run_record.ADAPTER_TYPE
                            , CAST(sx_run_record.PRE_ACTION as VARCHAR(32672)) AS PRE_ACTION
                            , CAST(sx_run_record.PRO_ACTION as VARCHAR(32672)) AS PRO_ACTION
                            , sx_run_record.SERVER_TYPE
                            , sx_run_record.PARAM_INDEX
                            , sx_cases.CASE_NAME
                        FROM
                            sx_run_record
                        INNER JOIN sx_cases 
                         ON (sx_run_record.CASES_ID = sx_cases.CASES_ID)
                        WHERE 
                            sx_run_record.task_id = %d and sx_run_record.RESULT = 'STATE_UNTEST'
                        ORDER BY
                            sx_run_record.COLLECTION_DETAIL_ID,sx_run_record.STEP
                    ''' % (runtask_id)

                ds1 = cF.executeCaseSQL(sql)
                Logging.getLog().debug("get %d unfinishedCases by SQL:%s" % (len(ds1), sql))
                for rec1 in ds1:
                    cases_list.append(rec1)

                self._cases_task_dict[runtask_id]['cases_list'] = cases_list
                self._cases_task_send_uncomfirm_dict[runtask_id]['cases_list'] = []
                cases_list = []
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def getCase(self, index, rec):
        try:
            CASES_DETAIL_IDS_DICT = {}
            priority_dict = {}  # 用于存放优先执行的案例前置
            cases_tree_ids = {}
            ds_server_ids = []
            cases_list = []
            collection_id = rec['COLLECTION_ID']
            collection_name = ""  # rec["COLLECTION_NAME"] fixme
            runtask_id = rec['COLLECTION_RUN_TASK_ID']
            timed_task_id = rec['TASK_ID']
            c = self._cases_task_dict[runtask_id] = OrderedDict()
            c['runtask_id'] = runtask_id
            c['collection_id'] = collection_id
            if not rec['AGENT_ID'] or rec['AGENT_ID'] == 'null':
                rec['AGENT_ID'] = '3'
            c['agent_id'] = rec['AGENT_ID'].split(',')
            c['distribution_strategy_id'] = rec["DISTRIBUTION_STRATEGY_ID"]
            c['run_status'] = rec['RUN_STATUS']
            c['init_state'] = rec['INIT_STATE']
            # 计算案例个数
            sql = "select count(distinct(collection_detail_id)) as CASE_NUM from sx_cases_collection_detail  where collection_id=%d" % (
                collection_id)
            ds = cF.executeCaseSQL(sql)
            case_num = ds[0]['CASE_NUM']
            c['case_num'] = int(case_num)

            c['run_case_num'] = 0
            c['run_case_num_success'] = 0
            c['run_case_num_fail'] = 0
            c['run_start_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c['run_end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # fixme

            # 获取待测系统的编号
            sql = """
                SELECT
                    sx_cases_collection.SYSTEM_ID
                    ,sx_cases_collection.COLLECTION_NAME
                FROM
                    sx_cases_collection
                    INNER JOIN sx_cases_collection_run_task 
                    ON (sx_cases_collection.COLLECTION_ID = sx_cases_collection_run_task.COLLECTION_ID)
                WHERE
                    sx_cases_collection_run_task.COLLECTION_RUN_TASK_ID = %d

            """ % int(runtask_id)
            ds1 = cF.executeCaseSQL(sql)
            # Logging.getLog().debug("getCasesList: %s" %sql)
            # Logging.getLog().debug("ds1: %s"%str(ds1))
            if (len(ds1) <= 0):
                Logging.getLog().critical("Fail to find the cmdb system_id")
                return -1, u"Fail to find the cmdb system_id  用例集被删除, 无法找到对应的系统数据。"

            system_id = c["system_id"] = ds1[0]['SYSTEM_ID']

            ADAPTER_TYPE_SYSTEM_ID = str(ds1[0]['SYSTEM_ID'])
            sign = 0
            # 已经在页面点击的时候下载
            try:
                self._mqserver.generate_account_group_xml(ADAPTER_TYPE_SYSTEM_ID, 0)
            except:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().error(exc_info)
            Logging.getLog().debug("generate_account_group_xml")
            c["collection_name"] = ds1[0]['COLLECTION_NAME']
            # 获取告警信息
            # sx_cases_collection_run_task 通过TASK_ID字段是否为空来判断是定时任务还是立即执行任务
            # 如果是定时任务，需要根据TASK_ID 来获取告警信息
            # 如果是非定时任务，需要根据案例集号来获取告警信息
            # if rec['TASK_ID'] == None or rec['TASK_ID'] == "":  # 为立即执行任务
            if not rec['TASK_ID']:  # 为立即执行任务
                sql = ''' SELECT
                            sx_task_warning_detail.WARNING_ID
                            , sx_task_warning_detail.WARNING_VAL
                            , sx_task_warning.WARNING_TYPE
                            , sx_task_warning.WARNING_EMAIL
                            , sx_task_warning.WARNING_TEL
                        FROM
                            sx_task_warning
                            INNER JOIN sx_task_warning_detail 
                                ON (sx_task_warning.TASK_WARNING_ID = sx_task_warning_detail.TASK_WARNING_ID)
                        WHERE
                            sx_task_warning_detail.IS_WARNING = '1' AND sx_task_warning.COLLECTION_ID = %d
                        ORDER BY sx_task_warning_detail.WARNING_ID
                      ''' % (collection_id)
            else:
                sql = ''' SELECT
                            sx_task_warning_detail.WARNING_ID
                            , sx_task_warning_detail.WARNING_VAL
                            , sx_task_warning.WARNING_TYPE
                            , sx_task_warning.WARNING_EMAIL
                            , sx_task_warning.WARNING_TEL
                        FROM
                            sx_task_warning
                            INNER JOIN sx_task_warning_detail 
                                ON (sx_task_warning.TASK_WARNING_ID = sx_task_warning_detail.TASK_WARNING_ID)
                        WHERE
                            sx_task_warning_detail.IS_WARNING = '1' AND sx_task_warning.TASK_ID = %d
                        ORDER BY sx_task_warning_detail.WARNING_ID
                      ''' % (int(rec['TASK_ID']))

            c['warning_info'] = OrderedDict()
            ds1 = cF.executeCaseSQL(sql)
            for rec1 in ds1:
                info_dict = OrderedDict()
                info_dict['warning_val'] = rec1['WARNING_VAL']
                info_dict['warning_type'] = rec1['WARNING_TYPE']
                info_dict['warning_email'] = rec1['WARNING_EMAIL']
                info_dict['warning_tel'] = rec1['WARNING_TEL']
                c['warning_info'][rec1['WARNING_ID']] = info_dict

            self._cases_task_send_uncomfirm_dict[runtask_id] = OrderedDict()
            self._cases_task_send_uncomfirm_dict[runtask_id]["cases_list"] = []

            # 往sx_run_record写入对应数据
            # sql = "select a.param_data_id,c.cases_id,c.cases_detail_id,a.script_name,a.param_data,a.expected_value,a.pre_action,a.pro_action,c.step from sx_cases_detail_param_data a,sx_cases_collection_detail b,sx_cases_detail c  where a.param_data_id = b.param_data_id and a.cases_detail_id = c.cases_detail_id and b.collection_id = '%s' " %collection_id

            sql = """
                            SELECT
                                sx_cases.TREE_DIRECTORY_ID,
                                sx_cases.PRIORITY,
                                sx_cases.CASE_NAME,
                                sx_cases_param_data.CASES_ID,
                                sx_cases_param_data.PARAM_DATA_ID_STR,
                                sx_cases_param_data.CASES_PARAM_DATA_ID,
                                sx_cases_collection_detail.COLLECTION_DETAIL_ID,
                                sx_cases_collection_detail.CASE_INDEX
                            FROM
                                sx_cases_param_data
                                INNER JOIN sx_cases_collection_detail 
                                ON (sx_cases_param_data.CASES_PARAM_DATA_ID = sx_cases_collection_detail.PARAM_DATA_ID)                               
                                INNER JOIN sx_cases 
                                ON (sx_cases_param_data.CASES_ID = sx_cases.CASES_ID)  
                            WHERE
                                sx_cases.DISABLEFLAG='0'
                            AND
                                sx_cases_collection_detail.COLLECTION_ID = %d
                            ORDER BY sx_cases_collection_detail.CASE_INDEX
                            """ % (collection_id)
            # sql = "select a.cases_id, a.cases_param_data_id,a.param_data_id_str,b.collection_detail_id from sx_cases_param_data a, sx_cases_collection_detail b where a.cases_param_data_id = b.PARAM_DATA_ID and b.COLLECTION_ID = %d" %collection_id
            Logging.getLog().debug(sql)
            ds1 = cF.executeCaseSQL(sql)
            order_by_case_index = {}

            func_ids = []
            run_result_list = []
            test_system_arr_str = ""
            ret_core, kcbp_info = "" ,""
            # 清算多核心问题
            sql = "select TEST_SYSTEM_ARR from sx_cases_collection_run_task where COLLECTION_RUN_TASK_ID=%s" % (
                int(runtask_id))
            test_system_arr_str = cF.executeCaseSQL(sql)
            if test_system_arr_str:
                test_system_arr_str = test_system_arr_str[0]["TEST_SYSTEM_ARR"]
                if test_system_arr_str == "" or test_system_arr_str == "null" or test_system_arr_str == None:
                    pass
                else:
                    TEST_SYSTEM_ARR = test_system_arr_str.split(",")
                    TEST_SYSTEM_ARR = [i.strip() for i in TEST_SYSTEM_ARR]
                    ret_core, kcbp_info = cF.get_kcbp_core(ADAPTER_TYPE_SYSTEM_ID, TEST_SYSTEM_ARR)
                    if ret_core == 0:
                        ds_server_ids = kcbp_info.keys()
            if ds_server_ids:
                count = 0
                RUN_SERVER_ALIAS_FLAG = '0'
                for server_id in ds_server_ids:
                    # 批量插入再批量修改
                    count += 1
                    if count == 1:
                        RUN_SERVER_ALIAS_FLAG = '0'
                    else:
                        RUN_SERVER_ALIAS_FLAG = '1'
                    for rec1 in ds1:
                        if rec1['PRIORITY']:
                            priority_dict[rec1['CASES_ID']] = rec1['PRIORITY']
                        cases_tree_ids[rec1['CASES_ID']] = rec1['TREE_DIRECTORY_ID']
                        order_by_case_index[rec1['CASES_ID']] = rec1['CASE_INDEX']
                        param_data_id_list = rec1['PARAM_DATA_ID_STR'].split(',')
                        for j in param_data_id_list:
                            run_result_list.append(
                                "('%s','RUN_TYPE_IMMI',%d,%d,%d,%d,%d,%d,'STATE_UNTEST','%s','%s')" % (
                                    str(server_id), runtask_id, collection_id, int(rec1['COLLECTION_DETAIL_ID']),
                                    int(rec1['CASES_ID']), int(rec1['CASES_PARAM_DATA_ID']), int(j), rec1["CASE_NAME"].replace("'", "''").replace('&comma&', ','),
                                    RUN_SERVER_ALIAS_FLAG))
            else:
                # 批量插入再批量修改
                for rec1 in ds1:
                    if rec1['PRIORITY']:
                        priority_dict[rec1['CASES_ID']] = rec1['PRIORITY']
                    order_by_case_index[rec1['CASES_ID']] = rec1['CASE_INDEX']
                    param_data_id_list = rec1['PARAM_DATA_ID_STR'].split(',')
                    for j in param_data_id_list:
                        run_result_list.append("('RUN_TYPE_IMMI',%d,%d,%d,%d,%d,%d,'STATE_UNTEST','%s')" % (
                            runtask_id, collection_id, int(rec1['COLLECTION_DETAIL_ID']), int(rec1['CASES_ID']),
                            int(rec1['CASES_PARAM_DATA_ID']), int(j), rec1["CASE_NAME"].replace("'", "''").replace('&comma&', ',')))
            # 更新配置文件标签的属性 ZHLCAutoTestSetting.xml
            try:
                Logging.getLog().debug("updateZHLCAutoTestSettingXml")
                cF.updateZHLCAutoTestSettingXml(ADAPTER_TYPE_SYSTEM_ID, runtask_id, test_system_arr_str)
            except Exception as e:
                pass
            if run_result_list == []:
                sql = "update sx_cases_collection_run_task set run_status='STATE_FINISH',run_result='RESULT_CANCEL',CASE_NUM=0,RUN_CASE_NUM=0,RUN_CASE_NUM_SUCCESS=0,RUN_CASE_NUM_FAIL=0,RUN_START_TIME='%s',RUN_END_TIME='%s',RUN_DURING_TIME='00:00:00' where collection_id=%d" % (
                    c['run_start_time'], c['run_end_time'], collection_id)
                cF.executeCaseSQL(sql)
                Logging.getLog().error(u"未能找到测试用例:取消该任务")
                self._cases_task_dict.pop(runtask_id)
                self._cases_task_send_uncomfirm_dict.pop(runtask_id)

                return -1, u"未能找到测试用例:取消该任务"
            sql = ""
            # FIXME 后续应该通过SQL解决
            run_result_list2 = list(set(run_result_list))
            run_result_list2.sort(key=run_result_list.index)
            Logging.getLog().debug("insert into sx_run_record")
            # 按100拆分
            run_result_list3 = [run_result_list2[i:i + 100] for i in range(0, len(run_result_list2), 100)]
            #处理多核心问题
            if ds_server_ids:  # fixme cbs
                for result_list in run_result_list3:
                    # 多一个核心问题
                    sql = "insert into sx_run_record(run_server_alias,run_type,task_id,collection_id,collection_detail_id,cases_id,cases_param_data_id,param_data_id,result, CASE_NAME, RUN_SERVER_ALIAS_FLAG) values %s" % (
                        ','.join(result_list))
                    # Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)
            else:
                for result_list in run_result_list3:
                    sql = "insert into sx_run_record(run_type,task_id,collection_id,collection_detail_id,cases_id,cases_param_data_id,param_data_id,result, CASE_NAME) values %s" % (
                        ','.join(result_list))
                    Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)

            # 更新命令串和步骤信息
            sql = '''
                SELECT
                    sx_run_record.RUN_RECORD_ID
                    , sx_run_record.PARAM_DATA_ID
                    , sx_run_record.RUN_RECORD_ID
                    , sx_run_record.RUN_TYPE
                    , sx_run_record.TASK_ID
                    , sx_run_record.SERVER_IP
                    , sx_run_record.COLLECTION_ID
                    , sx_run_record.COLLECTION_DETAIL_ID
                    , sx_run_record.CASES_ID
                    , sx_run_record.CASES_PARAM_DATA_ID
                    , sx_run_record.RESULT
                    , sx_run_record.RUN_START_TIME
                    , sx_run_record.RUN_END_TIME
                    , sx_cases_detail.CASES_DETAIL_ID
                    , sx_cases_detail.PARAM_ID
                    , sx_cases_detail.STEP
                    , sx_cases_detail.STEP_NAME
                    , sx_cases_detail.FUNCID
                    , sx_cases_detail.INPUT_STRING
                    , sx_cases_detail.ADAPTER_TYPE
                    , cast(sx_cases_detail.PRE_ACTION as VARCHAR(32672)) as PRE_ACTION 
                    , cast(sx_cases_detail.PRO_ACTION as VARCHAR(32672)) as PRO_ACTION 
                    , sx_cases_detail.SERVER_TYPE
                    , sx_cases_detail_param_data.PARAM_DATA
                    , sx_cases_detail_param_data.EXPECTED_VALUE
                    , sx_cases_detail_param_data.ACCOUNT_GROUP_ID
                    , sx_cases_param_data.PARAM_INDEX
                FROM
                    sx_run_record
                    INNER JOIN sx_cases_detail_param_data 
                        ON (sx_run_record.PARAM_DATA_ID = sx_cases_detail_param_data.PARAM_DATA_ID)
                    INNER JOIN sx_cases_detail 
                        ON (sx_cases_detail_param_data.CASES_DETAIL_ID = sx_cases_detail.CASES_DETAIL_ID)
                    INNER JOIN SX_CASES_PARAM_DATA
                        ON (sx_cases_detail.CASES_ID = sx_cases_param_data.CASES_ID)
                WHERE
                    sx_run_record.task_id = %d
            ''' % (runtask_id)

            value_list = []
            ds1 = cF.executeCaseSQL(sql)
            Logging.getLog().debug(u"更新命令串和步骤信息 获得%d条记录,执行SQL命令：%s" % (len(ds1), sql))
            sql = "select FUNCNAME, FUNC_BLOCK, PARAMMETER from SX_PUBLIC_FUNC_INFO where PUBLIC_FUNC_FLAG = 1"
            ds_func_info = cF.executeCaseSQL(sql)
            # ds_func_info_dict = {}
            # for func_info in ds_func_info:
            #     ds_func_info_dict.update(func_info)
            sql = '''
                                    update sx_run_record 
                                    set
                                    param_data_id = ? , 
                                    run_type = ? , 
                                    task_id = ? , 
                                    server_ip = ? , 
                                    collection_id = ?, 
                                    cases_detail_id = ? , 
                                    collection_detail_id = ? , 
                                    cases_id = ? , 
                                    cases_param_data_id = ? , 
                                    result = ? , 
                                    step = ? ,
                                    funcid = ? ,
                                    script_name = ? , 
                                    adapter_type = ? , 
                                    pre_action = ? , 
                                    pro_action = ? , 
                                    cmdstring = ? , 
                                    expected_value = ? , 
                                    account_group_id = ? ,
                                    server_type = ? ,
                                    param_index = ?,
                                  step_name=?
                                    where
                                    RUN_RECORD_ID = ?
                                '''
            update_sx_run_record_list = []
            for rec1 in ds1:
                try:
                    CASES_DETAIL_ID = rec1['CASES_DETAIL_ID']
                    PARAM_ID = rec1['PARAM_ID']
                    if PARAM_ID not in [None, 'null', ""]:
                        CASES_DETAIL_IDS_DICT[str(CASES_DETAIL_ID)] = str(PARAM_ID)
                except:
                    pass
                script_name = ""
                if rec1['INPUT_STRING'] == None:
                    script_name = ""
                else:
                    # Logging.getLog().debug(u"%s" % rec1['INPUT_STRING'])
                    script_name = self.getScriptNameFromInputString(rec1['INPUT_STRING'])

                if self._mqserver._case_db_type == 'DB2':

                    if rec1['PRE_ACTION']:
                        try:
                            pre_pro_action_list = json.loads(rec1['PRE_ACTION'].replace("$bfh$", '"'), encoding='gbk')
                            if len([i for i in pre_pro_action_list if i['PUBLIC_FUNC_FLAG'] == 1]) > 0:
                                ret, pre_pro_action = self.deal_with_public_func_block(pre_pro_action_list,
                                                                                       ds_func_info)
                                if ret == -1:
                                    pre_pro_action = pre_pro_action_list
                                rec1['PRE_ACTION'] = pre_pro_action
                        except Exception as e:
                            exc_info = cF.getExceptionInfo()
                            Logging.getLog().error(exc_info)
                    if rec1['PRO_ACTION']:
                        try:
                            pre_pro_action_list = json.loads(rec1['PRO_ACTION'].replace("$bfh$", '"'), encoding='gbk')
                            if len([i for i in pre_pro_action_list if i['PUBLIC_FUNC_FLAG'] == 1]) > 0:
                                ret, pre_pro_action = self.deal_with_public_func_block(pre_pro_action_list,
                                                                                       ds_func_info)
                                if ret == -1:
                                    pre_pro_action = pre_pro_action_list
                                rec1['PRO_ACTION'] = pre_pro_action
                        except Exception as e:
                            exc_info = cF.getExceptionInfo()
                            Logging.getLog().error(exc_info)
                    sigle_update_sx_run_record = (rec1['PARAM_DATA_ID'], rec1['RUN_TYPE'], rec1['TASK_ID'], rec1['SERVER_IP'],
                         rec1['COLLECTION_ID'], rec1['CASES_DETAIL_ID'], rec1['COLLECTION_DETAIL_ID'],
                         rec1['CASES_ID'], rec1['CASES_PARAM_DATA_ID'], rec1['RESULT'], rec1['STEP'],
                         rec1['FUNCID'], script_name, rec1['ADAPTER_TYPE'], rec1['PRE_ACTION'],
                         rec1['PRO_ACTION'], rec1['PARAM_DATA'], int(rec1['EXPECTED_VALUE']),
                         int(rec1['ACCOUNT_GROUP_ID']), rec1['SERVER_TYPE'], int(rec1['PARAM_INDEX']),
                         rec1['STEP_NAME'],
                         rec1['RUN_RECORD_ID'])
                    update_sx_run_record_list.append(sigle_update_sx_run_record)
            cF.executeCaseManySQL_DB2(sql, update_sx_run_record_list)

            #处理接口字段类型问题
            ret_i, data_i = cF.get_task_sx_interface_info(CASES_DETAIL_IDS_DICT)

            if value_list != []:
                if self._mqserver._case_db_type == 'DB2':
                    pass
                else:  # MYSQL
                    sql = "replace into sx_run_record(run_record_id,param_data_id,run_type,task_id,server_ip,collection_id,cases_detail_id,collection_detail_id,cases_id,cases_param_data_id,result,step,funcid,script_name,adapter_type,pre_action,pro_action,cmdstring,expected_value,account_group_id) values %s" % (
                        ','.join(value_list))
                    Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)

            # 建立内存数据结构
            sql = '''
               SELECT
                sx_run_record.RUN_SERVER_ALIAS_FLAG,
                    sx_run_record.RUN_SERVER_ALIAS,
                    sx_run_record.RUN_RECORD_ID
                    , sx_run_record.CASES_DETAIL_ID
                    , sx_run_record.TASK_ID
                    , sx_run_record.COLLECTION_ID
                    , sx_run_record.COLLECTION_DETAIL_ID
                    , sx_run_record.CASES_ID
                    , sx_run_record.PARAM_DATA_ID
                    , sx_run_record.CASES_PARAM_DATA_ID
                    , sx_run_record.STEP
                    , sx_run_record.STEP_NAME
                    , sx_run_record.FUNCID
                    , sx_run_record.CMDSTRING
                    , sx_run_record.ACCOUNT_GROUP_ID
                    , sx_run_record.EXPECTED_VALUE
                    , sx_run_record.SCRIPT_NAME
                    , sx_run_record.ADAPTER_TYPE
                    , CAST(sx_run_record.PRE_ACTION as VARCHAR(32672)) AS PRE_ACTION
                    , CAST(sx_run_record.PRO_ACTION as VARCHAR(32672)) AS PRO_ACTION
                    , sx_run_record.SERVER_TYPE
                    , sx_run_record.PARAM_INDEX
                    , sx_cases.CASE_NAME
                FROM
                    sx_run_record
                INNER JOIN sx_cases 
                 ON (sx_run_record.CASES_ID = sx_cases.CASES_ID)
                WHERE 
                    sx_run_record.task_id = %d AND RUN_SERVER_ALIAS_FLAG='0'
                ORDER BY sx_run_record.RUN_RECORD_ID
            ''' % (runtask_id)

            ds1 = cF.executeCaseSQL(sql)
            Logging.getLog().debug("get %d cases with SQL: %s" % (len(ds1), sql))
            order_by_cases_info = []
            cases_ids = []
            for rec1 in ds1:
                cases_ids.append(rec1['CASES_ID'])
                if rec1["CASES_ID"] in order_by_case_index.keys():
                    rec1["CASE_INDEX"] = order_by_case_index[rec1["CASES_ID"]]
                    order_by_cases_info.append(rec1)

            order_by_cases_info.sort(key=lambda x:x['CASE_INDEX'])

            in_param_legal = False  # 入参合法性字段
            sql = u"select TREE_DIRECTORY_ID from SX_FUNC_TREE_DIRECTORY where directory_name = '入参合法性校验'"
            ds_ = cF.executeCaseSQL_DB2(sql)
            c_tree_directory_id = ""
            if ds_ and ds_[0]["TREE_DIRECTORY_ID"]:
                c_tree_directory_id = ds_[0]["TREE_DIRECTORY_ID"]
            if c_tree_directory_id in cases_tree_ids.values():  # 判断入参合法性案例是否在cases_tree_ids里面
                in_param_legal = True
            run_record_id_list = []
            pre_priority_action_list = []  # 批量执行前置列表
            for rec1 in order_by_cases_info:
                interface_info = {}
                if priority_dict:
                    if rec1['CASES_ID'] in priority_dict.keys():  # priority_dict是优先执行前置案例的 cases_id: priority 对应的字典
                        rec1['PRE_ACTION'] = ''  # 将案例本身的前置置为空
                        pre_action_child = self.get_pre_list(rec1, system_id)  # 拼装前置格式并返回
                        pre_priority_action_list.append(pre_action_child)  # 加入批量执行前置列表
                if ret_i == 0:
                    try:
                        CASES_DETAIL_ID = str(rec1['CASES_DETAIL_ID'])
                        if CASES_DETAIL_ID in CASES_DETAIL_IDS_DICT.keys():
                            PARAM_ID = CASES_DETAIL_IDS_DICT[CASES_DETAIL_ID]
                            if PARAM_ID in data_i.keys():
                                interface_info = data_i[PARAM_ID]
                    except:
                        pass
                rec1['INTERFACE_INFO'] = interface_info
                cases_list.append(rec1)
                run_record_id_list.append(rec1["RUN_RECORD_ID"])

            # 修正案例个数，因为案例集中选择的案例，可能因为用户的遗漏，部分案例没有增添数据而无法执行，这样会造成用例集无法最终执行完成
            # 此处做一个workaround来避免这种情况，最终还是要在执行层面进行进行控制

            # 修改计算用例的方法，拥有单一cases_id 和cases_param_data_id为一个用例
            # cal_list = []
            case_num = 0
            if order_by_case_index:
                case_num = len(list(set(order_by_case_index.keys())))
            self._cases_task_dict[runtask_id]["case_num"] = case_num

            self._cases_task_dict[runtask_id]['cases_list'] = cases_list
            self._cases_task_send_uncomfirm_dict[runtask_id]['cases_list'] = []

            # 修改状态
            sql = "update sx_cases_collection_run_task set run_status='%s',run_start_time='%s',case_num=%d where collection_run_task_id = %d " % (
                gl.TASK_STATE_PREPARE, self._cases_task_dict[runtask_id]['run_start_time'], int(case_num),
                runtask_id)
            Logging.getLog().debug(sql)
            cF.executeCaseSQL(sql)

            # 1. 建立任务内存状态，
            timed_task_flag = 0
            if timed_task_id == "null" or timed_task_id == "":
                timed_task_flag = 1

            # -------------------上文是进行更改状态，更改数据库操作，下文进行用例数据拼接及队列发送------------------
            rs = []
            if ds_server_ids:
                # 多核心获取用例记录
                sql = "select RUN_RECORD_ID,TASK_ID,COLLECTION_DETAIL_ID,PARAM_DATA_ID,CASES_ID,CASES_DETAIL_ID," \
                      "CASES_PARAM_DATA_ID,STEP,RUN_SERVER_ALIAS,RUN_SERVER_ALIAS_FLAG from SX_RUN_RECORD where " \
                      "RUN_SERVER_ALIAS_FLAG = '1' and TASK_ID = %s" % runtask_id
                Logging.getLog().debug(sql)
                rs = cF.executeCaseSQL(sql)
                if not rs:
                    rs = []
            carry_dict = {}  # 用来存放下一步操作的数据
            carry_dict['runtask_id'] = runtask_id
            if ds_server_ids:
                carry_dict['server_ids'] = ",".join(ds_server_ids)
            else:
                carry_dict['server_ids'] = ""
            carry_dict['run_record_info'] = rs
            carry_dict['collection_id'] = collection_id
            carry_dict['collection_name'] = collection_name
            carry_dict['system_id'] = system_id
            carry_dict['case_num'] = case_num
            carry_dict['timed_task_flag'] = timed_task_flag
            carry_dict['run_record_id_list'] = run_record_id_list
            carry_dict['c[warning_info]'] = c['warning_info']
            carry_dict['rec[AGENT_ID]'] = rec['AGENT_ID']
            carry_dict['cases_list'] = cases_list
            carry_dict['c[agent_id]'] = c['agent_id']
            carry_dict['in_param_legal'] = in_param_legal  # 入参合法性字段匹配匹配操作
            # -------------------------将拼接的json进行重新拼接，由get_case_list进行处理---------------------------

            return 0, carry_dict, pre_priority_action_list
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def get_agent_info(self, rec):
        try:
            client_id = rec['AGENT_ID']
            sql = "select DEPLOY_IP, DEPLOY_PORT from SX_AGENT_INFO where agent_code = '%s'" % (str(client_id))
            ds = cF.executeCaseSQL_DB2(sql)
            agent_ip = ds[0]['DEPLOY_IP']
            agent_port = ds[0]['DEPLOY_PORT']
            pattern = '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
            flag = re.findall(pattern, agent_ip)
            if not flag or flag[0] == "127.0.0.1":
                return -1, 'err'
            # agent_ip = self._mqserver._clients_dict[client_id]["ip"]
            # agent_port = self._mqserver._clients_dict[client_id]["port"]

            return agent_ip, agent_port
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def getCasesList(self):
        '''
        查看任务表，获得测试案例的列表，直接加载到内存中，为后面的分发做准备
        '''
        try:
            sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_START'"
            ds = cF.executeCaseSQL(sql)
            if len(ds) <= 0:
                # Logging.getLog().debug(u"没有需要执行的测试任务")
                return 0, u"没有需要执行的测试任务"

            else:
                try:
                    for index, rec in enumerate(ds):  # 将任务(案例集)进行循环，将任务内部案例集进行分别分发
                        ret, carry_dict, pre_dict_all = self.getCase(index, rec)  # 拿到需要发送的案例信息
                        if pre_dict_all:  # 如果有，则拿到所有前置，先进行前置的执行
                            agent_ip, agent_port = self.get_agent_info(rec)  # 拿到agent信息
                            if agent_ip == -1:
                                msg = u'未拿到agent的ip和端口信息'
                                ret, msg = self.update_preaction_database_ip(msg, carry_dict)  # 由此进行最终数据写入操作
                                return ret, msg
                            try:
                                s = ServerProxy("http://%s:%s" % (agent_ip, agent_port))  # 调动rpc
                                tar, msg = s.pre_action_func(pre_dict_all)  # 运行rpc函数并拿到rpc调用结果
                            except:
                                exc_info = cF.getExceptionInfo()
                                Logging.getLog().error(exc_info)
                                return -1, exc_info
                            if tar == 0:  # 说明前置执行成功，继续执行后面的案例本身及案例后置
                                    # 此处是前置执行完之后，进行案例本身及后置的执行
                                ret, msg = self.redis_exec(carry_dict)  # 任务写入redis
                                if ret < 0:
                                    return ret, msg
                                ret, msg = self.rabbit_exec(carry_dict)  # rabbitmq发送
                                if ret < 0:
                                    return ret, msg
                            else:  # tar!=0 说明前置提前执行失败
                                print u'运行的错误信息 --------------->', msg
                                ret, msg = self.update_preaction_database(msg, carry_dict)  # 由此进行最终数据写入操作
                                return ret, msg
                        else:  # 如果没有标记前置则为案例本身
                            ret, msg = self.redis_exec(carry_dict)  # 任务写入redis
                            if ret < 0:
                                return ret, msg
                            ret, msg = self.rabbit_exec(carry_dict)  # rabbitmq发送
                            if ret < 0:
                                return ret, msg
                    return 0, ""
                except:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
                    return -1, exc_info
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info
    def update_preaction_database_ip(self, msg, carry_dict):
        collection_run_task_id = carry_dict['runtask_id']
        time_k = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = "update sx_cases_collection_run_task set " \
              "run_status='STATE_FINISH'," \
              "RUN_RESULT='RESULT_ALL_FAIL'," \
              "RUN_CASE_NUM_SUCCESS=0, " \
              "RUN_CASE_NUM=0," \
              "RUN_CASE_NUM_FAIL=%d," \
              "RUN_END_TIME='%s' " \
              "where collection_run_task_id = %d " % (carry_dict['case_num'], time_k, collection_run_task_id)
        ds = cF.executeCaseSQL(sql)
        for i in carry_dict['run_record_id_list']:
            sql_sx_record = "UPDATE SX_RUN_RECORD SET RESULT_MESSAGE='%s',  RUN_START_TIME='%s', " \
                            "RUN_END_TIME='%s', RESULT='STATE_FAIL'" \
                            "WHERE run_record_id=%d" \
                            % (msg, time_k, time_k, i)
            ds = cF.executeCaseSQL(sql_sx_record)
        return 0, 'ok'

    def update_preaction_database(self, test_result, carry_dict):
        """
        此函数进行最终的前置错误处理
        :param test_result:
                    testResult["result"] = "STATE_FAIL"
                    testResult["step"] = step
                    testResult["case_name"] = case["CASE_NAME"]
                    testResult["funcid"] = funcid
                    testResult["msg"] = u"步骤前置动作执行失败！%s" % str(msg_info)
                    testResult["log"] = u"步骤前置动作执行失败！%s" % str(msg_info)
                    testResult["cmdstring"] = cmdstring
                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        :return:
        """
        # 在此进行sx_cases_collection_run_task表进行更新
        try:
            collection_run_task_id = carry_dict['runtask_id']
            sql = "update sx_cases_collection_run_task set " \
                  "run_status='STATE_FINISH'," \
                  "RUN_RESULT='RESULT_ALL_FAIL'," \
                  "RUN_CASE_NUM_SUCCESS=0, " \
                  "RUN_CASE_NUM=0," \
                  "RUN_CASE_NUM_FAIL=1," \
                  "RUN_END_TIME='%s' " \
                  "where collection_run_task_id = %d " % (test_result["run_end_time"], collection_run_task_id)
            ds = cF.executeCaseSQL(sql)
            print u'前置批量运行失败sql: ', sql
            print
            print u'用例所有数据如下  --> ', carry_dict['run_record_id_list']  # 拿到所有的运行record数据
            print
            for i in carry_dict['run_record_id_list']:
                if test_result['run_record_id'] == i:
                    sql_sx_record = "UPDATE SX_RUN_RECORD SET RESULT_MESSAGE='%s',  RUN_START_TIME='%s', " \
                                    "RUN_END_TIME='%s', step_name='%s', RESULT='STATE_FAIL'" \
                                    "WHERE run_record_id=%d" \
                                    % (test_result["msg"].split('!!!')[0], test_result['run_end_time'],
                                       test_result['run_end_time'], test_result['step'], test_result['run_record_id'])

                else:
                    sql_sx_record = "UPDATE SX_RUN_RECORD SET RESULT_MESSAGE='%s',  RUN_START_TIME='%s', " \
                                    "RUN_END_TIME='%s', RESULT='STATE_FAIL'" \
                                    "WHERE run_record_id=%d" \
                                    % (u'已经被跳过', test_result['run_end_time'],
                                       test_result['run_end_time'], i)

                ds = cF.executeCaseSQL(sql_sx_record)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def chg_carry_dict(self, carry_dict):  # 从每个案例中抽取不需要的前置信息
        try:
            s = carry_dict['cases_list']
            for i in range(len(s)):
                cases_id = s[i]['CASES_ID']  # 拿到当前案例的id
                if cases_id == "" or cases_id == None or cases_id == "null" or cases_id == "(null)":
                    continue
                sql_str = 'select PRIORITY from sx_cases where cases_id = {}'.format(cases_id)  # 拿到案例的优先执标识符
                tag = cF.executeCaseSQL(sql_str)
                if tag[0]['PRIORITY'] == 1:
                    carry_dict['cases_list'][i]['PRE_ACTION'] = u''
            return carry_dict
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def judje_key(self, rec):
        # 此代码是用来获取任务(案例集)中的优先执行前置字段，然后返回判断的结果
        try:
            # count = 0
            p_list = []
            collection_id = rec['COLLECTION_ID']
            sql = "select cases_id from SX_CASES_COLLECTION_DETAIL where collection_id = {}".format(collection_id)
            ds_list = cF.executeCaseSQL_DB2(sql)
            # print u'优先执行判断 -->  start'
            if not ds_list:
                # count = count + 1
                # if count > 500:
                return 0, ''
            for pre_action in ds_list:
                p_list.append(str(pre_action['CASES_ID']))
            #     if cases_id == "" or cases_id == None or cases_id == "null" or cases_id == "(null)":
            pre_action_all_list = [p_list[i:i + 1000] for i in range(0, len(p_list), 1000)]
            for pre_action in pre_action_all_list:
                p_list_str = ",".join(pre_action)
                sql_case = "select count(PRIORITY) as num from sx_cases where cases_id in (%s) and PRIORITY!=''" % p_list_str

                col_id_list = cF.executeCaseSQL_DB2(sql_case)
                if col_id_list in col_id_list[0]['num']:
                    return 1, ''
            #     else:
            #         continue
            # print u'优先执行判断 -->  end'
            # return 0, ""
            return 0, ''
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def redis_exec(self, carry_dict):
        try:
            ret, msg = self._mqserver._redis_client.add_new_task_to_redis(carry_dict['runtask_id'],
                                                                          carry_dict['collection_id'],
                                                                          carry_dict['collection_name'],
                                                                          carry_dict['system_id'],
                                                                          carry_dict['case_num'],
                                                                          carry_dict['timed_task_flag'],
                                                                          carry_dict['run_record_id_list'],
                                                                          json.dumps(carry_dict['c[warning_info]'],
                                                                                     ensure_ascii=False),
                                                                          carry_dict['rec[AGENT_ID]'])
            if ret < 0:
                return ret, msg
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def rabbit_exec(self, carry_dict):
        try:  # carry_dict['server_ids']
            ret, msg = self.new_task_distribute(carry_dict['run_record_info'], carry_dict['server_ids'],
                                                carry_dict['runtask_id'],
                                                carry_dict['system_id'],
                                                carry_dict['run_record_id_list'], carry_dict['cases_list'],
                                                carry_dict['c[agent_id]'], carry_dict['in_param_legal'])
            if ret < 0:
                return ret, msg

            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def get_pre_list(self, rec1, system_id):  # 此函数是用来取出前置数据

        try:

            case_dict = {}

            case_dict['cases_id'] = rec1['CASES_ID']  # 案例id

            case_dict['step'] = rec1['STEP']

            case_dict['case_name'] = rec1['CASE_NAME']

            case_dict['system_id'] = system_id

            case_dict['account_group_id'] = rec1['ACCOUNT_GROUP_ID']

            case_dict['funcid'] = rec1['FUNCID']  # funcid

            case_dict['cmdstring'] = rec1['CMDSTRING']

            case_dict['run_record_id'] = rec1['RUN_RECORD_ID']

            case_dict['step_name'] = rec1['STEP_NAME']

            return case_dict

        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def handle_test_result_in_redis(self):
        """
        每秒钟执行一次，将redis的数据同步到用例数据库

        :return:
        """
        begin_time = datetime.datetime.now()
        while (gl.is_exit_all_thread != True):
            try:
                # 读取清算开账户的数据
                try:
                    ag = HandleAccountGroup.HandleAccountGroup(self)
                    ag.handle()
                    ag = None
                except Exception as e:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
                    Logging.getLog().error("read HandleAccountGroup error, please have a check")
                # last_time = datetime.datetime.now()
                # if (last_time - begin_time).seconds > 4:
                self.handle_count_tasks_unfinish_cases()
                # begin_time = last_time
                ####################################更新用例的agentid信息######################
                ret, agent_id_data_list = self._mqserver._redis_client.get_agent_id_data_list()
                if ret == 0:
                    Logging.getLog().debug("agent_id_data_list=%s" % (agent_id_data_list))
                    for agent_info_str in agent_id_data_list:
                        agent_id_data_list = json.loads(agent_info_str)
                        run_record_id_agent_ids = []
                        for agent_info in agent_id_data_list:
                            param = (agent_info["agent_id"], agent_info["RUN_RECORD_ID"])
                            run_record_id_agent_ids.append(param)
                        if run_record_id_agent_ids:
                            sql_agent_id = "update sx_run_record set AGENT_ID=?  where RUN_RECORD_ID = ?"
                            cF.executeCaseManySQL_DB2(sql_agent_id, run_record_id_agent_ids)
                ####################################账户组更新#################################
                ret, account_list = self._mqserver._redis_client.get_account_data_list()
                if ret == 0:
                    for account_dict_str in account_list:
                        account_dict = json.loads(account_dict_str)
                        account_system_id = account_dict['account_system_id']
                        account_data = account_dict['account_data']
                        account_id = account_dict['account_id']
                        case_adapter_type = account_dict['case_adapter_type']
                        try:
                            self._mqserver.asyncupdate_account_group_info(account_system_id, account_data, account_id, case_adapter_type)
                        except Exception as e:
                            pass
                ret, curr_task_list = self._mqserver._redis_client.read_curr_task_list()
                if ret < 0:
                    time.sleep(1)
                    continue

                now = datetime.datetime.now()

                # 批量更新结果集
                sx_run_record_sql = "update sx_run_record set RESULT= ? ,CMDSTRING=? ,RESULT_MESSAGE=? ,RUN_USER=?,ATTACHMENT=?, RUN_START_TIME = ?, RUN_END_TIME = ?,EXT_MESSAGE=?,DATA_CHANGE_INFO=? where RUN_RECORD_ID = ?"
                sx_run_record_list = []

                run_task_sql = "update sx_cases_collection_run_task set INIT_STATE=?, INIT_MSG=? where COLLECTION_RUN_TASK_ID=?"
                run_task_list = []

                # sx_agent_info_sql = "update sx_agent_info set STATE=?, LAST_ALIVE=? where AGENT_CODE=?"
                sx_agent_info_sql = "update sx_agent_info set LAST_ALIVE=? where AGENT_CODE=?"
                sx_agent_info_list = []

                # 记录case信息
                run_record_id_dict = {}
                # 记录任务信息
                task_record_id_set_dict = {}
                # 记录任务信息
                task_info_dict = {}

                # 记录用例执行成功情况
                case_run_dict = {}  # {TASK_ID:{CASES_PARAM_DATA_ID:'STATE_SUCC'}}

                # 记录任务和system_id 对应关系
                task_system_dict = {}

                # 运行完毕的结果数
                case_result_count = 0

                for task_id in curr_task_list:

                    run_record_id_dict[task_id] = []

                    case_run_dict[task_id] = {}

                    ret, task_info_list = self._mqserver._redis_client.read_task_info(task_id)
                    if ret < 0:
                        continue
                    task_record_id_set, task_init_state_dict, case_result_dict, task_info_local_dict = task_info_list

                    task_record_id_set_dict[task_id] = task_record_id_set

                    task_info_dict[task_id] = task_info_local_dict

                    case_result_count += len(case_result_dict.keys())

                    if task_init_state_dict["SYNC_FLAG"] == "FALSE" and task_init_state_dict[
                        "INIT_STATE"] != "STATE_UNINIT":
                        run_task_list.append(
                            (task_init_state_dict["INIT_STATE"], task_init_state_dict["INIT_MSG"], task_id))

                    system_id = task_init_state_dict["SYSTEM_ID"]

                    task_system_dict[task_id] = system_id

                    for run_record_id in case_result_dict.keys():
                        run_record_id_dict[task_id].append(run_record_id)

                        result_str = case_result_dict[run_record_id]

                        # result = json.loads(result_str)
                        result = self.eval_json_data(result_str)

                        return_json_string = result["return_message"]
                        data_change_info_json_string = result["data_change_info"]

                        if result["CASES_PARAM_DATA_ID"] not in case_run_dict[task_id].keys():
                            case_run_dict[task_id][result["CASES_PARAM_DATA_ID"]] = result["result"]
                        else:
                            if result['result'] == 'STATE_FAIL' or result['result'] == 'STATE_SKIP':
                                case_run_dict[task_id][result["CASES_PARAM_DATA_ID"]] = 'STATE_FAIL'

                        # if system_id in (
                        #         "142891090059622AV2", "1523514095162K1QR6", "1481617036190F5IU8", "142890425731984KH9",
                        #         "1428908551835S0NXP",
                        #         "142891263425277DZ1"):
                        try:
                            self.AddCasesRunningResult(task_id, result)
                        except Exception as e:
                            pass
                        try:
                            # if system_id == "1490844074559VS0IY":
                            return_json_string['message'] = return_json_string['message'].encode("gbk")
                            for j in return_json_string['values_list']:
                                for index, i in enumerate(j):
                                    if isinstance(i, unicode):
                                        # print 'enter'
                                        j[index] = i.encode("gbk")
                            try:
                                return_json_string_str = json.dumps(return_json_string, ensure_ascii=False)
                            except BaseException, ex:
                                return_json_string_str = json.dumps(return_json_string, ensure_ascii=False,
                                                                    encoding="gbk")
                                # return_json_string_str = json.dumps(return_json_string, sort_keys=True, indent=4,
                                #                                     ensure_ascii=False, encoding="gbk",
                                #                                     separators=(',', ':'))
                        except BaseException, ex:
                            return_json_string_str = str(return_json_string).encode("gbk")

                        if not return_json_string_str or return_json_string_str == 'null':
                            return_json_string_str = ""
                        if not data_change_info_json_string or data_change_info_json_string == 'null':
                            data_change_info_json_string = ""
                        if not result["cmdstring"] or result["cmdstring"] == 'null':
                            result["cmdstring"] = ""
                        else:
                            try:
                                result["cmdstring"] = MySQLdb.escape_string(
                                    result['cmdstring'].replace("&bfb&", "#").replace("&bft&", "=")).decode("utf-8")
                            except Exception as e:
                                result["cmdstring"] = MySQLdb.escape_string(
                                    result['cmdstring'].replace("&bfb&", "#").replace("&bft&", "="))
                        if not result["log"] or result["log"] == 'null':
                            result["log"] = ""

                        param = (result['result'],
                                 result['cmdstring'],
                                 result['log'].replace("'", "''"), str(result['run_user']),
                                 result['attachment'], result['run_start_time'], result['run_end_time'],
                                 return_json_string_str.replace('\n', '').replace(' ', ''),
                                 data_change_info_json_string.replace("'", "''"), int(result['RUN_RECORD_ID']))

                        sx_run_record_list.append(param)

                if sx_run_record_list:
                    cF.executeCaseManySQL_DB2(sx_run_record_sql, sx_run_record_list)
                    for task_id in run_record_id_dict.keys():
                        self._mqserver._redis_client.remove_case_result(task_id, run_record_id_dict[task_id])

                if run_task_list:
                    cF.executeCaseManySQL_DB2(run_task_sql, run_task_list)
                    for item in run_task_list:
                        self._mqserver._redis_client.send_env_init_result_back_to_redis("", item[2], item[0], item[1],
                                                                                        'TRUE')

                if case_result_count > 0:
                    case_run_sql = "update sx_cases_collection_run_task set RUN_CASE_NUM=?, RUN_CASE_NUM_SUCCESS=?, RUN_CASE_NUM_FAIL=? where COLLECTION_RUN_TASK_ID=?"
                    case_run_list = []
                    for task_id in case_run_dict.keys():
                        # 处理执行情况信息
                        pass_count = int(task_info_dict[task_id]["run_case_num_success"])
                        fail_count = int(task_info_dict[task_id]["run_case_num_fail"])
                        pass_count = 0
                        fail_count = 0
                        total_num = 0
                        sql = "select distinct CASES_ID from SX_RUN_RECORD where TASK_ID =%s" % task_id
                        Logging.getLog().debug(sql)
                        rs = cF.executeCaseSQL(sql)
                        total_num = len(rs)

                        sql = """select distinct CASES_ID from SX_RUN_RECORD where TASK_ID = %s and CASES_ID in (select CASES_ID 
from ( select CASES_ID, count( c.CASES_ID) as num from(select CASES_ID,count(RESULT) RESULT from SX_RUN_RECORD 
where TASK_ID = %s group by CASES_ID,RESULT) c group by c.CASES_ID ) cc where cc.num =1) and result = 'STATE_PASS'
                        """ % (task_id, task_id)
                        Logging.getLog().debug(sql)
                        rs = cF.executeCaseSQL(sql)
                        pass_count = len(rs)

                        sql = """select distinct CASES_ID from SX_RUN_RECORD where TASK_ID = %s and CASES_ID in (select CASES_ID 
                        from ( select CASES_ID, count( c.CASES_ID) as num from(select CASES_ID,count(RESULT) RESULT from SX_RUN_RECORD 
                        where TASK_ID = %s group by CASES_ID,RESULT) c group by c.CASES_ID ) cc where cc.num =1) and result = 'STATE_UNTEST'
                                                """ % (task_id, task_id)
                        Logging.getLog().debug(sql)
                        rs = cF.executeCaseSQL(sql)
                        untest_count = len(rs)

                        fail_count = total_num - pass_count - untest_count
                        # for key in case_run_dict[task_id].keys():
                        #     if case_run_dict[task_id][key] == 'STATE_PASS':
                        #         pass_count += 1
                        #     else:
                        #         fail_count += 1

                        task_info_dict[task_id]["run_case_num_success"] = pass_count
                        task_info_dict[task_id]["run_case_num_fail"] = fail_count

                        case_run_list.append((pass_count + fail_count, pass_count, fail_count, task_id))

                    if case_run_list:
                        print "cbs"
                        print case_run_list
                        cF.executeCaseManySQL_DB2(case_run_sql, case_run_list)
                    for item in case_run_list:
                        self._mqserver._redis_client.modify_task_info(item[3], run_case_num=item[0],
                                                                      run_case_num_success=item[1],
                                                                      run_case_num_fail=item[2])

                ## 判断是否需要报警
                for task_id in case_run_dict.keys():
                    warning_str = task_info_dict[task_id]["warning_info"]
                    warning_dict = json.loads(warning_str)
                    if warning_dict.has_key(2):  # 是否有案例运行比例告警
                        pass_count = task_info_dict[task_id]["run_case_num_success"]
                        fail_count = task_info_dict[task_id]["run_case_num_fail"]
                        if (pass_count + fail_count >= int(gl.g_ZHLCSystemSetting["WarningInfoMinCasesNum"])):
                            # 总的执行数量超过了最低限制
                            fail_ratio = int(fail_count * 100 / (pass_count + fail_count))
                            if fail_ratio >= int(warning_dict[2]['warning_val']):
                                warning_type = 'EMAIL'
                                if warning_dict[1]['warning_type'] == '2':
                                    warning_type = 'MOBILE'

                                sql = '''insert into sx_warning_info
                                                    (
                                                    TASK_ID,
                                                    COLLECTION_ID,
                                                    WARNING_ID,
                                                    WARNING_MSG,
                                                    WARNING_WAY,
                                                    SEND_STATE,
                                                    EMAIL_LIST,
                                                    MOBILE_LIST
                                                    )
                                                    values
                                                    (
                                                    %d,
                                                    %d,
                                                    1,
                                                    '%s',
                                                    '%s',
                                                    'STATE_UNSEND',
                                                    '%s',
                                                    '%s'
                                                    );
                                                  ''' % (int(task_id), task_info_dict[task_id]['collection_id'],
                                                         u"自动化任务%d案例失败率超过百分之%d，请做相关处理" % (
                                                                                                   int(task_id),
                                                                                                   int(warning_dict[2][
                                                                                                           'warning_val'])),
                                                         warning_type,
                                                         MySQLdb.escape_string(warning_dict[1]['warning_email']),
                                                         warning_dict[1]['warning_tel'])
                                Logging.getLog().debug(sql)
                                cF.executeCaseSQL(sql)
                                warning_dict.pop(2)  # 移除告警，报警一次即可
                                self._mqserver._redis_client.modify_task_info(task_id,
                                                                              warning_info=json.dumps(warning_dict,
                                                                                                      ensure_ascii=False))

                run_task_sql = "update sx_cases_collection_run_task set run_status=?,run_result=?,run_start_time=?,run_end_time=?,run_during_time=? where collection_run_task_id=?"
                run_task_sql_list = []

                for task_id in task_record_id_set_dict.keys():
                    if len(task_record_id_set_dict[task_id]) == 0:

                        system_id = task_system_dict[task_id]

                        ### 处理任务执行完毕之后的相关工作

                        # 上传日志


                        ## 更新任务运行状态



                        run_start_time = task_info_dict[task_id]["run_start_time"]
                        run_end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # 计算运行状态
                        run_result = ""
                        pass_count = int(task_info_dict[task_id]["run_case_num_success"])
                        fail_count = int(task_info_dict[task_id]["run_case_num_fail"])
                        Logging.getLog().debug("cancel_flag is %s" % str(task_info_dict[task_id]["cancel_flag"]))
                        if str(task_info_dict[task_id]["cancel_flag"]) == '1':
                            run_result = "RESULT_CANCEL"
                            Logging.getLog().debug("run_result is RESULT_CANCEL")
                        else:
                            if pass_count == 0:
                                run_result = "RESULT_ALL_FAIL"
                            elif fail_count == 0:
                                run_result = "RESULT_ALL_PASS"
                            else:
                                run_result = "RESULT_PARTIAL_PASS"

                        run_task_sql_list.append(('STATE_FINISH', run_result, run_start_time, run_end_time, str(
                            datetime.datetime.strptime(run_end_time, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                                run_start_time, '%Y-%m-%d %H:%M:%S')), task_id))

                        ## 判断是否案例全部运行完毕提示
                        warning_str = task_info_dict[task_id]["warning_info"]
                        warning_dict = json.loads(warning_str)

                        collection_id = task_info_dict[task_id]['collection_id']
                        sql = "select COLLECTION_NAME from SX_CASES_COLLECTION where COLLECTION_ID=%s" % collection_id
                        rs = cF.executeCaseSQL(sql)
                        COLLECTION_NAME = ""
                        try:
                            if rs:
                                COLLECTION_NAME = rs[0]["COLLECTION_NAME"]
                        except Exception as e:
                            pass
                        if warning_dict.has_key(5):  # 是否有案例全部运行完毕提示
                            warning_type = 'EMAIL'
                            if warning_dict[5]['warning_type'] == '2':
                                warning_type = 'MOBILE'
                            sql = '''insert into sx_warning_info
                                                    (
                                                    TASK_ID,
                                                    COLLECTION_ID,
                                                    WARNING_ID,
                                                    WARNING_MSG,
                                                    WARNING_WAY,
                                                    SEND_STATE,
                                                    EMAIL_LIST,
                                                    MOBILE_LIST
                                                    )
                                                    values
                                                    (
                                                    %d,
                                                    %d,
                                                    5,
                                                    '%s',
                                                    '%s',
                                                    'STATE_UNSEND',
                                                    '%s',
                                                    '%s'
                                                    );
                                                    ''' % (int(task_id), task_info_dict[task_id]['collection_id'],
                                                           u"自动化任务%s执行完毕，任务状态：%s，案例总数：%s，总执行数：%s，案例成功数：%s，案例失败数%s。请予以关注，谢谢！" % (
                                                                                                 u"[" + COLLECTION_NAME + u"(" + u"系统ID:" +
                                                                                                 task_info_dict[
                                                                                                     task_id][
                                                                                                     'system_id'] + "," + u"任务ID:" + str(
                                                                                                     task_id) + u")" + u"]",
                                                                                                 u"执行完毕" + u"(" + "STATE_FINISH" + u")",
                                                                                                 str(task_info_dict[
                                                                                                         task_id][
                                                                                                         'cases_num']),
                                                                                                 str(
                                                                                                     pass_count + fail_count),
                                                                                                 str(pass_count),
                                                                                                 str(fail_count)),
                                                           warning_type,
                                                           MySQLdb.escape_string(warning_dict[5]['warning_email']),
                                                           warning_dict[5]['warning_tel'])
                            Logging.getLog().debug(sql)
                            cF.executeCaseSQL(sql)
                            warning_dict.pop(5)  # 移除告警，报警一次即可
                            self._mqserver._redis_client.modify_task_info(task_id, warning_info=json.dumps(warning_dict,
                                                                                                           ensure_ascii=False))

                        ## 写入测试报告
                        if task_info_dict[task_id]["timed_task_flag"] == 0:
                            report_title = u"%s/%s/%s/手动/%s" % (
                                COLLECTION_NAME,
                                str(pass_count),
                                str(fail_count),
                                task_info_dict[task_id]["run_start_time"]
                            )
                            sql2 = "update sx_collection_test_report " \
                                   "set REPORT_TITLE='%s'," \
                                   "REPORT_TIME='%s' " \
                                   "where COLLECTION_RUN_TASK_ID=%s" % (report_title,
                                                                        task_info_dict[task_id]["run_start_time"],
                                                                        str(task_id))
                        else:
                            report_title = u"%s/%s/%s/自动/%s" % (
                                COLLECTION_NAME,
                                str(pass_count),
                                str(fail_count),
                                task_info_dict[task_id]["run_start_time"]
                            )
                            sql2 = "update sx_collection_test_report " \
                                   "set REPORT_TITLE='%s'," \
                                   "REPORT_TIME='%s' " \
                                   "where COLLECTION_RUN_TASK_ID=%s" % (report_title,
                                                                        task_info_dict[task_id]["run_start_time"],
                                                                        str(task_id)
                                                                        )
                        Logging.getLog().debug(sql2)
                        cF.executeCaseSQL(sql2)
                        try:
                            # 上传日志
                            f = XFer(self._mqserver._setting["FTPServer"]["IP"], gl.gl_ftp_info['FTPServer']['USER'], gl.gl_ftp_info['FTPServer']['PASSWORD'], '.',
                                     self._mqserver._setting["FTPServer"]["PORT"])
                            f.login()
                            # if system_id in ("14774643386617P4VW", "1481879345901LDJNJ"):
                            f.download_files('.\\logs\\%s' % str(task_id), r'.\\Log\\%s' % str(task_id))
                            if os.path.exists('.\\logs\\%s' % str(task_id)):
                                shutil.make_archive('.\\logs\\%s' % str(task_id), 'zip', r'.\\logs\\%s' % str(task_id))
                                f.upload_file_ex('./logs/%s.zip' % str(task_id), '/Log')
                        except:
                            exc_info = cF.getExceptionInfo()
                            Logging.getLog().error(exc_info)
                        # 任务跑完了， 从内存中移除
                        Logging.getLog().debug("del task info task_id:%s" % str(task_id))
                        self._mqserver._redis_client.del_task(task_id)
                        try:
                            sql_java_interface = "select PT_TAG from SX_CASES_COLLECTION_RUN_TASK where COLLECTION_RUN_TASK_ID = %s" % task_id
                            ds = cF.executeCaseSQL_DB2(sql_java_interface)
                            pt_tag = ds[0]['PT_TAG']
                            if pt_tag:
                                ret, data = cF.trans_web_interface(task_id, pt_tag)  # 调用java接口入口
                                print ret, data
                        except Exception as e:
                            print e
                            pass
                if run_task_sql_list:
                    Logging.getLog().debug(run_task_sql)
                    cF.executeCaseManySQL_DB2(run_task_sql, run_task_sql_list)

                # 读取agent状态
                ret, agent_state_dict = self._mqserver._redis_client.get_heartbeat_info()
                if ret == 0:
                    time_times = int(time.time())
                    if not gl.g_origin_agent_info:
                        for agent_id in agent_state_dict.keys():
                            state_info_str = agent_state_dict[agent_id]
                            state_dict = json.loads(state_info_str)
                            state_dict["time_times"] = time_times
                            gl.g_origin_agent_info[agent_id] = state_dict
                    else:
                        for agent_id in agent_state_dict.keys():
                            state_info_str = agent_state_dict[agent_id]
                            state_dict = json.loads(state_info_str)
                            last_alive = state_dict["last_alive"]
                            state = state_dict["state"]
                            if  agent_id in gl.g_origin_agent_info.keys() and time_times - gl.g_origin_agent_info[agent_id]['time_times'] >=5:
                                if gl.g_origin_agent_info[agent_id]['last_alive'] == last_alive:
                                    gl.g_origin_agent_info[agent_id]['state'] = 'STATE_EXCEPTION'
                                else:
                                    gl.g_origin_agent_info[agent_id]["time_times"] = time_times
                                    gl.g_origin_agent_info[agent_id]["last_alive"] = last_alive
                                    gl.g_origin_agent_info[agent_id]["state"] = state
                if ret == 0:
                    for agent_id in agent_state_dict.keys():
                        state_info_str = agent_state_dict[agent_id]
                        state_dict = json.loads(state_info_str)
                        if state_dict['state'] == "STATE_REGISTER" or state_dict["state"] == "STATE_UPDATE" or \
                                        state_dict["state"] == "STATE_UNKNOWN":
                            # sx_agent_info_list.append((state_dict["state"], state_dict["last_alive"], str(agent_id)))
                            sx_agent_info_list.append((state_dict["last_alive"], str(agent_id)))
                            sx_agent_info_sql_copy = "update sx_agent_info set STATE = '%s' where AGENT_CODE = '%s'" % (
                                state_dict['state'], str(agent_id))
                            ds = cF.executeCaseSQL_DB2(sx_agent_info_sql_copy)
                        else:
                            sx_agent_info_list.append((state_dict["last_alive"], str(agent_id)))

                    if len(sx_agent_info_list) > 0:
                        # Logging.getLog().debug(sx_agent_info_sql)
                        cF.executeCaseManySQL_DB2(sx_agent_info_sql, sx_agent_info_list)

                time.sleep(1)
            except:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().error(exc_info)
                continue

    def new_task_distribute(self, run_record_info, server_ids, runtaskid, system_id, run_record_id_list, cases_list,
                            agent_list, in_param_legal):
        """
        下发任务到队列
        :param runtaskid:
        :param system_id:
        :param run_record_id_list:
        :param cases_list:
        :param agent_list: agent 列表
        :return:
        """
        all_case_distribute_list = []  # 设定最终需要发送的数据列表
        # if in_param_legal:
        #     ret, all_case_distribute_list = self.process_queue_msg_in_param_legal(run_record_info, server_ids, runtaskid, system_id, cases_list)
        #     if ret < 0:
        #         return ret, all_case_distribute_list
        # else:
        ret, all_case_distribute_list = self.process_queue_msg(run_record_info, server_ids, runtaskid, system_id,
                                                           cases_list, in_param_legal)
        if ret < 0:
            return ret, all_case_distribute_list

        try:
            count = int(len(all_case_distribute_list))
            agent_list.sort()
            self._mqserver._task_agent_dict[runtaskid] = agent_list
            new_queue_name = "task_distribute_queue[%s]" % ",".join(agent_list)

            for agent_id in agent_list:
                public_new_task_msg = copy.copy(gl.public_new_task_msg)
                public_new_task_msg["msg_body"]["task_id"] = runtaskid
                public_new_task_msg["msg_body"]["queue_name"] = new_queue_name

                cmd_queue_name = "cmd_queue_%s" % str(agent_id)
                Logging.getLog().info("execute cmd_queue_name: %s" % str(cmd_queue_name))
                public_new_task_msg_str = ""
                try:
                    public_new_task_msg_str = json.dumps(public_new_task_msg, ensure_ascii=False)
                except:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
                    Logging.getLog().info("public_new_task_msg error")
                    public_new_task_msg_str = str(public_new_task_msg)
                try:
                    self._mqserver.send_msg_to_queue(public_new_task_msg_str, cmd_queue_name)
                except:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
            ## 下发环境初始化
            init_env_msg = copy.copy(gl.init_env_msg)
            init_env_msg["msg_body"]["task_id"] = str(runtaskid)
            init_env_msg['msg_body']['env'] = system_id
            init_env_msg['msg_body']['type'] = "0"
            Logging.getLog().info("execute new_queue_name: %s" % str(new_queue_name))
            init_env_msg_str = ""
            try:
                init_env_msg_str = json.dumps(init_env_msg, ensure_ascii=False)
            except:
                f = open("init_env_msg_%s" % str(time.time()), "w+")
                f.write(str(init_env_msg))
                f.close()
                exc_info = cF.getExceptionInfo()
                Logging.getLog().error(exc_info)
                Logging.getLog().info("init_env_msg error")
                init_env_msg_str = str(init_env_msg)
            try:
                self._mqserver.send_msg_to_queue(init_env_msg_str, new_queue_name)
            except:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().error(exc_info)
            ## 下发用例
            for i in xrange(count):
                case_distribute_list_str = ""
                try:
                    case_distribute_list_str = json.dumps(all_case_distribute_list[i], ensure_ascii=False)
                except:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
                    Logging.getLog().info("case_distribute_list[i] error")
                    case_distribute_list_str = str(all_case_distribute_list[i])
                try:
                    self._mqserver.send_msg_to_queue(case_distribute_list_str, new_queue_name)
                except:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)

            return -1, exc_info

    def process_queue_msg(self, run_record_info, server_ids, runtaskid, system_id, case_list, in_param_legal):
        """
        处理成适合入队列的用例下发消息
        :param case_list:
        :return:
        """

        case_count = len(case_list)
        case_distibute_list = []

        next_case = None
        case_to_send_list = []

        ret = None
        rs = ""

        # if system_id == '14774643386617P4VW':
        ret, rs = self._mqserver.get_sx_cases_collection_detail_info(runtaskid)
        if ret != 0:
            Logging.getLog().error("fail to get_sx_cases_collection_detail_info")

        while case_list != []:

            if next_case == None:
                case = case_list.pop(0)
                case_to_send_list.append(case)
            else:
                case = next_case

            while case_list != []:
                next_case = case_list.pop(0)
                if next_case['CASES_PARAM_DATA_ID'] == case["CASES_PARAM_DATA_ID"]:
                    case_to_send_list.append(next_case)
                else:
                    case_distribute_msg = copy.deepcopy(gl.case_distribute_msg)
                    case_distribute_msg['server_ids'] = server_ids
                    case_distribute_msg['run_record_info'] = run_record_info
                    case_distribute_msg["msg_body"]["runTaskid"] = runtaskid
                    case_distribute_msg["msg_body"]["system_id"] = system_id
                    case_distribute_msg["msg_body"]['in_param_legal'] = in_param_legal
                    case_to_send_list.sort(key=lambda x: x['STEP'])
                    case_distribute_msg["msg_body"]["cases"] = case_to_send_list
                    # if system_id == '14774643386617P4VW':
                    case_distribute_msg["excel_data"] = rs
                        # ret, rs = self._mqserver.get_sx_cases_collection_detail_info(runtaskid)
                        # if ret == 0:
                        #     case_distribute_msg["excel_data"] = rs
                        # else:
                        #     Logging.getLog().error("fail to get_sx_cases_collection_detail_info")
                    case_distibute_list.append(case_distribute_msg)

                    case_to_send_list = []
                    case_to_send_list.append(next_case)
                    break
        case_distribute_msg = copy.copy(gl.case_distribute_msg)
        case_distribute_msg['server_ids'] = server_ids
        case_distribute_msg['run_record_info'] = run_record_info
        case_distribute_msg["msg_body"]["runTaskid"] = runtaskid
        case_distribute_msg["msg_body"]["system_id"] = system_id
        case_distribute_msg["msg_body"]['in_param_legal'] = in_param_legal
        case_to_send_list.sort(key=lambda x: x['STEP'])
        case_distribute_msg["msg_body"]["cases"] = case_to_send_list
        # if system_id == '14774643386617P4VW':
        case_distribute_msg["excel_data"] = rs
            # ret, rs = self._mqserver.get_sx_cases_collection_detail_info(runtaskid)
            # if ret == 0:
            #     case_distribute_msg["excel_data"] = rs
            # else:
            #     Logging.getLog().error("fail to get_sx_cases_collection_detail_info")
        case_distibute_list.append(case_distribute_msg)
        if in_param_legal:
            try:
                result_case_distibute_list = []
                new_case_distibute_list = [case_distibute_list[i:i + 100] for i in range(0, len(case_distibute_list), 100)]
                for c_case_distibute_list in new_case_distibute_list:
                    root_case_distibute_dict = c_case_distibute_list.pop(0)
                    for case_distibute in c_case_distibute_list:
                        root_case_distibute_dict["msg_body"]["cases"].extend(case_distibute["msg_body"]["cases"])
                    result_case_distibute_list.append(root_case_distibute_dict)
                return 0, result_case_distibute_list
            except Exception as e:
                pass
        return 0, case_distibute_list
    def process_queue_msg_in_param_legal(self, run_record_info, server_ids, runtaskid, system_id, case_list):
        """
                处理成适合入队列的用例下发消息
                :param case_list:
                :return:
                """
        case_distibute_list = []
        case_distribute_msg = copy.copy(gl.case_distribute_msg)
        case_distribute_msg['server_ids'] = server_ids
        case_distribute_msg["msg_body"]['in_param_legal'] = True
        case_distribute_msg['run_record_info'] = run_record_info
        case_distribute_msg["msg_body"]["runTaskid"] = runtaskid
        case_distribute_msg["msg_body"]["system_id"] = system_id
        case_distribute_msg["msg_body"]["cases"] = case_list
        case_distibute_list.append(case_distribute_msg)
        return 0, case_distibute_list

    def deal_with_public_func_block(self, pre_pro_action_list, ds_func_info_dict):
        '''若前后置包含公共函数, 则进行转换成具体的函数模块'''
        try:
            pre_pro_action_new_list = []
            for pre_pro in pre_pro_action_list:
                if pre_pro['PUBLIC_FUNC_FLAG'] == 1:
                    content = pre_pro["content"]
                    for ds_func_info in ds_func_info_dict:
                        FUNCNAME = ds_func_info["FUNCNAME"].strip()

                        if str(FUNCNAME.split("(")[0]) == str(content.split("(")[0]):
                            funcblocklist = json.loads(ds_func_info["FUNC_BLOCK"])
                            # {"in_param": {"random_name": "\u968f\u673a\u6570\u540d\u79f0", " num": "\u968f\u673a\u6570\u957f\u5ea6"}, "out_param": {}}
                            PARAMMETER = json.loads(ds_func_info["PARAMMETER"])
                            in_params = PARAMMETER['in_param'].keys()
                            params = content.split("(")[1].replace(")", "").strip()
                            group_dict = {}
                            for fb in funcblocklist:
                                if in_params and params:
                                    params = params.split(",")
                                    in_params = ["@%s@" % in_param for in_param in in_params]
                                    if len(params) == len(in_params):
                                        group_dict = dict(zip(in_params, params))
                                if group_dict:
                                    for g in group_dict:
                                        content = fb["content"]
                                        value = ""
                                        if not group_dict[g] or group_dict[g] == 'null':
                                            value = ""
                                        else:
                                            value = group_dict[g]
                                        content = content.replace(g, value)
                                        fb["content"] = content
                                pre_pro_action_new_list.append(fb)
                            break
                else:
                    pre_pro_action_new_list.append(pre_pro)
            pre_pro_action = json.dumps(pre_pro_action_new_list)
            return 0, pre_pro_action
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info


            # def generate_account_group_xml(self, system_id, sign):
            #     '''数据库查询账户信息'''
            # 1. 准备文件内容
            #     if sign != 0:
            #         _setting = json.loads(open("settings.json", "r").read())
            #         gl.conntion_db2 = _setting
            #         gl.sign = sign
            #     sql = "select * from SX_ACCOUNT_GROUP_INFO where SYSTEM_ID='%s'" % system_id
            #     ds = cF.executeCaseSQL_DB2(sql)
            # 将返回的列表值转为dict方式，方便转换为json字符串，在Agent和AgentServer中传递
            #     detail_dict = OrderedDict()
            #     for i, rec in enumerate(ds):
            #         detail_dict[i] = rec

            #     if detail_dict.keys() != []:
            #         ret, msg = generate_account_group_xml_orderby_system_id(system_id, detail_dict)
            #         print ret, msg
            #         if ret < 0:
            #             Logging.getLog().error(msg)
            #             return -1, msg
            #     return 0, ""

            # def UpdateT2InterfaceDetailFile(self, sign, system_id):

            #     '''
            #     #TODO chenbaoshuai
            #     从数据库中抽取T2Interface内容的文件，调用TestAgent ProcessFileSendingMsg 函数写入相应位置
            #     :param client_id: TestAgent ID 号
            #     :param system_id: 系统ID号
            #     :return: 一个元组(ret,msg)
            #         ret: 0代表成功，-1代表失败
            #         msg：详细信息
            #     '''
            #     if sign != 0:
            #         _setting = json.loads(open("settings.json", "r").read())
            #         gl.conntion_db2 = _setting
            #         gl.sign = sign
            #     print 'enter >>>>>>>>>>>UpdateT2InterfaceDetailFile'
            # 1. 准备文件内容
            #     sql = "SELECT i.FUNCID,i.INTERFACE_NAME, i.FUNCID_DESC, i.TIMEOUT,i.NEED_LOG,d.INPUT_TYPE,d.PARAM_NAME,d.PARAM_TYPE," \
            #           "d.PARAM_DESC,d.DISABLEFLAG,d.PARAM_INDEX FROM sx_interface_info i LEFT JOIN " \
            #           "sx_interface_detail_info d ON i.ID=d.INTERFACE_ID WHERE i.SYSTEM_ID='%s' AND i.funcid != '' " \
            #           "AND d.INTERFACE_ID IS NOT NULL ORDER BY i.ID" % (system_id)
            #     ds = cF.executeCaseSQL(sql)

            # 将返回的列表值转为dict方式，方便转换为json字符串，在Agent和AgentServer中传递
            #     detail_dict = OrderedDict()
            #     for i, rec in enumerate(ds):
            #         detail_dict[i] = rec

            #     if detail_dict.keys() != []:
            # data = json.dumps(detail_dict)
            # 准备调用TestAgent接口
            # s = ServerProxy("http://%s:%s" % (
            #   self._mqserver._clients_dict[client_id]["ip"], self._mqserver._clients_dict[client_id]["port"]))

    #         ret, msg = update_t2_interface_detail_file(system_id, detail_dict)
    #         print ret, msg
    #         if ret < 0:
    #             Logging.getLog().error(msg)
    #             return -1, msg
    #     return 0, ""
    def sql_comt(self, sum_agent_n, task_agent_n, n):
        try:
            sql = "update SX_AGENT_INFO set STATE = 'STATE_RUNNING', CURR_TASK_NUM = %s, UN_FINISH_CASES_NUM = %s where AGENT_CODE = '%s'" % (
                task_agent_n, sum_agent_n, n)
            ds = cF.executeCaseSQL_DB2(sql)
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info
        return 0, ""

    def sql_comt_copy(self, sum_agent_n, task_agent_n, n):
        try:
            STATE = "STATE_FREE"
            if gl.g_origin_agent_info:
                if n in gl.g_origin_agent_info.keys():
                    if gl.g_origin_agent_info[n]['state'] == "STATE_EXCEPTION":
                        STATE = "STATE_EXCEPTION"
                else:
                    STATE = "STATE_EXCEPTION"
            sql = "update SX_AGENT_INFO set STATE = '%s', CURR_TASK_NUM = %s, UN_FINISH_CASES_NUM = %s where AGENT_CODE = '%s'" % (
                STATE, task_agent_n, sum_agent_n, n)
            cF.executeCaseSQL_DB2(sql)
            # print sql
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info
        return 0, ""

    def handle_count_tasks_unfinish_cases(self):
        """
        当前任务数和未完成案例实现
        :return:
        """
        try:
            sql = "select agent_id, case_num, run_case_num from SX_CASES_COLLECTION_RUN_TASK where RUN_STATUS !='STATE_FINISH'"
            ds = cF.executeCaseSQL_DB2(sql)
            agent_id_dict = {}
            sql_agent_list = 'SELECT AGENT_CODE FROM sx_agent_info'
            ds_agent_id = cF.executeCaseSQL_DB2(sql_agent_list)
            a_list = []
            for i in ds_agent_id:
                if i["AGENT_CODE"] != None:
                    a_list.append(i["AGENT_CODE"])
            for agent_id in a_list:
                agent_id_dict.setdefault(agent_id, {"task_count": 0, "unfinished_cases_num": 0})
            for rec in ds:
                agent_id_list = rec["AGENT_ID"].split(',')
                for agent_id in agent_id_list:
                    if not rec["RUN_CASE_NUM"] or rec["RUN_CASE_NUM"] == 'null':
                        rec["RUN_CASE_NUM"] = 0
                    if not rec["CASE_NUM"] or rec["CASE_NUM"] == 'null':
                        rec["CASE_NUM"] = 0
                    agent_id_dict.setdefault(agent_id, {"task_count": 0, "unfinished_cases_num": 0})[
                        "task_count"] += 1  # 任务数量统计
                    average_cases_num = int(math.ceil(
                        (float(rec["CASE_NUM"]) - float(rec["RUN_CASE_NUM"])) / len(agent_id_list)))  # 计算未完成案例数量
                    agent_id_dict[agent_id]["unfinished_cases_num"] += average_cases_num
            # time.sleep(5)
            for agent_id in agent_id_dict.keys():
                if agent_id_dict[agent_id]["unfinished_cases_num"] or agent_id_dict[agent_id]["task_count"]:
                    self.sql_comt(agent_id_dict[agent_id]["unfinished_cases_num"],
                                  agent_id_dict[agent_id]["task_count"], agent_id)
                else:
                    self.sql_comt_copy(agent_id_dict[agent_id]["unfinished_cases_num"],
                                       agent_id_dict[agent_id]["task_count"], agent_id)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def processTimedTask(self):
        '''
        处理定时任务，每分钟执行一次。
        每次读取整个sx_timed_task表，逐条分析：
        首先分析RULE_TYPE 字段 0 每月；1：每周；2：每日；3：每时；4：只执行一次
        MINUTE HOUR  字段直接转化为INT型即可；
        DAY,MONTH 可以为NULL，表示任意。
        WEEK为一个1,2,3,4,5,6,7的值的组合列表。或者为空，表示任意星期
        业务逻辑主要根据RULE_TYPE 的值执行不同的判断
        '''

        try:
            sql = "select * from sx_timed_task where IS_DELETE = '0'"
            ds = cF.executeCaseSQL(sql)
            if ds:
                # Logging.getLog().debug(u"判断用例集是否被删除")
                COLLECTION_IDS_TIMED_TASK = [str(rec['COLLECTION_ID']) for rec in ds]
                COLLECTION_IDS_TIMED_TASK_STR = ",".join(COLLECTION_IDS_TIMED_TASK)
                sql = "select COLLECTION_ID from SX_CASES_COLLECTION where COLLECTION_ID IN (" + COLLECTION_IDS_TIMED_TASK_STR + ") and STATUS = '0'"
                ds_c = cF.executeCaseSQL(sql)
                DEL_COLLECTION_IDS = []
                if ds_c:
                    COLLECTION_IDS = [str(rec['COLLECTION_ID']) for rec in ds_c]
                    DEL_COLLECTION_IDS = list(set(COLLECTION_IDS_TIMED_TASK).difference(set(COLLECTION_IDS)))
            for rec in ds:
                # 判断用例集是否被删除
                if DEL_COLLECTION_IDS and str(rec['COLLECTION_ID']) in DEL_COLLECTION_IDS:
                    Logging.getLog().debug(u"用例集被删除 COLLECTION_ID：%s 跳过" % str(rec['COLLECTION_ID']))
                    continue
                # 获取当前信息
                now = datetime.datetime.now()  # now.month day hour min isoweekday()
                is_trigger = False

                if rec['RULE_TYPE'] == '0':  # 每月
                    if int(rec['DAY']) == now.day and int(rec['HOUR']) == now.hour and int(rec['MINUTE']) == now.minute:
                        is_trigger = True
                elif rec['RULE_TYPE'] == '1':  # 每周
                    weekday_list = rec['WEEK'].split(',')
                    if str(now.isoweekday()) in weekday_list and int(rec['HOUR']) == now.hour and int(
                            rec['MINUTE']) == now.minute:
                        is_trigger = True
                elif rec['RULE_TYPE'] == '2':  # 每日
                    if int(rec['HOUR']) == now.hour and int(rec['MINUTE']) == now.minute:
                        is_trigger = True
                elif rec['RULE_TYPE'] == '3':  # 每时
                    if int(rec['MINUTE']) == now.minute:
                        is_trigger = True
                elif rec['RULE_TYPE'] == '4':  # 只执行一次
                    if int(rec['YEAR']) == now.year and int(rec['MONTH']) == now.month and int(
                            rec['DAY']) == now.day and int(rec['HOUR']) == now.hour and int(
                        rec['MINUTE']) == now.minute:
                        is_trigger = True

                if is_trigger == True:
                    # 获取告警信息
                    task_warning_id = ""
                    sql = "select TASK_WARNING_ID from SX_TASK_WARNING where task_id = %d" % (int(rec['TASK_ID']))
                    Logging.getLog().debug(sql)
                    ds1 = cF.executeCaseSQL(sql)
                    if len(ds1) > 0:
                        task_warning_id = ds1[0]['TASK_WARNING_ID']

                    if task_warning_id == "":
                        sql = '''insert into sx_cases_collection_run_task 
                                (COLLECTION_ID,
                                TEST_SYSTEM_ID,
                                AGENT_ID,
                                DISTRIBUTION_STRATEGY_ID, 
                                RUN_STATUS, 
                                TASK_ID, 
                                INIT_STATE, 
                                CANCEL_FLAG,
                             TEST_SYSTEM_ARR
                                )
                                values
                                (%d, 
                                %d, 
                                '%s', 
                                '0', 
                                'STATE_START', 
                                %d, 
                                'STATE_UNINIT', 
                                0,
                             '%s'
                                ); ''' % (
                            int(rec['COLLECTION_ID']),
                            int(rec['TEST_SYSTEM_ID']),
                            rec['AGENT_ID'],
                            int(rec['TASK_ID']),
                            str(rec['TEST_SYSTEM_ARR']))
                    else:
                        sql = '''insert into sx_cases_collection_run_task 
                                (COLLECTION_ID,
                                TEST_SYSTEM_ID,
                                AGENT_ID,
                                DISTRIBUTION_STRATEGY_ID, 
                                TASK_WARNING_ID, 
                                RUN_STATUS, 
                                TASK_ID, 
                                INIT_STATE, 
                                CANCEL_FLAG,
                             TEST_SYSTEM_ARR
                                )
                                values
                                (%d, 
                                %d, 
                                '%s', 
                                '0', 
                                %d, 
                                'STATE_START', 
                                %d, 
                                'STATE_UNINIT', 
                                0,
                             '%s'
                                ); ''' % (
                            int(rec['COLLECTION_ID']), int(rec['TEST_SYSTEM_ID']), rec['AGENT_ID'],
                            int(task_warning_id),
                            int(rec['TASK_ID']), str(['TEST_SYSTEM_ARR']))
                    Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)
                    sql1 = "select count(*) from sx_cases where DISABLEFLAG='0' and SYSTEM_ID='%s' and IS_DELETE = '0'" % (rec['SYSTEM_ID'])
                    ds1 = cF.executeCaseSQL(sql1)
                    sql2 = "select COLLECTION_RUN_TASK_ID from sx_cases_collection_run_task where RUN_STATUS='STATE_START' and TASK_ID=%d" % (
                        int(rec['TASK_ID']))
                    ds2 = cF.executeCaseSQL(sql2)
                    sql = '''insert into sx_collection_test_report
                            (COLLECTION_RUN_TASK_ID,
                            PROJECT_CASES_NUM,
                            REPORT_TYPE
                            )
                            values
                            (%d,
                            %d,
                            '1'
                            );''' % (int(ds2[0]['COLLECTION_RUN_TASK_ID']), int(ds1[0]['1']))
                    Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info
        return 0, ""

    def processCancelTask(self):
        '''
        处理取消任务。
        对于当前正常运行状态的任务，每30秒侦测一次取消状态。

        '''
        try:
            sql = "select CANCEL_FLAG, COLLECTION_RUN_TASK_ID from sx_cases_collection_run_task where RUN_STATUS !='STATE_FINISH'"
            # sql = "select CANCEL_FLAG, COLLECTION_RUN_TASK_ID from sx_cases_collection_run_task where collection_run_task_id = %d and RUN_STATUS !='STATE_FINISH'" % runtaskid
            # Logging.getLog().debug(sql)
            ds = cF.executeCaseSQL(sql)

            for rec in ds:
                if str(rec["CANCEL_FLAG"]) == '1':
                    task_id = int(rec["COLLECTION_RUN_TASK_ID"])
                    Logging.getLog().info(u"侦测到用户取消任务%d" % task_id)
                    try:
                        # 如果内存中没有找到该任务，直接取消
                        # 通知agent取消任务
                        if task_id in self._mqserver._task_agent_dict.keys():
                            for agent_id in self._mqserver._task_agent_dict[task_id]:
                                cancel_a_task_msg = copy.deepcopy(gl.cancel_a_task_msg)
                                cancel_a_task_msg["msg_body"]["task_id"] = task_id

                                queue_name = 'cmd_queue_%d' % int(agent_id)
                                try:
                                    self._mqserver.send_msg_to_queue(json.dumps(cancel_a_task_msg, ensure_ascii=False),
                                                                     queue_name)
                                except:
                                    exc_info = cF.getExceptionInfo()
                                    Logging.getLog().error(exc_info)
                        # 设置redis任务取消表示
                        self._mqserver._redis_client.cancel_task(task_id)
                    except:
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().error(exc_info)

                    run_result = "RESULT_CANCEL"
                    sql = "update sx_cases_collection_run_task set run_status='STATE_FINISH',run_result='%s' where collection_run_task_id=%d" % (
                        run_result, int(task_id))
                    Logging.getLog().debug(sql)
                    cF.executeCaseSQL(sql)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def processCasesExecuteOutOfTime(self, runtaskid):
        '''
        处理案例执行超时问题
        '''
        try:
            now = datetime.datetime.now()
            is_trigger = False

            warning_dict = self._cases_task_dict[runtaskid]['warning_info']
            if not warning_dict.has_key(4):
                return 0, ""

            timeout = int(warning_dict[4]['warning_val'])  # 超时设定，时间为分钟

            for case in self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list']:  # 第一个一般是最早发送出去的，所以比较一个即可
                if (now - datetime.datetime.strptime(case['RUN_START_TIME'],
                                                     '%Y-%m-%d %H:%M:%S')).seconds > timeout * 60:
                    Logging.getLog().debug("trigger one ExecuteOutOfTime event")
                    is_trigger = True
                break

            if is_trigger == True:
                warning_type = 'EMAIL'
                if warning_dict[4]['warning_type'] == '2':
                    warning_type = 'MOBILE'

                sql = '''insert into sx_warning_info 
                        (
                        TASK_ID, 
                        COLLECTION_ID, 
                        WARNING_ID, 
                        WARNING_MSG, 
                        WARNING_WAY, 
                        SEND_STATE, 
                        EMAIL_LIST, 
                        MOBILE_LIST
                        )
                        values
                        (
                        %d, 
                        %d, 
                        1, 
                        '%s', 
                        '%s', 
                        'STATE_UNSEND', 
                        '%s', 
                        '%s'
                        );
                        ''' % (int(runtaskid), self._cases_task_dict[runtaskid]['collection_id'],
                               u"自动化任务%d单案例执行时间超过%d分钟，请做相关处理" % (int(runtaskid), timeout), warning_type,
                               MySQLdb.escape_string(warning_dict[1]['warning_email']), warning_dict[1]['warning_tel'])
                Logging.getLog().debug(sql)
                cF.executeCaseSQL(sql)
                warning_dict.pop(4)  # 移除告警，报警一次即可
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            return -1, exc_info

    def LastAliveRecordThread(self):
        _alive_time = datetime.datetime.now()
        _alive_time_dict = {}
        _alive_time_dict["last_alive"] = _alive_time.strftime("%Y-%m-%d %H:%M:%S")

        alive_file = 'TestAgentServer_Alive.json'

        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        alive_file_path = os.path.join(application_path, alive_file)

        open(alive_file_path, 'w').write(json.dumps(_alive_time_dict, ensure_ascii=False, encoding="utf8"))

        while not gl.is_exit_all_thread:
            if (datetime.datetime.now() - _alive_time).seconds > 30:
                # 每30秒写入一次，代表存活状态，否则将会被守护进程杀掉并重新启动
                _alive_time_dict["last_alive"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                open(alive_file_path, 'w').write(
                    json.dumps(_alive_time_dict, indent=4, ensure_ascii=False, encoding="utf8"))
                _alive_time = datetime.datetime.now()
                time.sleep(5)

    def run(self):
        '''
        处理任务的下发，状态的调整等等

        对于每一个任务，查看是否有未下发的任务；
        如果有，查看是否有空闲的agent，如果有就下发；没有就等到有再下发
        '''
        last_time = last_task_monitor_time = last_timed_task_time = last_cases_out_of_time = _alive_time = datetime.datetime.now()

        # _alive_time_dict = {}
        # _alive_time_dict["last_alive"] = _alive_time.strftime("%Y-%m-%d %H:%M:%S")

        # alive_file = 'TestAgentServer_Alive.json'

        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        # alive_file_path = os.path.join(application_path, alive_file)

        # open(alive_file_path,'w').write(json.dumps(_alive_time_dict,indent=4,ensure_ascii=False,encoding="utf8"))
        self._last_alive_thread = threading.Thread(target=self.LastAliveRecordThread)
        self._last_alive_thread.start()

        self._handle_result_thread = threading.Thread(target=self.handle_test_result_in_redis)
        self._handle_result_thread.start()

        self._handle_getCasesListthreading = threading.Thread(target=self.getCasesListthreading)
        self._handle_getCasesListthreading.start()
        # [rzxiao] 应该可以不用了
        # ret, msg = self.processUnFinishedCases()
        # if ret < 0:
        #     Logging.getLog().error(msg)
        #     return

        # [rzxiao] 从redis上获取一次数据，维护在本程序的内存中，以减少读取redis的次数

        try:
            # 检测是否有需要执行的任务，然后是否有空闲的Agent，然后下发任务，处理任务结束的消息等等
            while True:
                if (gl.is_exit_all_thread == True):
                    break
                if (datetime.datetime.now() - _alive_time).seconds > 30:
                    # 每30秒写入一次，代表存活状态，否则将会被守护进程杀掉并重新启动
                    # _alive_time_dict["last_alive"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # open(alive_file_path,'w').write(json.dumps(_alive_time_dict,indent=4,ensure_ascii=False,encoding="utf8"))
                    _alive_time = datetime.datetime.now()

                    # 放在这里，每30秒扫描一次
                    # [rzxiao]后期处理
                    # for runtaskid in self._cases_task_dict.keys():
                    self.processCancelTask()
                try:
                    # 处理已经结束的任务
                    if self._cases_task_dict:
                        for runtaskid in self._cases_task_dict.keys():
                            if "run_status" in self._cases_task_dict[runtaskid].keys():
                                if self._cases_task_dict[runtaskid]['run_status'] == 'STATE_FINISH':
                                    # 将时间修改回来
                                    for ip in gl.g_timeSyncServerSettingList:
                                        ServerUrl = "http://" + ip + ":5556"
                                        # s = ServerProxy(ServerUrl)
                                        Logging.getLog().debug("ModifyRemoteServerDateTime:%s" % ServerUrl)
                                        try:
                                            now = datetime.datetime.now()
                                            # ret, msg = s.ModifyRemoteServerDateTime(int(now.year), int(now.month), int(now.day),
                                            #                                         int(now.hour), int(now.minute), int(now.second))
                                            ret, msg = 0, ''
                                            if ret < 0:
                                                Logging.getLog().error(msg)
                                        except:
                                            exc = cF.getExceptionInfo()
                                            Logging.getLog().error(exc)

                                    self._cases_task_dict.pop(runtaskid)
                                    self._cases_task_send_uncomfirm_dict.pop(runtaskid)
                except:
                    exc = cF.getExceptionInfo()
                    Logging.getLog().error(exc)
                    # for runtaskid in self._cases_task_dict.keys():
                    #
                    #     if 'cases_list' in self._cases_task_dict[runtaskid].keys() and len(
                    #             self._cases_task_dict[runtaskid]['cases_list']) != 0:  # 还有未下发的任务
                    #         for client_id in self._cases_task_dict[runtaskid]['agent_id']:
                    #
                    #             if client_id in self._mqserver._clients_dict.keys() and 'task_state' in \
                    #                     self._mqserver._clients_dict[client_id].keys() and \
                    #                             self._mqserver._clients_dict[client_id][
                    #                                 "task_state"] == gl.CLIENT_TASK_STATE_FREE:
                    #                 if self._cases_task_dict[runtaskid]['init_state'] == 'STATE_UNINIT' or \
                    #                                 self._cases_task_dict[runtaskid]['init_state'] == '':
                    #
                    #                     if self._cases_task_dict[runtaskid]['system_id'].upper() == '142891090059622AV2':
                    #                         # TODO chenbaoshuai
                    #                         # 调用产生T2Interfacedetail.xml 文件的代码，并将这个文件通过ftp上传到FTPServer的init文件相应位置
                    #                         pass
                    #
                    #                     # 发送初始化消息
                    #
                    #
                    #                     init_env_msg = copy.copy(gl.init_env_msg)
                    #                     init_env_msg["msg_body"]["task_id"] = str(runtaskid)
                    #                     init_env_msg['msg_body']['env'] = self._cases_task_dict[runtaskid][
                    #                         'system_id']  # fixme 以后需要根据任务表中的测试环境的信息加以变更
                    #                     init_env_msg['msg_body']['type'] = "0"
                    #
                    #                     Logging.getLog().debug("send init_env_msg to %d" % int(client_id))
                    #                     self._mqserver._clients_dict[client_id][
                    #                         "task_state"] = gl.CLIENT_TASK_STATE_ENIV_INIT
                    #                     s = ServerProxy("http://%s:%s" % (self._mqserver._clients_dict[client_id]["ip"],
                    #                                                       self._mqserver._clients_dict[client_id]["port"]))
                    #                     # ret,msg = self._mqserver.SendMessage(client_id,init_env_msg)
                    #                     retry_count = 0
                    #                     while retry_count < gl.SERVER_MAX_RETRY_COUNT:
                    #                         try:
                    #                             Logging.getLog().debug(
                    #                                 "call processEnvInit agent%s msg=%s" % (str(client_id), init_env_msg))
                    #                             ret, msg = s.processEnvInit(init_env_msg)
                    #                             if ret < 0:
                    #                                 Logging.getLog().error(msg)
                    #                             self._cases_task_dict[runtaskid]['init_state'] = 'STATE_EXECUTE'
                    #                             Logging.getLog().debug(
                    #                                 "switch %s task init_state to STATE_EXECUTE" % str(runtaskid))
                    #                             break
                    #
                    #                         except:
                    #                             exc = cF.getExceptionInfo()
                    #                             Logging.getLog().critical("call processEnvInit exception %s" % exc)
                    #                             retry_count += 1
                    #                             time.sleep(3)
                    #                             # gl.is_exit_all_thread = True
                    #
                    #                             # fixme 可能需要将这个状态写回到数据库中
                    #
                    #                 elif self._cases_task_dict[runtaskid]['init_state'] == 'STATE_EXECUTE':
                    #                     # 继续等待
                    #                     pass
                    #                 else:
                    #                     # 开始下发案例
                    #                     Logging.getLog().debug("client_id=%s" % str(client_id))
                    #                     ret, msg = self.distributeCasesToAgent(runtaskid, client_id, 1)
                    #                     # ret,msg = self.createCasesDistributeMsg(runtaskid,1) #每次拿一个出来下发
                    #                     if ret < 0:
                    #                         Logging.getLog().error(msg)
                    #                         continue
                    #     elif 'cases_list' in self._cases_task_dict[runtaskid].keys() and len(
                    #             self._cases_task_dict[runtaskid]['cases_list']) == 0:  # 已经全部下发
                    #         # 如果要执行的client都不是在运行阶段，那么进行一次漏单扫描
                    #         is_agents_free = True
                    #         for client_id in self._cases_task_dict[runtaskid]['agent_id']:
                    #             if client_id in self._mqserver._clients_dict.keys() and 'state' in \
                    #                     self._mqserver._clients_dict[client_id].keys() and \
                    #                             self._mqserver._clients_dict[client_id][
                    #                                 "task_state"] == gl.CLIENT_TASK_STATE_FREE:
                    #                 continue
                    #             else:
                    #                 is_agents_free = False
                    #
                    #         if is_agents_free == True:
                    #             # 如果某个任务指定的agent都处于空闲状态，而_cases_task_send_uncomfirm_dict不空，说明还有用用例执行信息丢失了，于是重发
                    #             case_count = len(self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'])
                    #             if case_count != 0:
                    #                 for i in xrange(case_count):
                    #                     self._cases_task_dict[runtaskid]['cases_list'].append(
                    #                         self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].pop(0))

                    # if (datetime.datetime.now() - last_task_monitor_time).seconds > 5:
                    #     last_task_monitor_time = datetime.datetime.now()
                    #     sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_START'"
                    #     ds = cF.executeCaseSQL(sql)
                    # if str(time.strftime("%H:%M", time.localtime())) == "10:14":
                    #     Logging()
                #     if len(ds) > 0:
                #         Logging.getLog().debug(u"找到新任务")
                #         ret, msg = self.getCasesListthreading()
                #         if ret < 0:
                #             Logging.getLog().error(msg)

                # 处理定时任务
                if (datetime.datetime.now() - last_timed_task_time).seconds > 60:

                    last_timed_task_time = datetime.datetime.now()
                    # Logging.getLog().info("processTimedTask")
                    ret, msg = self.processTimedTask()
                    if ret < 0:
                        Logging.getLog().error(msg)
                # 处理案例执行超时
                if (datetime.datetime.now() - last_cases_out_of_time).seconds > 60:
                    last_cases_out_of_time = datetime.datetime.now()
                    for runtaskid in self._cases_task_send_uncomfirm_dict.keys():
                        if 'cases_list' in self._cases_task_send_uncomfirm_dict[runtaskid].keys():
                            # Logging.getLog().debug('processCasesExecuteOutOfTime')
                            ret, msg = self.processCasesExecuteOutOfTime(runtaskid)
                            if ret < 0:
                                Logging.getLog().error(msg)
        except:
            exc_info = cF.getExceptionInfo()
            gl.is_exit_all_thread = True
            Logging.getLog().critical(exc_info)

    def getCasesListthreading(self):
        # while True:
        while gl.is_exit_all_thread != True:
            try:
                ret, msg = self.getCasesList()
                if ret < 0:
                    Logging.getLog().critical(msg)
                    continue
                time.sleep(5)
            except Exception as e:
                continue


def processTerm(signum, frame):
    Logging.getLog().debug("receive Term signal")
    gl.is_exit_all_thread = True


    # homedir = os.getcwd()


    # 创建一个根节点Managers对象


    # 创建一个根节点Managers对象
    # 加入Interface节点信息
    # 循环添加入、出参节点信息


    # 加入Interface节点信息
    # #循环添加入、出参节点信息


    # 开始写xml文档
    # 将生成的T2InterfaceDetail.xml上传到FTP


# def updateT2file(system_id, sign):
#     try:
#         server = MQServer()
#         server.setDaemon(True)
#         server.start()

#         Logging.getLog().info(u"启动消息服务器成功")

#         taskThread = task(server)
#         taskThread.UpdateT2InterfaceDetailFile(sign, system_id)
#         Logging.getLog().debug(u'%sT2文件已经成功上传到FTP' % system_id)
#         Logging.getLog().debug(u'T2文件更新成功')
#         return 0, ''
#     except:
#         exc_info = cF.getExceptionInfo()
#         Logging.getLog().error(exc_info)
#         return -1, exc_info


# def generate_xml(system_id, sign):
#     try:
#         server = MQServer()
#         server.setDaemon(True)
#         server.start()

#         Logging.getLog().info(u"启动消息服务器成功")

#         taskThread = task(server)
#         taskThread.generate_account_group_xml(system_id, sign)
#         Logging.getLog().debug(u'%s系统账户组xml已经成功上传到FTP' % system_id)
# s = ServerProxy("http://127.0.0.0:16001" , allow_none=True)
# Logging.getLog().debug(u'连接testagent客户端成功')
# s.update_account_xml(system_id)
#         Logging.getLog().debug(u'账户组信息更新成功')
#     except:
#         exc_info = cF.getExceptionInfo()
#         Logging.getLog().error(exc_info)
#         return -1, exc_info


def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)
    Logging.getLog().info(u'''
    时溪自动化测试平台-Test Agent Server v2.0 2019.03.05 alpha-7
    (上海时溪信息技术有限公司）
    ''')
    cF.readConfigFile()

    while True:
        server = MQServer()
        server.setDaemon(True)
        server.start()

        Logging.getLog().info(u"启动消息服务器成功")

        taskThread = task(server)

        # for debug
        # taskThread.UpdateT2InterfaceDetailFile(0,'ZHLC')
        taskThread.setDaemon(True)
        taskThread.start()
        Logging.getLog().info(u"启动调度引擎成功")

        Logging.getLog().info(u"初始化环境")

        '''
        ret,msg = cF.RunInitScript(0,'p')
        if ret < 0:
            print "Initialize env fail"
            print msg
            return
        '''
        #退出线程
        while True:
            if server.isAlive() == False and taskThread.isAlive() == False:
                server.rpcserver.server_close()
                return
            if server.mq_connect_closed == True:
                server.mq_connect_closed = False
                gl.is_exit_all_thread = True
                time.sleep(15)
                server.rpcserver.server_close()
                gl.is_exit_all_thread = False
                Logging.getLog().debug("server close")
                break


if __name__ == "__main__":
    main()


