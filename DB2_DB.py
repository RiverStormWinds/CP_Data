# -*- coding:gbk -*-
import pyodbc
import commFuncs as cF
from gl import GlobalLogging as Logging
from lxml import etree

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def DB2SkDB():
    HOSTNAME = '10.10.13.23'
    UID = 'back2'
    PWD = 'back2'
    # CURRENTSCHEMA='KS'
    dbstring = "driver={IBM DB2 ODBC DRIVER};database=KSDBS;hostname=%s;port=50000;protocol=tcpip;uid=%s;pwd=%s;" % (
        HOSTNAME, UID, PWD)
    print dbstring
    return pyodbc.connect(dbstring)


def selct():
    try:
        conn = DB2SkDB()
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"连接数据库出现异常,%s" % exc_info
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()
    sql = "select * from  KS.APPLY_HOLDER_ACC"
    crs.execute(sql)
    ds = crs.fetchall()
    print ds[0]


def generateDB2ColumnXml():
    """
    产生数据库字段配置表
    """
    Logging.getLog().info(u"扫描DB2数据库开始")
    root = etree.Element("comparesetting")
    try:
        conn = DB2SkDB()
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"连接数据库出现异常,%s" % exc_info
        Logging.getLog().critical(err)
        return -1, err
    crs = conn.cursor()
    try:
        schemaElem = etree.SubElement(root, "schema", schemaname='KS')
        sql = "select NAME from sysibm.systables where type='T' AND CREATOR='KS'"
        r = crs.execute(sql)
        ds_tablename = r.fetchall()
        for i, table in enumerate(ds_tablename):
            if table[0].startswith('AUTO_D_') or table[0].startswith('AUTO_I_'):
                continue
            tableElem = etree.SubElement(schemaElem, "table", tablename=table[0])
            tableElem.attrib["have_exclude_column"] = "0"
            tableElem.attrib["disableflag"] = '0'
            sql = "select NAME from sysibm.syscolumns where tbname = '%s' AND TBCREATOR='KS'" % (table[0])
            r = crs.execute(sql)
            ds_columns = r.fetchall()
            for column in ds_columns:
                subElem = etree.SubElement(tableElem, "column", column_name=column[0])
                subElem.attrib["is_exclude"] = "0"
                subElem.attrib["disableflag"] = "0"
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"数据库执行%s后出现异常,%s" % (sql, exc_info)
        Logging.getLog().critical(err)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err
    crs.close()
    conn.close()
    doc = etree.ElementTree(root)
    doc.write("DB2_column_report_scan.xml", pretty_print=True, xml_declaration=True, encoding='utf-8')
    Logging.getLog().info(u"扫描DB2数据库完成")
    return 0, ""


def createHTKSempTable():
    Logging.getLog().info(u"准备在创建临时表……")
    doc = ET.parse("DB2_column_report_scan.xml")
    table_root = doc.getroot()
    conn = DB2SkDB()
    crs = conn.cursor()
    try:
        sql = "select NAME from sysibm.systables where type='T' AND CREATOR='KS' AND NAME='TMP_AUTOTEST_TRIGGER'"
        crs.execute(sql)
        print sql
        ds = crs.fetchall()
        # if len(ds) !=0:
        #    sql = "drop table KS.TMP_AUTOTEST_TRIGGER;"
        #    try:
        #        crs.execute(sql)
        #    except:
        #        print "%s fail and continue" %(sql)
        #    conn.commit()
        # print sql
        # sql = "create table KS.TMP_AUTOTEST_TRIGGER(username VARCHAR(12),tablename VARCHAR(32),operation int)"
        # crs.execute(sql)
        # conn.commit()
        # print sql
        for schemaElem in table_root:
            for i, tableElem in enumerate(schemaElem):
                if tableElem.attrib["disableflag"] == "1":
                    continue
                schema = schemaElem.attrib["schemaname"]
                tablename = tableElem.attrib["tablename"]
                sql_i = "select COUNT(*) from sysibm.systables where CREATOR='KS' AND name='AUTO_I_%s';" % (tablename)
                # print sql_i
                sql_d = "select COUNT(*) from sysibm.systables where CREATOR='KS' AND name='AUTO_D_%s';" % (tablename)
                # print sql_d

                r = crs.execute(sql_i)
                ds_i = crs.fetchall()
                r = crs.execute(sql_d)
                ds_d = crs.fetchall()
                if ds_i[0][0] != 0:
                    sql = "drop table %s.AUTO_I_%s " % (schema, tablename)
                    print sql
                    try:
                        crs.execute(sql)
                    except:
                        print "%s fail and continue" % sql
                    conn.commit()
                if ds_d[0][0] != 0:
                    sql = "drop table %s.AUTO_D_%s " % (schema, tablename)
                    print sql
                    try:
                        crs.execute(sql)
                    except:
                        print "%s fail and continue" % sql
                    conn.commit()
                # c_i = "create table %s.AUTO_I_%s like %s.%s;" %(schema,tablename,schema,tablename)
                # c_d = "create table %s.AUTO_D_%s like %s.%s;" %(schema,tablename,schema,tablename)
                ##print c_i
                ##print c_d
                # r = crs.execute(c_i)
                # r = crs.execute(c_d)
                conn.commit()
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        err = u"连接数据库出现异常，%s" % exc_info
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err
    crs.close()
    conn.close()
    Logging.getLog().info(u"创建临时表完毕")
    return 0, ""


def createHTKSTrigger():
    Logging.getLog().info(u"准备在创建触发器……")
    doc = ET.parse("DB2_column_report_scan.xml")
    table_root = doc.getroot()
    conn = DB2SkDB()
    crs = conn.cursor()
    try:
        sql = "select trigname from syscat.triggers WHERE tabschema='KS' and trigname LIKE 'KS_%_%_TRIGGER'"
        crs.execute(sql)
        ds = crs.fetchall()
        for rec in ds:
            sql = "drop trigger KS.%s" % (rec[0])
            print sql
            try:
                crs.execute(sql)
            except:
                print "%s except and continue" % sql
            conn.commit()
            # 创建新触发器
            # for schemaElem in table_root:
            #    for i,tableElem in enumerate(schemaElem):
            #        if tableElem.attrib["disableflag"] == "1":
            #            continue
            #        schema = schemaElem.attrib["schemaname"]
            #        tablename = tableElem.attrib["tablename"]
            #        #if tableElem.attrib["have_exclude_column"] == "1":
            #        column_list = []
            #        for columnElem in tableElem:
            #            if columnElem.attrib["is_exclude"] == "0":
            #                column_list.append(columnElem.attrib["column_name"])
            #        sql_d = "CREATE TRIGGER %s.%s_%d_d_trigger AFTER DELETE ON %s.%s REFERENCING OLD AS O FOR EACH ROW MODE DB2SQL begin atomic insert into KS.TMP_AUTOTEST_TRIGGER(username,tablename,operation) values('%s','%s',3);insert into %s.AUTO_D_%s (%s) values (%s); end"%(schema,schema,i,schema,tablename,schema,tablename,schema,tablename,",".join(column_list),"O."+",O.".join(column_list))
            #        sql_u = "CREATE TRIGGER %s.%s_%d_u_trigger AFTER UPDATE ON %s.%s REFERENCING OLD AS O FOR EACH ROW MODE DB2SQL begin atomic insert into KS.TMP_AUTOTEST_TRIGGER(username,tablename,operation) values('%s','%s',2);insert into %s.AUTO_I_%s (%s) values (%s); end"%(schema,schema,i,schema,tablename,schema,tablename,schema,tablename,",".join(column_list),"O."+",O.".join(column_list))
            #        sql_i = "CREATE TRIGGER %s.%s_%d_i_trigger AFTER INSERT ON %s.%s REFERENCING NEW AS O FOR EACH ROW MODE DB2SQL begin atomic insert into KS.TMP_AUTOTEST_TRIGGER(username,tablename,operation) values('%s','%s',1);insert into %s.AUTO_I_%s (%s) values (%s); end"%(schema,schema,i,schema,tablename,schema,tablename,schema,tablename,",".join(column_list),"O."+",O.".join(column_list))
            #        #print sql_d
            #        #print sql_u
            #        #print sql_i
            #        #print '==========================================='
            #        crs.execute(sql_d)
            #        crs.execute(sql_u)
            #        crs.execute(sql_i)
            #        conn.commit()
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        err = u"出现异常，提示%s" % (exc_info)
        Logging.getLog().critical(err)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err
    crs.close()
    conn.close()
    Logging.getLog().info(u"创建触发器完毕")
    return 0, ""


def truncateHTKSempTable():
    Logging.getLog().info(u"准备清空临时表……")
    doc = ET.parse("DB2_column_report_scan.xml")
    table_root = doc.getroot()
    conn = DB2SkDB()
    crs = conn.cursor()
    try:
        sql = "select NAME from sysibm.systables where type='T' AND CREATOR='KS' AND NAME='TMP_AUTOTEST_TRIGGER'"
        crs.execute(sql)
        print sql
        ds = crs.fetchall()
        conn.commit()

        if len(ds) != 0:
            sql = "truncate table KS.TMP_AUTOTEST_TRIGGER IMMEDIATE;"
            crs.execute(sql)
            conn.commit()
            # print sql
        # print sql
        for schemaElem in table_root:
            for i, tableElem in enumerate(schemaElem):
                if tableElem.attrib["disableflag"] == "1":
                    continue
                schema = schemaElem.attrib["schemaname"]
                tablename = tableElem.attrib["tablename"]
                sql_i = "select COUNT(*) from sysibm.systables where CREATOR='KS' AND name='AUTO_I_%s';" % (tablename)
                # print sql_i
                sql_d = "select COUNT(*) from sysibm.systables where CREATOR='KS' AND name='AUTO_D_%s';" % (tablename)
                # print sql_d
                r = crs.execute(sql_i)
                ds_i = crs.fetchall()
                r = crs.execute(sql_d)
                ds_d = crs.fetchall()
                conn.commit()
                if ds_i[0][0] != 0:
                    sql = "truncate table %s.AUTO_I_%s IMMEDIATE " % (schema, tablename)
                    # print sql
                    crs.execute(sql)
                if ds_d[0][0] != 0:
                    conn.commit()
                    sql = "truncate table %s.AUTO_D_%s IMMEDIATE" % (schema, tablename)
                    # print sql
                    crs.execute(sql)
                conn.commit()
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        err = u"连接数据库出现异常，%s" % exc_info
        crs.close()
        conn.rollback()
        conn.close()
        return -1, err
    crs.close()
    conn.close()
    Logging.getLog().info(u"清空临时表完毕")
    return 0, ""


if __name__ == '__main__':
    # createHTKSempTable()#临时表
    createHTKSempTable()  # 触发器
    # createHTKSTrigger()
    pass
