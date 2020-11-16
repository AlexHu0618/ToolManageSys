import socket
from app.Object2 import GravityShelf, RfidR2000, Lcd, EntranceGuard
from queue import Queue
from app.myLogger import mylogger
import threading
from operator import methodcaller
from multiprocessing import Process
from app.globalvar import *


class GatewayServer(Process):
    def __init__(self, port: int, server_registered: dict, client_registered: dict, queue_task, queue_rsl):
        super().__init__()
        # {(ip, port): {'thread': thread, 'type': str, 'queuetask': queue, 'queuersl': queue, 'status': True, 'subeven': even, 'data': {}), }
        self.terminal_active = dict()
        self.terminal_inactive = dict()
        self.addr = ('', port)
        self.servers = server_registered
        self.clients = client_registered
        self.isrunning = True
        self.lock = threading.RLock()
        self.queue_task = queue_task
        self.queue_rsl = queue_rsl
        self.queue_equipment_push = Queue(100)
        self.lock_q_equipment_push = threading.RLock()
        self.loop = None

    def run(self):
        ########################
        # 1、主动连接所有已注册服务端；
        # 2、监听等待连接所有已注册客户端；
        # 3、打开注册子线程；
        # 4、打开创建与监测子线程；
        # 5、打开交互接口。
        #######################
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
            # monitor status subthread on time
            t = threading.Timer(interval=5, function=self.time_thread)
            t.daemon = True
            t.start()
            # wait for cmd
            while True:
                with self.lock:
                    status = self.isrunning
                if status:
                    self._handle_cmd()
                else:
                    self.loop.close()
                    break
        except Exception as e:
            print('gateway_server: ', e)
            mylogger.error(e)

    def time_thread(self):
        # 定时循环执行线程
        msg = self.check_push_from_equipments()
        if msg:
            pkg = TransferPackage(source=msg['addr'], msg_type=2, data=msg['data'], code=206, eq_type=1)
            self.queue_rsl.put(pkg)
        self.check_equipments_status()
        t = threading.Timer(interval=5, function=self.time_thread)
        t.daemon = True
        t.start()

    def check_equipments_status(self):
        t_status = {}
        with self.lock:
            for k, v in self.terminal_active.items():
                if v['thread'].isAlive():
                    print(k, 'is online')
                else:
                    self.terminal_active[k]['status'] = False
                    print(k, 'is offline')

    def check_push_from_equipments(self):
        if not self.queue_equipment_push.empty():
            with self.lock_q_equipment_push:
                data = self.queue_equipment_push.get()
                print(data)
        else:
            print('no equipment push data update')
            data = None
        return data

    def _connect_server(self, addr: tuple, ttype: str):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        failed_count = 0
        terminal_type = ttype
        queue_task = Queue(50)
        queue_rsl = Queue(50)
        subevent = threading.Event()
        thread = None
        while True:
            try:
                if terminal_type == 'guard':
                    thread = EntranceGuard(addr, queue_task, queue_rsl, self.queue_equipment_push, self.lock_q_equipment_push)
                else:
                    s.connect(addr)
                    if terminal_type == 'G':
                        thread = GravityShelf(addr, s, queue_task, queue_rsl, subevent, self.queue_equipment_push, self.lock_q_equipment_push)
                    elif terminal_type == 'L':
                        thread = Lcd(addr, s, queue_task, queue_rsl, subevent)
                    elif terminal_type == 'R':
                        thread = RfidR2000(addr, s, queue_task, queue_rsl, subevent, self.queue_equipment_push, self.lock_q_equipment_push)
                    else:
                        pass
                if thread:
                    thread.daemon = True
                    thread.start()
                    self.lock.acquire()
                    self.terminal_active[addr] = {'thread': thread, 'type': terminal_type, 'queuetask': queue_task,
                                                  'queuersl': queue_rsl, 'status': True, 'subevent': subevent, 'data': {}}
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
                subevent = threading.Event()
                thread = None
                client_type = self.clients[addr] if addr in self.clients.keys() else None
                if client_type == 'G':
                    thread = GravityShelf(addr, client_sock, queue_task, queue_rsl, subevent, self.queue_equipment_push, self.lock_q_equipment_push)
                elif client_type == 'L':
                    thread = Lcd(addr, client_sock, queue_task, queue_rsl, subevent)
                elif client_type == 'R':
                    thread = RfidR2000(addr, client_sock, queue_task, queue_rsl, subevent, self.queue_equipment_push, self.lock_q_equipment_push)
                else:
                    pass
                if thread:
                    thread.daemon = True
                    thread.start()
                    self.lock.acquire()
                    self.terminal_active[addr] = {'thread': thread, 'type': client_type, 'queuetask': queue_task,
                                                  'queuersl': queue_rsl, 'status': True, 'subevent': subevent, 'data': {}}
                    self.lock.release()
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
                # get transfer package type 'TransferPackage' from queue
                transfer_package = self.queue_task.get()
                target = transfer_package.target
                task = transfer_package.data['func']
                args = transfer_package.data['args']
                print('\033[1;33m', task, ' ', args, '\033[0m')
                # cmd for the equipment running async
                if target is not None:
                    thd = threading.Thread(target=self._get_data_from_equipment, args=(transfer_package,))
                    thd.setDaemon(True)
                    thd.start()
                # cmd for gateway server
                else:
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        self.queue_rsl.put(rsl)
            else:
                pass
        except Exception as e:
            mylogger.error(e)

    def _get_data_from_equipment(self, transfer_package):
        # 异步访问硬件
        target = transfer_package.target
        task = transfer_package.data['func']
        args = transfer_package.data['args']
        # get the queue of equipment
        self.lock.acquire()
        qt = self.terminal_active[target]['queuetask']
        qr = self.terminal_active[target]['queuersl']
        subevent = self.terminal_active[target]['subevent']
        self.lock.release()
        subevent.clear()
        qt.put((task, args))
        subevent.wait()
        if not qr.empty():
            data = qr.get()
            transfer_package.data['rsl'] = data
            transfer_package.code = 200
            self.queue_rsl.put(transfer_package)
        else:
            transfer_package.code = 202
            self.queue_rsl.put(transfer_package)
            print(target, ' qr is empty!')

    def stop(self):
        self.lock.acquire()
        self.isrunning = False
        self.lock.release()
