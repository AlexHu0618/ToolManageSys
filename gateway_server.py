import socket
from Object2 import GravityShelf, RfidR2000, Lcd, EntranceGuard
from queue import Queue
from myLogger import mylogger
import threading
import time
from operator import methodcaller


class GatewayServer(object):
    def __init__(self, port: int, server_registered: dict, client_registered: dict, queue_task, queue_rsl):
        # {(ip, port): (thread, queuetask, queuersl, status), }
        self.terminal_active = dict()
        self.addr = ('', port)
        self.servers = server_registered
        self.clients = client_registered
        self.isrunning = True
        self.lock = threading.RLock()
        self.queue_task = queue_task
        self.queue_rsl = queue_rsl

    def start(self):
        try:
            # connect all servers
            if self.servers is not None:
                print("Start to connect to registered servers!!!!")
                for k, v in self.servers.items():
                    self._connect_server(addr=k, ttype=v)
            else:
                mylogger.info('There is None registered server for connecting!')
            # listen all access clients
            thread_monitor = threading.Thread(target=self._monitor_access)
            thread_monitor.daemon = True
            thread_monitor.start()
            # thread_getcmd = threading.Thread(target=self._getcmd)
            # thread_getcmd.daemon = True
            # thread_getcmd.start()
            while True:
                self.lock.acquire()
                status = self.isrunning
                self.lock.release()
                if status:
                    self._handle_cmd()
                    time.sleep(5)
                else:
                    break
        except Exception as e:
            print('gateway_server: ', e)
            mylogger.error(e)

    def _connect_server(self, addr: tuple, ttype: str):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        failed_count = 0
        terminal_type = ttype
        queue_task = Queue(50)
        queue_rsl = Queue(50)
        thread = None
        while True:
            try:
                if terminal_type == 'guard':
                    thread = EntranceGuard(addr, queue_task, queue_rsl)
                else:
                    s.connect(addr)
                    if terminal_type == 'G':
                        thread = GravityShelf(s, queue_task, queue_rsl)
                    elif terminal_type == 'L':
                        thread = Lcd(s, queue_task, queue_rsl)
                    elif terminal_type == 'R':
                        thread = RfidR2000(s, queue_task, queue_rsl)
                    else:
                        pass
                if thread:
                    thread.daemon = True
                    thread.start()
                    self.lock.acquire()
                    self.terminal_active[addr] = (thread, queue_task, queue_rsl, terminal_type)
                    self.lock.release()
                    print('客户端(%s)已成功连接。。' % str(addr))
                    mylogger.info('客户端(%s)已成功连接。。' % str(addr))
                    return True
            except socket.error:
                failed_count += 1
                # print("fail to connect to server %d times" % failed_count)
                if failed_count == 10:
                    print('fail to connect to server %s' % str(addr))
                    mylogger.warning('fail to connect to server %s' % str(addr))
                    return False

    def _monitor_access(self):
        # 创建socket对象
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(self.addr)
        # 监听请求
        server_sock.listen()
        # 建立长连接
        try:
            print('--等待客户端连接本服务器8809！--')
            while self.isrunning:
                client_sock, addr = server_sock.accept()

                # 每循环一次就会产生一个线程
                queue_task = Queue(50)
                queue_rsl = Queue(50)
                thread = None
                client_type = self.clients[addr] if addr in self.clients.keys() else None
                if client_type == 'G':
                    thread = GravityShelf(client_sock, queue_task, queue_rsl)
                elif client_type == 'L':
                    thread = Lcd(client_sock, queue_task, queue_rsl)
                elif client_type == 'R':
                    thread = RfidR2000(client_sock, queue_task, queue_rsl)
                else:
                    pass
                if thread:
                    thread.daemon = True
                    thread.start()
                    self.terminal_active[addr] = (thread, queue_task, queue_rsl, client_type)
                    mylogger.info('客户端(%s)已成功连接。。' % str(addr))
                    print('客户端(%s)已成功连接。。' % str(addr))
        finally:
            server_sock.close()

    def add_new(self, ip: str, port: int, type_new: str, isserver: bool):
        addr = (ip, port)
        if isserver:
            rsl = self._connect_server(addr=addr, ttype=type_new)
            if rsl:
                return True
            else:
                return False
        else:
            try:
                self.lock.acquire()
                self.clients[addr] = type_new
                self.lock.release()
                return True
            except Exception as e:
                mylogger.error(e)
                return False

    def _handle_cmd(self):
        try:
            if not self.queue_task.empty():
                task, args = self.queue_task.get()
                rsl = methodcaller(task, *args)(self)
                if rsl is not None:
                    self.queue_rsl.put(rsl)
            else:
                pass
            # for (k, v) in self.terminal_active.items():
            #     qt = v[1]
            #     qr = v[2]
            #     if v[3] == 'G':
            #         # qt.put('readAllInfo')
            #         qt.put(('readWeight', ('0a',)))
            #         print('send cmd to ', k)
            #     elif v[3] == 'R':
            #         qt.put(('getOutputPower', ()))
            #         print('send cmd to ', k)
            #     elif v[3] == 'L':
            #         qt.put(('onLed', (True,)))
            #         print('send cmd to ', k)
            #     elif v[3] == 'guard':
            #         qt.put(('getDeviceParam', ()))
            #         print('send cmd to ', k)
            #     else:
            #         pass
            #     if not qr.empty():
            #         data = qr.get()
            #         print(k, ' back data: ', data)
            #         if data == 'timeout':
            #             print(k, ' timeout')
            #     else:
            #         print(k, ' qr is empty!')
        except Exception as e:
            mylogger.error(e)

    def stop(self):
        self.lock.acquire()
        self.isrunning = False
        self.lock.release()
