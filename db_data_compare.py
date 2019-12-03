# -*- coding: gbk -*-
import gl
import commFuncs as cF
import json
from gl import GlobalLogging as Logging
from collections import OrderedDict
import scanOracleDB
import difflib
import return_value_compare

"""
���ļ������û����ݿ�䶯�Աȵ���ش���
"""


def process_disable_column(db_id, schema, tablename, result_dict):
    '''
    �����ݽ����ı����ݣ�����disableflag��������������޳���������Ƚ�
    :param db_id:
    :param schema:
    :param tablename:
    :param result_dict:
    :param model:
    :return:
    '''
    try:
        table_column_disable_info = scanOracleDB.getTableColumnInfo()
        # if gl.g_table_column_disable_info == OrderedDict():
        #     scanOracleDB.getTableColumnInfo()

        remove_index_list = []
        field_list = result_dict["field"]
        if table_column_disable_info[db_id][schema][tablename]["disableflag"] == 1:  # ����ñ�����
            return 0, {}
        for idx, column in enumerate(table_column_disable_info[db_id][schema][tablename]["column_list"].keys()):
            if table_column_disable_info[db_id][schema][tablename]["column_list"][column]["disableflag"] == 1:
                remove_index_list.append(idx)

        # ɾ����ʱ������ֵ�Ӵ�Сɾ����

        # �Ӵ�С����
        remove_index_list.sort(reverse=True)
        for idx in remove_index_list:
            result_dict["field"].pop(idx)
            if result_dict.has_key('add'):
                for row in result_dict["add"]:
                    row.pop(idx)
            if result_dict.has_key('del'):
                for row in result_dict["del"]:
                    row.pop(idx)
            if result_dict.has_key('update'):
                for row in result_dict["update"]["old"]:
                    row.pop(idx)
                for row in result_dict["update"]["new"]:
                    row.pop(idx)
                for row in result_dict["update"]["diff_flag"]:
                    row.pop(idx)
        return 0, result_dict


    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def CompareTwoTableInfo(left, right, model):
    try:
        left_field_list = left["field"]
        right_field_list = right["field"]
        ret, new_left_field_list, new_right_field_list, field_juage_list = scanOracleDB.CompareTwoList(left_field_list,
                                                                                                       right_field_list)
        if ret < 0:
            return ret, new_left_field_list

        left_list = []
        right_list = []

        left_compare = None
        right_compare = None

        if model == 'update':
            left_compare = left[model]['new']
            right_compare = right[model]['new']
        else:
            left_compare = left[model]
            right_compare = right[model]
        if 0 in field_juage_list:  # ���ڲ���,��Ҫ�����ֶ�ֵ����жԱ�
            left_line = []
            for line in left_compare:
                for idx, field in enumerate(new_left_field_list):
                    if field == '':
                        left_line.append('')
                    else:
                        left_line.append(line.pop(0))
                left_list.append(",".join(left_line))

            right_line = []
            for line in right_compare:
                for idx, field in enumerate(new_right_field_list):
                    if field == '':
                        right_line.append('')
                    else:
                        right_line.append(line.pop(0))
                right_list.append(",".join(right_line))
        else:
            for line in left_compare:
                left_list.append(",".join(line))

            for line in right_compare:
                right_list.append(",".join(line))

        ret, new_left_list, new_right_list, juage_list = scanOracleDB.CompareTwoList(left_list, right_list)
        if ret < 0:
            return ret, new_left_list

        if not 0 in juage_list:
            return 0, None, None, None

        # fixme maybe remove if all the same
        left_result_dict = OrderedDict()
        right_result_dict = OrderedDict()
        diff_flag_dict = OrderedDict()
        left_result_dict["field"] = new_left_field_list
        right_result_dict["field"] = new_right_field_list
        diff_flag_dict["field_flag"] = field_juage_list

        left_result_dict["value_list"] = []
        right_result_dict["value_list"] = []
        diff_flag_dict["value_list_flag"] = []

        for idx, value in enumerate(juage_list):
            if value == 1:
                # fix ��ͬ���оͶ���
                continue

            else:
                l = new_left_list[idx].split(',')
                r = new_right_list[idx].split(',')
                max_len = max(len(l), len(r))
                if len(l) < max_len:  # ���ǿ��е����
                    l = []
                    for i in xrange(max_len):
                        l.append("")
                if len(r) < max_len:  # ���ǿ��е����
                    r = []
                    for i in xrange(max_len):
                        r.append("")
                left_result_dict["value_list"].append(l)
                right_result_dict["value_list"].append(r)

                diff_flag_list = []

                # ���ǿ��е����
                for i in xrange(max_len):
                    if l[i] == r[i]:
                        diff_flag_list.append(1)
                    else:
                        diff_flag_list.append(0)
                diff_flag_dict["value_list_flag"].append(diff_flag_list)
        return 0, left_result_dict, right_result_dict, diff_flag_dict
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def compare_two_data_change_info(left, right):
    """
    �Ƚ���������ִ�к�����ݿ�䶯
    :param left:
    :param right:
    :return:
    """
    try:
        left_dict = json.loads(left)
        right_dict = json.loads(right)

        data_change_dict = OrderedDict()

        '''
        �������ı䶯��¼������Ҳ�Ҳ��ͬ���ı䶯��Ϣ.
        �����㷨��
            1.���Ϊһ���������е��µ����ݿ�䶯�����ܰ������ɸ����ݿ�����ɸ�schema�������ű�ÿ�ű�ı䶯��ʽ���������޸ĺ�ɾ�������֣�������Ҫ�ֱ���бȽϣ�
            2.�ȴ����䶯��ʼ���������鿴���Ҳ��Ƿ����ͬһ�ű���������޸ĺ͸��£�����оͶ�Ӧ�Ƚϱ䶯��ֵ��
            3.���������Ҳ�û�У��ͷ����Ӧ��left���ͣ�����У��ͷ���differ���ͣ����ҽ����Ƚϵ����ݴ��Ҳ��޳���
            4.������ʣ�µ��Ҳ����ݣ�������еĻ���������right����
            
        '''
        for dbid in left_dict["data_change_info"].keys():
            if dbid in right_dict["data_change_info"].keys():
                for schema in left_dict["data_change_info"][dbid].keys():
                    if schema in right_dict["data_change_info"][dbid].keys():
                        for tablename in left_dict["data_change_info"][dbid][schema].keys():
                            if tablename in right_dict["data_change_info"][dbid][schema].keys():
                                ret, left_strip_dict = process_disable_column(int(dbid), schema, tablename,
                                                                              left_dict["data_change_info"][dbid][
                                                                                  schema][tablename])
                                if ret < 0:
                                    return ret, left_strip_dict
                                if left_strip_dict == {}:  # fixme
                                    right_dict["data_change_info"][dbid][schema].pop(tablename)  # ���ű��ñȽ���
                                    continue

                                ret, right_strip_dict = process_disable_column(int(dbid), schema, tablename,
                                                                               right_dict["data_change_info"][dbid][
                                                                                   schema][tablename])
                                if ret < 0:
                                    return ret, right_strip_dict
                                if right_strip_dict == {}:
                                    right_dict["data_change_info"][dbid][schema].pop(tablename)  # ���ű��ñȽ���
                                    continue

                                if "add" in left_dict["data_change_info"][dbid][schema][tablename].keys():
                                    if "add" in right_dict["data_change_info"][dbid][schema][tablename].keys():
                                        ret, left_result_dict, right_result_dict, diff_flag_dict = CompareTwoTableInfo(
                                            left_strip_dict, right_strip_dict, "add")
                                        if ret < 0:
                                            return ret, left_result_dict

                                        if left_result_dict == None:  # ˵����ȫ���
                                            right_dict["data_change_info"][dbid][schema][tablename].pop('add')
                                        else:

                                            if not data_change_dict.has_key("differ"):
                                                data_change_dict['differ'] = OrderedDict()
                                            if not data_change_dict['differ'].has_key(dbid):
                                                data_change_dict['differ'][dbid] = OrderedDict()
                                            if not data_change_dict['differ'][dbid].has_key(schema):
                                                data_change_dict['differ'][dbid][schema] = OrderedDict()
                                            if not data_change_dict['differ'][dbid][schema].has_key(tablename):
                                                data_change_dict['differ'][dbid][schema][tablename] = OrderedDict()

                                            data_change_dict['differ'][dbid][schema][tablename]["dbid"] = dbid
                                            data_change_dict['differ'][dbid][schema][tablename]["schema"] = schema
                                            data_change_dict['differ'][dbid][schema][tablename]["tablename"] = tablename
                                            data_change_dict['differ'][dbid][schema][tablename]["add"] = OrderedDict()
                                            data_change_dict['differ'][dbid][schema][tablename]["add"][
                                                "left"] = left_result_dict
                                            data_change_dict['differ'][dbid][schema][tablename]["add"][
                                                "right"] = right_result_dict
                                            data_change_dict['differ'][dbid][schema][tablename]["add"][
                                                "diff_flag"] = diff_flag_dict

                                            right_dict["data_change_info"][dbid][schema][tablename].pop('add')
                                    else:
                                        if not data_change_dict.has_key("left"):
                                            data_change_dict['left'] = OrderedDict()
                                        if not data_change_dict['left'].has_key(dbid):
                                            data_change_dict['left'][dbid] = OrderedDict()
                                        if not data_change_dict['left'][dbid].has_key(schema):
                                            data_change_dict['left'][dbid][schema] = OrderedDict()
                                        if not data_change_dict['left'][dbid][schema].has_key(tablename):
                                            data_change_dict['left'][dbid][schema][tablename] = OrderedDict()
                                        data_change_dict['left'][dbid][schema][tablename]["dbid"] = dbid
                                        data_change_dict['left'][dbid][schema][tablename]["schema"] = schema
                                        data_change_dict['left'][dbid][schema][tablename]["tablename"] = tablename
                                        data_change_dict['left'][dbid][schema][tablename]["field"] = \
                                            left_dict["data_change_info"][dbid][schema][tablename]["field"]
                                        data_change_dict['left'][dbid][schema][tablename]["add"] = \
                                            left_dict["data_change_info"][dbid][schema][tablename]["add"]

                                if "update" in left_dict["data_change_info"][dbid][schema][tablename].keys():
                                    if "update" in right_dict["data_change_info"][dbid][schema][tablename].keys():
                                        ret, left_result_dict, right_result_dict, diff_flag_dict = CompareTwoTableInfo(
                                            left_strip_dict, right_strip_dict, "update")
                                        if ret < 0:
                                            return ret, left_result_dict
                                        if left_result_dict == None:  # ˵����ȫ���
                                            right_dict["data_change_info"][dbid][schema][tablename].pop('update')
                                        else:

                                            if not data_change_dict.has_key("differ"):
                                                data_change_dict['differ'] = OrderedDict()
                                            if not data_change_dict['differ'].has_key(dbid):
                                                data_change_dict['differ'][dbid] = OrderedDict()
                                            if not data_change_dict['differ'][dbid].has_key(schema):
                                                data_change_dict['differ'][dbid][schema] = OrderedDict()
                                            if not data_change_dict['differ'][dbid][schema].has_key(tablename):
                                                data_change_dict['differ'][dbid][schema][tablename] = OrderedDict()

                                            data_change_dict['differ'][dbid][schema][tablename]["dbid"] = dbid
                                            data_change_dict['differ'][dbid][schema][tablename]["schema"] = schema
                                            data_change_dict['differ'][dbid][schema][tablename]["tablename"] = tablename
                                            data_change_dict['differ'][dbid][schema][tablename][
                                                "update"] = OrderedDict()
                                            data_change_dict['differ'][dbid][schema][tablename]["update"][
                                                "left"] = left_result_dict
                                            data_change_dict['differ'][dbid][schema][tablename]["update"][
                                                "right"] = right_result_dict
                                            data_change_dict['differ'][dbid][schema][tablename]["update"][
                                                "diff_flag"] = diff_flag_dict

                                            right_dict["data_change_info"][dbid][schema][tablename].pop('update')

                                    else:
                                        if not data_change_dict.has_key("left"):
                                            data_change_dict[
                                                'left'] = OrderedDict()
                                        if not data_change_dict['left'].has_key(
                                                dbid):
                                            data_change_dict['left'][
                                                dbid] = OrderedDict()
                                        if not data_change_dict['left'][
                                            dbid].has_key(schema):
                                            data_change_dict['left'][dbid][
                                                schema] = OrderedDict()
                                        if not data_change_dict['left'][dbid][
                                            schema].has_key(tablename):
                                            data_change_dict['left'][dbid][
                                                schema][
                                                tablename] = OrderedDict()
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["dbid"] = dbid
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["schema"] = schema
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["tablename"] = tablename
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["field"] = \
                                            left_dict["data_change_info"][dbid][
                                                schema][tablename]["field"]
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["update"] = \
                                            left_dict["data_change_info"][dbid][
                                                schema][tablename]["update"]

                                if "del" in left_dict["data_change_info"][dbid][
                                    schema][tablename].keys():
                                    if "del" in right_dict["data_change_info"][
                                        dbid][schema][tablename].keys():
                                        ret, left_result_dict, right_result_dict, diff_flag_dict = CompareTwoTableInfo(
                                            left_strip_dict, right_strip_dict, "del")
                                        if ret < 0:
                                            return ret, left_result_dict
                                        if left_result_dict == None:  # ˵����ȫ���
                                            right_dict["data_change_info"][dbid][schema][tablename].pop('del')
                                        else:
                                            if not data_change_dict.has_key(
                                                    "differ"):
                                                data_change_dict[
                                                    'differ'] = OrderedDict()
                                            if not data_change_dict[
                                                'differ'].has_key(dbid):
                                                data_change_dict['differ'][
                                                    dbid] = OrderedDict()
                                            if not data_change_dict['differ'][
                                                dbid].has_key(schema):
                                                data_change_dict['differ'][dbid][
                                                    schema] = OrderedDict()
                                            if not data_change_dict['differ'][dbid][
                                                schema].has_key(tablename):
                                                data_change_dict['differ'][dbid][
                                                    schema][
                                                    tablename] = OrderedDict()
                                            data_change_dict['differ'][dbid][
                                                schema][tablename]["dbid"] = dbid
                                            data_change_dict['differ'][dbid][
                                                schema][tablename][
                                                "schema"] = schema
                                            data_change_dict['differ'][dbid][
                                                schema][tablename][
                                                "tablename"] = tablename
                                            data_change_dict['differ'][dbid][
                                                schema][tablename][
                                                "del"] = OrderedDict()
                                            data_change_dict['differ'][dbid][
                                                schema][tablename]["del"][
                                                "left"] = left_result_dict
                                            data_change_dict['differ'][dbid][
                                                schema][tablename]["del"][
                                                "right"] = right_result_dict
                                            data_change_dict['differ'][dbid][
                                                schema][tablename]["del"][
                                                "diff_flag"] = diff_flag_dict

                                            right_dict["data_change_info"][dbid][
                                                schema][tablename].pop('del')
                                    else:
                                        if not data_change_dict.has_key("left"):
                                            data_change_dict[
                                                'left'] = OrderedDict()
                                        if not data_change_dict['left'].has_key(
                                                dbid):
                                            data_change_dict['left'][
                                                dbid] = OrderedDict()
                                        if not data_change_dict['left'][
                                            dbid].has_key(schema):
                                            data_change_dict['left'][dbid][
                                                schema] = OrderedDict()
                                        if not data_change_dict['left'][dbid][
                                            schema].has_key(tablename):
                                            data_change_dict['left'][dbid][
                                                schema][
                                                tablename] = OrderedDict()
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["dbid"] = dbid
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["schema"] = schema
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["tablename"] = tablename
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["field"] = \
                                            left_dict["data_change_info"][dbid][
                                                schema][tablename]["field"]
                                        data_change_dict['left'][dbid][schema][
                                            tablename]["del"] = \
                                            left_dict["data_change_info"][dbid][
                                                schema][tablename]["del"]

                                # right_dict["data_change_info"][dbid][schema].pop(tablename)
                                # �����Ƿ���ʣ�������Ҳ������
                                if "add" in right_dict["data_change_info"][dbid][schema][tablename].keys():
                                    if not data_change_dict.has_key("right"):
                                        data_change_dict['right'] = OrderedDict()
                                    if not data_change_dict['right'].has_key(dbid):
                                        data_change_dict['right'][dbid] = OrderedDict()
                                    if not data_change_dict['right'][dbid].has_key(schema):
                                        data_change_dict['right'][dbid][schema] = OrderedDict()
                                    if not data_change_dict['right'][dbid][schema].has_key(tablename):
                                        data_change_dict['right'][dbid][schema][tablename] = OrderedDict()

                                    data_change_dict['right'][dbid][schema][tablename]["dbid"] = dbid
                                    data_change_dict['right'][dbid][schema][tablename]["schema"] = schema
                                    data_change_dict['right'][dbid][schema][tablename]["tablename"] = tablename
                                    data_change_dict['right'][dbid][schema][tablename]["field"] = \
                                        right_dict["data_change_info"][dbid][schema][tablename]["field"]
                                    data_change_dict['right'][dbid][schema][tablename]["add"] = \
                                        right_dict["data_change_info"][dbid][schema][tablename]["add"]

                                if "update" in right_dict["data_change_info"][dbid][schema][tablename].keys():
                                    if not data_change_dict.has_key("right"):
                                        data_change_dict['right'] = OrderedDict()
                                    if not data_change_dict['right'].has_key(dbid):
                                        data_change_dict['right'][dbid] = OrderedDict()
                                    if not data_change_dict['right'][dbid].has_key(schema):
                                        data_change_dict['right'][dbid][schema] = OrderedDict()
                                    if not data_change_dict['right'][dbid][schema].has_key(tablename):
                                        data_change_dict['right'][dbid][schema][tablename] = OrderedDict()
                                    data_change_dict['right'][dbid][schema][tablename]["dbid"] = dbid
                                    data_change_dict['right'][dbid][schema][tablename]["schema"] = schema
                                    data_change_dict['right'][dbid][schema][tablename]["tablename"] = tablename
                                    data_change_dict['right'][dbid][schema][tablename]["field"] = \
                                        right_dict["data_change_info"][dbid][schema][tablename]["field"]
                                    data_change_dict['right'][dbid][schema][tablename]["update"] = \
                                        right_dict["data_change_info"][dbid][schema][tablename]["update"]
                                if "del" in right_dict["data_change_info"][dbid][schema][tablename].keys():
                                    if not data_change_dict.has_key("right"): data_change_dict['right'] = OrderedDict()
                                    if not data_change_dict['right'].has_key(dbid):
                                        data_change_dict['right'][dbid] = OrderedDict()
                                    if not data_change_dict['right'][
                                        dbid].has_key(schema):
                                        data_change_dict['right'][dbid][
                                            schema] = OrderedDict()
                                    if not data_change_dict['right'][dbid][
                                        schema].has_key(tablename):
                                        data_change_dict['right'][dbid][schema][
                                            tablename] = OrderedDict()
                                    data_change_dict['right'][dbid][schema][
                                        tablename]["dbid"] = dbid
                                    data_change_dict['right'][dbid][schema][
                                        tablename]["schema"] = schema
                                    data_change_dict['right'][dbid][schema][
                                        tablename]["tablename"] = tablename
                                    data_change_dict['right'][dbid][schema][
                                        tablename]["field"] = \
                                        right_dict["data_change_info"][dbid][
                                            schema][tablename]["field"]
                                    data_change_dict['right'][dbid][schema][
                                        tablename]["del"] = \
                                        right_dict["data_change_info"][dbid][
                                            schema][tablename]["del"]
                                right_dict["data_change_info"][dbid][schema].pop(tablename)
                            else:
                                if not data_change_dict.has_key("left"):
                                    data_change_dict['left'] = OrderedDict()
                                if not data_change_dict['left'].has_key(dbid):
                                    data_change_dict['left'][dbid] = OrderedDict()
                                if not data_change_dict['left'][dbid].has_key(schema):
                                    data_change_dict['left'][dbid][schema] = OrderedDict()
                                    data_change_dict['left'][dbid][schema][tablename] = \
                                        left_dict["data_change_info"][dbid][schema][tablename]

                        # �鿴�Ҳ��Ƿ���û�б�����ı�
                        for tablename in right_dict["data_change_info"][dbid][schema].keys():
                            if not data_change_dict.has_key("right"):
                                data_change_dict['right'] = OrderedDict()
                            if not data_change_dict['right'].has_key(dbid):
                                data_change_dict['right'][dbid] = OrderedDict()
                            if not data_change_dict['right'][dbid].has_key(schema):
                                data_change_dict['right'][dbid][schema] = OrderedDict()
                                data_change_dict['right'][dbid][schema][tablename] = \
                                    right_dict["data_change_info"][dbid][schema][tablename]
                        right_dict["data_change_info"][dbid].pop(schema)
                    else:
                        if not data_change_dict.has_key("left"):
                            data_change_dict['left'] = OrderedDict()
                        if not data_change_dict['left'].has_key(dbid):
                            data_change_dict['left'][dbid] = OrderedDict()
                        data_change_dict['left'][dbid][schema] = left_dict["data_change_info"][dbid][schema]
                for schema in right_dict["data_change_info"][dbid].keys():
                    if not data_change_dict.has_key("right"):
                        data_change_dict['right'] = OrderedDict()
                    if not data_change_dict['right'].has_key(dbid):
                        data_change_dict['right'][dbid] = OrderedDict()
                    data_change_dict['right'][dbid][schema] = right_dict["data_change_info"][dbid][schema]
                right_dict["data_change_info"].pop(dbid)
            else:
                if not data_change_dict.has_key("left"):
                    data_change_dict["left"] = OrderedDict()
                if not data_change_dict['left'].has_key(dbid):
                    data_change_dict['left'][dbid] = OrderedDict()
                data_change_dict["left"][dbid] = left_dict["data_change_info"][dbid]
        for dbid in right_dict["data_change_info"].keys():
            if not data_change_dict.has_key('right'):
                data_change_dict['right'] = OrderedDict()
            data_change_dict["right"][dbid] = right_dict["data_change_info"][dbid]

        return 0, data_change_dict
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def compare_two_run_task_db_data_change(run_task_id_1, run_task_id_2):
    """
    �Ƚ�������������֮������ݱ䶯���������ݶԱȽ��
    :param run_task_id_1:
    :param run_task_id_2:
    :return:
    """
    try:
        left_dict = OrderedDict()
        right_dict = OrderedDict()

        db_data_compare_dict = OrderedDict()

        sql = "select cases_id,cases_detail_id,cases_param_data_id,data_change_info from sx_run_record where task_id = %s and data_change_info !=''" % str(
            run_task_id_1)
        ds_left = cF.executeCaseSQL(sql)
        for rec in ds_left:
            left_dict[
                "%s_%s_%s" % (str(rec["cases_id"]), str(rec["cases_detail_id"]), str(rec["cases_param_data_id"]))] = \
                rec["data_change_info"]

        sql = "select cases_id,cases_detail_id,cases_param_data_id,data_change_info from sx_run_record where task_id = %s and data_change_info !=''" % str(
            run_task_id_2)
        ds_right = cF.executeCaseSQL(sql)
        for rec in ds_right:
            right_dict["%s_%s_%s" % (
                str(rec["cases_id"]), str(rec["cases_detail_id"]),
                str(rec["cases_param_data_id"]))] = rec["data_change_info"]

        for item in left_dict.keys():
            if item in right_dict.keys():
                # both
                if not db_data_compare_dict.has_key('both'):  # ���߶�������ͬ��������
                    db_data_compare_dict['both'] = OrderedDict()
                if not db_data_compare_dict['both'].has_key(item):
                    db_data_compare_dict['both'][item] = OrderedDict()
                ret, data_change_dict = compare_two_data_change_info(left_dict[item], right_dict[item])
                if ret < 0:
                    return ret, data_change_dict
                db_data_compare_dict['both'][item] = data_change_dict

                right_dict.pop(item)

            else:
                if not db_data_compare_dict.has_key('left_only'):
                    db_data_compare_dict['left_only'] = OrderedDict()

                if not db_data_compare_dict['left_only'].has_key(item):
                    db_data_compare_dict['left_only'][item] = OrderedDict()

                db_data_compare_dict['left_only'][item] = json.loads(left_dict[item])["data_change_info"]

        for item in right_dict.keys():
            if not db_data_compare_dict.has_key('right_only'):
                db_data_compare_dict['right_only'] = OrderedDict()

            db_data_compare_dict['right_only'][item] = json.loads(right_dict[item])["data_change_info"]

        return 0, db_data_compare_dict
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        # gl.threadQueue.put((-1, exc_info, "compare_two_run_task_db_data_change"))
        return -1, exc_info, "", ""
    pass


def compare_two_task_data_change(run_task_id_1, run_task_id_2):
    try:
        compare_result_info_dict = OrderedDict()

        ret, db_data_compare_dict = compare_two_run_task_db_data_change(run_task_id_1, run_task_id_2)
        if ret < 0:
            return ret, db_data_compare_dict
        ret, return_compare_dict = return_value_compare.compare_two_task_return_value(run_task_id_1, run_task_id_2)
        if ret < 0:
            return ret, return_compare_dict

        compare_result_info_dict["return"] = return_compare_dict
        compare_result_info_dict["data_change_info"] = db_data_compare_dict

        sql = "replace into sx_run_task_data_compare (left_run_task_id,right_run_task_id,compare_result_info) values(%s,%s,'%s')" % (
            run_task_id_1, run_task_id_2, json.dumps(compare_result_info_dict, ensure_ascii=False, indent=4))
        cF.executeCaseSQL(sql)
        gl.threadQueue.put((0, "", "compare_two_task_data_change"))
        return 0, ""
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        gl.threadQueue.put((-1, exc_info, "compare_two_task_data_change"))
        return -1, exc_info, "", ""


if __name__ == "__main__":
    compare_two_task_data_change(1, 2)
