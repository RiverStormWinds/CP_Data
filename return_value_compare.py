# -*- coding: gbk -*-
import gl
import commFuncs as cF
import json
from gl import GlobalLogging as Logging
from collections import OrderedDict
import scanOracleDB
import difflib



def compare_two_return_value(left, right):
    try:
        left_field_list = left["field"]
        right_field_list = right["field"]
        ret, new_left_field_list, new_right_field_list, field_juage_list = scanOracleDB.CompareTwoList(
            left_field_list, right_field_list)
        if ret < 0:
            return ret, new_left_field_list
        
        left_list = []
        right_list = []
        
        left_compare = left["values_list"]
        right_compare = right["values_list"]
        


        if 0 in field_juage_list:  # 存在差异,需要调整字段值后进行对比
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
        
        ret, new_left_list, new_right_list, juage_list = scanOracleDB.CompareTwoList(
            left_list,
            right_list)
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
                # fix 相同的行就丢掉
                continue
                # left_result_dict["value_list"].append(new_left_list[idx].split(','))
                # right_result_dict["value_list"].append(new_right_list[idx].split(','))
                #
                # diff_flag_list = []
                # for i in xrange(len(new_left_list[idx].split(','))):
                #     diff_flag_list.append(1)
                # diff_flag_dict["value_list_flag"].append(diff_flag_list)
            else:
                l = new_left_list[idx].split(',')
                r = new_right_list[idx].split(',')
                max_len = max(len(l), len(r))
                if len(l) < max_len:  # 考虑空行的情况
                    l = []
                    for i in xrange(max_len):
                        l.append("")
                if len(r) < max_len:  # 考虑空行的情况
                    r = []
                    for i in xrange(max_len):
                        r.append("")
                left_result_dict["value_list"].append(l)
                right_result_dict["value_list"].append(r)
                
                diff_flag_list = []
                
                # 考虑空列得情况
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

def compare_two_task_return_value(run_task_id_1, run_task_id_2):
    """
    :param run_task_id_1:
    :param run_task_id_2:
    :return:
    """
    try:
        left_dict = OrderedDict()
        right_dict = OrderedDict()
        
        data_compare_dict = OrderedDict()
        
        sql = "select cases_id,cases_detail_id,cases_param_data_id,return_detail_message from sx_run_record where task_id = %s and return_detail_message !=''" % str(
            run_task_id_1)
        ds_left = cF.executeCaseSQL(sql)
        for rec in ds_left:
            left_dict[
                "%s_%s_%s" % (str(rec["cases_id"]), str(rec["cases_detail_id"]),
                              str(rec["cases_param_data_id"]))] = json.loads(rec["return_detail_message"])
        
        sql = "select cases_id,cases_detail_id,cases_param_data_id,return_detail_message from sx_run_record where task_id = %s and return_detail_message !=''" % str(
            run_task_id_2)
        ds_right = cF.executeCaseSQL(sql)
        for rec in ds_right:
            right_dict[
                "%s_%s_%s" % (str(rec["cases_id"]), str(rec["cases_detail_id"]),
                              str(rec["cases_param_data_id"]))] = json.loads(rec["return_detail_message"])
        
        for item in left_dict.keys():
            if item in right_dict.keys():
                # both

                ret, left_result_dict, right_result_dict, diff_flag_dict = compare_two_return_value(
                    left_dict[item], right_dict[item])
                if ret < 0:
                    return ret, left_result_dict
                
                # if len(juage_list) == 0: #如果都相等，就忽略
                #     continue
                if ret == 0 and left_result_dict == None:
                    right_dict.pop(item)
                    continue
                
                if not data_compare_dict.has_key('both'):  # 两边都运行了同样的用例
                    data_compare_dict['both'] = OrderedDict()
                if not data_compare_dict['both'].has_key(item):
                    data_compare_dict['both'][item] = OrderedDict()
                data_compare_dict['both'][item]["left"] = left_result_dict
                data_compare_dict['both'][item]["right"] = right_result_dict
                data_compare_dict['both'][item]["diff_flag"] =diff_flag_dict
                
                right_dict.pop(item)
            
            else:
                if not data_compare_dict.has_key('left_only'):
                    data_compare_dict['left_only'] = OrderedDict()
                if not data_compare_dict['left_only'].has_key(item):
                    data_compare_dict['left_only'][item] = OrderedDict()
                data_compare_dict['left_only'][item] = left_dict[item]
        
        for item in right_dict.keys():
            if not data_compare_dict.has_key('right_only'):
                data_compare_dict['right_only'] = OrderedDict()
            data_compare_dict['right_only'][item] = right_dict[item]
        # gl.threadQueue.put((0, "", "compare_two_task_return_value"))
        
        # str_data_compare_dict = json.dumps(data_compare_dict,
        #                                    ensure_ascii=False, indent=True)
        # sql = "delete  from sx_run_task_data_compare where left_run_task_id=%d and right_run_task_id=%d" % (
        #     run_task_id_1, run_task_id_2)
        # cF.executeCaseSQL(sql)
        # sql = "insert into sx_run_task_data_compare (left_run_task_id,right_run_task_id,compare_result_info) values (%d,%d,'%s')" % (
        #     run_task_id_1, run_task_id_2, str_data_compare_dict)
        # cF.executeCaseSQL(sql)
        return 0, data_compare_dict
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        # gl.threadQueue.put((-1, exc_info, "compare_two_task_return_value"))
        return -1, exc_info, "", ""
    pass

