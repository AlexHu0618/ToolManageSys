from multiprocessing import Process, Queue
import threading
import socket
import time
from .globalvar import *
import struct
from app.myLogger import mylogger
from database.models2 import Entrance, User, Grid, History_inbound_outbound, Goods, ChannelMachine, Toolkit, Indicator
import sys
import datetime
from settings.config import config_parser as conpar
import json
from playsound import playsound
import os


class TaskControler(Process):
    def __init__(self, queue_task, queue_rsl):
        super().__init__()
        self.sock = None
        self.q_task = queue_task  # 从web接收的数据包队列
        self.q_rsl = queue_rsl  # 发送到web的数据包队列
        self.isrunning = True
        self.storeroom_thread = dict()  # {'storeroom_id': {'thread': thread, 'queue': queue}, }
        self.lock_storeroom_user = threading.RLock()
        self.web_pkg_counter = 0
        self.server_sock = None

    def run(self):
        try:
            print('PID--task_controler:', os.getpid())
            mylogger.info('PID--task_controler: %d' % os.getpid())
            thread_conn = threading.Thread(target=self._monitorconn)
            thread_send = threading.Thread(target=self._get_push_data)
            thread_conn.daemon = True
            thread_send.daemon = True
            thread_conn.start()
            thread_send.start()
            print('start task')
            thread_conn.join()
            print('stop task controler')
            mylogger.error('task controler was stop')
        except KeyboardInterrupt:
            # while self.sock is not None:
            #     print(self.server_sock)
            #     self.server_sock.shutdown(socket.SHUT_RDWR)
            #     self.server_sock.close()
            #     time.sleep(2)
                print('self.sock', self.sock)
        except Exception as e:
            print('task_controler was stop by exception: ', e)
            mylogger.error('task_controler was stop by exception:' + e)
        print('\033[1;33m', 'task_controler was stop', '\033[0m')
        mylogger.error('task_controler was stop')

    def _monitorconn(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        addr = ('', 9999)
        server_sock.bind(addr)
        server_sock.listen(1)
        self.server_sock = server_sock
        while self.isrunning:
            try:
                while True:
                    print('waitting for new web connection')
                    client_sock, addr = server_sock.accept()
                    self.sock = client_sock
                    print('new conn: ', addr)
                    break
                while True:
                    # length_data = client_sock.recv(1024)
                    length_data = client_sock.recv(4)
                    if length_data == b'exit':
                        break
                    elif len(length_data) == 0:
                        print('client: ', addr, ' was offline')
                        raise BrokenPipeError
                    else:
                        # self.puttask(data=length_data)
                        length = struct.unpack('i', length_data)[0]
                        data = client_sock.recv(length)
                        print(time.asctime(), 'recv: ', data)
                        # 接收的data为bytes类型的json数据，其中的None会自动换成null，需要注意，此刻如果使用eval（）转换会报错“null not defined”
                        # data_dict = eval(str(data, encoding='utf-8'))
                        data_dict = json.loads(data.decode().strip())
                        print('\033[1;34m', 'recv from web pkg--', data_dict, '\033[0m')
                        mylogger.info('recv web pkg--%s' % str(data, encoding='utf-8'))
                        self._analyze_web_pkg(data_dict)
            except (OSError, BrokenPipeError):
                continue
            except KeyboardInterrupt:
                print('monitor keyboard')
                break
        self.sock.send(b'exit')
        server_sock.shutdown()
        server_sock.close()
        print('\033[1;34m', 'tcp server shutdown', '\033[0m')

    def _analyze_web_pkg(self, package: dict):
        """
        1、gateway_server与设备的控制指令，不经过处理直接放入队列下发；
        2、其他指令进行包分析处理；
        :param package:
        :return:
        """
        if package['msg_type'] == 0 or package['msg_type'] == 1:
            mylogger.info('get pkg from webserver')
            self.puttask(package)
        else:
            self._analyze_pkg(package=package)

    def puttask(self, json_data):
        """
        1、发送gataway_server和设备相关的pkg到gataway_server；
        :param data: 
        :return: 
        """
        # package to transferpackage and put into task queue
        # cmds = data.split(b'\r\n')
        # if len(cmds) > 2:
        #     # 属于传感器的指令
        #     target = eval(cmds[0])
        #     tp = TransferPackage(target=target)
        #     tp.data['func'] = str(cmds[1], encoding='utf8')
        #     tp.data['args'] = eval(cmds[2])
        #     tp.uuid = str(cmds[3], encoding='utf8')
        # else:
        #     # 属于网关服务器的指令
        #     tp = TransferPackage()
        #     tp.data['func'] = str(cmds[0], encoding='utf8')
        #     tp.data['args'] = eval(cmds[1])
        #     tp.uuid = str(cmds[2], encoding='utf8')
        # self.q_task.put(tp)
        try:
            all_type = {1: 'entrance_zk', 2: 'entrance_hk', 3: 'code_scan', 4: 'gravity', 5: 'rfid2000',
                        6: 'rfid2000fh', 7: 'channel_machine', 8: 'led'}
            # pkg = eval(str(data, encoding='utf-8'))
            pkg = TransferPackage()
            pkg.uuid = json_data['uuid'] if 'uuid' in json_data.keys() else None
            pkg.target = json_data['target'] if 'target' in json_data.keys() else None
            pkg.source = json_data['source'] if 'source' in json_data.keys() else None
            pkg.code = json_data['code'] if 'code' in json_data.keys() else None
            pkg.msg_type = json_data['msg_type'] if 'msg_type' in json_data.keys() else None
            pkg.storeroom_id = json_data['storeroom_id'] if 'storeroom_id' in json_data.keys() else None
            if pkg.code == ENTRANCE_ADD_USER:
                eq_id = json_data['equipment_id'] if 'equipment_id' in json_data.keys() else None
                user_id = json_data['data']['user_id']
                user = User.by_uuid(user_id)
                entrance = Entrance.by_id(eq_id)
                func = 'add_new_user'
                args = (user.code, user.fingerprint, user.login_name, user.card_id)
                if entrance.type == 2:  # 1-ZK; 2-HK;
                    func = 'build_new_user_to_terminal'
                    args = (user_id, )
                pkg.data = {'func': func, 'args': args}
            elif pkg.code == ENTRANCE_REDUCE_USER:
                eq_id = json_data['equipment_id'] if 'equipment_id' in json_data.keys() else None
                user_id = json_data['data']['user_id']
                user = User.by_uuid(user_id)
                entrance = Entrance.by_id(eq_id)
                func = 'delete_user'
                args = (user.card_id, )
                if entrance.type == 2:  # 1-ZK; 2-HK;
                    func = 'del_user_from_web'
                    args = (user.card_id,)
                pkg.data = {'func': func, 'args': args}
            elif pkg.code == GATEWAY_ADD_NEW_EQUIPMENT:
                raw_data = json_data['data']
                func = 'add_new_equipment'
                eq_type_value = int(raw_data['type'])
                args = (raw_data['ip'], raw_data['port'], all_type[eq_type_value], raw_data['is_server'],
                        pkg.storeroom_id, pkg.uuid)
                pkg.data = {'func': func, 'args': args}
            elif pkg.code == GATEWAY_REDUCE_EQUIPMENT:
                raw_data = json_data['data']
                func = 'delete_equipment'
                args = (raw_data['ip'], raw_data['port'], raw_data['is_server'])
                pkg.data = {'func': func, 'args': args}
            else:
                pkg.data = json_data['data'] if 'data' in json_data.keys() else None
            self.q_task.put(pkg)
        except Exception as e:
            print(e)
            mylogger.warning(e)       

    def _get_push_data(self):
        """
        1、从队列获取package；
        2、分析包并触发相应处理程序；
        3、发送package。
        :return:
        """
        print('start send data')
        while self.isrunning:
            try:
                if not self.q_rsl.empty():
                    transfer_package = self.q_rsl.get()
                    data_dict = transfer_package.to_dict()
                    # print('get push data--', data_dict)
                    self._analyze_pkg(package=data_dict)
                    # data_send = bytes('{}'.format(data_dict), encoding='utf-8')
                    # print('File: "' + __file__ + '", Line ' + str(sys._getframe().f_lineno) + ' , in ' + sys._getframe().f_code.co_name)
                    # print(data_send)
                    # if self.sock:
                    #     self.sock.send(data_send)
            except (OSError, BrokenPipeError):
                continue
            except Exception as e:
                print(e)
                mylogger.error(e)
                continue

    def _analyze_pkg(self, package: dict):
        """
        1、门禁事件：
            查询是否存在该门禁的处理线程，存活的就放入pkg，否则创建开始新线程；
        2、数据更新事件：
            根据设备pkg中storeroom的ID号放入相应的线程；
        3、其他推送到web的响应事件；
        :param package:
        :return:
        """
        try:
            print('analyze pkg: ', package)
            # if self.sock:
            #     data_send = bytes('{}'.format(package), encoding='utf-8')
            #     self.sock.send(data_send)
            storeroom_id = package['storeroom_id']
            if package['msg_type'] == 3 and package['equipment_type'] in (3, 5):
                print('111')
                # 门禁的数据更新pkg处理
                if storeroom_id in self.storeroom_thread.keys() and self.storeroom_thread[storeroom_id]['thread'].isAlive():
                    self.storeroom_thread[storeroom_id]['queue'].put(package)
                else:
                    print('\033[1;33m', package['data']['user'] + 'enter to storeroom--' + storeroom_id + ' by entrance--' + str(package['source']), '\033[0m')
                    addr = package['source']
                    eq_id = package['equipment_id']
                    user_code = package['data']['user']
                    queue_storeroom = Queue(50)
                    thread_store_mag = StoreroomManager(entrance_addr=addr, entrance_id=eq_id, user_code=user_code,
                                                        queue_storeroom=queue_storeroom, q_send=self.q_rsl, q_task=self.q_task)
                    thread_store_mag.daemon = True
                    thread_store_mag.start()
                    self.storeroom_thread[storeroom_id] = {'thread': thread_store_mag, 'queue': queue_storeroom}
            elif package['msg_type'] == 3:
                print('222')
                # 其他设备的数据更新pkg处理. 判断是否为重力，并更新DB的实时总重量；若有人在库，则放入库房处理程序；
                if package['equipment_type'] == 1:
                    self._update_db_data(package=package)
                if storeroom_id in self.storeroom_thread.keys() and self.storeroom_thread[storeroom_id]['thread'].isAlive():
                    self.storeroom_thread[storeroom_id]['queue'].put(package)
                else:
                    print('someone has not login but did something')
                    path_cur = os.path.abspath(os.path.dirname(__file__))
                    playsound(path_cur + '/../util/a_o.mp3')
            elif package['msg_type'] == 2 and package['code'] == 301:
                print('333')
                # web确定按钮pkg
                if storeroom_id in self.storeroom_thread.keys() and self.storeroom_thread[storeroom_id]['thread'].isAlive():
                    self.storeroom_thread[storeroom_id]['queue'].put(package)
                    # 等待线程结束信号并返回web
                else:
                    # 此借还线程不存在，返回web信息不成功
                    package['code'] = TASK_HANDLE_ERR
                    package['msg_type'] = 4
                    package['data'] = {'msg': 'the thread of storeroom is not alive'}
                    if self.sock:
                        # data_send = bytes('{}'.format(package), encoding='utf-8')
                        print(type(package))
                        data_send = json.dumps(package).encode()
                        length = len(data_send)
                        # 定制包头 i为4个字节，所以接收方为四个字节，这个大小并不是输入的大小，而是封装固定的大小
                        data_length = struct.pack('i', length)  # 使用struct，直接将int转为二进制型数据传输，对方使用struct解包
                        self.sock.send(data_length)
                        self.sock.send(data_send)
            elif package['msg_type'] == 4 and package['source'] is None:
                print('444')
                # web response
                print('web response--', package)
            else:
                print('555')
                if self.sock:
                    # data_send = bytes('{}'.format(package), encoding='utf-8')
                    print(type(package))
                    data_send = json.dumps(package).encode()
                    length = len(data_send)
                    # 定制包头 i为4个字节，所以接收方为四个字节，这个大小并不是输入的大小，而是封装固定的大小
                    data_length = struct.pack('i', length)  # 使用struct，直接将int转为二进制型数据传输，对方使用struct解包
                    self.sock.send(data_length)
                    self.sock.send(data_send)
                    print('\033[1;34m', 'send to web pkg--', data_send, '\033[0m')
                    mylogger.info('send web pkg--%s' % str(data_send, encoding='utf-8'))
        except Exception as e:
            mylogger.error(e)

    def stop(self):
        self.isrunning = False

    def _update_db_data(self, package):
        eq_id = package['equipment_id']
        sensor_addr = package['data']['addr_num']
        total_weight = package['data']['total']
        grid = Grid.by_eqid_sensor(eq_id=eq_id, sensor_addr=sensor_addr)
        if grid:
            grid.total = total_weight
            grid.save()
            print('\033[1;34m', 'update Gravity--(%s, %d)' % (sensor_addr, total_weight), '\033[0m')


class StoreroomManager(threading.Thread):
    """
    进库房管理
    1、线程初始化先判断该库房的管理模式；
    2、从DB获取该库房的所有货架addr，以及user的工具包
    3、获取当前用户的借还信息列表；
    4、开启定时子线程；
    4、持续监听接收pkg，并定时监听数据是否有变化；
    5、包分析：
        5.1 若为门禁pkg，则保存当前用户的借还信息，修改当前线程用户名；
        5.2 模式一, 若为货架pkg，则对比用户的借还信息并缓存更新； 模式三, 若为入口通道机，则缓存更新用户归还信息；若为出通道机，
        则缓存更新用户借出信息。发送更新信息到web，扫码枪同理。若为web确定信息pkg，则保存当前用户借还信息并结束线程。
    6、定时到则结束线程。
    """
    def __init__(self, entrance_addr, entrance_id, user_code, queue_storeroom, q_send, q_task):
        threading.Thread.__init__(self)
        self.addr = entrance_addr
        self.user_code = user_code
        self.entrance_id = entrance_id
        self.user_id = None
        self.user_role = None
        self.card_id = None
        self.q_send = q_send
        self.q_task = q_task
        self.manage_mode = 1  # default=1
        self.storeroom_id = None
        self.isrunning = True
        self.queue_pkg = queue_storeroom
        self.gravity_goods = dict()  # {'grid_id': (type, value), }
        self.rfid_goods = dict()  # {'epc': (eq_id, ant, is_increased, addr), }
        self.is_close = True
        self.interval = 60
        self.lock = threading.RLock()
        self.gravity_precision = 10
        self.goods_inbound = list()
        self.goods_outbound = list()
        self.channel_machines = dict()
        self.lcd_return = None
        self.lcd_borrow = None

    def run(self):
        """
        1、获取该库房的管理模式;
        2、根据模式选择相应的处理方法并循环执行；
        3、数据无变化相隔interval秒后自动结束当前用户借还流程；
        4、点亮相应的LCD；
        :return:
        """
        self.gravity_precision = conpar.read_yaml_file('configuration')['gravity_precision']
        self.interval = conpar.read_yaml_file('configuration')['storeroom_close_delay_time']
        self._get_manage_mode()
        self._set_current_user(entrance_id=self.entrance_id, entrance_addr=self.addr)
        over_timer = threading.Timer(interval=self.interval, function=self._check_timeout_to_close, args=[self.interval, ])
        over_timer.daemon = True
        over_timer.start()
        self._set_lcd_on()
        while self.isrunning:
            if not self.queue_pkg.empty():
                with self.lock:
                    self.is_close = False
                pkg = self.queue_pkg.get()
                if self.manage_mode == 1:
                    self._handle_mode_one(pkg=pkg)
                elif self.manage_mode == 3:
                    self._handle_mode_three(pkg=pkg)
                else:
                    pass
            else:
                pass

    def _check_timeout_to_close(self, interval):
        """
        定时判断是否没有update，是则结束借还线程；
        :return:
        """
        if self.is_close:
            print('\033[1;33m', 'Times out to close thread--', threading.current_thread().name, '\033[0m')
            self._exit_manage()
        else:
            with self.lock:
                self.is_close = True
            over_timer = threading.Timer(interval=self.interval, function=self._check_timeout_to_close, args=[self.interval, ])
            over_timer.daemon = True
            over_timer.start()

    def _handle_mode_one(self, pkg):
        """
        1、新门禁用户事件；
        2、重力货架事件，获取增减的重量，并更新DB中的实时总重量；
        3、RFID货架事件；
        4、web事件;
        :param pkg:
        :return:
        """
        if pkg['equipment_type'] == 3 or pkg['equipment_type'] == 5:
            # 门禁package
            rsl = self._save_data2db()
            self._set_lcd_off()
            if rsl:
                self.entrance_id = pkg['equipment_id']
                self.user_code = pkg['data']['user']
                self.card_id = pkg['data']['card_id'] if 'card_id' in pkg['data'].keys() else None
                self._set_current_user(entrance_id=self.entrance_id, entrance_addr=pkg['source'])
                print('current user was change to ', self.user_code)
                self._set_lcd_on()
            else:
                pass
        elif pkg['equipment_type'] == 1:
            # 重力柜package
            # 1.modify grid; 2.modify history;
            eq_id = pkg['equipment_id']
            sensor_addr = pkg['data']['addr_num']
            total_weight = pkg['data']['total']
            grid = self._get_gravity_grid(eq_id=eq_id, sensor_addr=sensor_addr)
            if grid.id in self.gravity_goods.keys():
                self.gravity_goods[grid.id][1] += pkg['data']['value']
                if abs(self.gravity_goods[grid.id][1]) < self.gravity_precision:
                    del self.gravity_goods[grid.id]
            else:
                self.gravity_goods[grid.id] = [grid.type, pkg['data']['value']]
            print('all gravity--', self.gravity_goods)
        elif pkg['equipment_type'] == 2:
            # RFID柜package
            # 1.modify goods; 2.modify history;
            eq_id = pkg['equipment_id']
            is_increased = pkg['data']['is_increase']
            for epc_ant in pkg['data']['epcs']:
                ant = epc_ant[1]
                epc = epc_ant[0]
                addr_num = epc_ant[2]
                if epc in self.rfid_goods.keys():
                    del self.rfid_goods[epc]
                else:
                    self.rfid_goods[epc] = (eq_id, ant, is_increased, addr_num)
            print('all RFID--', self.rfid_goods)
        elif pkg['equipment_type'] == 7 and pkg['msg_type'] == 2:
            # 触摸屏下发package
            self._handle_web_btn_info_pkg(pkg=pkg)
        else:
            pass

    def _handle_mode_three(self, pkg):
        """
        1、门禁事件；
        2、出库/入库通道机事件；
        3、出库/入库触摸屏web事件（确定/查询）；
        :param pkg:
        :return:
        """
        if pkg['equipment_type'] == 3 or pkg['equipment_type'] == 5:
            # 门禁package
            rsl = self._save_data2db()
            if rsl:
                self.entrance_id = pkg['equipment_id']
                self.user_code = pkg['data']['user']
                self._set_current_user(entrance_id=self.entrance_id, entrance_addr=pkg['source'])
                print('current user was change to ', self.user_code)
            else:
                pass
            self._start_channel_machine()
        elif pkg['equipment_type'] == 4:
            # 先判断出库or入库
            eq_id = pkg['equipment_id']
            channel = ChannelMachine.by_id(eq_id)
            is_direc_out = channel.direction
            if not is_direc_out:
                # 入库
                is_increased = True
                epcs = list(i[0] for i in pkg['data']['epcs'])
                self.goods_inbound += epcs
                self.goods_inbound = list(set(self.goods_inbound))
                print(self.goods_inbound)
            else:
                # 出库
                is_increased = False
                epcs = list(i[0] for i in pkg['data']['epcs'])
                self.goods_outbound += epcs
                self.goods_outbound = list(set(self.goods_outbound))
                print(self.goods_outbound)
            for epc_ant in pkg['data']['epcs']:
                ant = epc_ant[1]
                epc = epc_ant[0]
                addr_num = epc_ant[2]
                if epc in self.rfid_goods.keys():
                    del self.rfid_goods[epc]
                else:
                    self.rfid_goods[epc] = (eq_id, ant, is_increased, addr_num)
            print('all RFID--', self.rfid_goods)
        elif pkg['equipment_type'] == 7 and pkg['msg_type'] == 2:
            # web确定按钮
            self._handle_web_btn_info_pkg(pkg=pkg)
        else:
            pass

    def _start_channel_machine(self):
        if len(self.channel_machines) > 0:
            for k, v in self.channel_machines.items():
                pkg = TransferPackage()
                pkg.target = v
                pkg.msg_type = 0
                pkg.storeroom_id = self.storeroom_id
                data = {'func': 'start_running', 'args': ()}
                pkg.data = data
                self.q_task.put(pkg)
        else:
            mylogger.warning('storeroom--(%s, %d) has no channel machine to start')

    def _stop_channel_machine(self):
        if len(self.channel_machines) > 0:
            for k, v in self.channel_machines.items():
                pkg = TransferPackage()
                pkg.target = v
                pkg.msg_type = 0
                pkg.storeroom_id = self.storeroom_id
                data = {'func': 'stop_running', 'args': ()}
                pkg.data = data
                self.q_task.put(pkg)
        else:
            mylogger.warning('storeroom--(%s, %d) has no channel machine to stop')

    def _handle_web_btn_info_pkg(self, pkg):
        if pkg['code'] == BTN_CONFIRM_FROM_WEB:
            # 点击确定按钮,保存并返回结果至web
            rsl = self._save_data2db()
            if rsl:
                pkg['code'] = SUCCESS
            else:
                pkg['code'] = TASK_HANDLE_ERR
            if not pkg['data']['is_dir_in']:
                self._stop_channel_machine()
                with self.lock:
                    self.isrunning = False
            pkg['msg_type'] = 4
            self.q_send.put(pkg)
        elif pkg['code'] == BTN_CHECK_FROM_WEB:
            # 点击查询按钮
            pkg['code'] = SUCCESS
            pkg['msg_type'] = 4
            pkg['data']['goods_list'] = {'gravity': self.gravity_goods, 'rfid': self.rfid_goods}
            self.q_send.put(pkg)
        else:
            pass

    def _save_data2db(self):
        """
        1、先查询用户是否有借出，有则清除并更新格子重量；
        2、更改对应EPC的在库状态，更新用户的借还历史；
        3、同时检测是否放置错误的重力格子或者RFID格子；
        :return:
        """
        try:
            print('_save_data2db')
            print('\033[1;33m', 'all gravity--', self.gravity_goods)
            print('all RFID--', self.rfid_goods, '\033[0m')
            history_list = History_inbound_outbound.by_user_need_return(self.user_id)
            # print('history_list--', history_list)
            history_gravity = [h for h in history_list if h.monitor_way == 1]
            history_rfid = [h for h in history_list if h.monitor_way == 2]
            if self.manage_mode == 1:
                self._save_gravity_data(history=history_gravity)
            self._save_rfid_data(history=history_rfid)
            with self.lock:
                self.rfid_goods.clear()
                self.gravity_goods.clear()
            return True
        except Exception as e:
            mylogger.error(e)
            return False

    # def _save_gravity_data(self, history: list):
    #     """
    #     1、若为耗材，则直接保存并设为已还；
    #     2、若为借出，先判断是否位置错误，符合条件则设置为已还，否则新增借出并设置未还；
    #     3、若为归还，则查询是否有未还，有再判断是否全部归还或者放置错误；没有则判断为放置错误；
    #     :param history:
    #     :return:
    #     """
    #     try:
    #         current_dt = datetime.datetime.now()
    #         grids_history = [h.grid_id for h in history]
    #         for k, v in self.gravity_goods.items():
    #             if v[0] == 2:
    #                 # 为耗材
    #                 record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]), outbound_datetime=current_dt,
    #                                                    status=0, monitor_way=1)
    #                 record.save()
    #             else:
    #                 # 工具或仪器
    #                 if v[1] < 0:
    #                     # 为借出
    #                     if k in grids_history:
    #                         # 存在位置错误的
    #                         record = history[grids_history.index(k)]
    #                         diff = record.count - abs(v[1])
    #                         if record.wrong_place_gid and abs(diff) < self.gravity_precision:
    #                             record.update('wrong_place_gid', None)
    #                     else:
    #                         record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]), monitor_way=1,
    #                                                           outbound_datetime=current_dt, status=1)
    #                         record.save()
    #                 else:
    #                     # 为归还
    #                     if k in grids_history:
    #                         # 有未还
    #                         record = history[grids_history.index(k)]
    #                         diff = record.count - v[1]
    #                         if abs(diff) < self.gravity_precision:
    #                             # 全部归还
    #                             record.update('status', 0)
    #                             record.update('inbound_datetime', current_dt)
    #                             if self.user_id != record.user_id:
    #                                 record.update('wrong_return_user', self.user_id)
    #                         elif diff > 5:
    #                             # 部分归还
    #                             record.update('count', diff)
    #                             record.update('inbound_datetime', current_dt)
    #                             if self.user_id != record.user_id:
    #                                 record.update('wrong_return_user', self.user_id)
    #                         else:
    #                             # 放置错误
    #                             record.update('wrong_place_gid', k)
    #                             record.update('inbound_datetime', current_dt)
    #                     else:
    #                         # 放置错误
    #                         record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]), monitor_way=1,
    #                                                           inbound_datetime=current_dt, status=0, wrong_place_gid=k)
    #                         record.save()
    #     except Exception as e:
    #         mylogger.warning(e)

    def _save_gravity_data(self, history: list):
        """
        1、借出
            1.1 有错放记录的格子
            1.2 正常的格子
        2、归还
            2.1 已借未还的格子
            2.2 无借却还的格子
        :param history:
        :return:
        """
        try:
            current_dt = datetime.datetime.now()
            # grids_history = [h.grid_id for h in history]
            for k, v in self.gravity_goods.items():
                if v[1] < 0:
                    # 为借出
                    records_this_grid = [record for record in history if record.grid_id == k]
                    is_wrong_place = False
                    for record in records_this_grid:
                        if record.status == 3:
                            is_wrong_place = True
                    if is_wrong_place:
                        # 有错放记录的格子
                        if self.user_role == 1 or self.user_role == 2:
                            msg = 'the wrong placed grid-%s was take out-%dg by administrator-%s' % (k, v[1], self.user_code)
                            mylogger.info(msg=msg)
                        else:
                            # 普通用户借出
                            is_returned = False
                            for g in self.gravity_goods.values():
                                if g[1] > 0 and abs(g[1] + v[1]) < self.gravity_precision:
                                    # 归还清单有对应的重量
                                    is_returned = True
                                    rsl = History_inbound_outbound.by_user_grid_status3(user_id=self.user_id, grid_id=k)
                                    if rsl:
                                        for record in rsl:
                                            if abs(record.count + v[1]) < self.gravity_precision:
                                                # 清除该错放记录
                                                record.update('status', 0)
                                                record.update('outbound_datetime', current_dt)
                            if not is_returned:
                                status = 0 if v[0] == 2 else 1
                                record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]),
                                                                  outbound_datetime=current_dt,
                                                                  status=status, monitor_way=1)
                                record.save()
                    else:
                        # 没有错放记录的格子
                        status = 0 if v[0] == 2 else 1
                        record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]),
                                                          outbound_datetime=current_dt,
                                                          status=status, monitor_way=1)
                        record.save()
                else:
                    # 为归还
                    grid_id_need_return = [h.grid_id for h in history if (h.status == 1 or h.status == 2)]
                    if k in grid_id_need_return:
                        # 已借未还
                        records_this_grid = [record for record in history if record.grid_id == k and (record.status == 1 or record.status == 2)]
                        remain = v[1]
                        for record in records_this_grid:
                            if record.return_mark is not None:
                                # 尚未还清的记录
                                return_mark_dict = eval(record.return_mark)
                                returned_count = sum(return_mark_dict.values())
                                need_return = record.count - returned_count
                                diff = remain - need_return
                                record.update('inbound_datetime', current_dt)
                                return_mark_dict[current_dt] = need_return
                                record.update('return_mark', str(return_mark_dict))
                                if diff >= -self.gravity_precision:
                                    # 该条记录全还清
                                    record.update('status', 0)
                                    remain -= need_return
                                else:
                                    # 该条记录只还部分，并结束该格子的归还
                                    break
                            else:
                                # 未还过的记录
                                diff = remain - record.count
                                record.update('inbound_datetime', current_dt)
                                return_mark_dict = {current_dt: record.count}
                                record.update('return_mark', str(return_mark_dict))
                                if diff >= -self.gravity_precision:
                                    # 该条记录全还清
                                    record.update('status', 0)
                                    remain -= record.count
                                else:
                                    # 该条记录只还部分，并结束该格子的归还
                                    break
                        print('remain--', remain)
                        if remain > self.gravity_precision:
                            # 归还后有超出重量的其他东西，记录为错放格子
                            record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=remain, monitor_way=1,
                                                              inbound_datetime=current_dt, status=3, wrong_place_gid=k)
                            record.save()
                            msg = 'the grid-%s was returned by overweight-%dg by user-%s' % (k, v[1], self.user_code)
                            mylogger.warning(msg=msg)
                    else:
                        # 无借却还
                        if self.user_role == 1 or self.user_role == 2:
                            msg = 'the grid-%s was put in-%dg by administrator-%s' % (k, v[1], self.user_code)
                            mylogger.info(msg=msg)
                            record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]),
                                                              monitor_way=1, inbound_datetime=current_dt, status=5)
                            record.save()
                            # 修改该格子物资的新增字段
                        else:
                            if grid_id_need_return:
                                # 只要仍然有未还的记录，放错格子
                                record = History_inbound_outbound(user_id=self.user_id, grid_id=k, count=abs(v[1]),
                                                                  monitor_way=1, inbound_datetime=current_dt, status=3,
                                                                  wrong_place_gid=k)
                                record.save()
                                msg = 'the grid-%s was wrong placed weight-%dg by user-%s' % (k, v[1], self.user_code)
                                mylogger.info(msg=msg)
        except Exception as e:
            mylogger.warning(e)

    # def _save_rfid_data(self, history: list):
    #     """
    #     1、逐个判断借出或者归还；
    #     2、借出：若耗材则直接保存已还，否则直接保存未还并设置goods出库；
    #     3、归还：是否在未还列表，是则修改已还并设置goods入库，否则新增记录设置错误用户已还并设置goods入库；
    #     :param history:
    #     :return:
    #     """
    #     try:
    #         # print('rfid history--', history)
    #         current_dt = datetime.datetime.now()
    #         # 先把self.rfid_goods中的key从bytes转为str；
    #         rfid_current = {k.hex(): v for k, v in self.rfid_goods.items()}
    #         goods_db = Goods.by_epc_list(epcs=rfid_current.keys())
    #         goods_epc_db = [g.epc for g in goods_db]
    #         epc_grid_id = {h.epc: h.grid_id for h in history} if history is not None else {}
    #         for epc, v in rfid_current.items():
    #             print('epc--', epc)
    #             print('goods_epc_db--', goods_epc_db)
    #             grid_current = Grid.by_eqid_antenna(eq_id=v[0], antenna_num=v[1].hex(), addr_num=v[3].hex())
    #             grid_id_current = grid_current.id if grid_current is not None else None
    #             if epc in goods_epc_db:
    #                 # 存在于DB的EPC
    #                 if v[2] is True:
    #                     # 为归还
    #                     wrong_place_gid = grid_current if grid_id_current != epc_grid_id[epc] else None
    #                     record = History_inbound_outbound.by_epc_need_return(epc=epc)
    #                     if record:
    #                         wrong_return_user = self.user_id if self.user_id != record.user_id else None
    #                         record.update('status', 0)
    #                         record.update('inbound_datetime', current_dt)
    #                         record.update('wrong_place_gid', wrong_place_gid)
    #                         record.update('wrong_return_user', wrong_return_user)
    #                         goods = [g for g in goods_db if g.epc == epc]
    #                         if goods:
    #                             goods[0].update('is_in_store', 1)
    #                     else:
    #                         record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc,
    #                                                           count=1, inbound_datetime=current_dt, status=0,
    #                                                           wrong_place_gid=grid_id_current, wrong_return_uid=self.user_id)
    #                         record.save()
    #                         mylogger.warning('get no history by_epc_need_return() EPC(%s) but still was returned' % epc)
    #                 else:
    #                     # 为借出
    #                     record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc,
    #                                                       count=1, outbound_datetime=current_dt, status=1)
    #                     record.save()
    #                     goods = [g for g in goods_db if g.epc == epc]
    #                     if goods:
    #                         goods[0].update('is_in_store', 0)
    #             else:
    #                 # 不存在于DB的EPC
    #                 record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc,
    #                                                   count=1, inbound_datetime=current_dt, status=0,
    #                                                   wrong_place_gid=grid_id_current)
    #                 record.save()
    #                 mylogger.warning('get no goods in database by EPC(%s) but still was returned' % epc)
    #     except Exception as e:
    #         mylogger.warning(e)

    def _save_rfid_data(self, rfid_history: list):
        """
        1、逐个判断借出或者归还；
        2、借出：若耗材则直接保存已还，否则直接保存未还并设置goods出库；
        3、归还：是否在未还列表，是则修改已还并设置goods入库，否则新增记录设置错误用户已还并设置goods入库；
        :param history:
        :return:
        """
        try:
            # print('rfid history--', history)
            current_dt = datetime.datetime.now()
            # 先把self.rfid_goods中的key从bytes转为str；
            rfid_current = {k.hex(): v for k, v in self.rfid_goods.items()}
            goods_registered = Goods.by_epc_list(epcs=list(rfid_current.keys()))
            goods_epc_db = {g.epc: g for g in goods_registered}
            epc_grid_history = {h.epc: h for h in rfid_history} if rfid_history is not None else {}
            for epc, v in rfid_current.items():
                grid_current = Grid.by_eqid_antenna(eq_id=v[0], antenna_num=v[1].hex(), addr_num=v[3].hex())
                grid_id_current = grid_current.id if grid_current is not None else None
                if epc in goods_epc_db.keys():
                    # 存在于DB的EPC
                    if v[2] is True:
                        # 为归还
                        if epc in epc_grid_history.keys():
                            # 该EPC在未还列表
                            goods_grid_id = goods_epc_db[epc].grid_id
                            wrong_place_gid = grid_id_current if grid_id_current != goods_grid_id else None
                            status = 3 if wrong_place_gid else 0
                            record = epc_grid_history[epc]
                            if record:
                                record.update('status', status)
                                record.update('inbound_datetime', current_dt)
                                record.update('wrong_place_gid', wrong_place_gid)
                        else:
                            if self.user_role == 1 or self.user_role == 2:
                                # 管理员新增物资
                                record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc,
                                                                  count=1, inbound_datetime=current_dt, status=5)
                                record.save()
                                mylogger.info('EPC(%s) was increased by administrator--%s' % (epc, self.user_code))
                            else:
                                # 普通用户代还
                                record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc,
                                                                  count=1, inbound_datetime=current_dt, status=4)
                                record.save()
                                mylogger.info('EPC(%s) was returned by wrong user--%s' % (epc, self.user_code))
                    else:
                        # 为借出
                        goods = goods_epc_db[epc]
                        status = 0 if goods.type == 2 else 1
                        record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc, count=1,
                                                          outbound_datetime=current_dt, status=status)
                        record.save()
                        goods.update('is_in_store', 0)
                else:
                    # 不存在于DB的EPC
                    record = History_inbound_outbound(user_id=self.user_id, grid_id=grid_id_current, epc=epc, count=1,
                                                      inbound_datetime=current_dt, status=6,
                                                      wrong_place_gid=grid_id_current)
                    record.save()
                    mylogger.warning('EPC(%s) was not registered but token in by user--%s' % (epc, self.user_code))
        except Exception as e:
            mylogger.warning(e)

    def _get_toolkit_data(self, user):
        """
        从DB获取当前用户的工具包数据
        :param user:
        :return:
        """
        pass

    def _get_manage_mode(self):
        """
        从DB获取该库房的管理模式以及所有货架数据
        :param storeroom_id:
        :return:
        """
        entrance = Entrance.by_addr(self.addr[0], self.addr[1])
        storeroom = entrance.storeroom
        self.storeroom_id = storeroom.id
        self.manage_mode = storeroom.manage_mode
        channels = storeroom.channel_machines
        if channels:
            for cm in channels:
                if cm.direction == 1:
                    self.channel_machines['in'] = (cm.ip, cm.port)
                elif cm.direction == 0:
                    self.channel_machines['out'] = (cm.ip, cm.port)
                else:
                    self.channel_machines['in_out'] = (cm.ip, cm.port)
        print(storeroom.shelfs)

    def _set_current_user(self, entrance_id, entrance_addr):
        """
        设置当前库房登录者并发送至web
        不存在就创建并保存到DB
        :return:
        """
        user = User.by_code(code=self.user_code)
        if user is not None:
            self.user_id = user.uuid
            data = {'user_id': self.user_id}
            pkg_to_web = TransferPackage(code=USER_ENTRANCE_SUCCESS, eq_type=3, msg_type=2, storeroom_id=self.storeroom_id, data=data,
                                         eq_id=entrance_id)
            self.q_send.put(pkg_to_web)
            print('put to q_send for sending to web--', pkg_to_web)
            print('size of q_send', self.q_send.qsize())
            roles = user.roles
            if roles:
                self.user_role = roles[0].level
            else:
                self.user_role = 3
        else:
            mylogger.warning('get no user by code %s' % self.user_code)
            user = User(login_name=self.user_code, code=self.user_code, card_id=self.card_id,
                        register_time=datetime.datetime.now())
            rsl = user.save()
            if not rsl:
                mylogger.warning('Fail to save user by code %s from entrance %s' % (self.user_code, str(entrance_addr)))

    def _get_gravity_grid(self, eq_id, sensor_addr):
        grid = Grid.by_eqid_sensor(eq_id=eq_id, sensor_addr=sensor_addr)
        return grid

    def _get_list_need_return(self):
        """
        查询待还格子对应的显示模块
        :return: {(ip, port, add_num), }
        """
        history = History_inbound_outbound.by_user_need_return(self.user_id)
        grids = {h.grid_id for h in history}
        lcd_modules = Grid.by_id_list(id_list=grids)
        lcd_addr_list = {(lcd.led_id, lcd.led_addr) for lcd in lcd_modules}
        lcd_list = list()
        for lcd in lcd_addr_list:
            if lcd[0] is not None and lcd[1] is not None:
                indicator = Indicator.by_id(lcd[0])
                if indicator:
                    lcd_list.append((indicator.ip, indicator.port, lcd[1]))
        return lcd_list

    def _get_list_need_borrow(self):
        """
        查询待借格子对应的显示模块
        :return: {(ip, port, add_num), }
        """
        goods = Toolkit.by_user(self.user_id)
        grids = {good[1].grid_id for good in goods}
        lcd_modules = Grid.by_id_list(id_list=grids)
        lcd_addr_list = {(lcd.led_id, lcd.led_addr) for lcd in lcd_modules}
        lcd_list = list()
        for lcd in lcd_addr_list:
            if lcd[0] is not None and lcd[1] is not None:
                indicator = Indicator.by_id(lcd[0])
                if indicator:
                    lcd_list.append((indicator.ip, indicator.port, lcd[1]))
        return lcd_list

    def _exit_manage(self):
        """
        出库房管理
        1、解除库房&人的绑定；
        2、保存库存与工具包信息到DB。
        3、关闭相应的LCD；
        :return:
        """
        self._save_data2db()
        # if self.channel_machines:
        #     self._stop_channel_machine()
        self._set_lcd_off()
        with self.lock:
            self.isrunning = False

    def check_inventory(self):
        """
        盘点
        :return:
        """
        pass

    def _set_lcd_on(self):
        """
        1、待借与待还格子开背光；
        2、待借led绿色，待还led红色；
        :return:
        """
        if self.manage_mode == 1:
            self.lcd_return = self._get_list_need_return()
            self.lcd_borrow = self._get_list_need_borrow()
            if self.lcd_return:
                for lcd in self.lcd_return:
                    data1 = {'func': 'onBacklight', 'args': (lcd[2],)}
                    pkg1 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data1)
                    self.q_task.put(pkg1)
                    data2 = {'func': 'onLed', 'args': (lcd[2], (1, 0, 0))}
                    pkg2 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data2)
                    self.q_task.put(pkg2)
            if self.lcd_borrow:
                for lcd in self.lcd_borrow:
                    data1 = {'func': 'onBacklight', 'args': (lcd[2],)}
                    pkg1 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data1)
                    self.q_task.put(pkg1)
                    data2 = {'func': 'onLed', 'args': (lcd[2], (0, 1, 0))}
                    pkg2 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data2)
                    self.q_task.put(pkg2)

    def _set_lcd_off(self):
        if self.manage_mode == 1:
            if self.lcd_return:
                for lcd in self.lcd_return:
                    data1 = {'func': 'offBacklight', 'args': (lcd[2],)}
                    pkg1 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data1)
                    self.q_task.put(pkg1)
                    data2 = {'func': 'offLed', 'args': (lcd[2],)}
                    pkg2 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data2)
                    self.q_task.put(pkg2)
            if self.lcd_borrow:
                for lcd in self.lcd_borrow:
                    data1 = {'func': 'offBacklight', 'args': (lcd[2],)}
                    pkg1 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data1)
                    self.q_task.put(pkg1)
                    data2 = {'func': 'offLed', 'args': (lcd[2],)}
                    pkg2 = TransferPackage(target=(lcd[0], lcd[1]), msg_type=0, storeroom_id=self.storeroom_id, data=data2)
                    self.q_task.put(pkg2)


if __name__ == '__main__':
    from queue import Queue

    mycontroler = None
    q_task = Queue(50)
    q_rsl = Queue(50)
    try:
        mycontroler = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        mycontroler.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mycontroler.stop()
        print('stop')
    finally:
        mycontroler.stop()
        print('stop')
