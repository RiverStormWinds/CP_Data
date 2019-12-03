# -*- coding:gbk -*-

# ���ļ��������ۺ����ϵͳ��ص�ҵ�����

from gl import GlobalLogging as Logging
import commFuncs as cF
import gl
import bizmod

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import time


def executeAccountInit():
    caseCount = 0
    succCount = 0
    failCount = 0

    sdk, msg = cF.connectT2(gl.g_ZHLCSystemSetting["T2Server"],"license.dat")
    if sdk == None:
        err = u"����T2������ʧ�ܣ�ԭ��:%s" % (msg)
        wx.MessageBox(err, u"���԰�������")
        Logging.getLog().critical(u"����T2������ʧ�ܣ�ԭ��:%s" % (msg))
        return -1, err

    # ѡ�п�����ذ���
    try:
        # sql = "select sno,sdkpos, sdkposdesc,funcidname,groupname,case_index,casename,funcid,cmdstring,expect_ret,pre_action,pro_action,account_group_id from tbl_cases where sdkpos = 'BA' and disableflag = 0 order by case_index"
        sql = "select sno,itempos, sdkposdesc,funcidname,groupname,case_index,casename,funcid,cmdstring,expect_ret,pre_action,pro_action,account_group_id from tbl_cases where itempos = '2.1.1' and disableflag = 0 order by case_index"
        ds = cF.executeCaseSQL(sql)

        for i, rec in enumerate(ds):
            sno = rec["sno"]
            itempos = rec["itempos"]
            funcidname = rec["funcidname"]
            groupname = rec["groupname"]
            case_index = rec["case_index"]
            funcid = rec["funcid"]
            cmdstring = rec["cmdstring"]
            casename = rec["casename"]
            expect_ret = rec["expect_ret"]
            pre_action = rec["pre_action"]
            pro_action = rec["pro_action"]
            account_group_id = rec["account_group_id"]
            cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))

            dir_name = "%s_%s_%s_%s_%s" % (sno, itempos, funcidname, groupname, case_index)
            Logging.getLog().info("ִ�п�������:%s" % dir_name)

            if case_index == 1:
                group_variable_dict = {}
                group_skip_cases_flag = False
            elif group_skip_cases_flag == True:
                failCount += 1
                caseCount += 1
                Logging.getLog().info("ִ�п�������:%s ������" % dir_name)
                continue

            if pre_action != "" and pre_action != None:
                ret, msg = cF.action_process(pre_action, group_variable_dict, [], funcid, cmdstring,
                                             str(account_group_id))
                if ret != 0:
                    failCount = failCount + 1
                    caseCount = caseCount + 1
                    err_info = u"��������������%s, �����ţ�%s, �������ƣ�%s, ���ܺ�:%s,ִ�н��:  ʧ��(--ǰ�ö���ʧ�� %s--)\n���: %s\n" % (
                        groupname, case_index, casename, funcidname, msg, cmdstring)
                    Logging.getLog().debug(err_info)
                    group_skip_cases_flag = True
                    continue
            if funcid == ('10200514'):
                time.sleep(2)
            cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
            # ִ�а���
            ret, msg = cF.ExecuteOneTestCase(sdk, funcid, cmdstring)

            if ret == 0 or ret == 1:
                dataset_list = cF.GetReturnRows(sdk)
                if ret == 0:
                    if int(expect_ret) != 0:
                        failCount += 1
                        caseCount += 1
                        err_info = u"��������������%s, �����ţ�%s, �������ƣ�%s, ���ܺ�:%s,ִ�н��:  ʧ��(���غ�������һ�£�����%d, ����0)\n���: %s\n" % (
                            groupname, case_index, casename, funcidname, int(expect_ret), cmdstring)
                        Logging.getLog().critical(err_info)
                        group_skip_cases_flag = True
                    else:
                        if pro_action != "" and pro_action != None:
                            ret, msg = cF.action_process(pro_action, group_variable_dict, dataset_list[0], funcid,
                                                         cmdstring, str(account_group_id))  # fixme rzxiao
                            if ret < 0:
                                failCount = failCount + 1
                                caseCount = caseCount + 1
                                err_info = u"��������������%s, �����ţ�%s, �������ƣ�%s, ���ܺ�:%s,ִ�н��:  ʧ��(--��������ʧ�� %s--)\n���: %s\n" % (
                                    groupname, case_index, casename, funcidname, msg, cmdstring)
                                Logging.getLog().critical(err_info)
                                group_skip_cases_flag = True
                            else:
                                succCount = succCount + 1
                                caseCount = caseCount + 1
                                Logging.getLog().info("ִ�п�������:%s �ɹ�!" % dir_name)
                        else:
                            succCount = succCount + 1
                            caseCount = caseCount + 1
                            Logging.getLog().info("ִ�п�������:%s �ɹ�!" % dir_name)
                else:  # ret == 1
                    rows_list = dataset_list[0]
                    if rows_list[0][1] == "error_no":
                        error_no = rows_list[1][1]
                    if error_no == '':  # �޷���ȷ��ȡerror_no
                        # �ж�����ʧ��
                        failCount += 1
                        caseCount += 1
                        err_info = u"��������������%s, �����ţ�%s, �������ƣ�%s, ���ܺ�:%s,ִ�н��:  ʧ��(ҵ�����ʧ�� %s--)\n���: %s\n" % (
                            groupname, case_index, casename, funcidname, msg, cmdstring)
                        Logging.getLog().critical(err_info)
                        group_skip_cases_flag = True
                    else:
                        if int(error_no) == int(expect_ret):  # ����Ԥ�ڣ��ж��ɹ�
                            succCount += 1
                            caseCount += 1
                            Logging.getLog().info("ִ�п�������:%s �ɹ�!" % dir_name)
                        else:
                            failCount += 1
                            caseCount += 1
                            msg = cF.GetErrorInfoFromReturnRows(dataset_list)
                            err_info = u"��������������%s, �����ţ�%s, �������ƣ�%s, ���ܺ�:%s,ִ�н��:  ʧ��(%s)\n���: %s\n" % (
                                groupname, case_index, casename, funcidname, msg, cmdstring)
                            Logging.getLog().critical(err_info)
                            group_skip_cases_flag = True
            else:
                failCount += 1
                caseCount += 1
                err_info = u"��������������%s, �����ţ�%s, �������ƣ�%s, ���ܺ�:%s,ִ�н��:  ʧ��(%s--)\n���: %s\n" % (
                    groupname, case_index, casename, funcidname, msg, cmdstring)
                Logging.getLog().critical(err_info)

    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        gl.threadQueue.put((-1, err, "executeAccountInit"))
        return -1, exc_info
    if (succCount == caseCount):  # ȫ���ɹ�
        print "ȫ���ɹ�"
        ret, msg = bizmod.replace_parameter(group_variable_dict["cif_account1"])
        info = u"���¶�ȡ�����ļ�"
        Logging.getLog().info(info)
        cF.readConfigFile()
        info = u"�û��ӳֲ�.."
        Logging.getLog().info(info)
        # �ӳֲ�
        bizmod.RunInitScript()
        gl.threadQueue.put((ret, "", "executeAccountInit"))  # ���ؽ��������У����߳̽������ȡ���н��
        info = "����%d������ȫ���ɹ�" % (caseCount)
        Logging.getLog().info(info)
        return 0, ""
    else:
        gl.threadQueue.put((-1, "", "executeAccountInit"))  # ���ؽ��������У����߳̽������ȡ���н��
        info = u"���������ɹ�%d����ʧ��%d�������黷��" % (succCount, failCount)
        Logging.getLog().info(info)
        return -1, info


def GetASYCfunctionTimeout(funcid):
    '''
    �����첽���ܺŻ�ȡ��ʱ����

    ����ϵͳ��Ҫ���õ�ֵ�����û���ҵ���Ӧ���ܺţ���û�о���ĳ�ʱ���þͷ���0
    '''
    if gl.g_interfaceTree == None:
        gl.g_interfaceTree = ET.parse("T2Interfaces.xml")
    root = gl.g_interfaceTree.getroot()
    xpath = ".//Interface[@funcid='%s']" % (funcid)
    elem = root.find(xpath)
    if elem == None:
        return -1, ""

    if elem.attrib.has_key("is_asyc"):
        timeout = elem.attrib["asyc_timeout"]
        return 0, timeout
    else:
        return -1, ""


if __name__ == '__main__':
    cF.readConfigFile()
    # time1  = time.time()
    print GetASYCfunctionTimeout("10201025")
    # print (time.time() - time1)
    pass
