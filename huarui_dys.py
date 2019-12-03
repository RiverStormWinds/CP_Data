# -*- coding: gbk -*-

import commFuncs as cF
import gl
from gl import GlobalLogging as Logging
import Adapter.GW.GWAdapter as gw
import GlobalDict

#"ADAPTER_TYPE" is "SPLX_HUARUI_DYS"

def ConnectGw(serverAddr,serverPort,user,password):
    '''
    获取一个
    '''
    sdk = GlobalDict.get_value("dys_gw_sdk")
    if not sdk:
        sdk = gw.GWAdapter(serverAddr,serverPort,user,password)
        GlobalDict.set_value("dys_gw_sdk",sdk)
    ret, msg = sdk.InitInterface()
    if ret != 0:
        return None, msg
    return sdk, msg

def GetSdk():
    return GlobalDict.get_value("dys_gw_sdk")

def ExecuteOneTestCase(sdk, funcid, cmdstring):
    '''
    命令行的发送,此时的cmdstring为已经替换过参数了

    返回值存在以下几种可能性：

    返回 小于0，判定案例失败
    返回 0，案例执行完毕，需要进一步判定（通过获取返回结果与期望结果来判定）
    '''
    try:
        print funcid
        ret, msg = sdk.SendRequest(funcid, cmdstring, 10000)
        if ret < 0:
            return ret, msg
        return 0, "OK"
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog.error(exc_info)
        return -1, exc_info


def deal_with_dataset_list(dataset_dict):
    """
    处理返回值
    可能会返回两个数据集，一个是通用信息，一个是数据结果集
    :param dataset_dict:
    :return:
    """
    try:
        print "dataset_list####################################"
        print dataset_dict
        dataset_list = []
        if True:  # 返回通用信息
            data = {'message': str(dataset_dict)}
            data['field'] = list(dataset_dict.keys())
            dataset_list.append(data['field'] )

            values_list = []
            values_list.append(list(dataset_dict.values()))
            # for i in dataset_list[0][1:]:
            #     i_new = []
            #     for j in i:
            #         i_new.append(j.replace("'", "''"))
            #     if len(str(values_list).replace(' ', '')) <= 90000:
            #         values_list.append(i_new)
            data['values_list'] = values_list
            dataset_list.append(data['values_list'])
        if dataset_dict and dataset_dict.has_key("business_reject_text") and dataset_dict.has_key("reject_reason_code"):
            return -1, data, dataset_list
        return 0, data, dataset_list
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info, []

def DeInitInterface():
    sdk = GetSdk()
    sdk.DeInitInterface()
def RunScript(execEngine, system_id, funcid, cmdstring, runtaskid, run_record_id, expect_ret):
    """
    运行接口脚本
    :param system_id: 系统ID
    :param funcid:
    :param cmdstring:
    :param runtaskid:
    :param run_record:
    :return:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
        log_info : 日志信息
        dataset_list: 中间件的返回值列表，用于后续动作的一个参数
        return_json_string: 中间件返回值的json字符串，返回给TestAgentServer，并写入数据库
        data_change_info_json_string:数据库变动的json字符串，返回给TestAgentServer，并写入数据库
    """
    succ_flag = False
    msg = ""
    log_info = ""
    return_json_string = ""
    data_change_info_json_string = ""
    dataset_list = []
    sdk = GetSdk()
    try:
        dataset_dict = {}
        ret, msg = ExecuteOneTestCase(sdk, funcid, cmdstring)
        if ret == 0:
            dataset_dict = sdk.GetReturnResult()
            r, return_json_string , dataset_list= deal_with_dataset_list(dataset_dict)
            if int(expect_ret) != 0:
                succ_flag = False
            else:
                succ_flag = True
            if r < 0:
                succ_flag = False
        else:
            succ_flag = False

        if succ_flag == True:
            return 0, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
        else:
            return -1, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
        return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (
            exc_info), log_info, [], return_json_string, data_change_info_json_string

