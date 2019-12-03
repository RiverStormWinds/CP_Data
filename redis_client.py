# -*- coding:gbk -*-
import redis
import commFuncs as cF
from gl import GlobalLogging as Logging
# import gl
import json
import datetime

"""
Memory DB Definition

+ agent_curr_state Agent当前状态
    + 描述：记录Agent当前状态
    + Key: agent_curr_state
    + Value: HashMap
    +   + agent_id: "{'state':'STATE_FREE','last_alive':'{时间}'}"
    + 例子: "agent_curr_state":{"1":"{'state':'STATE_FREE','last_alive':'2018-10-18 16:47:00'}","2":"{'state':'STATE_FREE','last_alive':'2018-10-18 16:47:00'}"
    
+ agent_curr_task 当前运行任务
    + 描述：记录当前需要运行的任务列表（包括正在运行的和尚未运行的，已经运行完毕的不包括在内）
    + Key: agent_curr_task
    + Value: task_id 列表
    + 例子: "agent_curr_task":[2,3,4,5]
    
+ task_agent_table 任务对应的执行agent对比表
    + 描述：任务与被分配的agent的对应表
    + Key: task_agent_table
    + Value: task_id:agent_id 列表
    + 例子: "task_agent_table":{"4":[2,3,4]}
    
+ curr_task_list 当前任务列表
    + Key: current_task_list
    + Value: task_id 列表
    + 例子: "current_task_list":[2,3,4,5]
    
+ task_record_id_set 某个任务包含的sx_run_record id 集合
    + Key: task_record_id_set:{task_id}
    + Value: sx_run_record id 集合
    + 例子: "task_record_id_set:4":(112,113,114,115)

+ task_info 任务信息表
    + Key: task_info:{task_id}
    + Value: HashMap
        + collection_id 用例集ID
        + collection_name 用例集名
        + system_id 系统ID
        + ...
    + 例子: "task_info:4":{"collection_id":3,"collection_name":"用例集名"}
    
+ task_init_state 任务初始化状态表
    + Key: task_init_state:{task_id}
    + Value: HashMap
        + AGNET_ID AGENT ID
        + INIT_STATE 初始化状态
        + INIT_MSG 初始化消息
        + SYNC_FLAG 同步标识
        + SYSTEM_ID 系统ID
    + 例子: "task_init_state:4":{"AGNET_ID":3,"collection_name":"用例集名"}
    
+ case_result 用例结果表
    + Key: case_result:{task_id}
    + Value: HashMap
        + run_record_id result
    + 例子: "case_result:4": {"{run_record_id}":{result}}
    
+ account_data_list 账号组信息
    + Key account_data_list
    + Value account_data_list
    + 例子: account_data_list:[{account_data_list}]
    
+ account_group_dict 集中营运项目-产生账号组信息
    + Key: account_group_dict:{}
    + Value: dict
    + 例子: "account_group_dict":{"CLYL002301":{"data":{"0":[{"sh_a_secuid":"A2384247248","sz_a_secuid":"4549223423"},{"sh_a_secuid":"A2384247248","sz_a_secuid":"4549223423"}]}}}
"""


class RedisClient(object):
    """Redis客户端

    

    Attributes:
        r: Redis的一个实例
    """

    def __init__(self, ip, port):
        self.r = redis.Redis(host=ip, port=port, db=0)
        pass

    def set_account_group_dict(self, id, account_group_dict):
        """
        设置账号组数据
        账号组数据
        :param account_group_dict:
        :return:
        """
        # Logging.getLog().debug(u"account_group_dict %s" % account_group_dict)
        self.r.hset("account_group_dict", id, json.dumps(account_group_dict, ensure_ascii=False))
        return 0, ""

    def get_account_group_dict(self, id):
        """
        获得账号组数据
        用例集id
        :param id:
        :return:
        """
        if id:
            account_group_dict = self.r.hget("account_group_dict", id)
        else:
            account_group_dict = self.r.hgetall("account_group_dict")
        # Logging.getLog().debug(u"account_group_dict %s" % account_group_dict)
        return account_group_dict

    def remove_account_group_dict(self, task_id_list):
        try:
            p = self.r.pipeline()
            for id in task_id_list:
                p.hdel("account_group_dict", id)
            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def rebuild_agent_info(self):
        rebuild_agent_dict = {}
        p = self.r.pipeline()
        p.lrange("curr_task_list", 0, -1)
        p.hgetall("task_agent_table")
        curr_task_list, task_agent_table_dict = p.execute()
        if curr_task_list:
            for task_id in curr_task_list:
                agent_list = task_agent_table_dict[task_id].split(',')
                agent_list.sort()
                rebuild_agent_dict[int(task_id)] = agent_list
        return rebuild_agent_dict

    def rebuild_task_info(self, agent_id):
        """
        当Agent启动的时候，根据redis 数据库的信息重建内存信息
        :param agent_id:
        :return:
        :    rebuld_info_dict {task_id:agent_id_list}
        """
        rebuild_info_dict = {}
        p = self.r.pipeline()
        p.lrange("agent_curr_task", 0, -1)
        p.hgetall("task_agent_table")
        agent_curr_task_list, task_agent_table_dict = p.execute()
        if agent_curr_task_list:
            for task_id in agent_curr_task_list:
                agent_list = task_agent_table_dict[task_id].split(',')
                if str(agent_id) in agent_list:
                    cancel_flag = int(self.r.hget("task_info:%s" % str(task_id), "cancel_flag"))
                    rebuild_info_dict[task_id] = {}
                    rebuild_info_dict[task_id]["agent_list"] = agent_list
                    rebuild_info_dict[task_id]["cancel_flag"] = cancel_flag

        return rebuild_info_dict

    def add_new_task_to_redis(self, task_id, collection_id, collection_name, system_id, cases_num, timed_task_flag,
                              run_record_id_list, warning_info, agent_list):
        """
        新建一个任务,向redis存放一个任务
        :param task_id:
        :param collection_id:
        :param collection_name:
        :param system_id:
        :param cases_num:
        :param timed_task_flag:
        :param run_record_id_list:
        :param warning_info: 警告信息，字符串形式
        :param agent_list: testagent id list
        :return:
        """
        try:
            Logging.getLog().debug("Redis:add_new_task_to_redis(%s)" % str(task_id))
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            p = self.r.pipeline()
            p.rpush("curr_task_list", task_id)

            p.delete("task_record_id_set:%s" % str(task_id))
            for id in run_record_id_list:
                p.sadd("task_record_id_set:%s" % str(task_id), id)

            p.hset("task_info:%s" % str(task_id), "collection_id", collection_id)
            p.hset("task_info:%s" % str(task_id), "collection_name", collection_name)
            p.hset("task_info:%s" % str(task_id), "system_id", system_id)
            p.hset("task_info:%s" % str(task_id), "cases_num", cases_num)
            p.hset("task_info:%s" % str(task_id), "timed_task_flag", timed_task_flag)
            p.hset("task_info:%s" % str(task_id), "run_start_time", now)
            p.hset("task_info:%s" % str(task_id), "run_end_time", "")
            p.hset("task_info:%s" % str(task_id), "run_case_num", 0)
            p.hset("task_info:%s" % str(task_id), "run_case_num_success", 0)
            p.hset("task_info:%s" % str(task_id), "run_case_num_fail", 0)
            p.hset("task_info:%s" % str(task_id), "warning_info", warning_info)
            p.hset("task_info:%s" % str(task_id), "cancel_flag", 0)

            # 新增任务的初始化状态
            p.hset("task_init_state:%s" % str(task_id), "AGNET_ID", "")
            p.hset("task_init_state:%s" % str(task_id), "INIT_STATE", "STATE_UNINIT")
            p.hset("task_init_state:%s" % str(task_id), "INIT_MSG", "")
            p.hset("task_init_state:%s" % str(task_id), "SYNC_FLAG", "FALSE")  # 是否同步到数据库了
            p.hset("task_init_state:%s" % str(task_id), "SYSTEM_ID", system_id)  # system_id fixme

            p.rpush("agent_curr_task", task_id)

            p.hset("task_agent_table", task_id, agent_list)

            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def lrem_item(self, pipe, name, val):
        try:
            pipe.lrem(name, val)
        except:
            pipe.lrem(name, 0, val)

    def del_task(self, task_id):
        try:
            p = self.r.pipeline()
            self.lrem_item(p, "curr_task_list", task_id)
            p.delete("task_record_id_set:%s" % str(task_id))
            p.delete("task_init_state:%s" % str(task_id))
            p.delete("task_info:%s" % str(task_id))
            self.lrem_item(p, "agent_curr_task", task_id)
            p.hdel("task_agent_table", task_id)
            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def cancel_task(self, task_id):
        try:
            Logging.getLog().debug("Redis:cancel_task %s" % str(task_id))
            key = "task_record_id_set:%s" % str(task_id)
            num = self.r.scard(key)

            p = self.r.pipeline()
            p.hset("task_info:%s" % str(task_id), "cancel_flag", 1)
            for i in xrange(num):
                p.spop(key)

            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def modify_task_info(self, task_id, run_start_time="", run_end_time="", run_case_num=0, run_case_num_success=0,
                         run_case_num_fail=0, warning_info="", cancel_flag=0):
        """
        修改任务信息表
        :param task_id:
        :param run_start_time:
        :param run_end_time:
        :param run_case_num:
        :param run_case_num_success:
        :param run_case_num_fail:
        :param warning_info:
        :param cancel_flag:
        :return:
        """
        try:
            Logging.getLog().debug("Redis:modify_task_info %s %s %s %d %d %d %s %s" % (str(task_id),
                                                                                       run_start_time,
                                                                                       run_end_time,
                                                                                       run_case_num,
                                                                                       run_case_num_success,
                                                                                       run_case_num_fail,
                                                                                       warning_info,
                                                                                       str(cancel_flag)))
            p = self.r.pipeline()
            if run_start_time != "":
                p.hset("task_info:%s" % str(task_id), "run_start_time", run_start_time)
            if run_end_time != "":
                p.hset("task_info:%s" % str(task_id), "run_end_time", run_end_time)
            if run_case_num != 0:
                p.hset("task_info:%s" % str(task_id), "run_case_num", run_case_num)
            if run_case_num_success != 0:
                p.hset("task_info:%s" % str(task_id), "run_case_num_success", run_case_num_success)
            if run_case_num_fail != 0:
                p.hset("task_info:%s" % str(task_id), "run_case_num_fail", run_case_num_fail)
            if warning_info != "":
                p.hset("task_info:%s" % str(task_id), "warning_info", warning_info)
            if cancel_flag != 0:
                p.hset("task_info:%s" % str(task_id), "cancel_flag", cancel_flag)
            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def send_test_result_back_to_redis(self, agent_id, task_id, test_result_list):
        try:
            p = self.r.pipeline()

            result_key = "case_result:%s" % task_id

            for test_result in test_result_list:
                run_record_id = test_result["RUN_RECORD_ID"]
                try:
                    result = json.dumps(test_result, ensure_ascii=False, encoding="gbk")
                except:
                    result = str(test_result).encode('gbk')
                p.hset(result_key, run_record_id, result)
                p.srem("task_record_id_set:%s" % str(task_id), run_record_id)

            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def read_curr_task_list(self):
        try:
            curr_task_list = self.r.lrange("curr_task_list", 0, -1)
            return 0, curr_task_list
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def read_task_info(self, task_id):
        try:
            p = self.r.pipeline()
            p.smembers("task_record_id_set:%s" % str(task_id))
            p.hgetall("task_init_state:%s" % str(task_id))
            p.hgetall("case_result:%s" % str(task_id))
            p.hgetall("task_info:%s" % str(task_id))
            task_info_list = p.execute()
            # curr_task_list = self.r.lrange("curr_task_list", 0, -1)
            return 0, task_info_list
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def read_task_env_init_state(self, task_id):
        try:
            state = self.r.hget("task_init_state:%s" % str(task_id), "INIT_STATE")
            return 0, state
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def send_env_init_result_back_to_redis(self, agent_id, task_id, result='', msg='', sync_flag=0):
        try:
            p = self.r.pipeline()

            if agent_id != "":
                p.hset("task_init_state:%s" % str(task_id), "AGNET_ID", agent_id)
            if result != '':
                p.hset("task_init_state:%s" % str(task_id), "INIT_STATE", result)
            if msg != '':
                p.hset("task_init_state:%s" % str(task_id), "INIT_MSG", msg)
            if sync_flag != 0:
                p.hset("task_init_state:%s" % str(task_id), "SYNC_FLAG", sync_flag)
            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    # def publish_new_task_to_redis(self, task_id, system_id, run_record_id_list):
    #     """
    #     发布一个新任务到对应的Agent队列
    #     :param task_id:
    #     :param run_record_id_list:
    #     :param case_list:
    #     :param agent_list:
    #     :return:
    #     """
    #     try:
    #         p = self.r.pipeline()
    #
    #         # 当前正在执行的任务
    #         p.rpush("curr_task_list", task_id)
    #
    #         # 每个任务的待执行的用例集合
    #         for id in run_record_id_list:
    #             p.sadd("task_record_id_set:%s" % str(task_id), id)
    #
    #         # 新增任务的初始化状态
    #         p.hset("task_init_state:%s" % str(task_id), "AGNET_ID", "")
    #         p.hset("task_init_state:%s" % str(task_id), "INIT_STATE", "STATE_UNINIT")
    #         p.hset("task_init_state:%s" % str(task_id), "INIT_MSG", "")
    #         p.hset("task_init_state:%s" % str(task_id), "SYNC_FLAG", "FALSE")  # 是否同步到数据库了
    #         p.hset("task_init_state:%s" % str(task_id), "SYSTEM_ID", system_id)  # system_id fixme
    #
    #         p.execute()
    #         return 0, "OK"
    #     except redis.RedisError:
    #         exc_info = cF.getExceptionInfo()
    #         Logging.getLog().error(exc_info)
    #         return -1, exc_info

    def report_case_result(self, task_id, case_result_dict):
        try:
            p = self.r.pipeline()
            for id in case_result_dict.keys():
                p.hset("case_result:%s" % str(task_id), id, case_result_dict[id])
                p.srem("task_record_id_set:%s" % str(task_id), id)
            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def remove_case_result(self, task_id, run_record_id_list):
        try:
            p = self.r.pipeline()
            for id in run_record_id_list:
                # p.hset("case_result:%d" % task_id, id, case_result_dict[id])
                p.hdel("case_result:%s" % str(task_id), id)
            p.execute()
            return 0, "OK"
        except redis.RedisError:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def is_task_finished(self, task_id):
        return self.r.scard("task_record_id_set:%s" % str(task_id)) == 0

    def set_heartbeat_info(self, agent_id, state, last_alive):
        """
        设置心跳状态
        :param agent_id:
        :param state:
        :param last_alive:
        :return:
        """
        # Logging.getLog().debug("set_heartbeat_info agent_id=%s, state=%s,last_alive=%s" %(str(agent_id), state, last_alive))

        agent_dict = {}
        agent_dict["state"] = state
        agent_dict["last_alive"] = last_alive

        self.r.hset("agent_curr_state", agent_id, json.dumps(agent_dict, ensure_ascii=False))
        return 0, "OK"

    def get_heartbeat_info(self):
        """
        获取心跳状态
        :return:
        """
        heartbeat_info = self.r.hgetall("agent_curr_state")
        return 0, heartbeat_info

    def set_account_data_list(self, account_info):
        """
        账号数据
        :param account_info:
        :return:
        """
        Logging.getLog().debug(u"set_account_data_list %s" % account_info)
        self.r.rpush("account_data_list", account_info)
        return 0, ""

    def get_account_data_list(self):
        account_data_list = self.r.lrange("account_data_list", 0, -1)
        if len(account_data_list) > 0:
            Logging.getLog().debug(u"get_account_data_list %d" % len(account_data_list))
            self.r.delete("account_data_list")
            return 0, account_data_list
        else:
            return -1, ""

    def set_agent_id_data_list(self, agent_id_data):
        """
        账号数据
        :param agent_id_data:
        :return:
        """
        Logging.getLog().debug(u"set_agent_id_data_list %s" % agent_id_data)
        self.r.rpush("agent_id_data_list", agent_id_data)
        return 0, ""

    def get_agent_id_data_list(self):
        agent_id_data_list = self.r.lrange("agent_id_data_list", 0, -1)
        if len(agent_id_data_list) > 0:
            Logging.getLog().debug(u"get_agent_id_data_list %d" % len(agent_id_data_list))
            self.r.delete("agent_id_data_list")
            return 0, agent_id_data_list
        else:
            return -1, ""


if __name__ == "__main__":
    c = RedisClient('10.187.160.140', 6379)
    # c = RedisClient('5.5.6.66', 6379)
    test_result = {}
    test_result["RUN_RECORD_ID"] = 3
    test_result_list = []
    test_result_list.append(test_result)
    a = ""
    # c.publish_new_task_to_redis(1, "", [1,2,3,4,5,6,7])
    # c.send_test_result_back_to_redis("1",1,test_result_list)
    # a = c.read_task_info(1)
    #更新账户组
    # c.set_account_group_dict("CLYL0000003", {"system_id": "142891263425277DZ1", "data": {
    #     "2": [{"sh_a_secuid": "A2384247248", "sz_a_secuid": "4549223423"},
    #           {"sh_a_secuid": "A2384247248", "sz_a_secuid": "4549223423"}]}})
    a = c.get_account_group_dict(None)
    print a
