# -*- coding:gbk -*-
import time
import os
import threading
from SimpleXMLRPCServer import SimpleXMLRPCServer


class TestServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.rpcserver = SimpleXMLRPCServer(('0.0.0.0', 5556))
        self.rpcserver.register_function(self.register_client)

        self._rpc_thread = threading.Thread(target=self.rpc_thread)
        self._rpc_thread.start()
        # s.serve_forever()

    def register_client(self, id, ip, port):
        print id, ip, port
        return 0, "end of rpc_thread"

    def rpc_thread(self):
        self.rpcserver.serve_forever()
        print 0, "end of rpc_thread"

    def run(self):
        while True:
            print "i'm here"
            time.sleep(5)


def main():
    server = TestServer()
    server.setDaemon(True)
    server.start()

    while True:
        if server.isAlive() == False:
            break;


if __name__ == "__main__":
    main()
