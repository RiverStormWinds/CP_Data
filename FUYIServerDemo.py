# -*- coding: gbk -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Jun 17 2015)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class MainFrame
###########################################################################

import MQServer
import message
import gl
import datetime
import json
import commFuncs as cF
from collections import OrderedDict
import copy
import task
import time
import threading


class MainFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=u"自动化测试Server模拟器", pos=wx.DefaultPosition,
                          size=wx.Size(1024, 768),
                          style=wx.CLOSE_BOX | wx.DEFAULT_FRAME_STYLE | wx.MAXIMIZE | wx.MAXIMIZE_BOX | wx.MINIMIZE | wx.TAB_TRAVERSAL)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.m_panel = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer121 = wx.BoxSizer(wx.VERTICAL)

        sbSizer3 = wx.StaticBoxSizer(wx.StaticBox(self.m_panel, wx.ID_ANY, u"发送框"), wx.VERTICAL)

        bSizer5 = wx.BoxSizer(wx.VERTICAL)

        self.m_txtSend = wx.TextCtrl(sbSizer3.GetStaticBox(), wx.ID_ANY,
                                     style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.ALIGN_LEFT | wx.TE_BESTWRAP)
        bSizer5.Add(self.m_txtSend, 1, wx.ALL | wx.EXPAND, 5)

        sbSizer3.Add(bSizer5, 1, wx.EXPAND, 5)

        bSizer6 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer7 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer7.AddSpacer((0, 0), 1, wx.EXPAND, 5)

        bSizer6.Add(bSizer7, 1, wx.EXPAND, 5)

        bSizerBtnRunTask = wx.BoxSizer(wx.HORIZONTAL)
        self.m_btnRunTask = wx.Button(sbSizer3.GetStaticBox(), wx.ID_ANY, u"RunTask", wx.DefaultPosition,
                                      wx.DefaultSize, 0)
        bSizerBtnRunTask.Add(self.m_btnRunTask, 0, wx.ALL, 5)
        bSizer6.Add(bSizerBtnRunTask, 0, wx.EXPAND, 5)

        bSizer8 = wx.BoxSizer(wx.HORIZONTAL)

        m_cmbAgentChoices = []
        self.m_cmbAgent = wx.ComboBox(sbSizer3.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition,
                                      wx.DefaultSize, m_cmbAgentChoices, 0)
        bSizer8.Add(self.m_cmbAgent, 0, wx.ALL, 5)

        bSizer6.Add(bSizer8, 0, wx.EXPAND, 5)

        bSizer9 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_btnSend = wx.Button(sbSizer3.GetStaticBox(), wx.ID_ANY, u"Send", wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer9.Add(self.m_btnSend, 0, wx.ALL, 5)

        bSizer6.Add(bSizer9, 0, wx.EXPAND, 5)

        sbSizer3.Add(bSizer6, 0, wx.EXPAND, 5)

        bSizer121.Add(sbSizer3, 3, wx.EXPAND, 5)

        sbSizer4 = wx.StaticBoxSizer(wx.StaticBox(self.m_panel, wx.ID_ANY, u"接收框"), wx.VERTICAL)

        bSizer10 = wx.BoxSizer(wx.VERTICAL)

        self.m_txtRecv = wx.TextCtrl(sbSizer4.GetStaticBox(), wx.ID_ANY,
                                     style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.ALIGN_LEFT | wx.HSCROLL | wx.TE_WORDWRAP)
        bSizer10.Add(self.m_txtRecv, 1, wx.ALL | wx.EXPAND, 5)

        sbSizer4.Add(bSizer10, 1, wx.EXPAND, 5)

        bSizer11 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer12 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer12.AddSpacer((0, 0), 1, wx.EXPAND, 5)

        bSizer11.Add(bSizer12, 1, wx.EXPAND, 5)

        bSizer13 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_checkNoHB = wx.CheckBox(sbSizer4.GetStaticBox(), wx.ID_ANY, u"屏蔽心跳消息", wx.DefaultPosition,
                                       wx.DefaultSize, 0)
        bSizer13.Add(self.m_checkNoHB, 0, wx.ALL, 5)

        bSizer11.Add(bSizer13, 0, wx.EXPAND, 5)

        sbSizer4.Add(bSizer11, 0, wx.EXPAND, 5)

        bSizer121.Add(sbSizer4, 1, wx.EXPAND, 5)

        self.m_panel.SetSizer(bSizer121)
        self.m_panel.Layout()
        bSizer121.Fit(self.m_panel)
        bSizer1.Add(self.m_panel, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

        message.sub(gl.RECEIVE_DATA_EVENT, self.receiveMsg)

        self._mqserver = MQServer.MQServer()
        self._mqserver.setDaemon(True)
        self._mqserver.start()

        # 客户端信息
        self._client_list = {}  # {"client_id":("state","last-live-time")}

        # 任务处理
        self._taskThread = task.task(self._mqserver)
        self._monitorTaskThread = threading.Thread(target=self.monitorTask)
        self.__exitMonitorTask = False
        self._taskThread.setDaemon(True)
        self._taskThread.start()

        self.m_btnSend.Bind(wx.EVT_BUTTON, self.OnSendButtonClick)
        self.m_btnRunTask.Bind(wx.EVT_BUTTON, self.OnRunTaskButtonClick)

    def OnSendButtonClick(self, evt):
        info = self.m_txtSend.GetValue()

        agent_selection = self.m_cmbAgent.GetStringSelection()
        agent_id = agent_selection[:agent_selection.find("(")]
        ret, msg = self._mqserver.SendMessage(agent_id, info)
        if ret < 0:
            print msg

    def OnRunTaskButtonClick(self, evt):
        self.m_btnRunTask.Enable(False)

        # 处理task任务
        sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_START'"
        ds = cF.executeCaseSQL(sql)
        if len(ds) <= 0:
            self.m_btnRunTask.Enable(True)
            return
        ret, msg = self._taskThread.getCasesList()
        if ret < 0:
            print msg

        self.m_btnRunTask.Enable(True)

    def monitorTask(self):
        '''
        监控数据库任务的下达
        '''
        pass
        while not self._exitMonitorTask:
            sql = "select * from sx_cases_collection_run_task where run_status = 'STATE_START'"
            ds = cF.executeCaseSQL(sql)
            if len(ds) > 0:
                self._task.getCasesList()
            time.sleep(1)

    def sendMessage(self, agent_id, json_msg):
        pass

    def receiveMsg(self, param):
        '''
        收到消息
        '''
        msg_json = json.loads(param)
        ret, msg = self.AnalyseMsg(msg_json)
        if ret < 0:
            return ret, msg

        _msg = param.decode('utf8') + "\r\n"
        self.m_txtRecv.WriteText(_msg)

        lines = self.m_txtRecv.GetNumberOfLines()
        pos = self.m_txtRecv.XYToPosition(0, lines - 1)
        self.m_txtRecv.ShowPosition(pos)

        return 0, ""

    def AnalyseMsg(self, msg):
        if msg["msg_id"] == gl.CLIENT_REGISTER_MSG_ID:
            now = date = datetime.datetime.now()
            self._client_list[msg["msg_body"]["agent_id"]] = (u"注册中", now)

            combo_list = []
            for key in self._client_list.keys():
                combo_list.append("%s(%s)" % (key, self._client_list[key][0]))
            self.m_cmbAgent.Set(combo_list)


        elif msg["msg_id"] == gl.HEARTBEAT_MSG_ID:
            now = datetime.datetime.now()
            self._client_list[msg["msg_body"]["agent_id"]] = (msg["msg_body"]["agent_state"], now)
            combo_list = []
            for key in self._client_list.keys():
                combo_list.append("%s(%s)" % (key, self._client_list[key][0]))
            self.m_cmbAgent.Set(combo_list)
        return 0, ""

    def SendMsg(self):
        pass

    def __del__(self):
        message.unsub(gl.RECEIVE_DATA_EVENT, self.receiveMsg)
        pass


if __name__ == '__main__':
    app = wx.App(redirect=False, filename="FUYIServerDemo.log")
    frame = MainFrame(parent=None)
    frame.Centre()
    frame.Show()
    app.MainLoop()
