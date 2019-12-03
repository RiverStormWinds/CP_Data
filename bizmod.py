# -*- coding:gbk -*-
import struct
import itertools
import decimal
import collections
import threading
import wx
import MySQLdb
import commFuncs_kcbp as cF_kcbp
import urllib, urllib2
import GlobalDict
import MQClient
import commFuncs as cF
import time
import random
import hashlib
from lxml import etree
from xml.dom import minidom
import gl
import subprocess
import json
from gl import GlobalLogging as Logging

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
# import updateT2InterfaceDetails
import os, sys, inspect
import xlrd
import random
import string
from KCBPCLIAdapter import KCBPAdapter
import datetime
from datetime import date
from datetime import timedelta
from xmlrpclib import ServerProxy
import os
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy
import datetime
from datetime import date
from datetime import timedelta
import re
from collections import OrderedDict
from decimal import *
import collections
import sys
import glob
import os
import xml.dom.minidom
import zhInit


def save_param(param_info, dataset):
    try:
        values = []
        if gl.g_case_adapter_type == 'SPLX_HUARUI':
            try:
                param_info_list = param_info.split(",")
                for param_info in param_info_list:
                    params = param_info.replace(']', '').split('[')
                    field = params[0]
                    list_index = params[1]
                    list_index = int(list_index)
                    value_index = params[2]
                    value_index = int(value_index) - 1
                    value = dataset[int(list_index)][int(value_index)]
                    if isinstance(value, (str, unicode)):
                        value = value.replace(',', '&comma&')
                    if len(params) == 4 and isinstance(value, dict):
                        key = params[3]
                        value = value[key]
                    if len(params) > 3 and isinstance(value, list):
                        parse_field_data = params[3:]
                        field_data = []
                        for i in parse_field_data:
                            try:
                                field_data.append(int(i) - 1)
                            except Exception as e:
                                i = str(i).replace("'", "").replace('"', '')
                                field_data.append(i)
                        if len(field_data) == 2:
                            value = value[field_data[0]][field_data[1]]
                        if len(field_data) == 3:
                            value = value[field_data[0]][field_data[1]][field_data[2]]
                        if len(field_data) == 4:
                            value = value[field_data[0]][field_data[1]][field_data[2]][field_data[3]]
                    Logging.getLog().debug(str(value))
                    values.append(value)
                return 0, tuple(values)
            except IndexError as e:
                errmsg = "dataset IndexError"
                Logging.getLog().debug("dataset IndexError")
                return -1, errmsg
        else:
            Logging.getLog().debug(str(dataset))
            param_info_list = param_info.split(",")
            if "[" and "]" not in param_info:
                for param_info in param_info_list:
                    value = param_info
                    values.append(value)
            else:
                for param_info in param_info_list:
                    split_num = 0
                    if "|" in param_info:
                        param_info, split_num = param_info.split("|")
                        split_num = int(split_num.strip())
                    value = param_info.strip()
                    value = value.replace(' ', '')  # 去除所有空格
                    row, col = value[1:-1].split('][')
                    row = int(row) + 1  # 数据集中第0行是字段名，所以需要从第1行开始
                    col = int(col)
                    try:
                        if isinstance(dataset[int(row)][int(col)], float):
                            value = "%.2f" % dataset[int(row)][int(col)]
                        else:
                            if split_num:
                                value = dataset[int(row)][int(col)].replace(',', '&comma&')[:split_num]
                            value = dataset[int(row)][int(col)].replace(',', '&comma&')
                        values.append(value)
                    except IndexError as e:
                        if gl.g_case_adapter_type in ["SPLX_UFX"]:
                            return 0, [0]
                        errmsg = "dataset IndexError"
                        Logging.getLog().debug("dataset IndexError")
                        return -1, errmsg
        Logging.getLog().debug("save_param cbs: %s" % values)
        return 0, values
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def save_in_param(param_list_str, funcid, cmdstring):
    """  new:  cif_account = save_in_param([cif_account])
    """
    try:
        param_list = param_list_str.split(",")
        ret, column_dict = cF.generate_cmd_column_dict(funcid, cmdstring)
        if ret != 0:
            return -1, column_dict  # 如果出错，直接返回错误信息
        values = []
        for value in param_list:
            value = value.strip()
            value = value.replace(' ', '')  # 去除所有空格
            value = value[1:-1]
            values.append(column_dict[value])
        return 0, tuple(values)
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def check_regular_expression(params):
    try:
        regular_expression, value = params.split(",")
        flag = re.search(regular_expression, value)
        if flag:
            return 0, "True"
        else:
            return -1, "False"
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def check_value(params):
    try:
        regular_expression, value = params.split(",")
        regular_expression = regular_expression.strip()
        value = value.strip()
        if regular_expression == value:
            return 0, "True"
        else:
            return -1, "False"
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def check_expression(expression):
    try:
        index = expression.find(",")
        expression = expression[index + 1:]
        flag = eval(expression)
        if flag:
            return 0, "True"
        else:
            return -1, "False"
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def get_value(): pass


def mobile_data_by_normalOfTable_to_dormancyOfTable_pre(param_info):
    try:
        client_id, gt_other_type = param_info.split(",")
        client_id = str(client_id.strip())
        gt_other_type = str(gt_other_type.strip())
        Logging.getLog().debug("检测休眠表是否有该客户的数据, 若无,将从正常表中取数据放入休眠表")
        cF.mobile_data(client_id, gt_other_type)
        Logging.getLog().debug("数据已成功转移休眠表--%s" % client_id)
        return 0, ""
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info)


def mobile_data_by_normalOfTable_to_dormancyOfTable_pro(param_info):
    try:
        client_id, gt_other_type = param_info.split(",")
        client_id = str(client_id.strip())
        gt_other_type = str(gt_other_type.strip())
        Logging.getLog().debug("检测休眠表是否有该客户的数据, 若无,将从正常表中取数据放入休眠表")
        cF.mobile_data_oracle_sqlserver(client_id, gt_other_type)
        Logging.getLog().debug("数据已成功转移休眠表--%s" % client_id)
        return 0, ""
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info)


def exec_sql(param_info):
    try:
        zero_flag = False
        zero_field = ""
        if "zero" in param_info:
            param_info = param_info.replace("zero", "").strip()
            zero_flag = True
        flag = False
        field = ""
        sql = param_info[:param_info.rfind(",")].strip()

        # fixme 兼容max的问题  如果select 当中不包含as自动添加
        select_flag = False
        index1 = 0
        index2 = 0
        if "SELECT" in sql and "FROM" in sql:
            index1 = sql.find("FROM")
            index2 = sql.find("SELECT")
            select_flag = True
        elif "SELECT" in sql and "from" in sql:
            index1 = sql.find("from")
            index2 = sql.find("SELECT")
            select_flag = True
        elif "select" in sql and "FROM" in sql:
            index1 = sql.find("FROM")
            index2 = sql.find("select")
            select_flag = True
        elif "select" in sql and "from" in sql:
            index1 = sql.find("from")
            index2 = sql.find("select")
            select_flag = True
        else:
            pass

        # if "SELECT" in sql.upper() and "FROM" in sql.upper() and 'MAX(' in sql.upper() and 'AS' not in sql.upper():
        #     return -1, ("please check the sql")

        if select_flag == True:
            str_field = ""
            field = sql[index2 + 6:index1].strip()
            if "as" not in field.lower():
                if field.count("(") == 1:
                    str_field = field.split("(")[1].replace(")", "").strip()
                    max_field_lsit = [str(i).strip().lower() for i in str_field.split(" ") if i != ""]
                    if len(max_field_lsit) == 2 and max_field_lsit[0] == max_field_lsit[1]:
                        pass
                    elif len(max_field_lsit) == 1:
                        sql = sql.replace(field, "%s as %s" % (field, str_field))
                elif field.count("(") == 2 and field.count("))") == 1:
                    str_field = field.split("(")[2].replace("))", "").strip()
                    max_field_lsit = [str(i).strip().lower() for i in str_field.split(" ") if i != ""]
                    if len(max_field_lsit) == 2 and max_field_lsit[0] == max_field_lsit[1]:
                        pass
                    elif len(max_field_lsit) == 1:
                        sql = sql.replace(field, "%s as %s" % (field, str_field))


        application_type = param_info[param_info.rfind(",") + 1:].strip()
        ret, result = 0, ""
        traversalDir_XMLFile(gl.current_system_id)
        server_id = cF.get_core(application_type)
        if server_id != -1:
            Logging.getLog().info("exe_sql executeRunSQL:%s, server_id:%s------cbs" % (sql, server_id))
            result = cF.executeRunSQL(sql, server_id)
            if result == -1:
                return -1, ("")

        else:
            Logging.getLog().info(
                "exe_sql executeRunSQL_oracle:%s, application_type:%s------cbs" % (sql, application_type))
            ret, result = cF.executeRunSQL_oracle(sql, application_type)
            if ret == -1:
                return -1, ("")
        if "select * into" in sql.lower():
            return ret, ("",)
        if gl.o32_for_flag == True:
            if result:
                all_args = []
                for i in result:
                    all_args.append(i.values()[0])
                return ret, (all_args,)
            else:
                return ret, ("",)
        # # fixme 兼容max的问题
        # if "SELECT" in sql.upper() and "FROM" in sql.upper() and 'MAX(' in sql.upper():
        #     sql1 = sql.upper()
        #     index1 = sql1.find("FROM")
        #     index2 = sql1.find("SELECT")
        #     field = sql1[index2 + 6:index1].strip()
        #     if "as" in field.lower():
        #         field = field.lower().split("as")[1].strip()
        #     else:
        #         field = field.lower().replace("max(", "").replace(")", "")
        #     flag = True
        if not result and zero_flag == True:
            result = []
            zero_dict = {str("zero_field"): "0"}
            result.append(zero_dict)
            zero_field = "0"
        if gl.check_data and not result:
            #需要校验的数据，如果查询结果为空，则此条sql验证失败
            return 0, ("",)
        if gl.check_data and result:
            return_list = []
            for func_name in gl.check_data:
                result_func_json = {"type": "", "express": "", "real_express": "", "pass_flag": ""}
                param = gl.check_data[func_name]
                param_list = param.split(",")
                parameterize_list = []
                for p in param_list:
                    if p.count("@") >= 2 and "dbtable" in p.lower():
                        index1 = p.find('@')
                        index2 = p.rfind('@')
                        variable = p[index1:index2 + 1]
                        variable1 = variable.replace("@", "").replace("]", "")
                        params = variable1.split("[")
                        line = int(params[1]) - 1
                        the_first_few_filed = params[2].replace("'", "").strip()

                        the_first_few_filed = the_first_few_filed.upper()
                        if zero_field == "0" and zero_flag == True:
                            result = [{the_first_few_filed: zero_field}]
                        value = ""
                        # if flag:
                        #     the_first_few_filed = field
                        if "*" in the_first_few_filed:
                            the_first_few_filed = the_first_few_filed.split("*")[0]
                        elif "+" in the_first_few_filed:
                            the_first_few_filed = the_first_few_filed.split("+")[0]
                        elif "-" in the_first_few_filed:
                            the_first_few_filed = the_first_few_filed.split("-")[0]
                        elif "\\" in the_first_few_filed:
                            the_first_few_filed = the_first_few_filed.split("\\")[0]
                        Logging.getLog().debug("the_first_few_filed : %s" % the_first_few_filed)
                        Logging.getLog().debug("result : %s" % str(result))

                        try:
                            if isinstance(result[line][str(the_first_few_filed)], int):
                                value = result[line][str(the_first_few_filed)]
                            elif isinstance(result[line][str(the_first_few_filed)], float):
                                value = result[line][str(the_first_few_filed)]
                            elif isinstance(result[line][str(the_first_few_filed)], long):
                                value = int(result[line][str(the_first_few_filed)])
                            elif isinstance(result[line][str(the_first_few_filed)], Decimal):
                                value = float(result[line][str(the_first_few_filed)])
                            else:
                                value = result[line][str(the_first_few_filed)]
                        except Exception as e:
                            the_first_few_filed = the_first_few_filed.lower()
                            if isinstance(result[line][str(the_first_few_filed)], int):
                                value = result[line][str(the_first_few_filed)]
                            elif isinstance(result[line][str(the_first_few_filed)], float):
                                value = result[line][str(the_first_few_filed)]
                            elif isinstance(result[line][str(the_first_few_filed)], long):
                                value = int(result[line][str(the_first_few_filed)])
                            elif isinstance(result[line][str(the_first_few_filed)], Decimal):
                                value = float(result[line][str(the_first_few_filed)])
                            else:
                                value = result[line][str(the_first_few_filed)]
                        p = p.replace(variable, str(value))
                        parameterize_list.append(p)
                    else:
                        parameterize_list.append(p)
                parameterize = ",".join(parameterize_list)
                if func_name == 'get_value':
                    return ret, tuple(parameterize_list)
                # param_info = cF.GroupParameterReplace(parameterize, group_dict)
                print "func_name:%s, parameterize:%s" % (func_name, str(parameterize))
                ret, result = eval(func_name)(parameterize)  # check_expression, parameterize:7,7==8
                if ret == -1:
                    return ret, (
                    "param_info:%s,func_name:%s,parameterize:%s execute error" % (param_info, func_name, parameterize))
                result_func_json["type"] = func_name
                result_func_json["express"] = param
                result_func_json["real_express"] = parameterize
                result_func_json["pass_flag"] = ret
                return_list.append(result_func_json)
            num_ = len(gl.return_check_data) + 1
            gl.return_check_data.update({str(num_) + str(sql): return_list})
            return 0, ("",)
        else:
            if not result:
                return ret, ("",)
            return ret, result
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def random_str(random_data):
    try:
        random_name, num = random_data.split(",")
        print random_name, num
        flag = False
        if not num:
            return
        elif 'int' in num:
            num = num.replace('int', "").replace('(', "").replace(')', "").strip()
            num = int(num)
            flag = True
        else:
            num = int(num)
        random_str = ""
        random_list = []
        # 随机生成中文
        ch_num = num
        char_num = num
        int_num = num
        # if ch_num:
        #     for i in range(0, int(ch_num)):
        #         random_list.append(unichr(random.randint(0x4e00, 0x9fa5)))
        # 随机生成字母
        if flag == False:
            if char_num:
                for j in range(0, int(char_num)):
                    char = random.choice(string.letters)
                    random_list.append(char)
        # 随机生成数字
        if int_num:
            for k in range(0, int(int_num)):
                num = random.randint(0, 9)
                random_list.append(str(num))
        if random_list:
            random.shuffle(random_list)
            random_list = random_list[:int_num]
            Logging.getLog().info(str(random_list))
            for i in random_list:
                random_str += i
            Logging.getLog().info(str(random_str))
        gl.random_args = {str(random_name): str(random_str)}
        return 0, ""
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def strncat(dst, src, n):
    dst += src[0:n]
    return dst


def memcpy(dst, src, n):
    dst = src[0:n]
    return dst


def sscanf(le, tmplen):
    tmplen = int(le, 16)
    return tmplen


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


# 调用sqlserver数据库方法
def change_db(sql, servertype):
    core = cF.get_core(servertype)
    ret, conn = cF.ConnectToRunDB(core)
    crs = conn.cursor()
    ds = []
    try:
        try:
            sql = sql.decode("gbk")
        except Exception as e:
            try:
                sql = sql.decode("utf-8")
            except Exception as e:
                pass
        r = crs.execute(sql)
        if sql.lower().__contains__("restore"):
            if r != 0:
                for i in r.fetchall():
                    ds.append(i)
                crs.close()
                conn.close()
                if len(ds) == 0:
                    return 0, []
                else:
                    return 0, ds
        if sql.lower().__contains__("select") and not sql.lower().__contains__("insert") and \
                not sql.lower().__contains__("update") and not sql.lower().__contains__("delete"):
            if r != 0:
                for i in r.fetchall():
                    ds.append(i)
                crs.close()
                conn.close()
                if len(ds) == 0:
                    return 0, []
                else:
                    return 0, ds
        crs.close()
        conn.commit()
        conn.close()
        return 0, r

    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        crs.close()
        conn.rollback()
        conn.close()
        return -1, exc_info


# 调用oracle数据库方法
def change_oracle_on_the_business(sql, user=''):
    if user == '':
        user = sql.split('.')[0].split(' ')[-1].upper()
    core = ''
    for server in gl.g_connectOracleSetting.keys():
        if user in gl.g_connectOracleSetting[server]["UserList"].split(','):
            core = server
            break;
    if core == '':
        # Logging.getLog().critical("sql传入用户名,在配置文件内没有")
        return -1, "sql传入用户名%s,在配置文件内不存在" % (user)
    ds = []
    conn = cF.ConnectOracleDB(core)
    if conn == -1:
        return -1, ""

    try:
        cursor = conn.cursor()
        r = cursor.execute(sql)
        cursor.close()
        conn.commit()
        conn.close()
        return 0, r
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        cursor.close()
        conn.rollback()
        conn.close()
        return -1, exc_info


# 调用oracle数据库方法
def change_oracle(sql, user=''):
    conn, cursor = "", ""
    try:
        if user == '':
            user = sql.split('.')[0].split(' ')[-1].upper()
        core = ''
        for server in gl.g_connectOracleSetting.keys():
            if user == gl.g_connectOracleSetting[server]["servertype"]:
                core = server
                break;
        if core == '':
            # Logging.getLog().critical("sql传入用户名,在配置文件内没有")
            return -1, "sql传入用户名%s,在配置文件内不存在" % (user)
        ds = []
        Logging.getLog().info(u"cbs---core %s" % core)
        conn = cF.ConnectOracleDB(core)
        if conn == -1:
            return -1, ""

        cursor = conn.cursor()
        # sql = sql.replace('//', '').replace('\\', '')
        r = cursor.execute(sql)
        # print r
        if sql.lower().__contains__("select"):
            if r != 0:
                for i in r.fetchall():
                    ds.append(i)
        cursor.close()
        conn.commit()
        conn.close()
        if sql.lower().__contains__("select"):
            Logging.getLog().critical(u"cbs---查询到数据 %s" % ds)
            return 0, ds
        else:
            return 0, r
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        if conn or cursor:
            cursor.close()
            conn.rollback()
            conn.close()
        return -1, exc_info


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
        return -1, (exc_info,)


def get_fundid(param):
    busin_account = param
    # 去除前面两位03,表示证券 和4位branch_no
    busin_account = busin_account[6:]
    # 去除填充的0，直到遇到第一个非零字符
    try:
        for i in xrange(len(busin_account)):
            if busin_account[i] != '0':
                break;
        fundid = busin_account[i:]
        return 0, (fundid,)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


def get_account_content(param):
    client_id = param
    # 去除前面两位03,表示证券
    client_id = client_id[2:]

    # 去除填充的0，直到遇到第一个非零字符
    try:
        l = 0
        for i in xrange(len(client_id)):
            if client_id[i] != '0':
                l = i
                break;
        account_content = client_id[l:]
        return 0, (account_content,)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


# 10602706(沪港通权限开通)
# 集中交易run..secuid表regflag=1
def change_secuid_regflag(param):
    custid = param
    sql = 'update run..secuid set regflag = 1 where custid=%s and market =1;' % (custid)
    # print sql
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 10602301(基金首次开户)后执行
def change_oftaacc_status(param):
    fund_company, custid = param.split(',')
    sql = 'update run..oftaacc set status = 0 where tacode = %s and custid = %s;' % (fund_company, custid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 10602311(基金外围定投开户)
# 修改风险承受级别
def change_custotherinfo_remark(param):
    custid = param
    sql = "update run..custotherinfo set remark ='68|1|20150625' where custid=%s;" % (custid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 10602312(基金外围定投销户)根据开户custid,fund_company获得sendsn
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


# 签署全局的风险揭示书(10602313)--联合开户时默认已签署，需要先删除run..ofrisksign表数据
def del_ofrisksign(param):
    custid, orgid = param.split(',')
    sql = "delete from run..ofrisksign where custid =%s and orgid=%s;" % (custid, orgid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 新退整买入权限设置(10602810)---开通退市板块买入权限，个人客户总资产需达到50万
def change_fundasset_fundbal(param):
    custid, orgid = param.split(',')
    sql = "update run..fundasset set fundlastbal=500000000.00,fundbal=500000000.00,fundavl=500000000.00 where custid =%s and orgid=%s;" % (
        custid, orgid)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


def demo_action(param):
    # 这个函数演示 action 写法，这个action 输入为3个参数，返回也是三个参数
    in1, in2, in3 = param.split(',')
    return 0, ('1', '2', '3')


# 按帐号市场查询stock_account
def get_gtja_iwmbusinsecuflow_stock_account(param):
    try:
        cif_account, exchange_type = param.split(',')
        sql = "select stock_account from HS_ACCT.gtja_iwmbusinsecuflow where cif_account='%s' and exchange_type='%s'" % (
            cif_account, exchange_type)
        # print sql
        ret, r = change_oracle(sql)
        if ret < 0:
            return ret, (r,)
        print sql, r
        sendsn = ','.join(r[0])
        # print sendsn
        return 0, (sendsn,)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        # return -1, ("%s" % (exc_info),)
        return -1, (u"原语执行失败",)


# 10602706(沪港通权限开通)
# 指定状态：综合理财服务的hs_acct.stockholder表regflag=1
def change_stockholder_regflag(param):
    client_id, stock_account = param.split(',')
    sql = "update hs_acct.stockholder set regflag = '1' where client_id='%s' and stock_account='%s'" % (
        client_id, stock_account)
    ret, r = change_oracle(sql)
    return ret, ("",)


# 适当性管理答卷提交(10201013)
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
#    pass
# 查询gtja_iwmbusinsecuflow表init_date、serial_no
def get_gtja_iwmbusinsecuflow_serial_no(param):
    cif_account = param
    sql = "select init_date,serial_no from hs_acct.gtja_iwmbusinsecuflow  where cif_account='%s' and business_flag in (1189,1104) order by serial_no " % (
        cif_account)
    ret, r = change_oracle(sql)
    return 0, (r[0][0], r[0][1], r[1][0], r[1][1], r[2][0], r[2][1])


def auto_zd(param):
    cif_account = param
    sql = "select init_date,serial_no from hs_acct.gtja_iwmbusinsecuflow  where cif_account='%s' and business_flag in (1189,1104) order by serial_no " % (
        cif_account)
    ret, r = change_oracle(sql)
    if len(r) == 0:
        return -1, u'在hs_acct.gtja_iwmbusinsecuflow表，没有查到%s的帐号信息。请检查环境！' % (cif_account)
    try:
        for i in range(3):
            if i == 0:
                cmd = AutoTask(cif_account, r[0][0], r[0][1])
            if i == 1:
                if cmd == '2':
                    cmd = AutoTask(cif_account, r[1][0], r[1][1])
                else:
                    break
            if i == 2:
                if cmd == '2':
                    cmd = AutoTask(cif_account, r[2][0], r[2][1])
                    if cmd == '2':
                        return 0, ''
                else:
                    break
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, ex


def AutoTask(cif_account, init_date, serial_no):
    try:
        n = 0;
        init_date = str(init_date)
        serial_no = str(serial_no)
        ret, r = executeAutoTask(init_date, serial_no)
        if ret != 0:
            Logging.getLog().critical(u"中登任务执行失败")
            return '3'
        while 1:
            sql = "select business_status from hs_acct.gtja_iwmbusinsecuflow a where cif_account='%s' and init_date='%s'  and serial_no='%s'" % (
                cif_account, init_date, serial_no)
            print sql
            ret, r = change_oracle(sql)
            if n == 15:
                Logging.getLog().critical(u"执行15遍超时......")
                return 0
            if r[0][0] == '1':
                n += 1
                time.sleep(2)
                ret, r = executeAutoTask(init_date, serial_no)
                if ret != 0:
                    Logging.getLog().critical(u"中登任务执行失败")
                    return '3'
                continue
            if r[0][0] == '2':
                n = 0
                Logging.getLog().critical(u"中登任务执行成功")
                return '2'
            if r[0][0] == '3':
                Logging.getLog().critical(u"中登任务执行失败")
                return '3'
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        print exc_info
        Logging.getLog().critical(exc_info)
        return '3'


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


# 转换用户登录token
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


# 身份证和手机号MD5转换
def ConvertMD5(param):
    id_no, mobile_tel = param.split(',')
    str = id_no + mobile_tel
    m = hashlib.md5()
    m.update(str)
    psw = m.hexdigest()
    md = psw.upper()
    return 0, (md,)


##获取当前日期
def get_nowdate(param):
    NOW_DATE = time.strftime("%Y%m%d")
    return 0, (NOW_DATE,)


# 基金赎回(10602305)
def del_ofelectcontract(param):
    orgid, fundid, tacode, ofcode = param.split(',')
    fundid = int(fundid[6:])
    sql = "delete run..ofelectcontract where orgid='%s' and fundid=%s and tacode=%s and ofcode='%s'" % (
        orgid, fundid, tacode, ofcode)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 替换全局参数
def replace_parameter(param, num):
    try:
        new_param = {}
        if param:
            for key in param:
                # if sElem.attrib["id"] == '4' or sElem.attrib["id"] == '11' or sElem.attrib["id"] == '12':
                if param[key] == None or param[key] == 'None':
                    new_param[key] = ""

                else:
                    new_param[key] = param[key]
                    # print elem.tag,' :     ',elem.text
                    # elem.text = u'%s'%param[elem.tag]

        gl.g_create_account_info.update({str(num): new_param})
        return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


# 初始化持仓
# def RunInitScript(param):
#    servertype = gl.g_connectSqlServerSetting[param["serverid"]]["servertype"]

#    init_script_file="initialise.sql"
#    dict={}
#    f = open(init_script_file, 'r')
#    lines = f.readlines()

#    srt = "select seat,market from run..orgseat where orgid='%s' and market in ('1','2')"%(param['orgid'])
#    Logging.getLog().debug(srt)
#    ret,r=change_db(srt,servertype)
#    param["sh_seat"] = r[0][0]
#    param["sz_seat"] = r[1][0]

#    for j,line in enumerate(lines):
#        line = line.strip()
#        Logging.getLog().debug(line)

#        if line.startswith('--'):
#            continue
#        if len(line) == 0:
#            continue

#        sql=str(cF.GroupParameterReplace(line,param))
#        Logging.getLog().debug(sql)

#        ret,r=change_db(sql,servertype)
# 初始化持仓--信用、融资融券
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

        # 普通委托基金起息日修改和价格获得


def change_valuedate(stkcode):
    r = NOW_DATE = time.strftime("%Y%m%d")
    sql1 = "update run..stktrd set upddate='%s',intrdate='%s' where stkcode='%s'" % (str(r), str(r), stkcode)
    ret, r = change_db(sql1, 'p')
    sql2 = "select fixprice from run..stktrd where stkcode ='%s'" % (stkcode)
    ret, r = change_db(sql2, 'p')
    fixprice = str(r[0][0])
    return ret, (fixprice,)


def sqlserver_Database(sql):
    """
    在指定类型的SQL Server数据库上执行一条SQL语句
    """
    try:
        servertype = sql[-1]
        sql1 = sql[0:len(sql) - 2]
        Logging.getLog().debug(sql1)

        flag = False
        if "zero" in sql1:
            sql1 = sql1.replace("zero", "").strip()
            flag = True

        ret, r = change_db(sql1, servertype)

        if flag and not r:
            return 0, ("0",)

        if sql.lower().__contains__("select") and sql.lower().__contains__("insert"):
            return ret, r
        elif sql.lower().__contains__("select") and sql.lower().__contains__("update"):
            return ret, r
        elif sql.lower().__contains__("select") and sql.lower().__contains__("delete"):
            return ret, r
        else:
            if sql1.lower().__contains__("select"):
                fixprice = str(r[0][0])
                return ret, (fixprice,)
            else:
                return ret, r
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def oracle_Database_on_the_business(sql, user):
    try:
        Logging.getLog().debug(sql)
        ret, r = change_oracle_on_the_business(sql, user.upper())
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def expected_value(param):
    try:
        # param = sql，timeout, times, 判断值, 数据库类型, 用户
        sql, timeout, times, expext_value, type, user = param.split(",")
        sql_type = ""
        if type.strip() == "oracle":
            sql_type = "oracle_Database"
        if type.strip() == "sqlserver":
            sql_type = "sqlserver_Database"
        if sql_type == "":
            return -1, "数据库类型填写有误 %s" % type
        timeout = timeout.strip()
        times = times.strip()
        user = user.strip()
        _param = sql + "," + user
        expext_value = expext_value.strip()
        now_time = int(time.time())
        for i in range(0, int(times)):
            if int(time.time()) - now_time >= int(timeout):
                Logging.getLog().debug("timeout")
                return -1, "timeout"
            ret, value = eval("%s" % sql_type)(_param)
            if ret == 0 and value:
                result = value[0]
                r = str(result) + str(expext_value)
                if eval(r):
                    Logging.getLog().debug("timeout (%s)s  get value %s" % (timeout, str(result)))
                    return ret, value
            wait_time = int(int(timeout) / int(times))
            time.sleep(wait_time)
        Logging.getLog().debug("timeout")
        return -1, "timeout"
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def oracle_Database(param):
    try:
        sql, user = "", ""
        if ',' in param:
            sql, user = param.rsplit(',', 1)
        elif u'，' in param:
            sql, user = param.rsplit(u'，', 1)
        else:
            pass
        Logging.getLog().debug(sql)
        # if '("")' in sql or "('')" in sql or '()' in sql:
        #     return 0, ("",)
        ret, r = change_oracle(sql, user.upper())
        if sql.lower().__contains__("select"):
            if ret < 0:
                return ret, r
            if r:
                sendsn = r[0][0]
                return ret, (sendsn,)
            else:
                return ret, ("",)
        else:
            return ret, r
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


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
        return -1, (u'未输入正确的市场代码',)


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


def Generate_random_sno(param):
    '''
    获取1000以内的随机数
    '''
    sysdate, serverid = param.split(',')
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select batchsno from run..closeorder where serverid='%s' and sysdate='%s'" % (serverid, sysdate)
    bs = []
    ret, r = change_db(sql, servertype)
    new_sno = ""
    if ret == 0:
        if len(r) == 0:
            new_sno = random.randint(0, 1000)
        else:
            for x in r:
                bs.append(int(x[0]))
            new_sno = random.randint(0, 1000)
            while new_sno in bs:
                new_sno = random.randint(0, 1000)
    else:
        new_sno = random.randint(0, 1000)
    return ret, (new_sno,)


def GeneNewSno(param):
    '''
        获取不重复的融券预约序号
        Args:
            param: 入参。"sysdate,serverid"
        Returns:
            一个元组（ret，msg）：
            ret : 0 表示 成功，-1 表示 失败
            msg : 对应信息
    '''
    sysdate, serverid = param.split(',')
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select sno from run..creditreservestk  where serverid = '%s' and sysdate = '%s'" % (serverid, sysdate)
    ds = []
    ret, r = change_db(sql, servertype)
    if ret < 0:  # 如果没有数据，就返回1
        return 0, (1,)
    for x in r:
        ds.append(int(x[0]))
    if len(ds) == 0:
        new_sno = 1
    else:
        new_sno = str(max(ds) + 1)
    return ret, (new_sno,)


def GeneNewBsno(param):
    '''
        获取不重复的报价回购未到期合约序号
        Args:
            param: 入参。"serverid"

        Returns:
            一个元组（ret，msg）：
            ret : 0 表示 成功，-1 表示 失败
            msg : 对应信息
    '''
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select sno from run..bjhg_contract where serverid='%s'" % serverid
    ds = []
    ret, r = change_db(sql, servertype)
    for x in r:
        ds.append(int(x[0]))
    new_sno = str(max(ds) + 1)
    return ret, (new_sno,)


def GeneNewFundid(param):
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select max(fundid) from run..fundinfo where serverid = '%s'" % (serverid)
    ds = []
    ret, r = change_db(sql, servertype)
    new_fundid = ''
    if r:
        new_fundid = str(int(r[0][0]) + 1)
    return ret, (new_fundid,)


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
            try:
                ds.append(int(x[0]))
            except Exception as e:
                pass
        if len(ds) == 0:
            new_matchcode = 1
        else:
            new_matchcode = str(max(ds) + 1)
        return ret, (new_matchcode,)
    except Exception, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


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


def GetLastSerialsno(param=-1):
    '''
    获取最新业务请求号
    '''
    try:
        if os.path.exists(".\Script\serial.json"):
            _setting = json.loads(open(".\Script\serial.json", "r").read())
            Serialsno = _setting["serial"]
        return 0, (Serialsno,)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


def GetParamValue(param=''):
    '''
    获取多步骤 开户信息
    '''
    try:
        param_value = ""
        if os.path.exists(".\Script\parameters.json"):
            _setting = json.loads(open(".\Script\parameters.json", "r").read())
            param_value = _setting[str(param)]
        if not param_value:
            Logging.getLog().error(u"未查到对应信息请核对入参")
        return 0, (param_value,)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


def AddETFBasketStockAsset_adapter(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid_1, secuid_2, stkcode,
                                   count):
    '''
    只支持沪市和深市
    '''
    try:
        serverid = cF.get_core(servertype)
        sql = "select stkcode,amount,marketstk from etfcomponentinfo where ofcode='%s' " % stkcode
        ds = cF.executeRunSQL(sql, serverid)
        # print ds
        if len(ds) <= 0:
            return -1, u"未找到成分股"

        adapter = KCBPAdapter(gl.g_connectSqlServerSetting[serverid]["xpip"])
        ret = adapter.KCBPCliInit()
        if ret < 0:
            return -1, u"初始化KCBP适配器失败"
        for rec in ds:
            secuid = ""
            if rec['marketstk'] == '1':
                secuid = secuid_1
            else:
                secuid = secuid_2
            cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:%s,fundid:%s,secuid:%s,market:%s,stkcode:%s,stkeffect:%s,cost:10,remark:" % (
                str(serverid), operid_1, trdpwd, orgid, fundid, secuid,
                str(rec['marketstk']), rec["stkcode"], str(int(rec["amount"]) * int(count)))
            ret, code, level, msg = adapter.SendRequest(cmdstring)
            if ret < 0 or code != "0":
                adapter.KCBPCliExit()
                return -1, u"ret=%s,code=%s,level=%s,msg=%s" % (str(ret), str(code), str(level), msg)
            ds = adapter.GetReturnResult()
            sno = ds[1][0]
            cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150420,g_stationaddr:06690A0013D2,operdate:%s,sno:%s,action:1,afmremark:autotest" % (
                serverid, operid_2, trdpwd,
                datetime.datetime.now().strftime('%Y%m%d'), sno)
            ret, code, level, msg = adapter.SendRequest(cmdstring)
            if ret < 0 or code != "0":
                adapter.KCBPCliExit()
                return -1, u"ret=%s,code=%s,level=%s,msg=%s" % (str(ret), str(code), str(level), msg)
        adapter.KCBPCliExit()
        return 0, "OK"
    except:
        exc_info = cF.getExceptionInfo()
        print exc_info
        return -1, exc_info


def AddStockAsset_adapter(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count):
    '''
    只支持沪市和深市
    '''
    try:
        serverid = cF.get_core(servertype)
        Logging.getLog().debug(str(gl.g_connectSqlServerSetting[serverid]["xpip"]))
        adapter = KCBPAdapter(gl.g_connectSqlServerSetting[serverid]["xpip"])
        ret = adapter.KCBPCliInit()
        Logging.getLog().debug(u"初始化成功")
        if ret < 0:
            return -1, u"init KCBP fail"
        # Logging.getLog().debug("gl.g_account_id:%s"%gl.g_account_id)
        # Logging.getLog().debug("gl.g_accountDict:%s"%str(gl.g_accountDict))

        cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:%s,fundid:%s,secuid:%s,market:%s,stkcode:%s,stkeffect:%s,cost:10,remark:" % (
            "@serverid_%s@" % servertype, operid_1, trdpwd, orgid, fundid, secuid, market,
            stkcode, str(count))
        # cmdstring = "g_serverid:1,g_operid:4211707,g_operpwd:*Sh//+)$,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:4211,fundid:2441339,secuid:A214662871,market:1,stkcode:600012,stkeffect:100,cost:10,remark:"
        cmdstring = cF.GlobalParameterReplace(cmdstring, gl.g_account_id)
        Logging.getLog().debug(cmdstring)
        ret, code, level, msg = adapter.SendRequest(cmdstring)
        if ret < 0 or code != "0":
            adapter.KCBPCliExit()
            error_msg = ""
            if msg:
                error_msg = u"ret=%s,code=%s,level=%s,msg=%s,cmdstring=%s" % (
                    str(ret), str(code), str(level), msg, cmdstring)
            return -1, error_msg
        ds = adapter.GetReturnResult()
        sno = ds[1][0]
        cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150420,g_stationaddr:06690A0013D2,operdate:%s,sno:%s,action:1,afmremark:autotest" % (
            "@serverid_%s@" % servertype, operid_2, trdpwd,
            datetime.datetime.now().strftime('%Y%m%d'), sno)
        cmdstring = cF.GlobalParameterReplace(cmdstring, gl.g_account_id)
        Logging.getLog().debug(cmdstring)
        ret, code, level, msg = adapter.SendRequest(cmdstring)
        if ret < 0 or code != "0":
            adapter.KCBPCliExit()
            error_msg = ""
            if msg:
                error_msg = u"ret=%s,code=%s,level=%s,msg=%s,cmdstring=%s" % (
                    str(ret), str(code), str(level), msg, cmdstring)
            return -1, error_msg
        adapter.KCBPCliExit()
        return 0, "OK"
    except:
        exc_info = cF.getExceptionInfo()
        print exc_info
        return -1, exc_info


def AddStockAsset(param):
    """
    增加股票资产

    Args:
        param: 入参。"servertype,operid_1,operid_2,trdpwd,orgid,fundid,secuid,market,stkcode,count"

    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    """
    Logging.getLog().debug("1")
    # AddStockAsset(@serverid@,@operid_1@,@operid_2@,@operid_1_pwd@,@orgid@,@fundid@,@sh_a_secuid@,1,600000,200,0)
    servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count = param.split(',')
    trdpwd = trdpwd.replace('@comma@', ',')  # fixme
    ret, msg = AddStockAsset_adapter(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode,
                                     count)
    if ret < 0:
        Logging.getLog().error(u"问题发生: %s" % msg)
        return ret, (msg,)
    else:
        return 0, ("OK",)


def JzjyAddETFBasketStockAsset(param):
    """
    增加ETF篮子股票资产

    Args:
        param: 入参。"serverid,operid_1,operid_2,trdpwd,orgid,fundid,secuid,market,stkcode,count,account_group_id"

    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    """
    try:
        # 保存一个元组(cmdstring,pre_action,pro_action,account_group_id)列表
        serverid, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count, account_group_id = param.split(
            ',')
        cmdstring_list = []

        sql = "select stkcode,amount,marketstk from etfcomponentinfo where ofcode='%s' " % stkcode
        servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
        ret, ds = change_db(sql, servertype)
        if ret < 0:
            return -1, (ds,)

        if len(ds) == 0:
            Logging.getLog().error(u"%s 未能找到成份股" % stkcode)
            return -1, (u"没能找到成份股",)

        for rec in ds:
            if str(rec[1]) == '0':  # 现金替代的股票跳过，不需要增加持仓
                continue
            sql1 = "select secuid from run..secuid where custid=(select custid from run..secuid where secuid='%s' and market='%s') and market='%s' and creditflag=0" % (
                secuid, market, rec[2])
            ret1, ds1 = change_db(sql1, servertype)
            current_secuid = ds1[0][0].strip()

            cmdstring = "g_serverid=%s#g_operid=%s#g_operpwd=%s#g_operway=4#g_funcid=150402#g_stationaddr=001641AA2350#orgid=%s#fundid=%s#secuid=%s#market=%s#stkcode=%s#stkeffect=%s#cost=10#remark=" % (
                serverid, operid_1, trdpwd, orgid, fundid, current_secuid, rec[2], rec[0].strip(),
                str(rec[1] * int(count)))
            # pro_action = "save_param:sno = [0][0]"
            pro_action = """[{"content": "sno &equ&save_param([0][0])", "PUBLIC_FUNC_FLAG": 0,"call_when": "normal_call", "type": "General_Operation", "desc": ""}]"""
            cmdstring_list.append((cmdstring, "", pro_action, account_group_id))

            cmdstring = "g_serverid=%s#g_operid=%s#g_operpwd=%s#g_operway=4#g_funcid=150420#g_stationaddr=001641AA2350#operdate=@sys_date@#sno=@sno@#action=1#afmremark=" % (
                serverid, operid_2, trdpwd)
            cmdstring_list.append((cmdstring, "", "", account_group_id))

        ret, msg = RunTest(serverid, cmdstring_list)
        if ret < 0:
            Logging.getLog().error(u"问题发生: %s" % msg)
            return ret, (msg,)
        else:
            return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        print exc_info
        return -1, exc_info


def AddETFBasketStockAsset(param):
    """
    增加ETF篮子股票资产

    Args:
        param: 入参。"servertype,operid_1,operid_2,trdpwd,orgid,fundid,secuid_1,secuid_2,stkcode,count"

    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    """
    # 保存一个元组(cmdstring,pre_action,pro_action,account_group_id)列表
    servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid_1, secuid_2, stkcode, count = param.split(',')

    ret, msg = AddETFBasketStockAsset_adapter(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid_1, secuid_2,
                                              stkcode, count)
    if ret < 0:
        Logging.getLog().error(u"问题发生: %s" % msg)
        return ret, (msg,)
    else:
        return 0, ("OK",)


# def RunTest(serverid,cmdstring_list):
#    """
#    将当前运行记录导出为xml格式

#    Args:
#        running_dir: 运行目录

#    Returns:
#        一个元组（ret，msg）：
#        ret : 0 表示 成功，-1 表示 失败
#        msg : 对应信息
#    """
#    group_variable_dict = {}

#    hHandle,cli = cF.KCBPCliInit(serverid)
#    if hHandle < 0 :
#        return -1,u"初始化KCBPCli接口失败"
#    try:
#        for i in xrange(len(cmdstring_list)):
#            cmdstring = cmdstring_list[i][0]
#            pre_action = cmdstring_list[i][1]
#            pro_action = cmdstring_list[i][2]
#            account_group_id = str(cmdstring_list[i][3])

#            account_dict = gl.g_paramInfoDict.get(serverid).get(account_group_id)
#            group_variable_dict.update(account_dict.items())

#            cmdstring = cF.GlobalParameterReplace(cmdstring,str(serverid))
#            cmdstring = cF.GroupParameterReplace(cmdstring,group_variable_dict)

#            if (pre_action != ""):
#                ret,msg = cF.action_process(serverid,pre_action,group_variable_dict,[],"",cmdstring)
#                if ret != 0:
#                    Logging.getLog().error("前置动作err,msg=%s" %msg)
#                    cF.KCBPCliExit(hHandle,cli)
#                    return ret,msg

#            cmdstring = cF.GroupParameterReplace(cmdstring,group_variable_dict)
#            ret,code,level,msg = cF.SendRequest(hHandle,cli,cmdstring)
#            if ret == 0:
#                dataset = []
#                if (int(code) !=0):
#                    dataset.append(["code","level","msg"])
#                    dataset.append([code,level,msg])
#                else:
#                    dataset = cF.GetReturnResult(hHandle,cli)
#                if (int(code) == 0):
#                    if (pro_action !=""):
#                        ret,msg = cF.action_process(serverid,pro_action,group_variable_dict,dataset,"",cmdstring) #fixme xiaorz
#                        if ret != 0:
#                            cF.KCBPCliExit(hHandle,cli)
#                            return ret,msg
#                else:
#                    cF.KCBPCliExit(hHandle,cli)
#                    return -1,msg
#            else:
#                cF.KCBPCliExit(hHandle,cli)
#                return -1,msg
#        return 0,""
#    except:
#        exc_info = cF.getExceptionInfo()
#        Logging.getLog().error(exc_info)
#        cF.KCBPCliExit(hHandle,cli)
#        return -1,exc_info

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
        elif market == '5':
            if creditflag == '0':
                sql = "select top 1 secuid from secuid where market='5' and creditflag = '0' order by secuid desc"

        servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
        if sql != "":
            ret, r = change_db(sql, servertype)
            if ret < 0:
                return ret, (u"sql%s执行失败" % sql,)
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
                elif market == '5':
                    s = r[0][0].strip()
                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                return -1, (u"暂不支持的入参方式",)
        else:
            return -1, (u"暂不支持的入参方式",)
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
                    # return ret, (u"sql%s执行失败" %sql,)
            else:
                if market == '1':
                    s = r[0][0]

                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                elif market == '2':
                    s = r[0][0]
                    secuid = s[:1] + '{:0>9}'.format(str(int(s[1:]) + 1))
                    return 0, (secuid,)
                return -1, (u"暂不支持的入参方式",)
        else:
            return -1, (u"暂不支持的入参方式",)


def exec_sql_database(param_info):
    try:
        sql = param_info[:param_info.rfind(",")]
        application_type = param_info[param_info.rfind(",") + 1:]
        server_id = cF.get_core(application_type)
        ret, result = "", ""
        if str(server_id) in gl.g_connectSqlServerSetting.keys():
            result = cF.executeRunSQL(sql, server_id)
        else:
            result = cF.executeRunSQL_oracle(sql, server_id)
        if result != -1:
            return 0, (result,)
        return -1, ""
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, exc_info


def GeneNewBankAccid(param):
    serverid, bankcode = param.split(',')
    sql = "select top 1 bankid from banktranid where bankcode ='%s' order by bankid desc " % (bankcode)
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    ret, r = change_db(sql, servertype)
    if ret < 0:
        return ret, (u"sql%s执行失败" % sql,)
    s = r[0][0]
    newAccid = str(int(s) + 1)
    return 0, (newAccid,)


def GeneRZRQContractNO(param):
    custid, sysdate = param.split(',')
    RZRQContractNo = str(custid) + '-' + sysdate
    print RZRQContractNo
    return 0, (RZRQContractNo,)


def GetNewDate(param):
    """
    根据一个日期和差异天数，求一个新的日期

    Args:
        param: 字符串形式的入参 "yyyymmdd,差额值"
            例如：求 20151015 的后一天 GetNewDate("20151015,1")
                   求 20151015 的前一天 GetNewDate("20151015,-1")

    Returns:
        一个元组（ret，(newdate,)）：
        ret : 0 表示 成功，-1 表示 失败
        newdate :产生的新日期
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


# 基金赎回(10602305)
def del_ofelectcontract(param):
    orgid, fundid, tacode, ofcode = param.split(',')
    fundid = int(fundid[6:])
    sql = "delete run..ofelectcontract where orgid='%s' and fundid=%s and tacode=%s and ofcode='%s'" % (
        orgid, fundid, tacode, ofcode)
    ret, r = change_db(sql, 'p')
    return ret, ("",)


# 替换全局参数
def replaceparameter(param):
    try:
        cif_account = param
        sql = "select c.busin_account,a.stock_account,b.client_id,b.id_no from HS_ACCT.stockholder a,HS_ACCT.CLIENT b,hs_acct.businaccount c where a.client_id=b.client_id and b.client_id = c.client_id and b.cif_account = '%s' and (a.stock_account like '%s' or a.stock_account like '%s')  order by c.busin_account,stock_account" % (
            cif_account, 'A%', '0%')
        ret, r = change_oracle(sql, 'HS_ACCT')
        dict = {'busin_account': r[0][0], 'sh_stock_account': r[1][1], 'sz_stock_account': r[0][1],
                'client_id': r[0][2],
                'id_no': r[0][3], 'cif_account': cif_account}
        print dict
        doc = etree.ElementTree(file=".\\init\\142891090059622AV2\\ZHLCAutoTestSetting.xml")
        root = doc.getroot()
        xpath = ".//AccountInfo"
        elem_list = root.findall(xpath)
        for i, elem in enumerate(elem_list):
            if elem_list[i].attrib['id'] == '0':
                for elem in elem_list[i]:
                    if dict.has_key(elem.tag):
                        elem.text = dict[elem.tag]
                    else:
                        continue
        doc.write(".\\init\\142891090059622AV2\\ZHLCAutoTestSetting.xml", pretty_print=True, xml_declaration=True,
                  encoding='utf-8')
        return 0, ("",)
    except:
        msg = cF.getExceptionInfo()
        Logging.getLog().error(u"异常%s" % msg)
        return -1, msg


# 权限设置前去除权限
def del_fundinfo(param):
    custid = param
    sql = "select trdright from run..fundinfo where custid = '%s'" % (custid)
    ret, r = change_db(sql, 'p')
    if ret < 0:
        return ret, r
    sendsn = ','.join(r[0])
    sendsn = sendsn.replace("*", "")
    sql1 = "update run..fundinfo set trdright ='%s' WHERE custid = '%s'" % (sendsn, custid)
    ret, r = change_db(sql1, 'p')
    return ret, ("",)


# 初始化持仓
# def RunInitScript(i=1):  # 因清算同名原语移动至此，平台无此原语应用，此原语暂时注释
#     try:
#         cF.readNewAccountInfo("142891090059622AV2")
#         init_script_file = ".\\init\\142891090059622AV2\\initialise.sql"
#         dict = {}
#         f = open(init_script_file, 'r')
#         lines = f.readlines()
#         core = str(gl.g_connectSqlServerSetting['p']['serverid'])
#         srt = "select seat,market from run..orgseat where orgid='%s' and market in ('1','2')" % (
#             gl.g_accountDict['0']['branch_no'])
#         ret, r = change_db(srt, 'p')
#         dict = {'custid': int(gl.g_accountDict['0']['client_id'][6:]), 'serverid': core, 'sh_seat': r[0][0],
#                 'sz_seat': r[1][0], 'fundid': int(gl.g_accountDict['0']['busin_account'][6:])}
#         gl.g_accountDict.update(dict)
#         for j, line in enumerate(lines):
#             line = line.strip()
#             if line.startswith('--'):
#                 continue
#             if len(line) == 0:
#                 continue
# line = line.decode('utf-8')
#             sql = str(cF.GroupParameterReplace(line, gl.g_accountDict))
#             sql = cF.GlobalParameterReplace(sql, '0')
#             print sql
# print j
#             ret, r = change_db(sql, 'p')
# cF.readConfigFile()
#         return ret, ("",)
#     except:
#         exc_info = cF.getExceptionInfo()
#         strerror = u"解析通用配置文件ZHLCAutoTestSetting.xml 出现异常。原因：%s" % (exc_info)
#         Logging.getLog().critical(strerror)
#         return -1, exc_info



def create_account(params):
    """开户案例调用原语"""
    try:
        # 10,code0000001,1|2|3
        num, collection_code, server_id_str = params.split(',')
        server_id_str = server_id_str.strip()
        server_id_list = server_id_str.split("|")
        collection_code = collection_code.strip()
        num = num.strip()
        print "enter: create_account"
        # 获取多个核心sqlserver连接信息
        read_server_id_list = server_id_list + [90, 12, 13]
        read_sqlserver_core_config(read_server_id_list, gl.current_system_id)
        data = []
        ip_core_dict = {}
        try:
            server_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 90]
            server_id_list_new = [int(i) for i in server_id_list]
            if set(server_id_list_new) < set(server_ids):
                for server_id in server_id_list:
                    single_core_data = {"ip85": "", "ip87":
                        {
                            'username': str(gl.g_connectSqlServerSetting[str(90)]['username']),
                            'ip': str(gl.g_connectSqlServerSetting[str(90)]['ip'].split(",")[0]),
                            'password': str(gl.g_connectSqlServerSetting[str(90)]['password']),
                            'database': str(gl.g_connectSqlServerSetting[str(90)]['database'])
                        },
                                        "ip89": "",
                                        "count": str(num)}
                    ip_core_dict[str(gl.g_connectSqlServerSetting[str(90)]['ip'].split(",")[0])] = 90
                    if int(server_id) <= 5:
                        single_core_data["ip85"] = {
                            'username': str(gl.g_connectSqlServerSetting[str(12)]['username']),
                            'ip': str(gl.g_connectSqlServerSetting[str(12)]['ip'].split(",")[0]),
                            'password': str(gl.g_connectSqlServerSetting[str(12)]['password']),
                            'database': str(gl.g_connectSqlServerSetting[str(12)]['database'])
                        }
                        ip_core_dict[str(gl.g_connectSqlServerSetting[str(12)]['ip'].split(",")[0])] = 12
                        single_core_data["ip89"] = {
                            'username': str(gl.g_connectSqlServerSetting[str(server_id)]['username']),
                            'ip': str(gl.g_connectSqlServerSetting[str(server_id)]['ip'].split(",")[0]),
                            'password': str(gl.g_connectSqlServerSetting[str(server_id)]['password']),
                            'database': str(gl.g_connectSqlServerSetting[str(server_id)]['database'])
                        }
                        ip_core_dict[str(gl.g_connectSqlServerSetting[str(server_id)]['ip'].split(",")[0])] = int(
                            server_id)
                    elif 5 < int(server_id) <= 10:
                        single_core_data["ip85"] = {
                            'username': str(gl.g_connectSqlServerSetting[str(13)]['username']),
                            'ip': str(gl.g_connectSqlServerSetting[str(13)]['ip'].split(",")[0]),
                            'password': str(gl.g_connectSqlServerSetting[str(13)]['password']),
                            'database': str(gl.g_connectSqlServerSetting[str(13)]['database'])
                        }
                        ip_core_dict[str(gl.g_connectSqlServerSetting[str(13)]['ip'].split(",")[0])] = int(13)
                        single_core_data["ip89"] = {
                            'username': str(gl.g_connectSqlServerSetting[str(server_id)]['username']),
                            'ip': str(gl.g_connectSqlServerSetting[str(server_id)]['ip'].split(",")[0]),
                            'password': str(gl.g_connectSqlServerSetting[str(server_id)]['password']),
                            'database': str(gl.g_connectSqlServerSetting[str(server_id)]['database'])
                        }
                        ip_core_dict[str(gl.g_connectSqlServerSetting[str(server_id)]['ip'].split(",")[0])] = int(
                            server_id)
                    elif int(server_id) in [12, 13]:
                        single_core_data["ip85"] = {
                            'username': str(gl.g_connectSqlServerSetting[str(server_id)]['username']),
                            'ip': str(gl.g_connectSqlServerSetting[str(server_id)]['ip'].split(",")[0]),
                            'password': str(gl.g_connectSqlServerSetting[str(server_id)]['password']),
                            'database': str(gl.g_connectSqlServerSetting[str(server_id)]['database'])
                        }
                        ip_core_dict[str(gl.g_connectSqlServerSetting[str(server_id)]['ip'].split(",")[0])] = int(
                            server_id)
                    else:
                        pass
                    data.append(single_core_data)
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(exc_info)
        Logging.getLog().info(json.dumps(data))
        data = {"list": data}
        while True:
            if gl.g_flag == False:
                break
        gl.g_flag = True
        data_urlencode = urllib.urlencode(data)
        # url = "http://10.187.160.92:8080/khsByTool.do?%s" % data_urlencode
        # url = "http://10.187.160.92:8080/khsByToolTestOfJson.do?%s" % data_urlencode
        url = "http://10.176.65.17:8010/khsByToolTestOfJson.do?%s" % data_urlencode
        # url = "http://10.176.173.30:8080/khsByToolTestOfJson.do?%s" % data_urlencode
        req = urllib2.Request(url)
        res_data = urllib2.urlopen(req, timeout=10000)
        res = res_data.read()
        gl.g_flag = False
        res = json.loads(res)
        rtn = {}
        rtn["system_id"] = gl.current_system_id
        rtn["data"] = {}
        if res["data"]:
            if res.has_key("data"):
                for k in res["data"]:
                    if k in ip_core_dict.keys():
                        server_id = ip_core_dict[k]
                        account_list = res["data"][k]
                        default_account = {}
                        if str(server_id) in gl.g_default_account_info.keys():
                            default_account = gl.g_default_account_info[str(server_id)]["0"]
                        if default_account:
                            for child_account_list in account_list:
                                child_account_list.update(default_account)
                        rtn["data"][server_id] = account_list
            GlobalDict.get_value("MQClient")._redis_client.set_account_group_dict(collection_code, rtn)
        else:
            return -1, "error create_account"
        return 0, ""
    except:
        exc_info = cF.getExceptionInfo()
        strerror = u"解析通用配置文件ZHLCAutoTestSetting.xml 出现异常。原因：%s" % (exc_info)
        Logging.getLog().critical(strerror)
        return -1, exc_info


def create_user():
    try:
        # init_script_file="create_user.sql"
        # f = open(init_script_file, 'r')
        # lines = f.readlines()
        for server in gl.g_connectOracleSetting.keys():
            UserName = gl.g_connectOracleSetting[server]['UserName']
            UserList = gl.g_connectOracleSetting[server]['UserList'].split(',')
            i = 0
            ss = ''
            while (i < len(UserList)):
                ss += "'AUTO_" + UserList[i] + "',"
                i += 1
            ss = ss[:-1]
            sql = "select username from all_users where username in (%s)" % (ss.upper())
            print sql
            ret, r = change_oracle(sql, UserName)
            if len(r) != 0:
                for s in r:
                    sql = 'drop user "%s" cascade' % (s)
                    print sql
                    change_oracle(sql, UserName)
                for emp in gl.g_connectOracleSetting[server]['UserList'].split(','):
                    sql = 'create user AUTO_%s identified by hundsun' % (emp)
                    change_oracle(sql, UserName)
                    sql1 = 'grant resource,connect,dba to AUTO_%s' % (emp)
                    change_oracle(sql1, UserName)
                sql = 'grant insert any table to AUTO_%s' % (UserName)
                change_oracle(sql, UserName)
            else:
                for emp in gl.g_connectOracleSetting[server]['UserList'].split(','):
                    sql = 'create user AUTO_%s identified by hundsun' % (emp)
                    change_oracle(sql, UserName)
                    sql1 = 'grant resource,connect,dba to AUTO_%s' % (emp)
                    change_oracle(sql1, UserName)
                sql = 'grant insert any table to AUTO_%s' % (UserName)
                change_oracle(sql, UserName)
                #    for j,line in enumerate(lines):
                #        line = line.strip()
                #        if line.startswith('--'):
                #            continue
                #        if len(line) == 0:
                #            continue
                #        ret,r=change_oracle(line)
                # else:
                #    for j,line in enumerate(lines):
                #        line = line.strip()
                #        if line.startswith('--'):
                #            continue
                #        if len(line) == 0:
                #            continue
                #        ret,r=change_oracle(line)
                # return ret,("",)
    except:
        exc_info = cF.getExceptionInfo()
        strerror = u"解析通用配置文件ZHLCAutoTestSetting.xml 出现异常。原因：%s" % (exc_info)
        Logging.getLog().critical(strerror)
        return -1, exc_info


def GetTodayString(param):
    """
    获取当天的日期字符串

    Args:
        param: 无

    Returns:
        一个元组(ret，(newdate,))：
        ret : 0 表示 成功，-1 表示 失败
        datestring :产生的当天日期字符串，格式为"20150101"
    """
    try:
        today = datetime.date.today()
        return 0, (today.strftime('%Y%m%d'),)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


def GetNewWorkDate(param):
    """
    根据一个日期和差异天数，求一个新的工作日。差异天数为正值，计算出为非工作日的，向后顺延至工作日，差异天数为负值时，计算出非工作日的，向前退后至工作日

    Args:
        param: 字符串形式的入参 "yyyymmdd,差额值"
            例如：求 20151015 的后一工作日 GetNewDate("20151015,1")
                  求 20151015 的前一工作日 GetNewDate("20151015,-1")

    Returns:
        一个元组（ret，(newdate,)）：
        ret : 0 表示 成功，-1 表示 失败
        newdate :产生的新日期
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


# 客户资质凭证开通
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

    # 融资融券专用
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

        # Logging.getLog().info(sql)

        ret, r = change_db(sql, servertype)

        # ret,r=change_db(sql,'b')

        # 新增沪港通股东代码
        # RunInitHGTSecuid(param["custid"],param["serverid"])


# 新增沪港通股东代码
def RunInitHGTSecuid(custid, serverid):
    """
    新增沪港通股东代码

    Args:
        param: custid：客户代码
               serverid: KCBP核心号

    Returns:
        ret : 0 表示 成功，-1 表示 失败
    """
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


def expression_evaluation(param):
    """表达式计算"""
    try:
        index = param.find(",")
        key = param[:index].strip()
        value = param[index + 1:].strip()
        Logging.getLog().info(u"接收表达式为：%s" % str(param))
        value = eval(value)
        str_value = str(value)
        if "." in str_value:
            str_value = str_value.split(".")[1]
            num = len(str_value)
            if num > 2:
                if param and isinstance(value, float):
                    value1 = float(int(value * 100))
                    value2 = value * 100 - value1
                    if float(value2) < float(0.5):
                        value = value1 / 100
                    elif str(value2) >= '0.5':
                        value = (value1 + 1) / 100
                    else:
                        value = value1 / 100
                    value = "%.2f" % value
        Logging.getLog().info(u"计算结果为：%s" % str(value))
        return 0, {key: value}
    except Exception as e:
        # exc_info = cF.getExceptionInfo()
        # Logging.getLog().error(exc_info)
        return -1, (e,)


def ASSERT_EXPRESSION(param):
    '''
    验证一个表达是否为真
    '''
    param = param.replace("&comma&", ',')
    Logging.getLog().info("ASSERT_EXPRESSION: param:%s" % param)
    try:
        ret = eval(param)
        if ret == True:
            Logging.getLog().info("ASSERT_EXPRESSION: (%s) True" % str(param))
            return 0, ("",)
    except Exception as e:
        pass
    try:
        if "compare_list" not in param:
            if "@" in param:
                return -1, (str(param),)
            param = param.replace(u"，", ",")
            param = param.replace(u"：", ":")
            random_error_num = "0.01"

            if 'like' in param:
                param_1 = param.split("like")[0].strip()
                param_2 = param.split("like")[1].strip()
                if param_1 in param_2:
                    Logging.getLog().info("ASSERT_EXPRESSION: (%s) True" % str(param))
                    return 0, ("",)
                else:
                    Logging.getLog().info("ASSERT_EXPRESSION: (%s) False" % str(param))
                    return -1, ("",)

        if "," in param:
            if 'compare_list' in param.lower():
                gl.compare_list_group_list
                param = param.replace("\r\n", "")
                param = param.replace("\n", "").replace("@", "")
                params_list = param[:param.rfind(",")].split("==")
                if len(params_list) == 2:
                    list_str_1, list_str_2 = "", ""
                    if params_list[0] in gl.compare_list_group_list.keys():
                        list_str_1 = gl.compare_list_group_list[params_list[0]]
                    if params_list[1] in gl.compare_list_group_list.keys():
                        list_str_2 = gl.compare_list_group_list[params_list[1]]
                    # list_str_1 =
                    # list_str_2 = params_list[1]
                    # list_str_1 = eval(list_str_1)
                    # list_str_2 = eval(list_str_2)
                    print "<<<<<<<<<<<<<<<<compare_list<<<<<<<<<<<<<<<<<<<<"
                    print list_str_1, list_str_2
                    if len(list_str_1) == len(list_str_2):
                        for i in list_str_1:
                            keys_1 = i.keys()
                            flag_c = False
                            for j in list_str_2:
                                keys_2 = j.keys()
                                diff_keys = list((set(keys_1).union(set(keys_2))) ^ (set(keys_1) ^ set(keys_2)))
                                if diff_keys:
                                    for k in diff_keys:
                                        if str(i[k]) == str(j[k]):
                                            flag_c = True
                                        else:
                                            flag_c = False
                                if flag_c == True:
                                    list_str_2.remove(j)
                                    break
                            if flag_c == False:
                                Logging.getLog().info(
                                    "ASSERT_EXPRESSION: (%s) False, Different field information: " % str(i))
                                return -1, ("ASSERT_EXPRESSION: (%s) False, Different field information: " % str(i),)
                        Logging.getLog().info("ASSERT_EXPRESSION: (%s) True" % str(param))
                        return 0, ("",)
                    else:
                        Logging.getLog().info(
                            "ASSERT_EXPRESSION: (%s) False, the number of results is not equal" % str(param))
                        return -1, ("ASSERT_EXPRESSION: (%s) False, the number of results is not equal" % str(param),)
                else:
                    Logging.getLog().info("ASSERT_EXPRESSION: (%s) False" % str(param))
                    return -1, ("ASSERT_EXPRESSION: (%s) False" % str(param),)
            flag = False
            if "random_error" in param.lower():
                random_error = param.split("|")[1]
                if ":" in random_error:
                    random_error_num = random_error.split(":")[1]
                param = param.replace(random_error, "")
                param = param.replace("|", "")
                flag = True
            params_list = param.split(",")
            if params_list[1].strip() == 'float':
                count_param = "%.2f" % eval(params_list[0].split("==")[1].strip())
                param = params_list[0].split("==")[0] + "==" + count_param
            if params_list[1].strip() == 'int':
                count_param = str(eval(params_list[0].split("==")[1].strip()))
                if "." in count_param:
                    count_param = int(count_param.split(".")[0])
                param = params_list[0].split("==")[0] + "==" + str(count_param)
            if flag:
                param = param.split(",")[0]
                ret = eval(param)
                if ret == True:
                    Logging.getLog().info("ASSERT_EXPRESSION: (%s) True" % str(param))
                    return 0, ("",)
                params = param.split("==")
                param_1 = params[0].strip()
                param_2 = params[1].strip()
                param = str(float(param_1) + float(random_error_num)) + "==" + str(float(param_2))
                ret = eval(param)
                if ret == True:
                    Logging.getLog().info("ASSERT_EXPRESSION: (%s) True 误差等于%s" % (str(param), str(random_error_num)))
                    return 0, ("",)
                param = str(float(param_1)) + "==" + str(float(param_2) + float(random_error_num))
                ret = eval(param)
                if ret == True:
                    Logging.getLog().info("ASSERT_EXPRESSION: (%s) True 误差等于%s" % (str(param), str(random_error_num)))
                    return 0, ("",)

                return -1, (u"ASSERT_EXPRESSION: (%s) False 误差超过%s" % (str(param), str(random_error_num)),)
        ret = eval(param)

        if ret == True:
            Logging.getLog().info("ASSERT_EXPRESSION: (%s) True" % str(param))
            return 0, ("",)
        else:
            Logging.getLog().info("ASSERT_EXPRESSION: (%s) False" % str(param))
            return -1, ("",)
    except:
        try:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, (u"参数对比失败，param：%s exc_info:%s" % (param, exc_info))
        except:
            return -1, (u"参数对比失败，param：%s" % (param))


def getparam(param):
    param_list = param.split(',')
    if len(param_list) == 5:
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
            return ret, (u"没有在run..fundasset表查到该客户%s持仓信息！" % (test),)
    elif len(param_list) == 3:
        fundid, test, serverid = param.split(',')
        if len(test) == 6:
            sql = "select stkavl,stksale from run..stkasset where fundid ='%s' and stkcode='%s'" % (fundid, test)
        else:
            if test == 'D' or test == 'd':
                moneytype = '1'
            elif test == 'H' or test == 'h':
                moneytype = '2'
            else:
                moneytype = '0'
            sql = "select fundavl,fundbuy from run..fundasset where fundid ='%s' and moneytype='%s'" % (fundid, moneytype)
        ret, r = change_db(sql, serverid)
        # if len(test)==6 and len(r)>2:
        if ret < 0:
            return ret, (u"没有在run..fundasset表查到该客户%s持仓信息！" % (test),)
        return ret, r[0]


def checkparam(param):
    if len(param.split(',')[1]) > 1:
        fundid, test, serverid, price, qty, bsflag, y_stkavl, y_stksale, secuid, orgid = param.split(',')
        g_list = fundid + "," + test + "," + serverid + "," + secuid + "," + orgid
        ret, r = cF.getparam(g_list)
        if ret == 0:
            h_stkbal = r[0]
            h_stksale = r[1]
        else:
            return -1, (r,)
        if int(y_stksale) + int(qty) == int(h_stksale):
            return 0, ("",)
        else:
            return -1, (u'卖出股份与冻结股份数量不符！%d+%d!=%d' % (int(y_stksale), int(qty), int(h_stksale)),)
    else:
        fundid, test, serverid, price, qty, bsflag, y_fundavl, y_fundbuy, secuid, orgid = param.split(',')
        h_list = fundid + "," + test + "," + serverid + "," + secuid + "," + orgid
        ret, r = cF.getparam(h_list)
        if ret == 0:
            h_fundavl = r[0]
            h_fundbuy = r[1]
        else:
            return -1, (r,)

        sql = "select orderprice,bondintr from run..orderrec where fundid='%s' and secuid='%s' and orderprice='%s' " \
              "ORDER BY ordersno desc" % (fundid, secuid, price)
        if price:
            sql = "select orderprice,bondintr from run..orderrec where fundid='%s' and secuid='%s' and orderprice='%s' " \
                  "ORDER BY ordersno desc" % (fundid, secuid, price)
        else:
            sql = "select orderprice,bondintr from run..orderrec where fundid='%s' ORDER BY ordersno desc" % (fundid)

        ret, r = change_db(sql, serverid)
        total = int(qty) * float(r[0][0] + r[0][1])
        B_flag = ['0.', '0B', '0M', '0N', '0a', '0b', '0c', '0d', '0e', '0l', '0q', '0u', '0w', '0y', '2I', 'B', 'M',
                  'N', 'a', 'b', 'c', 'd', 'e', 'l', 'q', 'u', 'w', 'y']
        print '--> ', h_fundavl, h_fundbuy, total, r[0][0], r[0][1]
        if bsflag in B_flag:
            k1 = float(y_fundavl) - float(h_fundavl) - total
            kywc = total * (float(gl.g_deviationPCT) / 100) + 5
            if k1 <= kywc:
                return 0, ("",)
            else:
                return -1, (u'误差金额超出设置百分比',)
        else:
            kk = total  # *1.1#默认涨停价格
            k2 = float(y_fundavl) - float(h_fundavl) - kk
            kywc = total * (float(gl.g_deviationPCT) / 100) + 5
            if k2 <= kywc:
                return 0, (u"",)
            else:
                return -1, (u'误差金额超出设置百分比',)


def switch_account_group_id(id):
    '''
    使用原语操作，需要考虑到原来没有账号组的概念，所以需要进行切换

    Args:
        param: id：用户组id
    Returns:
        一个元组（ret，(id,)）：
            ret : 0 表示 成功，-1 表示 失败
            id : 切换后的用户组id
    '''
    return 0, (id,)


def modify_remote_server_time(param):
    '''
    根据配置文件修改远程服务器的时间信息

    Args:
        param: 为空时，代表为当前时间
            year:年
            month: 月
            day: 日
            hour: 时
            min: 分
            sec: 秒
    Returns:
        一个元组（ret，("",)）：
            ret : 0 表示 成功，-1 表示 失败
    Example:
        call:modify_remote_server_time("","","","09","30","00")   空字符代表当前时间
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
            # s = ServerProxy(ServerUrl)
            Logging.getLog().debug("ModifyRemoteServerDateTime:%s" % ServerUrl)
            try:
                ret, msg = 0, ''
                # ret, msg = s.ModifyRemoteServerDateTime(int(year), int(month), int(day), int(hour), int(min), int(sec))
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


def restart_and_close(param):
    '''
        重启或关闭中等程序
    '''
    try:
        ip, file_name = param.split(',')
        ServerUrl = "http://" + str(ip) + ":8888"
        s = ServerProxy(ServerUrl)
        ret, msg = s.RunAutoitScript(file_name)
        if ret < 0:
            Logging.getLog().error(msg)
        return 0, ("",)
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


def execute_exe_file(param):
    """集中营运加持仓"""
    try:
        params = param.split('#')
        ip = params.pop(0).strip()
        path_file_name = ",".join(params).strip()
        ServerUrl = "http://" + str(ip) + ":8888"
        s = ServerProxy(ServerUrl)
        ret, msg = s.RunAutoitHsChangeMoney(path_file_name)
        if ret != 0:
            Logging.getLog().error(msg)
            return -1, (msg,)
        return 0, (msg,)
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


def sleep_time(second):
    '''前后置需要添加休眠时间'''
    try:
        if second:
            second = int(second)
            time.sleep(second)
            Logging.getLog().debug("休息%s秒" % str(second))
        return 0, ""
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


def addDbfFileData(param):
    '''
    根据配置文件修改远程服务器的时间信息
    '''
    try:
        ip, path, col, value = param.split(';')
        col = col.replace("[", "").replace("]", "").strip().split(",")
        value = value.replace("[", "").replace("]", "").strip().split(",")
        ServerUrl = "http://" + str(ip) + ":8888"
        s = ServerProxy(ServerUrl)
        Logging.getLog().debug("addDbfFileData:%s" % ServerUrl)
        try:
            ret, msg = s.add_dbf_file_data(path, col, value)
            if ret == 0:
                ret, msg = s.RunAutoitScript("ZD.exe")
            if ret < 0:
                Logging.getLog().error(msg)
        except:
            exc = cF.getExceptionInfo()
            Logging.getLog().error(exc)
            return -1, (exc,)
        return 0, ("",)
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


def modify_dbf_info(param):
    '''
    修改dbf文件
    '''
    try:
        ip, path, index_column_name_values, update_column_name_value = param.split(',')
        # path = r"D:\code\test\qtymtzl一码通模拟库.dbf".decode("gbk")
        # index_column_name_values = "YMTH=180000000096".decode("gbk")
        # update_column_name_value = "LXDZ=花果山水帘洞cbs00000001".decode("gbk")
        # path = path.decode("utf-8")
        # index_column_name_values = index_column_name_values.decode("gbk")
        # update_column_name_value = update_column_name_value.decode("gbk")
        # for ip in gl.g_timeSyncServerSettingList:
        # proxy = ServerProxy("http://127.0.0.1:5558/")
        ServerUrl = "http://" + str(ip) + ":8888"
        s = ServerProxy(ServerUrl)
        Logging.getLog().debug("modify_dbf_info:%s" % ServerUrl)

        # Logging.getLog().debug("ModifyRemoteServerDateTime:%s" %ServerUrl)
        try:
            ret, msg = s.dbf_read_write_info(path, index_column_name_values, update_column_name_value)
            if ret == 0:
                ret, msg = s.RunAutoitScript("ZD.exe")
            if ret < 0:
                Logging.getLog().error(msg)
        except:
            exc = cF.getExceptionInfo()
            Logging.getLog().error(exc)
            return -1, (exc,)
        return 0, ("",)
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(exc_info)
        return -1, (exc_info,)


def upload_account_setting_file(system_id):
    """
    TODO chenbaoshuai
    将对应系统（当前支持综合理财自动化，用户中心自动化，集中交易自动化）ZHLCAutoTestSetting.xml文件（路径在.\\init\\[system_id]\\..）中用户组信息上传到服务器，写入数据库表中
    在全能账号创建用例组的最后一个用例的后续动作调用。
    :return:一个元祖（ret,msg):
            ret:0代表成功，-1代表失败
            msg：详细信息
    """
    homedir = os.getcwd()
    SettingPath = ""
    if system_id == "1428908551835S0NXP":
        SettingPath = r"%s\init\%s\YHZXAccountGroupSetting.xml" % (homedir, system_id)
    if system_id == "142891090059622AV2":
        SettingPath = r"%s\init\%s\ZHLCAccountGroupSetting.xml" % (homedir, system_id)
    try:
        data = cF.read_xml_info(SettingPath)
        ret, msg = gl.g_server_proxy.update_account_group_info(system_id, data)
        if ret < 0:
            Logging.getLog().error(msg)
            return -1, (msg,)
        # ret, msg = gl.g_server_proxy.rpc_generate_xml(system_id)
        # if ret < 0:
        #     Logging.getLog().error(msg)
        #     return -1, (msg,)
        # pass
        return 0, ""
    except BaseException:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info
    return 0, ""


def combine_business_item(param):
    """
    用于拼接集中营运的办理端审核业务搜索字符串
    :param param:
    :return:
    """
    try:
        business, name = param.split(',')

        try:
            tmp_business = business.decode('utf-8')
            business = tmp_business
        except UnicodeDecodeError:
            pass

        # 排除gbk编码情况
        ##从数据库中取出的为gbk编码,从其他地方可能就不是
        # try:
        #     if type(name) == unicode:
        #         pass
        #     else:
        #         name = name.encode('gbk')
        # except UnicodeDecodeError:
        #     pass
        comb = ""
        try:
            name1 = name.encode('gbk')
            comb = u"[%s] %s" % (business, name1)
        except Exception as e:
            comb = u"[%s] %s" % (business, name)

        ret, value_list = cF.read_funcid_param('14774643386617P4VW', '0000000001', 1)
        if ret < 0:
            Logging.getLog().error(u"读取参数失败")
            return -1, ""
        value_list[3] = comb
        # value_list = cF.ExcelParameterReplace(value_list,group_dict,0)
        cF.write_funcid_param('14774643386617P4VW', '0000000001', 1, value_list)

        ret, value_list = cF.read_funcid_param('14774643386617P4VW', '0000000001', 2)
        if ret < 0:
            Logging.getLog().error(u"读取参数失败")
            return -1, ""
        value_list[3] = comb
        # value_list = cF.ExcelParameterReplace(value_list,group_dict,0)
        cF.write_funcid_param('14774643386617P4VW', '0000000001', 2, value_list)

        ret, value_list = cF.read_funcid_param('14774643386617P4VW', '0000000001', 3)
        if ret < 0:
            Logging.getLog().error(u"读取参数失败")
            return -1, ""
        value_list[3] = comb
        # value_list = cF.ExcelParameterReplace(value_list,group_dict,0)
        cF.write_funcid_param('14774643386617P4VW', '0000000001', 3, value_list)
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info
    return 0, ""


def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    return elem


def on_the_business(param):
    """#1. 删除待办表记录：
                call:oracle_Database(delete from OS_CURRENTSTEP_PREV where ID in (select ID from os_currentstep where entry_id in (select instid from lcgtyw where YHTH='@cif_account19@' and YWDM='20399')),CIF)
                #2. 删除待办表详细记录：
                call:oracle_Database(delete from os_currentstep where entry_id in (select instid from lcgtyw where YHTH='@cif_account19@' and YWDM='20399'),CIF)
                #3. 更新业务流水表的状态
                call:oracle_Database(update cif.tywqq set clzt = '8'  where YHTH='@cif_account19@' and YWDM='20399',CIF)
    """
    try:
        Logging.getLog().critical("param=%s" % param)
        YHTH, YWDM = param.split(",")
        sql = "delete from OS_CURRENTSTEP_PREV where ID in (select ID from os_currentstep where entry_id in (select instid from lcgtyw where YHTH='%s' and YWDM='%s'))" % (
            YHTH, YWDM)
        oracle_Database_on_the_business(sql, 'CIF')
        sql = "delete from os_currentstep where entry_id in (select instid from lcgtyw where YHTH='%s' and YWDM='%s')" % (
            YHTH, YWDM)
        oracle_Database_on_the_business(sql, 'CIF')
        sql = "update cif.tywqq set clzt = '8'  where YHTH='%s' and YWDM='%s'" % (YHTH, YWDM)
        oracle_Database_on_the_business(sql, 'CIF')
        return 0, ''
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(u"配置文件更新失败%s" % (exc_info))
        return -1, ''


def update_account_info(id):
    try:
        gl.account_id = int(id)
        Logging.getLog().critical(u"gl.account_id%s" % (gl.account_id))
        system_id = gl.current_system_id.upper()
        # system_id = "1490844074559VS0IY"
        suffix = cF.get_suffix(system_id)
        if os.path.exists(".\Script\parameters.json"):
            f = open(".\Script\parameters.json", "r")
            t = f.read()
            t = t.replace("\n", "").strip().replace(" ", "")
            f.close()
            _setting = ""
            try:
                _setting = json.loads(t)
            except Exception as e:
                _setting = eval(t)
            if not isinstance(_setting, dict):
                return -1, u'获取账户组信息有误，请集中营运组查看生成账户组信息案例'
            gl.account_info.update(_setting)
            # 读取文件
            doc = etree.ElementTree(file=".\\init\\%s\\%sAccountGroupSetting.xml" % (system_id, suffix))
            root = doc.getroot()
            for AccountInfoName in _setting:
                AccountInfoValue = _setting[AccountInfoName]
                if not AccountInfoValue:
                    Logging.getLog().debug("AccountInfoName:%s 值为空， 请检查数据" % AccountInfoName)
                    continue
                Logging.getLog().debug("%s,%s,%s" % (id, AccountInfoName, AccountInfoValue))
                AccountInfoValue = AccountInfoValue.replace('&comma&', ',')
                AccountInfoValue = AccountInfoValue.replace('&colon&', ':')
                # 获取节点信息
                xpath = "AccountInfo[@id='%s']" % id
                AccountInfo = root.find(xpath)
                print AccountInfo
                dictlist = []
                for n in AccountInfo:
                    dictlist.append(n.tag)
                if AccountInfoName in dictlist:
                    for n in AccountInfo:
                        if n.tag == AccountInfoName:
                            n.text = AccountInfoValue.replace('amp;amp;', 'amp;')
                            break
                else:
                    dasd = etree.SubElement(AccountInfo, AccountInfoName)
                    dasd.text = AccountInfoValue.replace('amp;amp;', 'amp;')
                    doc = etree.ElementTree(root)
                    indent(root)
                    doc.write(".\\init\\%s\\%sAccountGroupSetting.xml" % (system_id, suffix), pretty_print=True,
                              xml_declaration=True,
                              encoding='utf-8')
            cF.readConfigFile()
            return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(u"配置文件更新失败%s" % (exc_info))
        return -1, ''


def lh_ha_exit():
    try:
        if gl.hr_quant_handle != None:
            # hr_quant_handle.ha_eixt()
            gl.hr_quant_handle.ha_exit()
            gl.hr_quant_handle = None
        if gl.hr_csm_handle != None:
            gl.hr_csm_handle.ha_exit()
            gl.hr_csm_handle = None
        Logging.getLog().critical(u"量化关闭连接成功")
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(u"量化关闭连接%s" % (exc_info))
        return -1, ''


def updateDict(param):
    system_id = gl.current_system_id.upper()
    suffix = cF.get_suffix(system_id)
    id, AccountInfoName, AccountInfoValue, FieldName, FieldValue = param.split(',')
    # if system_id == "142891090059622AV2" and AccountInfoName =='id_no' and "@" not in AccountInfoValue:
    #     gl.birthday_zhlc = AccountInfoValue[6:14]
    gl.account_id = int(id)
    if not str(AccountInfoValue).strip():
        return 0, ""
    if str(id) in gl.lh_account_info.keys():
        gl.lh_account_info[str(id)][str(AccountInfoName)] = AccountInfoValue
    else:
        gl.lh_account_info.update({str(id): {str(AccountInfoName): AccountInfoValue}})
    print "gl.lh_account_info ", gl.lh_account_info
    AccountInfoName = AccountInfoName.strip()
    AccountInfoValue = AccountInfoValue.strip()
    FieldName = FieldName.strip()
    FieldValue = FieldValue.strip()
    Logging.getLog().debug("%s,%s,%s,%s,%s" % (id, AccountInfoName, AccountInfoValue, FieldName, FieldValue))
    AccountInfoValue = AccountInfoValue.replace('&comma&', ',')
    AccountInfoValue = AccountInfoValue.replace('&colon&', ':')
    try:
        # 读取文件
        doc = etree.ElementTree(file=".\\init\\%s\\%sAccountGroupSetting.xml" % (system_id, suffix))
        root = doc.getroot()
        # 获取节点信息
        xpath = "AccountInfo[@id='%s']" % id
        AccountInfo = root.find(xpath)
        dictlist = []
        for n in AccountInfo:
            dictlist.append(str(n.tag).lower())
        if AccountInfoName.lower() in dictlist:
            for n in AccountInfo:
                if str(n.tag).lower() == AccountInfoName.lower():
                    n.text = AccountInfoValue.replace('amp;amp;', 'amp;')
                    if str(id) not in gl.return_account_update.keys():
                        gl.return_account_update.update({str(id): {"update": {str(AccountInfoName.lower()): n.text}}})
                    else:
                        gl.return_account_update[str(id)]["update"][str(AccountInfoName.lower())] = n.text
                    break
        else:
            dasd = etree.SubElement(AccountInfo, AccountInfoName.lower())
            dasd.text = AccountInfoValue.replace('amp;amp;', 'amp;')
            if str(id) not in gl.return_account_insert.keys():
                gl.return_account_insert.update({str(id): {"insert": {str(AccountInfoName.lower()): dasd.text}}})
            else:
                gl.return_account_insert[str(id)]["insert"][str(AccountInfoName.lower())] = dasd.text
                # AccountInfoName.text=AccountInfoName
        # 读取文件
        doc1 = etree.ElementTree(file='.\\init\\%s\\Field_dict.xml' % system_id)
        root1 = doc1.getroot()
        xpath1 = "Field[@desc='%s']" % FieldName
        dict = root1.find(xpath1)
        if dict == None:
            schemaElem = etree.SubElement(root1, "Field")
            schemaElem.attrib['desc'] = FieldName
            FieldtElem = etree.SubElement(schemaElem, "Option")
            try:
                FieldtElem.attrib['desc'] = FieldValue.decode('gbk')
            except BaseException as e:
                try:
                    FieldtElem.attrib['desc'] = FieldValue.decode('utf-8')
                except BaseException as e:
                    FieldtElem.attrib['desc'] = FieldValue
            FieldtElem.attrib['value'] = "@" + AccountInfoName + "@"
        else:
            xpath1 = "Field[@desc='%s']/Option[@value='%s']" % (FieldName, "@" + AccountInfoName + "@")
            dict1 = root1.find(xpath1)
            if dict1 == None:
                etree.SubElement(dict, "Option", desc=FieldValue, value="@" + AccountInfoName + "@")
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().critical(u"配置文件更新失败%s" % (exc_info))
        return -1
    doc = etree.ElementTree(root)
    indent(root)
    doc.write(".\\init\\%s\\%sAccountGroupSetting.xml" % (system_id, suffix), pretty_print=True, xml_declaration=True,
              encoding='utf-8')
    doc1 = etree.ElementTree(root1)
    indent(root1)
    doc1.write(".\\init\\%s\\Field_dict.xml" % system_id, pretty_print=True, xml_declaration=True, encoding='utf-8')
    # cF.readConfigFile()
    cF.readNewAccountInfo(system_id)
    # upload_account_setting_file("142891090059622AV2")
    return 0, ""


# def update_dict(param):
#     id, AccountInfoName, AccountInfoValue, FieldName, FieldValue = param.split(',')
#     Logging.getLog().debug("%s,%s,%s,%s,%s" % (id, AccountInfoName, AccountInfoValue, FieldName, FieldValue))
#     AccountInfoValue = AccountInfoValue.replace('&comma&', ',')
#     AccountInfoValue = AccountInfoValue.replace('&colon&', ':')
#     try:
#         # 读取文件
#         doc = etree.ElementTree(file=".\\init\\1428908551835S0NXP\\YHZXAccountGroupSetting.xml")
#         root = doc.getroot()
#         # 获取节点信息
#         xpath = "AccountInfo[@id='%s']" % id
#         AccountInfo = root.find(xpath)
#         dictlist = []
#         for n in AccountInfo:
#             dictlist.append(n.tag)
#         if AccountInfoName in dictlist:
#             for n in AccountInfo:
#                 if n.tag == AccountInfoName:
#                     n.text = AccountInfoValue.replace('amp;amp;', 'amp;')
#                     break
#         else:
#             dasd = etree.SubElement(AccountInfo, AccountInfoName)
#             dasd.text = AccountInfoValue.replace('amp;amp;', 'amp;')
#             # AccountInfoName.text=AccountInfoName
#         # 读取文件
#         doc1 = etree.ElementTree(file='.\\init\\1428908551835S0NXP\\Field_dict.xml')
#         root1 = doc1.getroot()
#         xpath1 = "Field[@desc='%s']" % FieldName
#         dict = root1.find(xpath1)
#         if dict == None:
#             schemaElem = etree.SubElement(root1, "Field")
#             schemaElem.attrib['desc'] = FieldName
#             FieldtElem = etree.SubElement(schemaElem, "Option")
#             FieldtElem.attrib['desc'] = FieldValue.decode('gbk')
#             FieldtElem.attrib['value'] = "@" + AccountInfoName + "@"
#         else:
#             xpath1 = "Field[@desc='%s']/Option[@value='%s']" % (FieldName, "@" + AccountInfoName + "@")
#             dict1 = root1.find(xpath1)
#             if dict1 == None:
#                 etree.SubElement(dict, "Option", desc=FieldValue, value="@" + AccountInfoName + "@")
#     except BaseException, ex:
#         exc_info = cF.getExceptionInfo()
#         Logging.getLog().critical(u"配置文件更新失败%s" % (exc_info))
#         return -1
#     doc = etree.ElementTree(root)
#     indent(root)
#     doc.write(".\\init\\1428908551835S0NXP\\YHZXAccountGroupSetting.xml", pretty_print=True, xml_declaration=True,
#               encoding='utf-8')
#     doc1 = etree.ElementTree(root1)
#     indent(root1)
#     doc1.write(".\\init\\1428908551835S0NXP\\Field_dict.xml", pretty_print=True, xml_declaration=True, encoding='utf-8')
#     cF.readConfigFile()
#     upload_account_setting_file("1428908551835S0NXP")
#     return 0, ""

def RunExiternalScript(param):
    """
    运行Script下的外用脚本
    param：脚本名称
    """

    log_info = ""

    cmd_str = '.\\Script\\%s' % (param)

    try:
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        # Logging.getLog().debug("ready to execute")
        proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        # proc.wait()
        while proc.poll() is None:
            line = proc.stdout.readline()
            line = line.strip()
            if line:
                print "%s" % line

        # 退出监控线程
        # Logging.getLog().debug("quit subprocess")
        print "quit subprocess with returncode = %s" % str(proc.returncode)

        # output_info = proc.stdout.readlines()
        # log_info = "".join(output_info)
        if proc.returncode == 0:
            return 0, ""
        else:
            return -1, ""

    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        print u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info)
        return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info)


def sleepTime(i):
    time.sleep(int(i))
    return 0, ""


def testAction(a, b, c):
    print a, b, c
    return 0, "test"


def getBlicence(param):
    # 区域码
    Region = [110101, 110102, 110105, 110106, 110107, 110108, 110109, 110111, 110112, 110113, 110114, 110115, 110116,
              110117, 110228, 110229, 120101, 120102, 120103, 120104, 120105, 120106, 120110, 120111, 120112, 120113,
              120114, 120115, 120116, 120221, 120223, 120225, 130101, 130102, 130103, 130104, 130105, 130107, 130108,
              130121, 130123, 130124, 130125, 130126, 130127, 130128, 130129, 130130, 130131, 130132, 130133, 130181,
              130182, 130183, 130184, 130185, 130201, 130202, 130203, 130204, 130205, 130207, 130208, 130209, 130223,
              130224, 130225, 130227, 130229, 130281, 130283, 130301, 130302, 130303, 130304, 130321, 130322, 130323,
              130324, 130401, 130402, 130403, 130404, 130406, 130421, 130423, 130424, 130425, 130426, 130427, 130428,
              130429, 130430, 130431, 130432, 130433, 130434, 130435, 130481, 130501, 130502, 130503, 130521, 130522,
              130523, 130524, 130525, 130526, 130527, 130528, 130529, 130530, 130531, 130532, 130533, 130534, 130535,
              130581, 130582, 130601, 130602, 130603, 130604, 130621, 130622, 130623, 130624, 130625, 130626, 130627,
              130628, 130629, 130630, 130631, 130632, 130633, 130634, 130635, 130636, 130637, 130638, 130681, 130682,
              130683, 130684, 130701, 130702, 130703, 130705, 130706, 130721, 130722, 130723, 130724, 130725, 130726,
              130727, 130728, 130729, 130730, 130731, 130732, 130733, 130801, 130802, 130803, 130804, 130821, 130822,
              130823, 130824, 130825, 130826, 130827, 130828, 130901, 130902, 130903, 130921, 130922, 130923, 130924,
              130925, 130926, 130927, 130928, 130929, 130930, 130981, 130982, 130983, 130984, 131001, 131002, 131003,
              131022, 131023, 131024, 131025, 131026, 131028, 131081, 131082, 131101, 131102, 131121, 131122, 131123,
              131124, 131125, 131126, 131127, 131128, 131181, 131182, 140101, 140105, 140106, 140107, 140108, 140109,
              140110, 140121, 140122, 140123, 140181, 140201, 140202, 140203, 140211, 140212, 140221, 140222, 140223,
              140224, 140225, 140226, 140227, 140301, 140302, 140303, 140311, 140321, 140322, 140401, 140402, 140411,
              140421, 140423, 140424, 140425, 140426, 140427, 140428, 140429, 140430, 140431, 140481, 140501, 140502,
              140521, 140522, 140524, 140525, 140581, 140601, 140602, 140603, 140621, 140622, 140623, 140624, 140701,
              140702, 140721, 140722, 140723, 140724, 140725, 140726, 140727, 140728, 140729, 140781, 140801, 140802,
              140821, 140822, 140823, 140824, 140825, 140826, 140827, 140828, 140829, 140830, 140881, 140882, 140901,
              140902, 140921, 140922, 140923, 140924, 140925, 140926, 140927, 140928, 140929, 140930, 140931, 140932,
              140981, 141001, 141002, 141021, 141022, 141023, 141024, 141025, 141026, 141027, 141028, 141029, 141030,
              141031, 141032, 141033, 141034, 141081, 141082, 141101, 141102, 141121, 141122, 141123, 141124, 141125,
              141126, 141127, 141128, 141129, 141130, 141181, 141182, 150101, 150102, 150103, 150104, 150105, 150121,
              150122, 150123, 150124, 150125, 150201, 150202, 150203, 150204, 150205, 150206, 150207, 150221, 150222,
              150223, 150301, 150302, 150303, 150304, 150401, 150402, 150403, 150404, 150421, 150422, 150423, 150424,
              150425, 150426, 150428, 150429, 150430, 150501, 150502, 150521, 150522, 150523, 150524, 150525, 150526,
              150581, 150601, 150602, 150621, 150622, 150623, 150624, 150625, 150626, 150627, 150701, 150702, 150721,
              150722, 150723, 150724, 150725, 150726, 150727, 150781, 150782, 150783, 150784, 150785, 150801, 150802,
              150821, 150822, 150823, 150824, 150825, 150826, 150901, 150902, 150921, 150922, 150923, 150924, 150925,
              150926, 150927, 150928, 150929, 150981, 152201, 152202, 152221, 152222, 152223, 152224, 152501, 152502,
              152522, 152523, 152524, 152525, 152526, 152527, 152528, 152529, 152530, 152531, 152921, 152922, 152923,
              210101, 210102, 210103, 210104, 210105, 210106, 210111, 210112, 210113, 210114, 210122, 210123, 210124,
              210181, 210201, 210202, 210203, 210204, 210211, 210212, 210213, 210224, 210281, 210282, 210283, 210301,
              210302, 210303, 210304, 210311, 210321, 210323, 210381, 210401, 210402, 210403, 210404, 210411, 210421,
              210422, 210423, 210501, 210502, 210503, 210504, 210505, 210521, 210522, 210601, 210602, 210603, 210604,
              210624, 210681, 210682, 210701, 210702, 210703, 210711, 210726, 210727, 210781, 210782, 210801, 210802,
              210803, 210804, 210811, 210881, 210882, 210901, 210902, 210903, 210904, 210905, 210911, 210921, 210922,
              211001, 211002, 211003, 211004, 211005, 211011, 211021, 211081, 211101, 211102, 211103, 211121, 211122,
              211201, 211202, 211204, 211221, 211223, 211224, 211281, 211282, 211301, 211302, 211303, 211321, 211322,
              211324, 211381, 211382, 211401, 211402, 211403, 211404, 211421, 211422, 211481, 220101, 220102, 220103,
              220104, 220105, 220106, 220112, 220122, 220181, 220182, 220183, 220201, 220202, 220203, 220204, 220211,
              220221, 220281, 220282, 220283, 220284, 220301, 220302, 220303, 220322, 220323, 220381, 220382, 220401,
              220402, 220403, 220421, 220422, 220501, 220502, 220503, 220521, 220523, 220524, 220581, 220582, 220601,
              220602, 220605, 220621, 220622, 220623, 220681, 220701, 220702, 220721, 220722, 220723, 220724, 220801,
              220802, 220821, 220822, 220881, 220882, 222401, 222402, 222403, 222404, 222405, 222406, 222424, 222426,
              230101, 230102, 230103, 230104, 230108, 230109, 230110, 230111, 230112, 230123, 230124, 230125, 230126,
              230127, 230128, 230129, 230182, 230183, 230184, 230201, 230202, 230203, 230204, 230205, 230206, 230207,
              230208, 230221, 230223, 230224, 230225, 230227, 230229, 230230, 230231, 230281, 230301, 230302, 230303,
              230304, 230305, 230306, 230307, 230321, 230381, 230382, 230401, 230402, 230403, 230404, 230405, 230406,
              230407, 230421, 230422, 230501, 230502, 230503, 230505, 230506, 230521, 230522, 230523, 230524, 230601,
              230602, 230603, 230604, 230605, 230606, 230621, 230622, 230623, 230624, 230701, 230702, 230703, 230704,
              230705, 230706, 230707, 230708, 230709, 230710, 230711, 230712, 230713, 230714, 230715, 230716, 230722,
              230781, 230801, 230803, 230804, 230805, 230811, 230822, 230826, 230828, 230833, 230881, 230882, 230901,
              230902, 230903, 230904, 230921, 231001, 231002, 231003, 231004, 231005, 231024, 231025, 231081, 231083,
              231084, 231085, 231101, 231102, 231121, 231123, 231124, 231181, 231182, 231201, 231202, 231221, 231222,
              231223, 231224, 231225, 231226, 231281, 231282, 231283, 232721, 232722, 232723, 310101, 310104, 310105,
              310106, 310107, 310108, 310109, 310110, 310112, 310113, 310114, 310115, 310116, 310117, 310118, 310120,
              310230, 320101, 320102, 320103, 320104, 320105, 320106, 320107, 320111, 320113, 320114, 320115, 320116,
              320124, 320125, 320201, 320202, 320203, 320204, 320205, 320206, 320211, 320281, 320282, 320301, 320302,
              320303, 320305, 320311, 320312, 320321, 320322, 320324, 320381, 320382, 320401, 320402, 320404, 320405,
              320411, 320412, 320481, 320482, 320501, 320505, 320506, 320507, 320508, 320509, 320581, 320582, 320583,
              320585, 320601, 320602, 320611, 320612, 320621, 320623, 320681, 320682, 320684, 320701, 320703, 320705,
              320706, 320721, 320722, 320723, 320724, 320801, 320802, 320803, 320804, 320811, 320826, 320829, 320830,
              320831, 320901, 320902, 320903, 320921, 320922, 320923, 320924, 320925, 320981, 320982, 321001, 321002,
              321003, 321012, 321023, 321081, 321084, 321101, 321102, 321111, 321112, 321181, 321182, 321183, 321201,
              321202, 321203, 321281, 321282, 321283, 321284, 321301, 321302, 321311, 321322, 321323, 321324, 330101,
              330102, 330103, 330104, 330105, 330106, 330108, 330109, 330110, 330122, 330127, 330182, 330183, 330185,
              330201, 330203, 330204, 330205, 330206, 330211, 330212, 330225, 330226, 330281, 330282, 330283, 330301,
              330302, 330303, 330304, 330322, 330324, 330326, 330327, 330328, 330329, 330381, 330382, 330401, 330402,
              330411, 330421, 330424, 330481, 330482, 330483, 330501, 330502, 330503, 330521, 330522, 330523, 330601,
              330602, 330621, 330624, 330681, 330682, 330683, 330701, 330702, 330703, 330723, 330726, 330727, 330781,
              330782, 330783, 330784, 330801, 330802, 330803, 330822, 330824, 330825, 330881, 330901, 330902, 330903,
              330921, 330922, 331001, 331002, 331003, 331004, 331021, 331022, 331023, 331024, 331081, 331082, 331101,
              331102, 331121, 331122, 331123, 331124, 331125, 331126, 331127, 331181, 340101, 340102, 340103, 340104,
              340111, 340121, 340122, 340123, 340124, 340181, 340201, 340202, 340203, 340207, 340208, 340221, 340222,
              340223, 340225, 340301, 340302, 340303, 340304, 340311, 340321, 340322, 340323, 340401, 340402, 340403,
              340404, 340405, 340406, 340421, 340501, 340503, 340504, 340506, 340521, 340522, 340523, 340601, 340602,
              340603, 340604, 340621, 340701, 340702, 340703, 340711, 340721, 340801, 340802, 340803, 340811, 340822,
              340823, 340824, 340825, 340826, 340827, 340828, 340881, 341001, 341002, 341003, 341004, 341021, 341022,
              341023, 341024, 341101, 341102, 341103, 341122, 341124, 341125, 341126, 341181, 341182, 341201, 341202,
              341203, 341204, 341221, 341222, 341225, 341226, 341282, 341301, 341302, 341321, 341322, 341323, 341324,
              341501, 341502, 341503, 341521, 341522, 341523, 341524, 341525, 341601, 341602, 341621, 341622, 341623,
              341701, 341702, 341721, 341722, 341723, 341801, 341802, 341821, 341822, 341823, 341824, 341825, 341881,
              350101, 350102, 350103, 350104, 350105, 350111, 350121, 350122, 350123, 350124, 350125, 350128, 350181,
              350182, 350201, 350203, 350205, 350206, 350211, 350212, 350213, 350301, 350302, 350303, 350304, 350305,
              350322, 350401, 350402, 350403, 350421, 350423, 350424, 350425, 350426, 350427, 350428, 350429, 350430,
              350481, 350501, 350502, 350503, 350504, 350505, 350521, 350524, 350525, 350526, 350527, 350581, 350582,
              350583, 350601, 350602, 350603, 350622, 350623, 350624, 350625, 350626, 350627, 350628, 350629, 350681,
              350701, 350702, 350721, 350722, 350723, 350724, 350725, 350781, 350782, 350783, 350784, 350801, 350802,
              350821, 350822, 350823, 350824, 350825, 350881, 350901, 350902, 350921, 350922, 350923, 350924, 350925,
              350926, 350981, 350982, 360101, 360102, 360103, 360104, 360105, 360111, 360121, 360122, 360123, 360124,
              360201, 360202, 360203, 360222, 360281, 360301, 360302, 360313, 360321, 360322, 360323, 360401, 360402,
              360403, 360421, 360423, 360424, 360425, 360426, 360427, 360428, 360429, 360430, 360481, 360482, 360501,
              360502, 360521, 360601, 360602, 360622, 360681, 360701, 360702, 360721, 360722, 360723, 360724, 360725,
              360726, 360727, 360728, 360729, 360730, 360731, 360732, 360733, 360734, 360735, 360781, 360782, 360801,
              360802, 360803, 360821, 360822, 360823, 360824, 360825, 360826, 360827, 360828, 360829, 360830, 360881,
              360901, 360902, 360921, 360922, 360923, 360924, 360925, 360926, 360981, 360982, 360983, 361001, 361002,
              361021, 361022, 361023, 361024, 361025, 361026, 361027, 361028, 361029, 361030, 361101, 361102, 361121,
              361122, 361123, 361124, 361125, 361126, 361127, 361128, 361129, 361130, 361181, 370101, 370102, 370103,
              370104, 370105, 370112, 370113, 370124, 370125, 370126, 370181, 370201, 370202, 370203, 370205, 370211,
              370212, 370213, 370214, 370281, 370282, 370283, 370284, 370285, 370301, 370302, 370303, 370304, 370305,
              370306, 370321, 370322, 370323, 370401, 370402, 370403, 370404, 370405, 370406, 370481, 370501, 370502,
              370503, 370521, 370522, 370523, 370601, 370602, 370611, 370612, 370613, 370634, 370681, 370682, 370683,
              370684, 370685, 370686, 370687, 370701, 370702, 370703, 370704, 370705, 370724, 370725, 370781, 370782,
              370783, 370784, 370785, 370786, 370801, 370802, 370811, 370826, 370827, 370828, 370829, 370830, 370831,
              370832, 370881, 370882, 370883, 370901, 370902, 370911, 370921, 370923, 370982, 370983, 371001, 371002,
              371081, 371082, 371083, 371101, 371102, 371103, 371121, 371122, 371201, 371202, 371203, 371301, 371302,
              371311, 371312, 371321, 371322, 371323, 371324, 371325, 371326, 371327, 371328, 371329, 371401, 371402,
              371421, 371422, 371423, 371424, 371425, 371426, 371427, 371428, 371481, 371482, 371501, 371502, 371521,
              371522, 371523, 371524, 371525, 371526, 371581, 371601, 371602, 371621, 371622, 371623, 371624, 371625,
              371626, 371701, 371702, 371721, 371722, 371723, 371724, 371725, 371726, 371727, 371728, 410101, 410102,
              410103, 410104, 410105, 410106, 410108, 410122, 410181, 410182, 410183, 410184, 410185, 410201, 410202,
              410203, 410204, 410205, 410211, 410221, 410222, 410223, 410224, 410225, 410301, 410302, 410303, 410304,
              410305, 410306, 410311, 410322, 410323, 410324, 410325, 410326, 410327, 410328, 410329, 410381, 410401,
              410402, 410403, 410404, 410411, 410421, 410422, 410423, 410425, 410481, 410482, 410501, 410502, 410503,
              410505, 410506, 410522, 410523, 410526, 410527, 410581, 410601, 410602, 410603, 410611, 410621, 410622,
              410701, 410702, 410703, 410704, 410711, 410721, 410724, 410725, 410726, 410727, 410728, 410781, 410782,
              410801, 410802, 410803, 410804, 410811, 410821, 410822, 410823, 410825, 410882, 410883, 410901, 410902,
              410922, 410923, 410926, 410927, 410928, 411001, 411002, 411023, 411024, 411025, 411081, 411082, 411101,
              411102, 411103, 411104, 411121, 411122, 411201, 411202, 411221, 411222, 411224, 411281, 411282, 411301,
              411302, 411303, 411321, 411322, 411323, 411324, 411325, 411326, 411327, 411328, 411329, 411330, 411381,
              411401, 411402, 411403, 411421, 411422, 411423, 411424, 411425, 411426, 411481, 411501, 411502, 411503,
              411521, 411522, 411523, 411524, 411525, 411526, 411527, 411528, 411601, 411602, 411621, 411622, 411623,
              411624, 411625, 411626, 411627, 411628, 411681, 411701, 411702, 411721, 411722, 411723, 411724, 411725,
              411726, 411727, 411728, 411729, 419001, 420101, 420102, 420103, 420104, 420105, 420106, 420107, 420111,
              420112, 420113, 420114, 420115, 420116, 420117, 420201, 420202, 420203, 420204, 420205, 420222, 420281,
              420301, 420302, 420303, 420321, 420322, 420323, 420324, 420325, 420381, 420501, 420502, 420503, 420504,
              420505, 420506, 420525, 420526, 420527, 420528, 420529, 420581, 420582, 420583, 420601, 420602, 420606,
              420607, 420624, 420625, 420626, 420682, 420683, 420684, 420701, 420702, 420703, 420704, 420801, 420802,
              420804, 420821, 420822, 420881, 420901, 420902, 420921, 420922, 420923, 420981, 420982, 420984, 421001,
              421002, 421003, 421022, 421023, 421024, 421081, 421083, 421087, 421101, 421102, 421121, 421122, 421123,
              421124, 421125, 421126, 421127, 421181, 421182, 421201, 421202, 421221, 421222, 421223, 421224, 421281,
              421301, 421303, 421321, 421381, 422801, 422802, 422822, 422823, 422825, 422826, 422827, 422828, 429004,
              429005, 429006, 429021, 430101, 430102, 430103, 430104, 430105, 430111, 430112, 430121, 430124, 430181,
              430201, 430202, 430203, 430204, 430211, 430221, 430223, 430224, 430225, 430281, 430301, 430302, 430304,
              430321, 430381, 430382, 430401, 430405, 430406, 430407, 430408, 430412, 430421, 430422, 430423, 430424,
              430426, 430481, 430482, 430501, 430502, 430503, 430511, 430521, 430522, 430523, 430524, 430525, 430527,
              430528, 430529, 430581, 430601, 430602, 430603, 430611, 430621, 430623, 430624, 430626, 430681, 430682,
              430701, 430702, 430703, 430721, 430722, 430723, 430724, 430725, 430726, 430781, 430801, 430802, 430811,
              430821, 430822, 430901, 430902, 430903, 430921, 430922, 430923, 430981, 431001, 431002, 431003, 431021,
              431022, 431023, 431024, 431025, 431026, 431027, 431028, 431081, 431101, 431102, 431103, 431121, 431122,
              431123, 431124, 431125, 431126, 431127, 431128, 431129, 431201, 431202, 431221, 431222, 431223, 431224,
              431225, 431226, 431227, 431228, 431229, 431230, 431281, 431301, 431302, 431321, 431322, 431381, 431382,
              433101, 433122, 433123, 433124, 433125, 433126, 433127, 433130, 440101, 440103, 440104, 440105, 440106,
              440111, 440112, 440113, 440114, 440115, 440116, 440183, 440184, 440201, 440203, 440204, 440205, 440222,
              440224, 440229, 440232, 440233, 440281, 440282, 440301, 440303, 440304, 440305, 440306, 440307, 440308,
              440401, 440402, 440403, 440404, 440501, 440507, 440511, 440512, 440513, 440514, 440515, 440523, 440601,
              440604, 440605, 440606, 440607, 440608, 440701, 440703, 440704, 440705, 440781, 440783, 440784, 440785,
              440801, 440802, 440803, 440804, 440811, 440823, 440825, 440881, 440882, 440883, 440901, 440902, 440903,
              440923, 440981, 440982, 440983, 441201, 441202, 441203, 441223, 441224, 441225, 441226, 441283, 441284,
              441301, 441302, 441303, 441322, 441323, 441324, 441401, 441402, 441421, 441422, 441423, 441424, 441426,
              441427, 441481, 441501, 441502, 441521, 441523, 441581, 441601, 441602, 441621, 441622, 441623, 441624,
              441625, 441701, 441702, 441721, 441723, 441781, 441801, 441802, 441821, 441823, 441825, 441826, 441827,
              441881, 441882, 445101, 445102, 445121, 445122, 445201, 445202, 445221, 445222, 445224, 445281, 445301,
              445302, 445321, 445322, 445323, 445381, 450101, 450102, 450103, 450105, 450107, 450108, 450109, 450122,
              450123, 450124, 450125, 450126, 450127, 450201, 450202, 450203, 450204, 450205, 450221, 450222, 450223,
              450224, 450225, 450226, 450301, 450302, 450303, 450304, 450305, 450311, 450321, 450322, 450323, 450324,
              450325, 450326, 450327, 450328, 450329, 450330, 450331, 450332, 450401, 450403, 450404, 450405, 450421,
              450422, 450423, 450481, 450501, 450502, 450503, 450512, 450521, 450601, 450602, 450603, 450621, 450681,
              450701, 450702, 450703, 450721, 450722, 450801, 450802, 450803, 450804, 450821, 450881, 450901, 450902,
              450921, 450922, 450923, 450924, 450981, 451001, 451002, 451021, 451022, 451023, 451024, 451025, 451026,
              451027, 451028, 451029, 451030, 451031, 451101, 451102, 451121, 451122, 451123, 451201, 451202, 451221,
              451222, 451223, 451224, 451225, 451226, 451227, 451228, 451229, 451281, 451301, 451302, 451321, 451322,
              451323, 451324, 451381, 451401, 451402, 451421, 451422, 451423, 451424, 451425, 451481, 460101, 460105,
              460106, 460107, 460108, 460201, 460321, 460322, 460323, 469001, 469002, 469003, 469005, 469006, 469007,
              469021, 469022, 469023, 469024, 469025, 469026, 469027, 469028, 469029, 469030, 500101, 500102, 500103,
              500104, 500105, 500106, 500107, 500108, 500109, 500110, 500111, 500112, 500113, 500114, 500115, 500116,
              500117, 500118, 500119, 500223, 500224, 500226, 500227, 500228, 500229, 500230, 500231, 500232, 500233,
              500234, 500235, 500236, 500237, 500238, 500240, 500241, 500242, 500243, 510101, 510104, 510105, 510106,
              510107, 510108, 510112, 510113, 510114, 510115, 510121, 510122, 510124, 510129, 510131, 510132, 510181,
              510182, 510183, 510184, 510301, 510302, 510303, 510304, 510311, 510321, 510322, 510401, 510402, 510403,
              510411, 510421, 510422, 510501, 510502, 510503, 510504, 510521, 510522, 510524, 510525, 510601, 510603,
              510623, 510626, 510681, 510682, 510683, 510701, 510703, 510704, 510722, 510723, 510724, 510725, 510726,
              510727, 510781, 510801, 510802, 510811, 510812, 510821, 510822, 510823, 510824, 510901, 510903, 510904,
              510921, 510922, 510923, 511001, 511002, 511011, 511024, 511025, 511028, 511101, 511102, 511111, 511112,
              511113, 511123, 511124, 511126, 511129, 511132, 511133, 511181, 511301, 511302, 511303, 511304, 511321,
              511322, 511323, 511324, 511325, 511381, 511401, 511402, 511421, 511422, 511423, 511424, 511425, 511501,
              511502, 511503, 511521, 511523, 511524, 511525, 511526, 511527, 511528, 511529, 511601, 511602, 511621,
              511622, 511623, 511681, 511701, 511702, 511721, 511722, 511723, 511724, 511725, 511781, 511801, 511802,
              511803, 511822, 511823, 511824, 511825, 511826, 511827, 511901, 511902, 511921, 511922, 511923, 512001,
              512002, 512021, 512022, 512081, 513221, 513222, 513223, 513224, 513225, 513226, 513227, 513228, 513229,
              513230, 513231, 513232, 513233, 513321, 513322, 513323, 513324, 513325, 513326, 513327, 513328, 513329,
              513330, 513331, 513332, 513333, 513334, 513335, 513336, 513337, 513338, 513401, 513422, 513423, 513424,
              513425, 513426, 513427, 513428, 513429, 513430, 513431, 513432, 513433, 513434, 513435, 513436, 513437,
              520101, 520102, 520103, 520111, 520112, 520113, 520114, 520121, 520122, 520123, 520181, 520201, 520203,
              520221, 520222, 520301, 520302, 520303, 520321, 520322, 520323, 520324, 520325, 520326, 520327, 520328,
              520329, 520330, 520381, 520382, 520401, 520402, 520421, 520422, 520423, 520424, 520425, 520502, 520521,
              520522, 520523, 520524, 520525, 520526, 520527, 520602, 520603, 520621, 520622, 520623, 520624, 520625,
              520626, 520627, 520628, 522301, 522322, 522323, 522324, 522325, 522326, 522327, 522328, 522601, 522622,
              522623, 522624, 522625, 522626, 522627, 522628, 522629, 522630, 522631, 522632, 522633, 522634, 522635,
              522636, 522701, 522702, 522722, 522723, 522725, 522726, 522727, 522728, 522729, 522730, 522731, 522732,
              530101, 530102, 530103, 530111, 530112, 530113, 530114, 530122, 530124, 530125, 530126, 530127, 530128,
              530129, 530181, 530301, 530302, 530321, 530322, 530323, 530324, 530325, 530326, 530328, 530381, 530402,
              530421, 530422, 530423, 530424, 530425, 530426, 530427, 530428, 530501, 530502, 530521, 530522, 530523,
              530524, 530601, 530602, 530621, 530622, 530623, 530624, 530625, 530626, 530627, 530628, 530629, 530630,
              530701, 530702, 530721, 530722, 530723, 530724, 530801, 530802, 530821, 530822, 530823, 530824, 530825,
              530826, 530827, 530828, 530829, 530901, 530902, 530921, 530922, 530923, 530924, 530925, 530926, 530927,
              532301, 532322, 532323, 532324, 532325, 532326, 532327, 532328, 532329, 532331, 532501, 532502, 532503,
              532523, 532524, 532525, 532526, 532527, 532528, 532529, 532530, 532531, 532532, 532601, 532622, 532623,
              532624, 532625, 532626, 532627, 532628, 532801, 532822, 532823, 532901, 532922, 532923, 532924, 532925,
              532926, 532927, 532928, 532929, 532930, 532931, 532932, 533102, 533103, 533122, 533123, 533124, 533321,
              533323, 533324, 533325, 533421, 533422, 533423, 540101, 540102, 540121, 540122, 540123, 540124, 540125,
              540126, 540127, 542121, 542122, 542123, 542124, 542125, 542126, 542127, 542128, 542129, 542132, 542133,
              542221, 542222, 542223, 542224, 542225, 542226, 542227, 542228, 542229, 542231, 542232, 542233, 542301,
              542322, 542323, 542324, 542325, 542326, 542327, 542328, 542329, 542330, 542331, 542332, 542333, 542334,
              542335, 542336, 542337, 542338, 542421, 542422, 542423, 542424, 542425, 542426, 542427, 542428, 542429,
              542430, 542521, 542522, 542523, 542524, 542525, 542526, 542527, 542621, 542622, 542623, 542624, 542625,
              542626, 542627, 610101, 610102, 610103, 610104, 610111, 610112, 610113, 610114, 610115, 610116, 610122,
              610124, 610125, 610126, 610201, 610202, 610203, 610204, 610222, 610301, 610302, 610303, 610304, 610322,
              610323, 610324, 610326, 610327, 610328, 610329, 610330, 610331, 610401, 610402, 610403, 610404, 610422,
              610423, 610424, 610425, 610426, 610427, 610428, 610429, 610430, 610431, 610481, 610501, 610502, 610521,
              610522, 610523, 610524, 610525, 610526, 610527, 610528, 610581, 610582, 610601, 610602, 610621, 610622,
              610623, 610624, 610625, 610626, 610627, 610628, 610629, 610630, 610631, 610632, 610701, 610702, 610721,
              610722, 610723, 610724, 610725, 610726, 610727, 610728, 610729, 610730, 610801, 610802, 610821, 610822,
              610823, 610824, 610825, 610826, 610827, 610828, 610829, 610830, 610831, 610901, 610902, 610921, 610922,
              610923, 610924, 610925, 610926, 610927, 610928, 610929, 611001, 611002, 611021, 611022, 611023, 611024,
              611025, 611026, 620101, 620102, 620103, 620104, 620105, 620111, 620121, 620122, 620123, 620201, 620301,
              620302, 620321, 620401, 620402, 620403, 620421, 620422, 620423, 620501, 620502, 620503, 620521, 620522,
              620523, 620524, 620525, 620601, 620602, 620621, 620622, 620623, 620701, 620702, 620721, 620722, 620723,
              620724, 620725, 620801, 620802, 620821, 620822, 620823, 620824, 620825, 620826, 620901, 620902, 620921,
              620922, 620923, 620924, 620981, 620982, 621001, 621002, 621021, 621022, 621023, 621024, 621025, 621026,
              621027, 621101, 621102, 621121, 621122, 621123, 621124, 621125, 621126, 621201, 621202, 621221, 621222,
              621223, 621224, 621225, 621226, 621227, 621228, 622901, 622921, 622922, 622923, 622924, 622925, 622926,
              622927, 623001, 623021, 623022, 623023, 623024, 623025, 623026, 623027, 630101, 630102, 630103, 630104,
              630105, 630121, 630122, 630123, 632121, 632122, 632123, 632126, 632127, 632128, 632221, 632222, 632223,
              632224, 632321, 632322, 632323, 632324, 632521, 632522, 632523, 632524, 632525, 632621, 632622, 632623,
              632624, 632625, 632626, 632721, 632722, 632723, 632724, 632725, 632726, 632801, 632802, 632821, 632822,
              632823, 640101, 640104, 640105, 640106, 640121, 640122, 640181, 640201, 640202, 640205, 640221, 640301,
              640302, 640303, 640323, 640324, 640381, 640401, 640402, 640422, 640423, 640424, 640425, 640501, 640502,
              640521, 640522, 650101, 650102, 650103, 650104, 650105, 650106, 650107, 650109, 650121, 650201, 650202,
              650203, 650204, 650205, 652101, 652122, 652123, 652201, 652222, 652223, 652301, 652302, 652323, 652324,
              652325, 652327, 652328, 652701, 652722, 652723, 652801, 652822, 652823, 652824, 652825, 652826, 652827,
              652828, 652829, 652901, 652922, 652923, 652924, 652925, 652926, 652927, 652928, 652929, 653001, 653022,
              653023, 653024, 653101, 653121, 653122, 653123, 653124, 653125, 653126, 653127, 653128, 653129, 653130,
              653131, 653201, 653221, 653222, 653223, 653224, 653225, 653226, 653227, 654002, 654003, 654021, 654022,
              654023, 654024, 654025, 654026, 654027, 654028, 654201, 654202, 654221, 654223, 654224, 654225, 654226,
              654301, 654321, 654322, 654323, 654324, 654325, 654326, 659001, 659002, 659003, 659004]
    # 生成随机区域码
    R_id = str(random.choice(Region))
    seven = random.randint(0, 9)
    eight = ''
    nine = ''
    if seven in [6, 7, 8, 9]:
        no = '{:0>7}'.format(str(random.randint(0, 9999999)))
    elif seven in [0, 1, 2, 3]:
        eight = str(random.randint(1, 2))
        no = '{:0>6}'.format(str(random.randint(0, 999999)))
    else:
        eight = str(random.randint(1, 5))
        nine = str(random.randint(0, 2))
        no = '{:0>5}'.format(str(random.randint(0, 99999)))
    for n in range(10):
        sq = R_id + str(seven) + eight + nine + no + str(n)
        p = []
        a = []
        s = []
        m = 10
        p.append(m)
        for i in range(len(sq)):
            a.append(int(sq[i]))
            s.append((p[i] % (m + 1)) + a[i])
            if (0 == s[i] % m):
                p.append(10 * 2)
            else:
                p.append((s[i] % m) * 2)
        # print sq
        if len(sq) == 15:
            if s[14] % m == 0:
                # print sq
                return 0, (sq,)
                # else:
                #    if n==8:
                #        getBlicence('1')


def getOrgcode(param):
    d = [3, 7, 9, 10, 5, 8, 4, 2]
    # while(True):
    si = random.sample('0123456789ABCDEFGHIJKLMNOPQRSTYVWXYZ', 8)
    d2 = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'A': 10, 'B': 11, 'C': 12,
          'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 18, 'J': 19, 'K': 20, 'L': 21, 'M': 22, 'N': 23, 'O': 24,
          'P': 25, 'Q': 26, 'R': 27, 'S': 28, 'T': 29, 'U': 30, 'V': 31, 'W': 32, 'X': 33, 'Y': 34, 'Z': 35}
    i = 1
    s = 0
    while i <= 8:
        s = d2[si[i - 1]] * d[i - 1] + s
        i += 1
    # print s
    #  if s%11==1 or s%11==0:
    r = 11 - s % 11
    #       break

    if r == 10:
        value = ''.join(si) + '-X'
        # print value
        return 0, (value,)
    elif r == 11:
        value = ''.join(si) + '-0'
        # print value
        return 0, (value,)
    else:
        value = ''.join(si) + '-' + str(r)
        # print value
        return 0, (value,)


def max_value(param):
    """表达式计算"""
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


def readKCXPqueue(param):
    """
    1. 开发一个kcxp_queue_read.exe （使用C/C++）：
        入参为: kcxp IP，用户名，密码，队列名
        执行成功（包括没有读到队列信息），进程返回码为0；
        执行失败，进程返回码为-1；
        内部逻辑：
            如果执行成功：生成一个kcxp_queue.res文件，内部为队列信息列表，一条队列占一行；
            如果执行失败：生成一个kcxp_queue.res文件，内部为失败原因描述；
    2. 开发一个原语：readKCXPQueue，KCXP 标识号，用户名，密码，队列名
        内部逻辑：
        1. 将KCXP标识号，转化为IP地址（避免后期用例调整），再调用kcxp_queue_read.exe进程，获取队列信息（从kcxp_queue.res文件）
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
                        text = text.split("\n")
                        fw = open(path, "w")
                        if text:
                            for i in text:
                                if i:
                                    i = i.replace("\n", '').replace("\x01", " ").replace("\x00", "")
                                    fw.write(i + "\n")
                        fw.close()
                        return 0, (u"%s 成功获取数据" % queueName,)
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


def GeneNewTable(param):
    '''
    获取日期特定格式的表名
    Args:
        param: 入参。"table"
    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
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


def GeneNewExterSno(param):
    '''
    获取不重复的预约序号
    Args:
        param: 入参。"sysdate,serverid"
    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    '''
    sysdate, orgid, custid, serverid = param.split(',')
    s_str = '3_' + sysdate + '_' + orgid + '_' + custid
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select extersno from run..logunicounter where serverid = '%s' and sysdate = '%s' and extersno like '%s'" % (
        serverid, sysdate, '%' + s_str + '%')
    ds = []
    ret, r = change_db(sql, servertype)
    if ret < 0:  # 如果没有数据，就返回1
        return 0, (s_str + '_' + '00000001',)
    for x in r:
        ds.append(int(x[0].split('_')[-1]))
    if len(ds) == 0:
        new_extersno = s_str + '_' + '00000001'
    else:
        new_extersno = s_str + '_' + '{:0>8}'.format(str(max(ds) + 1))
    return ret, (new_extersno,)


def RunTest(serverid, cmdstring_list):
    """
    将当前运行记录导出为xml格式
    Args:
        running_dir: 运行目录
    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    """
    group_variable_dict = {}
    hHandle, cli = cF_kcbp.KCBPCliInit(serverid)
    if hHandle < 0:
        return -1, u"初始化KCBPCli接口失败"
    try:
        for i in xrange(len(cmdstring_list)):
            cmdstring = cmdstring_list[i][0]
            pre_action = cmdstring_list[i][1]
            pro_action = cmdstring_list[i][2]
            account_group_id = str(cmdstring_list[i][3])
            account_dict = gl.g_paramInfoDict.get(serverid).get(account_group_id)
            # group_variable_dict.update(account_dict.items())
            group_variable_dict.update(account_dict)
            cmdstring = cF_kcbp.GlobalParameterReplace(cmdstring, str(serverid))
            cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
            if pre_action:
                ret, msg = cF_kcbp.action_process(pre_action, group_variable_dict, [], "", cmdstring, serverid)
                if ret != 0:
                    Logging.getLog().error("前置动作err,msg=%s" % msg)
                    cF_kcbp.KCBPCliExit(hHandle, cli)
                    return ret, msg
            cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
            Logging.getLog().debug(cmdstring)
            ret, code, level, msg = cF_kcbp.SendRequest(hHandle, cli, cmdstring)
            if ret == 0:
                dataset = []
                if (int(code) != 0):
                    dataset.append(["code", "level", "msg"])
                    dataset.append([code, level, msg])
                else:
                    dataset = cF_kcbp.GetReturnResult(hHandle, cli)
                if (int(code) == 0):
                    if pro_action:
                        ret, msg = cF_kcbp.action_process(pro_action, group_variable_dict, dataset, "",
                                                          cmdstring, serverid)  # fixme xiaorz
                        if ret != 0:
                            cF_kcbp.KCBPCliExit(hHandle, cli)
                            return ret, msg
                else:
                    cF_kcbp.KCBPCliExit(hHandle, cli)
                    return -1, msg
            else:
                cF_kcbp.KCBPCliExit(hHandle, cli)
                return -1, msg
        return 0, ""
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        cF_kcbp.KCBPCliExit(hHandle, cli)
        return -1, exc_info


def GeneRZRQNewCreditDebtsSno(param):
    serverid = param
    servertype = gl.g_connectSqlServerSetting[str(serverid)]["servertype"]
    sql = "select top 1 sno, ordersno, orderid from run..creditdebts order by sno desc"
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
    newOrderId = orderStr + str(int(orderId) + 1)
    return ret, (newSno, newOrderSno, newOrderId)


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


def dbfreader(f):
    try:
        """Returns an iterator over records in a Xbase DBF file.
        The first row returned contains the field names.
        The second row contains field specs: (type, size, decimal places).
        Subsequent rows contain the data records.
        If a record is marked as deleted, it is skipped.
        File should be opened for binary reads.
        """
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
        fields.insert(0, ('DeletionFlag', 'C', 1, 0))
        fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in fields])
        fmtsiz = struct.calcsize(fmt)
        for i in xrange(numrec):
            record = struct.unpack(fmt, f.read(fmtsiz))
            if record[0] != ' ':
                continue  # deleted record
            result = []
            for (name, typ, size, deci), value in itertools.izip(fields, record):
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
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)


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


def querycheck(param):
    '''
    查询案例返回数据校验:
    checklist: 待校验字段列表
    count: 校验条数
    '''
    ret = param.count(',')
    if ret <= 0:
        count = int(param)
        if count == (len(gl.g_datalist) - 1):
            return 0, ("",)
        else:
            return -1, (u"返回数据条数校验失败！",)
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
                    return -1, (u"%s返回数据与预期不匹配！" % c_param,)
            row_count += 1
        if row_count == count:
            return 0, ("",)
        else:
            return -1, (u"返回数据条数校验失败！",)
    else:
        return -1, (u"数据返回出错或没有数据返回！",)


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


def test():
    import urllib
    import urllib2
    data = {"list": [{"ip85": "10.187.160.85", "ip87": "10.187.160.87", "ip89": "10.187.160.89", "count": "2"}]}
    data_urlencode = urllib.urlencode(data)
    url = "http://10.187.160.92:8080/khsdata.do?%s" % data_urlencode
    req = urllib2.Request(url)
    print url
    res_data = urllib2.urlopen(req)
    res = res_data.read()
    print res


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
    ver = 3
    now = datetime.datetime.now()
    yr, mon, day = now.year - 1900, now.month, now.day
    numrec = len(records)
    numfields = len(fieldspecs)
    lenheader = numfields * 32 + 33
    lenrecord = sum(field[1] for field in fieldspecs) + 1
    hdr = struct.pack('<BBBBLHH20x', ver, yr, mon, day, numrec, lenheader, lenrecord)
    f.write(hdr)
    for name, (typ, size, deci) in itertools.izip(fieldnames, fieldspecs):
        name = str(name).encode('GBK')
        name = name.ljust(11, '\x00')
        fld = struct.pack('<11sc4xBB14x', name, typ, size, deci)
        f.write(fld)
    f.write('\r')
    for record in records:
        f.write(' ')  # deletion flag
        for (typ, size, deci), value in itertools.izip(fieldspecs, record):
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
    f.write('\x1A')


def update_dbf_file(path, index_column_name_values, update_column_name_value):
    try:
        index_column_name_values_list = []
        if '&' in index_column_name_values:
            index_column_name_values_list = index_column_name_values.split("&")
        if not index_column_name_values_list:
            index_column_name_values_list.append(index_column_name_values)
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
                            print "flag_update=1"
                            print row_data.values()
                        dbf_data.append(row_data.values())
        if os.path.exists(path):
            os.remove(path)
        f = open(path, 'wb')
        dbfwriter(f, fieldnames, fieldspecs, dbf_data)
        f.close()
        return 0, ("",)
    except Exception as e:
        print e
        return -1, e


def file_rename(old_type, new_type, file_dir):
    old_files = find_file(old_type, file_dir)
    for old_file in old_files:  # 遍历所有文件
        filename = os.path.splitext(old_file)[0]  # 文件名
        new_file = os.path.join(filename + new_type)  # 新的文件路径
        os.remove(new_file)
        os.rename(old_file, new_file)  # 重命名


def find_file(file_type, file_dir):
    file_set = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == file_type:
                file_set.append(os.path.join(root, file))
    return file_set


def find_file(file_type, file_dir):
    file_set = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == file_type:
                file_set.append(os.path.join(root, file))
    return file_set


def get_minfee_commissionrate_info(params):
    try:
        serverid, market, stkcode, fundid, custid, bsflag, dbid, orgid = params.split(",")
        print "serverid, market, stkcode, fundid, custid, bsflag, dbid, orgid"
        print serverid, market, stkcode, fundid, custid, bsflag, dbid, orgid
        market = market.strip()
        stkcode = stkcode.strip()
        fundid = fundid.strip()
        custid = custid.strip()
        bsflag = bsflag.strip()
        dbid = dbid.strip()
        data = """#获取证券类型
        call:stktype = sqlserver_Database(select stktype from run..stktrd where market = '@market@' and  stkcode = '@stkcode@',@dbid@)
        #获取交易类型
        call:trdid = sqlserver_Database(select trdid from run..stktrd where market = '@market@' and  stkcode = '@stkcode@',@dbid@)
        #获取资金室号
        call:fundlevel = sqlserver_Database(select fundlevel from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #获取资金分组
        call:fundgroup = sqlserver_Database(select fundgroup from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #获取操作方式
        call:operway = sqlserver_Database(select operway from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #获取资金类别
        call:fundkind = sqlserver_Database(select fundkind from run..fundinfo where fundid = '@fundid@' ,@dbid@)
        #取佣金模板号#老佣金费率
        call:feemodelid1 = sqlserver_Database(select top 1 feemodelid from run..custcommission where orgid = @orgid@ and (fundid = -1 or fundid = '@fundid@') and (custid = -1 or custid = '@custid@') and (ltrim(rtrim(pt_fundkind)) = '' or charindex('@fundkind@',pt_fundkind) > 0)  and (ltrim(rtrim(pt_fundlevel)) = '' or charindex('@fundlevel@',pt_fundlevel) > 0) and (ltrim(rtrim(pt_fundgroup)) = '' or charindex('@fundgroup@',pt_fundgroup) > 0) and (ltrim(rtrim(pt_operway)) = '' or CHARINDEX('@operway@',pt_operway) > 0 ) and (ltrim(rtrim(pt_stktype)) = '' or CHARINDEX('@stktype@',pt_stktype) > 0 ) ORDER BY fundid DESC,custid DESC,pt_fundkind DESC,pt_fundlevel DESC,pt_fundgroup DESC, pt_operway DESC, pt_stktype DESC zero,@dbid@)
        #确认佣金模板号（若未取到值则默认模板号为：**）
        call:feemodelid = retures_qualified_value('@feemodelid1@',!='0',@feemodelid1@,**)
        #获取最低佣金
        call:minfee_old = sqlserver_Database(select minfee from run..commissionmodel where orgid = '@orgid@' and market = '@market@' and trdid = '@trdid@' and stktype = '@stktype@' and moneytype = '0' and bsflag = '@bsflag@' and feemodelid = '@feemodelid@' zero,@dbid@) 
        #获取佣金费率
        call:commissionrate_old = sqlserver_Database(select commissionrate from run..commissionmodel where orgid = '@orgid@' and market = '@market@' and trdid = '@trdid@' and stktype = '@stktype@' and moneytype = '0' and bsflag = '@bsflag@' and feemodelid = '@feemodelid@' zero,@dbid@)
        #取默认费率#新佣金费率
        call:commissionrate_new_1_1 = sqlserver_Database(select top 1 commissionrate from run..busicommission where market = '@market@' and stktype = '@stktype@' and bsflag = '@bsflag@' and trdid = '@trdid@' and moneytype = '0' and (stkcode = '' or stkcode = '@stkcode@') order by stkcode desc zero,@dbid@)
        #业务部门确认custdiscount未找到则取默认费率
        call:busikind1 = sqlserver_Database(select top 1 busikind from run..busicommission where market = '@market@' and stktype = '@stktype@' and bsflag = '@bsflag@' and trdid = '@trdid@' and moneytype = '0' and (stkcode = '' or stkcode = '@stkcode@') order by stkcode desc zero,@dbid@)
        call:busikind = retures_qualified_value('@busikind1@',!='0',@busikind1@,)
        call:discountrate1 = sqlserver_Database(select discountrate from run..custdiscount where orgid = '@orgid@' and fundid = '@fundid@' and custid = '@custid@' and busikind = '@busikind@' zero,@dbid@)
        call:discountrate = retures_qualified_value('@discountrate1@',!='0',@discountrate1@,0)
        call:commissionrate_new_1=expression_evaluation(@commissionrate_new_1_1@*@discountrate@)
        call:commissionrate_new = retures_qualified_value('@discountrate@',!='0',@commissionrate_new_1@,@commissionrate_new_1_1@)
        call:minfee_new = sqlserver_Database(select top 1 minfee from run..busicommission where market = '@market@' and stktype = '@stktype@' and bsflag = '@bsflag@' and trdid = '@trdid@' and moneytype = '0' and (stkcode = '' or stkcode = '@stkcode@') order by stkcode desc zero,@dbid@)
        #取orgcommission表中commissionflag_order值：commissionflag_order为0或''时采用老佣金模式；commissionflag_order为1时采用新佣金模式
        call:commissionflag_order = sqlserver_Database(select commissionflag_order from run..orgcommission where serverid='@serverid@' and orgid='@orgid@' zero,@dbid@)
        call:commissionrate = retures_qualified_value('@commissionflag_order@',!='1',@commissionrate_old@,@commissionrate_new@)
        call:minfee = retures_qualified_value('@commissionflag_order@',!='1',@minfee_old@,@minfee_new@) """
        data = data.decode("gbk").replace("@serverid@", serverid).replace("@market@", market).replace("@stkcode@",
                                                                                                      stkcode).replace(
            "@fundid@", fundid).replace("@custid@", custid).replace("@bsflag@", bsflag).replace("@dbid@", dbid).replace(
            "@orgid@", orgid)
        action_list = data.split("\n")
        action_list = [i.strip() for i in action_list]
        VARIABLE, actions = cF.action_update(action_list, {})
        # import commFuncs_kcbp as cF_kcbp
        # cF_kcbp.action_process(serverid, actions, gl.all_group_dict)
        cF_kcbp.action_process(actions, gl.all_group_dict, [], fundid, "", serverid)
        return 0, ('',)
    except Exception as e:
        print e
        return -1, e


def read_kcbp_info():
    cmd = ["E:\\soft\\xpbp\kcbp\\bin\\imdbcmd.exe", "list table"]
    sub = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    result_code = sub.stdout.read()
    print result_code


def add_dbf_file_data(params):
    try:
        anyone_data = []
        path, col, value = params.split(';')
        col = col.replace("[", "").replace("]", "").strip().split(",")
        value = value.replace("[", "").replace("]", "").strip().split(",")
        print "add_dbf_file_data"
        print "path:%s, col:%s, value:%s" % (str(path), str(col), str(value))
        new_data = collections.OrderedDict()
        col = [str(i).strip() for i in col]
        value = [str(i).strip() for i in value]
        add_data = collections.OrderedDict(zip(col, value))
        dbf_data = []
        path = path.strip()
        f = open(path, 'rb')
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


def QS_AddStockAsset(param):
    """
    增加股票资产
    Args:
        param: 入参。"serverid,operid_1,operid_2,trdpwd,orgid,fundid,secuid,market,stkcode,count,account_group_id"
    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    """  # 保存一个元组(cmdstring,pre_action,pro_action,account_group_id)列表
    serverid, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count, account_group_id = param.split(
        ',')
    cmdstring_list = []
    cmdstring = "g_serverid=%s#g_operid=%s#g_operpwd=%s#g_operway=4#g_funcid=150402#g_stationaddr=001641AA2350#orgid=%s#fundid=%s#secuid=%s#market=%s#stkcode=%s#stkeffect=%s#cost=10#remark=" % (
        serverid, operid_1, trdpwd, orgid, fundid, secuid, market, stkcode, count)
    pro_action = """[{"content": "sno &equ&save_param([0][0])", "PUBLIC_FUNC_FLAG": 0,"call_when": "normal_call", "type": "General_Operation", "desc": ""}]"""
    cmdstring_list.append((cmdstring, "", pro_action, account_group_id))
    cmdstring = "g_serverid=%s#g_operid=%s#g_operpwd=%s#g_operway=4#g_funcid=150420#g_stationaddr=001641AA2350#operdate=@sys_date@#sno=@sno@#action=1#afmremark=" % (
        serverid, operid_2, trdpwd)
    cmdstring_list.append((cmdstring, "", "", account_group_id))
    ret, msg = RunTest(serverid, cmdstring_list)
    if ret < 0:
        error_msg = u"问题发生: %s" % msg
        Logging.getLog().error(error_msg)
        return ret, (msg,)
    else:
        return 0, ("",)


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


def read_sqlserver_core_config(server_id, system_id):  # 读取配置文件中核心的数量
    homedir = os.getcwd()
    path_str = "%s\\init\\%s\\ZHLCAutoTestSetting_%s.xml" % (homedir, system_id, server_id)
    if os.path.exists(path_str):
        tree = ET.parse(path_str)
        root = tree.getroot()
        SqlServerElem = root.find("ConnectSqlServerSetting")
        for serverElem in SqlServerElem:
            gl.g_connectSqlServerSetting[serverElem.attrib["core"]] = {}
            for elem in serverElem:
                gl.g_connectSqlServerSetting[serverElem.attrib["core"]][elem.tag] = elem.text
                # print elem.text
    else:
        print u'no have this QS xml config'


def traversalDir_XMLFile(system_id):
    # 判断路径是否存在
    homedir = os.getcwd()
    # 得到该文件夹路径下下的所有xml文件路径
    f = glob.glob('%s\\init\\%s\\*.xml' % (homedir, system_id))
    for file in f:
        if file and "ZHLCAutoTestSetting_" in file:
            server_id = file.split("ZHLCAutoTestSetting_")[1].replace(".xml", "")
            try:
                # print int(server_id)
                read_sqlserver_core_config(server_id, system_id)
            except Exception as e:
                pass


def GKRunTest(serverid):
    """
    国开测试原语， 非自动化平台  主要测试是否兼容国开集中交易
    Args:
        running_dir: 运行目录
    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
    """
    group_variable_dict = {}
    hHandle, cli = cF_kcbp.KCBPCliInit(serverid)
    if hHandle < 0:
        return -1, u"初始化KCBPCli接口失败"
    try:
        cmdstring = "funcid=410503#custid=2352007#custorgid=4211#trdpwd=*Sh//+)$#netaddr=0#orgid=4211#operway=7#ext=0#market=1#fundid=2382460#secuid=A557727161#stkcode=601010#qryflag=1#count=10#poststr=1"
        Logging.getLog().debug(cmdstring)
        ret, code, level, msg = cF_kcbp.SendRequest(hHandle, cli, cmdstring)
        print "ret:%s, code:%s, level:%s, msg:%s" % (ret, code, level, msg)
        if ret == 0:
            dataset = []
            if (int(code) != 0):
                dataset.append(["code", "level", "msg"])
                dataset.append([code, level, msg])
            else:
                dataset = cF_kcbp.GetReturnResult(hHandle, cli)
            print "dataset:%s" % dataset
        return 0, ""
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        cF_kcbp.KCBPCliExit(hHandle, cli)
        return -1, exc_info


def executeAccountInit(ds, serverid, ip='', port=''):
    try:
        gl.g_create_account_info = {}
        # num_list = [0, 1, 2, 3]  # 在此控制开户数量
        for num in range(0, 10):
            zhInit.executeAccountInit(num, ds, serverid, ip, port)
            exc_info = u"开始创建账号组%d..." % (num)
        if int(serverid) in [1, 2, 3, 4, 5]:
            rtn = {}
            rtn[str("data")] = {serverid: gl.g_create_account_info, 12: gl.g_create_account_info}
            rtn["system_id"] = gl.current_system_id
            if rtn["data"]:
                GlobalDict.get_value("MQClient")._redis_client.set_account_group_dict("create_account", rtn)
        if int(serverid) in [6, 7, 8, 9, 10]:
            rtn = {}
            rtn[str("data")] = {serverid: gl.g_create_account_info, 13: gl.g_create_account_info}
            rtn["system_id"] = gl.current_system_id
            if rtn["data"]:
                GlobalDict.get_value("MQClient")._redis_client.set_account_group_dict("create_account", rtn)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def test_change_pre():
    data = """"""
    # action_list = data.split("\n")
    # action_list = [i.strip() for i in action_list]
    # VARIABLE, actions = cF.action_update(action_list, {})
    eval("check_expression")("7,7==8")  # check_expression, parameterize:7,7==8


def delete():
    homedir = os.getcwd()
    f = glob.glob('%s\\init\\%s\\*.xml' % (homedir, "142891263425277DZ1_test"))
    for file in f:
        if file and "ZHLCAutoTestSetting" in file:
            os.remove(file)


def DatabasesAuto(param):
    try:
        setting_file = './Script/' + param

        all_config_dict = cF.read_config(setting_file)  # 拿到配置文件
        ret, core_list = cF.deal_core_data(all_config_dict)  # 拿到需要连接的核心号
        # 处理core
        for core in core_list:
            print '--> ', core
            f_str = ''
            cursor = cF.get_conn(all_config_dict[core]['ip'], all_config_dict[core]['db'],
                                 all_config_dict[core]['user'], all_config_dict[core]['passwd'])  # 连接此核心数据库
            if all_config_dict[core]['file']:
                with open('./Script/' + all_config_dict[core]['file'], 'r') as f:
                    f_str = f.read()
            sql_cor_list = re.findall('--START--(.*?)--END--', f_str.replace('\n', '$$$'))
            sql_exec_list = []
            for sql_cor in sql_cor_list:
                sql_exec_list.append(sql_cor.replace('$$$', '\n'))
            for sql in sql_exec_list:
                cF.auto_exec_sql(cursor, sql, core)
            cursor.close()
            # print '--> SQL'
            # print sql
        print u'sql-->ok'

        # 处理ovi
        f_str_ovi = ''
        sql_list = []
        if all_config_dict['oiwfile']:
            with open('./Script/' + all_config_dict['oiwfile'], 'r') as f:
                f_str_ovi = f.read()
        sql_list = cF.ret_sql_list(f_str_ovi)

        core_first_list = all_config_dict['oiwdata'].split(',')
        ovi_data_list = []

        for i in core_first_list:
            i = i.strip()
            ovi_data_list.append(i)

        for sql in sql_list:
            for s in ovi_data_list:
                if s in sql:
                    print s, sql
                    cursor = cF.get_conn(all_config_dict['oiwconfig']['ip'], s, all_config_dict['oiwconfig']['user'],
                                         all_config_dict['oiwconfig']['passwd'])
                    try:
                        cursor.execute(sql)
                        cursor.commit()
                        cursor.close()
                    except Exception as e:
                        Logging.getLog().error(sql)
                        Logging.getLog().error(e.args[1].decode('gb2312'))

        print 'oiw --> ok'
    except Exception as e:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


if __name__ == '__main__':
    # delete()
    # GetNewWorkDate("1,20190527")
    # cF.readSystemConfigFile('1481879345901LDJNJ')
    # AddStockAsset("p, 4211707, 4211708, *Sh // +)$, 4211, 2441339, A214662871, 1, 600012, 100")
    # expression_evaluation("a,0.00-1067.12")
    ###############################################
    #############测试国开集中交易工具##############
    # gl.g_server_id = 1
    # cF.readSystemConfigFile('142891263425277DZ1')
    # GKRunTest("1")
    ###############################################
    ###############################################
    # traversalDir_XMLFile("142891263425277DZ1")
    # get_minfee_commissionrate_info('1,1,1,1,1,1,1,1')
    # expression_evaluation("count,0.105*1")
    # expression_evaluation('test,100*32.09')
    ASSERT_EXPRESSION(
        "[{'\xb3\xc9\xbd\xbb\xbd\xf0\xb6\xee': '0.00', '\xce\xaf\xcd\xd0\xc8\xd5\xc6\xda': 20190501, '\xd6\xa4\xc8\xaf\xc3\xfb\xb3\xc6': u'\u6d66\u53d1\u94f6\u884c', '\xb3\xc9\xbd\xbb\xca\xfd\xc1\xbf': 0L, '\xce\xaf\xcd\xd0\xbc\xdb\xb8\xf1': '17.8400', '\xb3\xb7\xb5\xa5\xca\xfd\xc1\xbf': 0L, '\xce\xaf\xcd\xd0\xca\xfd\xc1\xbf': 1000000L, '\xd6\xa4\xc8\xaf\xb4\xfa\xc2\xeb': u'600000'}]==[{u'证券名称': u'浦发银行', u'委托日期': u'20190501', u'委托价格': u'17.8400', u'委托状态': u'未报', u'成交数量': u'0', u'证券代码': u'600000', u'成交金额': u'0.00', u'撤单数量': u'0', u'冻结金额': u'17883172.80', u'交易类别': u'买成确认', u'委托时间': u'21:34:25.07', u'委托数量': u'1000000'}],compare_list")
    # ASSERT_EXPRESSION(
    #     "[{u'\u8bc1\u5238\u6570\u91cf': u'2200.00', u'\u53ef\u5356\u6570\u91cf': u'2200.00', u'\u8bc1\u5238\u4ee3\u7801': u'600008', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u6570\u91cf': u'500.00', u'\u53ef\u5356\u6570\u91cf': u'500.00', u'\u8bc1\u5238\u4ee3\u7801': u'601088', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u6570\u91cf': u'1200.00', u'\u53ef\u5356\u6570\u91cf': u'1200.00', u'\u8bc1\u5238\u4ee3\u7801': u'600031', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u6570\u91cf': u'500.00', u'\u53ef\u5356\u6570\u91cf': u'500.00', u'\u8bc1\u5238\u4ee3\u7801': u'600030', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u6570\u91cf': u'100000.00', u'\u53ef\u5356\u6570\u91cf': u'100000.00', u'\u8bc1\u5238\u4ee3\u7801': u'150023', u'\u80a1\u4e1c\u4ee3\u7801': u'0030143462'}] == [{u'\u8bc1\u5238\u540d\u79f0': u'\u9996\u521b\u80a1\u4efd', u'\u53c2\u8003\u6210\u672c\u4ef7': u'8.110', u'\u53ef\u5356\u6570\u91cf': u'2200.00', u'\u8bc1\u5238\u6570\u91cf': u'2200.00', u'\u53c2\u8003\u76c8\u4e8f\u6bd4\u4f8b%': u'-52.651', u'\u6700\u65b0\u5e02\u503c': u'8448.00', u'\u5f53\u524d\u4ef7': u'3.8400', u'\u53c2\u8003\u6d6e\u52a8\u76c8\u4e8f': u'-9427.45', u'\u8bc1\u5238\u4ee3\u7801': u'600008', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u540d\u79f0': u'\u4e2d\u4fe1\u8bc1\u5238', u'\u53c2\u8003\u6210\u672c\u4ef7': u'0.000', u'\u53ef\u5356\u6570\u91cf': u'500.00', u'\u8bc1\u5238\u6570\u91cf': u'500.00', u'\u53c2\u8003\u76c8\u4e8f\u6bd4\u4f8b%': u'0.000', u'\u6700\u65b0\u5e02\u503c': u'7755.00', u'\u5f53\u524d\u4ef7': u'15.5100', u'\u53c2\u8003\u6d6e\u52a8\u76c8\u4e8f': u'7724.25', u'\u8bc1\u5238\u4ee3\u7801': u'600030', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u540d\u79f0': u'\u4e09\u4e00\u91cd\u5de5', u'\u53c2\u8003\u6210\u672c\u4ef7': u'11.442', u'\u53ef\u5356\u6570\u91cf': u'1200.00', u'\u8bc1\u5238\u6570\u91cf': u'1200.00', u'\u53c2\u8003\u76c8\u4e8f\u6bd4\u4f8b%': u'-24.489', u'\u6700\u65b0\u5e02\u503c': u'10368.00', u'\u5f53\u524d\u4ef7': u'8.6400', u'\u53c2\u8003\u6d6e\u52a8\u76c8\u4e8f': u'-6890.29', u'\u8bc1\u5238\u4ee3\u7801': u'600031', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u540d\u79f0': u'\u4e2d\u56fd\u795e\u534e', u'\u53c2\u8003\u6210\u672c\u4ef7': u'70.441', u'\u53ef\u5356\u6570\u91cf': u'500.00', u'\u8bc1\u5238\u6570\u91cf': u'500.00', u'\u53c2\u8003\u76c8\u4e8f\u6bd4\u4f8b%': u'-74.248', u'\u6700\u65b0\u5e02\u503c': u'9070.00', u'\u5f53\u524d\u4ef7': u'18.1400', u'\u53c2\u8003\u6d6e\u52a8\u76c8\u4e8f': u'-21577.66', u'\u8bc1\u5238\u4ee3\u7801': u'601088', u'\u80a1\u4e1c\u4ee3\u7801': u'A125975750'}, {u'\u8bc1\u5238\u540d\u79f0': u'\u6df1\u6210\u6307B', u'\u53c2\u8003\u6210\u672c\u4ef7': u'0.000', u'\u53ef\u5356\u6570\u91cf': u'100000.00', u'\u8bc1\u5238\u6570\u91cf': u'100000.00', u'\u53c2\u8003\u76c8\u4e8f\u6bd4\u4f8b%': u'0.000', u'\u6700\u65b0\u5e02\u503c': u'15800.00', u'\u5f53\u524d\u4ef7': u'0.1580', u'\u53c2\u8003\u6d6e\u52a8\u76c8\u4e8f': u'15752.10', u'\u8bc1\u5238\u4ee3\u7801': u'150023', u'\u80a1\u4e1c\u4ee3\u7801': u'0030143462'}]")
    # addDbfFileData('10.187.96.109;D:\\test.dbf; [YMTH, YMTZT, KHRQ, XHRQ, KHFS]; [180000000023213, 213131321, 1231231, 12313, 131213]')
    # addDbfFileData('10.187.96.109; D:\\ABOSS2\\SSKH\\MN\\qtzhzl.dbf;[YMTH, YMTZT, ZHLB, ZQZH, ZQZHZT, KHFS, KHRQ, GLGXBS, BYZD];[180000001299, 0, 11, A000004731, 04, 0, 20180910, 1, ]')
    # cF.readConfigFile()
    # expression_evaluation("count,0.00-11.2100*100-5-0.02-0.1")
    # param = "860003851235,20081"
    # on_the_business(param)
    # cF.readConfigFile()
    # update_account_info(1)
    # GetParamValue('ccccc')
    # cF.readConfigFile()
    # combine_business_item("支付密码修改,小青")
    # if len(sys.argv) < 2:
    #     print "this command need at least two argument"
    #     sys.exit(1)
    # else:
    #     func = sys.argv[1]
    #     argv_list = sys.argv
    #     argv_list.pop(0)
    #     argv_list.pop(0)
    #     argv_string = ','.join(argv_list)
    #     if argv_string == "":
    #         exec( 'ret,msg = %s()' %func)
    #     else:
    #         func_call = 'ret,msg = %s("%s")' %(func,argv_string)
    #         print func_call
    #         exec(func_call)
    #     print u"return = %s,msg=%s" %(str(ret),msg)

    # ###############################################
    # config_name = 'TestAgent.ini'
    # if getattr(sys, 'frozen', False):
    #     application_path = os.path.dirname(sys.executable)
    # elif __file__:
    #     application_path = os.path.dirname(__file__)
    # config_path = os.path.join(application_path, config_name)
    # setting_string = open(config_path, "r").read()
    # try:
    #     mqclient_setting = json.loads(setting_string)
    # except:
    #     mqclient_setting = eval(setting_string)
    # mqclient = MQClient.MQClient(mqclient_setting)
    # create_account(2, "233dfkf", "0,1")
    # print "leave: create_account\n"
    # gl.is_exit_all_thread = True
    # mqclient.close_all()
    # print "mqclient close\n"
    # Logging.getLog().debug("mqclient close")
