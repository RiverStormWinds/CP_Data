# -*- coding:gbk -*-
import json
import subprocess
import commFuncs as cF
import commFuncs_kcbp as cF_kcbp
from ftpClient import XFer
import bizmod
import gl
import os
from gl import GlobalLogging as Logging
from PIL import ImageGrab
from collections import OrderedDict
import copy
# from Adapter.T2 import T2Adapter
import base64
# import param
import sys
import csv
import time
import datetime
import threading

reload(sys)
import re
import shutil
import zhlc
import copy
import urllib
import urllib2

sys.setdefaultencoding('utf8')
import chardet
import pyodbc
import json
import shutil
import time, Image
# import Image Fixme
import os, win32gui, win32ui, win32con, win32api
import hradapter
import export_excel
import huarui_dys
import requests

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import mblegal as mb


class executionEngine(object):
    def __init__(self, mqclient):
        self._result_msg_list = []

        # ������Ϣ��client
        self._mqclient = mqclient

        self._last_username = ""

        # �˳���غ�̨���̵ı�ʶ
        self._monitorScriptProcFlag = False

        # ����ִ�г�ʱ��ʶ
        self._caseOutOfTimeFlag = False

        # self._t2adapter = T2Adapter.T2Adapter(gl.g_ZHLCSystemSetting["T2Server"])
        pass

    def upload_appium_capture(self, runtaskid, run_record_id, filename):
        """
        ��appium�Ľ�����������ԭ�еĸ�����ʽ
        :param runtaskid:
        :param CASE_NAME:
        :param filename:
        :return:
        """
        try:
            if not os.path.exists('.\\logs\\%s' % runtaskid):
                os.makedirs('.\\logs\\%s' % runtaskid)

            if os.path.exists('.\\logs\\appium_capture.jpg'):
                # �������ŵ����ʵ�Ŀ¼����ȥ
                os.rename('.\\logs\\appium_capture.jpg', '.\\logs\\%s.jpg' % (run_record_id))
                shutil.move('.\\logs\\%s.jpg' % (run_record_id), '.\\logs\\%s' % runtaskid)

            ret, f = self._mqclient.createFTPClient()
            if ret < 0:
                print f
                return ret, f
            f.upload_file_ex('./logs/%s/%s.jpg' % (runtaskid, run_record_id), './Log/%s' % runtaskid)
            return 0, ""
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def window_capture(self, runtaskid, filename, log_info):
        '''''
      ��������,���÷���window_capture('d:\\') ,����Ϊָ�������Ŀ¼
      ����ͼƬ�ļ���,�ļ�����ʽ:����.jpg ��:2009328224853.jpg
        '''
        try:
            # global error_photo_path
            # if not os.path.exists(error_photo_path):
            #     os.makedirs(error_photo_path)
            print "CaptureScreen"
            if not os.path.exists('.\\logs\\%s' % runtaskid):
                os.makedirs('.\\logs\\%s' % runtaskid)
            jpg_path = ".\\logs\\%s\\" % (runtaskid)
            hwnd = 0
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            MoniterDev = win32api.EnumDisplayMonitors(None, None)
            w = MoniterDev[0][2][2]
            h = MoniterDev[0][2][3]
            # print w,h������#ͼƬ��С
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)
            # cc=time.gmtime()
            # bmpname=str(cc[0])+str(cc[1])+str(cc[2])+str(cc[3]+8)+str(cc[4])+str(cc[5])+'.bmp'
            _filename = filename.split('.')[0]
            bmpname = "%s.bmp" % (str(_filename))
            saveBitMap.SaveBitmapFile(saveDC, bmpname)
            Image.open(bmpname).save(bmpname[:-4] + ".jpg")
            os.remove(bmpname)
            jpgname = bmpname[:-4] + '.jpg'
            djpgname = jpg_path + jpgname
            copy_command = "move %s %s" % (jpgname, djpgname)
            os.popen(copy_command)

            # ���������־
            logfilename = '%s.log' % (filename.split('.')[0])
            logform = open('.\\logs\\%s\\%s.log' % (runtaskid, filename.split('.')[0]), 'w')
            logform.write(log_info)
            logform.close()
            # �ϴ���FTP
            # eczip = zf.ZipFile('.\\logs\\%s.zip'%(runtaskid),'w')
            ret, f = self._mqclient.createFTPClient()
            if ret < 0:
                print f
                return ret, f
            f.upload_file_ex('./logs/%s/%s' % (runtaskid, filename), '/Log/%s' % runtaskid)
            f.upload_file_ex('./logs/%s/%s' % (runtaskid, logfilename), '/Log/%s' % runtaskid)
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def CaptureScreen(self, runtaskid, filename, log_info):
        """
        ��������Agent����Log�б���һ�ݣ����ϴ�FTPһ��
        Args:
            runtaskid: ����id
            filename: ����ID
        Returns:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
        """
        try:
            print "CaptureScreen"
            im = ImageGrab.grab()
            if not os.path.exists('.\\logs\\%s' % runtaskid):
                os.makedirs('.\\logs\\%s' % runtaskid)

            # if filename.startswith('common\\'):
            #    filename = filename[7:]
            # ��������ͼ
            jpg_file = ".\\logs\\%s\\%s" % (runtaskid, filename)
            print "jpgfile = %s" % jpg_file
            im.save(jpg_file, 'jpeg')
            # ���������־
            logfilename = '%s.log' % (filename.split('.')[0])
            logform = open('.\\logs\\%s\\%s.log' % (runtaskid, filename.split('.')[0]), 'w')
            logform.write(log_info)
            logform.close()
            # �ϴ���FTP
            # eczip = zf.ZipFile('.\\logs\\%s.zip'%(runtaskid),'w')
            ret, f = self._mqclient.createFTPClient()
            if ret < 0:
                print f
                return ret, f
            f.upload_file_ex('./logs/%s/%s' % (runtaskid, filename), '/Log/%s' % runtaskid)
            f.upload_file_ex('./logs/%s/%s' % (runtaskid, logfilename), '/Log/%s' % runtaskid)

        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def CheckExitCode(self, output):
        exit_info = output[len(output) - 1]
        exit_info = exit_info.strip('\r\n')
        if exit_info.find('Exit code:') > 0:
            return int(exit_info[exit_info.find(":") + 1:])
        else:
            return 127

    def MonitorScriptProcess(self):
        '''
        ������̨���̺󣬼�ظý���״̬���������ָ��ʱ��û����Ӧ����ǿ�ƹر�
        '''
        Logging.getLog().debug("start up MonitorScriptProcess")
        startup_time = datetime.datetime.now()
        during_time = int(gl.g_ZHLCSystemSetting['CaseAllowedMaxRunTime']) * 60
        while (self._monitorScriptProcFlag):
            if (datetime.datetime.now() - startup_time).seconds > during_time:
                Logging.getLog().info(str(during_time))
                Logging.getLog().info(str((datetime.datetime.now() - startup_time).seconds))
                Logging.getLog().info(u"��̨���̳�ʱ����ִֹ��")
                cmd_str = 'taskkill /F /IM java.exe'
                # Logging.getLog().debug(cmd_str)
                si = subprocess.STARTUPINFO
                si.wShowWindow = subprocess.SW_HIDE
                proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                proc.wait()
                self._caseOutOfTimeFlag = True
                break
            time.sleep(0.1)
        Logging.getLog().debug("Exit MonitorScriptProcess")

    def deal_with_T2_dataset_list(self, dataset_list):
        """
        ����T2Э�鷵��ֵ
        :param dataset_list:
        :return:
        """
        try:
            data = {'message': ''}
            column = dataset_list[0][0]
            data['field'] = column
            values_list = []
            for i in dataset_list[0][1:]:
                i_new = []
                for j in i:
                    if isinstance(j, str):
                        i_new.append(j.replace("'", "''"))
                    elif isinstance(j, unicode):
                        i_new.append(j.replace("'", "''"))
                    elif isinstance(j, list):
                        if len(j) >= 50:
                            j = j[:40]
                        i_new.append(j)
                    else:
                        i_new.append(j)
                values_list.append(i_new)
                # ������sx_run_record�Ķ�����Ϣ����10�򱨴� fixme
                if len(str(values_list).replace(' ', '')) > 5000:
                    break
            Logging.getLog().info("cbs %s" % len(str(values_list)))
            # if values_list and len(str(values_list[0]).replace(' ', '')) > 10000:
            #     values_list = values_list[0]
            data['values_list'] = values_list
            return 0, data
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def deal_with_UFX_dataset_list(self, dataset_list):
        """
        ����UFXЭ�鷵��ֵ
        UFX ���ܻ᷵���������ݼ���һ����ͨ����Ϣ��һ�������ݽ����
        :param dataset_list:
        :return:
        """
        try:
            print "dataset_list####################################"
            print dataset_list
            if len(dataset_list) == 1:  # ֻ����ͨ����Ϣ
                data = {'message': '--'.join(dataset_list[0][1])}
                column = dataset_list[0][0]
                data['field'] = column
                values_list = []
                for i in dataset_list[0][1:]:
                    i_new = []
                    for j in i:
                        i_new.append(j.replace("'", "''"))
                    if len(str(values_list).replace(' ', '')) <= 90000:
                        values_list.append(i_new)
                data['values_list'] = values_list
            elif len(dataset_list) == 3:  # ��Ҫ�����ذ���
                data = {'message': '--'.join(dataset_list[0][1])}
                column = dataset_list[1][0]
                column1 = dataset_list[0][0]
                column2 = dataset_list[2][0]
                column.extend(column1)
                column.extend(column2)

                values_list = []
                all_i_new = []
                for i in dataset_list[1][1:]:
                    # i_new = []
                    for j in i:
                        if isinstance(j, float):
                            all_i_new.append(j)
                        else:
                            all_i_new.append(j.replace("'", "''"))
                            # if len(str(values_list).replace(' ', '')) <= 90000:
                            #     all_i_new.extend(i_new)
                for i in dataset_list[0][1:]:
                    # i_new = []
                    for j in i:
                        if isinstance(j, float):
                            all_i_new.append(j)
                        else:
                            all_i_new.append(j.replace("'", "''"))
                            # if len(str(values_list).replace(' ', '')) <= 90000:
                            #     all_i_new.extend(i_new)
                for i in dataset_list[2][1:]:
                    # i_new = []
                    for j in i:
                        if isinstance(j, float):
                            all_i_new.append(j)
                        else:
                            all_i_new.append(j.replace("'", "''"))
                            # if len(str(values_list).replace(' ', '')) <= 90000:
                            #     all_i_new.extend(i_new)
                dataset_list[1][1].extend(dataset_list[0][1])
                dataset_list[1][1].extend(dataset_list[2][1])
                values_list.append(all_i_new)
                data['field'] = column
                data['values_list'] = values_list
            else:
                data = {'message': '--'.join(dataset_list[0][1])}
                column = dataset_list[1][0]
                data['field'] = column
                values_list = []
                for i in dataset_list[1][1:]:
                    i_new = []
                    for j in i:
                        if isinstance(j, float):
                            i_new.append(j)
                        else:
                            i_new.append(j.replace("'", "''"))
                    if len(str(values_list).replace(' ', '')) <= 90000:
                        values_list.append(i_new)
                data['values_list'] = values_list
            return 0, data
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def RunHuaRuiScript(self, sdk, system_id, funcid, cmdstring, runtaskid, run_record_id, expect_ret):
        print sdk, funcid, cmdstring, expect_ret
        """
        ���л���ӿڽű�
        :param sdk: ���������
        :param system_id: ϵͳID
        :param funcid: ���ܺ�
        :param cmdstring: �������ַ���
        :param runtaskid: ��������ID
        :param run_record_id: ���м�¼��ID
        :param expect_ret: ����ֵ
        :return:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
            dataset_list: �м���ķ���ֵ�б����ں���������һ������
            return_json_string: �м������ֵ��json�ַ��������ظ�TestAgentServer����д�����ݿ�
            data_change_info_json_string:���ݿ�䶯��json�ַ��������ظ�TestAgentServer����д�����ݿ�
        """
        msg = ""
        log_info = ""
        dataset_list = [[]]
        return_json_string = ""
        data_change_info_json_string = ""
        try:
            in_param_dict = OrderedDict()
            # cmdstring = cmdstring.replace("&bfb&", "#")
            cmd_list = cmdstring.split('#')
            for i, inpar in enumerate(cmd_list):
                cmdStr = cmd_list[i].split("=")
                if len(cmdStr) == 2:
                    field, cmdValue = cmdStr
                    cmdValue = cmdValue.replace('&comma&', ',')
                    cmdValue = cmdValue.replace('&colon&', ':').replace("&bfb&", "#")
                else:
                    field = cmdStr[0]
                    cmdValue = ""
                if field == "in_param":
                    cmdValue = "{" + cmdValue + "}"
                    cmdValue = json.loads(cmdValue)
                ret, type = "", ""
                if field != "in_param":
                    ret, type = self.judge_data_type_order_field(funcid, field)
                print ret, type
                if ret != 0:
                    type = "str"
                if type == 'I':
                    cmdValue = int(cmdValue)
                if isinstance(cmdValue, (str, unicode)):
                    try:
                        cmdValue = json.loads(cmdValue)
                    except Exception as e:
                        pass
                if cmdValue != "":
                    in_param_dict[field] = cmdValue
            req_string = json.dumps(in_param_dict)
            print "req_string:%s" % req_string
            ret, rtn_msg = "", ""
            if not funcid:
                ret, rtn_msg = -1, u"���õ�funcid�ֶβ���Ϊ��!"
            else:
                ret, rtn_msg = sdk.send_msg(int(funcid), req_string)
            print ret, rtn_msg
            if str(ret) == str(expect_ret):
                succ_flag = True
            else:
                succ_flag = False
            data = {'message': '', 'field': [], 'values_list': [[]]}
            Logging.getLog().critical(rtn_msg)
            if "failed:" not in rtn_msg:
                try:
                    try:
                        rtn_dict = json.loads(rtn_msg, encoding='gbk', object_pairs_hook=OrderedDict)
                    except BaseException, ex:
                        rtn_dict = json.loads(rtn_msg, object_pairs_hook=OrderedDict)
                    for key in rtn_dict.keys():
                        if key == "out_param":
                            for key in rtn_dict["out_param"].keys():
                                if key == 'msg':
                                    if rtn_dict["out_param"][key]:
                                        data['message'] = rtn_dict["out_param"][key].encode('gbk')
                                        msg = rtn_dict["out_param"][key].encode('gbk')
                                    else:
                                        data['message'] = rtn_dict["out_param"][key]
                                        msg = rtn_dict["out_param"][key]
                                data['field'].append(key)
                                data['values_list'][0].append(rtn_dict["out_param"][key])
                        else:
                            if isinstance(rtn_dict[key], (unicode, str)):
                                data['field'].append(key)
                                data['values_list'][0].append(rtn_dict[key].decode('utf-8'))
                            else:
                                data['field'].append(key)
                                data['values_list'][0].append(rtn_dict[key])
                    dataset_list[0] = data['values_list'][0]
                    print dataset_list[0]
                except BaseException, ex:
                    exc_info = cF.getExceptionInfo()
                    Logging.getLog().error(exc_info)
                    log_info = rtn_msg
            else:
                try:
                    log_info = rtn_msg.decode("utf-8")
                except Exception as e:
                    try:
                        log_info = rtn_msg.decode("gbk")
                    except Exception as e:
                        log_info = rtn_msg
                        # if str(funcid) == "830166":
                        #     log_info = rtn_msg.decode("utf-8")
                        # else:
                        #     log_info = rtn_msg
            return_json_string = data
            data_change_info_json_string = ""
            print "succ_flag == %s" % succ_flag
            if succ_flag == True:
                return 0, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
            else:
                return -1, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (
                exc_info), log_info, [], return_json_string, data_change_info_json_string

    def judge_data_type_order_field(self, funcid, field):
        try:
            gl.g_interfaceDetailTree = ET.parse(".\\init\\%s\\T2InterfaceDetails.xml" % gl.current_system_id)
            func_root = gl.g_interfaceDetailTree.getroot()
            xpath = "Interface[@funcid='%s']" % (funcid)
            elem, type = "", ""
            try:
                elem = func_root.find(xpath)
            except Exception, ex:
                exc_info = cF.getExceptionInfo()
                Logging.getLog().critical("����judge_data_type_order_field �ù��ܺ� ������")
                Logging.getLog().critical("%s" % exc_info)
                return -1, "%s" % exc_info
            if not elem:
                return -1, "fail to find interface detail"
            for test in elem[0].getchildren():
                if test.attrib["name"] == field:
                    type = cF.judge_data_type(test.attrib["type"])
                    break
            return 0, type
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical("%s" % exc_info)
            return -1, "%s" % exc_info

    def RunHttpScript(self, system_id, cmdstring, task_id, run_record_id, case_name, group_variable_dict,
                      expected_value, interface_info):
        """
        ����Http�ӿڽű�
        :param system_id: ϵͳID
        :param funcid:
        :param cmdstring:
        :param runtaskid:
        :param run_record:
        :return:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
            dataset_list: �м���ķ���ֵ�б����ں���������һ������
            return_json_string: �м������ֵ��json�ַ��������ظ�TestAgentServer����д�����ݿ�
            data_change_info_json_string:���ݿ�䶯��json�ַ��������ظ�TestAgentServer����д�����ݿ�
        """
        msg, log_info, return_json_string, data_change_info_json_string = "", "", "", ""
        try:
            send_data = {}
            type, url = "", ''
            cmd_list = cmdstring.split("#")
            print interface_info
            for cmd in cmd_list:
                field_type = ""
                field = str(cmd.split("=")[0])
                value = cmd.split("=")[1].replace("&bfb&", "#")
                print field, value
                if field in interface_info.keys():
                    try:
                        field_type = interface_info[str(field)]
                    except:
                        pass
                if field == "httpurl":
                    url = value
                if field == "httpRequestMethod":
                    type = value
                if field not in ["httpurl", "httpRequestMethod"]:
                    if field_type == 'HttpList':
                        try:
                           send_data[field] = eval(value)
                        except:
                            return -1, u"�ֶ��������� field:%s, field_type:%s"%(field, field_type) , u"�ֶ��������� field:%s, field_type:%s"%(field, field_type), [],\
                                   return_json_string, data_change_info_json_string
                    elif field_type == 'HttpJson':
                        print "HttpJson"
                        try:
                            send_data[field] = eval(value)
                        except:
                            return -1, u"�ֶ��������� field:%s, field_type:%s"%(field, field_type) , u"�ֶ��������� field:%s, field_type:%s"%(field, field_type), [],\
                                   return_json_string, data_change_info_json_string
                    elif field_type == 'HttpInt':
                        print "HttpInt"
                        try:
                            send_data[field] = int(value)
                        except:
                            return -1, u"�ֶ��������� field:%s, field_type:%s"%(field, field_type) , u"�ֶ��������� field:%s, field_type:%s"%(field, field_type), [],\
                                   return_json_string, data_change_info_json_string
                    elif field_type == 'HttpFloat':
                        print "HttpFloat"
                        try:
                            send_data[field] = float(value)
                        except:
                            return -1, u"�ֶ��������� field:%s, field_type:%s"%(field, field_type) , u"�ֶ��������� field:%s, field_type:%s"%(field, field_type), [],\
                                   return_json_string, data_change_info_json_string
                    else:
                        send_data[str(field)] = value
            ret = 0
            dataset_list = []
            data = ""
            try:
                print send_data, "ur:%s" % url
                if type.lower() == "get":
                    r = ""
                    if send_data:
                        r = requests.get(url, params=send_data)
                        data = r.text
                    else:
                        r = requests.get(url)
                        data = r.text
                    status = r.status_code
                    if status == 200:
                        ret = 0
                    else:
                        ret = -1
                if type.lower() == "post":
                    r = ""
                    if send_data:
                        r = requests.post(url, data=json.dumps(send_data))
                        data = r.text
                    else:
                        r = requests.post(url)
                        data = r.text
                    status = r.status_code
                    if status == 200:
                        ret = 0
                    else:
                        ret = -1
            except Exception as e:
                exc_info = cF.getExceptionInfo()
                print exc_info
                data = "request address error, please check the address!  url:%s" % url
                ret = -1
            try:
                response_msg = json.loads(data)
                if isinstance(response_msg, list):
                    flag = True
                    for c in response_msg:
                        if not isinstance(c, dict):
                            flag = False
                    if flag:
                        dataset_list.append(response_msg[0].keys())
                        for c in response_msg:
                            dataset_list.append(c.values())
                    else:
                        dataset_list = [["response_msg"], [json.dumps(response_msg)]]
                elif isinstance(response_msg, dict):
                    dataset_list.append(response_msg.keys())
                    dataset_list.append(response_msg.values())
                else:
                    dataset_list = [["response_msg"], [json.dumps(response_msg)]]
            except:
                dataset_list = [["response_msg"], [data]]
            r, return_json_string = self.deal_with_T2_dataset_list([dataset_list])
            if r < 0:
                return_json_string = ""
            if ret == 0:
                return 0, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
            else:
                return -1, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical("%s" % exc_info)
            return -1, "%s" % exc_info, log_info, [], return_json_string, data_change_info_json_string

    def RunT2Script(self, sdk, system_id, funcid, cmdstring, runtaskid, run_record_id, expect_ret):
        """
        ����T2�ӿڽű�
        :param system_id: ϵͳID
        :param funcid:
        :param cmdstring:
        :param runtaskid:
        :param run_record:
        :return:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
            dataset_list: �м���ķ���ֵ�б����ں���������һ������
            return_json_string: �м������ֵ��json�ַ��������ظ�TestAgentServer����д�����ݿ�
            data_change_info_json_string:���ݿ�䶯��json�ַ��������ظ�TestAgentServer����д�����ݿ�
        """
        # Logging.getLog().debug('zzp:' + funcid + cmdstring)
        succ_flag = False
        msg = ""
        log_info = ""
        return_json_string = ""
        data_change_info_json_string = ""

        # Logging.getLog().debug("funcid=%s,cmdstring=%s,runtaskid=%s,run_record_id=%s,expect_ret=%s" %(funcid,cmdstring,runtaskid,run_record_id,expect_ret))
        # print cmdstring
        # print
        # FIXME DEBUG NOW
        # return 0,"fake ok","fake log_info",[],"",""

        try:
            dataset_list = []

            ret, msg = cF.ExecuteOneTestCase(sdk, funcid, cmdstring)

            rtn, timeout = zhlc.GetASYCfunctionTimeout(funcid)
            if timeout == "":
                timeout = 0
            if ret == 0 or ret == 1:
                dataset_list = cF.GetReturnRows(sdk)
                if timeout != 0:
                    Logging.getLog().debug("�ȴ��첽���ؽ����timeout = %s ��" % timeout)
                    time.sleep(int(timeout))
                if "DisableDBCompare" in gl.g_ZHLCSystemSetting.keys():
                    if gl.g_ZHLCSystemSetting["DisableDBCompare"] == "True":  # fixme
                        # TODO ��ȡ���ݿ�䶯ֵ������Oracle��SQL Server�䶯ֵ
                        data_chanret, data_change_info_json_string = self._mqclient.createResultJSON(system_id,
                                                                                                     runtaskid,
                                                                                                     run_record_id)
                        if data_chanret < 0:
                            # Logging.getLog().error(data_change_info_json_string)
                            data_change_info_json_string = ""

                # TODO ƴ���м������ֵ�����ݿ�䶯ֵΪһ��JSON�ַ��������ݻ�TestAgentServer
                r, return_json_string = self.deal_with_T2_dataset_list(dataset_list)
                if r < 0:
                    # Logging.getLog().error(return_json_string)
                    return_json_string = ""

                if ret == 0:
                    # ������һ�����裬������0��ʱ�򣬲������error_no���ֶΣ���ô���expect_idΪ����ֵʱ�����ж�����ʧ��
                    if int(expect_ret) != 0:
                        # TODO �ж�ʧ��
                        succ_flag = False
                    else:
                        # TODO �ж��ɹ�
                        succ_flag = True
                else:  # ret == 1
                    msg = cF.GetErrorInfoFromReturnRows(dataset_list)
                    rows_list = dataset_list[0]
                    error_no = ''
                    index_error_no = ""
                    if "error_no" in rows_list[0]:
                        index_error_no = rows_list[0].index("error_no")
                        error_no = rows_list[1][index_error_no]
                    Logging.getLog().debug(
                        "index_error_no:%s��error_no:%s, expect_ret:%s" % (index_error_no, error_no, expect_ret))
                    # if rows_list[0][1] == "error_no":  # ȷ����error_no �ֶ�
                    #     error_no = rows_list[1][1]
                    if error_no == '':  # �޷���ȷ��ȡerror_no
                        # TODO �ж�ʧ��
                        succ_flag = False
                    else:
                        if int(error_no) == int(expect_ret):  # ����Ԥ�ڣ��ж��ɹ�
                            # TODO �ж��ɹ�
                            succ_flag = True
                        else:
                            # TODO �ж�ʧ��
                            succ_flag = False

            else:
                # TODO �ж�ʧ��
                succ_flag = False
            # # �ر�T2Server ����
            # sdk.Close() #fixme
            # sdk.DeInitInterface()
            if succ_flag == True:
                return 0, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
            else:
                return -1, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (
                exc_info), log_info, [], return_json_string, data_change_info_json_string

    def RunUFXScript(self, sdk, system_id, funcid, cmdstring, runtaskid, run_record_id, expect_ret):
        """
        ����UFX�ӿڽű�
        :param system_id: ϵͳID
        :param funcid:
        :param cmdstring:
        :param runtaskid:
        :param run_record:
        :return:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
            dataset_list: �м���ķ���ֵ�б����ں���������һ������
            return_json_string: �м������ֵ��json�ַ��������ظ�TestAgentServer����д�����ݿ�
            data_change_info_json_string:���ݿ�䶯��json�ַ��������ظ�TestAgentServer����д�����ݿ�
        """
        succ_flag = False
        msg = ""
        log_info = ""
        return_json_string = ""
        data_change_info_json_string = ""
        try:
            dataset_list = []
            ret, msg = cF.ExecuteOneTestCase(sdk, funcid, cmdstring)
            rtn, timeout = zhlc.GetASYCfunctionTimeout(funcid)
            if timeout == "":
                timeout = 0
            if ret == 0 or ret == 1:
                dataset_list = cF.GetReturnRows(sdk)
                if timeout != 0:
                    Logging.getLog().debug("�ȴ��첽���ؽ����timeout = %s ��" % timeout)
                    time.sleep(int(timeout))
                if gl.g_ZHLCSystemSetting["DisableDBCompare"] == "True":  # fixme
                    data_chanret, data_change_info_json_string = self._mqclient.createResultJSON(system_id, runtaskid,
                                                                                                 run_record_id)
                    if data_chanret < 0:
                        data_change_info_json_string = ""
                r, return_json_string = self.deal_with_UFX_dataset_list(dataset_list)
                if r < 0:
                    return_json_string = ""
                if ret == 0:
                    if int(expect_ret) != 0:
                        succ_flag = False
                    else:
                        succ_flag = True
                else:  # ret == 1
                    msg = cF.GetErrorInfoFromReturnRows(dataset_list)
                    rows_list = dataset_list[0]
                    error_no = ''
                    if rows_list[0][1] == "error_no":  # ȷ����error_no �ֶ�
                        error_no = rows_list[1][1]
                    if error_no == '':  # �޷���ȷ��ȡerror_no
                        succ_flag = False
                    else:
                        if int(error_no) == int(expect_ret):  # ����Ԥ�ڣ��ж��ɹ�
                            succ_flag = True
                        else:
                            succ_flag = False
            else:
                succ_flag = False
            if succ_flag == True and len(dataset_list) == 1:
                dataset_list.insert(0, [[], []])
            else:
                if len(dataset_list) < 2:
                    succ_flag = False
                    log_info = u"��¼ʧ��"
            if succ_flag == True:
                return 0, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
            else:
                return -1, msg, log_info, dataset_list, return_json_string, data_change_info_json_string
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (
                exc_info), log_info, [], return_json_string, data_change_info_json_string

    def deal_with_KCBP_dataset_list(self, dataset, msg):
        """
                ����KCBP����ֵ
                :param dataset_list:
                :param_msg:
                :return:
                """
        try:
            data = {"message": "%s" % msg}
            column = dataset[0]
            data["field"] = column
            values_list = []
            for i in dataset[1:]:
                values_list.append(i)
            if len(values_list) > 50:
                values_list = values_list[:50]
            data["values_list"] = values_list
            # str_data = json.dumps(data, ensure_ascii=False, indent=4, encoding='utf-8')
            return 0, data
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info

    def RunKCBPScirpt(self, system_id, serverid, funcid, cmdstring, runtaskid, run_record_id, expect_ret):
        """
        ����KCBP�ӿڽű�
        :param system_id:
        :param handle:
        :param cli:
        :param funcid:
        :param cmdstring:
        :param runtaskid:
        :param run_record_id:
        :param expect_ret:
        :return:
         һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
            dataset_list: �м���ķ���ֵ�б����ں���������һ������
            return_json_string: �м������ֵ��json�ַ��������ظ�TestAgentServer����д�����ݿ�
            data_change_info_json_string:���ݿ�䶯��json�ַ��������ظ�TestAgentServer����д�����ݿ�
        """
        dataset = []
        msg = ""
        log_info = ""
        return_json_string = ""
        data_change_info_json_string = ""
        succ_flag = False
        try:
            if cmdstring.find("g_serverid=") >= 0:
                id_list = re.findall(r"g_serverid=(.+?)#", cmdstring)
                if len(id_list) > 0:
                    serverid_ = id_list[0]
                    try:
                        serverid = int(serverid_)
                        gl.g_server_id = serverid
                        cF.readSystemConfigFile(system_id)
                    except:
                        pass
                else:
                    cmdstring = cmdstring.replace("g_serverid=", "g_serverid=%s"%serverid)
            print "serverid:%s"%serverid
            hHandle, cli = cF_kcbp.KCBPCliInit(serverid)
            if hHandle < 0:
                Logging.getLog().info(u"��ʼ��KCBPCli�ӿ�ʧ��")
                return -1, u"��ʼ��KCBPCli�ӿ�ʧ��", "", [], "", ""
            ret, code, level, msg = cF_kcbp.SendRequest(hHandle, cli, cmdstring)

            error_code = int(code)
            if int(code) != 0:
                if str(funcid):  # ('410490', '410561', "410416")
                    try:
                        error_code = int(msg[:10])
                    except:
                        pass
                # ȥ��ȡ��ȷ�Ĵ������ֵ
                # ��msg��ȥ��ȡ������ж��[]��ȡ���һ���������ȫû�У��͵���code��ֵ
                if msg.__contains__('[-') and msg.__contains__(']'):
                    left_pos = msg.rfind('[-')
                    right_pos = msg.find(']', left_pos)
                    if right_pos > left_pos:
                        print msg
                        print "error_code = %s" % error_code
                        error_code = int(msg[left_pos + 1:right_pos])
                else:
                    error_code = '-1'
                    # if str(funcid) == '410490':
                    #     error_code = int(msg[:10])
                    # # ȥ��ȡ��ȷ�Ĵ������ֵ
                    # # ��msg��ȥ��ȡ������ж��[]��ȡ���һ���������ȫû�У��͵���code��ֵ
                    # else:
                    #     left_pos = msg.rfind('[-')
                    #     right_pos = msg.find(']', left_pos)
                    #
                    #     if right_pos > left_pos:
                    #         error_code = int(msg[left_pos + 1:right_pos])

            # ��ȡ����ֵ
            if str(error_code).__contains__('-') or str(error_code) == '90002':
                error_code = -1
            if ret == 0:
                # dataset_list = GetReturnRows(sdk)
                if (int(code) != 0):
                    dataset.append(["code", "level", "msg"])
                    dataset.append([code, level, msg])
                else:
                    dataset = cF_kcbp.GetReturnResult(hHandle, cli)

                # ƴ���м�����غ����ݿ�䶯��Ϣ
                data_chanret, data_change_info_json_string = self._mqclient.createResultJSON(system_id, runtaskid,
                                                                                             run_record_id)
                if data_chanret < 0:
                    # Logging.getLog().error(data_change_info_json_string)
                    data_change_info_json_string = ""

                # TODO ƴ���м������ֵ�����ݿ�䶯ֵΪһ��JSON�ַ��������ݻ�TestAgentServer
                r = 0
                if dataset:
                    print "dataset:%s" % dataset
                    r, return_json_string = self.deal_with_KCBP_dataset_list(dataset, msg)
                if r < 0:
                    # Logging.getLog().error(return_json_string)
                    return_json_string = ""

                if int(code) == 0:
                    # ������һ�����裬������0��ʱ�򣬲������error_no���ֶΣ���ô���expect_idΪ����ֵʱ�����ж�����ʧ��
                    if int(expect_ret) != 0:
                        succ_flag = False
                    else:
                        succ_flag = True
                else:  # int(code)<0
                    if (int(expect_ret) == int(error_code)):
                        succ_flag = True
                    else:
                        succ_flag = False
            else:
                succ_flag = False

            cF_kcbp.KCBPCliExit(hHandle, cli)
            print "return_json_string:%s" % return_json_string
            if succ_flag == True:
                return 0, msg, log_info, dataset, return_json_string, data_change_info_json_string
            else:
                return -1, msg, log_info, dataset, return_json_string, data_change_info_json_string
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)
            return -1, exc_info, log_info, [], return_json_string, data_change_info_json_string

    def RunSeleniumScript(self, system_id, funcid, param_data_id, runtaskid, run_record_id):
        """
        ����Selenium�ű���Seleniumʹ����ͳһ��һ���ű���ͨ�������Ĵ�����������ع��ܡ�
        Args:
            system_id: ϵͳID
            funcid: �Ѿ���������ƴ�ӵ����
            param_data_id: ������������id
            runtaskid:��������ID
            CASE_NAME:��������
            run_record_id: ���м�¼ID
            
        Returns:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
        """
        output_info_list = []
        log_info = ""

        cmd_str = 'java -jar .\\Script\\JZYYAutoTest.jar %s %s' % (funcid, param_data_id)

        try:
            # ��������߳�
            self._monitorScriptProcFlag = True
            self._caseOutOfTimeFlag = False
            t = threading.Thread(target=self.MonitorScriptProcess)
            t.start()

            si = subprocess.STARTUPINFO
            si.wShowWindow = subprocess.SW_HIDE
            Logging.getLog().debug("ready to execute %s" % cmd_str)
            proc = subprocess.Popen(cmd_str, shell=True,
                                    startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.PIPE)

            while proc.poll() is None:
                line = proc.stdout.readline()
                line = line.strip()
                if line:
                    output_info_list.append(line)
                    # Logging.getLog().debug("%s" % line)

            # �˳�����߳�
            Logging.getLog().debug("quit subprocess with returncode = %s" % str(proc.returncode))

            # output_info = proc.stdout.readlines()
            # log_info = "".join(output_info_list)
            exit_code = proc.returncode
            # �˳�����߳�
            self._monitorScriptProcFlag = False
            # print output_info
            # print exit_code
            # output_info = proc.stdout.readlines()
            # Logging.getLog().debug(output_info)
            # exit_code = proc.returncode
            # Logging.getLog().debug("return code is %s" % str(exit_code))

            log_info = '\n'.join(output_info_list).decode('gbk')

            if self._caseOutOfTimeFlag == True:
                log_info = log_info + "\r\n Cases be killed by Monitor process because of out of time"
                self._caseOutOfTimeFlag = False

            if int(exit_code) != 0:
                self.CaptureScreen(runtaskid, "%s.jpg" % (run_record_id), log_info)
                Logging.getLog().critical(u"�ű�δ�����˳���������־�ļ�")
                return -1, u"�ű�δ�����˳���������־�ļ�", log_info, ""

            ret, str_data_change_json = self._mqclient.createResultJSON(system_id, runtaskid, run_record_id)
            if ret < 0:
                return -1, str_data_change_json, log_info, ""
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info), log_info, ""
        return 0, "", log_info, str_data_change_json

    def RunGjSilkTestScript(self, system_id, cmdstring, runtaskid, run_record_id, group_variable_dict, EXPECTED_VALUE):
        """
        ���� ����SilkTest�ű���SilkTestʹ����ͳһ��һ���ű���ͨ�������Ĵ�����������ع��ܡ�
        Args:
            system_id: ϵͳID
            funcid: �Ѿ���������ƴ�ӵ����
            param_data_id: ������������id
            runtaskid:��������ID
            CASE_NAME:��������
            run_record_id: ���м�¼ID

        Returns:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
        """
        output_info_list = []
        log_info = ""
        cmdstring_list = cmdstring.split("#")
        cmd = {}
        for param in cmdstring_list:
            key, value = param.split("=")
            try:
                value = json.loads(value)
            except Exception as e:
                pass
            cmd[key] = value
        cmd = json.dumps(cmd)
        homedir = os.getcwd()
        path = homedir + "\\myParam.txt"
        f = open(path, 'w')
        f.write(cmd)
        f.close()
        cmd_str = 'java -jar .\\Script\\gjTdx.jar "%s"' % path
        Logging.getLog().debug(cmd_str)
        try:
            # ��������߳�
            self._monitorScriptProcFlag = True
            self._caseOutOfTimeFlag = False
            t = threading.Thread(target=self.MonitorScriptProcess)
            t.start()

            si = subprocess.STARTUPINFO
            si.wShowWindow = subprocess.SW_HIDE
            Logging.getLog().debug("ready to execute %s" % cmd_str)
            proc = subprocess.Popen(cmd_str, shell=True,
                                    startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.PIPE)
            lines = proc.stdout.read()
            self._monitorScriptProcFlag = False
            log_info = lines.decode('gbk')
            print log_info
            return_json_string = {"field": [],
                                  "message": "OK",
                                  "values_list": []}
            # ReturnValue = log_info.split("ReturnValue:")[1]
            # ReturnValue = ReturnValue.split("##")[1]
            # ReturnValue = json.loads(ReturnValue)
            ReturnValue = self.GetReturnValue(log_info)
            message = ReturnValue["message"]
            ret = message["result"]
            if str(ret) == '-1' and str(EXPECTED_VALUE) == '-1':
                return 0, "ok", log_info, "", return_json_string, ""
            if ret == "0":
                if ReturnValue["other"]:
                    for i in ReturnValue["other"]:
                        group_variable_dict[i] = ReturnValue["other"][i]
                    return_json_string["field"] = ReturnValue["other"].keys()
                    return_json_string["values_list"].append(ReturnValue["other"].values())
            else:
                return_json_string = ""
                self.CaptureScreen(runtaskid, "%s.jpg" % (run_record_id), log_info)
                Logging.getLog().critical(u"�ű�δ�����˳���������־�ļ�")
                return -1, u"�ű�δ�����˳���������־�ļ�", log_info, "", return_json_string, ""
            msg = log_info
            if ret == '0':
                return 0, msg, log_info, "", return_json_string, ""
            else:
                return -1, msg, log_info, "", return_json_string, ""
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info), log_info, ""

    def GetSilktestScriptName(self, script_name, src):
        n = src.find('#script=')
        old_name = script_name
        try:
            if n == -1:
                if src[:7] == 'script=':
                    n = 0
                    script_name = src[7:]
                    n = script_name.find('#')
                    if n >= 0:
                        script_name = script_name[:n]
            else:
                script_name = src[n + 8:]
                n = script_name.find('#')
                if n >= 0:
                    script_name = script_name[:n]
            if old_name == script_name:
                Logging.getLog().info("Silktest Script Name use default one")
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
        return script_name

    def GetReturnValue(self, log_info):
        rt = {'other': {}, 'message': {'result': '-1', 'text': 'fail'}}
        try:
            ReturnValue = log_info.split("ReturnValue:")[1]
            ReturnValue = ReturnValue.split("##")[1]
            ReturnValue = json.loads(ReturnValue)
            rt = ReturnValue
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
        return rt

    def RunSilktestScript(self, system_id, cmdstring, runtaskid, run_record_id, CASE_NAME, group_variable_dict,
                          EXPECTED_VALUE):
        """

        ����Silktest�ű���Silktestʹ����ͳһ��һ���ű���ͨ�������Ĵ�����������ع��ܡ�
        Args:
            system_id: ϵͳID
            funcid: �Ѿ���������ƴ�ӵ����
            param_data_id: ������������id
            runtaskid:��������ID
            CASE_NAME:��������
            run_record_id: ���м�¼ID

        Returns:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
        """
        Logging.getLog().debug(u"RunSilktestScript:cmdstring:%s" % (cmdstring))
        script_name = CASE_NAME
        output_info_list = []
        log_info = ""
        try:
            args = cmdstring.split("#")
            script_name = self.GetSilktestScriptName(script_name, cmdstring)
            for j in args:
                if j.startswith('script='):
                    args.remove(j)
                    break
            args = ['"' + i + '"' for i in args]
            args = [' ' + i for i in args]
            args = ",".join(args).replace(",", "")
            # cmd_str = 'stw -dsn SilkTest -u admin -p admin -r "GTJA_POC" -script "SJWT" -variable "password=990818" "code=600000" "type=sjwt"'
            cmd_str = ' -script "%s" -variable %s' % (script_name, args)
            cmd_str = gl.CMD_SPLX_SILKTEST + cmd_str
            cmd_str = cmd_str.encode("gbk")
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
        Logging.getLog().debug("cmd %s" % cmd_str)
        try:
            # ��������߳�
            self._monitorScriptProcFlag = True
            self._caseOutOfTimeFlag = False
            t = threading.Thread(target=self.MonitorScriptProcess)
            t.start()

            si = subprocess.STARTUPINFO
            si.wShowWindow = subprocess.SW_HIDE
            Logging.getLog().debug("ready to execute %s" % cmd_str)
            proc = subprocess.Popen(cmd_str, shell=True,
                                    startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.PIPE)

            while proc.poll() is None:
                line = proc.stdout.readline()
                line = line.strip()
                if line:
                    output_info_list.append(line)
            # �˳�����߳�
            Logging.getLog().debug("quit subprocess with returncode = %s" % str(proc.returncode))
            exit_code = proc.returncode
            # �˳�����߳�
            self._monitorScriptProcFlag = False

            log_info = '\n'.join(output_info_list).decode('gbk')

            return_json_string = {"field": [],
                                  "message": "OK",
                                  "values_list": []}
            ReturnValue = self.GetReturnValue(log_info)
            message = ReturnValue["message"]
            ret = message["result"]
            if str(ret) == '-1' and str(EXPECTED_VALUE) == '-1':
                return 0, "ok", log_info, "", return_json_string, ""
            if ret == "0":
                if ReturnValue["other"]:
                    for i in ReturnValue["other"]:
                        group_variable_dict[i] = ReturnValue["other"][i]
                    return_json_string["field"] = ReturnValue["other"].keys()
                    return_json_string["values_list"].append(ReturnValue["other"].values())
            else:
                return_json_string = ""
                self.CaptureScreen(runtaskid, "%s.jpg" % (run_record_id), log_info)
                Logging.getLog().critical(u"�ű�δ�����˳���������־�ļ�")
                return -1, u"�ű�δ�����˳���������־�ļ�", log_info, "", return_json_string, ""
            msg = log_info
            if ret == '0':
                return 0, msg, log_info, "", return_json_string, ""
            else:
                return -1, msg, log_info, "", return_json_string, ""
                #     return -1, u"�ű�δ�����˳���������־�ļ�", log_info, ""

                # ret, str_data_change_json = self._mqclient.createResultJSON(system_id, runtaskid, run_record_id)
                # if ret < 0:
                #     return -1, str_data_change_json, log_info, ""
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info), log_info, ""

    def RunAppiumScript(self, system_id, cmdstring, runtaskid, run_record_id):
        """
        ����Appium�ű���APPIUMʹ����ͳһ��һ���ű���ͨ�������Ĵ�����������ع��ܡ�
        Args:
            system_id: ϵͳID
            cmdstring: �Ѿ���������ƴ�ӵ����
            runtaskid:��������ID
            run_record_id: ���м�¼ID
            core_script_name: ���Ľű�������Ϊ���к��Ľű���֮ǰ����Ҫ���õ�¼�ű�����Ϊ�˽���ͼ�����ֻ��ɺ��Ľű������ڴ˴��룩
        Returns:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
        """

        log_info = ""

        cmd_str = 'java -jar .\\Script\\AutoTest.jar "%s"' % cmdstring
        # print cmd_str
        # open("run_appium_script.bat","w").write(cmd_str.encode('gb2312'))



        # return 0,"OK","Fake execute successful"

        try:
            # ��������߳�
            self._monitorScriptProcFlag = True
            self._caseOutOfTimeFlag = False
            t = threading.Thread(target=self.MonitorScriptProcess)
            t.start()

            # ����appium Server����Ϊappium server �ᾭ�����ȶ�������ÿ��ִ��һ��appium�ű�ǰ����������appium server

            # ȷ��appium �Ƿ�����״̬
            self._mqclient.stop_appium_server()
            Logging.getLog().debug("begin to start start_appium_server ")

            appium_thread = threading.Thread(target=self._mqclient.start_appium_server)
            appium_thread.start()

            # �ȴ�appium�������
            while self._mqclient._appium_is_started == False:
                Logging.getLog().debug("waiting for appium server started")
                time.sleep(0.1)
            Logging.getLog().debug("appium server is started")

            #############fixme debug use this method process keep blocking ,I dont'know why yet #######################3
            # si = subprocess.STARTUPINFO
            # si.wShowWindow = subprocess.SW_HIDE
            # Logging.getLog().debug("ready to execute")
            # proc = subprocess.Popen("run_appium_script.bat", shell=True, startupinfo=si, stdout=subprocess.PIPE,
            #                         stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            # proc.wait()

            print cmd_str
            f = os.popen(cmd_str.encode('gb2312'))
            output_info = f.read()
            exit_code = f.close()
            if exit_code == None:
                exit_code = 0

            # �˳�����߳�
            self._monitorScriptProcFlag = False
            print output_info
            print exit_code
            # output_info = proc.stdout.readlines()
            Logging.getLog().debug(output_info)
            # exit_code = proc.returncode
            Logging.getLog().debug("return code is %s" % str(exit_code))

            log_info = ''.join(output_info).decode('gbk')

            if self._caseOutOfTimeFlag == True:
                log_info = log_info + "\r\n Cases be killed by Monitor process because of out of time"
                self._caseOutOfTimeFlag = False

            if int(exit_code) != 0:
                self.upload_appium_capture(runtaskid, run_record_id, 'AutoTest.jar')
                Logging.getLog().critical(u"�ű�δ�����˳���������־�ļ�")
                return -1, u"�ű�δ�����˳���������־�ļ�", log_info, ""

            ret, str_data_change_json = self._mqclient.createResultJSON(system_id, runtaskid, run_record_id)
            if ret < 0:
                return -1, str_data_change_json, log_info, ""
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info), log_info, ""
        return 0, "", log_info, str_data_change_json

    def RunSikuliScript(self, system_id, need_login, cmdstring, param, runtaskid, run_record_id, core_script_name=""):
        """
        ����sikuli�ű�
        Args:
            need_login: �Ƿ���Ҫ�ȵ�¼,����Agent��¼ 0 ����½��1 ��¼
            username: ��¼�û���
            password: ��¼����
            cmdstring: sikuli�ű�����·������Թ���Ŀ¼�����·����
            param���ű����� ����"stkcode=xxxxxx#qty=xxx"
            runtaskid:��������ID
            run_record_id: ���м�¼ID
            CASE_NAME: ��������
            core_script_name: ���Ľű�������Ϊ���к��Ľű���֮ǰ����Ҫ���õ�¼�ű�����Ϊ�˽���ͼ�����ֻ��ɺ��Ľű������ڴ˴��룩
        Returns:
            һ��Ԫ�飨ret��msg����
            ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
            msg : ��Ӧ��Ϣ
            log_info : ��־��Ϣ
        """
        # ����ƴ��

        param_list = []
        param_list.append(need_login)

        if param != "":
            for item in param.split('#'):
                param_list.append(item.split('=')[1])

        log_info = ""

        cmd_str = "%s -r %s -- %s" % (
            gl.g_sikuli_path, os.path.join(gl.g_sikuli_script_dir, cmdstring), " ".join(param_list))
        Logging.getLog().info(cmd_str)

        try:
            # ��������߳�
            self._monitorScriptProcFlag = True
            self._caseOutOfTimeFlag = False
            t = threading.Thread(target=self.MonitorScriptProcess)
            t.start()

            ##############fixme debug#######################3
            si = subprocess.STARTUPINFO
            si.wShowWindow = subprocess.SW_HIDE
            Logging.getLog().debug("ready to execute")
            proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            proc.wait()

            # �˳�����߳�
            self._monitorScriptProcFlag = False
            Logging.getLog().debug("quit subprocess")

            output_info = proc.stdout.readlines()
            exit_code = self.CheckExitCode(output_info)
            log_info = ''.join(output_info)

            log_info = log_info.decode('gbk')

            if self._caseOutOfTimeFlag == True:
                log_info = log_info + "\r\n Cases be killed by Monitor process because of out of time"
                self._caseOutOfTimeFlag = False

            if int(exit_code) != 0:
                filename = cmdstring
                if cmdstring.startswith('common\\'):
                    filename = core_script_name

                self.CaptureScreen(runtaskid, "%s.jpg" % (run_record_id), log_info)
                # self.window_capture(runtaskid, "%s.jpg" % (run_record_id), log_info)
                Logging.getLog().critical(u"�ű�δ�����˳���������־�ļ�")
                return -1, u"�ű�δ�����˳���������־�ļ�", log_info, ""
            ret, str_data_change_json = self._mqclient.createResultJSON(system_id, runtaskid, run_record_id)
            if ret < 0:
                return -1, str_data_change_json, log_info, ""
        except BaseException, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().critical(u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info))
            return -1, u"�쳣������������־�ļ�,��ʾ��ϢΪ:%s" % (exc_info), log_info, ""
        return 0, "", log_info, str_data_change_json

    def getUserAndPassFromParam(self, param):
        s = param.find('user=')
        l = param.find('#')
        user = param[s + 5:l]

        s = param.find('pass=')
        l = param.find('#', s)
        if (l < 0):
            password = param[s + 5:]
        else:
            password = param[s + 5:l]
        return user, password

    def killFuyiProcess(self):
        cmd_str = 'taskkill /F /IM TdxW.exe'
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        proc.wait()
        cmd_str = 'taskkill /F /IM RichEZ.exe'
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        proc.wait()

    def down_load_file(self, system_id):
        homedir = os.getcwd()
        system_id = str(system_id).upper()
        suffix = cF.get_suffix(system_id)
        if os.path.exists("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix)):
            os.remove("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix))
        if os.path.exists("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id)):
            os.remove("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id))

        # �ӷ�������������ļ�
        try:  # fixme
            f = XFer(self._mqclient._setting['FTPServer']['IP'], self._mqclient._setting['FTPServer']['USER'], self._mqclient._setting['FTPServer']['PASSWORD'], '.',
                                 int(self._mqclient._setting['FTPServer']['PORT']))
            f.login()
            homedir = os.getcwd()
            system_id = str(system_id).upper()
            f.download_files(r'%s\init\%s' % (homedir, system_id), r'.\init\%s' % system_id)
        except Exception, ex:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().error(exc_info)

    def processCaseDistrubtionMsg(self, msg):
        '''
        ���շַ���Ϣ����һִ��ÿһ�����裬�����ʧ�ܵ��������Ҫɨ��һ�´�ִ�а����к�����صİ������裬��������Ϊ����״̬��
        '''
        try:
            # ���㰸����������Ǩ�ƺͳɽ����
            gl.restart_execute_many_row = {"220105": [], "220205": [], "220120": []}
            # �������İ�������
            print "server_id:%s" % msg['server_ids']
            serverid = msg['server_ids']
            if serverid:
                gl.execute_many_row[str(serverid)] = gl.restart_execute_many_row
            iter_group_variable_dict = []
            gl.case_state = "STATE_RUNNING"
            collect_task_id = ""
            case_result_msg = {}
            testResultBody = {}
            group_variable_dict = {}
            # ����������������
            skip_left_steps = False
            skip_left_steps_cases_param_data_id = -1
            # ���һ�εİ�������ID�����������Ƿ���������
            last_cases_param_data_id = -1
            return_json_string = ""  # �м������ֵ��JSON�� ֻ�Խӿڼ��������Ч
            data_change_info_json_string = ""  # ���ݿ�䶯��JSON��
            testResultList = []
            Logging.getLog().debug("GetCaseDistrubtionMsg %s" % msg)
            msg_object = msg
            msg_body = msg_object["msg_body"]
            system_id = msg_body["system_id"]
            in_param_legal = False
            if 'in_param_legal' in msg_body.keys():
                in_param_legal = msg_body["in_param_legal"]
            gl.current_system_id = system_id
            # ����ϵͳ�����ļ�, ÿ��ϵͳ�������ļ���������ͬ���������ݲ�ͬ�������ڲ�ͬ��Ŀ¼�¡�
            cF.readSystemConfigFile(system_id)
            # ��װӦ����Ϣͷ
            debug_last_run_record_id = 0
            # T2Server ������
            t2sdk = None
            hr_quant_handle = gl.hr_quant_handle
            if hr_quant_handle:
                print "�Ѿ�����hr_quant_handle"
            hr_csm_handle = gl.hr_csm_handle
            if hr_csm_handle:
                print "�Ѿ�����hr_csm_handle"
            case_adapter_type = ""
            case_pres_pros_incloud_updateDict = False
            INIT_CASE_NAME = ""
            gl.return_account_update = {}
            gl.return_account_insert = {}
            gl.account_info = {}
            agent_id_info = []
            for i, case in enumerate(msg_body["cases"]):
                run_record_id = case["RUN_RECORD_ID"]
                if gl.running_agent_id == "":
                    gl.running_agent_id = 1
                agent_id_info.append({"RUN_RECORD_ID": run_record_id, "agent_id": int(gl.running_agent_id)})
            if agent_id_info:
                self._mqclient._redis_client.set_agent_id_data_list(
                    json.dumps(agent_id_info, ensure_ascii=False, encoding="gbk"))
            if "run_record_info" not in msg.keys():
                msg['run_record_info'] = ""
            run_record_info = msg['run_record_info']
            for i, case in enumerate(msg_body["cases"]):
                # �������İ�������   �Ҷ�Ӧ���ĵļ�¼
                if run_record_info:
                    for sigle_run_record_info in run_record_info:
                        if str(serverid) != str(sigle_run_record_info['RUN_SERVER_ALIAS']): continue
                        if case["CASES_ID"] != sigle_run_record_info['CASES_ID']: continue
                        if case["PARAM_DATA_ID"] != sigle_run_record_info['PARAM_DATA_ID']: continue
                        if case["TASK_ID"] != sigle_run_record_info['TASK_ID']: continue
                        if case["STEP"] != sigle_run_record_info['STEP']: continue
                        if case["CASES_PARAM_DATA_ID"] != sigle_run_record_info['CASES_PARAM_DATA_ID']: continue
                        if case["CASES_DETAIL_ID"] != sigle_run_record_info['CASES_DETAIL_ID']: continue
                        case["RUN_RECORD_ID"] = sigle_run_record_info['RUN_RECORD_ID']
                        print sigle_run_record_info['RUN_RECORD_ID']
                        break

                # 032ѭ������ִ��
                gl.o32_for_flag = False
                gl.o32_for_running_flag = False
                gl.o32_for_field = {}
                gl.o32_pro_disableflag = False
                if case["STEP_NAME"] == None or case["STEP_NAME"] == "" or case["STEP_NAME"] == "null":
                    case["STEP_NAME"] = ""
                STEP_NAME = ""
                if "STEP_NAME" in case.keys():
                    STEP_NAME = case["STEP_NAME"]
                if "for_running" in STEP_NAME:
                    gl.o32_for_running_flag = True
                elif "for" in STEP_NAME:
                    gl.o32_for_flag = True
                else:
                    pass
                ###########032###########
                gl.return_check_data = {}
                testResult = {}
                # testResult["agentid"] = int(gl.running_agent_id)
                testResult["run_start_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                INIT_CASE_NAME = case["CASE_NAME"]
                # ��ʼ��һִ�в�������
                # ������ݿ�䶯���
                # self._mqclient.clear_data_change_table(system_id)
                task_id = case["TASK_ID"]
                collect_task_id = task_id
                run_record_id = case["RUN_RECORD_ID"]
                param_data_id = case["PARAM_DATA_ID"]
                server_type = case["SERVER_TYPE"]
                if case["PARAM_INDEX"] == '' or case["PARAM_INDEX"] == None:
                    param_index = 0
                else:
                    param_index = int(case["PARAM_INDEX"])
                account_group_id = int(case['ACCOUNT_GROUP_ID'])
                funcid = case["FUNCID"]
                cmdstring = case["CMDSTRING"]
                deep_cmdstring = copy.deepcopy(cmdstring)
                adapter_type = case["ADAPTER_TYPE"]
                # �������Ӳ���ȫ�ֱ���,ha_exit����֮��,��������
                if case["PRE_ACTION"]:
                    if "ha_exit" in case["PRE_ACTION"]:
                        hr_quant_handle = ""
                        hr_csm_handle = ""
                case_adapter_type = adapter_type
                # ����ȫ����������
                gl.g_case_adapter_type = adapter_type
                dataset = []
                # serverid = 0
                # if adapter_type == 'SPLX_KCBP':
                # serverid = cF_kcbp.GetServeridByServerType(server_type)
                Logging.getLog().info(u"------download system files------")
                if self._mqclient._last_task_id != task_id:
                    runtaskid = self._mqclient._last_task_id
                    self._mqclient._last_task_id = task_id
                    # ����һЩ����ʼʱ�ĳ�ʼ������
                    # system_db_info, system_db_table_column_disable_info =  self._mqclient._server_proxy.rpc_get_system_db_info()
                    # self._mqclient._system_db_info = json.loads(system_db_info)
                    # self._mqclient._system_db_table_column_disable_info = json.loads(system_db_table_column_disable_info)
                    self._mqclient.ProcessScriptUpdateMsg()
                    # self._mqclient.readSystemConfigFile(system_id)
                    homedir = os.getcwd()
                    system_id = str(system_id).upper()
                    suffix = cF.get_suffix(system_id)
                    if os.path.exists("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix)):
                        os.remove("%s\init\%s\%s" % (homedir, system_id, '%sAccountGroupSetting.xml' % suffix))

                    if case["ADAPTER_TYPE"] == "SPLX_KCBP":
                        if os.path.exists("%s\\init\\%s\\ZHLCAutoTestSetting_%s.xml" % (
                                homedir, system_id, serverid)):
                            os.remove("%s\\init\\%s\\ZHLCAutoTestSetting_%s.xml" % (
                                homedir, system_id, serverid))
                    else:
                        if os.path.exists("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id)):
                            os.remove("%s\\init\\%s\\ZHLCAutoTestSetting.xml" % (homedir, system_id))

                    # �ӷ�������������ļ�
                    try:  # fixme
                        f = XFer(self._mqclient._setting['FTPServer']['IP'], self._mqclient._setting['FTPServer']['USER'], self._mqclient._setting['FTPServer']['PASSWORD'], '.',
                                 int(self._mqclient._setting['FTPServer']['PORT']))
                        f.login()
                        homedir = os.getcwd()
                        system_id = str(system_id).upper()
                        f.download_files(r'%s\init\%s' % (homedir, system_id), r'.\init\%s' % system_id)
                    except Exception, ex:
                        exc_info = cF.getExceptionInfo()
                        Logging.getLog().error(exc_info)

                    #ͬһ��������Ҫ��ʼ��
                    gl.g_connectOracleSetting = {}
                    gl.g_connectSqlServerSetting = {}
                    if gl.g_server_ids:
                        for s in gl.g_server_ids:
                            gl.g_server_id = s
                            cF.readSystemConfigFile(system_id)
                        bizmod.traversalDir_XMLFile(system_id)
                    else:
                        cF.readSystemConfigFile(system_id)
                    # ����oracel�����ļ�
                    cF.add_tnsnames_info()
                    if case["ADAPTER_TYPE"] == 'SPLX_SELENIUM':
                        excel_data = msg["excel_data"]
                        export_excel.get_sx_cases_info_export_excel(excel_data, system_id)
                try:
                    if i == 0:
                        pres = case["PRE_ACTION"]
                        pros = case["PRO_ACTION"]
                        if pres == None:
                            pres = ""

                        if "executeAccountInit" in pres:
                            ip = ''
                            port = ''
                            ip_port = re.findall('(\d+\.\d+\.\d+\.\d+)\,(\d+)', pres)
                            if ip_port:
                                ip = ip_port[0][0]
                                port = ip_port[0][1]
                            bizmod.executeAccountInit(msg_body["cases"], serverid, ip, port)
                            print "create account current"
                except:
                    print "create account error"
                Logging.getLog().info(u"------the interface that connects each system------")
                if i == 0 and case["ADAPTER_TYPE"] == "SPLX_T2":
                    # ��һ�������У�����ֻ����һ��T2������������ִ����󣬹رշ�����
                    # TODO ����T2������,�ο����´���
                    Logging.getLog().debug(gl.g_ZHLCSystemSetting["T2Server"])
                    t2sdk, msg = cF.connectT2(gl.g_ZHLCSystemSetting["T2Server"], "license.dat")
                    if t2sdk == None:
                        Logging.getLog().critical(u"����T2������ʧ�ܣ�ԭ��:%s" % (msg))
                        case_result_msg = copy.copy(gl.case_result_msg)
                        case_result_msg["msg_body"]["client_id"] = str(self._mqclient._agent_id)
                        testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg
                        testResult["log"] = msg
                        testResult["attachment"] = "N"
                        testResult["run_user"] = self._mqclient._agent_id
                        testResult["cmdstring"] = cmdstring
                        testResult["return_message"] = ""
                        testResult["data_change_info"] = ""
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultBody["runTaskid"] = case["TASK_ID"]
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                elif i == 0 and case["ADAPTER_TYPE"] == "SPLX_UFX":
                    # Logging.getLog().debug(gl.g_ZHLCSystemSetting["T2Server"])
                    t2sdk, msg = cF.connectUFX(gl.g_ZHLCSystemSetting["T2Server"], "license_o32.dat")
                    if t2sdk == None:
                        Logging.getLog().critical(u"����UFX������ʧ�ܣ�ԭ��:%s" % (msg))
                        # return -1, msg, u"����T2������ʧ�ܣ�ԭ��:%s" % (msg)
                        case_result_msg = copy.copy(gl.case_result_msg)
                        case_result_msg["msg_body"]["client_id"] = str(self._mqclient._agent_id)
                        testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg
                        testResult["log"] = msg
                        testResult["attachment"] = "N"
                        testResult["run_user"] = self._mqclient._agent_id
                        testResult["cmdstring"] = cmdstring
                        testResult["return_message"] = ""
                        testResult["data_change_info"] = ""
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultBody["runTaskid"] = case["TASK_ID"]
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                        # TODO ��Ҫ���������ķ��������ͣ����Ӳ�ͬ��KCXP ������
                elif i == 0 and case["ADAPTER_TYPE"] == "SPLX_HUARUI":
                    if case["FUNCID"][:2] != '82':
                        if hr_quant_handle:
                            pass
                        else:
                            hr_quant_handle = hradapter.HRAdapter()
                            gl.hr_quant_handle = hr_quant_handle
                            Logging.getLog().debug(gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"])
                            l = gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"].find(":")
                            quant_gateway_addr = gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"][:l]
                            quant_gateway_port = gl.g_ZHLCSystemSetting["QUANT_GATEWAY_ADDR"][l + 1:]
                            ret, msg = hr_quant_handle.ha_init(quant_gateway_addr, int(quant_gateway_port))
                            if ret != 0:
                                Logging.getLog().critical(u"���ӻ�����������ʧ�ܣ�ԭ��:%s" % (msg))
                                case_result_msg = copy.copy(gl.case_result_msg)
                                case_result_msg["msg_body"]["client_id"] = str(self._mqclient._agent_id)
                                testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                                testResult["result"] = "STATE_FAIL"
                                testResult["step"] = case["STEP"]
                                testResult["case_name"] = case["CASE_NAME"]
                                testResult["funcid"] = case["FUNCID"]
                                testResult["msg"] = msg
                                testResult["log"] = msg
                                testResult["attachment"] = "N"
                                testResult["run_user"] = self._mqclient._agent_id
                                testResult["cmdstring"] = cmdstring
                                testResult["return_message"] = ""
                                testResult["data_change_info"] = ""
                                testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                                testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                testResultBody["runTaskid"] = case["TASK_ID"]
                                testResultList.append(testResult)
                                skip_left_steps = True
                                skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                                continue
                    else:
                        if hr_csm_handle:
                            pass
                        else:
                            hr_csm_handle = hradapter.HRAdapter()
                            gl.hr_csm_handle = hr_csm_handle
                            Logging.getLog().debug(gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"])
                            l = gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"].find(":")
                            csm_gateway_addr = gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"][:l]
                            csm_gateway_port = gl.g_ZHLCSystemSetting["CSM_GATEWAY_ADDR"][l + 1:]
                            ret, msg = hr_csm_handle.ha_init(csm_gateway_addr, int(csm_gateway_port))
                            if ret != 0:
                                Logging.getLog().critical(u"���ӻ�����������ʧ�ܣ�ԭ��:%s" % (msg))
                                case_result_msg = copy.copy(gl.case_result_msg)
                                case_result_msg["msg_body"]["client_id"] = str(self._mqclient._agent_id)
                                testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                                testResult["result"] = "STATE_FAIL"
                                testResult["step"] = case["STEP"]
                                testResult["case_name"] = case["CASE_NAME"]
                                testResult["funcid"] = case["FUNCID"]
                                testResult["msg"] = msg
                                testResult["log"] = msg
                                testResult["attachment"] = "N"
                                testResult["run_user"] = self._mqclient._agent_id
                                testResult["cmdstring"] = cmdstring
                                testResult["return_message"] = ""
                                testResult["data_change_info"] = ""
                                testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                                testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                testResultBody["runTaskid"] = case["TASK_ID"]
                                testResultList.append(testResult)
                                skip_left_steps = True
                                skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                                continue
                elif i == 0 and case["ADAPTER_TYPE"] == "SPLX_HUARUI_DYS":
                    Logging.getLog().debug(gl.g_ZHLCSystemSetting["HuaRuiDysServer"])
                    userDys = 'user3'
                    if "HuaRuiDysUsername" in gl.g_ZHLCSystemSetting.keys():
                        userDys = gl.g_ZHLCSystemSetting["HuaRuiDysUsername"]
                    passwordDys = 'password3'
                    if "HuaRuiDysPassword" in gl.g_ZHLCSystemSetting.keys():
                        passwordDys = gl.g_ZHLCSystemSetting["HuaRuiDysPassword"]
                    portDys = 32001
                    if "HuaRuiDysPort" in gl.g_ZHLCSystemSetting.keys():
                        portDys = int(gl.g_ZHLCSystemSetting["HuaRuiDysPort"])
                    dys_sdk, msg = huarui_dys.ConnectGw(gl.g_ZHLCSystemSetting["HuaRuiDysServer"], portDys, userDys,
                                                        passwordDys)
                    if dys_sdk == None:
                        Logging.getLog().critical(u"���ӻ������ʱ������ʧ�ܣ�ԭ��:%s" % (msg))
                        case_result_msg = copy.copy(gl.case_result_msg)
                        case_result_msg["msg_body"]["client_id"] = str(self._mqclient._agent_id)
                        testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg
                        testResult["log"] = msg
                        testResult["attachment"] = "N"
                        testResult["run_user"] = self._mqclient._agent_id
                        testResult["cmdstring"] = cmdstring
                        testResult["return_message"] = ""
                        testResult["data_change_info"] = ""
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultBody["runTaskid"] = case["TASK_ID"]
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue

                return_json_string = ""
                data_change_info_json_string = ""
                Logging.getLog().debug(
                    "begin to process the %d case run_record_id = %d" % (i, int(case['RUN_RECORD_ID'])))
                debug_last_run_record_id = case['RUN_RECORD_ID']
                if skip_left_steps == True and in_param_legal == False:
                    if case['CASES_PARAM_DATA_ID'] == skip_left_steps_cases_param_data_id:
                        # ���������Ҫ������
                        # testResult = {}
                        testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                        testResult["result"] = "STATE_SKIP"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["log"] = u"����������"
                        testResult["msg"] = ""
                        testResult["attachment"] = "N"
                        testResult["run_user"] = self._mqclient._agent_id
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        continue
                    else:
                        # �Ѿ�û����
                        skip_left_steps = False
                        skip_left_steps_cases_param_data_id = -1

                if last_cases_param_data_id != case['CASES_PARAM_DATA_ID']:
                    group_variable_dict = {}

                last_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                case_result_msg = copy.copy(gl.case_result_msg)
                case_result_msg["msg_body"]["client_id"] = str(self._mqclient._agent_id)
                testResultBody = {}
                testResultBody["runTaskid"] = case["TASK_ID"]
                testResult["RUN_RECORD_ID"] = case["RUN_RECORD_ID"]
                testResult["result"] = ""
                testResult["step"] = case["STEP"]
                testResult["case_name"] = case["CASE_NAME"]
                testResult["funcid"] = case["FUNCID"]
                testResult["log"] = ""
                testResult["msg"] = ""
                testResult["attachment"] = "N"
                testResult["run_user"] = self._mqclient._agent_id
                testResult["cmdstring"] = cmdstring
                if return_json_string:
                    return_json_string["check_point"] = gl.return_check_data
                testResult["return_message"] = return_json_string
                testResult["data_change_info"] = data_change_info_json_string
                testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if cmdstring == None:
                    cmdstring = ""
                if funcid == None:
                    funcid = ""
                # ����˳��ִ��ÿһ������
                # testResultList_index = 0 #��˳�����ÿ����������ݣ��ȽϷ�����������Ķ���
                # skip_left_steps = False
                Logging.getLog().info("------deal with PRE_ACTION or PRO_ACTION------")
                pres = case["PRE_ACTION"]
                pros = case["PRO_ACTION"]
                if pres == None:
                    pres = ""
                if pros == None:
                    pros = ""
                if adapter_type == 'SPLX_KCBP':
                    # clinch_a_deal_the_pair_and_the_data_into(funcid,)
                    # �ɽ���Ժ�����Ǩ��
                    funcid = case["FUNCID"]
                    if case["CASE_NAME"] in [u'�ɽ����', u'����ת��'] and funcid in ["220105", "220205", "220120"]:
                        if len(gl.execute_many_row[str(serverid)][funcid]) == 1:
                            cmdstring = cF_kcbp.GroupParameterReplace(deep_cmdstring,
                                                                      gl.execute_many_row[str(serverid)][funcid][0])
                        if len(gl.execute_many_row[str(serverid)][funcid]) > 1:
                            for i in range(len(gl.execute_many_row[str(serverid)][funcid])):
                                flag = True
                                count = i + 1
                                Logging.getLog().debug(u"cbs1---funcid:%s--total��%s, times:%s" % (
                                    funcid, len(gl.execute_many_row[str(serverid)][funcid]), count))
                                cmdstring = cF_kcbp.GroupParameterReplace(deep_cmdstring,
                                                                          gl.execute_many_row[str(serverid)][funcid][i])
                                # Logging.getLog().debug("cbs---cmdstring %s---" % new_cmdstring)
                                if count == len(gl.execute_many_row[str(serverid)][funcid]):
                                    break
                                else:
                                    cmdstring = cF_kcbp.GlobalParameterReplace(cmdstring, serverid)
                                    cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
                                    ret, msg_info = cF_kcbp.action_process(pres, group_variable_dict, [], funcid,
                                                                           cmdstring, serverid)
                                if ret != 0:
                                    Logging.getLog().critical("��������%s ǰ�ö���ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                                    testResult["result"] = "STATE_FAIL"
                                    testResult["step"] = case["STEP"]
                                    testResult["case_name"] = case["CASE_NAME"]
                                    testResult["funcid"] = case["FUNCID"]
                                    testResult["msg"] = u"����ǰ�ö���ִ��ʧ�ܣ�%s" % str(msg_info)
                                    testResult["log"] = u"����ǰ�ö���ִ��ʧ�ܣ�%s" % str(msg_info)
                                    testResult["cmdstring"] = cmdstring
                                    if return_json_string:
                                        return_json_string["check_point"] = gl.return_check_data
                                    testResult["return_message"] = return_json_string
                                    testResult["data_change_info"] = data_change_info_json_string
                                    testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    testResultList.append(testResult)

                                    skip_left_steps = True
                                    skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                                    flag = False
                                    break
                                ret, msg_info, log_info, dataset, return_json_string, data_change_info_json_string = self.RunKCBPScirpt(
                                    system_id, serverid, case["FUNCID"], cmdstring, case["TASK_ID"],
                                    case["RUN_RECORD_ID"],
                                    case["EXPECTED_VALUE"])
                                # �ݴ���
                                if ret < 0:
                                    ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                                 log_info=log_info,
                                                                 data_change_info_json_string="")
                                if ret < 0:
                                    testResult["result"] = "STATE_FAIL"
                                    testResult["step"] = case["STEP"]
                                    testResult["case_name"] = case["CASE_NAME"]
                                    testResult["funcid"] = case["FUNCID"]
                                    testResult["msg"] = msg_info
                                    testResult["log"] = msg_info
                                    testResult["attachment"] = "N"
                                    testResult["cmdstring"] = cmdstring
                                    if return_json_string:
                                        return_json_string["check_point"] = gl.return_check_data
                                    testResult["return_message"] = return_json_string
                                    testResult["data_change_info"] = data_change_info_json_string
                                    testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    testResultList.append(testResult)

                                    skip_left_steps = True
                                    skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                                    flag = False
                                    break

                                pros = cF_kcbp.GlobalParameterReplace(pros, serverid)
                                pros = self.paremReplace(pros, self._mqclient._system_account_group, system_id,
                                                         account_group_id)
                                pros = cF_kcbp.GroupParameterReplace(pros, group_variable_dict)
                                ret, pros_msg_info = cF_kcbp.action_process(pros, group_variable_dict, dataset, funcid,
                                                                            cmdstring, serverid)
                                if ret != 0:
                                    Logging.getLog().critical(
                                        u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(pros_msg_info)))
                                    testResult["msg"] = u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                                    testResult["log"] = u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                                    testResult["result"] = "STATE_FAIL"
                                    testResult["step"] = case["STEP"]
                                    testResult["case_name"] = case["CASE_NAME"]
                                    testResult["funcid"] = case["FUNCID"]
                                    testResult["attachment"] = "N"
                                    testResult["cmdstring"] = cmdstring
                                    if return_json_string:
                                        return_json_string["check_point"] = gl.return_check_data
                                    testResult["return_message"] = return_json_string
                                    testResult["data_change_info"] = data_change_info_json_string
                                    testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    testResultList.append(testResult)

                                    skip_left_steps = True
                                    skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                                    flag = False
                                    break
                            if flag == False:
                                continue
                    ####################################################################################################
                    # serverid = cF_kcbp.GetServeridByServerType(server_type)
                    # pres = cF_kcbp.GlobalParameterReplace(pres, serverid)
                    if str(serverid) in gl.g_paramInfoDict.keys():
                        if str(account_group_id) in gl.g_paramInfoDict.get(serverid).keys():
                            account_dict = gl.g_paramInfoDict.get(serverid).get(str(account_group_id))
                            # KCBP�ӿڵ��û�����Ϣ�Ǽ�����������н����滻��
                            group_variable_dict.update(account_dict.items())
                            # pres = cF_kcbp.GroupParameterReplace(pres, group_variable_dict)
                elif adapter_type == 'SPLX_UFX':
                    pass
                else:
                    pres = cF.GlobalParameterReplace(pres, account_group_id)
                    pres = cF.GroupParameterReplace(pres, group_variable_dict)
                if adapter_type in ["SPLX_T2", "SPLX_HUARUI", "SPLX_HUARUI_DYS"]:
                    gl.openprice_field = ""
                    if '@openprice@' in cmdstring:
                        gl.openprice_field = cmdstring.split('@openprice@')[0].split("#")[-1]
                    cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                    if 'id_no' in cmdstring:
                        id_no_value = cmdstring.split('id_no')[1].split('#')[0].replace("=", "")
                        group_variable_dict["generate_idno"] = id_no_value
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    # fixme ����
                    # ret=0
                    # msg_info = "fake ok"
                    # print "====================================================================="
                    # print pres
                    ret, msg_info = cF.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                      account_group_id)
                elif adapter_type in ["SPLX_HTTP"]:
                    cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    ret, msg_info = cF.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                      account_group_id)
                elif adapter_type == "SPLX_UFX":
                    gl.openprice_field = ""
                    if '@openprice@' in cmdstring:
                        gl.openprice_field = cmdstring.split('@openprice@')[0].split("#")[-1]

                    # cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    # cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                    ret, msg_info = cF.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                      account_group_id)

                elif adapter_type in ["SPLX_SIKULI", "SPLX_APPIUM", "SPLX_SELENIUM", "SPLX_SILKTEST", "SILKTEST"]:
                    Logging.getLog().info(u"------cbs pres------%s" % pres)
                    ret, msg_info = cF.action_process(pres, group_variable_dict, [], funcid, cmdstring,
                                                      account_group_id)
                elif adapter_type == 'SPLX_KCBP':
                    if in_param_legal:
                        ret, cmdstring_replace = mb.ReplaceParam(case['CASE_NAME'], cmdstring, serverid)
                        if ret == -1:
                            pass
                        else:
                            cmdstring = cmdstring_replace
                    cmdstring = cF_kcbp.GlobalParameterReplace(cmdstring, serverid)
                    cmdstring = cF_kcbp.GroupParameterReplace(cmdstring, group_variable_dict)
                    ret, msg_info = cF_kcbp.action_process(pres, group_variable_dict, [], funcid, cmdstring, serverid)
                else:
                    return -1, u"�ݲ�֧�ֵ�������"
                if ret != 0:
                    Logging.getLog().critical("��������%s ǰ�ö���ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                    testResult["result"] = "STATE_FAIL"
                    testResult["step"] = case["STEP"]
                    testResult["case_name"] = case["CASE_NAME"]
                    testResult["funcid"] = case["FUNCID"]
                    testResult["msg"] = u"����ǰ�ö���ִ��ʧ�ܣ�%s" % str(msg_info)
                    testResult["log"] = u"����ǰ�ö���ִ��ʧ�ܣ�%s" % str(msg_info)
                    testResult["cmdstring"] = cmdstring
                    if return_json_string:
                        return_json_string["check_point"] = gl.return_check_data
                    testResult["return_message"] = return_json_string
                    testResult["data_change_info"] = data_change_info_json_string
                    testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    testResultList.append(testResult)

                    skip_left_steps = True
                    skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                    continue

                # cmdstring = case["CMDSTRING"]
                # if cmdstring == None:
                #     cmdstring = ""
                # cmdstring = cF.GlobalParameterReplace(cmdstring,account_group_id) #fixme
                if adapter_type == 'SPLX_SELENIUM':
                    # ��ǰ��SELENIUM �Ĳ��������ʽ��֮ǰ�Ĳ�һ��
                    cF.ExcelProcessParam(system_id, funcid, param_index, group_variable_dict, account_group_id,
                                         param_data_id)
                else:
                    cmdstring = self.paremReplace(cmdstring, self._mqclient._system_account_group, system_id,
                                                  account_group_id)
                    cmdstring = cF.GlobalParameterReplace(cmdstring, account_group_id)
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                Logging.getLog().info(u"------��ϵͳ���а���------")
                if adapter_type == "SPLX_SIKULI":
                    # �ȵ�¼
                    if system_id == "1428904175882ZYQTA":
                        cmd_list = cmdstring.split('#')
                        username = cmd_list[0].split('=')[1]
                        password = cmd_list[1].split('=')[1]
                        login_param = '#'.join([cmd_list[0], cmd_list[1], cmd_list[2]])
                    else:
                        username, password = self.getUserAndPassFromParam(cmdstring)

                    if username != self._last_username:
                        # �ȴ�³һ�㣬�ɵ�TdxW����
                        self.killFuyiProcess()
                        if system_id != "1428904175882ZYQTA":
                            login_param = 'user=%s#pass=%s' % (username, password)
                        # print login_param
                        ret, msg_info, log_info, data_change_info_json_string = self.RunSikuliScript(system_id, "0",
                                                                                                     "common\\login.sikuli",
                                                                                                     login_param,
                                                                                                     case["TASK_ID"],
                                                                                                     case[
                                                                                                         "RUN_RECORD_ID"],
                                                                                                     case[
                                                                                                         "SCRIPT_NAME"])
                        Logging.getLog().debug('finish login script')
                        if ret < 0:
                            ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                         log_info=log_info,
                                                         data_change_info_json_string=data_change_info_json_string)
                        if ret < 0:
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = u"��¼����ʧ�ܣ�%s" % str(msg_info)
                            testResult["log"] = log_info
                            testResult["cmdstring"] = cmdstring
                            testResult["attachment"] = "Y"
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self._last_username = ""
                            testResultList.append(testResult)

                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue

                    self._last_username = username

                    # ִ��ҵ��ű�
                    ret, msg_info, log_info, data_change_info_json_string = self.RunSikuliScript(system_id, "0",
                                                                                                 case["SCRIPT_NAME"],
                                                                                                 cmdstring,
                                                                                                 case["TASK_ID"],
                                                                                                 case["RUN_RECORD_ID"],
                                                                                                 case["SCRIPT_NAME"])
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                     log_info=log_info,
                                                     data_change_info_json_string=data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg_info
                        testResult["log"] = log_info
                        testResult["cmdstring"] = cmdstring
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["attachment"] = "Y"
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        self._last_username = ""
                        continue
                elif adapter_type == "SPLX_HTTP":
                    # ִ��ҵ��ű�nsystem_id, cmdstring, runtaskid, run_record_id,CASE_NAME
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    Logging.getLog().debug("group_variable_dict:" + str(group_variable_dict))
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunHttpScript(
                        system_id, cmdstring,
                        case["TASK_ID"],
                        case["RUN_RECORD_ID"],
                        case["CASE_NAME"],
                        group_variable_dict,
                        case["EXPECTED_VALUE"],
                        case['INTERFACE_INFO']
                    )
                    # �ݴ���
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                     log_info=log_info,
                                                     data_change_info_json_string=data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        # testResult["msg"] = msg_info
                        testResult["log"] = log_info
                        testResult["cmdstring"] = cmdstring
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["attachment"] = "Y"
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        succ_flag = -1
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        ret, pros_msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag, [],
                                                                        None,
                                                                        None, account_group_id)
                        if ret != 0:
                            Logging.getLog().critical(u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                            testResult["msg"] = msg_info + u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                            self._last_username = ""
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            testResult["msg"] = msg_info
                            testResultList.append(testResult)
                            continue
                elif adapter_type == "SPLX_SILKTEST":
                    # ִ��ҵ��ű�nsystem_id, cmdstring, runtaskid, run_record_id,CASE_NAME
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    Logging.getLog().debug("group_variable_dict:" + str(group_variable_dict))
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunSilktestScript(
                        system_id, cmdstring,
                        case["TASK_ID"],
                        case[
                            "RUN_RECORD_ID"],
                        case["CASE_NAME"],
                        group_variable_dict,
                        case["EXPECTED_VALUE"]
                    )
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                     log_info=log_info,
                                                     data_change_info_json_string=data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        # testResult["msg"] = msg_info
                        testResult["log"] = log_info
                        testResult["cmdstring"] = cmdstring
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["attachment"] = "Y"
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        succ_flag = -1
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        ret, pros_msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag, [],
                                                                        None,
                                                                        None, account_group_id)
                        if ret != 0:
                            Logging.getLog().critical(u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                            testResult["msg"] = msg_info + u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                            self._last_username = ""
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            testResult["msg"] = msg_info
                            testResultList.append(testResult)
                            continue
                elif adapter_type == "SPLX_APPIUM":
                    # fixme
                    time.sleep(0.1)
                    ret, msg_info, log_info, data_change_info_json_string = self.RunAppiumScript(system_id, cmdstring,
                                                                                                 case["TASK_ID"],
                                                                                                 case["RUN_RECORD_ID"])
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                     log_info=log_info,
                                                     data_change_info_json_string=data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg_info
                        testResult["log"] = log_info
                        testResult["attachment"] = "Y"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)

                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                elif adapter_type == "SPLX_T2":
                    #  cmdstring = cmdstring.replace("@birthday@", gl.birthday_zhlc)
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    cmdstring = cmdstring.replace("&colon&", ":").replace('amp;amp;', 'amp;')
                    if gl.openprice_field:
                        openprice_key_index = cmdstring.find(gl.openprice_field)
                        key_value = cmdstring[openprice_key_index:].split("#")[0]
                        cmdstring = cmdstring.replace(key_value, gl.openprice_field + gl.openprice_zhlc)

                    # cmdstring = cmdstring.replace(" ", "")
                    if cmdstring:
                        cmdstring = cmdstring.strip()
                    # print cmdstring
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunT2Script(
                        t2sdk, system_id, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                        case["EXPECTED_VALUE"])
                    if return_json_string != '':
                        return_json_string["message"] = msg_info
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                     return_json_string,
                                                     data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg_info
                        testResult["log"] = msg_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)

                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                elif adapter_type == "SPLX_UFX" and gl.o32_for_flag == True:
                    # o32_for_flag  ����ΪFalse  ��ֹ���ò�ѯ����
                    gl.o32_for_flag = False
                    # gl.o32_pro_disableflag = True   ѭ���İ���������� ����治��Ҫִ��
                    gl.o32_pro_disableflag = True
                    # print gl.g_accountDict[str(account_group_id)].keys()
                    error_info = ""
                    error_flag = False
                    if str(account_group_id) not in gl.g_accountDict.keys():
                        error_info = u"���˻��鲻����,����:%s" % account_group_id
                        error_flag = True
                    if error_flag == False and 'user_token' not in gl.g_accountDict[str(account_group_id)].keys():
                        error_info = u"�˻���%sδ��ȡuser_token, �����Ӧ���˻�����Ϣ" % account_group_id
                        error_flag = True
                    if error_flag:
                        Logging.getLog().error(u"δ�ܻ��user_token")
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = error_info
                        testResult["log"] = error_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                    if gl.g_accountDict[str(account_group_id)]["user_token"] == "@user_token@":
                        ret, user_token = cF.getUserToken(t2sdk, str(account_group_id))
                        if ret < 0:
                            Logging.getLog().error(u"δ�ܻ��user_token")
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = u"δ�ܻ��user_token"
                            testResult["log"] = u"δ�ܻ��user_token"
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            Logging.getLog().info("new user_token is %s" % user_token)
                        gl.g_accountDict[str(account_group_id)]["user_token"] = user_token
                        if str(account_group_id) in gl.lh_account_info.keys() and "user_token" in gl.lh_account_info[
                            str(account_group_id)]:
                            gl.lh_account_info[str(account_group_id)]["user_token"] = user_token
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    cmdstring = cmdstring.replace("&colon&", ":").replace('amp;amp;', 'amp;')
                    if gl.openprice_field:
                        openprice_key_index = cmdstring.find(gl.openprice_field)
                        key_value = cmdstring[openprice_key_index:].split("#")[0]
                        cmdstring = cmdstring.replace(key_value, gl.openprice_field + gl.openprice_zhlc)
                    cmdstring = cmdstring.replace(" ", "")
                    print cmdstring
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = -1, u"gl.o32_for_flag Ϊ��", "", "", "", ""
                    if gl.o32_for_field != {}:
                        values = []
                        gl.select_result_key = ""
                        for key in gl.o32_for_field:
                            gl.select_result_key = key
                            values = gl.o32_for_field[key]
                        for num, value in enumerate(values):
                            sigle_group_variable_dict = copy.deepcopy(group_variable_dict)
                            sigle_group_variable_dict[gl.select_result_key] = value
                            cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                            cmdstring = cF.GroupParameterReplace(cmdstring, sigle_group_variable_dict)

                            index1 = cmdstring.find("stock_code")
                            cmdstring1 = cmdstring[:index1]
                            cmdstring2 = "stock_code=%s#" % value
                            cmd_list = cmdstring[index1:].split("#")
                            cmd_list.pop(0)
                            cmdstring3 = "#".join(cmd_list)
                            cmdstring = cmdstring1 + cmdstring2 + cmdstring3

                            ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunUFXScript(
                                t2sdk, system_id, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                                case["EXPECTED_VALUE"])
                            if return_json_string != '':
                                return_json_string["message"] = msg_info
                            if ret < 0:
                                ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                             return_json_string,
                                                             data_change_info_json_string)
                            if ret < 0:
                                break
                            ################032################
                            # pros = cF.GlobalParameterReplace(pros, account_group_id)
                            # pros = self.paremReplace(pros, self._mqclient._system_account_group, system_id,
                            #                          account_group_id)
                            # pros = cF.GroupParameterReplace(pros, sigle_group_variable_dict)
                            if dataset_list and pros:
                                Logging.getLog().debug(str(dataset_list))
                                ret, msg_info = cF.action_process(pros, sigle_group_variable_dict, dataset_list[1],
                                                                  funcid,
                                                                  cmdstring, account_group_id)
                                if 'updateDict' in pros or 'updateDict' in pres and ret == 0:
                                    case_pres_pros_incloud_updateDict = True
                                if ret < 0:
                                    break
                            # sigle_group_variable_dict.update({select_result_key:value})
                            # gl.iter_group_variable_dict[value] = sigle_group_variable_dict
                            # sigle_group_variable_dict["bf_current_amount_v1"]
                            iter_group_variable_dict.append({value: sigle_group_variable_dict})

                        if ret < 0:
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = msg_info
                            testResult["log"] = msg_info
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                            #################032###############
                    else:
                        if return_json_string != '':
                            return_json_string["message"] = msg_info
                        if ret < 0:
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = msg_info
                            testResult["log"] = msg_info
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                elif adapter_type == "SPLX_UFX" and gl.o32_for_running_flag == True:
                    # o32_for_running_flag  ѭ��ִ�жԱȿ�ʼ
                    gl.o32_for_running_flag = False
                    # gl.o32_pro_disableflag = True   ѭ���İ���������� ����治��Ҫִ��
                    gl.o32_pro_disableflag = True
                    # print gl.g_accountDict[str(account_group_id)].keys()
                    error_info = ""
                    error_flag = False
                    if str(account_group_id) not in gl.g_accountDict.keys():
                        error_info = u"���˻��鲻����,����:%s" % account_group_id
                        error_flag = True
                    if error_flag == False and 'user_token' not in gl.g_accountDict[str(account_group_id)].keys():
                        error_info = u"�˻���%sδ��ȡuser_token, �����Ӧ���˻�����Ϣ" % account_group_id
                        error_flag = True
                    if error_flag:
                        Logging.getLog().error(u"δ�ܻ��user_token")
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = error_info
                        testResult["log"] = error_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                    if gl.g_accountDict[str(account_group_id)]["user_token"] == "@user_token@":
                        ret, user_token = cF.getUserToken(t2sdk, str(account_group_id))
                        if ret < 0:
                            Logging.getLog().error(u"δ�ܻ��user_token")
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = u"δ�ܻ��user_token"
                            testResult["log"] = u"δ�ܻ��user_token"
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            Logging.getLog().info("new user_token is %s" % user_token)
                        gl.g_accountDict[str(account_group_id)]["user_token"] = user_token
                        if str(account_group_id) in gl.lh_account_info.keys() and "user_token" in gl.lh_account_info[
                            str(account_group_id)]:
                            gl.lh_account_info[str(account_group_id)]["user_token"] = user_token
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    cmdstring = cmdstring.replace("&colon&", ":").replace('amp;amp;', 'amp;')
                    if gl.openprice_field:
                        openprice_key_index = cmdstring.find(gl.openprice_field)
                        key_value = cmdstring[openprice_key_index:].split("#")[0]
                        cmdstring = cmdstring.replace(key_value, gl.openprice_field + gl.openprice_zhlc)
                    cmdstring = cmdstring.replace(" ", "")
                    print cmdstring
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = -1, u"gl.o32_for_field Ϊ��", "", "", "", ""
                    if iter_group_variable_dict:
                        for index_dict in iter_group_variable_dict:
                            index = index_dict.keys()[0]
                            Logging.getLog().debug("SPLX_UFX_CBS stock_code %s" % index)
                            # index_dict[index].update(group_variable_dict)
                            # group_variable_dict.update(index_dict[index])
                            new_group = index_dict[index]
                            new_group[gl.select_result_key] = index
                            cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                            cmdstring = cF.GroupParameterReplace(cmdstring, new_group)
                            index1 = cmdstring.find("stock_code")
                            cmdstring1 = cmdstring[:index1]
                            cmdstring2 = "stock_code=%s#" % index
                            cmd_list = cmdstring[index1:].split("#")
                            cmd_list.pop(0)
                            cmdstring3 = "#".join(cmd_list)
                            cmdstring = cmdstring1 + cmdstring2 + cmdstring3
                            ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunUFXScript(
                                t2sdk, system_id, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                                case["EXPECTED_VALUE"])
                            if return_json_string != '':
                                return_json_string["message"] = msg_info
                            if ret < 0:
                                ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                             return_json_string,
                                                             data_change_info_json_string)
                            if ret < 0:
                                break
                            ################032################
                            # pros = cF.GlobalParameterReplace(pros, account_group_id)
                            # pros = self.paremReplace(pros, self._mqclient._system_account_group, system_id,
                            #                          account_group_id)
                            # pros = cF.GroupParameterReplace(pros, group_variable_dict)
                            if dataset_list and pros:
                                Logging.getLog().debug(str(dataset_list))
                                ret, msg_info = cF.action_process(pros, new_group, dataset_list[1], funcid,
                                                                  cmdstring, account_group_id)
                                if 'updateDict' in pros or 'updateDict' in pres and ret == 0:
                                    case_pres_pros_incloud_updateDict = True
                                if ret < 0:
                                    break

                        if ret < 0:
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = msg_info
                            testResult["log"] = msg_info
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                            #################032###############
                    else:
                        if return_json_string != '':
                            return_json_string["message"] = msg_info
                        if ret < 0:
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = msg_info
                            testResult["log"] = msg_info
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                elif adapter_type == "SPLX_UFX":
                    # print gl.g_accountDict[str(account_group_id)].keys()
                    error_info = ""
                    error_flag = False
                    if str(account_group_id) not in gl.g_accountDict.keys():
                        error_info = u"���˻��鲻����,����:%s" % account_group_id
                        error_flag = True
                    if error_flag == False and 'user_token' not in gl.g_accountDict[str(account_group_id)].keys():
                        error_info = u"�˻���%sδ��ȡuser_token, �����Ӧ���˻�����Ϣ" % account_group_id
                        error_flag = True
                    if error_flag:
                        Logging.getLog().error(u"δ�ܻ��user_token")
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = error_info
                        testResult["log"] = error_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                    if gl.g_accountDict[str(account_group_id)]["user_token"] == "@user_token@":
                        ret, user_token = cF.getUserToken(t2sdk, str(account_group_id))
                        if ret < 0:
                            Logging.getLog().error(u"δ�ܻ��user_token")
                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = u"δ�ܻ��user_token"
                            testResult["log"] = u"δ�ܻ��user_token"
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            Logging.getLog().info("new user_token is %s" % user_token)
                        gl.g_accountDict[str(account_group_id)]["user_token"] = user_token
                        if str(account_group_id) in gl.lh_account_info.keys() and "user_token" in gl.lh_account_info[
                            str(account_group_id)]:
                            gl.lh_account_info[str(account_group_id)]["user_token"] = user_token

                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))

                    cmdstring = cmdstring.replace("&colon&", ":").replace('amp;amp;', 'amp;')
                    if gl.openprice_field:
                        openprice_key_index = cmdstring.find(gl.openprice_field)
                        key_value = cmdstring[openprice_key_index:].split("#")[0]
                        cmdstring = cmdstring.replace(key_value, gl.openprice_field + gl.openprice_zhlc)
                    cmdstring = cmdstring.replace(" ", "")
                    Logging.getLog().info(u"------exe cmdstring:%s------" % cmdstring)
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunUFXScript(
                        t2sdk, system_id, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                        case["EXPECTED_VALUE"])
                    if return_json_string != '':
                        return_json_string["message"] = msg_info
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                     return_json_string,
                                                     data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg_info
                        testResult["log"] = msg_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                elif adapter_type == 'SPLX_KCBP':
                    ret, msg_info, log_info, dataset, return_json_string, data_change_info_json_string = 0, "", "", "", "", ""
                    if case["FUNCID"] != "10001":
                        ret, msg_info, log_info, dataset, return_json_string, data_change_info_json_string = self.RunKCBPScirpt(
                            system_id, serverid, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                            case["EXPECTED_VALUE"])

                        # ����ɽ���Ժ�����ת��clinch_a_deal_the_pair_and_the_data_into(funcid, endsno, commflag, filesize)
                        if "clinch_a_deal_the_pair_and_the_data_into" in pres:
                            # fix me cbs
                            funcid = ""
                            action_list = cF.deal_with_action_str(pres)
                            for action_dict in action_list:
                                action = action_dict['content']
                                if "clinch_a_deal_the_pair_and_the_data_into" in action:
                                    funcid = action.split("clinch_a_deal_the_pair_and_the_data_into")[1] \
                                        .replace("(", "").replace(")", "").strip()
                            funcid = funcid.strip()
                            # endsno = endsno.strip()
                            # commflag = commflag.strip()
                            # filesize = filesize.strip()
                            # if case["FUNCID"] == "220101" and len(dataset) >= 2:
                            if case["FUNCID"] == str(funcid) and len(dataset) >= 2:
                                key = dataset[0]
                                if case["CASE_NAME"] == u'����ת��':
                                    for row in dataset[1:]:
                                        key_value = dict(zip(key, row))
                                        # print "key_value"
                                        # print key_value
                                        if int(key_value["endsno"]) >= 1:
                                            if str(key_value['commflag']) == "0":
                                                gl.execute_many_row[str(serverid)]['220105'].append(key_value)
                                            elif str(key_value['commflag']) == "1":
                                                gl.execute_many_row[str(serverid)]['220205'].append(key_value)
                                            else:
                                                pass
                                if case["CASE_NAME"] == u'�ɽ����':
                                    for row in dataset[1:]:
                                        key_value = dict(zip(key, row))
                                        if int(key_value['filesize']) > 0:
                                            gl.execute_many_row[str(serverid)]['220120'].append(key_value)
                        if ret < 0:
                            ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset,
                                                         return_json_string,
                                                         data_change_info_json_string)
                            # --------------------------------------------------
                        if ret < 0:
                            pros = cF_kcbp.GlobalParameterReplace(pros, serverid)
                            pros = self.paremReplace(pros, self._mqclient._system_account_group, system_id,
                                                     account_group_id)
                            pros = cF_kcbp.GroupParameterReplace(pros, group_variable_dict)
                            ret, pros_msg_info = cF_kcbp.action_process(pros, group_variable_dict, dataset, funcid,
                                                                        cmdstring, serverid)

                            testResult["result"] = "STATE_FAIL"
                            testResult["step"] = case["STEP"]
                            testResult["case_name"] = case["CASE_NAME"]
                            testResult["funcid"] = case["FUNCID"]
                            testResult["msg"] = msg_info
                            testResult["log"] = msg_info
                            testResult["attachment"] = "N"
                            testResult["cmdstring"] = cmdstring
                            if return_json_string:
                                return_json_string["check_point"] = gl.return_check_data
                            testResult["return_message"] = return_json_string
                            testResult["data_change_info"] = data_change_info_json_string
                            testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                            testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            testResultList.append(testResult)

                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                elif case["ADAPTER_TYPE"] == "SPLX_SELENIUM":
                    # fixme
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    ret, msg_info, log_info, data_change_info_json_string = self.RunSeleniumScript(system_id, funcid,
                                                                                                   param_data_id,
                                                                                                   case["TASK_ID"],
                                                                                                   case[
                                                                                                       "RUN_RECORD_ID"])
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(func_id=case["FUNCID"], ret=ret, msg_info=msg_info,
                                                     log_info=log_info,
                                                     data_change_info_json_string=data_change_info_json_string)
                    if log_info and len(log_info) > 60000:  # fixme cbs
                        log_info = ""
                    if 'empty_log' in pres or 'empty_log' in pros:
                        # ��ռ���Ӫ�˷��ص�log��Ϣ
                        log_info = ""
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        # testResult["msg"] = msg_info
                        testResult["log"] = log_info
                        testResult["attachment"] = "Y"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        succ_flag = -1
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        # continue fix by zzp
                        # ����ʧ���ж��Ƿ�ִ�к�������
                        # ret, pros_msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag, account_group_id)
                        ret, pros_msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag, [], None,
                                                                        None, account_group_id)
                        if pros and 'update_account_info' in pros:
                            case_pres_pros_incloud_updateDict = True
                        if ret != 0:
                            Logging.getLog().critical(u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                            testResult["msg"] = msg_info + u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                            self._last_username = ""
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            testResult["msg"] = msg_info
                            testResultList.append(testResult)
                            continue
                elif case["ADAPTER_TYPE"] == "SILKTEST":
                    # fixme
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    # 0, msg, log_info, "", return_json_string, ""
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunGjSilkTestScript(
                        system_id,
                        cmdstring,
                        case["TASK_ID"],
                        case[
                            "RUN_RECORD_ID"], group_variable_dict, case["EXPECTED_VALUE"])
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                     return_json_string,
                                                     data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["log"] = log_info
                        testResult["attachment"] = "Y"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        succ_flag = -1
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        ret, pros_msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag, [],
                                                                        None,
                                                                        None, account_group_id)
                        if ret != 0:
                            Logging.getLog().critical(u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                            testResult["msg"] = msg_info + u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                            self._last_username = ""
                            testResultList.append(testResult)
                            skip_left_steps = True
                            skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                            continue
                        else:
                            testResult["msg"] = msg_info
                            testResultList.append(testResult)
                            continue
                elif case["ADAPTER_TYPE"] == "SPLX_HUARUI":
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    cmdstring = cmdstring.replace("&colon&", ":")  # .replace('amp;amp;', 'amp;')
                    print cmdstring
                    if case["FUNCID"][:2] == '82':  # 82��ͷ�Ĺ��ܺŷ�����������
                        ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunHuaRuiScript(
                            hr_csm_handle, system_id, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                            case["EXPECTED_VALUE"])
                        if ret < 0:
                            ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                         return_json_string,
                                                         data_change_info_json_string)
                    else:
                        ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = self.RunHuaRuiScript(
                            hr_quant_handle, system_id, case["FUNCID"], cmdstring, case["TASK_ID"],
                            case["RUN_RECORD_ID"],
                            case["EXPECTED_VALUE"])
                        if ret < 0:
                            ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                         return_json_string,
                                                         data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg_info
                        testResult["log"] = log_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                elif case["ADAPTER_TYPE"] == "SPLX_HUARUI_DYS":
                    cmdstring = cF.GlobalParameterReplace(cmdstring, str(account_group_id))
                    cmdstring = cF.GroupParameterReplace(cmdstring, group_variable_dict)
                    cmdstring = cmdstring.replace("&colon&", ":").replace('amp;amp;', 'amp;')
                    if gl.openprice_field:
                        openprice_key_index = cmdstring.find(gl.openprice_field)
                        key_value = cmdstring[openprice_key_index:].split("#")[0]
                        cmdstring = cmdstring.replace(key_value, gl.openprice_field + gl.openprice_zhlc)
                    if cmdstring:
                        cmdstring = cmdstring.strip()
                    ret, msg_info, log_info, dataset_list, return_json_string, data_change_info_json_string = huarui_dys.RunScript(
                        self, system_id, case["FUNCID"], cmdstring, case["TASK_ID"], case["RUN_RECORD_ID"],
                        case["EXPECTED_VALUE"])
                    if return_json_string != '':
                        return_json_string["message"] = msg_info
                    if ret < 0:
                        ret, msg = cF.fault_tolerant(case["FUNCID"], ret, msg_info, log_info, dataset_list,
                                                     return_json_string,
                                                     data_change_info_json_string)
                    if ret < 0:
                        testResult["result"] = "STATE_FAIL"
                        testResult["step"] = case["STEP"]
                        testResult["case_name"] = case["CASE_NAME"]
                        testResult["funcid"] = case["FUNCID"]
                        testResult["msg"] = msg_info
                        testResult["log"] = msg_info
                        testResult["attachment"] = "N"
                        testResult["cmdstring"] = cmdstring
                        if return_json_string:
                            return_json_string["check_point"] = gl.return_check_data
                        testResult["return_message"] = return_json_string
                        testResult["data_change_info"] = data_change_info_json_string
                        testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                        testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        testResultList.append(testResult)
                        skip_left_steps = True
                        skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                        continue
                Logging.getLog().info(u"------�����ɹ�ִ�����ݺ�������------")

                if adapter_type == "SPLX_KCBP":
                    pros = cF_kcbp.GlobalParameterReplace(pros, serverid)
                    pros = self.paremReplace(pros, self._mqclient._system_account_group, system_id, account_group_id)
                    pros = cF_kcbp.GroupParameterReplace(pros, group_variable_dict)
                    ret, pros_msg_info = cF_kcbp.action_process(pros, group_variable_dict, dataset, funcid,
                                                                cmdstring, serverid)
                else:
                    if adapter_type in ["SPLX_UFX", "SPLX_HUARUI"]:
                        pass
                    else:
                        pros = cF.GlobalParameterReplace(pros, account_group_id)
                        pros = self.paremReplace(pros, self._mqclient._system_account_group, system_id,
                                                 account_group_id)
                        pros = cF.GroupParameterReplace(pros, group_variable_dict)
                if case["ADAPTER_TYPE"] in ["SPLX_HUARUI", "SPLX_HUARUI_DYS"]:
                    if pros:
                        ret, pros_msg_info = cF.action_process(pros, group_variable_dict, dataset_list, funcid,
                                                               cmdstring, account_group_id)
                        if 'updateDict' in pros or 'updateDict' in pres and ret == 0:
                            case_pres_pros_incloud_updateDict = True
                if case["ADAPTER_TYPE"] == "SPLX_T2":
                    # fixme ����
                    if pros:
                        ret, pros_msg_info = cF.action_process(pros, group_variable_dict, dataset_list[0], funcid,
                                                               cmdstring, account_group_id)
                        if 'updateDict' in pros or 'updateDict' in pres and ret == 0:
                            case_pres_pros_incloud_updateDict = True
                elif case["ADAPTER_TYPE"] == "SPLX_SELENIUM":
                    succ_flag = 0
                    if pros:
                        ret, msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag)
                        if 'update_account_info' in pros and ret == 0:
                            case_pres_pros_incloud_updateDict = True
                elif case["ADAPTER_TYPE"] in ["SPLX_HTTP", "SILKTEST"]:
                    succ_flag = 0
                    if pros:
                        ret, msg_info = cF.action_process_selenium(pros, group_variable_dict, succ_flag)
                elif case["ADAPTER_TYPE"] in ["SPLX_SIKULI", "SPLX_APPIUM", "SPLX_SILKTEST"]:
                    ret, msg_info = cF.action_process(pros, group_variable_dict)
                elif case["ADAPTER_TYPE"] == "SPLX_UFX" and gl.o32_pro_disableflag == False:
                    if dataset_list and pros:
                        Logging.getLog().debug(str(dataset_list))
                        ret, pros_msg_info = cF.action_process(pros, group_variable_dict, dataset_list[1], funcid,
                                                               cmdstring, account_group_id)
                        if 'updateDict' in pros or 'updateDict' in pres and ret == 0:
                            case_pres_pros_incloud_updateDict = True
                else:
                    pass

                if ret != 0:
                    if case["ADAPTER_TYPE"] in ["SPLX_KCBP", "SPLX_T2", "SPLX_HUARUI", "SPLX_UFX", "SPLX_KCBP",
                                                "SPLX_HUARUI_DYS"]:
                        Logging.getLog().critical(u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(pros_msg_info)))
                        testResult["msg"] = u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                        testResult["log"] = u"���ݺ�������ִ��ʧ�ܣ�%s" % pros_msg_info
                    elif case["ADAPTER_TYPE"] in ["SPLX_HTTP", "SPLX_SIKULI", "SPLX_APPIUM", "SPLX_SELENIUM",
                                                  "SPLX_SILKTEST",
                                                  "SILKTEST"]:
                        Logging.getLog().critical(u"��������%s ��������ִ��ʧ�ܣ�%s" % (str(case["STEP"]), str(msg_info)))
                        testResult["msg"] = u"���ݺ�������ִ��ʧ�ܣ�%s" % msg_info
                        testResult["log"] = log_info
                    else:
                        pass
                    testResult["result"] = "STATE_FAIL"
                    testResult["step"] = case["STEP"]
                    testResult["case_name"] = case["CASE_NAME"]
                    testResult["funcid"] = case["FUNCID"]
                    testResult["cmdstring"] = cmdstring
                    if return_json_string:
                        return_json_string["check_point"] = gl.return_check_data
                    testResult["return_message"] = return_json_string
                    testResult["data_change_info"] = data_change_info_json_string
                    testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                    testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    self._last_username = ""
                    testResultList.append(testResult)
                    skip_left_steps = True
                    skip_left_steps_cases_param_data_id = case['CASES_PARAM_DATA_ID']
                    continue

                testResult["result"] = "STATE_PASS"
                testResult["step"] = case["STEP"]
                testResult["case_name"] = case["CASE_NAME"]
                testResult["funcid"] = case["FUNCID"]
                if adapter_type == "SPLX_KCBP" or case["ADAPTER_TYPE"] == "SPLX_T2" or case[
                    "ADAPTER_TYPE"] == "SPLX_HUARUI_DYS":
                    testResult["msg"] = msg_info
                    testResult["log"] = msg_info
                elif case["ADAPTER_TYPE"] in ["SPLX_SILKTEST", "SPLX_SIKULI", "SPLX_APPIUM", "SPLX_SELENIUM",
                                              "SILKTEST"]:
                    testResult["msg"] = ""
                    testResult["log"] = log_info
                else:
                    pass
                testResult["cmdstring"] = cmdstring
                if return_json_string:
                    return_json_string["check_point"] = gl.return_check_data
                    Logging.getLog().debug(u"check_point:%s" % (json.dumps(gl.return_check_data, sort_keys=True,
                                                                           indent=4, ensure_ascii=False, encoding="gbk",
                                                                           separators=(',', ':'))))
                testResult["return_message"] = return_json_string
                testResult["data_change_info"] = data_change_info_json_string
                testResult["CASES_PARAM_DATA_ID"] = case['CASES_PARAM_DATA_ID']
                testResult["run_end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                testResultList.append(testResult)

            # �ر�T2Server ����
            if case_adapter_type == "SPLX_T2":
                if t2sdk:
                    t2sdk.Close()  # fixme
                    t2sdk.DeInitInterface()
            if case_adapter_type == "SPLX_HUARUI_DYS":
                huarui_dys.DeInitInterface()
            testResultBody["testResult"] = testResultList
            case_result_msg["msg_body"]["result"] = testResultBody
            case_result_msg["msg_body"]["result"]["system_id"] = system_id

            if case_adapter_type in ["SPLX_HTTP", "SPLX_T2", "SPLX_HUARUI", "SPLX_SELENIUM",
                                     "SPLX_UFX", "SPLX_HUARUI_DYS"] and case_pres_pros_incloud_updateDict == True:
                ret, account_system_id, account_data, account_id = self.update_db2_account_into()
                if ret == 0 and account_data:
                    account_data_dict = {}
                    account_data_dict['case_adapter_type'] = case_adapter_type
                    account_data_dict['account_system_id'] = account_system_id
                    account_data_dict['account_data'] = account_data
                    account_data_dict['account_id'] = account_id
                    self._mqclient._redis_client.set_account_data_list(
                        json.dumps(account_data_dict, ensure_ascii=False, encoding="gbk"))
            # ���ڿ��Է�����Ϣ�����������ˡ�
            a = ""
            # ===================== use redis to send back result
            # �ȴ������ȫ�����н��� �ٷ��ذ��������Ϣ
            if case_adapter_type == "SPLX_KCBP":
                gl.all_core[str(serverid)] = 1
                gltestResultList = gl.server_result_info["testResultList"]
                gltestResultList.extend(testResultList)
                gl.server_result_info["testResultList"] = gltestResultList
                gl.server_result_info["case_result_msg"] = case_result_msg
                gl.server_result_info["collect_task_id"] = collect_task_id
                time.sleep(0.1)
                # cF.wait_resultinfo()
                if 0 not in gl.all_core.values():
                    allTestResult = gl.server_result_info["testResultList"]
                    # for value in gl.server_result_info:
                    #     allTestResult.extend(value)
                    case_result_msg["msg_body"]["result"]["testResult"] = allTestResult
                    try:
                        a = json.dumps(case_result_msg, sort_keys=True, indent=4, ensure_ascii=False, encoding="gbk",
                                       separators=(',', ':'))
                        print a
                        Logging.getLog().info("exe success")
                    except:
                        a = str(case_result_msg).encode('gbk')
                    self._result_msg_list.append(a)

                    ret, msg = self._mqclient._redis_client.send_test_result_back_to_redis(self._mqclient._agent_id,
                                                                                           collect_task_id,
                                                                                           allTestResult)
                    # ����������� 0Ϊ�ر�
                    gl.g_thread_flag = 0
                    if ret < 0:
                        Logging.getLog().error(u"send_test_result_back_to_redis fail msg=%s" % msg)
            else:
                try:
                    a = json.dumps(case_result_msg, sort_keys=True, indent=4, ensure_ascii=False, encoding="gbk",
                                   separators=(',', ':'))
                except:
                    a = str(case_result_msg).encode('gbk')
                self._result_msg_list.append(a)
                try:
                    Logging.getLog().debug(u"send case_result_msg back %s" % (
                        json.dumps(case_result_msg, sort_keys=True, indent=4, ensure_ascii=False, encoding="gbk",
                                   separators=(',', ':'))))
                    Logging.getLog().info("exe success")
                except:
                    Logging.getLog().debug(u"send case_result_msg back %s" % str(case_result_msg).encode('gbk'))
                ret, msg = self._mqclient._redis_client.send_test_result_back_to_redis(self._mqclient._agent_id,
                                                                                       collect_task_id, testResultList)
                if ret < 0:
                    Logging.getLog().error(u"send_test_result_back_to_redis fail msg=%s" % msg)
            if case_adapter_type == "SPLX_T2" and INIT_CASE_NAME == gl.INIT_CASENAME:
                if testResultList:
                    results = [i['result'] for i in testResultList]
                    results = list(set(results))
                    if len(results) == 1 and "STATE_PASS" in results:
                        Logging.getLog().info(u"��ʼ���˻��ɹ�")
                        Logging.getLog().info(u"�û��ӳֲ�..")
                        cF.runInit_Script()
            gl.case_state = ""
            return 0, ""
        except:
            gl.case_state = ""
            msg = cF.getExceptionInfo()
            Logging.getLog().error(u"�쳣%s" % msg)
            return -1, msg

    def return_case_result_msg(self):
        try:
            values = gl.server_result_info.values()
            case_result_msg = gl.server_result_info["case_result_msg"]
            collect_task_id = gl.server_result_info["collect_task_id"]
            if "" not in values:
                allTestResult = []
                for value in values:
                    allTestResult.extend(value)
                case_result_msg["msg_body"]["result"]["testResult"] = allTestResult
                try:
                    a = json.dumps(case_result_msg, sort_keys=True, indent=4, ensure_ascii=False, encoding="gbk",
                                   separators=(',', ':'))
                except:
                    a = str(case_result_msg).encode('gbk')
                ret, msg = self._mqclient._redis_client.send_test_result_back_to_redis(self._mqclient._agent_id,
                                                                                       collect_task_id,
                                                                                       allTestResult)
                if ret < 0:
                    Logging.getLog().error(u"send_test_result_back_to_redis fail msg=%s" % msg)
        except:
            gl.case_state = ""
            msg = cF.getExceptionInfo()
            Logging.getLog().error(u"�쳣%s" % msg)
            return -1, msg

    def update_db2_account_into(self):
        try:
            data = []
            account_id = gl.account_id
            if gl.g_case_adapter_type == 'SPLX_SELENIUM':
                data = gl.account_info
            else:
                if gl.return_account_update:
                    data.append(gl.return_account_update)
                if gl.return_account_insert:
                    data.append(gl.return_account_insert)
            return 0, gl.current_system_id, data, account_id
        except:
            msg = cF.getExceptionInfo()
            Logging.getLog().error(u"�쳣%s" % msg)
            return -1, msg, '', ''

    def paremReplace(self, cmdstring, dync_dict, system_id, account_group_id):
        """
        :param dync_dict:
        :return:
        """
        if not dync_dict.has_key(system_id):
            return cmdstring
        if not dync_dict[system_id].has_key(str(account_group_id)):
            return cmdstring
        for key in dync_dict[system_id][str(account_group_id)].keys():
            cmdstring = cmdstring.replace("@%s@" % key, dync_dict[system_id][str(account_group_id)][key])
        return cmdstring

    def getT2Funcid(self, addtional_info, key):
        pair_list = addtional_info.split('#')
        value = ""
        for pair in pair_list:
            pair_key, pair_value = pair.split('=')
            if pair_key.upper() == key.upper():
                return pair_value
        return value

        # def processInit(self,url):
        #    try:
        #        case_result_msg = {}
        #        testResultBody = {}

        #        group_variable_dict = {}

        #        f = open(url,'r')
        #        info = f.read().decode('gbk')

        #        msg_object = json.loads(info,object_pairs_hook=OrderedDict)

        #        # ��װӦ����Ϣͷ
        #        case_list = [msg_object]

        #        for i,case in enumerate(case_list):
        #            # ��װӦ����Ϣͷ
        #            case_result_msg = copy.copy(gl.case_result_msg)
        #            testResultBody = {}

        #            testResultBody["runTaskid"] = ""
        #            testResultList = []


        #            for j,step in enumerate(case["caseSteps"]):
        #                for k,test_data in enumerate(step["test_data"]):
        #                    testResult = {}
        #                    testResult["param_data_id"] = test_data["param_data_id"]
        #                    testResult["caseid"] = case["caseid"]
        #                    testResult["result"] = ""
        #                    testResult["log"] = ""
        #                    testResult["msg"] = ""
        #                    testResult["attachment"] = "N"
        #                    testResultList.append(testResult)


        #            #����˳��ִ��ÿһ������

        #            testResultList_index = 0 #��˳�����ÿ����������ݣ��ȽϷ�����������Ķ���
        #            skip_left_steps = False

        #            for j,step in enumerate(case["caseSteps"]):

        #                if skip_left_steps == True:
        #                    break

        #                funcid = self.getT2Funcid(step["addtional_info"],"funcid")
        #                account_group_id = self.getT2Funcid(step["addtional_info"],"accountInfo_id")

        #                #����˳��ִ��ÿһ������
        #                for k,test_data in enumerate(step["test_data"]):
        #                    #����˳��ִ��ÿһ����������

        #                    #ִ������ǰ��
        #                    pres = test_data["pres"]
        #                    pros = test_data["pros"]
        #                    if step.has_key('adapter_type') and step['adapter_type'] == "ADAPTER_T2":
        #                        # ��Ҫ�����ݽ��н���
        #                        if step["step_no"] == '19':
        #                            pass
        #                        pres = base64.b64decode(pres).decode('utf8')
        #                        pros = base64.b64decode(pros).decode('utf8')
        #                        #print pres
        #                        #print ''
        #                        #print pros
        #                    cmdstring = test_data["param"]
        #                    cmdstring = cF.GlobalParameterReplace(cmdstring,account_group_id) #fixme

        #                    ret,msg = cF.action_process(pres,group_variable_dict,[],funcid,cmdstring,account_group_id)
        #                    if ret != 0:
        #                        #Logging.getLog().critical("��������%s ǰ�ö���ִ��ʧ�ܣ�%s" %(test_data["param_data_id"],str(msg)))
        #                        print msg
        #                        testResultList[testResultList_index]["result"] = "STATE_SKIP"
        #                        testResultList[testResultList_index]["msg"] = u"����ǰ�ö���ִ��ʧ�ܣ�%s" %str(msg)
        #                        testResultList_index += 1
        #                        skip_left_steps = True
        #                        break
        #                    print u"��ʼִ��ҵ��ű� %s" %step["step_no"]
        #                    cmdstring = cF.GroupParameterReplace(cmdstring,group_variable_dict)
        #                    #ִ��ҵ��ű�
        #                    if step.has_key('adapter_type') and step['adapter_type'] == "ADAPTER_T2":
        #                        if self._t2adapter._state == 0:
        #                            ret,msg = self._t2adapter.connect()
        #                            if ret < 0:
        #                                #Logging.getLog().critical("��ʼ���ű�%s ����T2Serverʧ�ܣ�%s" %(test_data["stepid"],str(msg)))
        #                                print msg
        #                                testResultList[testResultList_index]["result"] = "STATE_SKIP"
        #                                testResultList[testResultList_index]["msg"] = u"��ʼ���ű�����T2Serverʧ�ܣ�%s%s" %str(msg)
        #                                testResultList_index += 1
        #                                skip_left_steps = True
        #                                break
        #                        ret,msg = self._t2adapter.executeOneTestCase(funcid,cmdstring)
        #                        if ret < 0:
        #                            #Logging.getLog().critical("sendT2Bizʧ�ܣ�%s" %(test_data["param_data_id"],str(msg)))
        #                            print msg
        #                            testResultList[testResultList_index]["result"] = "STATE_FAIL"
        #                            testResultList[testResultList_index]["msg"] = msg
        #                            testResultList_index += 1
        #                            skip_left_steps = True
        #                            break
        #                        elif ret == 0:
        #                            dataset_list = self._t2adapter.getReturnRows()
        #                            #######
        #                            writer = csv.writer(file("%s.csv" %step["step_no"],"wb"))
        #                            for row in dataset_list[0]:
        #                                writer.writerow(row)
        #                            #######
        #                            if int(test_data['expectation']) != 0:
        #                                testResultList[testResultList_index]["result"] = "STATE_FAIL"
        #                                testResultList[testResultList_index]["msg"] = "���غ�Ԥ��ֵ��һ�£�Ԥ��%s ����0" %test_data['expectation']
        #                                testResultList_index += 1
        #                                skip_left_steps = True
        #                                break
        #                            else:
        #                                #ִ�����ݺ�������
        #                                ret,msg = cF.action_process(pros,group_variable_dict,dataset_list[0],funcid,cmdstring,account_group_id)
        #                                if ret != 0:
        #                                    print msg
        #                                    #Logging.getLog().critical(u"��������%s ǰ�ö���ִ��ʧ�ܣ�%s" %(test_data["param_data_id"],str(msg)))
        #                                    testResultList[testResultList_index]["result"] = "STATE_FAIL"
        #                                    testResultList[testResultList_index]["msg"] = u"���ݺ�������ִ��ʧ�ܣ�%s" %msg
        #                                    #testResultList[testResultList_index]["log"] = log_info
        #                                    testResultList_index += 1
        #                                    self._last_username = ""
        #                                    skip_left_steps = True
        #                                    break
        #                                else:
        #                                    testResultList[testResultList_index]["result"] = "STATE_PASS"
        #                                    testResultList[testResultList_index]["msg"] = ""
        #                                    testResultList_index += 1
        #                        elif ret == 1:
        #                            dataset_list = self._t2adapter.getReturnRows()
        #                            rows_list = dataset_list[0]

        #                            #######
        #                            writer = csv.writer(file("%s.csv" %step["step_no"],"wb"))
        #                            for row in rows_list:
        #                                writer.writerow(row)
        #                            #######
        #                            error_no = ''
        #                            if rows_list[0][1] == 'error_no':
        #                                error_no = rows_list[1][1]
        #                            if error_no == '': #�޷���ȷ��ȡerror_no
        #                                testResultList[testResultList_index]["result"] = "STATE_FAIL"
        #                                testResultList[testResultList_index]["msg"] = msg
        #                                testResultList_index += 1
        #                                skip_left_steps = True
        #                                break
        #                            else:
        #                                if int(error_no) == int(test_data['expectation']): #����Ԥ�ڣ��ж��ɹ�
        #                                    #fixme
        #                                    #TODO
        #                                    print "TODO LATER"
        #                                    pass
        #                                else:
        #                                    testResultList[testResultList_index]["result"] = "STATE_FAIL"
        #                                    testResultList[testResultList_index]["msg"] = msg
        #                                    testResultList_index += 1
        #                                    skip_left_steps = True
        #                                    break

        #                    else:
        #                        ret,msg,log_info = self.RunSikuliScript("0",test_data["path"],test_data["param"],msg_body["runTaskid"],test_data["param_data_id"],case["SCRIPT_NAME"])
        #                        if ret < 0:

        #                            testResultList[testResultList_index]["result"] = "STATE_FAIL"
        #                            testResultList[testResultList_index]["msg"] = msg
        #                            testResultList[testResultList_index]["log"] = log_info
        #                            testResultList_index += 1
        #                            skip_left_steps = True
        #                            self._last_username = ""
        #                            break

        #            if skip_left_steps == True:
        #                self._last_username = ""
        #                for idx in xrange(testResultList_index+1,len(testResultList)):
        #                    testResultList[idx]["testResult"] = "STATE_SKIP"

        #            testResultBody["testResult"] = testResultList
        #            case_result_msg["msg_body"]["result"] = testResultBody

        #            #���ڿ��Է�����Ϣ�����������ˡ�
        #            a = json.dumps(case_result_msg,indent=4,ensure_ascii=False,encoding="utf8")
        #            self._result_msg_list.append(a)
        #            #open("%s.json" %msg_body["runTaskid"],'w').write(a)
        #            print a

        #            #ret,msg = self._mqclient.SendMessage(case_result_msg)
        #            #if ret < 0:
        #            #    print u"������Ϣʧ����ʾ %s" %msg
        #            #    return ret,msg
        #            #else:
        #            #    print u"���ͽ����Ϣ�ɹ�"
        #        return 0,""
        #    except:
        #        msg = cF.getExceptionInfo()
        #        print u"�쳣%s" %msg
        #        return -1,msg
        #    pass
        # def AnalyseMessage(self,url):
        #    _last_username = ""
        #    try:
        #        testResultDict = {}
        #        testResultBody = {}


        #        f = open(url,'r')
        #        info = f.read().decode('gbk')

        #        msg_object = json.loads(info,object_pairs_hook=OrderedDict)
        #        msg_body = msg_object["msg_body"]

        #        # ��װӦ����Ϣͷ

        #        for i,case in enumerate(msg_body["cases"]):
        #            # ��װӦ����Ϣͷ
        #            testResultDict = {}
        #            testResultBody = {}

        #            testResultDict["msg_id"] = "5"
        #            testResultDict["msg_desc"] = u"���Խ���ϴ�"

        #            testResultBody["runTaskid"] = msg_body["runTaskid"]
        #            testResultList = []


        #            for j,step in enumerate(case["caseSteps"]):
        #                for k,test_data in enumerate(step["test_data"]):
        #                    testResult = {}
        #                    testResult["param_data_id"] = test_data["param_data_id"]
        #                    testResult["result"] = ""
        #                    testResult["log"] = ""
        #                    testResult["msg"] = ""
        #                    testResult["attachment"] = "N"
        #                    testResultList.append(testResult)


        #            #����˳��ִ��ÿһ������

        #            testResultList_index = 0 #��˳�����ÿ����������ݣ��ȽϷ�����������Ķ���
        #            skip_left_steps = False

        #            for j,step in enumerate(case["caseSteps"]):

        #                if skip_left_steps == True:
        #                    break

        #                #����˳��ִ��ÿһ������
        #                for k,test_data in enumerate(step["test_data"]):
        #                    #����˳��ִ��ÿһ����������

        #                    #ִ������ǰ��
        #                    ret,msg = cF.action_process(0,test_data["pres"])
        #                    if ret != 0:
        #                        Logging.getLog().critical("��������%s ǰ�ö���ִ��ʧ�ܣ�%s" %(test_data["stepid"],str(msg)))
        #                        testResultList[testResultList_index]["result"] = u"����"
        #                        testResultList[testResultList_index]["msg"] = u"����ǰ�ö���ִ��ʧ�ܣ�%s" %str(msg)
        #                        testResultList_index += 1
        #                        skip_left_steps = True
        #                        break

        #                    #�ȵ�¼
        #                    username, password = self.getUserAndPassFromParam(test_data['param'])

        #                    if username != _last_username:

        #                        #�ȴ�³һ�㣬�ɵ����׽���
        #                        self.killFuyiProcess()
        #                        login_param = 'user=%s#pass=%s' %(username,password)
        #                        ret,msg,log_info = self.RunSikuliScript("0","common\\login.sikuli",login_param,msg_body["runTaskid"],test_data["param_data_id"])
        #                        if ret < 0:
        #                            testResultList[testResultList_index]["result"] = u"ʧ��"
        #                            testResultList[testResultList_index]["msg"] = u"��¼����ʧ�ܣ�%s" %str(msg)
        #                            testResultList[testResultList_index]["log"] = log_info
        #                            testResultList_index += 1
        #                            skip_left_steps = True
        #                            break
        #                        _last_username = username

        #                    #ִ��ҵ��ű�
        #                    ret,msg,log_info = self.RunSikuliScript("0",test_data["path"],test_data["param"],msg_body["runTaskid"],test_data["param_data_id"])
        #                    if ret < 0:
        #                        testResultList[testResultList_index]["result"] = u"ʧ��"
        #                        testResultList[testResultList_index]["msg"] = msg
        #                        testResultList[testResultList_index]["log"] = log_info
        #                        testResultList_index += 1
        #                        skip_left_steps = True
        #                        break

        #                    #���ǳ�
        #                    #ret,msg,log_info = RunSikuliScript("0",username,password,"common\\logout.sikuli","",test_data["param_data_id"])
        #                    #if ret < 0:
        #                    #    testResultList[testResultList_index]["result"] = u"ʧ��"
        #                    #    testResultList[testResultList_index]["msg"] = u"�ǳ�����ʧ�ܣ�%s" %str(msg)
        #                    #    testResultList[testResultList_index]["log"] = log_info
        #                    #    testResultList_index += 1
        #                    #    skip_left_steps = True
        #                    #    break

        #                    #ִ�����ݺ�������
        #                    ret,msg = cF.action_process(0,test_data["pros"])
        #                    if ret != 0:
        #                        Logging.getLog().critical(u"��������%s ǰ�ö���ִ��ʧ�ܣ�%s" %(test_data["stepid"],str(msg)))
        #                        testResultList[testResultList_index]["result"] = u"ʧ��"
        #                        testResultList[testResultList_index]["msg"] = u"���ݺ�������ִ��ʧ�ܣ�%s" %msg
        #                        testResultList[testResultList_index]["log"] = log_info
        #                        testResultList_index += 1
        #                        skip_left_steps = True
        #                        break


        #                    testResultList[testResultList_index]["result"] = u"�ɹ�"
        #                    testResultList[testResultList_index]["msg"] = ""
        #                    testResultList[testResultList_index]["log"] = log_info
        #                    testResultList_index += 1

        #            if skip_left_steps == True:
        #                for idx in xrange(testResultList_index+1,len(testResultList)):
        #                    testResultList[idx]["testResult"] = u"����"

        #            testResultBody["testResult"] = testResultList
        #            testResultDict["msg_body"] = testResultBody

        #            #���ڿ��Է�����Ϣ�����������ˡ�
        #            a = json.dumps(testResultDict,indent=4,ensure_ascii=False,encoding="utf8")
        #            self._result_msg_list.append(a)
        #            open("%s.json" %msg_body["runTaskid"],'w').write(a)
        #            print a
        #        return 0,""
        #    except:
        #        msg = cF.getExceptionInfo()
        #        return -1,msg
        #    pass


if __name__ == '__main__':
    cF.readConfigFile()
    engine = executionEngine(None)
    engine.upload_appium_capture(1, 2, 'AutoTest.jar')
    # gl.g_engine = engine
    # ret,msg = engine.processInit(r'C:\01_projects\TestAgent\init.json')
    # if ret < 0:
    #    print msg
    # engine.CaptureScreen()
    # engine = executionEngine()
    # engine.killFuyiProcess()
    # pass
