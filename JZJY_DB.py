# -*- coding:gbk -*-
import pyodbc

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from xml.dom import minidom
from lxml import etree
import datetime
from datetime import date
from datetime import timedelta
import commFuncs as cF
import gl
import random
import time
# import math
from gl import GlobalLogging as Logging


def generateJZJYColumnXml():
    """
    ����SQL Server Run ���ݿ��ֶ����ñ�
    """
    Logging.getLog().info(u"ɨ�輯�н������ݿ⿪ʼ")
    root = etree.Element("comparesetting")
    for key in gl.g_connectSqlServerSetting.keys():
        try:
            ret, conn = cF.ConnectToRunDB(key)
            if ret == -1:
                err = '����%s,���ݿ������쳣ԭ��%s' % (str(key), conn)
                Logging.getLog().critical(err)
                return -1, err
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            err = u"�������ݿ�����쳣,%s" % exc_info
            Logging.getLog().critical(err)
            return -1, err
        crs = conn.cursor()
        identity_dict = {}
        try:
            schema_list = ['run']
            for schema in schema_list:

                # ɨ��identity����Ϣ,����Ӧ�ֶα������ֵ���
                sql = "select object_name(id) tablename,name column_name from syscolumns where COLUMNPROPERTY(ID,NAME,'IsIdentity')=1 AND OBJECTPROPERTY(id, N'IsUserTable')= 1 ORDER BY object_name(id)"
                crs.execute(sql)
                ds = crs.fetchall()
                for rec in ds:
                    if rec[0].upper().startswith('AUTO_D_') or rec[0].upper().startswith('AUTO_I_') or rec[
                        0].upper() == "TMP_AUTOTEST_TRIGGER":  # �����Զ���ϵͳ��������ʱ��
                        continue
                    if rec[0] not in identity_dict.keys():
                        identity_dict[rec[0]] = [rec[1]]
                    else:
                        identity_dict[rec[0]].append(rec[1])

                schemaElem = etree.SubElement(root, "schema", schemaname=schema)
                schemaElem.attrib["core"] = str(key)
                sql = "SELECT name FROM sysobjects Where XType= 'U' order by Name;"
                r = crs.execute(sql)
                ds_tablename = r.fetchall()
                for i, table in enumerate(ds_tablename):
                    # print "table %d" %i
                    if table[0].startswith('AUTO_D_') or table[0].startswith('AUTO_I_') or rec[
                        0].upper() == "TMP_AUTOTEST_TRIGGER":
                        continue
                    tableElem = etree.SubElement(schemaElem, "table", tablename=table[0], whereclause="")
                    if table[0] in identity_dict.keys():
                        tableElem.attrib["have_exclude_column"] = "1"
                    else:
                        tableElem.attrib["have_exclude_column"] = "0"
                    tableElem.attrib["disableflag"] = '0'
                    # print table[0]
                    sql = "sp_columns @table_name = '%s'" % (table[0])
                    r = crs.execute(sql)
                    ds_columns = r.fetchall()

                    for column in ds_columns:
                        subElem = etree.SubElement(tableElem, "column", column_name=column[3])  # COLUMN_NAME  column[3]
                        if table[0] in identity_dict.keys() and column[3] in identity_dict[table[0]]:
                            subElem.attrib["is_exclude"] = "1"
                        elif column[5] in ["image", "text", "ntext"]:  # TYPE_NAME column[5]
                            subElem.attrib["is_exclude"] = "1"
                            tableElem.attrib["have_exclude_column"] = "1"
                        else:
                            subElem.attrib["is_exclude"] = "0"
                        subElem.attrib["disableflag"] = "0"

        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            err = u"���ݿ�ִ��%s������쳣,%s" % (sql, exc_info)
            Logging.getLog().critical(err)
            crs.close()
            conn.rollback()
            conn.close()
            return -1, err
        crs.close()
        conn.close()
    doc = etree.ElementTree(root)
    doc.write("JZJY_column_report_scan.xml", pretty_print=True, xml_declaration=True, encoding='utf-8')
    Logging.getLog().info(u"ɨ�輯�н������ݿ����")
    return 0, ""


def CheckJZJYColumnSetting():
    Logging.getLog().info(u"���¼��н������ݿ������ļ���ʼ")

    # ��ȡ�ļ�
    doc = etree.ElementTree(file='JZJY_column_report.xml')
    root = doc.getroot()
    # ���ݽӿڲ����ļ�
    doc = etree.ElementTree(root)  # root Ϊ��Ԫ��
    doc.write("JZJY_column_report.xml%s.xml" % time.strftime('%Y%m%d%H%M%S'), pretty_print=True, xml_declaration=True,
              encoding='utf-8')

    root = ET.parse("JZJY_column_report.xml").getroot()
    root_scan = etree.ElementTree(file="JZJY_column_report_scan.xml").getroot()

    for schemaElem in root:
        # print schemaElem.attrib['schemaname']

        for tableElem in schemaElem:
            # print tableElem.tag,tableElem.attrib['tablename']
            # if tableElem.attrib['disableflag']=='1':
            if tableElem.attrib.get("disableflag", None) == "1":
                try:
                    xpath = "schema[@schemaname='%s']/table[@tablename='%s']" % (
                        schemaElem.attrib['schemaname'], tableElem.attrib['tablename'])
                    column_elem_y = root_scan.find(xpath)
                    if column_elem_y == None:
                        continue
                    column_elem_y.attrib["disableflag"] = '1'
                except Exception, ex:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().critical(exc_info)
                    return -1, exc_info
            for columnElem in tableElem:
                # print columnElem.tag,columnElem.attrib['column_name']
                try:
                    if columnElem.attrib['disableflag'] == '1':
                        xpath = "schema[@schemaname='%s']/table[@tablename='%s']/column[@column_name='%s']" % (
                            schemaElem.attrib['schemaname'], tableElem.attrib['tablename'],
                            columnElem.attrib['column_name'])
                        column_elem = root_scan.find(xpath)
                        if column_elem == None:
                            continue
                        column_elem.attrib["disableflag"] = "1"
                except Exception, ex:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().critical(exc_info)
                    return -1, exc_info

    doc = etree.ElementTree(root_scan)
    doc.write("JZJY_column_report.xml", pretty_print=True, xml_declaration=True, encoding='utf-8')
    Logging.getLog().info(u"���¼��н������ݿ������ļ����")
    return 0, ""


def createJZJYTempTable(server=0):
    '''
    Ϊ�˱���ɾ�����ݣ�������ʱ��
    '''
    # t = datetime.datetime.now()
    # table_xml = ET.parse("JZJY_column_report.xml")
    Logging.getLog().info(u"׼���ڼ��н��� server %s ������ʱ����" % str(server))
    if gl.g_JZJY_column_Tree == None:
        gl.g_JZJY_column_Tree = ET.parse("JZJY_column_report.xml")

    table_root = gl.g_JZJY_column_Tree.getroot()
    ret, conn = cF.ConnectToRunDB(server)
    if ret == -1:
        err = '����%s,���ݿ������쳣ԭ��%s' % (str(server), conn)
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()
    try:
        # ���� TMP_AUTOTEST_TRIGGER
        sql = "select count(*) from dbo.sysobjects where name = 'TMP_AUTOTEST_TRIGGER'"
        crs.execute(sql)
        ds = crs.fetchall()
        if ds[0][0] != 0:
            sql = "drop table TMP_AUTOTEST_TRIGGER"
            # print sql
            crs.execute(sql)
        sql = "create table TMP_AUTOTEST_TRIGGER(username VARCHAR(12),tablename VARCHAR(32),operation int,row_id VARCHAR(128))"
        crs.execute(sql)

        for schemaElem in table_root:
            if schemaElem.attrib["core"] != str(server):
                continue
            for i, tableElem in enumerate(schemaElem):
                if tableElem.attrib["disableflag"] == "1":
                    continue

                schema = schemaElem.attrib["schemaname"]
                tablename = tableElem.attrib["tablename"]

                sql_i = "select COUNT(*) from  dbo.sysobjects where name='AUTO_I_%s';" % (tablename)
                sql_d = "select COUNT(*) from  dbo.sysobjects where name='AUTO_D_%s';" % (tablename)
                r = crs.execute(sql_i)
                ds_i = crs.fetchall()
                r = crs.execute(sql_d)
                ds_d = crs.fetchall()
                # print ds_i[0][0]
                # print ds_d[0][0]
                if ds_i[0][0] != 0:
                    sql = "drop table %s..AUTO_I_%s " % (schema, tablename)
                    # print sql
                    crs.execute(sql)
                if ds_d[0][0] != 0:
                    sql = "drop table %s..AUTO_D_%s " % (schema, tablename)
                    # print sql
                    crs.execute(sql)
                c_i = "select * into %s..AUTO_I_%s from %s..%s where 1=2;" % (schema, tablename, schema, tablename)
                c_d = "select * into %s..AUTO_D_%s from %s..%s where 1=2;" % (schema, tablename, schema, tablename)
                # print c_i
                # print c_d
                r = crs.execute(c_i)
                r = crs.execute(c_d)
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        err = u"�������ݿ�����쳣��%s" % exc_info
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err
    crs.close()
    conn.commit()
    conn.close()
    Logging.getLog().info(u"�ڼ��н��� server %s ������ʱ�����" % str(server))
    return 0, ""


def dropJZJYTempTable(server=0):
    # t = datetime.datetime.now()
    Logging.getLog().info(u"׼���ڼ��н��� server %s ɾ����ʱ����" % str(server))
    if gl.g_JZJY_column_Tree == None:
        gl.g_JZJY_column_Tree = ET.parse("JZJY_column_report.xml")
    table_root = gl.g_JZJY_column_Tree.getroot()
    try:
        ret, conn = cF.ConnectToRunDB(server)
        if ret == -1:
            err = '����%s,���ݿ������쳣ԭ��%s' % (str(server), conn)
            Logging.getLog().critical(err)
            return -1, err
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"���Ӽ��н���server %s ���ݿ�����쳣" % (str(server), exc_info)
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()
    try:
        # ɾ�� TMP_AUTOTEST_TRIGGER
        sql = "select COUNT(*) from dbo.sysobjects where name='TMP_AUTOTEST_TRIGGER'"
        crs.execute(sql)
        ds = crs.fetchall()
        if len(ds) > 0:
            if ds[0][0] != 0:
                sql = "drop table TMP_AUTOTEST_TRIGGER"
                crs.execute(sql)

        for schemaElem in table_root:
            if schemaElem.attrib["core"] != str(server):
                continue
            for i, tableElem in enumerate(schemaElem):

                if tableElem.attrib["disableflag"] == "1":
                    continue

                schema = schemaElem.attrib["schemaname"]
                tablename = tableElem.attrib["tablename"]

                sql_i = "select COUNT(*) from  dbo.sysobjects where name='AUTO_I_%s';" % (tablename)
                sql_d = "select COUNT(*) from  dbo.sysobjects where name='AUTO_D_%s';" % (tablename)
                r = crs.execute(sql_i)
                ds_i = crs.fetchall()
                r = crs.execute(sql_d)
                ds_d = crs.fetchall()
                # print ds_i[0][0]
                # print ds_d[0][0]
                if ds_i[0][0] != 0:
                    sql = "drop table %s..AUTO_I_%s " % (schema, tablename)
                    # print sql
                    crs.execute(sql)
                if ds_d[0][0] != 0:
                    sql = "drop table %s..AUTO_D_%s " % (schema, tablename)
                    # print sql
                    crs.execute(sql)
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"���н���server %s ���ݿ�����쳣��%s" % (str(server), exc_info)
        Logging.getLog().critical(err)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err
    crs.close()
    conn.commit()
    conn.close()
    Logging.getLog().info(u"�ڼ��н��� server %s ɾ����ʱ�����" % str(server))
    return 0, ""


def createJZJYTrigger(server=0):
    '''
    SQL Server ���ݿⴴ��������
    '''
    Logging.getLog().info(u"׼���ڼ��н��� server %s ��������������" % str(server))
    t = datetime.datetime.now()

    if gl.g_JZJY_column_Tree == None:
        gl.g_JZJY_column_Tree = ET.parse("JZJY_column_report.xml")
    table_root = gl.g_JZJY_column_Tree.getroot()

    try:
        ret, conn = cF.ConnectToRunDB(server)
        if ret == -1:
            err = '����%s,���ݿ������쳣ԭ��%s' % (str(server), conn)
            Logging.getLog().critical(err)
            return -1, err
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"���Ӽ��н���server %s ���ݿ�����쳣��%s" % (str(server), exc_info)
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()
    try:
        # �Ƴ����д�����
        sql = "SELECT name FROM sysobjects WHERE xtype='TR' AND name LIKE 'run_%%_%%_trigger'"
        crs.execute(sql)
        ds = crs.fetchall()
        for rec in ds:
            sql = "drop trigger %s" % (rec[0])
            # print sql
            crs.execute(sql)

        # �����´�����
        for schemaElem in table_root:
            if schemaElem.attrib["core"] != str(server):
                continue

            for i, tableElem in enumerate(schemaElem):
                if tableElem.attrib["disableflag"] == "1":
                    continue

                schema = schemaElem.attrib["schemaname"]
                tablename = tableElem.attrib["tablename"]
                try:
                    if tableElem.attrib["have_exclude_column"] == "1":
                        column_list = []
                        for columnElem in tableElem:
                            if columnElem.attrib["is_exclude"] == "0":
                                column_list.append(columnElem.attrib["column_name"])
                        sql = "create trigger %s_%d_d_trigger on %s..%s After delete as insert into run..TMP_AUTOTEST_TRIGGER (username,tablename,operation) values('%s','%s',3);insert into %s..AUTO_D_%s(%s) select %s from deleted;" % (
                            schema, i, schema, tablename, schema, tablename, schema, tablename, ",".join(column_list),
                            ",".join(column_list))
                        r = crs.execute(sql)
                        sql = "create trigger %s_%d_i_trigger on %s..%s for insert as insert into run..TMP_AUTOTEST_TRIGGER (username,tablename,operation) values('%s','%s',1);insert into %s..AUTO_I_%s(%s) select %s from inserted;" % (
                            schema, i, schema, tablename, schema, tablename, schema, tablename, ",".join(column_list),
                            ",".join(column_list))
                        r = crs.execute(sql)
                        sql = "create trigger %s_%d_u_trigger on %s..%s for update as insert into run..TMP_AUTOTEST_TRIGGER (username,tablename,operation) values('%s','%s',2);insert into %s..AUTO_I_%s(%s) select %s from deleted;" % (
                            schema, i, schema, tablename, schema, tablename, schema, tablename, ",".join(column_list),
                            ",".join(column_list))
                        r = crs.execute(sql)
                    else:

                        sql = "create trigger %s_%d_d_trigger on %s..%s After delete as insert into run..TMP_AUTOTEST_TRIGGER (username,tablename,operation) values('%s','%s',3);insert into %s..AUTO_D_%s select * from deleted;" % (
                            schema, i, schema, tablename, schema, tablename, schema, tablename)
                        r = crs.execute(sql)
                        sql = "create trigger %s_%d_i_trigger on %s..%s for insert as insert into run..TMP_AUTOTEST_TRIGGER (username,tablename,operation) values('%s','%s',1);insert into %s..AUTO_I_%s select * from inserted;" % (
                            schema, i, schema, tablename, schema, tablename, schema, tablename)
                        r = crs.execute(sql)
                        sql = "create trigger %s_%d_u_trigger on %s..%s for update as insert into run..TMP_AUTOTEST_TRIGGER (username,tablename,operation) values('%s','%s',2);insert into %s..AUTO_I_%s select * from deleted;" % (
                            schema, i, schema, tablename, schema, tablename, schema, tablename)
                        r = crs.execute(sql)
                except BaseException, ex:
                    exc_info = cF.getExceptionInfo()
                    err = "���н���server = %s ִ��%s�����쳣����ʾ%s" % (str(server), sql, exc_info)
                    Logging.getLog().critical(err)
                    crs.close()
                    conn.rollback()
                    conn.close()
                    return -1, err
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"���н���server = %s ִ��%s�����쳣����ʾ%s" % (str(server), sql, exc_info)
        Logging.getLog().critical(err)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err

    crs.close()
    conn.commit()
    conn.close()
    Logging.getLog().info(u"���н��� server %s �������������" % str(server))
    return 0, ""


def dropJZJYTrigger(server=0):
    Logging.getLog().info(u"׼���ڼ��н��� server %s ɾ������������" % str(server))
    t = datetime.datetime.now()
    if gl.g_JZJY_column_Tree == None:
        gl.g_JZJY_column_Tree = ET.parse("JZJY_column_report.xml")
    table_root = gl.g_JZJY_column_Tree.getroot()
    try:
        ret, conn = cF.ConnectToRunDB(server)
        if ret == -1:
            err = '����%s,���ݿ������쳣ԭ��%s' % (str(server), conn)
            Logging.getLog().critical(err)
            return -1, err
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"���Ӽ��н���server %s ���ݿ��쳣���� %s" % (str(server), exc_info)
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()

    try:
        sql = "SELECT name FROM sysobjects WHERE xtype='TR' AND name LIKE 'run_%%_%%_trigger'"
        crs.execute(sql)
        ds = crs.fetchall()
        for rec in ds:
            sql = "drop trigger %s" % (rec[0])
            crs.execute(sql)
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"���н���server=%s���ݿ����%s�쳣���� %s" % (str(server), sql, exc_info)
        Logging.getLog().critical(err)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err

    crs.close()
    conn.commit()
    conn.close()
    Logging.getLog().info(u"���н��� server %s ɾ�����������" % str(server))
    return 0, ""


def scanJZJYDB():
    '''
    ɨ�輯�н������ݿ⣬�����̵߳���
    '''
    ret, msg = generateJZJYColumnXml()
    if ret < 0:
        gl.threadQueue.put((ret, msg, "scanJZJYDB"))  # ���ؽ��������У����߳̽������ȡ���н��
        return ret, msg
    ret, msg = CheckJZJYColumnSetting()
    gl.threadQueue.put((ret, msg, "scanJZJYDB"))  # ���ؽ��������У����߳̽������ȡ���н��
    return ret, msg


def initJZJYDB(server=0):
    '''
    ��ʼ�����н������ݿ⣬�����̵߳���
    '''
    ret, msg = createJZJYTempTable(server)
    if ret < 0:
        gl.threadQueue.put((ret, msg, "initJZJYCDB", server))  # ���ؽ��������У����߳̽������ȡ���н��
        return ret, msg
    ret, msg = createJZJYTrigger(server)
    gl.threadQueue.put((ret, msg, "initJZJYDB", server))  # ���ؽ��������У����߳̽������ȡ���н��
    return ret, msg


# ��ʼ����Ʊ�۸�
def ChangStkPrice(server=0):
    '''
    ��ʼ�������õ���Ʊ����ļ۸�
    '''
    price_dict = {"maxrisevalue": "17.8300", "maxdownvalue": "14.5900", "stopflag": "F", "closeprice": "16.2100",
                  "openprice": "16.2200", "lastprice": "16.2500", "highprice": "16.3200", "lowprice": "16.1300",
                  "lastcloseprice": "16.2500"}
    stkcode_list = []
    Logging.getLog().info(u"׼���ڼ��н��� server %s ��ʼ����Ʊ�۸񡭡�" % str(server))
    ret, conn = cF.ConnectToRunDB(server)
    cursor = conn.cursor()
    servertype = gl.g_connectSqlServerSetting[server]["servertype"]
    try:
        sql = "select * from tbl_cases where cmdstring like '%stkcode:%' and cmdstring like '%price:%'"
        ds = cF.executeCaseSQL(sql)
        if len(ds) > 0:
            for i, line in enumerate(ds):
                stkcode = line["cmdstring"].split('stkcode:')[1].split(',')[0]
                if stkcode not in stkcode_list:
                    stkcode_list.append(stkcode)

        for item in stkcode_list:
            sql = "select * from run..stktrd where  stkcode='%s'" % (stkcode)
            cursor.execute(sql)
            dss = cursor.fetchall()
            if len(dss) > 0:
                sql = "update run..stktrd set maxrisevalue='%s',maxdownvalue='%s',stopflag='%s',fixprice='%s' where stkcode='%s'" % (
                    price_dict["maxrisevalue"], price_dict["maxdownvalue"], price_dict["stopflag"],
                    price_dict["openprice"],
                    item)
                cursor.execute(sql)

            sql1 = "select * from run..stkprice where stkcode='%s'" % (item)
            cursor.execute(sql1)
            dsp = cursor.fetchall()
            if len(dsp) > 0:
                sql1 = "update run..stkprice set closeprice='%s',openprice='%s',lastprice='%s',highprice='%s',lowprice='%s',lastcloseprice='%s' where stkcode='%s'" % (
                    price_dict["closeprice"], price_dict["openprice"], price_dict["lastprice"], price_dict["highprice"],
                    price_dict["lowprice"], price_dict["lastcloseprice"], item)
                cursor.execute(sql1)

    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().info(u"�ں���%s��ʼ����Ʊ����۸�����쳣����ʾ��Ϣ stkcode= %s  %s����" % (str(server), stkcode, exc_info))
        cursor.close()
        conn.rollback()
        conn.close()
        gl.threadQueue.put((-1, u"exc_info", "ChangStkPrice", server))  # ���ؽ��������У����߳̽������ȡ���н��
        return -1, exc_info

    cursor.close()
    conn.commit()
    conn.close()
    Logging.getLog().info(u"�ں���%s��ʼ����Ʊ����۸����" % str(server))
    gl.threadQueue.put((0, '', "ChangStkPrice", server))  # ���ؽ��������У����߳̽������ȡ���н��
    return 0, ""


def UnInitJZJYDB(server=0):
    '''
    �ָ�ԭʼ�ۺ�������ݿ⣬�����̵߳���
    '''
    ret, msg = dropJZJYTrigger(server)
    if ret < 0:
        gl.threadQueue.put((ret, msg, "UnInitJZJYDB", server))  # ���ؽ��������У����߳̽������ȡ���н��
        return ret, msg
    ret, msg = dropJZJYTempTable(server)
    gl.threadQueue.put((ret, msg, "UnInitJZJYDB", server))  # ���ؽ��������У����߳̽������ȡ���н��
    return ret, msg


def RunInitScript(server=10):
    Logging.getLog().info(u"�ں���%s���г�ʼ���ű�����" % str(server))

    ret, conn = cF.ConnectToRunDB(server)
    if ret == -1:
        err = '����%s,���ݿ������쳣ԭ��%s' % (str(server), conn)
        Logging.getLog().critical(err)
        return -1, err
    cursor = conn.cursor()
    if conn < 0:
        gl.threadQueue.put((-1, u"�������ݿ��쳣", "RunInitScript", server))  # ���ؽ��������У����߳̽������ȡ���н��
        return -1, u"�������ݿ��쳣"

    if gl.g_JZJYSystemSetting.get(str(server)).attrib["type"] in ["z", "p", "v"]:
        init_script_file = "AutoTest_Init.sql"
    else:
        init_script_file = "AutoTest_Init(90,11).sql"
    key_dict = {}
    sql = "select top 1 serverid, orderdate,sysdate,lastsysdate from run..sysconfig where serverid = %d" % int(server)
    cursor.execute(sql)
    ds = cursor.fetchall()
    key_dict["@sid"] = str(ds[0][0])
    key_dict["@orderdate"] = str(ds[0][1])
    key_dict["@opendate"] = str(ds[0][2])
    key_dict["@lastsysdate"] = str(ds[0][3])
    f = open(init_script_file, 'r')
    lines = f.readlines()
    try:
        for j, line in enumerate(lines):
            line = line.strip()
            if line.startswith('--'):
                continue
            if len(line) == 0:
                continue
            line = line.decode('gbk')
            print j
            # print line

            if "select" in line:
                # ���ñ���ֵ
                if "@futureday1" in line and "@futureday2" not in line:
                    l = line.split(",")[-1]
                    delta = int(''.join(l.split(")")))
                    k = cF.dateoffset(key_dict["@orderdate"], delta)
                    key_dict["@futureday1"] = k
                elif "@futureday2" in line:
                    l = line.split(",")[-1]
                    delta = int(''.join(l.split(")")))
                    k = cF.dateoffset(key_dict["@orderdate"], delta)
                    key_dict["@futureday2"] = k
                else:
                    line = ''.join(line.split('@'))
                    sql = line
                    j = cursor.execute(sql)
                    ds = j.fetchone()

                    i = 0
                    m = len(ds)
                    m = m - 1
                    while i <= m:
                        key_dict['@' + ds.cursor_description[i][0]] = str(ds[i]).decode('gbk')
                        i = i + 1
                pass
            else:
                for key in key_dict:
                    line = line.replace(key, "'%s'" % str(key_dict[key]))
                # print line

                cursor.execute(line)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().info(u"�ں���%s���г�ʼ���ű� �����쳣����ʾ��Ϣ line %d  %s����" % (str(server), j, exc_info))
        cursor.close()
        conn.rollback()
        conn.close()
        gl.threadQueue.put((-1, u"exc_info", "RunInitScript", server))  # ���ؽ��������У����߳̽������ȡ���н��
        return -1, exc_info
    cursor.close()
    conn.commit()
    conn.close()
    Logging.getLog().info(u"�ں���%s���г�ʼ���ű����" % str(server))
    gl.threadQueue.put((ret, msg, "UnInitJZJYDB", server))  # ���ؽ��������У����߳̽������ȡ���н��

    return 0, ""


if __name__ == '__main__':
    cF.readConfigFile()
    time1 = time.time()
    scanJZJYDB()
    # createJZJYTrigger(10)
    initJZJYDB(10)
    print (time.time() - time1)
