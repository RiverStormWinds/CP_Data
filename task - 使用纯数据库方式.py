# -*- coding:gbk -*-
import commFuncs as cF
from collections import OrderedDict
import threading
import gl
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

class task(threading.Thread):
    def __init__(self,mqserver):
        # 保存每个正在进行的任务的相关信息，以runtaskid 作为关键值。相关信息也为一个字典结构，
        # 包括"runtaskid","collection_id","agent_id","run_status","case_num","run_case_num","run_case_num_success","run_case_num_fail",
        # "run_start_time","run_end_time"等信息
        self._cases_task_dict = OrderedDict() 

        #进行下发，但是尚未收到确认应答的队列，
        self._cases_task_send_uncomfirm_dict = OrderedDict()
        self._mqserver = mqserver
        self._mqserver.registerTaskThread(self)
        threading.Thread.__init__ (self)
        pass
    #def getLeftCasesCount(self,runtaskid):
    #    '''
    #    根据运行任务id获得剩下的案例个数
    #    '''
    #    if runtaskid in self._cases_task_dict.keys():
    #        return len(self._cases_task_dict[runtaskid]['cases_list'])
    #    else:
    #        return 0
    #def getUnConfirmResultCasesCount(self,runtaskid):
    #    '''
    #    获得已经下发，但是没有回传结果的案例个数
    #    '''
    #    if runtaskid in self._cases_task_send_uncomfirm_dict.keys():
    #        return len(self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'])
    #    else:
    #        return -1
    #def confirmCasesResult(self,runtaskid,RUN_RECORD_ID):
    #    '''
    #    确认案例的测试结果,将对应的列表数据删除
    #    '''
    #    if runtaskid not in self._cases_task_send_uncomfirm_dict.keys():
    #        return -1,u"未找到"
        
    #    index = -1
    #    for i, case in enumerate(self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list']):
    #        if case['RUN_RECORD_ID'] == RUN_RECORD_ID:
    #            index = i 
    #            break
    #    if index == -1:
    #        return -1,u"未找到要删除的值"
    #    self._cases_task_send_uncomfirm_dict[runtaskid]['cases_list'].pop(index)
    #    return 0,""      

    def createCasesDistributeMsg(self,runtaskid,count=0,strategyid = 0):
        '''
        从案例列表中，创建案例分发消息
        '''
        try:
            case_to_send_list = []
            debug_last_run_record_id = 0

            #加载所有未测试案例，从里面挑选一个出来
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
                        , sx_run_record.CMDSTRING
                        , sx_run_record.EXPECTED_VALUE
                        , sx_run_record.SCRIPT_NAME
                        , sx_run_record.ADAPTER_TYPE
                        , sx_run_record.PRE_ACTION
                        , sx_run_record.PRO_ACTION
                    FROM
                        sx_run_record
                    WHERE 
                        sx_run_record.task_id = %d and sx_run_record.RESULT = 'STATE_UNTEST'
                    ORDER BY
                        sx_run_record.COLLECTION_DETAIL_ID,sx_run_record.STEP
                ''' %(runtask_id)
                
            ds1 = cF.executeCaseSQL(sql)
            for rec1 in ds1:
                cases_list.append(rec1)        


            if count == 0:
                #全部案例一次性下发
                case_to_send_list = cases_list
            else:
                for i in xrange(count):
                    if len(cases_list)>0:
                        case = cases_list.pop(0)
                        case_to_send_list.append(case)
                        debug_last_run_record_id = case['RUN_RECORD_ID']
                        #判断这个案例是否有其他步骤
                        while len(cases_list)> 0 and cases_list[0]['CASES_PARAM_DATA_ID'] == case['CASES_PARAM_DATA_ID']:
                            print "multi steps"
                            case = cases_list.pop(0)
                            print case
                            case_to_send_list.append(case)
                            debug_last_run_record_id = case['RUN_RECORD_ID']
                    else:
                    	return -1,u"队列空了" #fixme 
            
            run_record_id_list = []
            for case in case_to_send_list:
                run_record_id_list.append(str(case['RUN_RECORD_ID']))
            sql = "update sx_run_record set result = 'STATE_DISTRIBUTED' where run_record_id in (%s)" %(",".join(run_record_id_list))
            cF.executeCaseSQL(sql)

            case_distribute_msg = copy.copy(gl.case_distribute_msg)
            case_distribute_msg["msg_body"]["runTaskid"] = runtaskid
            case_distribute_msg["msg_body"]["cases"] = case_to_send_list
            open('case_distribute_%s.json' %str(debug_last_run_record_id),'w').write(json.dumps(case_distribute_msg,ensure_ascii=False,encoding="utf8"))
            return 0,case_distribute_msg

        except:
            exc_info = cF.getExceptionInfo()
            return -1,exc_info
    def processInitEnvRepMsg(self,msg):
        '''
        处理初始化脚本回传结果
        '''
        try:
            print msg
            runtaskid = int(msg["msg_body"]["task_id"])
            result = msg["msg_body"]["result"]
            self._cases_task_dict[runtaskid]['init_state'] = result
            sql = "update sx_cases_collection_run_task set init_state = '%s' where collection_run_task_id = %d " %(result,int(runtaskid))
            cF.executeCaseSQL(sql)
            return 0,""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1,exc_info

    def processCasesResultMsg(self,msg):
        '''
        处理案例回传结果
        '''
        try:
            case_result_dict = OrderedDict()  # {"cases_param_data_id","成功"}
            runtaskid = msg["msg_body"]["runTaskid"]
            test_result_list = msg["msg_body"]["testResult"]

            for result in test_result_list:
                sql = "update sx_run_record set result='%s',result_message='%s' ,RUN_USER='%s',ATTACHMENT='%s' where RUN_RECORD_ID='%s'" %(result['result'],MySQLdb.escape_string(result['log']),str(result['run_user']),result['attachment'],str(result['RUN_RECORD_ID']))
                print sql
                cF.executeCaseSQL(sql)
                #self.confirmCasesResult(runtaskid,result['RUN_RECORD_ID'])
                

            # 处理一下多步骤问题
            sql = "select * from sx_run_record where TASK_ID = %d " %runtaskid
            ds = cF.executeCaseSQL(sql)
            for rec in ds:
                if case_result_dict.has_key(rec['CASES_PARAM_DATA_ID']):
                    if rec['RESULT'] == 'STATE_FAIL' or rec['RESULT'] == 'STATE_SKIP':
                        case_result_dict[rec['CASES_PARAM_DATA_ID']] = 'STATE_FAIL'
                else:
                    case_result_dict[rec['CASES_PARAM_DATA_ID']] = rec['RESULT']

            pass_count = 0
            fail_count = 0
            untest_count = 0
            for key in case_result_dict.keys():
                if case_result_dict[key] == 'STATE_PASS':
                    pass_count += 1
                elif case_result_dict[key] == 'STATE_FAIL' or case_result_dict[key] == 'STATE_SKIP':
                    fail_count += 1
                else:
                    untest_count += 1

            if runtaskid not in self._cases_task_dict.keys():
                return -1,"taskid %d has been removed" %runtaskid
            self._cases_task_dict[runtaskid]["run_case_num_success"] = pass_count
            self._cases_task_dict[runtaskid]["run_case_num_fail"] = fail_count
            self._cases_task_dict[runtaskid]["run_case_num"] = pass_count + fail_count

            #写入数据库
            sql = "update sx_cases_collection_run_task set run_case_num=%d,run_case_num_success=%d,run_case_num_fail=%d where collection_run_task_id=%d" %(self._cases_task_dict[runtaskid]["run_case_num"],self._cases_task_dict[runtaskid]["run_case_num_success"],self._cases_task_dict[runtaskid]["run_case_num_fail"],runtaskid)
            
            cF.executeCaseSQL(sql)

            if self._cases_task_dict[runtaskid]["case_num"] == self._cases_task_dict[runtaskid]["run_case_num"]: #全部执行完毕
                self._cases_task_dict[runtaskid]['run_end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sql = "update sx_cases_collection_run_task set run_status='STATE_FINISH',run_start_time='%s',run_end_time='%s',run_during_time='%s' where collection_run_task_id='%s'" %(self._cases_task_dict[runtaskid]['run_start_time'],self._cases_task_dict[runtaskid]['run_end_time'],str(datetime.datetime.strptime(self._cases_task_dict[runtaskid]['run_end_time'],'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(self._cases_task_dict[runtaskid]['run_start_time'],'%Y-%m-%d %H:%M:%S')),runtaskid)
                print sql
                cF.executeCaseSQL(sql)

                #删除容易导致同步问题，fixme
                #del self._cases_task_dict[runtaskid]
                #del self._cases_task_send_uncomfirm_dict[runtaskid]

            return 0,""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1,exc_info
    def getScriptNameFromInputString(self,input_string):
        script_name  = ''
        input_string = input_string.strip('#')

        l = input_string.find('path=')
        if l < 0:
            return script_name
        r = input_string.find('#')
        if r < 0:
            script_name = input_string[l+5:]
        else:
            script_name = input_string[l+5:r]
        return script_name
        
    def processUnFinishedCases(self):
        '''
        因为各种原因导致的TestAgentServer中断，需要启动的时候去扫描任务和运行记录，将未完成的继续完成。
        '''
        try:

            sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_PREPARE'"
            ds = cF.executeCaseSQL(sql)
            if len(ds) <= 0:
                return 0,u"没有需要继续的任务"
            cases_list = []
            for rec in ds:

                collection_id = rec['COLLECTION_ID']
                runtask_id = rec['COLLECTION_RUN_TASK_ID']
                c = self._cases_task_dict[runtask_id] = OrderedDict()
                c['runtask_id'] = runtask_id
                c['agent_id']=rec['AGENT_ID'].split(',')
                c['distribution_strategy_id'] = rec["DISTRIBUTION_STRATEGY_ID"]
                c['run_status'] = rec['RUN_STATUS']
                c['init_state'] = rec['INIT_STATE']
                c['case_num'] = rec['CASE_NUM']


                c['run_case_num'] = rec['RUN_CASE_NUM']
                c['run_case_num_success'] = rec['RUN_CASE_NUM_SUCCESS']
                c['run_case_num_fail'] = rec['RUN_CASE_NUM_FAIL']
                c['run_start_time'] = rec['RUN_START_TIME']
                c['run_end_time'] = rec['RUN_END_TIME']


                # 因为中断导致的已经分发，但是没有来得及应答的案例全部重新下发
                sql = "update sx_run_record set RESULT='STATE_UNTEST' where task_id = %d  and RESULT='STATE_DISTRIBUTED'" %(runtask_id)
                cF.executeCaseSQL(sql)

                #self._cases_task_send_uncomfirm_dict[runtask_id] = OrderedDict()
                #self._cases_task_send_uncomfirm_dict[runtask_id]["cases_list"] = []

                # 建立内存数据结构

                #sql = '''
                #       SELECT
                #            sx_run_record.RUN_RECORD_ID
                #            , sx_run_record.TASK_ID
                #            , sx_run_record.COLLECTION_ID
                #            , sx_run_record.COLLECTION_DETAIL_ID
                #            , sx_run_record.CASES_ID
                #            , sx_run_record.PARAM_DATA_ID
                #            , sx_run_record.CASES_PARAM_DATA_ID
                #            , sx_run_record.STEP
                #            , sx_run_record.CMDSTRING
                #            , sx_run_record.EXPECTED_VALUE
                #            , sx_run_record.SCRIPT_NAME
                #            , sx_run_record.ADAPTER_TYPE
                #            , sx_run_record.PRE_ACTION
                #            , sx_run_record.PRO_ACTION
                #        FROM
                #            sx_run_record
                #        WHERE 
                #            sx_run_record.task_id = %d and sx_run_record.RESULT = 'STATE_UNTEST'
                #        ORDER BY
                #            sx_run_record.COLLECTION_DETAIL_ID,sx_run_record.STEP
                #    ''' %(runtask_id)
                
                #ds1 = cF.executeCaseSQL(sql)
                #for rec1 in ds1:
                #    cases_list.append(rec1)        

                #self._cases_task_dict[runtask_id]['cases_list'] = cases_list
                #self._cases_task_send_uncomfirm_dict[runtask_id]['cases_list'] = []

            return 0,""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1,exc_info
    def getCasesList(self):
        '''
        查看任务表，将案例写入执行记录表
        '''
        try:
            sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_START'"
            ds = cF.executeCaseSQL(sql)
            if len(ds) <= 0:
                return 0,u"没有需要执行的测试任务"


            #逻辑层面的一个案例由多个可以分别执行的步骤绑定数据后执行，
            #而在任务调度里面，一个案例为一个最小的可执行单元
            cases_list = [] 

            cases_dict = OrderedDict()
            cases_steps_dict = OrderedDict()
            #cases_datas_dict = OrderedDict()
        
            for rec in ds:
            
                collection_id = rec['COLLECTION_ID']
                runtask_id = rec['COLLECTION_RUN_TASK_ID']
                c = self._cases_task_dict[runtask_id] = OrderedDict()
                c['runtask_id'] = runtask_id
                c['agent_id']=rec['AGENT_ID'].split(',')
                c['distribution_strategy_id'] = rec["DISTRIBUTION_STRATEGY_ID"]
                c['run_status'] = rec['RUN_STATUS']
                c['init_state'] = rec['INIT_STATE']

                #计算案例个数
                sql = "select count(distinct(collection_detail_id)) as case_num from sx_cases_collection_detail  where collection_id=%d" %(collection_id)
                ds = cF.executeCaseSQL(sql)
                case_num = ds[0]["case_num"]
                c['case_num'] = int(case_num)


                c['run_case_num'] = 0
                c['run_case_num_success'] = 0
                c['run_case_num_fail'] = 0
                c['run_start_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c['run_end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") #fixme
                

                self._cases_task_send_uncomfirm_dict[runtask_id] = OrderedDict()
                self._cases_task_send_uncomfirm_dict[runtask_id]["cases_list"] = []

                # 往sx_run_record写入对应数据
                # sql = "select a.param_data_id,c.cases_id,c.cases_detail_id,a.script_name,a.param_data,a.expected_value,a.pre_action,a.pro_action,c.step from sx_cases_detail_param_data a,sx_cases_collection_detail b,sx_cases_detail c  where a.param_data_id = b.param_data_id and a.cases_detail_id = c.cases_detail_id and b.collection_id = '%s' " %collection_id
                
                sql = '''
                    SELECT
                        sx_cases_param_data.CASES_ID
                        , sx_cases_param_data.PARAM_DATA_ID_STR
                        , sx_cases_param_data.CASES_PARAM_DATA_ID
                        , sx_cases_collection_detail.COLLECTION_DETAIL_ID
                    FROM
                        sx_cases_param_data
                        INNER JOIN sx_cases_collection_detail 
                        ON (sx_cases_param_data.CASES_PARAM_DATA_ID = sx_cases_collection_detail.PARAM_DATA_ID)
                    WHERE
                        sx_cases_collection_detail.COLLECTION_ID = %d
                    ''' %(collection_id)
                #sql = "select a.cases_id, a.cases_param_data_id,a.param_data_id_str,b.collection_detail_id from sx_cases_param_data a, sx_cases_collection_detail b where a.cases_param_data_id = b.PARAM_DATA_ID and b.COLLECTION_ID = %d" %collection_id
                ds1 = cF.executeCaseSQL(sql)

                # 批量插入再批量修改

                run_result_list = []
                for rec1 in ds1:
                    
                    param_data_id_list = rec1['PARAM_DATA_ID_STR'].split(',')
                    for j in param_data_id_list:
                        run_result_list.append("('RUN_TYPE_IMMI',%d,%d,%d,%d,%d,%d,'STATE_UNTEST')" %(runtask_id,collection_id,int(rec1['COLLECTION_DETAIL_ID']),int(rec1['CASES_ID']),int(rec1['CASES_PARAM_DATA_ID']),int(j)))

                # 写入运行记录表
                sql = "insert into sx_run_record(run_type,task_id,collection_id,collection_detail_id,cases_id,cases_param_data_id,param_data_id,result) values %s" %(','.join(run_result_list))
                print sql
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
                        , sx_cases_detail.CASES_DETAIL_ID
                        , sx_cases_detail.STEP
                        , sx_cases_detail.INPUT_STRING
			            , sx_cases_detail.ADAPTER_TYPE
			            , sx_cases_detail.PRE_ACTION
			            , sx_cases_detail.PRO_ACTION
                        , sx_cases_detail_param_data.PARAM_DATA
                        , sx_cases_detail_param_data.EXPECTED_VALUE
                        , sx_cases_detail_param_data.ACCOUNT_GROUP_ID
                    FROM
                        sx_run_record
                        INNER JOIN sx_cases_detail_param_data 
                            ON (sx_run_record.PARAM_DATA_ID = sx_cases_detail_param_data.PARAM_DATA_ID)
                        INNER JOIN sx_cases_detail 
                            ON (sx_cases_detail_param_data.CASES_DETAIL_ID = sx_cases_detail.CASES_DETAIL_ID)
                    WHERE
                        sx_run_record.task_id = %d
                ''' %(runtask_id)
                
                value_list = []
                ds1 = cF.executeCaseSQL(sql)
                for rec1 in ds1:
                    script_name = self.getScriptNameFromInputString(rec1['INPUT_STRING'])
                    value_list.append("(%d,%d,'%s',%d,'%s',%d,%d,%d,%d,%d,'%s',%d,'%s','%s','%s','%s','%s',%d,%d)" %(rec1['RUN_RECORD_ID'],rec1['PARAM_DATA_ID'],\
                        rec1['RUN_TYPE'],rec1['TASK_ID'],rec1['SERVER_IP'],rec1['COLLECTION_ID'],rec1['CASES_DETAIL_ID'],rec1['COLLECTION_DETAIL_ID'],\
                        rec1['CASES_ID'],rec1['CASES_PARAM_DATA_ID'],rec1['RESULT'],rec1['STEP'],script_name,rec1['ADAPTER_TYPE'],MySQLdb.escape_string(rec1['PRE_ACTION']),MySQLdb.escape_string(rec1['PRO_ACTION']),rec1['PARAM_DATA'],rec1['EXPECTED_VALUE'],rec1['ACCOUNT_GROUP_ID']))

                sql = "replace into sx_run_record(run_record_id,param_data_id,run_type,task_id,server_ip,\
                    collection_id,cases_detail_id,collection_detail_id,cases_id,cases_param_data_id,result,step,script_name,adapter_type,pre_action,pro_action,cmdstring,expected_value,account_group_id)\
                    values %s" %(','.join(value_list))
                print sql
                cF.executeCaseSQL(sql)

                # 建立内存数据结构

                #sql = '''
                #       SELECT
                #            sx_run_record.RUN_RECORD_ID
                #            , sx_run_record.TASK_ID
                #            , sx_run_record.COLLECTION_ID
                #            , sx_run_record.COLLECTION_DETAIL_ID
                #            , sx_run_record.CASES_ID
                #            , sx_run_record.PARAM_DATA_ID
                #            , sx_run_record.CASES_PARAM_DATA_ID
                #            , sx_run_record.STEP
                #            , sx_run_record.CMDSTRING
                #            , sx_run_record.ACCOUNT_GROUP_ID
                #            , sx_run_record.EXPECTED_VALUE
                #            , sx_run_record.SCRIPT_NAME
                #            , sx_run_record.ADAPTER_TYPE
                #            , sx_run_record.PRE_ACTION
                #            , sx_run_record.PRO_ACTION
                #        FROM
                #            sx_run_record
                #        WHERE 
                #            sx_run_record.task_id = %d
                #        ORDER BY
                #            sx_run_record.COLLECTION_DETAIL_ID,sx_run_record.STEP
                #    ''' %(runtask_id)
                
                #ds1 = cF.executeCaseSQL(sql)
                #for rec1 in ds1:
                #    cases_list.append(rec1)

                #self._cases_task_dict[runtask_id]['cases_list'] = cases_list
                #self._cases_task_send_uncomfirm_dict[runtask_id]['cases_list'] = []

                #修改状态
                sql = "update sx_cases_collection_run_task set run_status='%s',run_start_time='%s',case_num=%d where collection_run_task_id = %d " %(gl.TASK_STATE_PREPARE, self._cases_task_dict[runtask_id]['run_start_time'],int(case_num),runtask_id)
                print sql
                cF.executeCaseSQL(sql)

            return 0,""
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1,exc_info
    
    def run(self):
        '''
        处理任务的下发，状态的调整等等

        对于每一个任务，查看是否有未下发的任务；
        如果有，查看是否有空闲的agent，如果有就下发；没有就等到有再下发
        '''
        last_time = last_task_monitor_time = _alive_time = datetime.datetime.now()

        _alive_time_dict = {}
        _alive_time_dict["last_alive"] = _alive_time.strftime("%Y-%m-%d %H:%M:%S")

        alive_file = 'TestAgentServer_Alive.json'

        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        alive_file_path = os.path.join(application_path, alive_file)

        open(alive_file_path,'w').write(json.dumps(_alive_time_dict,ensure_ascii=False,encoding="utf8"))


        ret,msg = self.processUnFinishedCases()
        if ret < 0:
            print msg
            return

        try:
            #检测是否有需要执行的任务，然后是否有空闲的Agent，然后下发任务，处理任务结束的消息等等
            while True:
                if (gl.is_exit_all_thread == True):
                    break
                if (datetime.datetime.now() - _alive_time).seconds > 30:
                    # 每30秒写入一次，代表存活状态，否则将会被守护进程杀掉并重新启动
                    _alive_time_dict["last_alive"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    open(alive_file_path,'w').write(json.dumps(_alive_time_dict,ensure_ascii=False,encoding="utf8"))
                    _alive_time = datetime.datetime.now()

                for i, runtaskid in enumerate(self._cases_task_dict.keys()):

                    # 由于初始化问题的存在，一个测试环境只能让测试任务排队来执行，运行完一个任务以后才可以运行下一个任务。当有多个测试环境的时候，测试任务就可以并行了
                    # 所以这一点需要在以后加以改进（当有多个测试环境的时候）
                    if i != 0:
                        continue 

                    for client_id in self._cases_task_dict[runtaskid]['agent_id']:
                        if client_id in self._mqserver._clients_dict.keys() and 'state' in self._mqserver._clients_dict[client_id].keys() and self._mqserver._clients_dict[client_id]["state"] == gl.CLIENT_STATE_FREE:
                            if self._cases_task_dict[runtaskid]['init_state'] == 'STATE_UNINIT' or self._cases_task_dict[runtaskid]['init_state'] == '':
                                #发送初始化消息
                                init_env_msg = copy.copy(gl.init_env_msg)
                                init_env_msg["msg_body"]["task_id"] = str(runtaskid)
                                init_env_msg['msg_body']['env'] = 'fuyi' #fixme 以后需要根据任务表中的测试环境的信息加以变更
                                ret,msg = self._mqserver.SendMessage(client_id,init_env_msg)
                                if ret<0:
                                    print msg
                                self._cases_task_dict[runtaskid]['init_state'] == 'STATE_EXECUTE'
                                #fixme 可能需要将这个状态写回到数据库中
                                pass
                            elif self._cases_task_dict[runtaskid]['init_state'] == 'STATE_EXECUTE':
                                #继续等待
                                pass
                            else:
                                #开始下发案例
                                ret,msg = self.createCasesDistributeMsg(runtaskid,1) #每次拿一个出来下发
                                if ret < 0:
                                    print msg
                                    Logging.getLog().error(msg)
                                    continue
                                ret,msg = self._mqserver.SendMessage(client_id,msg)
                                if ret<0:
                                    print msg

                if (datetime.datetime.now() - last_task_monitor_time).seconds > 5:
                    last_task_monitor_time = datetime.datetime.now()
                    sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_START'"
                    ds = cF.executeCaseSQL(sql)
                    if len(ds) > 0:
                        print u"找到新任务"
                        ret,msg = self.getCasesList()
                        if ret < 0:
                            print msg

                    # 处理任务取消情况

                    sql = "select collection_run_task_id from sx_cases_collection_run_task where run_status = 'STATE_PREPARE' and cancel_flag = 1"
                    ds = cF.executeCaseSQL(sql)
                    for rec in ds:
                        runtaskid = rec['collection_run_task_id']
                        self._cases_task_dict[runtaskid]['run_end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        sql = "update sx_cases_collection_run_task set run_status='STATE_USER_CANCEL',run_start_time='%s',run_end_time='%s',run_during_time='%s' where collection_run_task_id='%s'" %(self._cases_task_dict[runtaskid]['run_start_time'],self._cases_task_dict[runtaskid]['run_end_time'],str(datetime.datetime.strptime(self._cases_task_dict[runtaskid]['run_end_time'],'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(self._cases_task_dict[runtaskid]['run_start_time'],'%Y-%m-%d %H:%M:%S')),runtaskid)
                        cF.executeCaseSQL(sql)
                        #取消任务
                        self._cases_task_dict.pop(runtaskid)
                    

        except:
            exc_info = cF.getExceptionInfo()
            print exc_info

def processTerm(signum, frame):
    gl.is_exit_all_thread = False
def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)
    print '''
    时溪自动化测试平台-Test Agent Server v0.6 2016.11.23.61
    (上海时溪信息技术有限公司）
    '''
    cF.readConfigFile()
    server = MQServer()
    server.setDaemon(True)
    server.start()

    print u"启动消息服务器成功"

    taskThread = task(server)
    taskThread.setDaemon(True)
    taskThread.start()
    print u"启动调度引擎成功"
    
    print u"初始化环境"

    '''
    ret,msg = cF.RunInitScript(0,'p')
    if ret < 0:
        print "Initialize env fail"
        print msg
        return
    '''
    while True:
        if server.isAlive() == False and taskThread.isAlive() == False:
            break

if __name__ == "__main__":
    main()