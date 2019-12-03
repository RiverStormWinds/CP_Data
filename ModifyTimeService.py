# -*- coding:gbk -*-
import time
import os
from SimpleXMLRPCServer import SimpleXMLRPCServer
import commFuncs as cF

def ModifyRemoteServerDateTime(year,month,day,hour,min,sec):
    '''
    修改本地日期和时间
    '''
    try:
        dat = "date %u-%02u-%02u"%(year,month,day)
        tm = "time %02u:%02u:%02u"%(hour,min,sec)
        os.system(dat)
        os.system(tm)
    except :
        exc_info = cF.getExceptionInfo()
        print exc_info
        return -1,exc_info
    return 0,"";

if __name__ =='__main__':
    s=SimpleXMLRPCServer( ('0.0.0.0',5556) )
    s.register_function(ModifyRemoteServerDateTime)
    s.serve_forever()