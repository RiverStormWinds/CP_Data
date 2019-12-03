# -*- coding:gbk -*-
import commFuncs as cF
from KCBPCLIAdapter import KCBPAdapter
import sys
import gl
import datetime


def AddETFBacketStockAsset(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid_1, secuid_2, stkcode, count):
    '''
    只支持沪市和深市
    '''
    try:
        sql = "select stkcode,amount,marketstk from etfcomponentinfo where ofcode='%s' " % stkcode
        ds = cF.executeRunSQL(sql, 'p')
        # print ds
        if len(ds) <= 0:
            return -1, u"未找到成分股"
        serverid = cF.get_core(servertype)
        adapter = KCBPAdapter(gl.g_connectSqlServerSetting[serverid]["xpip"])
        ret = adapter.KCBPCliInit()
        if ret < 0:
            return -1, u"初始化KCBP适配器失败"
        for rec in ds:
            secuid = ""
            if rec['marketstk'] == '1':
                secuid = secuid_1
            else:
                secuid = secuid_2
            cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:%s,fundid:%s,secuid:%s,market:%s,stkcode:%s,stkeffect:%s,cost:10,remark:" % (
                str(serverid), operid_1, trdpwd, orgid, fundid, secuid,
                str(rec['marketstk']), rec["stkcode"], str(int(rec["amount"]) * int(count)))
            ret, code, level, msg = adapter.SendRequest(cmdstring)
            if ret < 0 or code != "0":
                adapter.KCBPCliExit()
                return -1, u"ret=%s,code=%s,level=%s,msg=%s" % (str(ret), str(code), str(level), msg)
            ds = adapter.GetReturnResult()
            sno = ds[1][0]
            cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150420,g_stationaddr:06690A0013D2,operdate:%s,sno:%s,action:1,afmremark:autotest" % (
                serverid, operid_2, trdpwd,
                datetime.datetime.now().strftime('%Y%m%d'), sno)
            ret, code, level, msg = adapter.SendRequest(cmdstring)
            if ret < 0 or code != "0":
                adapter.KCBPCliExit()
                return -1, u"ret=%s,code=%s,level=%s,msg=%s" % (str(ret), str(code), str(level), msg)
        adapter.KCBPCliExit()
        return 0, "OK"
    except:
        exc_info = cF.getExceptionInfo()
        print exc_info
        return -1, exc_info


def AddStockAsset(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid, market, stkcode, count):
    '''
    只支持沪市和深市
    '''
    try:
        serverid = cF.get_core(servertype)
        adapter = KCBPAdapter(gl.g_connectSqlServerSetting[serverid]["xpip"])
        ret = adapter.KCBPCliInit()
        if ret < 0:
            return -1, u"初始化KCBP适配器失败"

        cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150402,g_stationaddr:001641AA2350,orgid:%s,fundid:%s,secuid:%s,market:%s,stkcode:%s,stkeffect:%s,cost:10,remark:" % (
            str(serverid), operid_1, trdpwd, orgid, fundid, secuid, market,
            stkcode, str(count))
        ret, code, level, msg = adapter.SendRequest(cmdstring)
        if ret < 0 or code != "0":
            adapter.KCBPCliExit()
            return -1, u"ret=%s,code=%s,level=%s,msg=%s" % (str(ret), str(code), str(level), msg)
        ds = adapter.GetReturnResult()
        sno = ds[1][0]
        cmdstring = "g_serverid:%s,g_operid:%s,g_operpwd:%s,g_operway:4,g_funcid:150420,g_stationaddr:06690A0013D2,operdate:%s,sno:%s,action:1,afmremark:autotest" % (
            serverid, operid_2, trdpwd,
            datetime.datetime.now().strftime('%Y%m%d'), sno)

        ret, code, level, msg = adapter.SendRequest(cmdstring)
        if ret < 0 or code != "0":
            adapter.KCBPCliExit()
            return -1, u"ret=%s,code=%s,level=%s,msg=%s" % (str(ret), str(code), str(level), msg)
        adapter.KCBPCliExit()
        return 0, "OK"
    except:
        exc_info = cF.getExceptionInfo()
        print exc_info
        return -1, exc_info


if __name__ == '__main__':

    # for etf stock 
    if len(sys.argv) != 11:
        print u'请输入AddETFBasketStockAsset.exe servertype operid_1 operid_2 trdpwd orgid fundid secuid_1 secuid_2 stkcode count'
        sys.exit(1)
    cF.readConfigFile()
    servertype = sys.argv[1]
    operid_1 = sys.argv[2]
    operid_2 = sys.argv[3]
    trdpwd = sys.argv[4]
    orgid = sys.argv[5]
    fundid = sys.argv[6]
    secuid_1 = sys.argv[7]
    secuid_2 = sys.argv[8]
    stkcode = sys.argv[9]
    count = sys.argv[10]
    ret, msg = AddETFBacketStockAsset(servertype, operid_1, operid_2, trdpwd, orgid, fundid, secuid_1, secuid_2,
                                      stkcode, count)
    # for general stock
    '''
    if len(sys.argv) != 11:
        print u'请输入AddETFBasketStockAsset.exe servertype operid_1 operid_2 trdpwd orgid fundid secuid market stkcode count'
        sys.exit(1)
    cF.readConfigFile()
    servertype = sys.argv[1]
    operid_1 = sys.argv[2]
    operid_2 = sys.argv[3]
    trdpwd = sys.argv[4]
    orgid = sys.argv[5]
    fundid = sys.argv[6]
    secuid = sys.argv[7]
    market = sys.argv[8]
    stkcode = sys.argv[9]
    count = sys.argv[10]
    ret,msg = AddStockAsset(servertype,operid_1,operid_2,trdpwd,orgid,fundid,secuid,market,stkcode,count)
    '''
    if ret == 0:
        print "Operation OK"
    else:
        print "Operation Fail"
        print msg
        sys.exit(1)
