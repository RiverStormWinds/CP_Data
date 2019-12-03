# -*- coding:gbk -*-
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


class daemon(object):
    def __init__(self):
        self.stop_requested = False
        self.logger = self._getLogger()

    def _getLogger(self):

        logger = logging.getLogger('[daemon]')
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        handler = logging.FileHandler(os.path.join(application_path, "daemon.log"))

        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)

        return logger
        # def SvcStop(self):

    # self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
    #    win32event.SetEvent(self.stop_event)
    #    self.logger.info('Stopping service ...')
    #    self.stop_requested = True

    # def SvcDoRun(self):
    #    servicemanager.LogMsg(
    #        servicemanager.EVENTLOG_INFORMATION_TYPE,
    #        servicemanager.PYS_SERVICE_STARTED,
    #        (self._svc_name_,'')
    #    )
    #    self.main()

    def main(self):
        self.logger.info(u' ** 时溪守护进程启动 v2017.04.24.97 ** ')
        self.logger.info(u'frozen is %s' % getattr(sys, 'frozen', False))
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        self.logger.info("application_path = %s" % application_path)

        self._proc = None
        # Simulate a main loop
        '''
        for i in range(0,50):
            if self.stop_requested:
                logging.info('A stop signal was received: Breaking main loop ...')
                break
            time.sleep(5)
            logging.info("Hello at %s" % time.ctime())
        '''
        try:

            start_process_time = datetime.datetime.now()
            # 读取配置文件，了解TestAgentServer程序的安装位置

            # self.logger.debug("1")


            init_file = os.path.join(application_path, "daemon.ini")
            self.logger.debug(init_file)
            value = open(init_file, "r").read()
            self.logger.debug(value)
            dir_dict = mqclient_setting = json.loads(value)
            self.logger.debug(dir_dict)
            process_name = os.path.basename(dir_dict['monitor_application_path'])

            self.logger.debug(process_name)
            while not self.stop_requested:
                # self.logger.info(u"I'm alive")

                # rc=win32event.WaitForSingleObject(self.hWaitStop, self.timeout)
                self.logger.info(u"进程检查")
                time.sleep(5)
                # 查看进程是否还在

                if self.CheckProcExistByPN(process_name) == 1:
                    try:
                        alive_time_dict = json.loads(open(dir_dict['application_alive_file_path'], "r").read())
                    except Exception, e:
                        exc_info = self.getExceptionInfo()
                        self.logger.error(exc_info)
                        continue

                    alive_time = datetime.datetime.strptime(alive_time_dict['last_alive'], '%Y-%m-%d %H:%M:%S')
                    self.logger.info(u"检测到%s进程" % process_name)
                    # if self._proc != None:
                    #    info = self._proc.stdout.readlines()
                    #    for line in info:
                    #        self.logger.info(line)
                    if (datetime.datetime.now() - alive_time).seconds > 300 and (
                        datetime.datetime.now() - start_process_time).seconds > 10:  # 进程已经死了30秒以上，并且拉起进程后需要至少等10秒才能再拉
                        # 杀掉进程
                        self.logger.info(u"%s进程距离上次活跃时间已经超过300秒，尝试重新启动" % process_name)
                        self.killProcess(process_name)
                        time.sleep(5)
                        dirname = os.path.dirname(dir_dict['monitor_application_path'])
                        cmdline = "%s >>%s 2>%s" % (
                        dir_dict['monitor_application_path'], os.path.join(dirname, 'output.log'),
                        os.path.join(dirname, 'error.log'))
                        cmdline = "%s" % (dir_dict['monitor_application_path'])
                        si = subprocess.STARTUPINFO
                        si.wShowWindow = subprocess.SW_HIDE
                        # self._proc = subprocess.Popen(cmdline,shell=True, startupinfo=si, stdout = subprocess.PIPE, stderr=subprocess.STDOUT)
                        self._proc = subprocess.Popen(cmdline, shell=True, startupinfo=si)
                        start_process_time = datetime.datetime.now()
                        time.sleep(5)
                        # else:
                        #    if self._proc != None:
                        #        if not self._proc.poll():
                        #            print "1"
                        #            out,err = self._proc.communicate()
                        #            print "2"
                        #            print out
                        #            print err
                        #            if out != None:
                        #                self.logger.info(out)
                        #            if err != None:
                        #                self.logger.info(out)
                else:
                    self.logger.error(u"未能检测到%s进程，尝试重新启动 %s" % (process_name, dir_dict['monitor_application_path']))

                    dirname = os.path.dirname(dir_dict['monitor_application_path'])
                    # cmdline = "%s >>%s 2>%s" %(dir_dict['monitor_application_path'],os.path.join(dirname,'output.log'),os.path.join(dirname,'error.log'))
                    cmdline = "%s" % (dir_dict['monitor_application_path'])

                    si = subprocess.STARTUPINFO
                    si.wShowWindow = subprocess.SW_HIDE
                    # self._proc = subprocess.Popen(cmdline,shell=True, startupinfo=si, stdout = subprocess.PIPE, stderr=subprocess.STDOUT)
                    self._proc = subprocess.Popen(cmdline, shell=True, startupinfo=si)

                    start_process_time = datetime.datetime.now()
                    time.sleep(5)
        except Exception, e:
            exc_info = self.getExceptionInfo()
            self.logger.error(exc_info)
            return
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
        else:
            traceback_details = {
                'filename': exc_traceback.tb_frame.f_code.co_filename,
                'lineno': exc_traceback.tb_lineno,
                'name': exc_traceback.tb_frame.f_code.co_name,
                'type': exc_type.__name__,
                'message': exc_value.message,  # or see traceback._some_str()
                'more_info': ""
            }
        return "%s" % (
        '''Traceback (most recent call last):  File "%(filename)s", line %(lineno)s, in %(name)s %(type)s: %(message)s %(more_info)s\n''' % traceback_details)


if __name__ == '__main__':
    d = daemon()
    d.main()
