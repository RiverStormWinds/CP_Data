# coding=utf-8
from xml.etree import ElementTree
import xml.dom.minidom
import xml.etree.ElementTree as ET
import threading
import os
import pyodbc


def get_sx_run_record_id(CASE_NAME, TASK_ID):
    try:
        RUN_RECORD_ID = ""
        conn, cursor = getConnected()
        sql = "select r.RUN_RECORD_ID from SX_RUN_RECORD r ,SX_CASES s where r.CASES_ID = s.CASES_ID and s.CASE_NAME = '%s' and r.TASK_ID=%s and r.RESULT in ('STATE_FAIL', 'STATE_UNTEST')" % (
            CASE_NAME, TASK_ID)
        cursor.execute(sql)
        rs = cursor.fetchall()
        if rs and len(rs) == 1:
            RUN_RECORD_ID = rs[0][0]
        return RUN_RECORD_ID
    except Exception as e:
        return ""
    finally:
        cursor.close()
        conn.close()


def getConnected():
    try:
        type = 'DB2'
        conn = None
        if type == 'DB2':
            dbstring = "driver={IBM DB2 ODBC DRIVER};database=AUTOTEST;hostname=10.181.101.151;port=50000;protocol=TCPIP;uid=autotest;pwd=1GaTjest;"
            conn = pyodbc.connect(dbstring)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        raise e


def rename_piture(log_path, TASK_ID):
    list = os.listdir(log_path)
    for i in list:
        pathname = os.path.join(log_path, i)
        if os.path.isfile(pathname):
            filename, suffix = i.split(".")
            if suffix not in ["jpg", "log"]:
                continue
            filename = filename.decode("gbk")
            pathname = pathname.decode("gbk")
            try:
                filename = int(filename)
                continue
            except Exception as e:
                pass
            RUN_RECORD_ID = get_sx_run_record_id(filename, TASK_ID)
            if RUN_RECORD_ID:
                new_path = log_path + "\\%s.%s" % (RUN_RECORD_ID, suffix)
                print pathname, new_path
                os.rename(pathname, new_path)


def update_picture_name(log_path):
    list = os.listdir(log_path)
    for i in list:
        pathname = os.path.join(log_path, i)
        if os.path.isfile(pathname):
            filename, suffix = i.split(".")
            if suffix not in ["jpg", "log"]:
                continue
                # filename = filename.decode("gbk")
                # try:
                #     filename = int(filename)
                #     continue
                # except Exception as e:
                #     pass
                # get_sx_run_record_id()
                # count += 1
                # new_path = log_path + "\\%s.%s"%(count,suffix)
                # print pathname, new_path
                # os.rename(pathname, new_path)
        else:
            rename_piture(pathname, i)


if __name__ == '__main__':
    homedir = os.getcwd()
    log_path = "%s\\Log" % homedir
    update_picture_name(log_path)
