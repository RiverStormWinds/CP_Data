# -*- coding:gbk -*-
import os
import MySQLdb
import subprocess
import commFuncs as cF
import time
import random
import hashlib
from lxml import etree
import gl
from gl import GlobalLogging as Logging
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy
import datetime
from datetime import date
from datetime import timedelta
import struct
import decimal
import itertools

import time
import collections
import subprocess
import struct
import datetime
import decimal
import logging
import itertools
from gl import GlobalLogging as Logging

# ok
def readKCXPqueue(param):
    """
    1. ����һ��kcxp_queue_read.exe ��ʹ��C/C++����
        ���Ϊ: kcxp IP���û��������룬������
        ִ�гɹ�������û�ж���������Ϣ�������̷�����Ϊ0��
        ִ��ʧ�ܣ����̷�����Ϊ-1��
        �ڲ��߼���
            ���ִ�гɹ�������һ��kcxp_queue.res�ļ����ڲ�Ϊ������Ϣ�б�һ������ռһ�У�
            ���ִ��ʧ�ܣ�����һ��kcxp_queue.res�ļ����ڲ�Ϊʧ��ԭ��������
    2. ����һ��ԭ�readKCXPQueue��KCXP ��ʶ�ţ��û��������룬������
        �ڲ��߼���
        1. ��KCXP��ʶ�ţ�ת��ΪIP��ַ����������������������ٵ���kcxp_queue_read.exe���̣���ȡ������Ϣ����kcxp_queue.res�ļ���
    """
    try:
        ip, username, password, queueNames = param.split(',')
        queueNames = queueNames.split(":")
        if queueNames:
            home_dir = os.getcwd()
            path = "%s\kcxp_queue_read\kcxp_queue.res" % home_dir
            for queueName in queueNames:
                ip = ip.strip()
                username = username.strip()
                password = password.strip()
                queueName = queueName.strip()
                exe_path = home_dir + "\kcxp_queue_read"
                # os.chdir(exe_path)
                cmd = "%s&cd %s&kcxp_queue_read.exe %s %s %s %s" % (
                    home_dir[0:2], exe_path, ip, username, password, queueName)
                print os.getcwd()
                sub = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                result_code = sub.stdout.read()
                print result_code
                if '0' in result_code and 'shagoffer messagedata is empty' not in result_code:
                    print queueName
                    if os.path.exists(path):
                        f = open(path, "r")
                        text = f.read()
                        f.close()
                        # f = open(path, "w")
                        text = text.split("\n")
                        fw = open(path, "w")
                        if text:
                            for i in text:
                                if i:
                                    i = i.replace("\n", '').replace("\x01", " ").replace("\x00", "")
                                    fw.write(i + "\n")
                        fw.close()
                        return 0, (u"%s �ɹ���ȡ����" % queueName,)
                if "-1" in result_code:
                    fw = open(path, "w")
                    fw.write(result_code)
                    fw.close()
                    Logging.getLog().critical(result_code)
                    return -1, (result_code,)
            if '0' in result_code and 'shagoffer messagedata is empty' in result_code:
                fw = open(path, "w")
                fw.write("")
                fw.close()
                Logging.getLog().critical(result_code)
                return 0, ("no message",)
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


# ok
def strncat(dst, src, n):
    dst += src[0:n]
    return dst


# ok
def memcpy(dst, src, n):
    dst = src[0:n]
    return dst


# ok
def sscanf(le, tmplen):
    tmplen = int(le, 16)
    return tmplen


# ok
def convert(le):
    x = ""
    y = ""
    oo = ""
    x = strncat(x, le[0:], 1)
    y = strncat(y, le[1:], 1)
    if ord(x) > 57 or ord(x) < 48:
        pass
    else:
        oo = x
    if ord(y) > 57 or ord(y) < 48:
        pass
    else:
        oo += y
    return oo


# ����sqlserver���ݿⷽ��
# ��ԭ��ٺϲ����ʵ
def change_db(sql, servertype):
    core = -1
    for server in gl.g_connectSqlServerSetting.keys():
        if gl.g_connectSqlServerSetting[server]["servertype"] == servertype:
            core = server
            break
    ret, conn = cF.ConnectToRunDB(core)
    if ret == -1:
        err = '����%s,���ݿ������쳣ԭ��%s' % (str(core), conn)
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()
    ds = []
    try:
        Logging.getLog().debug("change_db execute:in %s execute %s" % (servertype, sql))
        r = crs.execute(sql)

        if sql.upper().__contains__("SELECT") and not sql.upper().__contains__("INSERT") and not sql.upper().__contains__("INTO"):
            if r != 0:
                for i in r.fetchall():
                    ds.append(i)
                crs.close()
                conn.close()
                if len(ds) == 0:
                    return 0, ds
                else:
                    return 0, ds
        crs.close()
        conn.commit()
        conn.close()
        return 0, ds
        # if not sql.__contains__("select") and sql.__contains__("insert"):
        #    crs.close()
        #    conn.commit()
        #    conn.close()
        #    return 0,r
        # elif sql.__contains__("select") and sql.__contains__("insert"):
        #    crs.close()
        #    conn.commit()
        #    conn.close()
        #    return 0,r
        # else:
        #    if sql.__contains__("select"):
        #        if r != 0:
        #            for i in r.fetchall():
        #                ds.append(i)
        #    crs.close()
        #    conn.commit()
        #    conn.close()
        #    if sql.__contains__("select"):
        #        return 0,ds
        #    else:
        #        return 0,r
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, exc_info


# ����oracle���ݿⷽ��
# ��ԭ��ٺϲ����ʵ
def change_oracle(sql):
    ds = []
    conn = cF.ConnectOracleDB()
    if conn == -1:
        return -1, ""

    try:
        cursor = conn.cursor()
        r = cursor.execute(sql)
        # print r
        if sql.__contains__("select"):
            if r != 0:
                for i in r.fetchall():
                    ds.append(i)
        cursor.close()
        conn.commit()
        conn.close()
        if sql.__contains__("select"):
            return 0, ds
        else:
            return 0, r
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        cursor.close()
        conn.rollback()
        conn.close()
        return -1, exc_info


# ok
def change_banktranreg_status(param):
    date, cert_no = param.split(',')
    sql = "update hs_acct.gtja_custbanktransreg set bktrans_status = 2 where init_date = '%s' and serial_no = %s " % (
        date, cert_no)
    conn = cF.ConnectOracleDB()
    if conn == -1:
        return -1, ""

    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.close()
        conn.commit()
        conn.close()
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        cursor.close()
        conn.rollback()
        conn.close()
        return -1, exc_info


# ok
def get_account_content(param):
    client_id = param
    # ȥ��ǰ����λ03,��ʾ֤ȯ
    client_id = client_id[2:]

    # ȥ������0��ֱ��������һ�������ַ�
    try:
        for i in xrange(len(client_id)):
            if client_id[i] != '0':
                break;
        account_content = client_id[i:]
        return 0, (account_content,)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


# 10602706(����ͨȨ�޿�ͨ)
# ���н���run..secuid��regflag=1]
# ok
def change_secuid_regflag(param):
    custid = param
    sql = 'update run..secuid set regflag = 1 where custid=%s and market =1;' % (custid)
    # print sql
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 10602301(�����״ο���)��ִ��
# ok
def change_oftaacc_status(param):
    fund_company, custid = param.split(',')
    sql = 'update run..oftaacc set status = 0 where tacode = %s and custid = %s;' % (fund_company, custid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 10602311(������Χ��Ͷ����)
# �޸ķ��ճ��ܼ���
# ok
def change_custotherinfo_remark(param):
    custid = param
    sql = "update run..custotherinfo set remark ='68|1|20150625' where custid=%s;" % (custid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 10602312(������Χ��Ͷ����)���ݿ���custid,fund_company���sendsn
# ok
def get_oftimerconfig_entrustno_str(param):
    fund_company, custid, serial_no = param.split(',')
    sql = 'select sendsn from run..oftimerconfig where  tacode=%s and custid=%s and sno =%s;' % (
        fund_company, custid, serial_no)
    # print sql
    ret, r = change_db(sql, 'p')
    if ret < 0:
        return ret, (r,)
    sendsn = ','.join(r[0])
    return 0, (sendsn,)


# ǩ��ȫ�ֵķ��ս�ʾ��(10602313)--���Ͽ���ʱĬ����ǩ����Ҫ��ɾ��run..ofrisksign������
# ok
def del_ofrisksign(param):
    custid, orgid = param.split(',')
    sql = "delete from run..ofrisksign where custid =%s and orgid=%s;" % (custid, orgid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# ����������Ȩ������(10602810)---��ͨ���а������Ȩ�ޣ����˿ͻ����ʲ���ﵽ50��
# ok
def change_fundasset_fundbal(param):
    custid, orgid = param.split(',')
    sql = "update run..fundasset set fundlastbal=500000000.00,fundbal=500000000.00,fundavl=500000000.00 where custid =%s and orgid=%s;" % (
        custid, orgid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# ok
def demo_action(param):
    # ���������ʾ action д�������action ����Ϊ3������������Ҳ����������
    in1, in2, in3 = param.split(',')
    return 0, ('1', '2', '3')


# ���ʺ��г���ѯstock_account
# ok
def get_gtja_iwmbusinsecuflow_stock_account(param):
    cif_account, exchange_type = param.split(',')
    sql = "select stock_account from HS_ACCT.gtja_iwmbusinsecuflow where cif_account='%s' and exchange_type='%s'" % (
        cif_account, exchange_type)
    # print sql
    ret, r = change_oracle(sql)
    if ret < 0:
        return ret, (r,)
    sendsn = ','.join(r[0])
    # print sendsn
    return 0, (sendsn,)


# 10602706(����ͨȨ�޿�ͨ)
# ָ��״̬���ۺ���Ʒ����hs_acct.stockholder��regflag=1
# ok
def change_stockholder_regflag(param):
    client_id, stock_account = param.split(',')
    sql = "update hs_acct.stockholder set regflag = '1' where client_id='%s' and stock_account='%s'" % (
        client_id, stock_account)
    ret, r = change_oracle(sql)
    return ret, ("",)


# �ʵ��Թ������ύ(10201013)
# ok
def inset_cifprodrisklevel(param):
    cif_account = param
    sql1 = "select count(*) from HS_ACCT.cifprodrisklevel a where a.cif_account='%s'" % (cif_account)
    ret, r = change_oracle(sql1)
    if r[0][0] < 1:
        N = int(time.strftime("%Y"))
        M = time.strftime("%m")
        D = time.strftime("%d")
        CORP_BEGIN_DATE = str(N) + M + D
        CORP_END_DATE = str(N + 1) + M + D
        sql = "insert into HS_ACCT.cifprodrisklevel (CIF_ACCOUNT,PRODTA_NO,PAPER_ANSWER,CORP_RISK_LEVEL,CORP_BEGIN_DATE,CORP_END_DATE,PAPER_TYPE,ORGAN_FLAG,COMPANY_NO,PAPER_CODE,PAPER_SCORE,CLIENT_ID,BUSIN_ACCOUNT) values ('%s','D01' ,'104'|| chr(38 )||'4'|| '|105'||chr (38)|| '1|106'||chr (38)|| '2|107'||chr (38)|| '1|108'||chr (38)|| '1|109'||chr (38)|| '1|110'||chr (38)|| '1|111'||chr (38)|| '2|112'||chr (38)|| '1|','2' ,'%s', '%s','7' ,'0', '1','70000000000100000000000000000D01' ,'26.00', ' ',' ' )" % (
            cif_account, CORP_BEGIN_DATE, CORP_END_DATE)
        ret, r = change_oracle(sql)
    return ret, ("",)


# def change_stockholder_regflag():
# ��ѯgtja_iwmbusinsecuflow��init_date��serial_no
# ok
def get_gtja_iwmbusinsecuflow_serial_no(param):
    cif_account = param
    sql = "select init_date,serial_no from hs_acct.gtja_iwmbusinsecuflow  where cif_account='%s' and business_flag in (1189,1104) order by serial_no " % (
        cif_account)
    ret, r = change_oracle(sql)
    return 0, (r[0][0], r[0][1], r[1][0], r[1][1], r[2][0], r[2][1])


# ok
def GetToken(srt):
    try:
        if len(srt) > 4:
            index = 0
            le = ""
            retv = ""
            tmplen = 0
            strReturn = srt
            characteristic = "a5252c4ad4eca0cb1111652199e6c03dFF"
            retv = strncat(retv, "ND", 2)
            for i in range(21):
                for x in range(21):
                    if i == 0 or i == 1 or i == 19:
                        le = memcpy(le, strReturn[index:], 2)
                        tmplen = int(le, 16)
                        # tmplen=sscanf(le,tmplen)
                        retv = strncat(retv, strReturn[index:], 2 + tmplen)
                        index += 2 + tmplen
                        break
                    elif i == 8:
                        le = memcpy(le, strReturn[index:], 2)
                        tmplen = int(le, 10)
                        # tmplen=sscanf(le,tmplen)
                        retv = strncat(retv, strReturn[index:], 2 + tmplen)
                        # print strncat(retv,strReturn[index:],2+tmplen)
                        index += 2 + tmplen
                        retv = strncat(retv, "34", 2)
                        retv = strncat(retv, characteristic, len(characteristic))
                        break
                    elif i == 2:
                        retv = strncat(retv, "23", 2)
                        index += 2
                        break
                    elif i == 6:
                        le = memcpy(le, strReturn[index:], 2)
                        tmplen = int(le, 10)
                        # tmplen=sscanf(le,tmplen)
                        retv = strncat(retv, strReturn[index + 2:], tmplen)
                        # print strncat(retv,strReturn[index+2:],tmplen)
                        index += 2 + tmplen
                        break
                    else:
                        le = memcpy(le, strReturn[index:], 2)
                        tmplen = int(le, 10)
                        index += 2 + tmplen
                        break
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return ""
    return retv


# ת���û���¼token
# ok
def ConvertToken(srt):
    tokenInfo = ""
    FreeTokenInfo = GetToken(srt)
    index = 0
    le = ""
    szret = ""
    tmplen = 0
    xx = ""
    for i in range(8):
        for x in range(8):
            if i == 0:
                tokenInfo = strncat(tokenInfo, FreeTokenInfo[index:], 2)
                index += 2
                break
            elif i == 3:
                tokenInfo = strncat(tokenInfo, "24", 2)
                index += 2
                break
            elif i == 4:
                index += 2
                break
            elif i == 1 or i == 2 or i == 5 or i == 7:
                le = memcpy(le, FreeTokenInfo[index:], 2)
                # tmplen=sscanf(le,tmplen)
                tmplen = int(le, 16)
                tokenInfo = strncat(tokenInfo, FreeTokenInfo[index:], 2 + tmplen)
                index += 2 + tmplen
                break
            else:
                le = memcpy(le, FreeTokenInfo[index:], 2)
                xx = convert(le)
                print xx
                tmplen = int(xx, 10)
                index += 2 + tmplen
                break
    return 0, (tokenInfo,)


# ���֤���ֻ���MD5ת��
# ok
def ConvertMD5(param):
    id_no, mobile_tel = param.split(',')
    str = id_no + mobile_tel
    m = hashlib.md5()
    m.update(str)
    psw = m.hexdigest()
    md = psw.upper()
    return 0, (md,)


##��ȡ��ǰ����
# ok
def get_nowdate(param):
    NOW_DATE = time.strftime("%Y%m%d")
    return 0, (NOW_DATE,)


# �������(10602305)
# ok
def del_ofelectcontract(param):
    orgid, fundid, tacode, ofcode = param.split(',')
    fundid = int(fundid[6:])
    sql = "delete run..ofelectcontract where orgid='%s' and fundid=%s and tacode=%s and ofcode='%s'" % (
        orgid, fundid, tacode, ofcode)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# �滻ȫ�ֲ���
# ok
def replace_parameter(param, num):
    try:
        doc = etree.ElementTree(file="JZ_JZJY_AutoTestSetting.xml")
        root = doc.getroot()
        spath = "JZJYSystemSetting"
        s_elem_list = root.find(spath)
        for sElem in s_elem_list:
            if sElem.tag == "DisableDBCompare":
                continue
            if sElem.tag == "DisableExportHtml":
                continue
            # if sElem.attrib["id"] == '4' or sElem.attrib["id"] == '11' or sElem.attrib["id"] == '12':
            if sElem.attrib["type"] == 'p' or sElem.attrib["type"] == 'v':
                apath = "AccountGroup[@id='%d']" % num
                acc_elem_list = sElem.find(apath)

                for elem in acc_elem_list:
                    if param.has_key(elem.tag):
                        # print elem.tag,' :     ',elem.text
                        elem.text = param[elem.tag]
                        # elem.text = u'%s'%param[elem.tag]

        doc.write("JZ_JZJY_AutoTestSetting.xml", pretty_print=True, xml_declaration=True, encoding='utf-8')
        return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


# Ȩ������ǰȥ��Ȩ��
# ok
def del_fundinfo(param):
    custid = param
    sql = "select trdright from run..fundinfo where custid = '%s'" % (custid)
    ret, r = change_db(sql, 'p')
    if ret < 0:
        return ret, (r,)
    sendsn = ','.join(r[0])
    sendsn = sendsn.replace("*", "")
    sql1 = "update run..fundinfo set trdright ='%s' WHERE custid = '%s'" % (sendsn, custid)
    ret, r = change_db(sql1, 'p')
    return ret, ("",)


# ��ʼ���ֲ�
# ��ԭ��ٺϲ����ʵ
def RunInitScript(param):
    servertype = gl.g_connectSqlServerSetting[param["serverid"]]["servertype"]

    init_script_file = "initialise.sql"
    dict = {}
    f = open(init_script_file, 'r')
    lines = f.readlines()

    srt = "select seat,market from run..orgseat where orgid='%s' and market in ('1','2')" % (param['orgid'])
    Logging.getLog().debug(srt)
    ret, r = change_db(srt, servertype)
    param["sh_seat"] = r[0][0]
    param["sz_seat"] = r[1][0]

    for j, line in enumerate(lines):
        line = line.strip()
        Logging.getLog().debug(line)

        if line.startswith('--'):
            continue
        if len(line) == 0:
            continue

        sql = str(cF.GroupParameterReplace(line, param))
        Logging.getLog().debug(sql)

        ret, r = change_db(sql, servertype)

        # ��ʼ���ֲ�--���á�������ȯ


# ok
def RunInitScriptForRZRQ(param):
    servertype = gl.g_connectSqlServerSetting[param["serverid"]]["servertype"]

    init_script_file = "initialise-rzrq.sql"
    dict = {}
    f = open(init_script_file, 'r')
    Logging.getLog().debug("open %s" % (init_script_file))

    lines = f.readlines()

    srt = "select seat,market from run..orgseat where orgid='%s' and market in ('1','2')" % (param['orgid'])
    Logging.getLog().debug(srt)
    ret, r = change_db(srt, servertype)
    param["sh_seat"] = r[0][0]
    param["sz_seat"] = r[1][0]

    for j, line in enumerate(lines):
        line = line.strip()
        Logging.getLog().debug(line)
        if line.startswith('--'):
            continue
        if len(line) == 0:
            continue

        sql = str(cF.GroupParameterReplace(line, param))
        Logging.getLog().debug(sql)

        ret, r = change_db(sql, servertype)

        # ��ͨί�л�����Ϣ���޸ĺͼ۸���


# ok
def change_valuedate(stkcode):
    r = NOW_DATE = time.strftime("%Y%m%d")
    sql1 = "update run..stktrd set upddate='%s',intrdate='%s' where stkcode='%s'" % (str(r), str(r), stkcode)
    ret, r = change_db(sql1, 'p')
    sql2 = "select fixprice from run..stktrd where stkcode ='%s'" % (stkcode)
    ret, r = change_db(sql2, 'p')
    fixprice = str(r[0][0])
    return ret, (fixprice,)


# ��ԭ��ٺϲ����ʵ
def sqlserver_Database(sql):
    r = sql.rfind(',')
    servertype = sql[r+1:]
    sql1 = sql[:r]
    # servertype = sql[-1]
    # sql1 = sql[0:len(sql) - 2]
    flag = False
    if "zero" in sql1:
        sql1 = sql1.replace("zero","").strip()
        flag = True
    ret, r = change_db(sql1, servertype)
    if flag and not r:
        return 0, ("0",)
    if ret < 0:
        return ret, (r,)
    if sql.__contains__("select") and sql.__contains__("insert"):
        return ret, (r,)
    else:
        if sql1.__contains__("select") and not sql.__contains__("into"):
            fixprice = str(r[0][0])
            return ret, (fixprice,)
        else:
            return ret, (r,)


# ��ԭ��ٺϲ����ʵ
def oracle_Database(sql):
    ret, r = change_oracle(sql)
    if sql.__contains__("select"):
        if ret < 0:
            return ret, r
        sendsn = r[0][0]
        return ret, (sendsn,)
    else:
        return ret, (r,)


# ok
def GeneNewOrderid(param):
    market, serverid = param.split(',')
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    if market == '1':
        sql = "select orderid from run..orderrec where market='%s'" % (market)
        ds = []
        ret, r = change_db(sql, servertype)
        for x in r:
            ds.append(int(x[0]))
        new_orderid = str(max(ds) + 1)
        return ret, (new_orderid,)
    elif market == '2':
        sql = "select orderid from run..orderrec where market='%s'" % (market)
        ds = []
        ret, r = change_db(sql, servertype)
        for x in r:
            if x[0].__contains__('G'):
                ds.append(int(x[0].split('G')[1]))
            else:
                continue
        fix_orderid = str(max(ds) + 1)
        new_orderid = 'G' + fix_orderid
        return ret, (new_orderid,)
    else:
        return -1, (u'δ������ȷ���г�����',)


# ok
def GeneNewPromisesno(param):
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select promisesno from run..orderrec_ext where serverid = '%s'" % (serverid)
    ds = []
    ret, r = change_db(sql, servertype)
    for x in r:
        ds.append(int(x[0]))
    sno = 1
    while sno < 999999 and (sno in ds):
        sno += 1
    else:
        new_promisesno = sno
    return ret, (new_promisesno,)


# ok
def Generate_random_sno(param):
    '''
    ��ȡ1000���ڵ������
    '''
    sysdate, serverid = param.split(',')
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select batchsno from run..closeorder where serverid='%s' and sysdate='%s'" % (serverid, sysdate)
    bs = []
    ret, r = change_db(sql, servertype)
    if len(r) == 0 or ret < 0:
        new_sno = random.randint(0, 1000)
    else:
        for x in r:
            bs.append(int(x[0]))
        new_sno = random.randint(0, 1000)
        while new_sno in bs:
            new_sno = random.randint(0, 1000)
            # new_sno = str(max(bs) + 1)
    return 0, (new_sno,)


# ok
def GeneNewSno(param):
    '''
    ��ȡ���ظ�����ȯԤԼ���
    Args:
        param: ��Ρ�"sysdate,serverid"

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    '''
    sysdate, serverid = param.split(',')
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select sno from run..creditreservestk  where serverid = '%s' and sysdate = '%s'" % (serverid, sysdate)
    ds = []
    ret, r = change_db(sql, servertype)
    if ret < 0:  # ���û�����ݣ��ͷ���1
        return 0, (1,)
    for x in r:
        ds.append(int(x[0]))
    if len(ds) == 0:
        new_sno = 1
    else:
        new_sno = str(max(ds) + 1)
    return ret, (new_sno,)


# ok
def GeneNewTable(param):
    '''
    ��ȡ�����ض���ʽ�ı���
    Args:
        param: ��Ρ�"table"

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    '''
    try:
        table = param
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        new_table = table + "_" + str(year) + "_" + '{:0>2}'.format(str(month))
        return 0, (new_table,)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


# ok
def GeneNewExterSno(param):
    '''
    ��ȡ���ظ���ԤԼ���
    Args:
        param: ��Ρ�"sysdate,serverid"

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    '''
    sysdate, orgid, custid, serverid = param.split(',')
    s_str = '3_' + sysdate + '_' + orgid + '_' + custid
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select extersno from run..logunicounter where serverid = '%s' and sysdate = '%s' and extersno like '%s'" % (
        serverid, sysdate, '%' + s_str + '%')
    ds = []
    ret, r = change_db(sql, servertype)
    if ret < 0:  # ���û�����ݣ��ͷ���1
        return 0, (s_str + '_' + '00000001',)
    for x in r:
        ds.append(int(x[0].split('_')[-1]))
    if len(ds) == 0:
        new_extersno = s_str + '_' + '00000001'
    else:
        new_extersno = s_str + '_' + '{:0>8}'.format(str(max(ds) + 1))
    return ret, (new_extersno,)


# ok
def GeneNewBsno(param):
    '''
    ��ȡ���ظ��ı��ۻع�δ���ں�Լ���
    Args:
        param: ��Ρ�"serverid"

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    '''
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select sno from run..bjhg_contract  where serverid = '%s'" % serverid
    ds = []
    ret, r = change_db(sql, servertype)
    for x in r:
        ds.append(int(x[0]))
    new_sno = str(max(ds) + 1)
    return ret, (new_sno,)


# ok
def GeneNewFundid(param):
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select fundid from run..fundinfo where serverid = '%s' order by fundid" % (serverid)
    ds = []
    ret, r = change_db(sql, servertype)
    for x in r:
        ds.append(int(x[0]))
    new_fundid = str(max(ds) + 1)
    return ret, (new_fundid,)


# ok
def GeneNewMatchcode(param):
    try:
        market, serverid = param.split(',')
        servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
        sql = "select matchcode from run..bjhg_contract_sz where market='%s' and serverid='%s'" % (market, serverid)
        ds = []
        ret, r = change_db(sql, servertype)
        for x in r:
            if x[0] == '':
                continue
            ds.append(int(x[0]))
        if len(ds) == 0:
            new_matchcode = 1
        else:
            new_matchcode = str(max(ds) + 1)
        return ret, (new_matchcode,)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


# ok
def GeneNewBorderid(param):
    market, serverid = param.split(',')
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select orderid from run..bjhg_contract_sz where market='%s'" % (market)
    ds = []
    ret, r = change_db(sql, servertype)
    try:
        for x in r:
            if x[0][:1] == 'G' and x[0].split('G')[1].strip().isdigit() == True:
                ds.append(int(x[0].split('G')[1]))
            else:
                continue
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)
    if len(ds) == 0:
        new_Borderid = 'G1'
    else:
        fix_orderid = str(max(ds) + 1)
        new_Borderid = 'G' + fix_orderid
    return ret, (new_Borderid,)


# ok
def GeneNewApplysno(param):
    try:
        sysdate, serverid = param.split(',')
        servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
        sql = "select applysno from run..loan_applylist where serverid='%s'" % (serverid)
        ds = []
        ret, r = change_db(sql, servertype)
        for x in r:
            if str(x[0])[8:] == '':
                continue
            if str(x[0])[:4] == sysdate[:4]:
                ds.append(int(str(x[0])[8:]))
            else:
                continue
        if ds == []:
            s = str(1)
        else:
            y = len(str(max(ds) + 1))
            s = str(max(ds) + 1)
        new_applysno = sysdate + '{:0>6}'.format(s)
        return ret, (new_applysno,)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


# ��ԭ��ٺϲ����ʵ
def AddStockAsset(param):
    """
    ���ӹ�Ʊ�ʲ�

    Args:
        param: ��Ρ�"serverid,operid_1,operid_2,trdpwd,orgid,fundid,secuid,market,stkcode,count,account_group_id"

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    """  # ����һ��Ԫ��(cmdstring,pre_action,pro_action,account_group_id)�б�
    serverid, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count, account_group_id = param.split(
        ',')
    cmdstring_list = []

    cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:%s,fundid:%s,secuid:%s,market:%s,stkcode:%s,stkeffect:%s,cost:10,remark:" % (
        serverid, operid_1, trdpwd, orgid, fundid, secuid, market, stkcode, count)
    pro_action = "save_param:sno = [0][0]"
    cmdstring_list.append((cmdstring, "", pro_action, account_group_id))

    cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150420,g_stationaddr:001641AA2350,operdate:@sys_date@,sno:@sno@,action:1,afmremark:" % (
        serverid, operid_2, trdpwd)
    cmdstring_list.append((cmdstring, "", "", account_group_id))

    ret, msg = RunTest(serverid, cmdstring_list)
    if ret < 0:
        error_msg = u"���ⷢ��: %s" % msg
        Logging.getLog().error(error_msg)
        return ret, (msg,)
    else:
        return 0, ("",)


# ��ԭ��ٺϲ����ʵ
def AddETFBasketStockAsset(param):
    """
    ����ETF���ӹ�Ʊ�ʲ�

    Args:
        param: ��Ρ�"serverid,operid_1,operid_2,trdpwd,orgid,fundid,secuid,market,stkcode,count,account_group_id"

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    """
    # ����һ��Ԫ��(cmdstring,pre_action,pro_action,account_group_id)�б�
    serverid, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count, account_group_id = param.split(
        ',')
    cmdstring_list = []

    sql = "select stkcode,amount,marketstk from etfcomponentinfo where ofcode='%s' " % stkcode
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    ret, ds = change_db(sql, servertype)
    if ret < 0:
        return -1, (ds,)

    if len(ds) == 0:
        Logging.getLog().error(u"%s δ���ҵ��ɷݹ�" % stkcode)
        return -1, (u"û���ҵ��ɷݹ�",)

    for rec in ds:
        if str(rec[1]) == '0':  # �ֽ�����Ĺ�Ʊ����������Ҫ���ӳֲ�
            continue
        sql1 = "select secuid from run..secuid where custid=(select custid from run..secuid where secuid='%s' and market='%s') and market='%s' and creditflag=0" % (
            secuid, market, rec[2])
        ret1, ds1 = change_db(sql1, servertype)
        current_secuid = ds1[0][0].strip()

        cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:%s,fundid:%s,secuid:%s,market:%s,stkcode:%s,stkeffect:%s,cost:10,remark:" % (
            serverid, operid_1, trdpwd, orgid, fundid, current_secuid, rec[2], rec[0].strip(), str(rec[1] * int(count)))
        pro_action = "save_param:sno = [0][0]"
        cmdstring_list.append((cmdstring, "", pro_action, account_group_id))

        cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150420,g_stationaddr:001641AA2350,operdate:@sys_date@,sno:@sno@,action:1,afmremark:" % (
            serverid, operid_2, trdpwd)
        cmdstring_list.append((cmdstring, "", "", account_group_id))

    ret, msg = RunTest(serverid, cmdstring_list)
    if ret < 0:
        Logging.getLog().error(u"���ⷢ��: %s" % msg)
        return ret, (msg,)
    else:
        return 0, ("",)


# ok
def RunTest(serverid, cmdstring_list):
    """
    ����ǰ���м�¼����Ϊxml��ʽ

    Args:
        running_dir: ����Ŀ¼

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
    """
    group_variable_dict = {}

    hHandle, cli = cF.KCBPCliInit(serverid)
    if hHandle < 0:
        return -1, u"��ʼ��KCBPCli�ӿ�ʧ��"
    try:
        for i in xrange(len(cmdstring_list)):
            cmdstring = cmdstring_list[i][0]
            pre_action = cmdstring_list[i][1]
            pro_action = cmdstring_list[i][2]
            account_group_id = str(cmdstring_list[i][3])

            account_dict = gl.g_paramInfoDict.get(serverid).get(account_group_id)
            group_variable_dict.update(account_dict.items())

            cmdstring = cF.GlobalParameterReplace(cmdstring, str(serverid))
            cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)

            if (pre_action != ""):
                ret, msg = cF.action_process(serverid, pre_action, group_variable_dict, [], "", cmdstring)
                if ret != 0:
                    Logging.getLog().error("ǰ�ö���err,msg=%s" % msg)
                    cF.KCBPCliExit(hHandle, cli)
                    return ret, msg

            cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
            Logging.getLog().debug(cmdstring)
            ret, code, level, msg = cF.SendRequest(hHandle, cli, cmdstring)
            if ret == 0:
                dataset = []
                if (int(code) != 0):
                    dataset.append(["code", "level", "msg"])
                    dataset.append([code, level, msg])
                else:
                    dataset = cF.GetReturnResult(hHandle, cli)
                if (int(code) == 0):
                    if (pro_action != ""):
                        ret, msg = cF.action_process(serverid, pro_action, group_variable_dict, dataset, "",
                                                     cmdstring)  # fixme xiaorz
                        if ret != 0:
                            cF.KCBPCliExit(hHandle, cli)
                            return ret, msg
                else:
                    cF.KCBPCliExit(hHandle, cli)
                    return -1, msg
            else:
                cF.KCBPCliExit(hHandle, cli)
                return -1, msg
        return 0, ""
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        cF.KCBPCliExit(hHandle, cli)
        return -1, exc_info


# ��ԭ��ٺϲ����ʵ
def GeneNewSecuid(param):
    if param.count(',') == 2 or param.split(',')[-1] == '0':
        if param.count(',') == 2:
            serverid, market, creditflag = param.split(',')
        else:
            serverid, market, creditflag, secucls = param.split(',')
        sql = ""
        par = ""
        if market == '1':
            if creditflag == '1':
                sql = "select top 1 secuid from secuid where market='1'  and secuid like 'E0%%' order by secuid desc"
            elif creditflag == '0':
                sql = "select top 1 secuid from secuid where market='1'  and secuid like 'A%' and secuid not like 'A9%' order by secuid desc"
        elif market == 'D':
            if creditflag == '1':
                sql = "select top 1 secuid from secuid where market='D'  and secuid like 'C1%%' order by secuid desc"
            elif creditflag == '0':
                sql = "select top 1 secuid from secuid where market='D'  and secuid like 'C1%' and secuid not like 'C9%' order by secuid desc"
        elif market == '2' or market == '9' or market == 'H':
            if creditflag == '1':
                sql = "select top 1 secuid from secuid where market='2'  and secuid like '06%%' order by secuid desc"
            elif creditflag == '0':
                sql = "select top 1 secuid from secuid where market='2'  and secuid like '00%%' order by secuid desc"

        servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
        if sql != "":
            ret, r = change_db(sql, servertype)
            if ret < 0:
                return ret, (u"sql%sִ��ʧ��" % sql,)
            else:
                if market == '1' or market == 'D':
                    s = r[0][0]

                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                elif market == 'D':
                    s = r[0][0]
                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                elif market == '2' or market == '9' or market == 'H':
                    s = r[0][0]
                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                return -1, (u"�ݲ�֧�ֵ���η�ʽ",)
        else:
            return -1, (u"�ݲ�֧�ֵ���η�ʽ",)
    elif param.count(',') == 3 and param.split(',')[-1] == '1':
        serverid, market, creditflag, secucls = param.split(',')
        sql = ''
        if market == '1':
            sql = "select top 1 secuid from secuid where market='1'  and secuid like 'F0%%' order by secuid desc"
        elif market == '2':
            sql = "select top 1 secuid from secuid where market='2'  and secuid like '00%%' order by secuid desc"

        servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
        if sql != "":
            ret, r = change_db(sql, servertype)
            if ret < 0:
                if market == '1':
                    secuid = 'F' + '{:0>9}'.format('1')
                    return 0, (secuid,)
                elif market == '2':
                    secuid = '0' + '{:0>9}'.format('1')
                    return 0, (secuid,)
                    # return ret, (u"sql%sִ��ʧ��" %sql,)
            else:
                if market == '1':
                    s = r[0][0]

                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                elif market == '2':
                    s = r[0][0]
                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                return -1, (u"�ݲ�֧�ֵ���η�ʽ",)
        else:
            return -1, (u"�ݲ�֧�ֵ���η�ʽ",)


# ok
def GeneNewBankAccid(param):
    serverid, bankcode = param.split(',')
    sql = "select top 1 bankid from banktranid where bankcode ='%s' order by bankid desc " % (bankcode)
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    ret, r = change_db(sql, servertype)
    if ret < 0:
        return ret, (u"sql%sִ��ʧ��" % sql,)
    s = r[0][0]
    newAccid = str(int(s) + 1)
    return 0, (newAccid,)


# ok
def GeneRZRQContractNO(param):
    custid, sysdate = param.split(',')
    RZRQContractNo = str(custid) + '-' + sysdate
    print RZRQContractNo
    return 0, (RZRQContractNo,)


# ok
def GeneRZRQNewCreditDebtsSno(param):
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select top 1 sno, ordersno, orderid from run..creditdebts order by sno desc"
    # sql = 'select top 1 sno, ordersno, orderid from run..creditdebts order by sno desc'
    ret, r = change_db(sql, servertype)
    if r == []:
        newSno = 1
        newOrderSno = 1
        newOrderId = 1
    else:
        newSno = int(r[0][0]) + 1
        newOrderSno = int(r[0][1]) + 1
        newOrderId = r[0][2].strip()

    orderStr = ''
    orderId = ''
    for item in str(newOrderId):
        if item not in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            orderStr = orderStr + item
        else:
            orderId = orderId + item

    newOrderId = orderStr+str(int(orderId)+1)

    return ret, (newSno, newOrderSno, newOrderId)


# ok
def getSysConfigDate(param):
    serverid = param
    sql = "select lastsysdate,sysdate from sysconfig where status = '0' and serverid = '%s'" % serverid

    servertype = gl.g_connectSqlServerSetting[serverid]["servertype"]
    ret, ds = change_db(sql, servertype)

    if len(ds) > 0:
        lastSysDate = str(ds[0][0]).strip()
        sysdate = str(ds[0][1]).strip()

        nextSysDate = (str(datetime.datetime.strptime(sysdate, '%Y%m%d') + datetime.timedelta(1))[:10]).replace('-', '')

        return ret, (lastSysDate, sysdate, nextSysDate)
    return -1, '', '', ''


# ok
def GetNewDate(param):
    """
    ����һ�����ںͲ�����������һ���µ�����

    Args:
        param: �ַ�����ʽ����� "yyyymmdd,���ֵ"
            ���磺�� 20151015 �ĺ�һ�� GetNewDate("20151015,1")
                   �� 20151015 ��ǰһ�� GetNewDate("20151015,-1")

    Returns:
        һ��Ԫ�飨ret��(newdate,)����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        newdate :������������
    """
    try:
        orig_date, delta = param.split(',')
        d = date(int(orig_date[0:4]), int(orig_date[4:6]), int(orig_date[6:8]))
        d = d + timedelta(days=int(delta))
        return 0, (d.strftime('%Y%m%d'),)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


# ok
def dbfreader(f):
    try:
        """Returns an iterator over records in a Xbase DBF file.
    
        The first row returned contains the field names.
        The second row contains field specs: (type, size, decimal places).
        Subsequent rows contain the data records.
        If a record is marked as deleted, it is skipped.
    
        File should be opened for binary reads.
    
        """
        # See DBF format spec at:
        #     http://www.pgts.com.au/download/public/xbase.htm#DBF_STRUCT

        numrec, lenheader = struct.unpack('<xxxxLH22x', f.read(32))
        numfields = (lenheader - 33) // 32

        fields = []
        for fieldno in xrange(numfields):
            name, typ, size, deci = struct.unpack('<11sc4xBB14x', f.read(32))
            name = name.replace('\0', '')  # eliminate NULs from string
            fields.append((name, typ, size, deci))
        yield [field[0] for field in fields]
        yield [tuple(field[1:]) for field in fields]

        terminator = f.read(1)
        # assert terminator == '\r'

        fields.insert(0, ('DeletionFlag', 'C', 1, 0))
        fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in fields])
        fmtsiz = struct.calcsize(fmt)
        for i in xrange(numrec):
            record = struct.unpack(fmt, f.read(fmtsiz))
            if record[0] != ' ':
                continue  # deleted record
            result = []
            for (name, typ, size, deci), value in itertools.izip(fields, record):
                # value = str(value).decode("utf-8").encode('gb2312')
                if name == 'DeletionFlag':
                    continue
                if typ == "N":
                    value = value.replace('\0', '').lstrip()
                    if value == '':
                        value = 0
                    elif deci:
                        value = decimal.Decimal(value)
                    else:
                        if isinstance(value, int):
                            value = int(value)
                elif typ == 'D':
                    y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                    value = datetime.date(y, m, d)
                elif typ == 'L':
                    value = (value in 'YyTt' and 'T') or (value in 'NnFf' and 'F') or '?'
                elif typ == 'F':
                    value = float(value)
                result.append(value)
            yield result
    except :
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        # return -1, (exc_info,)


# ok
def read_dbf_file(path):
    try:
        f = open(path, 'rb')
        db = list(dbfreader(f))
        num = len(db)
        if num >= 2:
            num = num - 1
        print num
        return 0, (num)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


# ok
def GetNewWorkDate(param):
    """
    ����һ�����ںͲ�����������һ���µĹ����ա���������Ϊ��ֵ�������Ϊ�ǹ����յģ����˳���������գ���������Ϊ��ֵʱ��������ǹ����յģ���ǰ�˺��������� 

    Args:
        param: �ַ�����ʽ����� "yyyymmdd,���ֵ"
            ���磺�� 20151015 �ĺ�һ������ GetNewDate("20151015,1")
                   �� 20151015 ��ǰһ������ GetNewDate("20151015,-1")

    Returns:
        һ��Ԫ�飨ret��(newdate,)����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        newdate :������������
    """
    try:
        orig_date, delta = param.split(',')
        d = date(int(orig_date[0:4]), int(orig_date[4:6]), int(orig_date[6:8]))
        d = d + timedelta(days=int(delta))
        if int(delta) >= 0:
            while d.weekday() == 5 or d.weekday() == 6:
                d = d + timedelta(days=1)
        else:
            while d.weekday() == 5 or d.weekday() == 6:
                d = d + timedelta(days=-1)
        return 0, (d.strftime('%Y%m%d'),)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


# �ͻ�����ƾ֤��ͨ
# ok
def RunInitQualifications(param):
    servertype = gl.g_connectSqlServerSetting[param["serverid"]]["servertype"]

    init_qualif_file = "initQualifications.sql"
    dict = {}
    f = open(init_qualif_file, 'r')
    Logging.getLog().debug("open %s" % (init_qualif_file))
    lines = f.readlines()

    sql = "select top 1 SN from DDAid order by SN desc"
    Logging.getLog().debug(sql)
    ret, r = change_db(sql, servertype)
    if r == []:
        newSN = 1
    else:
        newSN = int(r[0][0])

    # ������ȯר��
    orderSql = "select top 1 sno,ordersno,orderid from run..creditdebts order by sno desc"
    Logging.getLog().debug(orderSql)

    ret, orderR = change_db(orderSql, servertype)
    if orderR == []:
        newSno = 1
        newOrderSno = 1
        newOrderId = 1
    else:
        newSno = int(orderR[0][0]) + 1
        newOrderSno = int(orderR[0][1]) + 1
        newOrderId = orderR[0][2].strip()

    orderStr = ''
    orderId = ''
    for item in str(newOrderId):
        if item != '0' and item != '1' and item != '2' and item != '3' and item != '4' and item != '5' and item != '6' and item != '7' and item != '8' and item != '9':
            orderStr = orderStr + item
        else:
            orderId = orderId + item

    # orderIdStr = newOrderId[0:1]
    # if orderIdStr != '0' and orderIdStr != '1' and orderIdStr != '2' and orderIdStr != '3' and orderIdStr != '4' and orderIdStr != '5' and orderIdStr != '6' and orderIdStr != '7' and orderIdStr != '8' and orderIdStr != '9':
    #    orderIdStr = newOrderId[0:1]
    #    newOrderId = newOrderId[1:]
    # else:
    #    orderIdStr = '' 

    newOrderId = orderStr + str(int(orderId) + 1)

    param["newSno"] = newSno
    param["newOrderSno"] = newOrderSno
    param["newOrderId"] = newOrderId

    bjhg_sz_sno_sql = "select top 1 sno from run..bjhg_fundinfo_sz order by sno desc"
    Logging.getLog().debug(bjhg_sz_sno_sql)
    ret, bjghSZ = change_db(bjhg_sz_sno_sql, servertype)
    if bjghSZ == []:
        new_bjhg_sz_sno = 1
    else:
        new_bjhg_sz_sno = int(bjghSZ[0][0]) + 1
    param["new_bjhg_sz_sno"] = new_bjhg_sz_sno

    for j, line in enumerate(lines):
        line = line.strip()
        Logging.getLog().debug(line)
        if line.startswith('--'):
            continue
        if len(line) == 0:
            continue

        if line.startswith('insert into run..DDAid'):
            newSN = newSN + 1
            param["newSN"] = newSN

        sql = str(cF.GroupParameterReplace(line, param))
        Logging.getLog().debug(sql)

        # Logging.getLog().debug(sql)

        ret, r = change_db(sql, servertype)

        # ret,r=change_db(sql,'b')

        # ��������ͨ�ɶ�����
        # RunInitHGTSecuid(param["custid"],param["serverid"])


# ��������ͨ�ɶ�����
# ok
def RunInitHGTSecuid(custid, serverid):
    sql = "select secuid,rptsecuid,insidesecuid,orgid,name,idtype,idno,regflag,bondreg,seat,secucls,foreignflag,seculevel,secuseq,seculimit,status,creditflag,opendate,fullname,secuotherkind1,secuotherkinds from run..secuid where custid = '%s' and market = '1'  and charindex('A', secuid) = 1 " % custid
    ret, r = change_db(sql, 'p')
    for i, ds in enumerate(r):
        secuid = str(ds[0]).strip()
        rptsecuid = str(ds[1]).strip()
        insidesecuid = str(ds[2]).strip()
        orgid = str(ds[3]).strip()
        name = str(ds[4]).strip()
        idtype = str(ds[5]).strip()
        idno = str(ds[6]).strip()
        regflag = str(ds[7]).strip()
        bondreg = str(ds[8]).strip()
        seat = str(ds[9]).strip()
        secucls = str(ds[10]).strip()
        foreignflag = str(ds[11]).strip()
        seculevel = str(ds[12]).strip()
        secuseq = str(ds[13]).strip()
        seculimit = str(ds[14]).strip()
        status = str(ds[15]).strip()
        creditflag = str(ds[16]).strip()
        opendate = str(ds[17]).strip()
        fullname = str(ds[18]).strip()
        secuotherkind1 = str(ds[19]).strip()
        secuotherkinds = str(ds[20]).strip()

        addSql = "insert into run..secuid (serverid,custid,market,secuid,rptsecuid,insidesecuid,orgid,name,idtype,idno,regflag,bondreg,seat,secucls,foreignflag,seculevel,secuseq,seculimit,status,creditflag,opendate,fullname,secuotherkind1,secuotherkind2,secuotherkinds) " \
                 " values ('" + serverid + "','" + custid + "','5','" + secuid + "','" + rptsecuid + "','" + insidesecuid + "','" + orgid + "','" + name + "','" + idtype + "','" + idno + "','" + regflag + "','" + bondreg + "','" + seat + "','" + secucls + "','" + foreignflag + "','" + seculevel + "','" + secuseq + "','" + seculimit + "','" + status + "','" + creditflag + "','" + opendate + "','" + fullname + "','" + secuotherkind1 + "','1','" + secuotherkinds + "')"

        if serverid == '4':
            ret, r = change_db(addSql, 'p')
        elif serverid == '12':
            ret, r = change_db(addSql, 'v')

        return 0


# ��ԭ��ٺϲ����ʵ
def ASSERT_EXPRESSION(param):
    '''
    ��֤һ������Ƿ�Ϊ��
    '''
    # ret = True
    ret = eval(param)
    if ret == True:
        Logging.getLog().debug("ASSERT_EXPRESSION: (%s) True" % param)
        return 0, ("",)
    else:
        Logging.getLog().debug("ASSERT_EXPRESSION: (%s) False" % param)
        return -1, ("",)


# ok
def getparam(param):
    fundid, test, serverid, secuid, orgid = param.split(',')
    if len(test) > 1:
        sql = "select stkavl,stksale from run..stkasset where fundid ='%s' and secuid = '%s' and orgid = '%s' and stkcode='%s'" % (
            fundid, secuid, orgid, test)
    else:
        if test == 'D' or test == 'd':
            moneytype = '1'
        elif test == 'H' or test == 'h':
            moneytype = '2'
        else:
            moneytype = '0'
        sql = "select fundavl,fundbuy from run..fundasset where fundid ='%s' and orgid = '%s' and moneytype='%s'" % (
            fundid, orgid, moneytype)
    ret, r = change_db(sql, serverid)

    if ret < 0:
        return ret, (u"û����run..fundasset��鵽�ÿͻ�%s�ֲ���Ϣ��" % (test),)

    return ret, r[0]


# ��ԭ����������ʵ
def checkparam(param):
    if len(param.split(',')[1]) > 1:
        fundid, test, serverid, price, qty, bsflag, y_stkavl, y_stksale, secuid, orgid = param.split(',')
        g_list = fundid + "," + test + "," + serverid + "," + secuid + "," + orgid
        ret, r = getparam(g_list)
        if ret == 0:
            h_stkbal = r[0]
            h_stksale = r[1]
        else:
            return -1, (r,)
        if int(y_stksale) + int(qty) == int(h_stksale):
            return 0, ("",)
        else:
            return -1, (u'�����ɷ��붳��ɷ�����������%d+%d!=%d' % (int(y_stksale), int(qty), int(h_stksale)),)
    else:
        fundid, test, serverid, price, qty, bsflag, y_fundavl, y_fundbuy, secuid, orgid = param.split(',')
        h_list = fundid + "," + test + "," + serverid + "," + secuid + "," + orgid
        ret, r = getparam(h_list)
        if ret == 0:
            h_fundavl = r[0]
            h_fundbuy = r[1]
        else:
            return -1, (r,)
        sql = "select orderprice,bondintr from run..orderrec where fundid='%s' ORDER BY ordersno desc" % (fundid)
        ret, r = change_db(sql, serverid)
        total = int(qty) * float(r[0][0] + r[0][1])
        B_flag = ['0.', '0B', '0M', '0N', '0a', '0b', '0c', '0d', '0e', '0l', '0q', '0u', '0w', '0y', '2I', 'B', 'M',
                  'N', 'a', 'b', 'c', 'd', 'e', 'l', 'q', 'u', 'w', 'y']
        if bsflag in B_flag:
            k1 = float(y_fundavl) - float(h_fundavl) - total
            kywc = total * (float(gl.g_deviationPCT) / 100) + 5
            if k1 <= kywc:
                return 0, ("",)
            else:
                return -1, (u'���������ðٷֱ�',)
        else:
            kk = total  # *1.1#Ĭ����ͣ�۸�
            k2 = float(y_fundavl) - float(h_fundavl) - kk
            kywc = total * (float(gl.g_deviationPCT) / 100) + 5
            if k2 <= kywc:
                return 0, (u"",)
            else:
                return -1, (u'���������ðٷֱ�',)


# ok
def switch_account_group_id(id):
    '''
    ʹ��ԭ���������Ҫ���ǵ�ԭ��û���˺���ĸ��������Ҫ�����л�

    Args:
        param: id���û���id
    Returns:
        һ��Ԫ�飨ret��(newdate,)����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            id : �л�����û���id
    '''
    return 0, (id,)


# ��ԭ����������ʵ
def modify_remote_server_time(param):
    '''
    ���������ļ��޸�Զ�̷�������ʱ����Ϣ

    Args:
        param: Ϊ��ʱ������Ϊ��ǰʱ��
            year:��
            month: ��
            day: ��
            hour: ʱ
            min: ��
            sec: ��
    Returns:
        һ��Ԫ�飨ret��("",)����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
    '''
    try:
        year, month, day, hour, min, sec = param.split(',')

        year = year.strip('"').strip("'")
        month = month.strip('"').strip("'")
        day = day.strip('"').strip("'")
        hour = hour.strip('"').strip("'")
        min = min.strip('"').strip("'")
        sec = sec.strip('"').strip("'")

        now = datetime.datetime.now()
        if year == "":
            year = now.year
        if month == "":
            month = now.month
        if day == "":
            day = now.day
        if hour == "":
            hour = now.hour
        if min == "":
            min = now.minute
        if sec == "":
            sec = now.second

        for ip in gl.g_timeSyncServerSettingList:
            ServerUrl = "http://" + ip + ":5556"
            s = ServerProxy(ServerUrl)
            Logging.getLog().debug("ModifyRemoteServerDateTime:%s" % ServerUrl)
            try:
                ret, msg = s.ModifyRemoteServerDateTime(int(year), int(month), int(day), int(hour), int(min), int(sec))
                if ret < 0:
                    Logging.getLog().error(msg)
            except:
                exc = cF.getExceptionInfo()
                Logging.getLog().error(exc)
        return 0, ("",)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


# ok
def sleepTime(i):
    time.sleep(int(i))
    return 0, ""


# ok
def querycheck(param):
    '''
    ��ѯ������������У��:

    checklist: ��У���ֶ��б�
    count: У������
    '''
    ret = param.count(',')
    if ret <= 0:
        count = int(param)
        if count == (len(gl.g_datalist) - 1):
            return 0, ("",)
        else:
            return -1, (u"������������У��ʧ�ܣ�",)
    else:
        checklist = param.split(',')[:-1]
        count = int(param.split(',')[-1])
    row_count = 0
    if int(gl.g_RsFetchRow_ret) == 0 and len(gl.g_datalist) > 1:
        for i, row in enumerate(gl.g_datalist):
            if i == 0:
                continue
            for c_param in checklist:
                if row[gl.g_datalist[0].index(c_param)] == gl.g_CmdstrDict.get(c_param):
                    continue
                else:
                    return -1, (u"%s����������Ԥ�ڲ�ƥ�䣡" % c_param,)
            row_count += 1
            # continue
        if row_count == count:
            return 0, ("",)
        else:
            return -1, (u"������������У��ʧ�ܣ�",)

    else:
        return -1, (u"���ݷ��س����û�����ݷ��أ�",)


# ��ԭ����������ʵ
def expression_evaluation(value):
    """���ʽ����"""
    try:
        value = value.strip()
        Logging.getLog().debug(u"���ձ��ʽΪ��%s" % str(value))
        value = eval(value)
        if '.' in str(value):
            if len(str(value).split(".")[1]) <= 2:
                Logging.getLog().debug(u"������Ϊ��%s" % str(value))
                return 0, (value,)
        if value and isinstance(value, float):
            value1 = float(int(value * 100))
            value2 = value * 100 - value1
            if str(value2) >= '0.5':
                value = (value1 + 1) / 100
            else:
                value = value1 / 100
            value = "%.2f" % value
        Logging.getLog().debug(u"������Ϊ��%s" % str(value))
        return 0, (value,)
    except Exception as e:
        # exc_info = cF.getExceptionInfo()
        # Logging.getLog().error(exc_info)
        return -1, (e,)


# ��ԭ����������ʵ
def max_value(param):
    """���ʽ����"""
    try:
        params = param.split(",")
        params = [i.strip() for i in params]
        param_1 = float(params[0])
        param_2 = float(params[1])
        if param_1 >= param_2:
            return 0, (param_1,)
        else:
            return 0, (param_2,)
    except Exception as e:
        return -1, (e,)


# def expression_evaluation(value):
#     """���ʽ����"""
#     try:
#         value = value.strip()
#         Logging.getLog().debug(u"���ձ��ʽΪ��%s" % str(value))
#         value = eval(value)
#         value = "%.2f" % value
#         Logging.getLog().debug(u"������Ϊ��%s" % str(value))
#         return 0, (value,)
#     except Exception as e:
#         return -1, (e,)


# ok


# ok
def retures_qualified_value(params):
    try:
        Logging.getLog().debug(params)
        a, b, c, d = params.split(",")
        a = a.strip()
        b = b.strip()
        c = c.strip()
        d = d.strip()
        value = a + b
        if eval(value):
            return 0, (c,)
        else:
            return 0, (d,)
    except Exception as e:
        return -1, (e,)


# ok
def test():
    import urllib
    import urllib2
    #ip85  VIP
    #ip87 ȫ��
    #ip89 ��ͨ����
    #count ��ͨ�˻�����

    #1-5 ��Ӧ���Ǻ���12   84
    # 6-10 ��Ӧ���Ǻ���13 85
    data = {"list":[{"ip85":"10.187.160.85","ip87":"10.187.160.87","ip89":"10.187.160.89","count":"2"}]}
    data_urlencode = urllib.urlencode(data)
    url = "http://10.187.160.92:8080/khsdata.do?%s" % data_urlencode
    req = urllib2.Request(url)
    print url
    res_data = urllib2.urlopen(req)
    res = res_data.read()
    print res


# ok
def dbfwriter(f, fieldnames, fieldspecs, records):
    """ Return a string suitable for writing directly to a binary dbf file.

    File f should be open for writing in a binary mode.

    Fieldnames should be no longer than ten characters and not include \x00.
    Fieldspecs are in the form (type, size, deci) where
        type is one of:
            C for ascii character data
            M for ascii character memo data (real memo fields not supported)
            D for datetime objects
            N for ints or decimal objects
            L for logical values 'T', 'F', or '?'
        size is the field width
        deci is the number of decimal places in the provided decimal object
    Records can be an iterable over the records (sequences of field values).

    """

    # header info

    ver = 3
    now = datetime.datetime.now()
    yr, mon, day = now.year - 1900, now.month, now.day
    numrec = len(records)
    numfields = len(fieldspecs)
    lenheader = numfields * 32 + 33
    lenrecord = sum(field[1] for field in fieldspecs) + 1
    hdr = struct.pack('<BBBBLHH20x', ver, yr, mon, day, numrec, lenheader, lenrecord)
    f.write(hdr)

    # field specs
    for name, (typ, size, deci) in itertools.izip(fieldnames, fieldspecs):
        # name = str(name).decode("utf-8").encode('gb2312')
        name = str(name).encode('GBK')
        name = name.ljust(11, '\x00')
        fld = struct.pack('<11sc4xBB14x', name, typ, size, deci)
        f.write(fld)

    # terminator
    f.write('\r')

    # records
    for record in records:
        f.write(' ')  # deletion flag
        for (typ, size, deci), value in itertools.izip(fieldspecs, record):
            # value = str(value).decode("utf-8").encode('gb2312')
            value = str(value).encode('GBK')
            if typ == "N":
                value = str(value).rjust(size, ' ')
            elif typ == 'D':
                value = value.strftime('%Y%m%d')
            elif typ == 'L':
                value = str(value)[0].upper()
            else:
                value = str(value)[:size].ljust(size, ' ')
            assert len(value) == size
            f.write(value)

    # End of file
    f.write('\x1A')


# ok
def update_dbf_file(path, index_column_name_values, update_column_name_value):
    try:
        # dbf_read_write_info('C:\\test.dbf', "YMTH=180000000040&KHRQ=20161013", "KHMC=����ɽˮ����20180203")
        # mycopyfile("before")
        index_column_name_values_list = []
        if '&' in index_column_name_values:
            index_column_name_values_list = index_column_name_values.split("&")
        if not index_column_name_values_list:
            index_column_name_values_list.append(index_column_name_values)
        # for index, i in enumerate(index_column_name_values_list):
        #
        # index_column_name = str(index_column_name_values.split("=")[0]).strip()
        # index_column_value = str(index_column_name_values.split("=")[1]).strip()
        update_column_name = str(update_column_name_value.split("=")[0]).strip()
        update_column_value = str(update_column_name_value.split("=")[1]).strip()
        dbf_data = []
        f = open(path, 'rb')
        fieldspecs = []
        fieldnames = []
        db = list(dbfreader(f))
        f.close()
        flag = False
        flag_update = 0
        if db:
            if db[0]:
                for names in db[0]:
                    names = str(names.encode('utf-8')).strip()
                    fieldnames.append(names)
            # dbf_data.append(fieldnames)
            print fieldnames
            if len(db) > 1:
                for record in db[1:]:
                    if flag == False:
                        for child_record in record:
                            if isinstance(child_record, tuple):
                                fieldspecs = record
                                flag = True
                                break
                    else:
                        new_record = []
                        for i in record:
                            if isinstance(i, str):
                                i = i.strip()
                            new_record.append(i)
                        row_data = collections.OrderedDict(zip(fieldnames, new_record))
                        # if flag_update == 0:
                        code_status_list = []
                        for index, i in enumerate(index_column_name_values_list):
                            code_status = 'False'
                            index_column_name = str(i.split("=")[0]).strip()
                            index_column_value = str(i.split("=")[1]).strip()
                            if index_column_name in fieldnames:
                                if str(row_data[str(index_column_name)]).strip() == str(index_column_value).strip():
                                    code_status = 'True'
                                    code_status_list.append(code_status)
                        if len(index_column_name_values_list) == len(code_status_list) and 'True' in code_status_list:
                            row_data[str(update_column_name)] = str(update_column_value)
                            # flag_update = 1
                            print "flag_update=1"
                            print row_data.values()
                        dbf_data.append(row_data.values())
        if os.path.exists(path):
            os.remove(path)
        f = open(path, 'wb')
        # print dbf_data[-1]
        dbfwriter(f, fieldnames, fieldspecs, dbf_data)
        f.close()
        # mycopyfile("after")
        return 0, ("",)
    except Exception as e:
        print e
        return -1, e


# ��ԭ����������ʵ
def add_dbf_file_data(params):
    try:
        # col = [YMTH, YMTZT, KHRQ, XHRQ, KHFS]
        # value = [180000000096, 2, 3, 43, 5]
        anyone_data = []
        path, col, value = params.split(';')
        col = col.replace("[", "").replace("]", "").strip().split(",")
        value = value.replace("[", "").replace("]", "").strip().split(",")
        print "add_dbf_file_data"
        print "path:%s, col:%s, value:%s"%(str(path), str(col), str(value))
        new_data = collections.OrderedDict()
        col = [str(i).strip() for i in col]
        value = [str(i).strip() for i in value]
        add_data = collections.OrderedDict(zip(col, value))
        dbf_data = []
        path = path.strip()
        f = open(path, 'rb')
        # f = open(path, 'a+')
        fieldspecs = []
        fieldnames = []
        db = list(dbfreader(f))
        col_list = db[0]
        new_db = []
        col_names = []
        for i in col_list:
            if i == "_NullFlags":
                break
            col_names.append(i)
        num = len(col_names)
        f.close()
        for i in db:
            new_db.append(i[:num])
        db = new_db
        flag = False
        if db:
            if db[0]:
                for names in db[0]:
                    names = str(names.encode('utf-8')).strip()
                    fieldnames.append(names)
            if len(db) > 1:
                for record in db[1:]:
                    if flag == False:
                        for child_record in record:
                            if isinstance(child_record, tuple):
                                fieldspecs = record
                                flag = True
                                break
                    else:
                        new_record = []
                        for i in record:
                            if isinstance(i, str):
                                i = i.strip()
                            new_record.append(i)
                        row_data = collections.OrderedDict(zip(fieldnames, new_record))
                        anyone_data = row_data
                        dbf_data.append(row_data.values())
            # if not dbf_data:
            #     nums = len(fieldnames)
            #     for i in range(nums):
            #         dbf_data.append("")
            # if dbf_data:
            for i in fieldnames:
                if i in add_data.keys():
                    new_data[i] = add_data[i]
                else:
                    new_data[i] = ""
            if new_data:
                print "new_data"
                print new_data
                dbf_data.append(new_data.values())
            if os.path.exists(path):
                os.remove(path)
            f = open(path, 'wb')
            dbfwriter(f, fieldnames, fieldspecs, dbf_data)
            f.close()
        return 0, ("",)
    except Exception as e:
        print e
        return -1, e


#��file_dirĿ¼�µ�old_type���͵��ļ��ĳ�new_type���͵��ļ�
# ok
def file_rename(old_type, new_type, file_dir):
    old_files = find_file(old_type, file_dir)
    for old_file in old_files:#���������ļ�
        filename=os.path.splitext(old_file)[0]#�ļ���
        #filetype=os.path.splitext(old_file)[1];#�ļ���չ��
        new_file=os.path.join(filename+ new_type)#�µ��ļ�·��
        os.remove(new_file)
        os.rename(old_file, new_file)#������

#��ĳ���ļ����͵��ļ�
# ok
def find_file(file_type, file_dir):
    file_set = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == file_type:
                file_set.append(os.path.join(root, file))

    return file_set

# def test():
#     f = open("J:\\zqbd.dbf",'a+')
#     f.read()

# ok
def get_minfee_commissionrate_info(params):
    try:
        # Ӷ���ȡ - -���: market(�г�), stkcode��֤ȯ���룩, fundid���ʽ���룩��custid���ͻ����룩��bsflag����������[�����������]��
        # --���Σ�minfee����СӶ��ֵ��, commissionrate��Ӷ����ʣ���
        serverid, market, stkcode, fundid, custid, bsflag, dbid, orgid = params.split(",")
        print "serverid, market, stkcode, fundid, custid, bsflag, dbid, orgid"
        print serverid, market, stkcode, fundid, custid, bsflag, dbid, orgid
        market = market.strip()
        stkcode = stkcode.strip()
        fundid = fundid.strip()
        custid = custid.strip()
        bsflag = bsflag.strip()
        dbid = dbid.strip()

        data = """
        #��ȡ֤ȯ����
        call:stktype = sqlserver_Database(select stktype from run..stktrd where market = '@market@' and  stkcode = '@stkcode@',@dbid@)
        #��ȡ��������
        call:trdid = sqlserver_Database(select trdid from run..stktrd where market = '@market@' and  stkcode = '@stkcode@',@dbid@)
        #��ȡ�ʽ��Һ�
        call:fundlevel = sqlserver_Database(select fundlevel from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #��ȡ�ʽ����
        call:fundgroup = sqlserver_Database(select fundgroup from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #��ȡ������ʽ
        call:operway = sqlserver_Database(select operway from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #��ȡ�ʽ����
        call:fundkind = sqlserver_Database(select fundkind from run..fundinfo where fundid = '@fundid@' ,@dbid@)

        #��Ӷ�����
        #ȡӶ��ģ���
        call:feemodelid1 = sqlserver_Database(select top 1 feemodelid from run..custcommission where orgid = @orgid@ and (fundid = -1 or fundid = '@fundid@') and (custid = -1 or custid = '@custid@') and (ltrim(rtrim(pt_fundkind)) = '' or charindex('@fundkind@',pt_fundkind) > 0)  and (ltrim(rtrim(pt_fundlevel)) = '' or charindex('@fundlevel@',pt_fundlevel) > 0) and (ltrim(rtrim(pt_fundgroup)) = '' or charindex('@fundgroup@',pt_fundgroup) > 0) and (ltrim(rtrim(pt_operway)) = '' or CHARINDEX('@operway@',pt_operway) > 0 ) and (ltrim(rtrim(pt_stktype)) = '' or CHARINDEX('@stktype@',pt_stktype) > 0 ) ORDER BY fundid DESC,custid DESC,pt_fundkind DESC,pt_fundlevel DESC,pt_fundgroup DESC, pt_operway DESC, pt_stktype DESC zero,@dbid@)

        #ȷ��Ӷ��ģ��ţ���δȡ��ֵ��Ĭ��ģ���Ϊ��**��
        call:feemodelid = retures_qualified_value('@feemodelid1@',!='0',@feemodelid1@,**)
        #��ȡ���Ӷ��
        call:minfee_old = sqlserver_Database(select minfee from run..commissionmodel where orgid = '@orgid@' and market = '@market@' and trdid = '@trdid@' and stktype = '@stktype@' and moneytype = '0' and bsflag = '@bsflag@' and feemodelid = '@feemodelid@' zero,@dbid@) 
        #��ȡӶ�����
        call:commissionrate_old = sqlserver_Database(select commissionrate from run..commissionmodel where orgid = '@orgid@' and market = '@market@' and trdid = '@trdid@' and stktype = '@stktype@' and moneytype = '0' and bsflag = '@bsflag@' and feemodelid = '@feemodelid@' zero,@dbid@)
        
        #��Ӷ�����
        #ȡĬ�Ϸ���
        call:commissionrate_new_1_1 = sqlserver_Database(select top 1 commissionrate from run..busicommission where market = '@market@' and stktype = '@stktype@' and bsflag = '@bsflag@' and trdid = '@trdid@' and moneytype = '0' and (stkcode = '' or stkcode = '@stkcode@') order by stkcode desc zero,@dbid@)
        #ҵ����ȷ��custdiscountδ�ҵ���ȡĬ�Ϸ���
        call:busikind1 = sqlserver_Database(select top 1 busikind from run..busicommission where market = '@market@' and stktype = '@stktype@' and bsflag = '@bsflag@' and trdid = '@trdid@' and moneytype = '0' and (stkcode = '' or stkcode = '@stkcode@') order by stkcode desc zero,@dbid@)
        call:busikind = retures_qualified_value('@busikind1@',!='0',@busikind1@,)
        call:discountrate1 = sqlserver_Database(select discountrate from run..custdiscount where orgid = '@orgid@' and fundid = '@fundid@' and custid = '@custid@' and busikind = '@busikind@' zero,@dbid@)
        call:discountrate = retures_qualified_value('@discountrate1@',!='0',@discountrate1@,0)
        call:commissionrate_new_1=expression_evaluation(@commissionrate_new_1_1@*@discountrate@)
        call:commissionrate_new = retures_qualified_value('@discountrate@',!='0',@commissionrate_new_1@,@commissionrate_new_1_1@)
        call:minfee_new = sqlserver_Database(select top 1 minfee from run..busicommission where market = '@market@' and stktype = '@stktype@' and bsflag = '@bsflag@' and trdid = '@trdid@' and moneytype = '0' and (stkcode = '' or stkcode = '@stkcode@') order by stkcode desc zero,@dbid@)
        
        #ȡorgcommission����commissionflag_orderֵ��commissionflag_orderΪ0��''ʱ������Ӷ��ģʽ��commissionflag_orderΪ1ʱ������Ӷ��ģʽ
        call:commissionflag_order = sqlserver_Database(select commissionflag_order from run..orgcommission where serverid='@serverid@' and orgid='@orgid@' zero,@dbid@)
        call:commissionrate = retures_qualified_value('@commissionflag_order@',!='1',@commissionrate_old@,@commissionrate_new@)
        call:minfee = retures_qualified_value('@commissionflag_order@',!='1',@minfee_old@,@minfee_new@)
        """
        data = data.decode("gbk").replace("@serverid@", serverid).replace("@market@", market).replace("@stkcode@", stkcode).replace("@fundid@", fundid).replace(
            "@custid@", custid).replace("@bsflag@", bsflag).replace("@dbid@", dbid).replace("@orgid@", orgid)

        cF.action_process(serverid, data, gl.all_group_dict)
        # print 'ok'
        return 0, ('',)
    except Exception as e:
        print e
        return -1, e

# ok
def read_kcbp_info():
    cmd = ["E:\\soft\\xpbp\kcbp\\bin\\imdbcmd.exe" ,"list table"]
    sub = subprocess.Popen(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    # result,err = sub.communicate(input='')
    result_code = sub.stdout.read()
    print result_code


if __name__ == '__main__':
    read_kcbp_info()
    # get_minfee_commissionrate_info("1,2,3,4,5,6")
    # file_dir = r"D:\dbf"
    # file_rename('.dbf', '.csv', file_dir)
    #����dbf�ļ��޸�ΪCSV
    # retures_qualified_value('4d, != 0,4d, **')
    # max_value('294.0,5')
    # # expression_evaluation("9.9500*100*0.001")
    # cF.readConfigFile()
    # # ret, sysdate = GeneRZRQNewCreditDebtsSno('12')
    # ret, sysdate = getSysConfigDate('12')
    # print sysdate
    # param = {'custid':'25210679','orgid':'3202','fundid':'10494391','serverid':'4'}
    # RunInitQualifications(param)
    # pass
    # readKCXPqueue("10.187.96.38, KCXP00, 888888, shagoffer:shbgoffer")
    # call:readKCXPqueue(10.187.96.38, KCXP00, 888888, shagoffer)
