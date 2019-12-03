# -*- coding:gbk -*-

import httplib, urllib
import gzip, binascii, os
from cStringIO import StringIO


def gzip_uncompress(c_data):
    buf = StringIO(c_data)
    f = gzip.GzipFile(mode='rb', fileobj=buf)
    try:
        r_data = f.read()
    finally:
        f.close()
    return r_data


httpClient = None
try:
    params = urllib.urlencode({
        'id': 'select_stock',
        'app': 'pubs',
        'USER_CODE': '40902',
        'tranCode': 'GT1001',
        'app_version': '8.2.5',
        'ID_TYPE': '6',
        'ID_CODE': '12345678901',
        'SOCKET_PWD': 'fTqA0qfcAXzEW4F4iPzzTTYQTDh%2FActYMZC7zpER7O%2BnD62%2FA0Qpww%2FG8gtXNbdVrC1981mrJ0jboQcq%2BNPeortlZJimAsknrxBbxHaC0OcuWTmighpmB7f1DvS3ZDAD8x3BTNht2LpNGEAOJ0fqyV%2BBVmf%2FJUJWWAoL78%2B0AVU%3D',
        'platfrom': 'android',
        'GROUP_NO': '0'
    })
    # params = 'id=select_stock&app=pubs&USER_CODE=40902&tranCode=GT1001&app_version=8.2.5&ID_TYPE=6&ID_CODE=12345678901&SOCKET_PWD=fTqA0qfcAXzEW4F4iPzzTTYQTDh%2FActYMZC7zpER7O%2BnD62%2FA0Qpww%2FG8gtXNbdVrC1981mrJ0jboQcq%2BNPeortlZJimAsknrxBbxHaC0OcuWTmighpmB7f1DvS3ZDAD8x3BTNht2LpNGEAOJ0fqyV%2BBVmf%2FJUJWWAoL78%2B0AVU%3D&platfrom=android&GROUP_NO=0'
    headers = {
        "X-Emp-Cookie": "_app_id=6485005F7D56098E5877FD875522F9D4,_session_id=ffffffff-8cf2-73ea-4f29-77d30033c590,_anti_id=sf235eaf65UFE1481278026815jkf57dI2UF",
        "Content-type": "application/x-www-form-urlencoded",
        "Content-Length": "334",
        "Host": "114.141.166.25:4002",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/3.3.1",
        "Accept": "text/plain"
    }

    httpClient = httplib.HTTPSConnection("114.141.166.25:4002")
    httpClient.request("POST", "/channel/run", params, headers)

    response = httpClient.getresponse()
    print response.status
    print response.reason
    a = response.read()
    b = gzip_uncompress(a)
    print response.getheaders()  # 获取头信息
except Exception, e:
    print e
finally:
    if httpClient:
        httpClient.close()
