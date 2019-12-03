# -*- coding:utf-8 -*-
import sys
import os
from ctypes import *
import json
import time
import binascii
import logging

print(os.getcwd())
sys.path.append(os.getcwd())
# sys.path.append(os.path.abspath(os.getcwd()+os.path.sep+'..'+os.path.sep+'..'))

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


g_cli = None

def GetDllCli():
    global g_cli
    if g_cli is None:
        # load dll
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        sys.path.append(application_path)
        dllpath = os.path.join(application_path, "_TimesvcT2SDK.dll")
        print(dllpath)
        g_cli = CDLL(dllpath)  #
    return g_cli

class TimesvcT2SDK(object):
    """
    适配器，适用于T2
    """

    def __init__(self):
        self._hHandle = None
        self.logger = self._getLogger()

    def _getLogger(self):

        logger = logging.getLogger('[T2 Adapter]')
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        handler = logging.FileHandler(os.path.join(application_path, "CLI Adapter.log"))

        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        return logger

    def InitInterface(self, addr, license_path):
        if self._hHandle != None:
            self.DeInitInterface()
        self._hHandle = None

        """Init T2 API library and return hHandle and cli"""
        ret = c_int(0)
        self._hHandle = c_void_p(0)
        GetDllCli().InitInterface(byref(self._hHandle), addr.encode("gbk"), license_path.encode("gbk"))  #
        return 0

    def DeInitInterface(self):
        """Exit """
        GetDllCli().DeInitInterface(self._hHandle)
        self._hHandle = None
        self.logger.info(u"CLI 退出成功")
        return

    def Connect(self, uiTimeout):
        return GetDllCli().Connect(self._hHandle, uiTimeout)

    def Close(self):
        return GetDllCli().Close(self._hHandle)

    def GenNewPacker(self, npack):
        return GetDllCli().GenNewPacker(self._hHandle, c_int(npack))

    def BeginPack(self):
        GetDllCli().BeginPack(self._hHandle)

    def EndPack(self):
        GetDllCli().EndPack(self._hHandle)

    def AddField(self, szFieldName, cFieldType, iFieldWidth):
        return GetDllCli().AddField(self._hHandle, szFieldName.encode("gbk"), string_to_int8(cFieldType), c_int(iFieldWidth),
                                  c_int(4))

    def AddStr(self, szValue):
        return GetDllCli().AddStr(self._hHandle, szValue.encode("gbk"))

    def AddInt(self, iValue):
        return GetDllCli().AddInt(self._hHandle, iValue)

    def AddDouble(self, fValue):
        return GetDllCli().AddDouble(self._hHandle, c_float(fValue))

    def AddChar(self, cValue):
        return GetDllCli().AddChar(self._hHandle, string_to_int8(cValue))

    def AddRaw(self, lpBuff, iLen):
        return GetDllCli().AddRaw(self._hHandle, lpBuff, iLen)

    def SendBiz(self, funcid):
        return GetDllCli().AddDouble(self._hHandle, c_int(funcid))

    def RecvBiz(self, retPrev, timeout):
        return GetDllCli().RecvBiz(self._hHandle, c_int(retPrev), c_int(timeout))

    def GetErrorMsg(self, nErrorCode):
        return ConvertText(GetDllCli().GetErrorMsg(self._hHandle, c_int(nErrorCode)))

    def GetDatasetCount(self):
        return GetDllCli().GetDatasetCount(self._hHandle)

    def GetColCount(self):
        return GetDllCli().Connect(self._hHandle)

    def SetCurrentDatasetByIndex(self, iDataset):
        return GetDllCli().SetCurrentDatasetByIndex(self._hHandle, c_int(iDataset))

    def GetColName(self, iCol):
        return ConvertText(GetDllCli().GetColName(self._hHandle, c_int(iCol)))

    def GetRowCount(self):
        return GetDllCli().GetRowCount(self._hHandle)

    def GetColType(self, column):
        return GetDllCli().GetColType(self._hHandle, c_int(column))

    def GetStrByIndex(self, column):
        return ConvertText(GetDllCli().GetStrByIndex(self._hHandle, c_int(column)))

    def GetCharByIndex(self, column):
        ch = GetDllCli().GetCharByIndex(self._hHandle, c_int(column))
        if ch:
            ch = chr(ch)
        else:
            ch = ''
        return ch

    def GetDoubleByIndex(self, column):
        return GetDllCli().GetDoubleByIndex(self._hHandle, c_int(column))

    def GetIntByIndex(self, column):
        return GetDllCli().GetIntByIndex(self._hHandle, c_int(column))

    def GetRawByIndex(self, column, lpRawLen):
        rln = lpRawLen
        return c_void_p(GetDllCli().GetRawByIndex(self._hHandle, c_int(column), byref(rln)))

    def Next(self):
        return GetDllCli().Next(self._hHandle)

    def GetLastExtraErrorMsg(self):
        return ConvertText(GetDllCli().GetLastExtraErrorMsg(self._hHandle))

    def testPoint(self):
        return GetDllCli().testPoint(self._hHandle)

    def ConvertToken(self):
        return GetDllCli().ConvertToken(self._hHandle)

def string_to_int8(ch):
    return c_int8(ord(ch))
def new_intp():
    intp = c_int(0)
    return intp


def intp_value(intp):
    return intp.value


def cdata(raw, len):
    szTmpbuf = create_string_buffer(b'\000' * (len + 2))
    memset(szTmpbuf, 0, len + 2)
    memmove(szTmpbuf, raw, len)
    return szTmpbuf


def ConvertText(txt):
    if txt is None:
        return None
    str1 = c_char_p(txt)
    return str1.value


if __name__ == '__main__':

    o32 = TimesvcT2SDK()
    o32.InitInterface('127.0.0.1:99000', 'license.dat')
    ret = o32.Connect(1000)
    if ret != 0:
        ret = o32.GetErrorMsg(ret).decode('gbk')
    ret = o32.AddField("a111",  'S',1000)
    ret = o32.AddStr('str111')
    ret = o32.AddInt(666)
    ret = o32.AddDouble(0.888)
    ret = o32.AddChar('s')
    szTmpbuf = create_string_buffer(b'\000' * (10 + 2))
    ret = o32.AddRaw(szTmpbuf,10)

    ret = o32.GetColName(5)
    ret = o32.GetColType(5)
    ret = o32.GetStrByIndex(5)
    ret = o32.GetCharByIndex(5)
    ret = o32.GetDoubleByIndex(5)
    ret = o32.GetIntByIndex(5)
    lpLen = new_intp()
    raw = o32.GetRawByIndex(2, lpLen)
    len = intp_value(lpLen)
    str1 = cdata(raw, len)
    s = str1.value.decode()
    val = binascii.b2a_hex(str1)
    #ret = o32.GetRawByIndex(5,)
    ret = o32.Close()
    o32.DeInitInterface()
    pass
