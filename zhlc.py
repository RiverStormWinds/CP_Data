# -*- coding:gbk -*-

# 本文件放置与综合理财系统相关的业务代码

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
        err = u"连接T2服务器失败，原因:%s" % (msg)
        wx.MessageBox(err, u"测试案例运行")
        Logging.getLog().critical(u"连接T2服务器失败，原因:%s" % (msg))
        return -1, err

    # 选中开户相关案例
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
            Logging.getLog().info("执行开户案例:%s" % dir_name)

            if case_index == 1:
                group_variable_dict = {}
                group_skip_cases_flag = False
            elif group_skip_cases_flag == True:
                failCount += 1
                caseCount += 1
                Logging.getLog().info("执行开户案例:%s 被跳过" % dir_name)
                continue

            if pre_action != "" and pre_action != None:
                ret, msg = cF.action_process(pre_action, group_variable_dict, [], funcid, cmdstring,
                                             str(account_group_id))
                if ret != 0:
                    failCount = failCount + 1
                    caseCount = caseCount + 1
                    err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(--前置动作失败 %s--)\n入参: %s\n" % (
                        groupname, case_index, casename, funcidname, msg, cmdstring)
                    Logging.getLog().debug(err_info)
                    group_skip_cases_flag = True
                    continue
            if funcid == ('10200514'):
                time.sleep(2)
            cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
            # 执行案例
            ret, msg = cF.ExecuteOneTestCase(sdk, funcid, cmdstring)

            if ret == 0 or ret == 1:
                dataset_list = cF.GetReturnRows(sdk)
                if ret == 0:
                    if int(expect_ret) != 0:
                        failCount += 1
                        caseCount += 1
                        err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(返回和期望不一致，期望%d, 返回0)\n入参: %s\n" % (
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
                                err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(--后续动作失败 %s--)\n入参: %s\n" % (
                                    groupname, case_index, casename, funcidname, msg, cmdstring)
                                Logging.getLog().critical(err_info)
                                group_skip_cases_flag = True
                            else:
                                succCount = succCount + 1
                                caseCount = caseCount + 1
                                Logging.getLog().info("执行开户案例:%s 成功!" % dir_name)
                        else:
                            succCount = succCount + 1
                            caseCount = caseCount + 1
                            Logging.getLog().info("执行开户案例:%s 成功!" % dir_name)
                else:  # ret == 1
                    rows_list = dataset_list[0]
                    if rows_list[0][1] == "error_no":
                        error_no = rows_list[1][1]
                    if error_no == '':  # 无法正确提取error_no
                        # 判定案例失败
                        failCount += 1
                        caseCount += 1
                        err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(业务操作失败 %s--)\n入参: %s\n" % (
                            groupname, case_index, casename, funcidname, msg, cmdstring)
                        Logging.getLog().critical(err_info)
                        group_skip_cases_flag = True
                    else:
                        if int(error_no) == int(expect_ret):  # 符合预期，判定成功
                            succCount += 1
                            caseCount += 1
                            Logging.getLog().info("执行开户案例:%s 成功!" % dir_name)
                        else:
                            failCount += 1
                            caseCount += 1
                            msg = cF.GetErrorInfoFromReturnRows(dataset_list)
                            err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(%s)\n入参: %s\n" % (
                                groupname, case_index, casename, funcidname, msg, cmdstring)
                            Logging.getLog().critical(err_info)
                            group_skip_cases_flag = True
            else:
                failCount += 1
                caseCount += 1
                err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(%s--)\n入参: %s\n" % (
                    groupname, case_index, casename, funcidname, msg, cmdstring)
                Logging.getLog().critical(err_info)

    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        gl.threadQueue.put((-1, err, "executeAccountInit"))
        return -1, exc_info
    if (succCount == caseCount):  # 全部成功
        print "全部成功"
        ret, msg = bizmod.replace_parameter(group_variable_dict["cif_account1"])
        info = u"重新读取配置文件"
        Logging.getLog().info(info)
        cF.readConfigFile()
        info = u"用户加持仓.."
        Logging.getLog().info(info)
        # 加持仓
        bizmod.RunInitScript()
        gl.threadQueue.put((ret, "", "executeAccountInit"))  # 返回结果放入队列，供线程结束后读取运行结果
        info = "开户%d个案例全部成功" % (caseCount)
        Logging.getLog().info(info)
        return 0, ""
    else:
        gl.threadQueue.put((-1, "", "executeAccountInit"))  # 返回结果放入队列，供线程结束后读取运行结果
        info = u"开户案例成功%d个，失败%d个，请检查环境" % (succCount, failCount)
        Logging.getLog().info(info)
        return -1, info


def GetASYCfunctionTimeout(funcid):
    '''
    根据异步功能号获取超时设置

    返回系统需要设置的值，如果没有找到对应功能号，或没有具体的超时设置就返回0
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
