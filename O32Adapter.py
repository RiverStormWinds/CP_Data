# -*- coding:gbk -*-
from ctypes import *

class IKnown(Structure):
    _pack_ =1
    _fields_ = [
        ("QueryInterface",long),
        ("AddRef",long),
        ("Release",long),
    ]
class CConfigInterface(IKnown):
    _pack_ = 1
    _fields_ = [
        ("Load",c_int)
        ("Save",c_int)
        ("GetString",c_void_p)
    ]

class O32Adapter(object):
    def __init__(self):
        pass
    def _init_interface(self,address,license_path):
        dllpath = ".\\t2sdk_o32.dll"
        self._dll_handle = windll.LoadLibrary(dllpath)
        config = self._dll_handle.NewConfig()
        config.AddRef()

        pass

if __name__ == '__main__':
    adapter = O32Adapter()
    adapter._init_interface("10.189.65.106:9003':","license_o32.dat")

    pass