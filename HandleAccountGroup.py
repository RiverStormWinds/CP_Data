# -*- coding:gbk -*-
import time
import commFuncs as cF
from gl import GlobalLogging as Logging


class HandleAccountGroup():
    def __init__(self, task):
        self.task = task

    def handle(self):
        ag = self.task._mqserver._redis_client.get_account_group_dict(None)
        if ag is None or len(ag) <= 0:
            return
        del_sql = "delete from sx_account_group_info where SYSTEM_ID='%s' and GROUP_ID=%s and SERVERID=%s"
        sqlSelect = "select count(*) as NUM from sx_account_group_info where SYSTEM_ID='%s' and FILELD_NAME='%s' and GROUP_ID=%s and SERVERID=%s"
        sqlInsert = "insert into sx_account_group_info(GROUP_ID, SYSTEM_ID, FILELD_NAME,  FIELD_VALUE, GROUP_DESC, SERVERID) values(?,?,?,?,?,?)"
        sqlUpdate = "update sx_account_group_info set FIELD_VALUE=? where SYSTEM_ID=? and FILELD_NAME=? and GROUP_ID=? and SERVERID=?"
        GROUP_DESC = "created automatically"
        system_id = ""
        group_id_first = 0

        try:
            for (key, value) in ag.items():
                # key: it is collection_code
                value = eval(value)
                update_list = []
                insert_list = []
                system_id = value["system_id"]
                data = value["data"]

                ###########################################集中交易###########################################
                if key == "create_account":
                    for (server_id, group_data_arr) in data.items():
                        for group_id in group_data_arr:
                            field_dict = group_data_arr[group_id]
                            for field_name in field_dict:
                                update_list.append((field_dict[field_name], system_id, field_name, group_id, server_id))
                    cF.executeCaseManySQL_DB2(sqlUpdate, update_list)
                    continue

                ###########################################清算###########################################
                # 核心
                # 获得SYSTEM_ID
                Logging.getLog().debug("SYSTEM_ID :" + str(system_id))
                ds1 = cF.executeCaseSQL(
                    "select collection_id from SX_CASES_COLLECTION where collection_code='%s' and SYSTEM_ID='%s'" % (
                        key, system_id))
                max_size_group_data_arr = 0
                for (server_id, group_data_arr) in data.items():
                    server_id = int(server_id)
                    group_id = group_id_first
                    if len(group_data_arr) > max_size_group_data_arr:
                        max_size_group_data_arr = len(group_data_arr)
                    #非锁定的账户组可以删除
                    for dt in group_data_arr:
                        # 获取锁定账户组的数据 ISLOCK = 1 表示已经锁定的账户组
                        sql_is_lock = "select count(*) as NUM from SX_ACCOUNT_GROUP_INFO where SYSTEM_ID='%s' " \
                                      "and ISLOCK = 1 and GROUP_ID=%s and SERVERID=%s" % (system_id, group_id, server_id)
                        ds = cF.executeCaseSQL(sql_is_lock)
                        num = ds[0]['NUM']
                        if num == 0:
                            # print u"非锁定的账户组!"
                            sql = del_sql % (system_id, group_id, server_id)
                            cF.executeCaseSQL(sql)
                            for field_name in dt.keys():
                                insert_list.append(
                                    (group_id, system_id, field_name, dt[field_name], GROUP_DESC, server_id))
                        else:
                            print u"锁定的账户组不能删除 不能更新!"
                        group_id += 1
                cF.executeCaseManySQL_DB2(sqlInsert, insert_list)

                # 2. update GROUP_ID to table about cases data
                if ds1:
                    sql = "select DISTINCT CASES_ID from  SX_CASES_COLLECTION_DETAIL WHERE COLLECTION_ID = %s" % (
                        ds1[0]["COLLECTION_ID"])
                    ds = cF.executeCaseSQL(sql)
                    current_record = group_id_first
                    update_list = []
                    sql = "UPDATE SX_CASES_DETAIL_PARAM_DATA SET ACCOUNT_GROUP_ID=? WHERE CASES_DETAIL_ID IN " \
                          "(SELECT CASES_DETAIL_ID FROM SX_CASES_DETAIL WHERE CASES_ID = ?)"
                    for item in ds:
                        if current_record - group_id_first < max_size_group_data_arr:
                            CASES_ID = item["CASES_ID"]
                            pdi = int(CASES_ID)
                            update_list.append((current_record, pdi))
                            current_record += 1
                    print "sql:%s, update_list:%s"%(sql, str(len(update_list)))
                    cF.executeCaseManySQL_DB2(sql, update_list)
                    if len(ds) != max_size_group_data_arr:
                        Logging.getLog().debug("len(ds) != max_size_group_data_arr")

        except Exception as e1:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
        finally:
            self.task._mqserver._redis_client.remove_account_group_dict(ag.keys())

        Logging.getLog().debug("HandleAccountGroup ok")
