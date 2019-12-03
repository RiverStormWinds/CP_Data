# -*- coding:gbk -*-
import threading
import time
import pika
from collections import OrderedDict
from gl import GlobalLogging as Logging
import commFuncs as cF
import json
import functools
import uuid
import signal
import sys
import os
import gl


def async(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.start()
    
    return wrapper


class MQClient(threading.Thread):
    """MessageClient"""
    
    def __init__(self, setting):
        threading.Thread.__init__(self)
        self._setting = setting
        self._agent_id = setting["AgentID"]
        print "_agent_id = %s" % self._agent_id
        # self._registered = False

        #连接到RabbitMQ
        credentials = pika.PlainCredentials('timesvc', 'timesvc')
        self._rpc_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', credentials=credentials, heartbeat=0))
        
        self.rpc_channel = self._rpc_connection.channel()
        
        result = self.rpc_channel.queue_declare(queue="rpc_queue_callback_%s" % self._agent_id, exclusive=True)
        self.callback_queue = result.method.queue
        
        self.rpc_channel.basic_consume(self.on_response, no_ack=True,
                                       queue=self.callback_queue)
        
        self.result_dict = {}
        self._channel_dict = {}  ##该客户端需要读取的队列列表 {queue_name:channel}
        self._task_queue_dict = OrderedDict()  #保存任务号和queue的对应关系 {task_id:{"queue_name":queue_name, "state":""}}
    
    def get_agent_id(self):
        return self._agent_id
    def on_response(self, ch, method, props, body):
        if props.correlation_id in self.result_dict.keys():
            self.result_dict[props.correlation_id] = body
        # self.rpc_channel.basic_consume(self.on_response, no_ack=True,
        #                                queue=self.callback_queue)
        # if self.corr_id == props.correlation_id:
        #     self.response = body
    
    
    def cmd_queue_callback(self, ch, method, properties, body):
        """
        命令队列的回调函数
        这个里面可以慢慢的一个一个消化消息
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return:
        """
        try:
            msg_dict = json.loads(body)
            
            Logging.getLog().debug(" [x] Received %s" % msg_dict["msg_desc"])
            # Logging.getLog().debug("acquire Lock")
            self.check_sync_lock(release=False)
            
            msg_id = msg_dict["msg_id"]
            if msg_id == gl.PUBLIC_NEW_TASK_ID:
                ret, msg = self.process_new_task_msg(msg_dict)
        
                func_body_dict = {}
                func_body_dict["func"] = "tell_new_task_result"
                if ret < 0:
                    func_body_dict["func_param"] = (self._agent_id, msg_dict["msg_body"]["task_id"], 0)
                else:
                    func_body_dict["func_param"] = (self._agent_id, msg_dict["msg_body"]["task_id"], 1)
        
                ret, msg = self.call_server_rpc(func_body_dict)
                if ret < 0:
                    Logging.getLog().error("call_server_rpc fail")
                else:
                    Logging.getLog().error("call_server_rpc OK %s" % msg)
            elif msg_id == gl.CANCEL_A_TASK_ID:
                
                task_id = msg_dict["msg_body"]["task_id"]
                self._task_queue_dict.pop(task_id)
                Logging.getLog().debug("cancel %d task" % int(task_id))
                
            elif msg_id == gl.UPDATE_SCRIPT_MSG_ID:
                func_body_dict = {}
                func_body_dict["func"] = "just_a_test"
                func_body_dict["func_param"] = (0, )
         
    
                ret, msg = self.call_server_rpc(func_body_dict)
                if ret < 0:
                    Logging.getLog().error("call_server_rpc fail")
                else:
                    Logging.getLog().debug("call_server_rpc OK %s" % msg)
                # self._task_queue_dict.pop(task_id) #直接移除即可
    
            ch.basic_ack(delivery_tag=method.delivery_tag)
            # Logging.getLog().debug("release Lock")
            self.check_sync_lock(release=True)
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            # TODO 增加错误返回码
            ch.basic_ack(delivery_tag=method.delivery_tag)
            # Logging.getLog().debug("release Lock")
            self.check_sync_lock(release=True)
    
    @async
    def listen_cmd_queue_thread(self):
        credentials = pika.PlainCredentials('timesvc', 'timesvc')
        self._cmd_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', credentials=credentials, heartbeat=0))
        
        new_queue_name = "cmd_queue_%s" % self._agent_id
        if new_queue_name not in self._channel_dict.keys():
            channel = self._cmd_connection.channel()
            channel.queue_declare(queue=new_queue_name)
            self._channel_dict[new_queue_name] = channel

        channel = self._channel_dict[new_queue_name]
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.cmd_queue_callback,
                              queue=new_queue_name)
        thread = threading.current_thread()
        print "curr thread is %s" % thread.getName()
        channel.start_consuming()
        
    @async
    def listen_task_queue(self):
        """
        
        :param channel: 这里的channel是命令队列
        :param queue_name:
        :return:
        """
        # 当队列中存在多个消息的时候，可以不休息，以增加性能。
        # 优先处理命令队列里的消息
        
        msg_count_dict = {}

        thread = threading.current_thread()
        print "curr thread is %s" % thread.getName()
        
        while gl.is_exit_all_thread != True:

            task_list = self._task_queue_dict.keys()
            if task_list != []:
                task_list.sort() # 从最小的开始处理
                curr_task_id = task_list[0]
                task_queue_name = self._task_queue_dict[curr_task_id]["queue_name"]
                task_channel = self._channel_dict[task_queue_name]
                # Logging.getLog().debug("ready to read a msg from queue:%s" % task_queue_name)
                if msg_count_dict.get(task_queue_name, 0) == 0:
                    time.sleep(1)
                method_frame, header_frame, body = task_channel.basic_get(task_queue_name)
                if method_frame:
                    # Logging.getLog().debug("release Lock")
                    self.check_sync_lock(False)
                    
                    msg_count_dict[task_queue_name] = method_frame.message_count - 1
                    # 判断这个消息所属的任务是否和当前需要执行的任务一致，一致就处理，不一致就先退回，按照任务顺序来执行其他任务
                    msg_dict = json.loads(body)
                    if msg_dict["msg_id"] == gl.CASE_DISTRIBUTE_MSG_ID: #用例下发消息
                        run_task_id = msg_dict["msg_body"]["runTaskid"]
                        serial_no = msg_dict["msg_serialno"]
                        # if run_task_id in self._task_queue_dict.keys() and self._task_queue_dict[run_task_id]["state"] == "cancel":
                        #     Logging.getLog().debug("cancel a msg for queue:%s no=%s" % (task_queue_name, serial_no))
                        #     task_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                        #     self.check_sync_lock(True)
                        #
                        #     continue
                        if run_task_id == curr_task_id:
                            # 运行用例
                            time.sleep(1) #fixme for test only
                            
                            Logging.getLog().debug("ack a msg for queue:%s no=%s" % (task_queue_name, serial_no))
                            task_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                            
                        else:
                            #已经读到了其他任务了，暂时放弃
                            if run_task_id not in self._task_queue_dict.keys():
                                Logging.getLog().debug("queue:%s read another task (curr:%s,read:%s), seems curr task finished.remove this task from TaskAgent and reject this message no=%s" % (task_queue_name, str(curr_task_id), str(run_task_id), serial_no))
                                task_channel.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
                            else:
                                Logging.getLog().debug("queue:%s read another task (curr:%s,read:%s), seems curr task finished.remove this task from TaskAgent and return this message no=%s" %(task_queue_name, str(curr_task_id), str(run_task_id), serial_no))
                                self._task_queue_dict.pop(curr_task_id)
                                task_channel.basic_reject(delivery_tag=method_frame.delivery_tag)

                    self.check_sync_lock(True)
                else:
                    #因为任务是一次性下发到队列的，所以如果改队列为空，可以认为该任务已经处理完毕了
                    Logging.getLog().debug("queue:%s read nothing, seems this task finished.remove this task from TaskAgent" % task_queue_name)
                    self._task_queue_dict.pop(curr_task_id)

                
            else:
                time.sleep(1)

                    
    def check_sync_lock(self, release=False):
        if release == False:
            gl.g_sync_Lock.acquire()
        else:
            gl.g_sync_Lock.release()
        
        
    def call_server_rpc(self, func_body_dict):
        try:
            self.corr_id = str(uuid.uuid4())
            self.result_dict[self.corr_id] = None
        
            self.rpc_channel.basic_publish(exchange='',
                                           routing_key='server_rpc_queue',
                                           properties=pika.BasicProperties(
                                               reply_to=self.callback_queue,
                                               correlation_id=self.corr_id,
                                           ),
                                           body=json.dumps(func_body_dict, ensure_ascii=False))
            try:
                while self.result_dict[self.corr_id] is None and gl.is_exit_all_thread == False:
                    self._rpc_connection.process_data_events()
                
                if gl.is_exit_all_thread == True:
                    Logging.getLog().debug("exit call_server_rpc")
                    return -1, "exit call_server_rpc"
                else:
                    Logging.getLog().debug("call %s return %s" %(func_body_dict["func"], self.result_dict[self.corr_id]))
                    return 0, self.result_dict[self.corr_id]
            except KeyboardInterrupt:
                Logging.getLog().debug("get KeyboardInterrupt")
                return -1, "KeyboardInterrupt"
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, ""
        
    def process_new_task_msg(self,msg_dict):
        """
        看队列是否已经创建，否则创建channel和queue
        :param msg_dict:
        :return:
        """
        try:
            task_id = msg_dict["msg_body"]["task_id"]
            queue_name = msg_dict["msg_body"]["queue_name"]
            if queue_name not in self._channel_dict.keys():
                channel = self._rpc_connection.channel()
                self._channel_dict[queue_name] = channel
                channel.queue_declare(queue=queue_name)
            task_info = {}
            task_info["queue_name"] = queue_name
            task_info["state"] = ""
            self._task_queue_dict[task_id] = task_info
            # self._task_queue_dict[task_id] = queue_name
            # self._task_queue_dict.setdefault(task_id, {}).setdefault("queue_name", queue_name).setdefault("state", "")
            return 0,""
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info
        
        
    def process_cmd_msg(self, msg_dict, channel, queue_name):
        """
        
        :param msg_dict:
        :param channel:
        :param queue_name:
        :return:
        """
        
        
    def register_client(self):
        """
        注册客户端
        :return:
        """
        try:
            func_body = OrderedDict()
            func_body["func"] = "register_client"
            
            func_body["func_param"] = ("%s" % str(self._agent_id),)
            
            ret, msg = self.call_server_rpc(func_body)
            if ret < 0:
                Logging.getLog().error(msg)
                return -1, msg
            

            # 启动一个线程去拉命令队列
            # self.listen_cmd_queue_thread()
            self._cmd_thread = threading.Thread(target=self.listen_cmd_queue_thread)
            self._cmd_thread.start()
            # 启动一个线程去侦听任务队列
            self._task_thread = threading.Thread(target=self.listen_task_queue)
            self._task_thread.start()
            
            return 0, ""
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, ""
def processTerm(signum, frame):
    gl.is_exit_all_thread = True
    Logging.getLog().debug("Receive Term Signal")

def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)
    Logging.getLog().info(u'''
    时溪自动化测试平台-Test Agent v2.0 2018.08.22
    (上海时溪信息技术有限公司）
    ''')
    config_name = 'TestAgent.ini'
    # cF.readConfigFile()
    
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    
    config_path = os.path.join(application_path, config_name)
    
    mqclient_setting = json.loads(open(config_path, "r").read())
    
    mqclient = MQClient(mqclient_setting)
    mqclient.setDaemon(True)
    mqclient.start()
    
    ret, ret_info = mqclient.register_client()
    # ret, ret_info = mqclient.register_client()
    # ret, ret_info = mqclient.register_client()
    # ret, ret_info = mqclient.register_client()
    print ret, ret_info
    # mqclient.start_appium_server()
    thread = threading.current_thread()
    print "curr thread is %s" % thread.getName()
    while gl.is_exit_all_thread == False:
        # mqclient._rpc_connection.process_data_events()
        pass
        # if mqclient.isAlive() == False:
        #     mqclient.rpcserver.server_close()
        #     break;
    if gl.is_exit_all_thread == True:
        new_queue_name = "cmd_queue_%s" % mqclient.get_agent_id()
        
        #退出命令队列，如果命令队列存在的话
        cmd_channel = mqclient._channel_dict.get(new_queue_name,"")
        if cmd_channel != "":
            cmd_channel.stop_consuming()
            mqclient._cmd_thread.join()
            mqclient._task_thread.join()
    Logging.getLog().debug("Exit the Client Safely")

if __name__ == "__main__":
    main()
