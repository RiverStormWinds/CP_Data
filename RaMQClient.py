# -*- coding:gbk -*-
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
        
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    
        self.rpc_channel = self._connection.channel()
    
        result = self.rpc_channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
    
        self.rpc_channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)
    
        self.result_dict = {}
        self._channel_dict = {}
        
    def on_response(self, ch, method, props, body):
        if props.correlation_id in self.result_dict.keys():
            self.result_dict[props.correlation_id] = body
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
            print(" [x] Received %s" % msg_dict["func"])
            # TODO 增加消息的处理办法
            print(" [x] Done")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            # TODO 增加错误返回码
            ch.basic_ack(delivery_tag=method.delivery_tag)

    @async
    def listen_queue(self, channel, queue_name):
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.cmd_queue_callback,
                              queue=queue_name)
        channel.start_consuming()
        
    def register_client(self):
        try:
            func_body = OrderedDict()
            func_body["func"] = "register_client"
            
            func_body["func_param"] = "%s" % str(self._agent_id)
    
            self.corr_id = str(uuid.uuid4())
            self.result_dict[self.corr_id] = None
            
            self.rpc_channel.basic_publish(exchange='',
                                       routing_key='server_rpc_queue',
                                       properties=pika.BasicProperties(
                                           reply_to=self.callback_queue,
                                           correlation_id=self.corr_id,
                                       ),
                                       body=json.dumps(func_body))
            while self.result_dict[self.corr_id] is None:
                self._connection.process_data_events()

            # 创建一个队列
            new_queue_name = "TA_%s_cmd_queue" % self._agent_id
            if new_queue_name not in self._channel_dict.keys():
                channel = self._connection.channel()
                channel.queue_declare(queue=new_queue_name)
                self._channel_dict[new_queue_name] = channel
        
            channel = self._channel_dict[new_queue_name]
            
            # 启动一个线程去侦听命令队列
            self.listen_queue(channel, new_queue_name)
            return 0, ""
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, ""

def main():
    # signal.signal(signal.SIGINT, processTerm)
    # signal.signal(signal.SIGTERM, processTerm)
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
    print ret, ret_info
    # mqclient.start_appium_server()
    while True:
        pass
        # if mqclient.isAlive() == False:
        #     mqclient.rpcserver.server_close()
        #     break;


if __name__ == "__main__":
    main()
