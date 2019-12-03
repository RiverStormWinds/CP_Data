import time
import os
import sys
from xmlrpclib import ServerProxy


def callRpcClassFunction():
    try:
        ServerUrl = "http://127.0.0.1:5556"
        s = ServerProxy(ServerUrl)
        print s
        ret, msg = s.register_client("1", "127.0.0.1", "16002")
        if ret < 0:
            print msg
        else:
            print msg
    except BaseException, ex:
        print ex


def callModifyRemoteServerDateTime(IP, Port, Date, Time):
    # print( "Please enter the server IP:" )
    # IP = raw_input()
    # print( "Please enter the server port:" )
    # Port = raw_input()
    # print( "Please enter the time，like（2015-03-02 02：03：04）" )
    # ServerTime=raw_input()

    ltime = time.strptime("%s %s" % (Date, Time), "%Y-%m-%d %H:%M:%S")
    print(ltime)
    ttime = time.localtime(time.mktime(ltime))
    print(ttime)
    ServerUrl = "http://" + IP + ":" + Port
    # s = ServerProxy(ServerUrl)
    # print s
    # ret, msg = s.ModifyRemoteServerDateTime(ttime.tm_year, ttime.tm_mon, ttime.tm_mday, ttime.tm_hour, ttime.tm_min,
    #                                         ttime.tm_sec)
    ret, msg = 0, ''
    if ret < 0:
        print msg


if __name__ == '__main__':
    callRpcClassFunction()
    # if (len(sys.argv) >3):
    #    IP = sys.argv[1]
    #    Port = sys.argv[2]
    #    Date = sys.argv[3]
    #    Time = sys.argv[4]
    #    callModifyRemoteServerDateTime(IP,Port,Date,Time)
    # else:
    #    print("para error, pls input ip,port,date,time ...")
