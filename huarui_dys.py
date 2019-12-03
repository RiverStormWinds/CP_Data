# -*- coding: gbk -*-

import commFuncs as cF
import gl
from gl import GlobalLogging as Logging
import Adapter.GW.GWAdapter as gw
import GlobalDict

#"ADAPTER_TYPE" is "SPLX_HUARUI_DYS"

def ConnectGw(serverAddr,serverPort,user,password):
    '''
    ��ȡһ��
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
    �����еķ���,��ʱ��cmdstringΪ�Ѿ��滻��������

    ����ֵ�������¼��ֿ����ԣ�

    ���� С��0���ж�����ʧ��
    ���� 0������ִ����ϣ���Ҫ��һ���ж���ͨ����ȡ���ؽ��������������ж���
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
    ������ֵ
    ���ܻ᷵���������ݼ���һ����ͨ����Ϣ��һ�������ݽ����
    :param dataset_dict:
    :return:
    """
    try:
        print "dataset_list####################################"
        print dataset_dict
        dataset_list = []
        if True:  # ����ͨ����Ϣ
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
    ���нӿڽű�
    :param system_id: ϵͳID
    :param funcid:
    :param cmdstring:
    :param runtaskid:
    :param run_record:
    :return:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
        log_info : ��־��Ϣ
        dataset_list: �м���ķ���ֵ�б����ں���������һ������
        return_json_string: �м������ֵ��json�ַ��������ظ�TestAgentServer����д�����ݿ�
        data_change_info_json_string:���ݿ�䶯��json�ַ��������ظ�TestAgentServer����д�����ݿ�
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
        Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
        return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (
            exc_info), log_info, [], return_json_string, data_change_info_json_string

