# coding=utf-8
'''
接口信息迁移
'''
from xml.etree import ElementTree
import xml.dom.minidom
import xml.etree.ElementTree as ET
import threading
import MySQLdb
import pyodbc
import commFuncs as cF
SHOW_LOG = True


def get_connection_local(db_name='zhlcauto'):
    '''数据库连接信息'''
    _t = dict(host='127.0.0.1', user='root', passwd='123456', db=db_name)
    return MySQLdb.connect(host=_t["host"], user=_t["user"], passwd=_t["passwd"], \
                           db=_t["db"], connect_timeout=10, charset='utf8', init_command='SET NAMES UTF8')


# def check_sx_interface_detail_info(data):
#     """判断接口详细信息是否存在"""
#     conn = get_connection_local()
#     cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
#     args = (data["desc"])
#     sql = "select ID from sx_interface_detail_info where PARAM_DESC=%s"
#     if data["INTERFACE_ID"]:
#         sql += " AND INTERFACE_ID=" + str(data["INTERFACE_ID"]) + ""
#     cursor.execute(sql, args)
#     result = cursor.fetchall()
#     id = ""
#     if result:
#         id = int(result[0]["ID"])
#     cursor.close()
#     conn.close()
#     return id
#
#
# def update_sx_interface_detail_info(id, data):
#     """更新接口详细信息"""
#     conn = get_connection_local()
#     cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
#     sql = ""
#     args = ()
#     if data["INTERFACE_ID"]:
#         args = (
#             int(data["INTERFACE_ID"]), data["INPUT_TYPE"], data["name"], data["type"], data["desc"], data["INDEX"], id)
#         sql = "update sx_interface_detail_info set INTERFACE_ID=%s, INPUT_TYPE=%s, PARAM_NAME=%s, PARAM_TYPE=%s, PARAM_DESC=%s, PARAM_INDEX=%s  " \
#               "where ID=%s"
#     else:
#         args = (data["INPUT_TYPE"], data["name"], data["type"], data["desc"], data["INDEX"], id)
#         sql = "update sx_interface_detail_info set INPUT_TYPE=%s, PARAM_NAME=%s, PARAM_TYPE=%s, PARAM_DESC=%s, PARAM_INDEX=%s  " \
#               "where ID=%s"
#     cursor.execute(sql, args)
#
#     conn.commit()
#     cursor.close()
#     conn.close()


def sava_sx_interface_detail_info(all_data):
    '''保存接口详细信息'''
    conn = get_connection_local()
    cursor = conn.cursor()
    try:
        for i in all_data:
            # id = check_sx_interface_detail_info(i)
            # if id:
            #     update_sx_interface_detail_info(id, i)
            # else:
            sql = ""
            args = ()
            if i["INTERFACE_ID"]:
                args = (int(i["INTERFACE_ID"]), i["INPUT_TYPE"], i["name"], i["type"], i["desc"], i["INDEX"])
                sql = "insert into sx_interface_detail_info(INTERFACE_ID, INPUT_TYPE, PARAM_NAME, PARAM_TYPE, PARAM_DESC, PARAM_INDEX) VALUES(%s,%s,%s,%s,%s,%s)"
            else:
                args = (i["INPUT_TYPE"], i["name"], i["type"], i["desc"], i["INDEX"])
                sql = "insert into sx_interface_detail_info(INPUT_TYPE, PARAM_NAME, PARAM_TYPE, PARAM_DESC, PARAM_INDEX) VALUES(%s,%s,%s,%s,%s)"
            cursor.execute(sql, args)
    except Exception as e:
        raise e
    finally:
        conn.commit()
        cursor.close()
        conn.close()


def deal_sx_interface_detail_info(T2InterfacesDetailsFilePath, system_id):
    '''获取接口详细信息'''
    tree = ET.parse(T2InterfacesDetailsFilePath)
    root = tree.getroot()
    flag, data = check_whether_there_exists(root)
    all_data = []
    if flag:
        for child in root:
            funcid = child.attrib['funcid']
            id = query_id_order_by_funcid(funcid)
            flag, data = check_whether_there_exists(child)
            if flag:
                for i in data:
                    INDEX = 0
                    flag, child_data = check_whether_there_exists(i)
                    if flag:
                        for j in child_data:
                            INDEX += 1
                            # print j.tag, j.attrib
                            interfacej_data = j.attrib
                            interfacej_data["INTERFACE_ID"] = id
                            interfacej_data["INDEX"] = INDEX
                            interfacej_data["INPUT_TYPE"] = str(j.tag)
                            all_data.append(interfacej_data)
    for i in range(0, len(all_data), 1000):
        b = all_data[i:i + 1000]
        t = threading.Thread(target=sava_sx_interface_detail_info, args=(b,))
        t.start()
        t.join()


def query_id_order_by_funcid(funcid):
    '''所属funcid 在 sx_interface_info 的ID===> INTERFACE_ID'''
    conn = get_connection_local()
    cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    try:
        sql = "select ID from sx_interface_info where FUNCID=%s"
        cursor.execute(sql, funcid)
        result = cursor.fetchall()
        ID = ""
        if result:
            ID = result[0]['ID']
        return ID
    except Exception as e:
        raise e
    finally:
        cursor.close()
        conn.close()


def check_whether_there_exists(child):
    flag = False
    data = child.getchildren()
    if data:
        flag = True
    return flag, data


# def check_sx_interface_info(interfaceinfo, system_id):
#     """判断接口的信息是否存在"""
#     conn = get_connection_local()
#     cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
#     try:
#         args = (interfaceinfo["funcid"], system_id)
#         sql = "select ID from sx_interface_info where FUNCID=%s and SYSTEM_ID=%s"
#         cursor.execute(sql, args)
#         result = cursor.fetchall()
#         id = ""
#         if result:
#             id = int(result[0]["ID"])
#         return id
#     except Exception as e:
#         raise e
#     finally:
#         cursor.close()
#         conn.close()

#
# def update_sx_interface_info(interfaceinfo, id, system_id, TREE_DIRECTORY_ID):
#     """更新目录信息"""
#     conn = get_connection_local()
#     cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
#     try:
#         sql = ""
#         args = ()
#         keys = interfaceinfo.keys()
#         if 'need_log' not in keys:
#             interfaceinfo['need_log'] = 1
#         if 'timeout' in keys:
#             args = (interfaceinfo["funcid"], interfaceinfo["desc"], int(TREE_DIRECTORY_ID), system_id,
#                     interfaceinfo["timeout"], int(interfaceinfo["need_log"]), id)
#             sql = "update sx_interface_info set FUNCID=%s, FUNCID_DESC=%s, TREE_DIRECTORY_ID=%s, SYSTEM_ID=%s, TIMEOUT=%s, NEED_LOG=%s  " \
#                   "where ID=%s"
#         else:
#             args = (interfaceinfo["funcid"], interfaceinfo["desc"], int(TREE_DIRECTORY_ID), system_id,
#                     int(interfaceinfo["need_log"]), id)
#             sql = "update sx_interface_info set FUNCID=%s, FUNCID_DESC=%s, TREE_DIRECTORY_ID=%s, SYSTEM_ID=%s, NEED_LOG=%s  " \
#                   "where ID=%s"
#         cursor.execute(sql, args)
#     except Exception as e:
#         raise e
#     finally:
#         conn.commit()
#         cursor.close()
#         conn.close()


def sava_sx_interface_info(interfaceinfo, TREE_DIRECTORY_ID, system_id):
    '''保存接口信息'''
    conn = get_connection_local()
    cursor = conn.cursor()
    try:
        keys = interfaceinfo.keys()
        if "funcid" in keys:
            # id = check_sx_interface_info(interfaceinfo, system_id)
            # if id:
            #     update_sx_interface_info(interfaceinfo, id, system_id, TREE_DIRECTORY_ID)
            # else:
            sql = ""
            args = ()
            if 'need_log' not in keys:
                interfaceinfo['need_log'] = 1
            if 'timeout' in keys:
                args = (interfaceinfo["funcid"], interfaceinfo["desc"], int(TREE_DIRECTORY_ID), system_id,
                        interfaceinfo["timeout"], int(interfaceinfo["need_log"]))
                sql = "insert into sx_interface_info(FUNCID, FUNCID_DESC, TREE_DIRECTORY_ID, SYSTEM_ID, TIMEOUT, NEED_LOG) " \
                      "VALUES (%s, %s, %s, %s, %s, %s)"
            else:
                args = (interfaceinfo["funcid"], interfaceinfo["desc"], int(TREE_DIRECTORY_ID), system_id,
                        int(interfaceinfo["need_log"]))
                sql = "insert into sx_interface_info(FUNCID, FUNCID_DESC, TREE_DIRECTORY_ID, SYSTEM_ID, NEED_LOG) " \
                      "VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, args)
    except Exception as e:
        raise e
    finally:
        conn.commit()
        cursor.close()
        conn.close()


def circulation(root_data, child, data, DIRECTORY_LEVEL, root_id, system_id):
    '''循环'''
    AArry = child.getchildren()
    IS_LEAF = 0
    if AArry:
        DIRECTORY_LEVEL += 1
        INDEX_NUM = 0
        for i in AArry:
            cat_list = i.getchildren()
            if cat_list:
                IS_LEAF = 1
            root_data["IS_LEAF"] = IS_LEAF
            root_data["DIRECTORY_TYPE"] = "DIRECTORY_LEVEL_%s" % (DIRECTORY_LEVEL)
            root_data["PARENT_ID"] = root_id
            root_data["DIRECTORY_NAME"] = i.attrib["desc"]
            INDEX_NUM += 1
            root_data["INDEX_NUM"] = INDEX_NUM
            root_data["itempos"] = str(i.attrib["itempos"])
            # str(i.attrib["itempos"])[-1:]
            data.append(root_data)
            new_id = sava_interfacesfile_data(root_data)
            sava_sx_interface_info(i.attrib, new_id, system_id)
            if IS_LEAF:
                circulation(root_data, i, data, DIRECTORY_LEVEL, new_id, system_id)
            else:
                new_id = root_id
    return data


# def check_tree_info_is_not_exist(data):
#     """判断树的信息是否存在"""
#     conn = get_connection_local()
#     cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
#     try:
#         args = (data["DIRECTORY_NAME"], data["SYSTEM_ID"], data["PARENT_ID"])
#         sql = "select TREE_DIRECTORY_ID from sx_func_tree_directory where DIRECTORY_NAME=%s and SYSTEM_ID=%s and PARENT_ID=%s"
#         cursor.execute(sql, args)
#         result = cursor.fetchall()
#         id = ""
#         if result:
#             id = int(result[0]["TREE_DIRECTORY_ID"])
#         return id
#     except Exception as e:
#         raise e
#     finally:
#         cursor.close()
#         conn.close()


# def update_tree_info_is_not_exist(data):
#     """更新目录信息"""
#     conn = get_connection_local()
#     cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
#     try:
#         args = (data["DIRECTORY_TYPE"], data["IS_LEAF"], data["INDEX_NUM"], data["TREE_STATE"],
#                 data["DIRECTORY_NAME"], data["SYSTEM_ID"], data["PARENT_ID"])
#         sql = "update sx_func_tree_directory set DIRECTORY_TYPE=%s, IS_LEAF=%s, INDEX_NUM=%s, TREE_STATE=%s " \
#               "where DIRECTORY_NAME=%s and SYSTEM_ID=%s and PARENT_ID=%s"
#         cursor.execute(sql, args)
#     except Exception as e:
#         raise e
#     finally:
#         conn.commit()
#         cursor.close()
#         conn.close()


def sava_interfacesfile_data(data):
    '''报存接口目录信息'''
    # id = check_tree_info_is_not_exist(data)
    # if id:
    #     #更新数据
    #     update_tree_info_is_not_exist(data)
    #     return id
    conn = get_connection_local()
    cursor = conn.cursor()
    try:
        args = (data["DIRECTORY_NAME"], data["DIRECTORY_TYPE"], data["PARENT_ID"], data["IS_LEAF"],
                data["INDEX_NUM"], data["TREE_STATE"], data["SYSTEM_ID"], data["itempos"])
        sql = "insert into sx_func_tree_directory(DIRECTORY_NAME,DIRECTORY_TYPE, PARENT_ID, IS_LEAF, INDEX_NUM, TREE_STATE," \
              " SYSTEM_ID, itempos) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, args)
        id = int(conn.insert_id())
        return id
    except Exception as e:
        raise e
    finally:
        conn.commit()
        cursor.close()
        conn.close()


def delete_table(table_name, system_id):
    conn = get_connection_local()
    cursor = conn.cursor()
    # flag = False
    # if table_name == "sx_interface_detail_info":
    #     flag = True
    #     ids = query_sx_interface_info_id(system_id)
    #     if ids:
    #         ids_str = ",".join(ids)
    #         sql = " delete from sx_interface_detail_info where INTERFACE_ID in ("+ids_str+")"
    #         cursor.execute(sql)
    # if flag == False:
    sql = "delete from %s"%table_name
    if system_id:
        system_id = "'" + system_id + "'"
        sql += " WHERE system_id=%s"%system_id
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

def query_sx_interface_info_id(system_id):
    ids=[]
    conn = get_connection_local()
    cursor = conn.cursor()
    try:
        sql = "select ID, SYSTEM_ID from sx_interface_info where SYSTEM_ID=%s"
        cursor.execute(sql, system_id)
        for row in cursor.fetchall():
            ID, SYSTEM_ID = row
            ids.append(str(ID))
    except Exception as e:
        print e
    finally:
        cursor.close()
        conn.close()

    return ids

def import_t2_interface_files(T2InterfacesFilePath, T2InterfacesDetailsFilePath, system_id):
    '''导入接口信息xml的文件'''
    err_no = 0
    err_message = " "
    try:
        #delete_table("sx_interface_detail_info", "")
        #delete_table("sx_func_tree_directory", system_id)
        #delete_table("sx_interface_info", system_id)
        
        sql = "delete from sx_func_tree_directory where system_id ='%s'" %system_id
        cF.executeCaseSQL(sql)
        
        sql = "DELETE FROM SX_INTERFACE_DETAIL_INFO WHERE interface_id IN (SELECT id FROM sx_interface_info WHERE system_id='%s') " %system_id
        cF.executeCaseSQL(sql)
        
        sql = "delete from sx_interface_info where system_id ='%s'" %system_id
        cF.executeCaseSQL(sql)
        
        tree = ET.parse(T2InterfacesFilePath)
        root = tree.getroot()
        root_cat = root.getchildren()
        root_data = {"INDEX_NUM": 0, "IS_LEAF": 0, "TREE_STATE": 1, "SYSTEM_ID": "ZHLC",
                     "PARENT_ID": 0, "DIRECTORY_NAME": u"根目录", "DIRECTORY_TYPE": "DIRECTORY_LEVEL_0", "itempos":"0"}
        data = []
        DIRECTORY_LEVEL = 0
        if root_cat:
            IS_LEAF = 1
            root_data['IS_LEAF'] = IS_LEAF
            root_id = sava_interfacesfile_data(root_data)
            data.append(root_data)
            DIRECTORY_LEVEL += 1
            for child in root:
                cat_list = child.getchildren()
                if not cat_list:
                    IS_LEAF = 0
                root_data["IS_LEAF"] = IS_LEAF
                root_data["DIRECTORY_TYPE"] = "DIRECTORY_LEVEL_%s" % (DIRECTORY_LEVEL)
                root_data["PARENT_ID"] = root_id
                root_data["DIRECTORY_NAME"] = child.attrib["desc"]
                root_data["INDEX_NUM"] = str(child.attrib["itempos"])[-1:]
                root_data["itempos"] = str(child.attrib["itempos"])
                data.append(root_data)
                new_id = sava_interfacesfile_data(root_data)
                sava_sx_interface_info(child.attrib, new_id, system_id)
                if IS_LEAF:
                    data = circulation(root_data, child, data, DIRECTORY_LEVEL, new_id, system_id)
                new_id = root_id
        deal_sx_interface_detail_info(T2InterfacesDetailsFilePath, system_id)
    except Exception as e:
        err_no = 1
        err_message = str(e)
        raise e
    return (err_no, err_message)


if __name__ == '__main__':
    cF.readConfigFile()
    import os
    homedir = os.getcwd()
    system_id = "ZHLC"
    T2InterfacesFilePath = r"%s\T2Interfaces.xml"%(homedir)
    T2InterfacesDetailsFilePath = r"%s\T2InterfaceDetails.xml"%(homedir)
    err_no, err_message = import_t2_interface_files(T2InterfacesFilePath, T2InterfacesDetailsFilePath, system_id)
    print err_no, err_message
