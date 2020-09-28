from concurrent.futures import ThreadPoolExecutor
import time
import threading
import socket
import select
from myLogger import mylogger
from queue import Queue
from Object import *


class PullServer:
    """
        1、根据注册列表创建tcp线程与设备实例，放入线程列表；
        2、通过接收线程池与发送线程池操作线程列表；
    """
    def __init__(self):
        self.equipments = {}
        self.equipments_fail = []
        self.inputs = []
        self.is_running = False
        self.queue_send = Queue(maxsize=5)

    def _build_equipment_list(self):
        pass

    def run(self):
        equipments_info = [('192.168.8.127', 23, 'GravityShelf'), ('192.168.8.127', 26, 'RfidR2000')]
        self._conn_equipment(equipments_info=equipments_info)
        self.is_running = True
        t1 = threading.Thread(target=self._loop_recv)
        t2 = threading.Thread(target=self._loop_send)
        t1.start()
        t2.start()
        # self._loop_recv()
        # self._loop_send()

    def _conn_equipment(self, equipments_info: list):
        ###############################
        # connecte to all registered equipment
        ###############################
        for e in equipments_info:
            print('e is: ', e[:2])
            socket_created = self._create_socket(e[:2])
            if socket_created:
                equipment = eval(e[2])(socket_created)
                self.equipments[e[:2]] = equipment
                self.inputs.append(socket_created)
            else:
                self.equipments_fail.append(e)

    def _create_socket(self, addr: tuple):
        ##############################
        # create every socket connected to equipment
        ##############################
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)

        failed_count = 0
        while True:
            try:
                s.connect(addr)
                print('success to conn client: ', addr)
                break
            except socket.error:
                failed_count += 1
                print("fail to connect to server %d times" % failed_count)
                if failed_count == 10:
                    print('Fail to connect Client: ', addr)
                    mylogger.error('Fail conn to: ' + str(addr))
                    return None
        return s

    def _loop_recv(self):
        with ThreadPoolExecutor() as executor:
            try:
                while self.is_running:
                    inputs = self.inputs
                    outputs = []
                    r_list, w_list, e_list = select.select(inputs, outputs, inputs, 1)
                    if r_list:
                        for r in r_list:
                            executor.submit(self._handle_recv, r)
            except Exception as e:
                print(e)

    def _handle_recv(self, s):
        thid = threading.currentThread().ident
        data_bytes = s.recv(1024)
        if data_bytes == b'':
            del self.equipments[s.getpeername()]
        else:
            data_str = str(data_bytes, encoding='utf-8')
            print('thread %s received Msg: %s' % (thid, data_str))
            self.queue_send.put((s, data_bytes))

    def _loop_send(self):
        with ThreadPoolExecutor() as executor:
            try:
                while self.is_running:
                    time.sleep(1)
                    if not self.queue_send.empty():
                        rsl = self.queue_send.get()
                        executor.submit(self._handle_send, rsl[0], rsl[1])
                        self.queue_send.task_done()
            except Exception as e:
                print(e)

    def _handle_send(self, s, data):
        s.send(data)
        print('sent msg to ', s.getpeername())

    def close(self):
        self.is_running = False

    def send(self, addr: tuple):



#
#
#
#
#
# CLIENTS = {}
#
#
# class Equip:
#     def __init__(self, ip: str, port: int, etype: int):
#         self.ip = ip
#         self.port = port
#         self.etype = etype   # 0-G; 1-R2000; 2-
#         self.socket = None
#         self.status = 1  # 1-online; 0-offline
#
#
# def connClient(ip, port):
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#
#     failed_count = 0
#     while True:
#         try:
#             print("start connect to server ")
#             s.connect((ip, port))
#             CLIENTS[str(ip) + ':' + str(port)] = s
#             print('success to conn client == ', ip, ':', port)
#             print(CLIENTS)
#             break
#         except socket.error:
#             failed_count += 1
#             print("fail to connect to server %d times" % failed_count)
#             if failed_count == 10:
#                 print('Fail to connect Client ==', ip, ':', port)
#                 mylogger.error('Fail conn, ' + ip + ':' + port)
#                 return
#
#
# def checkAndRecv(r: socket):
#     thid = threading.currentThread().ident
#     print('id: ', thid)
#     data_bytes = r.recv(1024)
#     print(r.raddr)
#     data_str = str(data_bytes, encoding='utf-8')
#     print('received Msg: ', data_str)
#
#
# def sendMsg(msg: bytes):
#     for k, v in CLIENTS.items():
#         v.send(msg)
#         print('sent MSG to ', k)
#
#
# def main():
#     with ThreadPoolExecutor() as executor:
#         try:
#             inputs = CLIENTS.values()
#             print(inputs)
#             outputs = []
#             while True:
#                 time.sleep(1)
#                 sendMsg(b'hello')
#                 r_list, w_list, e_list = select.select(inputs, outputs, inputs, 1)
#                 if r_list:
#                     for r in r_list:
#                         executor.submit(checkAndRecv, r)
#                         print('new thread')
#         except Exception as e:
#             print(e)
#
#
# def conn2equipment():
#     clients = [('192.168.8.127', 23), ('192.168.8.127', 26)]
#     for c in clients:
#         connClient(c[0], c[1])
#
