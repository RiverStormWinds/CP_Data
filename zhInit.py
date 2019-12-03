# -*- coding:gbk -*-

# 本文件放置与综合理财系统相关的业务代码
import os
from gl import GlobalLogging as Logging
import commFuncs_kcbp as cF_kcbp
import gl
import bizmod
import subprocess
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import time
import bizmod
import datetime
# import secrecy as sc
import commFuncs as cF
from xmlrpclib import ServerProxy

def executeAccountInit(num, ds, serverid, ip, port):
    caseCount = 0
    succCount = 0
    failCount = 0
    group_skip_cases_flag = False
    group_variable_dict = {}
    error_no = ""
    
    # for item in gl.g_connectSqlServerSetting.keys():
    #     if gl.g_connectSqlServerSetting[item]["servertype"] == 'p':
    #         serverid = item
    #         break

    hHandle, cli = cF_kcbp.KCBPCliInit(serverid)
    if hHandle < 0:
        Logging.getLog().info(u"初始化KCBPCli接口失败")
        return -1, u"初始化KCBPCli接口失败"

    # 选中开户相关案例
    try:
            # else:
            # sql = "select sno,itempos, sdkposdesc,funcidname,groupname,case_index,casename,funcid,cmdstring,expect_ret,pre_action,pro_action,account_group_id from tbl_cases where itempos = '3.1.3' and groupname = '%s' and disableflag = 0 order by case_index"%u'设置VIP客户（单核心）'

        custid = ""

        for i, rec in enumerate(ds):
            # if not rec["cmdstring"].__contains__(':'):
            #     rec["cmdstring"] = sc.decrypt_mode_cbc(rec["cmdstring"].encode('gbk'), 'abcdefghijklmnop')

            system_id = gl.current_system_id
            groupname = rec["CASE_NAME"]
            case_index = rec["STEP"]
            funcid = rec["FUNCID"]
            cmdstring = rec["CMDSTRING"]
            casename = rec["STEP_NAME"]
            expect_ret = rec["EXPECTED_VALUE"]
            pre_action = rec["PRE_ACTION"]
            pro_action = rec["PRO_ACTION"]
            account_group_id = rec["ACCOUNT_GROUP_ID"]
            if account_group_id == '':
                account_group_id = '0'

            cmdstring = cF_kcbp.GlobalParameterReplace(cmdstring, serverid)

            dir_name = "%s_%s_%s_%s_%s" % ("", "", "", groupname, case_index)
            Logging.getLog().info(u"执行开户案例:%s" % dir_name)

            if case_index == 1:
                group_variable_dict = {}
                group_skip_cases_flag = False
            elif group_skip_cases_flag == True:
                failCount += 1
                caseCount += 1
                Logging.getLog().info(u"执行开户案例:%s 被跳过" % dir_name)
                continue

            account_dict = gl.g_paramInfoDict.get(serverid).get(str(account_group_id))
            group_variable_dict.update(account_dict)

            # 前置条件
            if pre_action != "" and pre_action != None:
                ret, msg = cF_kcbp.action_process(pre_action, group_variable_dict, [], funcid, cmdstring, serverid)
                if ret != 0:
                    failCount = failCount + 1
                    caseCount = caseCount + 1
                    err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(--前置动作失败 %s--)\n入参: %s\n" % (
                    groupname, case_index, casename, "", msg, cmdstring)
                    Logging.getLog().debug(err_info)
                    group_skip_cases_flag = True
                    continue

            # if funcid==('10200514'):
            #    time.sleep(2)

            cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
            # 执行案例
            ret, code, level, msg, dataset = cF_kcbp.ExecuteOneTestCase(hHandle, cli, funcid, cmdstring)

            if ret == 0:
                # dataset_list = cF.GetReturnRows(sdk)
                # dataset = []
                # if (int(code) != 0):
                #     dataset.append(["code", "level", "msg"])
                #     dataset.append([code, level, msg])
                # else:
                #     dataset = cF.GetReturnResult(hHandle, cli)

                if i == 2:
                    try:
                        custid = dataset[1][1]
                    except BaseException, ex:
                        exc_info = cF_kcbp.getExceptionInfo()
                        Logging.getLog().error(exc_info)
                if ret == 0:
                    if int(expect_ret) != 0:
                        failCount += 1
                        caseCount += 1
                        err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(返回和期望不一致，期望%d, 返回0)\n入参: %s\n" % (
                        groupname, case_index, casename, "", int(expect_ret), cmdstring)
                        Logging.getLog().critical(err_info)
                        group_skip_cases_flag = True
                    else:
                        # 后置条件
                        if pro_action != "" and pro_action != None:
                            # ret,msg = cF.action_process(pro_action,group_variable_dict,dataset_list[0],funcid,cmdstring,str(account_group_id))  #fixme rzxiao
                            ret, msg = cF_kcbp.action_process(pro_action, group_variable_dict, dataset, funcid,
                                                         cmdstring, serverid)  # fixme rzxiao
                            if ret < 0:
                                failCount = failCount + 1
                                caseCount = caseCount + 1
                                err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(--后续动作失败 %s--)\n入参: %s\n" % (
                                groupname, case_index, casename, "", msg, cmdstring)
                                Logging.getLog().critical(err_info)
                                group_skip_cases_flag = True
                            else:
                                succCount = succCount + 1
                                caseCount = caseCount + 1
                                Logging.getLog().info(u"执行开户案例:%s 成功!" % dir_name)
                        else:
                            succCount = succCount + 1
                            caseCount = caseCount + 1
                            Logging.getLog().info(u"执行开户案例:%s 成功!" % dir_name)
            else:
                failCount += 1
                caseCount += 1
                err_info = u"测试用例组名：%s, 步骤编号：%s, 案例名称：%s, 功能号:%s,执行结果:  失败(%s--)\n入参: %s\n" % (
                groupname, case_index, casename, "", msg, cmdstring)
                Logging.getLog().critical(err_info)

    except BaseException, ex:
        exc_info = cF_kcbp.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info
    if (succCount == caseCount):  # 全部成功
        try:
            Logging.getLog().debug(u"全部成功")
            accountParam = {}
            if len(gl.g_connectSqlServerSetting) > 1:
                ret, accountParam = getAccountParam1(custid)
            else:
                ret, accountParam = getAccountParam2(custid)
            if ret == -1:
                # gl.threadQueue.put((-1, "fail to execute getAccountParam", "executeAccountInit"))
                return -1, accountParam
            ret, msg = bizmod.replace_parameter(accountParam, num)
            info = u"重新读取配置文件"
            Logging.getLog().info(info)
            # cF_kcbp.readConfigFile()

            accountParam["serverid"] = serverid
            sysdateParam = getSysConfigDate(serverid)
            if sysdateParam != None:  # 此处{}被更改为None
                accountParam["lastSysDate"] = sysdateParam["lastSysDate"]
                accountParam["sysdate"] = sysdateParam["sysdate"]
                accountParam["nextSysDate"] = sysdateParam["nextSysDate"]

            Logging.getLog().info(u"资质认证..")
            # bizmod.RunInitQualifications(accountParam)
            group_variable_dict.update(accountParam)
            cF_kcbp.RunInitScriptEx(group_variable_dict, "initQualifications.ini", path="init\\14288901937052FXJA\\")

            info = u"用户加持仓.."
            Logging.getLog().info(info)
            # 加持仓
            # bizmod.RunInitScript(accountParam)
            ret, msg = cF_kcbp.RunInitScriptEx(group_variable_dict, "initialise.ini", path="init\\14288901937052FXJA\\")
            if ret == -1:
                # gl.threadQueue.put((-1, msg, "executeAccountInit"))
                return -1, msg

            if len(gl.g_connectSqlServerSetting) > 1:
                # bizmod.RunInitScriptForRZRQ(accountParam)
                ret, msg = cF_kcbp.RunInitScriptEx(group_variable_dict, "initialise-rzrq.ini", path="init\\14288901937052FXJA\\")
            if ret == -1:
                # gl.threadQueue.put((-1, exc_info, "executeAccountInit"))
                return -1, msg

            Logging.getLog().info(u"同步资质认证、用户持仓数据..")
            for serverItem in gl.g_connectSqlServerSetting.keys():
                if gl.g_connectSqlServerSetting[serverItem]["servertype"] == 'v':
                    accountParam["serverid"] = serverItem
                    sysdateParam = getSysConfigDate(serverItem)

                    if sysdateParam != {}:
                        accountParam["lastSysDate"] = sysdateParam["lastSysDate"]
                        accountParam["sysdate"] = sysdateParam["sysdate"]
                        accountParam["nextSysDate"] = sysdateParam["nextSysDate"]

                    # bizmod.RunInitQualifications(accountParam)
                    group_variable_dict.update(accountParam)
                    ret, msg = cF_kcbp.RunInitScriptEx(group_variable_dict, "initQualifications.ini", path="init\\14288901937052FXJA\\")
                    if ret == -1:
                        # gl.threadQueue.put((-1, msg, "executeAccountInit"))
                        return -1, msg
                    # bizmod.RunInitScript(accountParam)
                    ret, msg = cF_kcbp.RunInitScriptEx(group_variable_dict, "initialise.ini", path="init\\14288901937052FXJA\\")
                    if ret == -1:
                        # gl.threadQueue.put((-1, msg, "executeAccountInit"))
                        return -1, msg

                    if len(gl.g_connectSqlServerSetting) > 1:
                        # bizmod.RunInitScriptForRZRQ(accountParam)
                        cF_kcbp.RunInitScriptEx(group_variable_dict, "initialise-rzrq.ini", path="init\\14288901937052FXJA\\")

                    break

            # gl.threadQueue.put((ret, "", "executeAccountInit"))  # 返回结果放入队列，供线程结束后读取运行结果
            info = u"开户%d个案例全部成功" % (caseCount)
            Logging.getLog().info(info)
            exc_info = u"账号组%s创建完毕" % (num)
            Logging.getLog().info(exc_info)
            #3是最后一组，之后同步数据
            if int(num) == 9:
                Logging.getLog().info(u"同步数据开始")
                ret, msg = jzjy_init_Sync_zk_data(ip, port)
                if ret!=0:
                    return -1, u"同步数据失败"
                Logging.getLog().info(u"同步数据结束")
            return 0, ""
        except BaseException, ex:
            exc_info = cF_kcbp.getExceptionInfo()
            Logging.getLog().critical(exc_info)
            # gl.threadQueue.put((-1, exc_info, "executeAccountInit"))
            return -1, exc_info
    else:
        # gl.threadQueue.put((-1, "", "executeAccountInit"))  # 返回结果放入队列，供线程结束后读取运行结果
        info = u"开户案例成功%d个，失败%d个，请检查环境" % (succCount, failCount)
        Logging.getLog().info(info)
        return -1, info

# def init_Sync_zk_data():
#     try:
#         homedir = os.getcwd()
#         path  = homedir + "\\Sync_zk\\Sync_ZK.bat"
        # path  = homedir + "\\Sync_zk\\1.bat"
        # p = subprocess.Popen("cmd.exe /d" + "%s abc"%path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#         p = subprocess.Popen("%s"%path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#         curline = p.stdout.readline()
#         while (curline != b''):
#             print(curline)
#             curline = p.stdout.readline()
#         p.wait()
#         print(p.returncode)
#         return 0, ""
#     except Exception as e:
#         print e
#         return -1, e
def getAccountParam2(custid):
    # sql ="select '8888' sys_operid_1,'8887' sys_operid_2,'3203705' operid_1,'3203711' operid_2,'4' serverid,   '0' server_z_id,   '4' server_p_id,   '12' server_v_id,  '11' server_b_id,  '90' server_q_id,  c.orgid,     c.trdpwd,    c.custid,    f1.fundid,   i.idno,f2.fundid credit_fundid,  '' bjhg_sz_clientid,   '' bjhg_sz_fundid, f1.bankcode,    f2.bankcode credit_bankcode,    s1.secuid sh_a_secuid, s3.secuid sz_a_secuid, s2.secuid sh_a_credit_secuid,   s4.secuid sz_a_credit_secuid,   s1.insidesecuid sh_a_inside_secuid,   s3.insidesecuid sz_a_inside_secuid,   s2.insidesecuid sh_a_credit_inside_secuid,  s4.insidesecuid sz_a_credit_inside_secuid from run .. customer c, run .. custbaseinfo i, run .. fundinfo f1,run .. fundinfo f2,run .. secuid s1,  run .. secuid s2,  run .. secuid s3,  run .. secuid s4 where c.custid = i.custid   and c.custid = f1.custid  and c.custid = f2.custid  and c.custid = s1.custid  and c.custid = s2.custid  and c.custid = s3.custid  and c.custid = s4.custid  and f1.creditflag = '0'   and f1.fundkind = '0'  and f2.creditflag = '1'   and f2.fundkind = '0'  and s1.market = '1'and s2.market = '1'and s3.market = '2'and s4.market = '2'and charindex('A', s1.secuid) = 1  and charindex('E', s2.secuid) = 1 and charindex('06', s3.secuid) != 1 and charindex('06', s4.secuid) = 1 and c.custid = '%s'"%custid
    sql = "select c.orgid,                                  " \
          "      c.serverid,                                " \
          "      c.trdpwd,                                  " \
          "      c.custid,                                  " \
          "      f1.fundid,                                 " \
          "      i.idno,                                    " \
          "      '' bjhg_sz_clientid,                       " \
          "      '' bjhg_sz_fundid,                         " \
          "      f1.bankcode,                               " \
          "      s1.secuid sh_a_secuid,                     " \
          "      s3.secuid sz_a_secuid,                     " \
          "      s1.insidesecuid sh_a_inside_secuid,        " \
          "      s3.insidesecuid sz_a_inside_secuid,        " \
          "      c.custname,                                " \
          "      i.idtype                                  " \
          " from run..customer c,                         " \
          "      run..custbaseinfo i,                     " \
          "      run..fundinfo f1,                        " \
          "      run..secuid s1,                          " \
          "      run..secuid s3                          " \
          "where c.custid = i.custid                        " \
          "  and c.custid = f1.custid                       " \
          "  and c.custid = s1.custid                       " \
          "  and c.custid = s3.custid                       " \
          "  and f1.creditflag = '0'                        " \
          "  and f1.fundkind = '0'                          " \
          "  and s1.market = '1'                            " \
          "  and s3.market = '2'                            " \
          "  and charindex('A', s1.secuid) = 1              " \
          "  and charindex('06', s3.secuid) != 1            " \
          "  and c.custid = '%s'                            " % custid

    ret, ds = bizmod.change_db(sql, 'p')

    # serverid = ''
    # for item in gl.g_connectSqlServerSetting.keys():
    #    if gl.g_connectSqlServerSetting[item]["servertype"] == 'p':
    #        serverid = item
    #        break

    for i, rec in enumerate(ds):
        if i > 0:
            break
        # server_p_id = serverid
        orgid = str(ds[0][0]).strip()
        # serverid = str(ds[0][1]).strip()
        trdpwd = str(ds[0][2]).strip()
        custid = str(ds[0][3]).strip()
        fundid = str(ds[0][4]).strip()
        idno = str(ds[0][5]).strip()
        bjhg_sz_clientid = str(ds[0][6]).strip()
        bjhg_sz_fundid = str(ds[0][7]).strip()
        bankcode = str(ds[0][8]).strip()
        sh_a_secuid = str(ds[0][9]).strip()
        sz_a_secuid = str(ds[0][10]).strip()
        sh_a_inside_secuid = str(ds[0][11]).strip()
        sz_a_inside_secuid = str(ds[0][12]).strip()
        custname = str(ds[0][13]).strip()
        idtype = str(ds[0][14]).strip()
        param = {
            # "serverid" : serverid,
            "orgid": orgid,
            "trdpwd": trdpwd,
            "custid": custid,
            "fundid": fundid,
            "idtype": idtype,
            "idno": idno,
            "bjhg_sz_clientid": bjhg_sz_clientid,
            "bjhg_sz_fundid": bjhg_sz_fundid,
            "bankcode": bankcode,
            "sh_a_secuid": sh_a_secuid,
            "sz_a_secuid": sz_a_secuid,
            "sh_a_inside_secuid": sh_a_inside_secuid,
            "sz_a_inside_secuid": sz_a_inside_secuid,
            "custname": custname}
        return 0, param


def getAccountParam1(custid):
    core = -1
    for server in gl.g_connectSqlServerSetting.keys():
        if gl.g_connectSqlServerSetting[server]["servertype"] == 'p':
            core = server
            break
    # sql ="select '8888' sys_operid_1,'8887' sys_operid_2,'3203705' operid_1,'3203711' operid_2,'4' serverid,   '0' server_z_id,   '4' server_p_id,   '12' server_v_id,  '11' server_b_id,  '90' server_q_id,  c.orgid,     c.trdpwd,    c.custid,    f1.fundid,   i.idno,f2.fundid credit_fundid,  '' bjhg_sz_clientid,   '' bjhg_sz_fundid, f1.bankcode,    f2.bankcode credit_bankcode,    s1.secuid sh_a_secuid, s3.secuid sz_a_secuid, s2.secuid sh_a_credit_secuid,   s4.secuid sz_a_credit_secuid,   s1.insidesecuid sh_a_inside_secuid,   s3.insidesecuid sz_a_inside_secuid,   s2.insidesecuid sh_a_credit_inside_secuid,  s4.insidesecuid sz_a_credit_inside_secuid from run .. customer c, run .. custbaseinfo i, run .. fundinfo f1,run .. fundinfo f2,run .. secuid s1,  run .. secuid s2,  run .. secuid s3,  run .. secuid s4 where c.custid = i.custid   and c.custid = f1.custid  and c.custid = f2.custid  and c.custid = s1.custid  and c.custid = s2.custid  and c.custid = s3.custid  and c.custid = s4.custid  and f1.creditflag = '0'   and f1.fundkind = '0'  and f2.creditflag = '1'   and f2.fundkind = '0'  and s1.market = '1'and s2.market = '1'and s3.market = '2'and s4.market = '2'and charindex('A', s1.secuid) = 1  and charindex('E', s2.secuid) = 1 and charindex('06', s3.secuid) != 1 and charindex('06', s4.secuid) = 1 and c.custid = '%s'"%custid
    sql = "select '8888' sys_operid_1,                      " \
          "      '8887' sys_operid_2,                       " \
          "(select top 1 operid from run..operator where orgid = c.orgid and status = '0' order by operid desc) operid_1," \
          "(select top 1 operid from run..operator where orgid = c.orgid and status = '0' order by operid asc) operid_2, " \
          "      c.serverid,                                " \
          "      c.orgid,                                   " \
          "      c.trdpwd,                                  " \
          "      c.custid,                                  " \
          "      f1.fundid,                                 " \
          "      i.idno,                                    " \
          "      f2.fundid credit_fundid,                   " \
          "      '' bjhg_sz_clientid,                       " \
          "      '' bjhg_sz_fundid,                         " \
          "      f1.bankcode,                               " \
          "      f2.bankcode credit_bankcode,               " \
          "      s1.secuid sh_a_secuid,                     " \
          "      s3.secuid sz_a_secuid,                     " \
          "      s2.secuid sh_a_credit_secuid,              " \
          "      s4.secuid sz_a_credit_secuid,              " \
          "      s5.secuid sh_b_secuid,        " \
          "      s6.secuid sz_b_secuid,        " \
          "      s7.secuid hgt_secuid, " \
          "      s9.secuid ggt_secuid, " \
          "      s8.secuid gz_secuid, " \
          "      s1.insidesecuid sh_a_inside_secuid,        " \
          "      s3.insidesecuid sz_a_inside_secuid,        " \
          "      s2.insidesecuid sh_a_credit_inside_secuid, " \
          "      s4.insidesecuid sz_a_credit_inside_secuid, " \
          "      c.custname,                                " \
          "      i.idtype,                                  " \
          "(select transacc from run..oftaacc where custid = c.custid and tacode = '3') jjzh_secuid_3, " \
          "(select transacc from run..oftaacc where custid = c.custid and tacode = '8') jjzh_secuid_8  " \
          " from run..customer c,                         " \
          "      run..custbaseinfo i,                     " \
          "      run..fundinfo f1,                        " \
          "      run..fundinfo f2,                        " \
          "      run..secuid s1,                          " \
          "      run..secuid s2,                          " \
          "      run..secuid s3,                          " \
          "      run..secuid s4,                          " \
          "      run..secuid s5,                           " \
          "      run..secuid s6,                           " \
          "      run..secuid s7,                           " \
          "      run..secuid s8,                           " \
          "      run..secuid s9                           " \
          "where c.custid = i.custid                        " \
          "  and c.custid = f1.custid                       " \
          "  and c.custid = f2.custid                       " \
          "  and c.custid = s1.custid                       " \
          "  and c.custid = s2.custid                       " \
          "  and c.custid = s3.custid                       " \
          "  and c.custid = s4.custid                       " \
          "  and c.custid = s5.custid                       " \
          "  and c.custid = s6.custid                       " \
          "  and c.custid = s7.custid                       " \
          "  and c.custid = s8.custid                       " \
          "  and c.custid = s9.custid                       " \
          "  and f1.creditflag = '0'                        " \
          "  and f1.fundkind = '0'                          " \
          "  and f2.creditflag = '1'                        " \
          "  and f2.fundkind = '0'                          " \
          "  and s1.market = '1'                            " \
          "  and s2.market = '1'                            " \
          "  and s3.market = '2'                            " \
          "  and s4.market = '2'                            " \
          "  and s5.market = 'D'                            " \
          "  and s6.market = 'H'                            " \
          "  and s7.market = '5'                            " \
          "  and s9.market = 'S'                            " \
          "  and s8.market = '9'                            " \
          "  and charindex('A', s1.secuid) = 1              " \
          "  and charindex('E', s2.secuid) = 1              " \
          "  and charindex('06', s3.secuid) != 1            " \
          "  and charindex('06', s4.secuid) = 1             " \
          "  and c.custid = '%s'                            " % custid

    ret, ds = bizmod.change_db(sql, 'p')
    if ret == -1:
        err = u'核心%s,数据库连接异常原因：%s' % (str(core), ds)
        Logging.getLog().critical(err)
        gl.threadQueue.put((-1, err, "executeAccountInit"))
        return -1, err

    for i, rec in enumerate(ds):
        if i > 0:
            break
        if len(rec[i]) == 0:
            ds[0][i] = None
        else:
            continue
    # serverid = ''
    # for item in gl.g_connectSqlServerSetting.keys():
    #    if gl.g_connectSqlServerSetting[item]["servertype"] == 'p':
    #        serverid = item
    #        break

    for i, rec in enumerate(ds):
        if i > 0:
            break
        sys_operid_1 = str(ds[0][0]).strip()
        sys_operid_2 = str(ds[0][1]).strip()
        operid_1 = str(ds[0][2]).strip()
        operid_2 = str(ds[0][3]).strip()
        serverid = str(ds[0][4]).strip()
        orgid = str(ds[0][5]).strip()
        trdpwd = str(ds[0][6]).strip()
        custid = str(ds[0][7]).strip()
        fundid = str(ds[0][8]).strip()
        idno = str(ds[0][9]).strip()
        credit_fundid = str(ds[0][10]).strip()
        if len(str(ds[0][11]).strip()) == 0:
            bjhg_sz_clientid = 'None'
        else:
            bjhg_sz_clientid = str(ds[0][11]).strip()
        if len(str(ds[0][12]).strip()) == 0:
            bjhg_sz_fundid = 'None'
        else:
            bjhg_sz_fundid = str(ds[0][12]).strip()
        if len(str(ds[0][13]).strip()) == 0:
            bankcode = 'None'
        else:
            bankcode = str(ds[0][13]).strip()
        if len(str(ds[0][14]).strip()) == 0:
            credit_bankcode = 'None'
        else:
            credit_bankcode = str(ds[0][14]).strip()
        sh_a_secuid = str(ds[0][15]).strip()
        sz_a_secuid = str(ds[0][16]).strip()
        sh_a_credit_secuid = str(ds[0][17]).strip()
        sz_a_credit_secuid = str(ds[0][18]).strip()
        sh_b_secuid = str(ds[0][19]).strip()
        sz_b_secuid = str(ds[0][20]).strip()
        hgt_secuid = str(ds[0][21]).strip()
        ggt_secuid = str(ds[0][22]).strip()
        gz_secuid = str(ds[0][23]).strip()
        sh_a_inside_secuid = str(ds[0][24]).strip()
        sz_a_inside_secuid = str(ds[0][25]).strip()
        sh_a_credit_inside_secuid = str(ds[0][26]).strip()
        sz_a_credit_inside_secuid = str(ds[0][27]).strip()
        custname = str(ds[0][28]).strip()
        idtype = str(ds[0][29]).strip()
        jjzh_secuid_3 = str(ds[0][30]).strip()
        jjzh_secuid_8 = str(ds[0][31]).strip()
        param = {"sys_operid_1": sys_operid_1,
                 "sys_operid_2": sys_operid_2,
                 # "operid_1" : operid_1,
                 # "operid_2" : operid_2,
                 # "serverid" : serverid,
                 "orgid": orgid,
                 "trdpwd": trdpwd,
                 "custid": custid,
                 "fundid": fundid,
                 "idtype": idtype,
                 "idno": idno,
                 "credit_fundid": credit_fundid,
                 "bjhg_sz_clientid": bjhg_sz_clientid,
                 "bjhg_sz_fundid": bjhg_sz_fundid,
                 "bankcode": bankcode,
                 "credit_bankcode": credit_bankcode,
                 "sh_a_secuid": sh_a_secuid,
                 "sz_a_secuid": sz_a_secuid,
                 "sh_a_inside_secuid": sh_a_inside_secuid,
                 "sz_a_inside_secuid": sz_a_inside_secuid,
                 "sh_a_credit_secuid": sh_a_credit_secuid,
                 "sz_a_credit_secuid": sz_a_credit_secuid,
                 "sh_b_secuid": sh_b_secuid,
                 "sz_b_secuid": sz_b_secuid,
                 "hgt_secuid": hgt_secuid,
                 "ggt_secuid": ggt_secuid,
                 "gz_secuid": gz_secuid,
                 "sh_a_credit_inside_secuid": gz_secuid,
                 "sz_a_credit_inside_secuid": gz_secuid,
                 "custname": custname,
                 "jjzh_secuid_3": jjzh_secuid_3,
                 "jjzh_secuid_8": jjzh_secuid_8}
        return 0, param


def getSysConfigDate(serverid):
    sql = "select lastsysdate,sysdate from sysconfig where status = '0' and serverid = '%s'" % serverid

    servertype = gl.g_connectSqlServerSetting[serverid]["servertype"]
    ret, ds = bizmod.change_db(sql, servertype)

    for i, rec in enumerate(ds):
        lastSysDate = str(ds[0][0]).strip()
        sysdate = str(ds[0][1]).strip()

        nextSysDate = (str(datetime.datetime.strptime(sysdate, '%Y%m%d') + datetime.timedelta(1))[:10]).replace('-', '')

        param = {"lastSysDate": lastSysDate, "sysdate": sysdate, "nextSysDate": nextSysDate}

        return param


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


def jzjy_init_Sync_zk_data(ip, port):
    try:
        s = ServerProxy("http://10.187.96.38:16001")
        if ip and port:
            s = ServerProxy("http://%s:%s"%(ip, port))
        ret, msg = s.init_Sync_zk_data()
        if ret != 0:
            return -1, u"同步数据失败 sync_zk"
        return 0, "success"
    except Exception as e:
        return -1, u"同步数据失败 sync_zk"


if __name__ == '__main__':
    jzjy_init_Sync_zk_data()
    # cF.readConfigFile()
    # # time1  = time.time()
    # print GetASYCfunctionTimeout("10201025")
    # # print (time.time() - time1)
    #
    # param = getSysConfigDate('4')
    # 加持仓
    # bizmod.RunInitScript(param)
    # gl.threadQueue.put((ret,"","executeAccountInit")) #返回结果放入队列，供线程结束后读取运行结果
    # info = "开户%d个案例全部成功" %(caseCount)
    # Logging.getLog().info(info)
    # return 0,""




    pass
