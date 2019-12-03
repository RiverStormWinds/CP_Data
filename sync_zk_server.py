#!/usr/bin/python
# -*- coding: gbk -*-
import os
import sys
import subprocess
from SimpleXMLRPCServer import SimpleXMLRPCServer
reload(sys)
sys.setdefaultencoding('gbk')


def init_Sync_zk_data():
    try:
        homedir = os.getcwd()
        path  = homedir + "\\Sync_ZK.bat"
        p = subprocess.Popen("%s"%path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        curline = p.stdout.readline()
        while (curline != b''):
            print(curline)
            curline = p.stdout.readline()
        p.wait()
        print(p.returncode)
        return 0, ""
    except Exception as e:
        print e
        return -1, e


if __name__ == '__main__':
    print u"启动 远程调用 Sync_ZK服务"
    s = SimpleXMLRPCServer(('0.0.0.0', 16001))
    s.register_function(init_Sync_zk_data)
    s.serve_forever()
