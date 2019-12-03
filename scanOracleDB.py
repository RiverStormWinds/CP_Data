# -*- coding: gbk -*-
import time
import gl
import threading
import commFuncs as cF
import cx_Oracle
import pyodbc
import json
from gl import GlobalLogging as Logging
import subprocess
import os
from collections import OrderedDict
import chardet
import difflib
import MySQLdb
import csv

global rst_database_info
rst_database_info = None
global rst_table_info
rst_table_info = None
global rst_column_info
rst_column_info = None
global dictTableInfo
dictTableInfo = {}
global dictColumnInfo
dictColumnInfo = {}
global RestorePointTime
RestorePointTime = None
global rst_database_info_for_trigger
rst_database_info_for_trigger = None
global rst_table_info_for_trigger
rst_table_info_for_trigger = None
global rst_column_info_for_trigger
rst_column_info_for_trigger = None
global dictTableInfoForTrigger
dictTableInfoForTrigger = {}
global dictColumnInfoForTrigger
dictColumnInfoForTrigger = {}


def scanOracleDB(system_id):
    """
    根据数据库配置，扫描整个Oracle数据库，获取schema，table，column，以及主键信息，并保存到相关数据表
    :return:
    """
    try:
        start = time.clock()
        ret, old_table_dict = getTableColumnInfo(system_id, "ORACLE")
        if ret < 0:
            raise Exception(old_table_dict)

        table_primary_key_dict = OrderedDict()  # {"service_name":{"schema":{"table_name":"primary_key_list_string"}}}
        table_column_info_dict = OrderedDict()

        str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info where system_id = '%s' and db_type= 'ORACLE'" % system_id
        # rst_database_info = cF.executeCaseSQL(str_MySQL_SQL)
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        # crs.execute(str_MySQL_SQL)
        # rst_database_info = crs.fetchall()
        rst_database_info = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        db_id_dict = OrderedDict()

        # 获取数据库信息
        for rec in rst_database_info:
            db_id = rec['DB_ID']
            username = rec['DB_USERNAME']
            password = rec['DB_PASSWORD']
            servicename = rec['DB_SERVICENAME']
            schema = rec['DB_SCHEMA']

            if not db_id_dict.has_key(db_id):
                db_id_dict[db_id] = OrderedDict()
                db_id_dict[db_id]['schema_list'] = []
            db_id_dict[db_id]['username'] = username
            db_id_dict[db_id]['password'] = password
            db_id_dict[db_id]['servicename'] = servicename
            db_id_dict[db_id]['schema_list'].append(schema)

        # 逐一数据库收集主键，表，字段信息
        for db_id in db_id_dict.keys():
            conn = cx_Oracle.connect(db_id_dict[db_id]['username'], db_id_dict[db_id]['password'],
                                     db_id_dict[db_id]['servicename'])
            cursor = conn.cursor()

            # 获取Oracle 表主键信息
            schema_string_list = []
            for schema in db_id_dict[db_id]['schema_list']:
                schema_string_list.append("'%s'" % schema)
            str_Oracle_SQL = "select owner, table_name,column_name,position from " \
                             "dba_cons_columns where owner in (%s) and " \
                             "constraint_name in (select constraint_name " \
                             "from dba_constraints where owner in (%s) and " \
                             "constraint_type='P') order by owner,table_name,position" \
                             % (','.join(schema_string_list), ','.join(schema_string_list))
            # %(','.join(db_id_dict[db_id]['schema_list']),','.join(db_id_dict[db_id]['schema_list']))
            # print str_Oracle_SQL
            cursor.execute(str_Oracle_SQL)
            rs = cursor.fetchall()

            for rec in rs:
                owner = rec[0]
                table_name = rec[1]
                column = rec[2]

                if not table_primary_key_dict.has_key(db_id):
                    table_primary_key_dict[db_id] = OrderedDict()

                if not table_primary_key_dict[db_id].has_key(owner):
                    table_primary_key_dict[db_id][owner] = OrderedDict()

                if not table_primary_key_dict[db_id][owner].has_key(table_name):
                    table_primary_key_dict[db_id][owner][table_name] = []

                table_primary_key_dict[db_id][owner][table_name].append(column)

            # 找出所有的表名，注意直接从DBA_TAB_COLUMNS获取的表名不准确
            table_name_list = []
            str_Oracle_SQL = "SELECT TABLE_NAME FROM ALL_TABLES WHERE owner in (%s)" % (','.join(schema_string_list))
            Logging.getLog().debug(str_Oracle_SQL)
            cursor.execute(str_Oracle_SQL)
            rst_table = cursor.fetchall()
            for rec in rst_table:
                table_name_list.append("'%s'" % rec[0])
            num = 0
            before_table_name_list, after_table_name_list = [], []
            if table_name_list:
                num = len(table_name_list) / 2
                before_table_name_list = table_name_list[0:num]
                after_table_name_list = table_name_list[num:]
            str_Oracle_SQL = "SELECT OWNER,TABLE_NAME,COLUMN_NAME,COLUMN_ID FROM DBA_TAB_COLUMNS WHERE OWNER IN (%s)  AND  DATA_TYPE NOT IN ('RAW','LONG RAW','BLOB','BFILE','NROWID') AND TABLE_NAME IN (%s) or TABLE_NAME IN (%s) ORDER BY OWNER,TABLE_NAME,COLUMN_ID" % (
                ','.join(schema_string_list), ','.join(before_table_name_list), ','.join(after_table_name_list))
            # print str_Oracle_SQL
            cursor.execute(str_Oracle_SQL)
            rst_column = cursor.fetchall()
            for rec in rst_column:
                owner = rec[0]
                table_name = rec[1]
                column = str(rec[2]).strip()
                column_id = rec[3]
                if not table_column_info_dict.has_key(db_id):
                    table_column_info_dict[db_id] = OrderedDict()
                if not table_column_info_dict[db_id].has_key(owner):
                    table_column_info_dict[db_id][owner] = OrderedDict()
                if not table_column_info_dict[db_id][owner].has_key(table_name):
                    table_column_info_dict[db_id][owner][table_name] = OrderedDict()
                    table_column_info_dict[db_id][owner][table_name]["disableflag"] = 0
                    table_column_info_dict[db_id][owner][table_name]["column_list"] = OrderedDict()
                    table_column_info_dict[db_id][owner][table_name]["pk"] = ""
                if not table_column_info_dict[db_id][owner][table_name]["column_list"].has_key(column):
                    table_column_info_dict[db_id][owner][table_name]["column_list"][column] = OrderedDict()
                table_column_info_dict[db_id][owner][table_name]["column_list"][column]["disableflag"] = 0
                table_column_info_dict[db_id][owner][table_name]["column_list"][column]["is_exclude"] = 0
                table_column_info_dict[db_id][owner][table_name]["column_list"][column]["idx"] = column_id

            ###############
            # 设置主键
            for db_id in table_primary_key_dict.keys():
                for schema in table_primary_key_dict[db_id].keys():
                    for table_name in table_primary_key_dict[db_id][schema].keys():
                        # if table_name == 'BIN$UxpM8JcKL3/gUAEKEAEz1w==$0':
                        #     pass
                        if table_column_info_dict[db_id][schema].has_key(table_name):
                            table_column_info_dict[db_id][schema][table_name]['pk'] = ','.join(
                                table_primary_key_dict[db_id][schema][table_name])

            # 设置之前的disable值
            for db_id in old_table_dict.keys():
                for schema in old_table_dict[db_id].keys():
                    # print schema
                    for table in old_table_dict[db_id][schema].keys():
                        if old_table_dict[db_id][schema][table]["disableflag"] == 1:
                            print "table %s == 1" % table
                            table_column_info_dict[db_id][schema][table]["disableflag"] = 1
                        for column in old_table_dict[db_id][schema][table]["column_list"].keys():
                            if old_table_dict[db_id][schema][table]["column_list"][column]["disableflag"] == 1:
                                table_column_info_dict[db_id][schema][table]["column_list"][column]["disableflag"] = 1

        # gl.g_table_column_disable_info = table_column_info_dict
        ret, msg = saveOracleTableColumnInfo(system_id, table_column_info_dict)
        if ret < 0:
            gl.threadQueue.put((-1, msg, "scanOracleDB"))
            return ret, msg

        gl.threadQueue.put((0, "", "scanOracleDB"))
        print "scanOracleDB cost %s" % str(time.clock() - start)
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
        return -1, exc_info


def update_sx_column_info_disableflag():
    try:

        str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password," \
                        "db_servicename,db_schema from sx_database_info where DB_TYPE='ORACLE'"
        rst_temp = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        for item in rst_temp:
            str_db_id = item['DB_ID']
            str_db_type = item['DB_TYPE']
            str_db_alias = item['DB_ALIAS']
            str_db_ip = item['DB_IP']
            str_db_port = item['DB_PORT']
            str_db_username = item['DB_USERNAME']
            str_db_password = item['DB_PASSWORD']
            str_db_servicename = item['DB_SERVICENAME']
            str_db_schema = item['DB_SCHEMA']
            conn = cx_Oracle.connect(str_db_username, str_db_password, str_db_servicename)
            cursor = conn.cursor()
            str_Oracle_SQL = "SELECT OWNER,TABLE_NAME,COLUMN_NAME,COLUMN_ID, DATA_TYPE FROM DBA_TAB_COLUMNS WHERE " \
                             "OWNER IN ('%s')  AND  DATA_TYPE IN ('RAW','LONG RAW','BLOB','BFILE','NROWID') " % str_db_schema
            cursor.execute(str_Oracle_SQL)
            for row in cursor.fetchall():
                OWNER, TABLE_NAME, COLUMN_NAME, COLUMN_ID, DATA_TYPE = row
                sql = "update SX_COLUMN_INFO set DISABLEFLAG= 1 where TABLE_ID in (select TABLE_ID from SX_TABLE_INFO " \
                      "where TABLENAME='%s' and DB_ID=%s) and COLUMNNAME='%s'" % (TABLE_NAME, str_db_id, COLUMN_NAME)
                Logging.getLog().info(sql)
                cF.executeCaseSQL_DB2(sql)
            cursor.close()
            conn.close()
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
        return -1, exc_info


# def compare_chage_data_order_by_csv_files():
#     try:
#         return 0, ""
#     except BaseException, ex:
#         exc_info = cF.getExceptionInfo()
#         Logging.getLog().critical(exc_info)
#         gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
#         return -1, exc_info

def delete_change_data_oracle_or_slqserver():
    try:
        str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info"
        rst_temp = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        for item in rst_temp:
            str_db_id = item['DB_ID']
            str_db_type = item['DB_TYPE']
            str_db_alias = item['DB_ALIAS']
            str_db_ip = item['DB_IP']
            str_db_port = item['DB_PORT']
            str_db_username = item['DB_USERNAME']
            str_db_password = item['DB_PASSWORD']
            str_db_servicename = item['DB_SERVICENAME']
            str_db_schema = item['DB_SCHEMA']
            if str_db_type == "SQLServer":
                # continue
                dbstring = ""
                if str_db_type.strip() == "SQLServer":
                    dbstring = 'DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;' \
                               'autocommit=True' % (str_db_ip, str_db_schema, str_db_username, str_db_password)
                conn = pyodbc.connect(dbstring)
                cursor = conn.cursor()
                sql = "delete from run..TMP_AUTOTEST_TRIGGER"
                cursor.execute(sql)
                conn.commit()
                cursor.close()
                conn.close()
            else:
                try:
                    if str_db_schema in ("HS_ACCT", "CIF"):
                        con = cx_Oracle.connect(str_db_username, str_db_password, str_db_servicename)
                        cursor = con.cursor()
                        sql = """select lpad(' ',decode(l.xidusn ,0,3,0))||l.oracle_username user_name,
                                       o.OWNER,
                                       o.OBJECT_NAME,
                                       o.OBJECT_TYPE,
                                       s.SID,
                                       s.serial# as SERIAL
                                from v$locked_object l,dba_objects o,v$session s
                                where l.object_id=o.object_id
                                and l.session_id=s.sid
                                order by o.object_id,xidusn desc"""
                        cursor.execute(sql)
                        for row in cursor.fetchall():
                            USER_NAME, OWNER, OBJECT_NAME, OBJECT_TYPE, SID, SERIAL = row
                            print USER_NAME, OWNER, OBJECT_NAME, OBJECT_TYPE, SID, SERIAL
                            sql = "alter system kill session '%s,%s';" % (SID, SERIAL)
                            print sql
                            cursor.execute(sql)
                            con.commit()
                        # str_Oracle_SQL = "delete from SYSTEM.TMP_AUTOTEST_TRIGGER where  rownum <=10000"
                        str_Oracle_SQL = "truncate table system.tmp_autotest_trigger"
                        cursor.execute(str_Oracle_SQL)
                        con.commit()
                        cursor.close()
                        con.close()
                except BaseException, ex:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().critical(exc_info)
                    return -1, exc_info
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        gl.threadQueue.put((-1, exc_info, "scanOracleDB"))
        return -1, exc_info


# def delete_TMP_AUTOTEST_TRIGGER(con, cursor):
#     print 'delete delete_TMP_AUTOTEST_TRIGGER '
#     sql = "select /*+ rule */ lpad(' ',decode(l.xidusn ,0,3,0))||l.oracle_username user_name, o.owner, o.object_name, o.object_type, s.sid, s.serial# from v$locked_object l,dba_objects o,v$session s where l.object_id=o.object_id and l.session_id=s.sidorder by o.object_id,xidusn desc"
#     cursor.execute(sql)
#     for row in cursor.fetchall():
#
#     str_Oracle_SQL = "delete from SYSTEM.TMP_AUTOTEST_TRIGGER where  rownum <=10000"
#     cursor.execute(str_Oracle_SQL)
#     str_Oracle_SQL = "select count(*) as num from SYSTEM.TMP_AUTOTEST_TRIGGER where rownum <=10"
#     cursor.execute(str_Oracle_SQL)
#     result = cursor.fetchall()
#     if result[0][0]:
#         print result
#         delete_TMP_AUTOTEST_TRIGGER(con, cursor)
#     else:
#         con.commit()
#         return con, cursor
def get_change_data_oracle_or_slqserver():
    try:
        count = 0
        homepath = os.getcwd()
        date = time.strftime("%Y%m%d%H%M%S", time.localtime())
        log_path = os.path.join(homepath, "case_change_data")
        if not os.path.isdir(log_path):
            os.mkdir(log_path)
        log_path = os.path.join(log_path, "%s" % date)
        os.mkdir(log_path)
        str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info"
        rst_temp = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        for item in rst_temp:
            str_db_id = item['DB_ID']
            str_db_type = item['DB_TYPE']
            str_db_alias = item['DB_ALIAS']
            str_db_ip = item['DB_IP']
            str_db_port = item['DB_PORT']
            str_db_username = item['DB_USERNAME']
            str_db_password = item['DB_PASSWORD']
            str_db_servicename = item['DB_SERVICENAME']
            str_db_schema = item['DB_SCHEMA']
            if str_db_type == "SQLServer":
                continue
                dbstring = ""
                if str_db_type.strip() == "SQLServer":
                    dbstring = 'DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;' \
                               'autocommit=True' % (str_db_ip, str_db_schema, str_db_username, str_db_password)
                conn = pyodbc.connect(dbstring)
                cursor = conn.cursor()
                sql = "select * from run..TMP_AUTOTEST_TRIGGER"
                cursor.execute(sql)
                for row in cursor.fetchall():
                    tablename, operation, change_content = row
                    print tablename, operation, change_content
                    if not change_content or change_content == None or change_content == 'None':
                        continue
                    else:
                        change_content = change_content.decode("gbk")
                    flag = ""
                    if operation == 0:
                        flag = "insert"
                    elif operation == 1:
                        flag = "update"
                    else:
                        flag = "delete"
                    sql = "select c.COLUMNNAME as COLUMNNAME from SX_COLUMN_INFO c left join SX_TABLE_INFO t on t.TABLE_ID=c.TABLE_ID where t.TABLENAME='%s' and t.DB_ID=%s ORDER BY c.IDX" % (
                        tablename, str_db_id)
                    COLUMNNAMEs = cF.executeCaseSQL_DB2(sql)
                    COLUMNNAME_LIST = [i["COLUMNNAME"] for i in COLUMNNAMEs]
                    if flag in ("insert", "delete"):
                        tablename_csv = tablename + "%s." % flag
                        data = change_content.split("&")
                        line_data = [str(i) for i in data]
                        _log_path = os.path.join(log_path, "run.6.%s_0.csv" % (tablename_csv))
                        if os.path.exists(_log_path):
                            num = int(_log_path.replace(".csv", "")[-1:]) + 1
                            _log_path = os.path.join(log_path, "run.6.%s_%s.csv" % (tablename_csv, num))
                        csvfile = file(_log_path, 'wb')
                        writer = csv.writer(csvfile)
                        writer.writerow(COLUMNNAME_LIST)
                        writer.writerows([tuple(line_data)])
                        csvfile.close()
                    else:
                        # {"old":"6&600000109&2&9698000.00","new":"6&600000109&1&9698000.00"}
                        before_tablename_csv = tablename + ".update_before"
                        after_tablename_csv = tablename + ".update_after"
                        # change_content = json.loads(change_content)
                        change_content = eval(change_content)
                        old_data = change_content["old"]
                        new_data = change_content["new"]
                        old_data = old_data.split("&")
                        line_old_data = [str(i) for i in old_data]
                        new_data = new_data.split("&")
                        line_new_data = [str(i) for i in new_data]
                        before_log_path = os.path.join(log_path, "run.6.%s_0.csv" % (before_tablename_csv))
                        if os.path.exists(before_log_path):
                            num = int(before_log_path.replace(".csv", "")[-1:]) + 1
                            before_log_path = os.path.join(log_path, "run.6.%s_%s.csv" % (before_tablename_csv, num))
                        after_log_path = os.path.join(log_path, "run.6.%s_0.csv" % (after_tablename_csv))
                        if os.path.exists(after_log_path):
                            num = int(after_log_path.replace(".csv", "")[-1:]) + 1
                            after_log_path = os.path.join(log_path, "run.6.%s_%s.csv" % (after_tablename_csv, num))
                        # before
                        csvfile = file(before_log_path, 'wb')
                        writer = csv.writer(csvfile)
                        writer.writerow(COLUMNNAME_LIST)
                        writer.writerows([tuple(line_old_data)])
                        csvfile.close()
                        # after
                        csvfile = file(after_log_path, 'wb')
                        writer = csv.writer(csvfile)
                        writer.writerow(COLUMNNAME_LIST)
                        writer.writerows([tuple(line_new_data)])
                        csvfile.close()
            else:
                pre = 0
                if str_db_schema == "CIF":
                    pre = 1
                if str_db_schema in ("HS_ACCT", "HS_BANK", "HS_AAS", "HS_USER", "HS_PAY", "HS_ARCH"):
                    count += 1
                if count == 1 or str_db_schema == "CIF":
                    con = cx_Oracle.connect(str_db_username, str_db_password, str_db_servicename)
                    cursor = con.cursor()
                    str_Oracle_SQL = "select username, tablename, operation, change_content from SYSTEM.TMP_AUTOTEST_TRIGGER"
                    cursor.execute(str_Oracle_SQL)
                    while (True):
                        row = cursor.fetchone()
                        if row == None:
                            break
                        # for row in cursor.fetchall():
                        #     change_content_str = ""
                        username = row[0]
                        str_db_id = 0
                        if username == "HS_ACCT":
                            str_db_id = 4
                        elif username == "HS_BANK":
                            str_db_id = 5
                        elif username == "HS_AAS":
                            str_db_id = 6
                        elif username == "HS_USER":
                            str_db_id = 7
                        elif username == "HS_PAY":
                            str_db_id = 8
                        elif username == "HS_ARCH":
                            str_db_id = 9
                        elif username == "CIF":
                            str_db_id = 10
                        else:
                            pass
                        tablename = row[1]
                        operation = row[2]
                        change_content = row[3]
                        change_content = change_content.read()
                        # change_content = change_content_str
                        replace_values = {}
                        replace_values_0 = {}
                        replace_values_1 = {}
                        if "TYWQQ" == tablename:
                            pass

                        if tablename == "TYWQQCL":
                            pass
                        if not change_content or change_content == None or change_content == 'None':
                            continue
                        else:
                            # change_content = change_content.replace("&amp;", "&")
                            change_content = change_content.decode("gbk")
                            # change_content = change_content
                        flag = ""
                        if operation == 0:
                            flag = "insert"
                        elif operation == 1:
                            flag = "update"
                        else:
                            flag = "delete"
                        sql = "select c.COLUMNNAME as COLUMNNAME from SX_COLUMN_INFO c left join SX_TABLE_INFO t on t.TABLE_ID=c.TABLE_ID where t.TABLENAME='%s' and t.DB_ID=%s ORDER BY c.IDX" % (
                            tablename, str_db_id)
                        COLUMNNAMEs = cF.executeCaseSQL_DB2(sql)
                        COLUMNNAME_LIST = [i["COLUMNNAME"] for i in COLUMNNAMEs]
                        COLUMNNAME_LIST = sorted(set(COLUMNNAME_LIST), key=COLUMNNAME_LIST.index)
                        if flag in ("insert", "delete"):
                            tablename_csv = tablename + ".%s" % flag
                            data = change_content.split("&amp;")
                            line_data = [str(i).replace(",", "&amp;") for i in data]
                            _log_path = os.path.join(log_path, "%s.%s.%s_0.csv" % (pre, username, tablename_csv))
                            if os.path.exists(_log_path):
                                num = int(_log_path.replace(".csv", "")[-1:]) + 1
                                _log_path = os.path.join(log_path,
                                                         "%s.%s.%s_%s.csv" % (pre, username, tablename_csv, num))
                            csvfile = file(_log_path, 'wb')
                            writer = csv.writer(csvfile)
                            writer.writerow(COLUMNNAME_LIST)
                            writer.writerows([tuple(line_data)])
                            csvfile.close()
                        else:
                            try:
                                # {"old":"6&600000109&2&9698000.00","new":"6&600000109&1&9698000.00"}
                                before_tablename_csv = tablename + ".update_before"
                                after_tablename_csv = tablename + ".update_after"
                                if username == 'CIF' and tablename == 'TYWQQCL':
                                    pass
                                json_b = ""
                                try:
                                    # change_content = change_content.replace("&amp;", ",")
                                    # change_content = json.loads(change_content)
                                    if tablename == "FUNDACCOUNTAUTH":
                                        key_special1 = "*FS'Yr%-/\""
                                        replace_values_0["key_special1"] = key_special1
                                        change_content = change_content.replace(key_special1, "key_special1")
                                    change_content = eval(change_content)
                                except Exception as e:
                                    print username, tablename, operation, change_content
                                    print e
                                    # return -1, exc_info
                                    # json串的值中包含json串有误，需要把json串截取出来替换
                                    # time_nums = change_content.count(':{')
                                    for time_num in ['j', 'k', 'l', 'm', 'n']:
                                        if ":[{" in change_content:
                                            key = "replace_value_%s" % time_num
                                            index_3 = change_content.find(':[{')
                                            index_4 = change_content.find('}]', index_3)
                                            replace_value = change_content[index_3 + 1:index_4 + 2]
                                            replace_values_1[key] = replace_value
                                            change_content = change_content.replace(replace_value, key)
                                        else:
                                            break
                                    for time_num in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                                        if ":{" in change_content:
                                            key = "replace_value_%s" % time_num
                                            index_3 = change_content.find(':{')
                                            index_4 = change_content.find('}', index_3)
                                            replace_value = change_content[index_3 + 1:index_4 + 1]
                                            replace_values_0[key] = replace_value
                                            change_content = change_content.replace(replace_value, key)
                                        else:
                                            break
                                    count_1 = change_content.count("{")
                                    count_2 = change_content.count("}")
                                    # print count_1, count_2
                                    if count_1 == count_2 and count_1 >= 2:
                                        print "-------------------------test1"
                                        num = count_1 - 1
                                        b = change_content[1:-1]
                                        # pdb.set_trace()
                                        for i in range(0, num):
                                            print i
                                            index_1 = b.index("{")
                                            index_2 = b.index("}")
                                            # print index_1, index_2 + 1
                                            replace_value = b[index_1:index_2 + 1]
                                            key = "replace_value_%s" % i
                                            replace_values[key] = replace_value
                                            new_b = b.replace(replace_value, key)
                                            b = new_b
                                            if "{" not in b:
                                                break
                                        b = "{" + b + "}"
                                        if b.count(r'\x') >= 5:
                                            b = b.decode('utf-8')
                                        json_b = eval(b)
                                        # print json_b["old"].decode("utf-8")
                                        # print json_b["new"].decode("utf-8")
                                if json_b:
                                    change_content = json_b
                                old_data = change_content["old"]
                                if old_data.count('\\x') >= 5:
                                    old_data = old_data.decode('utf-8')
                                new_data = change_content["new"]
                                if new_data.count('\\x') >= 5:
                                    new_data = new_data.decode('utf-8')
                                old_data = old_data.split("&amp;")
                                line_old_data = []
                                line_old_datas = [i.replace(",", "&amp;") for i in old_data]
                                if replace_values:
                                    for key in replace_values.keys():
                                        line_old_data = [linedata.decode('utf-8').replace(key, replace_values[key]) for
                                                         linedata in line_old_datas]
                                        # if key in line_old_data:
                                        #     line_old_data[line_old_data.index(key)] = replace_values[key]
                                else:
                                    line_old_data = line_old_datas
                                if replace_values_0:
                                    for key in replace_values_0.keys():
                                        line_old_data = [linedata.decode('utf-8').replace(key, replace_values_0[key])
                                                         for linedata in line_old_datas]
                                        # if key in line_old_data:
                                        #     line_old_data[line_old_data.index(key)] = replace_values[key]
                                if replace_values_1:
                                    for key in replace_values_0.keys():
                                        line_old_data = [linedata.decode('utf-8').replace(key, replace_values_0[key])
                                                         for linedata in line_old_datas]
                                new_data = new_data.split("&amp;")
                                line_new_data = []
                                line_new_datas = [i.replace(",", "&amp;") for i in new_data]
                                if replace_values:
                                    for key in replace_values.keys():
                                        line_new_data = [line_data.decode('utf-8').replace(key, replace_values[key]) for
                                                         line_data in line_new_datas]
                                else:
                                    line_new_data = line_new_datas
                                if replace_values_0:
                                    for key in replace_values_0.keys():
                                        line_old_data = [linedata.decode('utf-8').replace(key, replace_values_0[key])
                                                         for linedata in line_old_datas]
                                if replace_values_1:
                                    for key in replace_values_0.keys():
                                        line_old_data = [linedata.decode('utf-8').replace(key, replace_values_0[key])
                                                         for linedata in line_old_datas]
                                before_log_path = os.path.join(log_path,
                                                               "%s.%s.%s_0.csv" % (pre, username, before_tablename_csv))
                                if os.path.exists(before_log_path):
                                    num = int(before_log_path.replace(".csv", "")[-1:]) + 1
                                    before_log_path = os.path.join(log_path,
                                                                   "%s.%s.%s_%s.csv" % (
                                                                       pre, username, before_tablename_csv, num))
                                after_log_path = os.path.join(log_path,
                                                              "%s.%s.%s_0.csv" % (pre, username, after_tablename_csv))
                                if os.path.exists(after_log_path):
                                    num = int(after_log_path.replace(".csv", "")[-1:]) + 1
                                    after_log_path = os.path.join(log_path, "%s.%s.%s_%s.csv" % (
                                        pre, username, after_tablename_csv, num))
                                # before
                                csvfile = file(before_log_path, 'wb')
                                writer = csv.writer(csvfile)
                                writer.writerow(COLUMNNAME_LIST)
                                writer.writerows([tuple(line_old_data)])
                                csvfile.close()
                                # after
                                csvfile = file(after_log_path, 'wb')
                                writer = csv.writer(csvfile)
                                writer.writerow(COLUMNNAME_LIST)
                                writer.writerows([tuple(line_new_data)])
                                csvfile.close()
                            except Exception as e:
                                print "-------------------------cbs"
                                print username, tablename, operation, change_content
                                print e
                                pass
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def saveOracleTableColumnInfo(system_id, table_column_info_dict):
    '''
    保存扫描出来的数据库表信息
    '''
    try:
        start = time.clock()

        # conn = cF.ConnectCaseDB()
        # crs = conn.cursor(MySQLdb.cursors.DictCursor)
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)

        table_info_param = []
        column_info_param = []

        table_id = 0
        column_id = 0

        # 计算合适的table_id
        sql = "SELECT MAX(table_id) as MAX_ID FROM sx_table_info"
        # crs.execute(sql)
        # ds = list(crs.fetchall())
        ds = cF.executeCaseSQL_DB2(sql)
        if len(ds) == 0 or ds[0]["MAX_ID"] == "" or ds[0]["MAX_ID"] == None:
            table_id = 1
        else:
            table_id = int(ds[0]["MAX_ID"]) + 1

        # 计算合适的column_id
        sql = "SELECT MAX(column_id) AS MAX_ID FROM sx_column_info"
        # crs.execute(sql)
        # ds = list(crs.fetchall())
        ds = cF.executeCaseSQL_DB2(sql)
        if len(ds) == 0 or ds[0]["MAX_ID"] == "" or ds[0]["MAX_ID"] == None:
            column_id = 1
        else:
            column_id = int(ds[0]["MAX_ID"]) + 1

        # 设置值，准备写入数据库
        for db_id in table_column_info_dict.keys():
            for schema in table_column_info_dict[db_id].keys():
                for table_idx, table in enumerate(table_column_info_dict[db_id][schema].keys()):
                    table_info_param.append((table_id, db_id, schema, table,
                                             table_column_info_dict[db_id][schema][table]['pk'],
                                             table_column_info_dict[db_id][schema][table]['disableflag']))
                    for column_idx, column in enumerate(
                            table_column_info_dict[db_id][schema][table]['column_list'].keys()):
                        column_info_param.append((column_id, table_id,
                                                  table_column_info_dict[db_id][schema][table]['column_list'][column][
                                                      'idx'], column,
                                                  table_column_info_dict[db_id][schema][table]['column_list'][column][
                                                      'is_exclude'],
                                                  table_column_info_dict[db_id][schema][table]['column_list'][column][
                                                      'disableflag']))
                        column_id = column_id + 1
                    table_id = table_id + 1

        sql = "delete from sx_column_info WHERE table_id IN (SELECT table_id FROM sx_table_info WHERE db_id IN (SELECT db_id FROM sx_database_info WHERE db_type='ORACLE' AND system_id = '%s'))" % system_id
        cF.executeCaseSQL_DB2(sql)

        # sql = "DELETE FROM SX_TABLE_INFO where db_id in (SELECT db_id FROM sx_database_info WHERE db_type='ORACLE' AND system_id = '%s'))" %system_id

        sql = "delete from SX_TABLE_INFO WHERE db_id IN (SELECT db_id FROM sx_database_info WHERE db_type='ORACLE' AND system_id = '%s')" % system_id
        cF.executeCaseSQL_DB2(sql)

        if table_info_param != []:
            # table_info_param = []
            # table_info_param.append((0,1L,'security','asdf','asdf',0L))
            for tabledata in table_info_param:
                sql = "insert into sx_table_info (table_id,db_id,db_schema,tablename,pk,disableflag) values (%s,%s,'%s','%s','%s',%s)" % tabledata
                cF.executeCaseSQL_DB2(sql)
                # crs.executemany(sql, tuple(table_info_param))

        # sql = "delete from sx_column_info"
        # crs.execute(sql)
        if table_info_param != []:
            for column_info_param in column_info_param:
                sql = "insert into sx_column_info (column_id,table_id,idx,columnname,is_exclude,disableflag) values (%s,%s,%s,'%s',%s,%s)" % column_info_param
                # crs.executemany(sql, tuple(column_info_param))
                cF.executeCaseSQL_DB2(sql)
        # crs.close()
        # conn.commit()
        # conn.close()
        end = time.clock()

        print "save cost %s" % (end - start)
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        # conn.rollback()
        return -1, exc_info


def getTableColumnInfo(system_id, db_type="", db_id=-1):
    """
    获取本地表信息获取表和字段信息，用于保存原始disableflag状态
    :param:
    :   system_id : 系统ID
        db_type: 数据库类型，当前支持ORACLE,SQLSERVER,默认为全部
    ：  db_id : 获取指定的数据库ID，如果为-1，表名取所有的
    :return:
    """
    print "getTableColumnInfo"
    start = time.clock()
    table_dict = OrderedDict()
    try:
        if system_id == "":
            system_id_str = ""
        else:
            system_id_str = "and system_id = '%s'" % system_id
        if db_type == "":
            db_type_str = "(select db_id from sx_database_info where db_type in ('ORACLE','SQLSERVER') %s)" % system_id_str
        else:
            db_type_str = "(select db_id from sx_database_info where db_type in ('%s') %s)" % (db_type, system_id_str)

        if db_id == -1:
            db_id_str = "(select db_id from sx_database_info)"
        else:
            db_id_str = "(%d)" % db_id
        sql = """
        SELECT
            sx_table_info.table_id
            , sx_table_info.db_id
            , sx_table_info.db_schema
            , sx_table_info.tablename
            , sx_table_info.pk
            , sx_table_info.disableflag AS table_dis_flag
            , sx_column_info.column_id
            , sx_column_info.idx
            , sx_column_info.columnname
            , sx_column_info.is_exclude
            , sx_column_info.disableflag AS column_dis_flag
        FROM
            sx_table_info
            INNER JOIN sx_column_info
                ON (sx_table_info.table_id = sx_column_info.table_id)
        WHERE
            sx_column_info.disableflag != 1 and sx_table_info.db_id IN %s and sx_table_info.db_id IN %s
        ORDER BY sx_table_info.db_id,sx_table_info.db_schema,sx_table_info.tablename,sx_column_info.idx
        """ % (db_id_str, db_type_str)
        # sx_table_info.`db_id` IN %s and sx_table_info.db_id IN %s
        Logging.getLog().debug(sql)

        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        # crs.execute(sql)
        # ds = crs.fetchall()
        ds = cF.executeCaseSQL_DB2(sql)
        for rec in ds:
            db_id = rec["DB_ID"]
            schema = rec["DB_SCHEMA"]
            tablename = rec["TABLENAME"]
            columnname = rec["COLUMNNAME"].strip()
            if not table_dict.has_key(db_id):
                table_dict[db_id] = OrderedDict()
            if not table_dict[db_id].has_key(schema):
                table_dict[db_id][schema] = OrderedDict()
            if not table_dict[db_id][schema].has_key(tablename):
                table_dict[db_id][schema][tablename] = OrderedDict()
            if not table_dict[db_id][schema][tablename].has_key("column_list"):
                table_dict[db_id][schema][tablename] = OrderedDict()
                table_dict[db_id][schema][tablename]["column_list"] = OrderedDict()
                table_dict[db_id][schema][tablename]["disableflag"] = rec["TABLE_DIS_FLAG"]
                if rec["TABLE_DIS_FLAG"] == 1:
                    print "tablename %s == 1" % tablename
                table_dict[db_id][schema][tablename]['pk'] = rec['PK']
            # if not table_dict[db_id][schema][tablename]["column_list"].has_key(columnname):
            #     table_dict[db_id][schema][tablename]["column_list"] = OrderedDict()
            if not table_dict[db_id][schema][tablename]["column_list"].has_key(columnname):
                table_dict[db_id][schema][tablename]["column_list"][columnname] = OrderedDict()
            table_dict[db_id][schema][tablename]["column_list"][columnname]["disableflag"] = rec["COLUMN_DIS_FLAG"]
            table_dict[db_id][schema][tablename]["column_list"][columnname]["column_id"] = rec["COLUMN_ID"]
            table_dict[db_id][schema][tablename]["column_list"][columnname]["idx"] = rec["IDX"]
            table_dict[db_id][schema][tablename]["column_list"][columnname]["is_exclude"] = rec["IS_EXCLUDE"]
        # gl.g_table_column_disable_info = table_dict
        end = time.clock()
        print "getTableColumnInfo cost %s" % (end - start)
        return 0, table_dict
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def createOracleTrigger(system_id):
    try:
        global rst_database_info_for_trigger
        global rst_table_info_for_trigger
        global rst_column_info_for_trigger
        global dictTableInfoForTrigger
        global dictColumnInfoForTrigger

        dictTableInfoForTrigger.clear()
        dictColumnInfoForTrigger.clear()

        # fixme remove after debug
        ret, table_column_disable_info = getTableColumnInfo(system_id, "ORACLE")
        if ret < 0:
            gl.threadQueue.put((-1, table_column_disable_info, "createOracleTrigger"))
            return ret, table_column_disable_info
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info where system_id = '%s' and db_type= 'ORACLE'" % system_id
        rst_database_info_for_trigger = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        # crs.execute(str_MySQL_SQL)
        # rst_database_info_for_trigger = crs.fetchall()
        str_MySQL_SQL = "SELECT table_id,db_id,db_schema,tablename,disableflag FROM sx_table_info WHERE db_id IN (SELECT db_id FROM sx_database_info WHERE system_id = '%s' and db_type= 'ORACLE')" % system_id
        rst_table_info_for_trigger = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        # crs.execute(str_MySQL_SQL)
        # rst_table_info_for_trigger = crs.fetchall()
        createDictTableInfoForTrigger()

        str_MySQL_SQL = "SELECT table_id,idx,columnname,is_exclude,disableflag FROM sx_column_info WHERE table_id IN (SELECT table_id FROM sx_table_info WHERE db_id IN (SELECT db_id FROM sx_database_info WHERE system_id = '%s' and db_type= 'ORACLE'))" % system_id
        rst_column_info_for_trigger = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        # crs.execute(str_MySQL_SQL)
        # rst_column_info_for_trigger = crs.fetchall()
        createDictColumnInfoForTrigger()

        for item in rst_database_info_for_trigger:
            str_database_info_db_id = item['DB_ID']
            str_database_info_db_type = item['DB_TYPE']
            str_database_info_db_alias = item['DB_ALIAS']
            str_database_info_db_ip = item['DB_IP']
            str_database_info_db_port = item['DB_PORT']
            str_database_info_db_username = item['DB_USERNAME']
            str_database_info_db_password = item['DB_PASSWORD']
            str_database_info_db_servicename = item['DB_SERVICENAME']
            str_database_info_db_schema = item['DB_SCHEMA']

            if (dictColumnInfoForTrigger.has_key(str_database_info_db_servicename) and dictTableInfoForTrigger.has_key(
                    str_database_info_db_servicename)):
                if (dictColumnInfoForTrigger[str_database_info_db_servicename].has_key(str_database_info_db_schema) and
                        dictTableInfoForTrigger[str_database_info_db_servicename].has_key(str_database_info_db_schema)):
                    con = cx_Oracle.connect(str_database_info_db_username, str_database_info_db_password,
                                            str_database_info_db_servicename)
                    cursor = con.cursor()
                    sql_permisstion = "grant insert any table to %s" % str_database_info_db_schema
                    cursor.execute(sql_permisstion)
                    Logging.getLog().info(sql_permisstion)
                    list_tablename_in_dicttable = dictTableInfoForTrigger[str_database_info_db_servicename][
                        str_database_info_db_schema].keys();
                    for tablename_in_dicttable in list_tablename_in_dicttable:
                        print str_database_info_db_servicename, \
                            str_database_info_db_schema, \
                            tablename_in_dicttable
                        if (dictTableInfoForTrigger[str_database_info_db_servicename][str_database_info_db_schema][
                                tablename_in_dicttable][0] == 0 and
                                dictColumnInfoForTrigger[str_database_info_db_servicename][
                                    str_database_info_db_schema].has_key(tablename_in_dicttable)):
                            list_columnname_in_dictcolumn = \
                                dictColumnInfoForTrigger[str_database_info_db_servicename][str_database_info_db_schema][
                                    tablename_in_dicttable].keys()
                            sqlCreateInserTriggerFront = "create or replace Trigger %s.T_%s_ITG before insert on %s.%s for each row declare change_content_source clob; begin change_content_source := " % (
                                str_database_info_db_schema, tablename_in_dicttable, str_database_info_db_schema,
                                tablename_in_dicttable)
                            sqlCreateInserTriggerMid = ""
                            sqlCreateInserTriggerTail = "; insert into SYSTEM.TMP_AUTOTEST_TRIGGER( username,tablename,operation,row_id, change_content ) values ( '%s','%s',0,ROWIDTOCHAR(:new.rowid),change_content_source ); end;" % (
                                str_database_info_db_schema, tablename_in_dicttable)

                            sqlCreateUpdateTriggerFront = "create or replace Trigger %s.T_%s_UTG before update on %s.%s for each row declare change_content_source clob; begin change_content_source :=null;" % (
                                str_database_info_db_schema, tablename_in_dicttable, str_database_info_db_schema,
                                tablename_in_dicttable)
                            sqlCreateUpdateTriggerIfList = ""
                            sqlCreateUpdateTriggerTail = " if( change_content_source = null )then change_content_source :=null;  else insert into SYSTEM.TMP_AUTOTEST_TRIGGER ( username,tablename,operation,row_id, change_content ) values ( '%s','%s',1,ROWIDTOCHAR(:old.rowid),change_content_source ); end if; end;" % (
                                str_database_info_db_schema, tablename_in_dicttable)

                            sqlCreateDeleteTriggerFront = "create or replace Trigger %s.T_%s_DTG before delete on %s.%s for each row declare change_content_source clob; begin change_content_source :=" % (
                                str_database_info_db_schema, tablename_in_dicttable, str_database_info_db_schema,
                                tablename_in_dicttable)
                            sqlCreateDeleteTriggerMid = ""
                            sqlCreateDeleteTriggerTail = ";insert into SYSTEM.TMP_AUTOTEST_TRIGGER( username,tablename,operation,row_id, change_content ) values ( '%s','%s',2,ROWIDTOCHAR(:old.rowid),change_content_source );    end;" % (
                                str_database_info_db_schema, tablename_in_dicttable)

                            # for strColunm_name in list_columnname_in_dictcolumn:
                            for strColunm_name in \
                                    table_column_disable_info[str_database_info_db_id][str_database_info_db_schema][
                                        tablename_in_dicttable]["column_list"].keys():
                                strColunm_name = str(strColunm_name).strip()
                                if (dictColumnInfoForTrigger[str_database_info_db_servicename][
                                        str_database_info_db_schema][tablename_in_dicttable][strColunm_name][1] == 0):
                                    if (sqlCreateInserTriggerMid == ""):
                                        sqlCreateInserTriggerMid = "TO_CHAR( :new.%s )" % (strColunm_name)
                                    else:
                                        sqlCreateInserTriggerMid = sqlCreateInserTriggerMid + "||'&amp;'||TO_CHAR( :new.%s )" % (
                                            strColunm_name)

                                    if (sqlCreateDeleteTriggerMid == ""):
                                        sqlCreateDeleteTriggerMid = "TO_CHAR( :old.%s )" % (strColunm_name)
                                    else:
                                        sqlCreateDeleteTriggerMid = sqlCreateDeleteTriggerMid + "||'&amp;'||TO_CHAR( :old.%s )" % (
                                            strColunm_name)

                            str_old_update = ""
                            str_new_update = ""
                            for strColumn_name in \
                                    table_column_disable_info[str_database_info_db_id][str_database_info_db_schema][
                                        tablename_in_dicttable]["column_list"].keys():
                                strColunm_name = str(strColunm_name).strip()
                                if str_old_update == "":
                                    str_old_update = "TO_CHAR(:old.%s)" % (strColumn_name)
                                else:
                                    str_old_update = str_old_update + "||'&amp;'||TO_CHAR(:old.%s)" % (strColumn_name)
                                if str_new_update == "":
                                    str_new_update = "TO_CHAR(:new.%s)" % (strColumn_name)
                                else:
                                    str_new_update = str_new_update + "||'&amp;'||TO_CHAR(:new.%s)" % (strColumn_name)

                            sqlCreateUpdateTriggerIfList = """change_content_source:='{"old":"'||%s||'","new":"'||%s||'"}'; """ % (
                                str_old_update, str_new_update)

                            str_Oracle_SQL = sqlCreateInserTriggerFront + sqlCreateInserTriggerMid + sqlCreateInserTriggerTail
                            # Logging.getLog().debug(str_Oracle_SQL)
                            try:
                                cursor.execute(str_Oracle_SQL)
                                str_Oracle_SQL = sqlCreateUpdateTriggerFront + sqlCreateUpdateTriggerIfList + sqlCreateUpdateTriggerTail
                                # Logging.getLog().debug(str_Oracle_SQL)
                                cursor.execute(str_Oracle_SQL)
                                str_Oracle_SQL = sqlCreateDeleteTriggerFront + sqlCreateDeleteTriggerMid + sqlCreateDeleteTriggerTail
                                # Logging.getLog().debug(str_Oracle_SQL)
                                cursor.execute(str_Oracle_SQL)
                            except Exception as e:
                                Logging.getLog().error(str_Oracle_SQL)
                                print str_Oracle_SQL
                                print e
                                pass

                    cursor.close()
                    con.close()
        gl.threadQueue.put((0, "", "createOracleTrigger"))
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        gl.threadQueue.put((-1, exc_info, "createOracleTrigger"))
        Logging.getLog().error(exc_info)
        return -1, exc_info


def dropOracleTrigger(system_id, db_id=-1):
    """
    删除Oracle 触发器
    :param system_id: 系统ID
    :param db_id: -1代表全部
    :return:
    """
    str_MySQL_SQL = ""
    try:
        if db_id == -1:
            str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info where system_id = '%s' and db_type= 'ORACLE'" % system_id
        else:
            str_MySQL_SQL = "select db_id,db_type,db_alias,db_ip,db_port,db_username,db_password,db_servicename,db_schema from sx_database_info where system_id = '%s' and db_type= 'ORACLE' and db_id = %s" % (
                system_id, db_id)
        rst_temp = cF.executeCaseSQL_DB2(str_MySQL_SQL)
        # conn = MySQLdb.connect(host="127.0.0.1",
        #                        port=3306,
        #                        db="test",
        #                        user="root",
        #                        passwd="123456",
        #                        charset='gbk')
        # crs = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        # crs.execute(str_MySQL_SQL)
        # rst_temp = crs.fetchall()
        for item in rst_temp:
            str_db_id = item['DB_ID']
            str_db_type = item['DB_TYPE']
            str_db_alias = item['DB_ALIAS']
            str_db_ip = item['DB_IP']
            str_db_port = item['DB_PORT']
            str_db_username = item['DB_USERNAME']
            str_db_password = item['DB_PASSWORD']
            str_db_servicename = item['DB_SERVICENAME']
            str_db_schema = item['DB_SCHEMA']

            con = cx_Oracle.connect(str_db_username, str_db_password, str_db_servicename)
            cursor = con.cursor()
            str_Oracle_SQL = "select trigger_name from dba_triggers where trigger_name like 'T_%%TG' AND owner = '%s'" % str_db_schema
            Logging.getLog().debug("begin to drop %s.%s trigger" % (str_db_alias, str_db_schema))
            cursor.execute(str_Oracle_SQL)
            rst_trigger_list = cursor.fetchall()
            for trigger_item in rst_trigger_list:
                str_Oracle_SQL = "Drop trigger %s.%s" % (str_db_schema, trigger_item[0])
                Logging.getLog().debug(str_Oracle_SQL)
                cursor.execute(str_Oracle_SQL)
            cursor.close()
            con.close()

        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        gl.threadQueue.put((-1, exc_info, "createOracleTrigger"))
        Logging.getLog().error(exc_info)
        return -1, exc_info


# def getFirstLetra( strData ):
#     if( len(strData) > 0 ):
#         return strData[0:1]
#     else:
#         return 'X'

def createDictTableInfoForTrigger():
    global rst_table_info_for_trigger
    global dictTableInfoForTrigger
    for item in rst_table_info_for_trigger:
        table_id = item['TABLE_ID']
        db_id = item['DB_ID']
        tablename = item['TABLENAME']
        str_schema = item['DB_SCHEMA']
        disableflag = item['DISABLEFLAG']
        str_servicename = getDatabaseServicenameByDataBaseIdForTrigger(db_id)
        listTableInfo = []
        listTableInfo.append(disableflag)
        if (dictTableInfoForTrigger.has_key(str_servicename)):
            if (dictTableInfoForTrigger[str_servicename].has_key(str_schema)):
                dictTableInfoForTrigger[str_servicename][str_schema][tablename] = listTableInfo
            else:
                dictTableInfo_schema = {}
                dictTableInfo_schema[tablename] = listTableInfo
                dictTableInfoForTrigger[str_servicename][str_schema] = dictTableInfo_schema
        else:
            dictTableInfo_schema = {}
            dictTableInfo_schema[tablename] = listTableInfo
            dictTableInfo_service = {}
            dictTableInfo_service[str_schema] = dictTableInfo_schema
            dictTableInfoForTrigger[str_servicename] = dictTableInfo_service


def createDictColumnInfoForTrigger():
    global rst_column_info_for_trigger
    global dictColumnInfoForTrigger
    for item in rst_column_info_for_trigger:
        table_id = item['TABLE_ID']
        idx = item['IDX']
        columnname = item['COLUMNNAME']
        is_exclude = item['IS_EXCLUDE']
        disableflag = item['DISABLEFLAG']
        listColumnInfo = []
        listColumnInfo.append(idx)
        listColumnInfo.append(is_exclude)
        listColumnInfo.append(disableflag)
        str_db_id, str_schema, str_tablename = getDatabaseId_Schema_TablenameByTableIdForTrigger(table_id)
        str_servicename = getDatabaseServicenameByDataBaseIdForTrigger(str_db_id)
        if (dictColumnInfoForTrigger.has_key(str_servicename)):
            if (dictColumnInfoForTrigger[str_servicename].has_key(str_schema)):
                if (dictColumnInfoForTrigger[str_servicename][str_schema].has_key(str_tablename)):
                    dictColumnInfoForTrigger[str_servicename][str_schema][str_tablename][columnname] = listColumnInfo
                else:
                    dictColumnInfo_table = {}
                    dictColumnInfo_table[columnname] = listColumnInfo
                    dictColumnInfoForTrigger[str_servicename][str_schema][str_tablename] = dictColumnInfo_table
            else:
                dictColumnInfo_table = {}
                dictColumnInfo_table[columnname] = listColumnInfo
                dictColumnInfo_schema = {}
                dictColumnInfo_schema[str_tablename] = dictColumnInfo_table
                dictColumnInfoForTrigger[str_servicename][str_schema] = dictColumnInfo_schema
        else:
            dictColumnInfo_table = {}
            dictColumnInfo_table[columnname] = listColumnInfo
            dictColumnInfo_schema = {}
            dictColumnInfo_schema[str_tablename] = dictColumnInfo_table
            dictColumnInfo_servicename = {}
            dictColumnInfo_servicename[str_schema] = dictColumnInfo_schema
            dictColumnInfoForTrigger[str_servicename] = dictColumnInfo_servicename


def getDatabaseId_Schema_TablenameByTableIdForTrigger(table_id):
    global rst_table_info_for_trigger
    for item in rst_table_info_for_trigger:
        if (table_id == item['TABLE_ID']):
            return item['DB_ID'], item['DB_SCHEMA'], item['TABLENAME']
    return -1, 'none', 'none'


def getDatabaseServicenameByDataBaseIdForTrigger(db_id):
    global rst_database_info_for_trigger
    for item in rst_database_info_for_trigger:
        if (db_id == item['DB_ID']):
            return item['DB_SERVICENAME']
    return 'none'


def create_system_table():
    ddl = """
    CREATE TABLE "SYSTEM"."TMP_AUTOTEST_TRIGGER" 
   (	"USERNAME" NVARCHAR2(12), 
	"TABLENAME" NVARCHAR2(32), 
	"OPERATION" NUMBER, 
	"ROW_ID" NVARCHAR2(128), 
	"CHANGE_CONTENT" VARCHAR2(4000)
   ) PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 NOCOMPRESS LOGGING
  STORAGE(INITIAL 65536 NEXT 1048576 MINEXTENTS 1 MAXEXTENTS 2147483645
  PCTINCREASE 0 FREELISTS 1 FREELIST GROUPS 1 BUFFER_POOL DEFAULT)
  TABLESPACE "SYSTEM" ;
    """


def CompareTwoList(left_list, right_list):
    new_left_list = []
    new_right_list = []
    result_list = []
    left_buff_list = []
    right_buff_list = []
    diff_list = []
    juage_list = []
    try:
        diff = difflib.unified_diff(left_list, right_list, "left", "right")
        for line in diff:
            result_list.append(line)

        if result_list == []:  # the same
            for i in xrange(len(left_list)):
                juage_list.append(1)
            return 0, left_list, right_list, juage_list
        for line in result_list:
            if line.startswith('---') or line.startswith('+++'):
                continue
            if line.find('@@') >= 0:
                # 暂不考虑行号问题
                continue
            if line[0] == ' ':  # the same
                # 先把之前待定的全部输入空格

                if len(new_left_list) > len(new_right_list):
                    pass
                    for i in xrange(len(new_left_list) - len(new_right_list)):
                        new_right_list.append('')
                        juage_list.append(0)
                elif len(new_left_list) < len(new_right_list):
                    for i in xrange(len(new_right_list) - len(new_left_list)):
                        new_left_list.append('')
                        juage_list.append(0)

                new_left_list.append(line[1:])
                new_right_list.append(line[1:])
                juage_list.append(1)

            elif line[0] == '-':
                new_left_list.append(line[1:])
            elif line[0] == '+':
                new_right_list.append(line[1:])

        if len(new_left_list) > len(new_right_list):
            for i in xrange(len(new_left_list) - len(new_right_list)):
                new_right_list.append('')
                juage_list.append(0)
        elif len(new_left_list) < len(new_right_list):
            for i in xrange(len(new_right_list) - len(new_left_list)):
                new_left_list.append('')
                juage_list.append(0)

        if len(new_left_list) > len(juage_list):
            for i in xrange(len(new_left_list) - len(juage_list)):
                juage_list.append(0)

        return 0, new_left_list, new_right_list, juage_list
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


if __name__ == "__main__":
    cF.readConfigFile()
    # scanOracleDB('ZHLC')
    # createOracleTrigger('ZHLC')
    a = getTableColumnInfo('', "", -1)
    # dropOracleTrigger('ZHLC',1)
    pass
