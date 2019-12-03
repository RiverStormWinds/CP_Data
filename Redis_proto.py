# -*- coding:gbk -*-
import redis
import time
import json

# many code snipper come from https://www.cnblogs.com/clover-siyecao/p/5600078.html

def simple():
    r = redis.Redis(host='localhost', port=6379, db=0)
    print r.set('guo','shuai')
    print r.get('guo')
    print r.keys()
    print r.dbsize()
    print r.delete('guo')
    print r.save()
    print r.get("guo")
    print r.flushdb()
    
    
def verify_hash():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.hset('users:jdoe', 'name', 'John Doe')
    r.hset('users:jdoe', 'email', 'Jhon@test.com')
    r.hset('users:jdoe', 'phone', '1555313940')
    a = {}
    a["1"] = "a"
    a["2"] = "a"
    b = {}
    b["3"] = a
    
    r.hset('users:jdoe', 'phone', json.dumps(b, ensure_ascii=False))
    r.hincrby('users:jdoe', 'visits', 1)
    a = r.hgetall('users:jdoe')
    print a
    print r.hkeys('users:jdoe')
    return r.hget('users:jdoe', 'phone')
    
def verify_set():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.srem("test")
    # s_list = (1,2,3,4,5,6,7)
    # r.sadd("test",s_list)
    # print r.smembers("test")
    # r.sadd('circle:game:lol','users:debugo')
    # r.sadd('circle:game:lol', 'users:xiaorz')
    # r.sadd('circle:game:lol', 'users:rzxiao')
    #
    # r.sadd('circle:soccer:InterMilan', 'users:xiaorz')
    # r.sadd('circle:soccer:InterMilan', 'users:rzxiao')
    # r.sadd('circle:soccer:InterMilan', 'users:leo')
    #
    # print r.smembers('circle:game:lol')
    # print r.sinter('circle:game:lol', 'circle:soccer:InterMilan')
    # print r.sunion('circle:game:lol', 'circle:soccer:InterMilan')

    
def verify_pipeline():
    r = redis.Redis(host='localhost', port=6379, db=0)
    p = r.pipeline()
    # for i in xrange(1000000):
    #     p.sadd("set",i)
        
    # p.sadd("asdf","fdsa")
    # p.sadd("aaaa","aaaa")
    # p.sadd("aaaa", "bbbb")
    p.hgetall('users:jdoe')
    p.hget('users:jdoe', 'phone')
    a = p.execute()
    return a
    
def verify_list():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.lpush("list1",1,2,3)
    r.lpushx("list1",4)
    a =  r.lrange("list1",0,-1)
    print a
    return a
    
def temp_use():
    r = redis.Redis(host='10.176.65.17', port=6379, db=0)
    # r.delete('task_record_id_set:14981')
    # r.delete('task_record_id_set:14981')
    p = r.pipeline()
    task_id = '14995'
    result_key = "case_result:%s" % task_id
    result = '''
    {"cmdstring": "OP_CODE=#OP_BRANCH_NO=#OP_SITE=#OP_WAY=#OP_PROGRAM=#USER_CODE=#BRANCH_NO=#FUNC_ID=#PASSWORD=123456#USER_TOKEN=#TOKEN_SERIAL_NO=#CERT_TYPE=6#ID_TYPE=6#CERT_CODE=15021863640#AUTH_PRODUCT_TYPE=#AUTH_KEY=#AUTH_BIND_STATION=#SYS_SOURCE=#CERT_KIND=9", "run_user": "1", "log": "OK", "attachment": "N", "CASES_PARAM_DATA_ID": 123689, "data_change_info": "", "case_name": "12000000手机号登录", "return_message": {"field": ["USER_CODE", "BRANCH_NO", "USER_TOKEN", "TOKEN_SERIAL_NO", "LAST_LOGIN_DATE", "LAST_LOGIN_TIME", "LAST_OP_ENTRUST_WAY", "LAST_OP_STATION", "CLIENT_NAME", "CIF_ACCOUNT", "IDNO_TYPE", "ID_NO", "FIRST_OPEN_DATE", "ACCT_LIST", "PASSWORD", "ACCT_TYPE", "USER_TYPE"], "message": "OK", "values_list": [["44924", "0", "", "2018102221351900003000096000000000000000                                                       44924", "0", "0", "", "", "测试", "", "", "", "20180411", "", "", "", ""]]}, "step": 1, "result": "STATE_PASS", "RUN_RECORD_ID": 6914069, "msg": "OK", "funcid": "12000000"}
    '''
    p.hset(result_key, 1, result)
    p.execute()
    # r.hset(result_key, 1, result)
    return
#def temp_use():
#    r = redis.Redis(host='10.176.65.17', port=6379, db=0)
#    r.hset("task_agent_table", 14564, '16')
    
if __name__ == "__main__":
    temp_use()
    # time1 = time.time()
    # verify_pipeline()
    # print time.time() - time1
    # verify_set()
    # a = verify_pipeline()
    # print a
    # a = verify_list()
    # a = verify_hash()
    # print a
    # b = json.loads(a)
    # print b