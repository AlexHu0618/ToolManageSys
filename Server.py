# -*- coding: utf-8 -*-
# @Time    : 11/11/19 1:31 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: Server.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.1.0

import socketserver

EQUIPMENTS = {}


class MyTCPHandler(socketserver.BaseRequestHandler):
    """

    """
    clients = {}

    def handle(self):
        self.request.settimeout(5)
        while True:
            try:
                self.request.send(b'hello')
                data = self.request.recv(1024)
                if data != b'':
                    print(self.client_address, 'said: ', data)
                    if data == b'exit':
                        break
                    else:
                        self.request.send(data)
                else:
                    break
            except Exception as e:
                print(e)
                if e == 'timed out':
                    continue
                else:
                    print(self.client_address, "连接断开")

    def setup(self):
        print('new conn: ', self.client_address)
        EQUIPMENTS[self.client_address] = self.request

    def finish(self):
        print("finish run  after handle", self.client_address)
        if self.client_address in EQUIPMENTS.keys():
            EQUIPMENTS.pop(self.client_address)
        print('the remaining clients: ', EQUIPMENTS)


if __name__ == '__main__':
    HOST, PORT = "", 8809
    print('server is starting....')

    server = socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler)  # 多线程版
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print('\nclosed')
        exit()
