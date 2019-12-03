# -*- coding:gbk -*-
from spyne import Application, rpc, ServiceBase
from spyne import Integer, Unicode, Array, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server
import sys


class TestAgentServerService(ServiceBase):
    @rpc(Unicode, Unicode, Unicode, _returns=Unicode)
    def register_client(self, id, ip, port):
        print name
        print version
        pass


if __name__ == "__main__":
    soap_app = Application([TestAgentServerService],
                           'SampleServices',
                           in_protocol=Soap11(validator="lxml"),
                           out_protocol=Soap11())
    wsgi_app = WsgiApplication(soap_app)
    server = make_server("0.0.0.0", 15555, wsgi_app)

    sys.exit(server.serve_forever())
