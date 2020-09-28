# concurrent.futures实现进程池和线程池

from concurrent.futures import ThreadPoolExecutor
import time
import threading
import socket
import select
from myLogger import mylogger

CLIENTS = {}


class Equip:
    def __init__(self, ip: str, port: int, etype: int):
        self.ip = ip
        self.port = port
        self.etype = etype   # 0-G; 1-R2000; 2-
        self.socket = None
        self.status = 1  # 1-online; 0-offline


def connClient(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    failed_count = 0
    while True:
        try:
            print("start connect to server ")
            s.connect((ip, port))
            CLIENTS[str(ip) + ':' + str(port)] = s
            print('success to conn client == ', ip, ':', port)
            print(CLIENTS)
            break
        except socket.error:
            failed_count += 1
            print("fail to connect to server %d times" % failed_count)
            if failed_count == 10:
                print('Fail to connect Client ==', ip, ':', port)
                mylogger.error('Fail conn, ' + ip + ':' + port)
                return


def checkAndRecv(r: socket):
    thid = threading.currentThread().ident
    print('id: ', thid)
    data_bytes = r.recv(1024)
    print(r.raddr)
    data_str = str(data_bytes, encoding='utf-8')
    print('received Msg: ', data_str)


def sendMsg(msg: bytes):
    for k, v in CLIENTS.items():
        v.send(msg)
        print('sent MSG to ', k)


def main():
    with ThreadPoolExecutor() as executor:
        try:
            inputs = CLIENTS.values()
            print(inputs)
            outputs = []
            while True:
                time.sleep(1)
                sendMsg(b'hello')
                r_list, w_list, e_list = select.select(inputs, outputs, inputs, 1)
                if r_list:
                    for r in r_list:
                        executor.submit(checkAndRecv, r)
                        print('new thread')
        except Exception as e:
            print(e)


def conn2equipment():
    clients = [('192.168.8.127', 23), ('192.168.8.127', 26)]
    for c in clients:
        connClient(c[0], c[1])


# class Connector:
#     def checkNewEquip(self):
#         pass
#
#     def run(self):
#         pass
#
#
# class Transmitter:
#     pass
#
#
# class Receiver:
#     pass


if __name__ == '__main__':
    mylogger.info('Start PullServer')
    conn2equipment()
    mylogger.info('Success conn, ' + '---'.join(CLIENTS))
    main()
