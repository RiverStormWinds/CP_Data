# -*- coding:gbk -*-
import threading
import time
import pika
from collections import OrderedDict
from gl import GlobalLogging as Logging
import commFuncs as cF
import json
import gl
import copy
import signal
import functools
import httplib
import base64
import socket

def async(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.start()
    
    return wrapper

class MQServer(threading.Thread):
    """MessageClient"""

    def __init__(self):
        threading.Thread.__init__(self)

        self._clients_dict = {}
        self._channel_dict = {} #{queue_name:channel}
        self._task_agent_dict = {} #{task_id:[agent_id]}

        credentials = pika.PlainCredentials('timesvc', 'timesvc')
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', credentials=credentials, heartbeat=0))
    
        self._rpc_channel = self._connection.channel()

        self._rpc_channel.queue_declare(queue='server_rpc_queue')

        self._rpc_channel.basic_qos(prefetch_count=1)
        self._rpc_channel.basic_consume(self.rpc_process, queue='server_rpc_queue')

        print(" [x] Awaiting RPC requests")
        # self._rpc_channel.start_consuming()
        self.start_consuming()
    
    @async
    def start_consuming(self):
        self._rpc_channel.start_consuming()
        
    def run(self):
        while gl.is_exit_all_thread == False:
            input_string = raw_input("please input what you want server to do:")
            input_list = input_string.split(' ')
            if input_list[0] == "new_task":
                self.fire_new_task(input_list[1], input_list[2], input_list[3])
            elif input_list[0] == "cancel_task":
                self.cancel_a_task(input_list[1], input_list[2])
        Logging.getLog().debug("Exit server loop")
                
    def tell_new_task_result(self, agent_id, task_id, result):
        print agent_id, task_id, result
        return 0, ""
    
    def just_a_test(self,state):
        print "just_a_test(%s)" %(str(state))
        return 0, ""
    
    def register_client(self, id):
        try:
            Logging.getLog().debug("receive register_client(%s)\n" % (id))
            agent_id = str(id)

            self._clients_dict[agent_id] = OrderedDict()
            
            #创建一个队列
            new_queue_name = "cmd_queue_%s" % str(id)
            if new_queue_name not in self._channel_dict.keys():
                channel = self._connection.channel()
                channel.queue_declare(queue=new_queue_name)
                self._channel_dict[new_queue_name] = channel
            
            #通知更新脚本
            # cmd_dict = OrderedDict()
            # cmd_dict["func"] = "processScriptUpdate"
            # cmd_dict["func_param"] = ""
            update_script_msg = copy.copy(gl.update_script_msg)
            
            channel = self._channel_dict[new_queue_name]
            channel.basic_publish(exchange='',
                  routing_key=new_queue_name,
                  body=json.dumps(update_script_msg, ensure_ascii=False))
        
            return 0, "OK"
        except:
            exc_info = cF.getExceptionInfo()
            print exc_info
            return -1, exc_info

    def rpc_process(self, ch, method, props, body):
        try:
            msg_dict = json.loads(body)
            return_dict = OrderedDict()
            
            if msg_dict["func_param"] == "":
                func_call = "self.%s()" % msg_dict["func"]
            else:
                # func_call = "self.%s(%s)" % (msg_dict["func"], ','.join(str(i) for i in msg_dict["func_param"]))
                func_call = "self.%s(%s)" % (msg_dict["func"], ','.join("'%s'" % str(i) for i in msg_dict["func_param"]))

            Logging.getLog().debug(func_call)
            ret, ret_info = eval(func_call)
            # ret, ret_info = eval("self.%s" % msg_dict["func"])tuple(msg_dict["func_param"])
            return_dict["return"] = ret
            return_dict["return_info"] = ret_info
            
            ch.basic_publish(exchange='',
                             routing_key=props.reply_to,
                             properties=pika.BasicProperties(correlation_id= \
                                                                 props.correlation_id),
                             body=json.dumps(return_dict, ensure_ascii=False))
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)

    def fire_new_task(self, task_id, count, agent_str): # test only
        try:
            count = int(count)
            agent_list = agent_str.split(",")
            agent_list.sort()
            self._task_agent_dict[task_id] = agent_list
            new_queue_name = "task_distribute_queue_%s" % "_".join(agent_list)
            
            for agent_id in agent_list:
                public_new_task_msg = copy.copy(gl.public_new_task_msg)
                public_new_task_msg["msg_body"]["task_id"] = task_id
                public_new_task_msg["msg_body"]["queue_name"] = new_queue_name
                cmd_queue_name = "cmd_queue_%s" % str(agent_id)
                cmd_channel = self._channel_dict[cmd_queue_name]
                cmd_channel.basic_publish(exchange='',
                                          routing_key=cmd_queue_name,
                                          body=json.dumps(public_new_task_msg, ensure_ascii=False))
            
            
            if new_queue_name not in self._channel_dict.keys():
                channel = self._connection.channel()
                channel.queue_declare(queue=new_queue_name)
                self._channel_dict[new_queue_name] = channel
            
            channel = self._channel_dict[new_queue_name]
            
            for i in xrange(count):
                case_distribute_msg = copy.copy(gl.case_distribute_msg)
                case_distribute_msg["msg_body"]["runTaskid"] = task_id
                case_distribute_msg["msg_serialno"] = str(i+1)
                channel.basic_publish(exchange='',
                                      routing_key=new_queue_name,
                                      body=json.dumps(case_distribute_msg, ensure_ascii=False))
            print("OK")
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
    def cancel_a_task(self, task_id,agent_str): # test only
        # if task_id in self._task_agent_dict.keys():
            agent_id_list = agent_str.split(",")
            for agent_id in agent_id_list:
                cancel_a_task_msg = copy.copy(gl.cancel_a_task_msg)
                cancel_a_task_msg["msg_body"]["task_id"] = task_id
                cmd_queue_name = "cmd_queue_%s" % str(agent_id)
                cmd_channel = self._channel_dict[cmd_queue_name]
                cmd_channel.basic_publish(exchange='',
                                          routing_key=cmd_queue_name,
                                          body=json.dumps(cancel_a_task_msg, ensure_ascii=False))
                
            # self._task_agent_dict.pop(task_id)
            print("OK")

    def get_queue_msg(self):
        conn = httplib.HTTPConnection("127.0.0.1", "15672")
        auth = ("timesvc:timesvc")
        headers = {"Authorization": "Basic "+base64.b64encode(auth)}
        path = '/api/queues?columns=name,messages'
        try:
            conn.request('GET', path, '', headers)
        except socket.error as e:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info
        
        resp = conn.getresponse()
        if resp.status == 400:
            Logging.getLog().error(json.loads(resp.read())['reason'])
        elif resp.status == 401:
            Logging.getLog().error('access refused')
        elif resp.status == 404:
            Logging.getLog().error('Not found')
        elif resp.status == 301:
            Logging.getLog().error('301 error')
        
        if resp.status < 200 or resp.status > 400:
            Logging.getLog().error("Received %d %s for path %s\n%s" % (resp.status, resp.reason, path, resp.read()))
            
        data = resp.read().decode('utf-8')
        queue_msg_dict = json.loads(data)
        return queue_msg_dict
        
        
        
        
        
def processTerm(signum, frame):
    gl.is_exit_all_thread = True
    Logging.getLog().debug("Receive Term Signal")

def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)
    Logging.getLog().info(u'''
    时溪自动化测试平台-Test Agent Server v2.0 2018.08.22
    (上海时溪信息技术有限公司）
    ''')
    server = MQServer()
    server.setDaemon(True)
    server.start()
    
    # server.get_queue_msg()
    while gl.is_exit_all_thread == False:
        pass

    if gl.is_exit_all_thread == True:
        
        server._rpc_channel.stop_consuming()
        server._connection.close()
        server.join()
    Logging.getLog().debug("Exit Server Safely")
        
if __name__ == "__main__":
    main()