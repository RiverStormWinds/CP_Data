# coding:utf-8
import json
from xmlrpclib import ServerProxy
import suds
from gl import GlobalLogging as Logging

def trans_web_interface(task_id='', pt_tag=''):
    if not task_id:
        task_id = 22251
    if not pt_tag:
        pt_tag = 'ZDH'
    url = 'http://10.176.65.17:8080/fyauto/services/csglService?wsdl'
    client = suds.client.Client(url)
    service = client.service

    rec_result = service.returnRunningState(task_id, pt_tag)
    print rec_result


def test():
    s = ServerProxy("http://10.176.173.174:16004")
    a = '''[{"cases_id":"347534","cases_name":"验证升级后VIP3客户资金账号权限修改设置成功-1","system_id":"1428912311065GCAO2","adapter_type":"SPLX_KCBP","pre_action":[{"content":"datetime&equ&GetTodayString()","PUBLIC_FUNC_FLAG":0,"type":"General_Operation","desc":"无","call_when":"normal_call"},{"content":"new_extersno1&equ&GeneNewSno(@datetime@,9)","PUBLIC_FUNC_FLAG":0,"type":"General_Operation","desc":"无","call_when":"normal_call"},{"content":"p.exec_sql(delete from run..vip_customers where serverid='@serverid@' and custid='@custid@' and fundid='@fundid@')","PUBLIC_FUNC_FLAG":0,"type":"DB_Operation","desc":"无","call_when":"normal_call"},{"content":"p.exec_sql(INSERT INTO run..vip_customers VALUES ('@serverid@', '@serverid@', '@orgid@', '@custid@', '@fundid@', 'VIP3', '1'))","PUBLIC_FUNC_FLAG":0,"type":"DB_Operation","desc":"无","call_when":"normal_call"}],"pro_action":[{"content":"p.exec_sql(delete from run..vip_customers where serverid='@serverid@' and custid='@custid@' and fundid='@fundid@')","PUBLIC_FUNC_FLAG":0,"type":"DB_Operation","desc":"无","call_when":"normal_call"}],"funcid":"121025","account_group_id":"0","serverid":"9","cmdstring":"billproway=#ctrlkinds=#custid=@custid@#custorgid=@orgid@#doublevideo=#estimated=0#ext=#exterbrhid=3504#exteroperid=14988#extersno=@new_extersno4@#funcid=121025#fundagentright=#fundid=@fundid@#fundlimit=#fundright=#fundtrdflag=0#g_funcid=121025#g_operid=@sys_operid_1@#g_operpwd=@sys_operid_1_pwd@#g_operway=4#g_stationaddr=#netaddr=#noticeway=#operway=01247adefgimycu#orgid=@orgid@#outbizsno=#passflag=#protocolno1=#protocolno2=#protocolver=#trdright=1234567#serverid=@serverid@#g_serverid=@serverid@","param_id":"54014","step_id":"1","step_name":"验证升级后VIP3客户资金账号权限修改设置成功-1","expect_ret":"0","interface_field":{"doublevideo":"HsChar255","estimated":"HsChar255","ext":"HsChar255","exterbrhid":"HsChar255","exteroperid":"HsChar255","extersno":"HsChar255","funcid":"HsChar255","fundagentright":"HsChar255","fundid":"HsNum","fundlimit":"HsChar255","fundright":"HsChar255","fundtrdflag":"HsChar255","g_funcid":"HsChar255","g_operid":"HsChar255","g_operpwd":"HsChar255","g_operway":"HsChar255","g_stationaddr":"HsChar255","netaddr":"HsChar255","noticeway":"HsChar255","operway":"HsChar255","orgid":"HsChar255","outbizsno":"HsChar255","passflag":"HsChar255","protocolno1":"HsChar255","protocolno2":"HsChar255","protocolver":"HsChar255","trdright":"HsChar255","serverid":"HsChar255","g_serverid":"HsChar255","billproway":"HsChar255","ctrlkinds":"HsChar255","custid":"HsChar255","custorgid":"HsChar255"}}]'''

    print s.run_test(a)


if __name__ == '__main__':
    # select * from SX_ACCOUNT_GROUP_INFO where SYSTEM_ID = '1428908551835S0NXP'
    test()

