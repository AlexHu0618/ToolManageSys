import socket
from app.Object2 import GravityShelf, RfidR2000, Indicator, EntranceZK, RfidR2000FH, HKVision, ChannelMachineR2000FH
# from app.object_test import GravityShelf, RfidR2000, Indicator, EntranceZK
from queue import Queue
from app.myLogger import mylogger
import threading
from operator import methodcaller
from multiprocessing import Process
from app.globalvar import *
import time
from database.models2 import Entrance, Collector, Indicator, CodeScanner, ChannelMachine
import datetime


class GatewayServer(Process):
    """
    1、所有的TCP设备终端应该按库房进行分类管理；
    2、设备的类型包括：['entrance_zk', 'entrance_hk', 'code_scane', 'channel_machine', 'led', 'gravity', 'rfid2000', 'rfid2000fh']
    """
    def __init__(self, port: int, servers_registered: dict, clients_registered: dict, queue_task, queue_rsl):
        super().__init__()
        # {(ip, port): {'thread': thread, 'type': str, 'queuetask': queue, 'queuersl': queue, 'status': True, 'subeven': even, 'data': {}, 'is_server': True), }
        self.terminal_active = dict()
        # {(ip, port): 'type'}
        self.server_active = dict()
        self.client_active = dict()
        self.addr = ('', port)
        self.servers = servers_registered
        self.clients = clients_registered
        self.isrunning = True
        self.lock = threading.RLock()
        self.queue_task = queue_task
        self.queue_rsl = queue_rsl
        self.queue_equipment_push = Queue(100)

    def run(self):
        """
        1、主动连接所有已注册服务端；
        2、监听等待连接所有已注册客户端；
        3、打开注册子线程；
        4、打开创建与监测子线程；
        5、打开交互接口。
        :return:
        """
        try:
            # connect all servers
            if self.servers is not None:
                print("Start to connect to registered servers!!!!")
                for k, v in self.servers.items():
                    self._connect_server(addr=k, ttype=v[0], storeroom_id=v[1], uuid=v[2])
            else:
                mylogger.info('There is None registered server for connecting!')
            # monitor and reconn servers
            thread_reconn_server = threading.Thread(target=self._reconnect_offline_server)
            thread_reconn_server.daemon = True
            thread_reconn_server.start()
            # listen all access clients
            thread_monitor_client = threading.Thread(target=self._monitor_access)
            thread_monitor_client.daemon = True
            thread_monitor_client.start()
            # monitor status subthread on time
            t = threading.Timer(interval=1, function=self.time_thread)
            t.daemon = True
            t.start()
            # wait for cmd
            while True:
                with self.lock:
                    status = self.isrunning
                if status:
                    self._handle_cmd()
                else:
                    break
            mylogger.error('gateway_server was stop')
        except Exception as e:
            print('gateway_server was stop: ', e)
            mylogger.error('gateway_server was stop by exception:' + e)

    def time_thread(self):
        """
        定时循环执行线程
        1、检查设备状态；
        2、检查获取设备pkg并推送到task控制器；
        :return:
        """
        self.check_equipments_status()
        self.check_push_from_equipments()
        t = threading.Timer(interval=1, function=self.time_thread)
        t.daemon = True
        t.start()

    def check_equipments_status(self):
        """
        如果线程为None，表示连接已断开, 则删除相应激活字典中键值对。
        :return:
        """
        with self.lock:
            for k, v in self.terminal_active.copy().items():
                if not v['thread'].isAlive():
                    pkg = TransferPackage(source=k, msg_type=2, code=EQUIPMENT_OFFLINE)
                    self.queue_rsl.put(pkg)
                    if v['is_server']:
                        del self.server_active[k]
                    else:
                        del self.client_active[k]
                    del self.terminal_active[k]
                    mylogger.warning('equipment (%s, %d) is offline' % k)
                    self._modify_db_eq_status(eq_type=v['type'], addr=k, is_online=False)

    def check_push_from_equipments(self):
        """
        查询是否有设备推送信息
        :return:
        """
        print('size of push queue--', self.queue_equipment_push.qsize())
        if not self.queue_equipment_push.empty():
            pkg = self.queue_equipment_push.get()
            print('got push data--', pkg)
            self.queue_rsl.put(pkg)
        else:
            # print('no equipment push data update')
            pkg = None
        return pkg

    def _reconnect_offline_server(self):
        """
        定时检查是否有断开的server连接，有则重新连接
        :return:
        """
        while self.isrunning:
            self.lock.acquire()
            server_offline = dict(set(self.servers.items()) - set(self.server_active.items()))
            self.lock.release()
            if server_offline is not None:
                print("Start to reconnect to offline servers!!!!")
                for k, v in server_offline.items():
                    self._connect_server(addr=k, ttype=v[0], storeroom_id=v[1], uuid=v[2])
            time.sleep(20)

    def _connect_server(self, addr: tuple, ttype: str, storeroom_id: str, uuid: str):
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
                if terminal_type == 'entrance_zk':
                    thread = EntranceZK(addr, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid)
                elif terminal_type == 'entrance_hk':
                    thread = HKVision(addr, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid)
                else:
                    s.connect(addr)
                    if terminal_type == 'gravity':
                        gravity = Collector.by_addr(addr[0], addr[1])
                        if gravity:
                            addr_nums = gravity.node_addrs.replace(' ', '').split(',')
                        thread = GravityShelf(addr, s, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid, addr_nums)
                    elif terminal_type == 'led':
                        thread = Indicator(addr, s, queue_task, queue_rsl, subevent, storeroom_id, uuid)
                    elif terminal_type == 'rfid2000':
                        thread = RfidR2000(addr, s, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid)
                    elif terminal_type == 'rfid2000fh':
                        r2000fh = Collector.by_addr(addr[0], addr[1])
                        addr_nums = ['01']
                        if r2000fh:
                            addr_nums = r2000fh.node_addrs.replace(' ', '').split(',')
                        thread = RfidR2000FH(addr, s, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid, addr_nums)
                    elif terminal_type == 'channel_machine':
                        r2000fh = Collector.by_addr(addr[0], addr[1])
                        addr_nums = ['01']
                        if r2000fh:
                            addr_nums = r2000fh.node_addrs.replace(' ', '').split(',')
                        thread = ChannelMachineR2000FH(addr, s, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid, addr_nums)
                    else:
                        pass
                if thread:
                    thread.setDaemon(True)
                    thread.start()
                    self.lock.acquire()
                    self.terminal_active[addr] = {'thread': thread, 'type': terminal_type, 'queuetask': queue_task,
                                                  'queuersl': queue_rsl, 'status': False, 'subevent': subevent,
                                                  'data': {}, 'is_server': True}
                    self.server_active[addr] = (terminal_type, storeroom_id, uuid)
                    self.lock.release()
                    print('服务端(%s)已成功连接。。' % str(addr))
                    mylogger.info('服务端(%s)已成功连接。。online' % str(addr))
                    self._modify_db_eq_status(eq_type=terminal_type, addr=addr, is_online=True)
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
                client_type = self.clients[addr][0] if addr in self.clients.keys() else None
                storeroom_id = self.clients[addr][1] if addr in self.clients.keys() else None
                uuid = self.clients[addr][2] if addr in self.clients.keys() else None
                if client_type == 'gravity':
                    gravity = Collector.by_addr(addr[0], addr[1])
                    if gravity:
                        addr_nums = gravity.node_addrs.replace(' ', '').split(',')
                    thread = GravityShelf(addr, client_sock, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid, addr_nums)
                elif client_type == 'led':
                    indicator = Indicator.by_addr(addr[0], addr[1])
                    if indicator:
                        addr_nums = indicator.node_addrs.replace(' ', '').split(',')
                    thread = Indicator(addr, client_sock, queue_task, queue_rsl, subevent, storeroom_id, uuid, addr_nums)
                elif client_type == 'rfid2000':
                    thread = RfidR2000(addr, client_sock, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid)
                elif client_type == 'rfid2000fh':
                    r2000fh = Collector.by_addr(addr[0], addr[1])
                    addr_nums = ['01']
                    if r2000fh:
                        addr_nums = r2000fh.node_addrs.replace(' ', '').split(',')
                    thread = RfidR2000FH(addr, client_sock, queue_task, queue_rsl, subevent, self.queue_equipment_push, storeroom_id, uuid, addr_nums)
                elif client_type == 'channel_machine':
                    r2000fh = Collector.by_addr(addr[0], addr[1])
                    addr_nums = ['01']
                    if r2000fh:
                        addr_nums = r2000fh.node_addrs.replace(' ', '').split(',')
                    thread = ChannelMachineR2000FH(addr, client_sock, queue_task, queue_rsl, subevent, self.queue_equipment_push,
                                                   storeroom_id, uuid, addr_nums)
                else:
                    pass
                if thread:
                    thread.daemon = True
                    thread.start()
                    self.lock.acquire()
                    self.terminal_active[addr] = {'thread': thread, 'type': client_type, 'queuetask': queue_task,
                                                  'queuersl': queue_rsl, 'status': True, 'subevent': subevent,
                                                  'data': {}, 'is_server': False}
                    self.client_active[addr] = client_type
                    self.lock.release()
                    mylogger.info('客户端(%s)已成功连接。。online' % str(addr))
                    self._modify_db_eq_status(eq_type=client_type, addr=addr, is_online=True)
                    print('客户端(%s)已成功连接。。' % str(addr))
                else:
                    mylogger.info('客户端(%s)连接创建线程失败。。' % str(addr))
                    print('客户端(%s)连接创建线程失败。。' % str(addr))
        finally:
            server_sock.close()

    def add_new_equipment(self, ip: str, port: int, type_new: str, isserver: bool, storeroom_id: str, uuid: str):
        """
        1、加入设备服务器列表或设备客户端列表；
        2、尝试连接设备；
        :param ip:
        :param port:
        :param type_new:
        :param isserver:
        :return:
        """
        addr = (ip, port)
        try:
            if isserver:
                self.lock.acquire()
                self.servers[addr] = (type_new, storeroom_id, uuid)
                self.lock.release()
                self._connect_server(addr=addr, ttype=type_new, storeroom_id=storeroom_id, uuid=uuid)
                if addr in self.server_active.keys():
                    return True
                else:
                    return False
            else:
                self.lock.acquire()
                self.clients[addr] = (type_new, storeroom_id, uuid)
                self.lock.release()
                time.sleep(1)
                if addr in self.client_active:
                    return True
                else:
                    return False
        except Exception as e:
            print(e)
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
                print('\033[1;33m CMD: ', task, ' ', args, '\033[0m')
                # cmd for the equipment running async
                if transfer_package.msg_type == 0:
                    thd = threading.Thread(target=self._operate_equipment, args=(transfer_package,))
                    thd.setDaemon(True)
                    thd.start()
                # cmd for gateway server
                elif transfer_package.msg_type == 1:
                    rsl = methodcaller(task, *args)(self)
                    if rsl is True:
                        transfer_package.code = SUCCESS
                        transfer_package.msg_type = 4
                    else:
                        transfer_package.code = ERR_EQUIPMENT_RESP
                        transfer_package.msg_type = 4
                    self.queue_rsl.put(transfer_package)
                else:
                    pass
            else:
                pass
        except Exception as e:
            print('excetp', e)
            mylogger.error(e)

    def _operate_equipment(self, transfer_package):
        """
        异步访问硬件
        :param transfer_package:
        :return:
        """
        try:
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
                pkg = qr.get()
                self.queue_rsl.put(pkg)
            else:
                print(target, ' qr is empty!')
        except Exception as e:
            print('except------', e)
            mylogger.error(e)

    def stop(self):
        self.lock.acquire()
        self.isrunning = False
        self.lock.release()

    def _modify_db_eq_status(self, eq_type: str, addr: tuple, is_online: bool):
        """
        设备的类型包括：['entrance_zk', 'code_scane', 'channel_machine', 'led', 'gravity', 'rfid2000', 'rfid2000fh']
        :param eq_type:
        :return:
        """
        try:
            if eq_type == 'entrance_zk' or eq_type == 'entrance_hk':
                entrance = Entrance.by_addr(ip=addr[0], port=addr[1])
                if entrance is not None:
                    entrance.update('status', int(is_online))
                    if not is_online:
                        cur_dt = str(datetime.datetime.now())
                        entrance.update('last_offline_time', cur_dt)
                else:
                    mylogger.warning('Not found object(%s,%d) from DB-entrance while updating' % addr)
            elif eq_type in ['gravity', 'rfid2000', 'rfid2000fh']:
                collector = Collector.by_addr(ip=addr[0], port=addr[1])
                if collector is not None:
                    collector.update('status', int(is_online))
                    # shelf = collector.shelf
                    # map(lambda grid: grid.update('status', int(is_online)), shelf.grids)
                    if not is_online:
                        cur_dt = str(datetime.datetime.now())
                        collector.update('last_offline_time', cur_dt)
                else:
                    mylogger.warning('Not found object(%s,%d) from DB-collector while updating' % addr)
            elif eq_type == 'led':
                indicator = Indicator.by_addr(ip=addr[0], port=addr[1])
                if indicator is not None:
                    indicator.update('status', int(is_online))
                    if not is_online:
                        cur_dt = str(datetime.datetime.now())
                        indicator.update('last_offline_time', cur_dt)
                else:
                    mylogger.warning('Not found object(%s,%d) from DB-indicator while updating' % addr)
            elif eq_type == 'channel_machine':
                cm = ChannelMachine.by_addr(ip=addr[0], port=addr[1])
                if cm is not None:
                    cm.update('status', int(is_online))
                    if not is_online:
                        cur_dt = str(datetime.datetime.now())
                        cm.update('last_offline_time', cur_dt)
                else:
                    mylogger.warning('Not found object(%s,%d) from DB-indicator while updating' % addr)
            else:
                pass
            print('\033[1;33m', str(addr), 'is online' if is_online else 'is offline', '\033[0m')
        except Exception as e:
            print('_modify_db_eq_status', e)
