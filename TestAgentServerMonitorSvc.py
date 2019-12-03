# -*- coding:gbk -*-
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import logging
import sys
import time
import datetime
import json
import win32com.client
import subprocess
import os


# logging.basicConfig(
#    filename = 'c:\\Temp\\TestAgent-Monitor-service.log',
#    level = logging.DEBUG, 
#    # format = '[helloworld-service] %(levelname)-7.7s %(message)s'
#    format = '[TestAgent-monitor-service] %(asctime)s %(name)-12s %(levelname)-8s %(message)s'
# )

class TestAgentServerMonitorSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "TestAgent Server Monitor Service"
    _svc_display_name_ = u"TestAgent Server 监控服务"
    # 服务描述
    _svc_description_ = u"用于监控时溪TestAgent Server的后台服务"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.stop_requested = False
        self.logger = self._getLogger()

    def _getLogger(self):

        logger = logging.getLogger('[TestAgentServerMonitorSvc]')
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        handler = logging.FileHandler(os.path.join(application_path, "TestAgentServer-Monitor-service.log"))

        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        return logger

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.logger.info('Stopping service ...')
        self.stop_requested = True

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        self.logger.info(u' ** 服务启动 ** ')
        self.logger.info(u'frozen is %s' % getattr(sys, 'frozen', False))
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        self.logger.info("application_path = %s" % application_path)
        # Simulate a main loop
        '''
        for i in range(0,50):
            if self.stop_requested:
                logging.info('A stop signal was received: Breaking main loop ...')
                break
            time.sleep(5)
            logging.info("Hello at %s" % time.ctime())
        '''

        start_process_time = datetime.datetime.now()
        # 读取配置文件，了解TestAgentServer程序的安装位置




        init_file = os.path.join(application_path, "TestAgentServerMonitorSvc.ini")

        value = open(init_file, "r").read()
        dir_dict = mqclient_setting = json.loads(value)

        process_name = os.path.basename(dir_dict['monitor_application_path'])

        while not self.stop_requested:
            self.logger.info(u"I'm alive")

            # rc=win32event.WaitForSingleObject(self.hWaitStop, self.timeout)
            self.logger.info(u"进程检查")
            time.sleep(10)
            # 查看进程是否还在

            if self.CheckProcExistByPN(process_name) == 1:
                alive_time_dict = json.loads(open(dir_dict['application_alive_file_path'], "r").read())
                alive_time = datetime.datetime.strptime(alive_time_dict['last_alive'], '%Y-%m-%d %H:%M:%S')
                self.logger.info(u"检测到%s进程" % process_name)
                if (datetime.datetime.now() - alive_time).seconds > 30 and (
                            datetime.datetime.now() - start_process_time).seconds > 10:  # 进程已经死了30秒以上，并且拉起进程后需要至少等10秒才能再拉
                    # 杀掉进程
                    self.logger.info(u"%s进程距离上次活跃时间已经超过30秒，尝试重新启动" % process_name)
                    self.killProcess(process_name)
                    time.sleep(5)
                    dirname = os.path.dirname(dir_dict['monitor_application_path'])
                    cmdline = "%s >>%s 2>%s" % (
                        dir_dict['monitor_application_path'], os.path.join(dirname, 'output.log'),
                        os.path.join(dirname, 'error.log'))
                    subprocess.Popen(cmdline, shell=True)
                    start_process_time = datetime.datetime.now()
                    time.sleep(5)
            else:
                self.logger.error(u"未能检测到%s进程，尝试重新启动 %s" % (process_name, dir_dict['monitor_application_path']))

                dirname = os.path.dirname(dir_dict['monitor_application_path'])
                cmdline = "%s >>%s 2>%s" % (dir_dict['monitor_application_path'], os.path.join(dirname, 'output.log'),
                                            os.path.join(dirname, 'error.log'))

                subprocess.Popen(cmdline, shell=True)

                start_process_time = datetime.datetime.now()
                time.sleep(5)

        return

    def killProcess(self, process_name):
        cmd_str = 'taskkill /F /IM %s' % process_name
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        proc.wait()

    def CheckProcExistByPN(self, process_name):
        try:
            WMI = win32com.client.GetObject('winmgmts:')
            processCodeCov = WMI.ExecQuery('select * from Win32_Process where Name="%s"' % process_name)
        except Exception, e:
            exc_info = cF.getExceptionInfo()
            self.logger.error(exc_info)
        if len(processCodeCov) > 0:
            print process_name + " exist";
            return 1
        else:
            print process_name + " is not exist";
            return 0

    def getExceptionInfo(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        more_info = ""
        if len(exc_value.args) == 2:
            more_info = exc_value.args[1].decode('gbk')
            traceback_details = {
                'filename': exc_traceback.tb_frame.f_code.co_filename,
                'lineno': exc_traceback.tb_lineno,
                'name': exc_traceback.tb_frame.f_code.co_name,
                'type': exc_type.__name__,
                'message': exc_value.message,  # or see traceback._some_str()
                'more_info': more_info
            }
        return "%s" % (
            '''Traceback (most recent call last):  File "%(filename)s", line %(lineno)s, in %(name)s %(type)s: %(message)s %(more_info)s\n''' % traceback_details)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TestAgentServerMonitorSvc)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TestAgentServerMonitorSvc)
