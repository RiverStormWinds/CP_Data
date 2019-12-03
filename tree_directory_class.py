# -*- coding:gbk -*-
import commFuncs as cF
from collections import OrderedDict
import json
import gl
from gl import GlobalLogging as Logging


class tree_directory_class():
    def __init__(self):
        self._tree_directory_dict = OrderedDict()
        self._gnd_dict = json.loads(open("settings.json", 'r').read())

        sql = "select tree_directory_id, directory_name,parent_id,system_id from sx_func_tree_directory"
        ds = cF.executeCaseSQL(sql)
        for rec in ds:
            value_dict = OrderedDict()
            value_dict["directory_name"] = rec["DIRECTORY_NAME"]
            value_dict["parent_id"] = rec["PARENT_ID"]
            id = str(rec["TREE_DIRECTORY_ID"])
            self._tree_directory_dict[id] = value_dict

    def update(self):
        self._tree_directory_dict.clear()
        sql = "select tree_directory_id, directory_name,parent_id,system_id from sx_func_tree_directory"
        ds = cF.executeCaseSQL(sql)

        for rec in ds:
            value_dict = OrderedDict()
            value_dict["directory_name"] = rec["DIRECTORY_NAME"]
            value_dict["parent_id"] = rec["PARENT_ID"]
            self._tree_directory_dict[rec["TREE_DIRECTORY_ID"]] = value_dict

    def get_func_string_according_id(self, id):
        '''
        在上海证券大智慧项目中使用，根据id来查找功能点的目录串
        :param id: 目录ID
        :return: 路径组合，用减号连接
        '''
        func_string = ""
        id = str(id)
        if self._tree_directory_dict.has_key(id):
            while True:

                if str(self._tree_directory_dict[id]['parent_id']) == '0':
                    break
                if func_string == "":
                    func_string = self._tree_directory_dict[id]["directory_name"]
                else:
                    func_string = "%s-%s" % (self._tree_directory_dict[id]["directory_name"], func_string)

                id = str(self._tree_directory_dict[id]["parent_id"])

        return 0,func_string

    def get_GND_param_from_func_string(self, func_string):
        if self._gnd_dict[u"DZH"]["interface-mapping"].has_key(func_string):
            return 0,self._gnd_dict[u"DZH"]["interface-mapping"][func_string]
        else:
            Logging.getLog().error('fail to find GND number from %s' % func_string)
            return -1,'fail to find GND number from %s' % func_string

    def pre_process_test_case(self, case):
        '''
        modify cmdstring on-line before send to the agent
        :param case:
        :return:
        '''
        # case_id =
        try:
            tree_directory_id = ''
            case_id = case["CASES_ID"]
            sql = "SELECT TREE_DIRECTORY_ID FROM SX_CASES WHERE CASES_ID ='%s'" %str(case_id)
            ds = cF.executeCaseSQL(sql)
            if len(ds)>0:
                tree_directory_id = str(ds[0]["TREE_DIRECTORY_ID"])
            else:
                Logging.getLog().error("fail to find the tree_directory_id according cases_id(%s)" %str(case_id))
                return -1, case

            ret, func_string = self.get_func_string_according_id(tree_directory_id)
            if ret < 0:
                return ret,func_string

            ret, GND_string = self.get_GND_param_from_func_string(func_string)
            if ret < 0:
                Logging.getLog().error(GND_string)
                return ret,GND_string
            Logging.getLog().debug("begin to process %s" %case["CMDSTRING"])
            cmdstring = case["CMDSTRING"]
            cmd_list= cmdstring.split('#')
            user = cmd_list[0].split('=')[1]
            pwd = cmd_list[1].split('=')[1]

            func_string_list = func_string.split('-')

            cmdstring = "GND00 %s %s %s %s " %(func_string_list[0],user,pwd,GND_string)
            for i in range(1,len(func_string_list)):
                cmdstring = cmdstring + "%s " %func_string_list[i]
            for i in range(2,len(cmd_list)):
                cmdstring = cmdstring + "%s " %cmd_list[i].split('=')[1]

            cmdstring = cmdstring +"GND99"

            case["CMDSTRING"] = cmdstring

            return 0,case

        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info


if __name__ == "__main__":
    cF.readConfigFile()
    a = tree_directory_class()
    case = {}
    case["CASES_ID"]="22"
    case["CMDSTRING"] = u"账号=@khh@#密码=@khh_pwd@#转账金额=100#资金密码=111111"
    #b = a.get_func_string_according_id('517')
    a.pre_process_test_case(case)
    print b
