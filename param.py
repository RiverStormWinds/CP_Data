# -*- coding: gbk -*- 
import gl
import commFuncs as cF
import datetime
from datetime import date
from datetime import timedelta

InParamReplaceDict={
    "@openprice@":"getPrice"
}


def getStkcodeByString(cmd):
    flag = False
    lpos = cmd.find("stkcode=")
    if lpos == -1:
        flag = True
        lpos = cmd.find("ofcode=")
        if lpos == -1:
            return None
    rpos = cmd.find("#",lpos)
    if rpos == -1:
        if flag == False:
            return cmd[cmd.find('stkcode')+7:]
        else:
            return cmd[cmd.find('ofcode')+8:]
    else:
        if (lpos + 8  == rpos and flag == False) or (lpos + 7  == rpos and flag == True):
            return None
        else:
            if flag == False:
                return cmd[lpos+len("stkcode="):rpos]
            else:
                return cmd[lpos+len("ofcode="):rpos]
def getPriceByStkcode(market, stkcode,serverid=0):
    if market:
        sql = "select openprice from stkprice where stkcode = '%s' and market='%s'" %(stkcode, market)
        ds = cF.executeRunSQL(sql,serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['openprice']
    else:
        sql = "select openprice from stkprice where stkcode = '%s'" % (stkcode)
        ds = cF.executeRunSQL(sql, serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['openprice']

def getFixPriceByStkcode(market, stkcode,serverid=0):
    if market:
        sql = "select  fixprice from stktrd where stkcode = '%s' and market= '%s'" %(stkcode, market)
        ds = cF.executeRunSQL(sql,serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['fixprice']
    else:
        sql = "select  fixprice from stktrd where stkcode = '%s'" % (stkcode)
        ds = cF.executeRunSQL(sql, serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['fixprice']

def getMaxRisevalueByStkcode(market, stkcode,serverid=0):
    if market:
        sql = "select  maxrisevalue from stktrd where stkcode = '%s' and market='%s'" %(stkcode, market)
        ds = cF.executeRunSQL(sql,serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['maxrisevalue']
    else:
        sql = "select  maxrisevalue from stktrd where stkcode = '%s'" % (stkcode)
        ds = cF.executeRunSQL(sql, serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['maxrisevalue']
def getMaxDownvalueByStkcode(market, stkcode,serverid=0):
    if market:
        sql = "select  maxdownvalue from stktrd where stkcode = '%s' and market = '%s'" %(stkcode, market)
        ds = cF.executeRunSQL(sql,serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['maxdownvalue']
    else:
        sql = "select  maxdownvalue from stktrd where stkcode = '%s'" % (stkcode)
        ds = cF.executeRunSQL(sql, serverid)
        if ds == []:
            return 0
        else:
            return ds[0]['maxdownvalue']
def getPrice(cmdstring,serverid=0):
    stkcode = getStkcodeByString(cmdstring)
    if stkcode == None:
        return 0
    cmd_list = cmdstring.split("#")
    market = ""
    for cmd in cmd_list:
        field = cmd.split("=")[0].strip()
        value = cmd.split("=")[1].strip()
        if field == "market":
            market = value
    return getPriceByStkcode(market, stkcode,serverid)
def getfixPrice(cmdstring,serverid=0):
    stkcode = getStkcodeByString(cmdstring)
    if stkcode == None:
        return 0
    cmd_list = cmdstring.split("#")
    market = ""
    for cmd in cmd_list:
        field = cmd.split("=")[0].strip()
        value = cmd.split("=")[1].strip()
        if field == "market":
            market = value
    return getFixPriceByStkcode(market, stkcode,serverid)
def getmaxRisevalue(cmdstring,serverid=0):
    stkcode = getStkcodeByString(cmdstring)
    if stkcode == None:
        return 0
    cmd_list = cmdstring.split("#")
    market = ""
    for cmd in cmd_list:
        field = cmd.split("=")[0].strip()
        value = cmd.split("=")[1].strip()
        if field == "market":
            market = value
    return getMaxRisevalueByStkcode(market, stkcode,serverid)
def getmaxDownvalue(cmdstring,serverid=0):
    stkcode = getStkcodeByString(cmdstring)
    if stkcode == None:
        return 0
    cmd_list = cmdstring.split("#")
    market = ""
    for cmd in cmd_list:
        field = cmd.split("=")[0].strip()
        value = cmd.split("=")[1].strip()
        if field == "market":
            market = value
    return getMaxDownvalueByStkcode(market, stkcode,serverid)

#def getOperDate(serverid = 0):
#    sql = "exec sql..up_com_getphydate"
#    ds = cF.executeRunSQLWithMultiCursor(sql,serverid)
#    pass
    #dbstring =  "DRIVER={SQL Server};SERVER=%s;DATABASE=';UID=%s;PWD=%s;autocommit=True" %(gl.g_connectSqlServerSetting[str(server)]["ip"],gl.g_connectSqlServerSetting[str(server)]["database"],gl.g_connectSqlServerSetting[str(server)]["username"],gl.g_connectSqlServerSetting[str(server)]["password"])


def getSysDate(serverid=0):
    sql = "select sysdate from sysconfig"
    ds = cF.executeRunSQL(sql,serverid)
    return ds[0]["sysdate"]

def getLastWorkDay(nowday):
    d = date(int(nowday[0:4]),int(nowday[4:6]),int(nowday[6:8]))
    d = d+timedelta(days = -1)
    while d.weekday() == 5 or d.weekday()==6:
        d = d+timedelta(days = -1)
    return d.strftime('%Y%m%d')

def getNextWorkDay(nowday):
    d = date(int(nowday[0:4]),int(nowday[4:6]),int(nowday[6:8]))
    d = d+timedelta(days = 1)
    while d.weekday() == 5 or d.weekday()==6:
        d = d+timedelta(days = 1)
    return d.strftime('%Y%m%d')

def inParamReplace(cmdstring,serverid=0):

    # 价格参数替换
    if cmdstring.find("@openprice@")>=0:
        cmdstring = cmdstring.replace("@openprice@",str(getPrice(cmdstring,serverid)))
    elif cmdstring.find("@closeprice@")>=0:
        cmdstring = cmdstring.replace("@closeprice@",str(getPrice(cmdstring,serverid)))
    elif cmdstring.find("@lastprice@")>=0:
        cmdstring = cmdstring.replace("@lastprice@",str(getPrice(cmdstring,serverid)))
    elif cmdstring.find("@highprice@")>=0:
        cmdstring = cmdstring.replace("@highprice@",str(getPrice(cmdstring,serverid)))
    elif cmdstring.find("@lowprice@")>=0:
        cmdstring = cmdstring.replace("@lowprice@",str(getPrice(cmdstring,serverid)))
    elif cmdstring.find("@maxrisevalue@")>=0:
        cmdstring = cmdstring.replace("@maxrisevalue@",str(getmaxRisevalue(cmdstring,serverid)))
    elif cmdstring.find("@maxdownvalue@")>=0:
        cmdstring = cmdstring.replace("@maxdownvalue@",str(getmaxDownvalue(cmdstring,serverid)))
    elif cmdstring.find("@fixprice@")>=0:
        cmdstring = cmdstring.replace("@fixprice@",str(getfixPrice(cmdstring,serverid)))

    # 日期参数替换
    if cmdstring.find("@sys_date@")>=0:
        cmdstring = cmdstring.replace("@sys_date@",str(getSysDate(serverid)))
    elif cmdstring.find("@last_work_date@")>=0:
        cmdstring = cmdstring.replace("@last_work_date@",getLastWorkDay(str(getSysDate(serverid))))
    elif cmdstring.find("@next_work_date@")>=0:
        cmdstring = cmdstring.replace("@next_work_date@",getLastWorkDay(str(getSysDate(serverid))))

    return cmdstring
    pass
def getInParamDictFromCmdstring(cmdstring):
    """
    将命令行变为入参：值的字典

    Args:
        cmdstring: 命令行

    Returns:
        par_dict: 给出｛入参：值｝的字典
    """ 
    par_dict = {}
    cmdstring = cmdstring.strip(',')
    for item in cmdstring.split(','):
        par,val = item.strip().split(':')
        par_dict[par] = val
    return par_dict
        

if __name__=='__main__':
    getStkcodeByString("funcid=410411#custid=@custid@#custorgid=@orgid@#trdpwd=@trdpwd@#netaddr=000000000000#orgid=@orgid@#operway=7#ext=#market=1#secuid=@sh_a_secuid@#fundid=@fundid@#stkcode=600000#bsflag=0B#price=@openprice@#qty=100#ordergroup=0#bankcode=@bankcode@#remark=#bankpwd=")
    # cF.readConfigFile()
    # getOperDate("4")
    # # getInParamDictFromCmdstring("g_serverid:%s,g_operid:%s,g_operpwd:@trdpwd@,g_operway:4,g_funcid:150420,g_stationaddr:001641AA2350,operdate:@sys_date@,sno:@sno@,action:1,afmremark:,")