# -*- coding:gbk -*-

from suds.client import Client

try:
    client = Client("http://127.0.0.1:15555/?wsdl")
    ret = client.service.make_project("Test", "1.0.0")
except BaseException, ex:
    print ex
