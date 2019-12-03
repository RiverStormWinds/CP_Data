# -*- coding: GBK -*-
import MySQLdb
import ibm_db
import pyodbc
import sys

reload(sys)
sys.setdefaultencoding('GBK')


def get_Dbconnection_test():
    return MySQLdb.connect(host='localhost', port=3306, user='root',
                           passwd='123456', db='zhlcauto', charset='GBK')


def getDbconnection_zhlc():
    return MySQLdb.connect(host='localhost', port=3306, user='root',
                           passwd='123456', db='zhlc', charset='GBK')


def get_row_id(col, table_name):
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    try:
        sql = "select max(%s) FROM TIMESVC.%s" % (col, table_name)
        cursor.execute(sql)
        result = cursor.fetchall()
        max_id = 0
        if result:
            max_id = result[0][0]
        return max_id
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()


def get_tbl_cases_data():
    conn2 = getDbconnection_zhlc()
    cursor = conn2.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    try:
        sql = "select * from tbl_cases"
        cursor.execute(sql)
        result = cursor.fetchall()
        result = group_by_tbl_cases_data(list(result))
        return result
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn2.close()


def group_by_tbl_cases_data(data):
    result = {}
    keys = []
    for i in data:
        child = []
        if i["groupname"] not in keys:
            keys.append(i["groupname"])
            child.append(i)
            result[i["groupname"]] = child
        else:
            child_data = result[i["groupname"]]
            child_data.append(i)
            result[i["groupname"]] = child_data

    return result


def sava_sx_cases_info():
    # conn = get_Dbconnection_test()
    # cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    try:
        del_table()
        case_data = get_tbl_cases_data()
        TREE_DIRECTORY_info = order_by_itempos_to_get_tree_directory_id()
        keys = TREE_DIRECTORY_info.keys()
        id_data = query_id_order_by_funcid()
        count = 0
        num = 0
        for i in case_data:
            if case_data[i]:
                CASES_CODE = "ZHLC000000"
                count += 1
                CASES_CODE = CASES_CODE + str(count)
                if CASES_CODE == "ZHLC00000050":
                    print "wait"
                itempos = case_data[i][0]["itempos"]
                TREE_DIRECTORY_ID, sql, args = "", "", ()
                flag = True
                if not itempos:
                    flag = False
                elif itempos in keys:
                    itempos = str(itempos.strip())
                    TREE_DIRECTORY_ID = TREE_DIRECTORY_info[itempos]
                else:
                    pass
                if not TREE_DIRECTORY_ID:
                    flag = False
                if flag:
                    args = (
                        CASES_CODE, i, "CASE_LEVEL_HIGH", '0', "ZHLC",
                        int(TREE_DIRECTORY_ID))
                    sql = "insert into TIMESVC.SX_CASES(CASES_CODE, CASE_NAME, CASE_LEVEL, IS_DELETE, SYSTEM_ID, TREE_DIRECTORY_ID) " \
                          "VALUES('%s', '%s', '%s', '%s', '%s', %s)" % args
                else:
                    args = (CASES_CODE, i, "CASE_LEVEL_HIGH", '0', "ZHLC")
                    sql = "insert into TIMESVC.SX_CASES(CASES_CODE, CASE_NAME, CASE_LEVEL, IS_DELETE, SYSTEM_ID) " \
                          "VALUES('%s', '%s', '%s', '%s', '%s')" % args
                cursor.execute(sql)
                conn.commit()
                # case_id = conn.insert_id()
                case_id = get_row_id('CASES_ID', 'SX_CASES')
                sava_sx_cases_detail(case_id, case_data[i], id_data)
                num = num + len(case_data[i])
                print num
        print num
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()


def order_by_itempos_to_get_tree_directory_id():
    conn = get_Dbconnection_test()
    cursor = conn.cursor()
    try:
        data = {}
        sql = "select itempos, TREE_DIRECTORY_ID from sx_func_tree_directory"
        cursor.execute(sql)
        for row in cursor.fetchall():
            itempos, TREE_DIRECTORY_ID = row
            child_data = {str(itempos): TREE_DIRECTORY_ID}
            data.update(child_data)
        return data
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()


def sava_sx_cases_detail_param_data(CASES_DETAIL_ID, data):
    # conn = get_Dbconnection_test()
    # cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    try:
        PARAM_DATA = data["cmdstring"].replace(",", "#").replace(":", "=")
        args = (CASES_DETAIL_ID, MySQLdb.escape_string(PARAM_DATA.replace("'", "!@#$^&*")), data["expect_ret"],
                data["account_group_id"])
        sql = "insert into TIMESVC.SX_CASES_DETAIL_PARAM_DATA(CASES_DETAIL_ID, PARAM_DATA, EXPECTED_VALUE, ACCOUNT_GROUP_ID) " \
              "VALUES(%s, '%s', '%s', %s)" % args
        cursor.execute(sql)
        conn.commit()
        # PARAM_DATA_ID = conn.insert_id()
        PARAM_DATA_ID = get_row_id('PARAM_DATA_ID', 'SX_CASES_DETAIL_PARAM_DATA')
        sql = """update TIMESVC.SX_CASES_DETAIL_PARAM_DATA set PARAM_DATA=replace(PARAM_DATA, '!@#$^&*', '''')
                    WHERE PARAM_DATA_ID=%s""" % PARAM_DATA_ID
        cursor.execute(sql)
        conn.commit()
        return PARAM_DATA_ID
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()


def query_id_order_by_funcid():
    conn = get_Dbconnection_test()
    cursor = conn.cursor()
    try:
        data = {}
        sql = "select ID, FUNCID from sx_interface_info"
        cursor.execute(sql)
        for row in cursor.fetchall():
            ID, FUNCID = row
            child_data = {str(FUNCID): ID}
            data.update(child_data)
        return data
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()


def sava_sx_cases_detail(case_id, data, id_data):
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    try:
        PARAM_DATA_IDs = []
        for i in data:
            flag = True
            id = ""
            keys = id_data.keys()
            if not i["funcid"]:
                flag = False
            elif i["funcid"] in keys:
                id = id_data[str(i["funcid"])]
            else:
                pass
            if not id:
                flag = False
            INPUT_STRING = "".join([str(j.split(":")[0]) + "=#" for j in i["cmdstring"].split(",")])
            sql = ""
            args = ()
            if flag:
                args = (
                    case_id, i["case_index"], "SPLX_T2",
                    MySQLdb.escape_string(str(INPUT_STRING).replace("'", "!@#$%^&*")),
                    MySQLdb.escape_string(str(i["pre_action"]).replace("'", "!@#$%^&*")),
                    MySQLdb.escape_string(str(i["pro_action"]).replace("'", "!@#$%^&*")), id, i['funcid'],
                    i['disableflag'])
                sql = "insert into TIMESVC.SX_CASES_DETAIL(CASES_ID, STEP, ADAPTER_TYPE, INPUT_STRING, PRE_ACTION, PRO_ACTION, PARAM_ID, FUNCID, IS_DELETE)  VALUES(%s, %s, '%s', '%s', '%s', '%s', %s, '%s', '%s')" % args
            else:

                args = (
                    case_id, int(i["case_index"]), "SPLX_T2",
                    MySQLdb.escape_string(INPUT_STRING.replace("'", "!@#$^&*")),
                    MySQLdb.escape_string(i["pre_action"].replace("'", "!@#$^&*")),
                    MySQLdb.escape_string(i["pro_action"].replace("'", "!@#$^&*")), i['funcid'], i['disableflag'])
                sql = "insert into TIMESVC.SX_CASES_DETAIL(CASES_ID, STEP, ADAPTER_TYPE, INPUT_STRING, PRE_ACTION, PRO_ACTION, FUNCID, IS_DELETE)" \
                      " VALUES(%s,  %s, '%s', '%s', '%s', '%s', '%s', '%s')" % args
            cursor.execute(sql)
            conn.commit()
            # CASES_DETAIL_ID = conn.insert_id()
            CASES_DETAIL_ID = get_row_id('CASES_DETAIL_ID', 'SX_CASES_DETAIL')
            sql = """update TIMESVC.SX_CASES_DETAIL set INPUT_STRING=replace(INPUT_STRING, '!@#$^&*', ''''), 
            PRE_ACTION=replace(PRE_ACTION, '!@#$^&*', ''''),
            PRO_ACTION=replace(PRO_ACTION, '!@#$^&*', '''')
            WHERE CASES_DETAIL_ID=%s""" % CASES_DETAIL_ID
            cursor.execute(sql)
            conn.commit()
            PARAM_DATA_ID = sava_sx_cases_detail_param_data(CASES_DETAIL_ID, i)
            PARAM_DATA_IDs.append(str(PARAM_DATA_ID))
        sava_sx_cases_param_data_info(case_id, PARAM_DATA_IDs)
    except Exception as e:
        print e
        pass
    finally:
        # conn.commit()
        cursor.close()
        conn.close()


def sava_sx_cases_param_data_info(case_id, PARAM_DATA_IDs):
    # conn = get_Dbconnection_test()
    # cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    try:
        PARAM_DATA_ID_STR = ""
        if PARAM_DATA_IDs:
            PARAM_DATA_ID_STR = ",".join(PARAM_DATA_IDs)
        args = (case_id, u"基础数据", "CASE_LEVEL_MIDDLE", PARAM_DATA_ID_STR)
        sql = "insert into TIMESVC.SX_CASES_PARAM_DATA(CASES_ID, PARAM_NAME, PRI, PARAM_DATA_ID_STR) VALUES(%s, '%s', '%s', '%s')" % args
        cursor.execute(sql)
    except Exception as e:
        raise e
    finally:
        conn.commit()
        cursor.close()
        conn.close()


def del_table():
    # conn = get_Dbconnection_test()
    # cursor = conn.cursor()
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    case_id, CASES_DETAIL_IDs = get_case_id()
    if not case_id:
        return
    table_name = ["TIMESVC.SX_CASES_PARAM_DATA", "TIMESVC.SX_CASES_DETAIL", "TIMESVC.SX_CASES",
                  "TIMESVC.SX_CASES_DETAIL_PARAM_DATA"]
    col_name = ['CASES_DETAIL_ID', 'CASES_ID']
    try:
        for i in table_name:
            col = ""
            ids = []
            if i == "TIMESVC.SX_CASES_DETAIL_PARAM_DATA":
                if not CASES_DETAIL_IDs:
                    continue
                col = col_name[0]
                ids = ",".join(CASES_DETAIL_IDs)
            else:
                col = col_name[1]
                ids = ",".join(case_id)
            sql = "delete from %s where %s in (%s)" % (i, col, ids)
            cursor.execute(sql)

    except Exception as e:
        raise e
    finally:
        conn.commit()
        cursor.close()
        conn.close()


def get_case_id():
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    sql = "select CASES_ID, CASES_CODE from TIMESVC.SX_CASES where SYSTEM_ID='ZHLC'"
    cursor.execute(sql)
    case_id = []
    for row in cursor.fetchall():
        CASES_ID, CASES_CODE = row
        case_id.append(str(CASES_ID))
    cursor.close()
    conn.close()
    CASES_DETAIL_IDs = []
    if case_id:
        CASES_DETAIL_IDs = get_case_detail_id(case_id)
    return case_id, CASES_DETAIL_IDs


def get_case_detail_id(case_id):
    type = 'DB2'
    conn = None
    if type == 'DB2':
        dbstring = "driver={IBM DB2 ODBC DRIVER};database=CSZDH;hostname=10.189.96.6;port=50000;protocol=TCPIP;uid=TIMESVC;pwd=timesvc;"
        conn = pyodbc.connect(dbstring)
    cursor = conn.cursor()
    case_id = ",".join(case_id)
    sql = "select CASES_DETAIL_ID, CASES_ID from TIMESVC.SX_CASES_DETAIL where CASES_ID in (" + case_id + ")"
    cursor.execute(sql)
    CASES_DETAIL_IDs = []
    for row in cursor.fetchall():
        CASES_DETAIL_ID, CASES_ID = row
        CASES_DETAIL_IDs.append(str(CASES_DETAIL_ID))
    cursor.close()
    conn.close()
    return CASES_DETAIL_IDs


if __name__ == '__main__':
    sava_sx_cases_info()
