from multiprocessing import Process, Queue
import threading
import socket
import time
from .globalvar import *
import struct
from app.myLogger import mylogger
from database.models2 import Entrance, User, Grid, History_inbound_outbound
import sys


class TaskControler(Process):
    def __init__(self, queue_task, queue_rsl):
        super().__init__()
        self.sock = None
        self.q_task = queue_task  # 从web接收的数据包队列
        self.q_rsl = queue_rsl  # 发送到web的数据包队列
        self.isrunning = True
        self.storeroom_thread = dict()  # {'storeroom_id': {'thread': thread, 'queue': queue}, }
        self.lock_storeroom_user = threading.RLock()

    def run(self):
        thread_conn = threading.Thread(target=self._monitorconn)
        thread_send = threading.Thread(target=self._get_push_data)
        thread_conn.daemon = True
        thread_send.daemon = True
        thread_conn.start()
        thread_send.start()
        print('start task')
        while self.isrunning:
            pass

    def _monitorconn(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = ('', 9999)
        server_sock.bind(addr)
        server_sock.listen(1)
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
                        data_dict = eval(str(data, encoding='utf-8'))
                        # # data_send = bytes('{}'.format(data_dict), encoding='utf-8')
                        # # client_sock.send(data_send)
                        # cmd = data_dict['data']['addr'].__str__() + '\r\n' + data_dict['data']['func'] + '\r\n' + \
                        #       data_dict['data']['args'].__str__() + '\r\n' + data_dict['uuid']
                        # cmd_b = bytes(cmd, encoding='utf-8')
                        # print(cmd_b)
                        # self.puttask(data=cmd_b)
                        self.puttask(data_dict)
            except (OSError, BrokenPipeError):
                continue
            except KeyboardInterrupt:
                break
        server_sock.shutdown()
        server_sock.close()

    def puttask(self, data):
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
            # pkg = eval(str(data, encoding='utf-8'))
            pkg = TransferPackage()
            pkg.uuid = data['uuid'] if 'uuid' in data.keys() else None
            pkg.target = data['target'] if 'target' in data.keys() else None
            pkg.source = data['source'] if 'source' in data.keys() else None
            pkg.code = data['code'] if 'code' in data.keys() else None
            pkg.msg_type = data['msg_type'] if 'msg_type' in data.keys() else None
            pkg.data = data['data'] if 'data' in data.keys() else None
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
            storeroom_id = package['storeroom_id']
            if package['msg_type'] == 3 and package['equipment_type'] in (3, 5):
                if storeroom_id in self.storeroom_thread.keys() and self.storeroom_thread[storeroom_id]['thread'].isAlive():
                    self.storeroom_thread['queue'].put(package)
                else:
                    print(package['data']['user'], ' enter to storeroom--', package['source'])
                    addr = package['source']
                    user_code = package['data']['user']
                    queue_storeroom = Queue(50)
                    thread_store_mag = StoreroomManager(addr=addr, user_code=user_code, queue_storeroom=queue_storeroom)
                    thread_store_mag.daemon = True
                    thread_store_mag.start()
                    self.storeroom_thread[storeroom_id] = {'thread': thread_store_mag, 'queue': queue_storeroom}
            elif package['msg_type'] == 3:
                if storeroom_id in self.storeroom_thread.keys() and self.storeroom_thread[storeroom_id]['thread'].isAlive():
                    self.storeroom_thread[storeroom_id]['queue'].put(package)
            else:
                pass
        except Exception as e:
            mylogger.error(e)

    def stop(self):
        self.isrunning = False


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
    def __init__(self, addr, user_code, queue_storeroom):
        threading.Thread.__init__(self)
        self.addr = addr
        self.user_code = user_code
        self.user_id = None
        self.manage_mode = 1  # default=1
        self.storeroom_id = None
        self.isrunning = True
        self.queue_pkg = queue_storeroom
        self.gravity_goods = dict()  # {'grid_id': (type, value), }
        self.rfid_goods = dict()  # {'grid_id': (type, value), }
        self.is_close = True
        self.lock = threading.RLock()

    def run(self):
        """
        1、获取该库房的管理模式;
        2、根据模式选择相应的处理方法并循环执行；
        :return:
        """
        self._get_manage_mode()
        self._get_user()
        interval = 60
        over_timer = threading.Timer(interval=interval, function=self._get_is_close, args=[interval, ])
        over_timer.start()
        while self.isrunning:
            if not self.queue_pkg.empty():
                with self.lock:
                    self.is_close = False
                pkg = self.queue_pkg.get()
                print('store: ', self.storeroom_id, ' got package: ', pkg)
                if self.manage_mode == 1:
                    self._handle_mode_one(pkg=pkg)
                elif self.manage_mode == 3:
                    self._handle_mode_three(pkg=pkg)
                else:
                    pass
            else:
                pass

    def _get_is_close(self, interval):
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
            over_timer = threading.Timer(interval=interval, function=self._get_is_close, args=[interval, ])
            over_timer.start()

    def _handle_mode_one(self, pkg):
        """
        1、新门禁用户事件；
        2、重力货架事件；
        3、RFID货架事件；
        :param pkg:
        :return:
        """
        if pkg['equipment_type'] == 3:
            self._save_data2db()
            self.user_code = pkg['data']['user']
            self._get_user()
        elif pkg['equipment_type'] == 1:
            eq_id = pkg['equipment_id']
            sensor_addr = pkg['data']['addr_num']
            grid = self._get_grid(eq_id=eq_id, sensor_addr=sensor_addr)
            if grid.id in self.gravity_goods.keys():
                self.gravity_goods[grid.id][1] += pkg['data']['value']
                if abs(self.gravity_goods[grid.id][1]) < 5:
                    del self.gravity_goods[grid.id]
            else:
                self.gravity_goods[grid.id] = [grid.type, pkg['data']['value']]
            print(self.gravity_goods)
        elif pkg['equipment_type'] == 2:
            pass
        else:
            pass

    def _handle_mode_three(self, pkg):
        pass

    def _save_data2db(self):
        """
        1、先查询用户是否有借出，有则清除并更新格子重量；
        :return:
        """
        history_list = History_inbound_outbound.by_user_not_return()
        goods_id = [h.goods_id for h in history_list]
        if history_list is not None:
            for k, v in self.gravity_goods:
                goods = Grid.by_id(k)
                weight_change = v[1] - goods.weight
                if k in goods_id:
                    pass
        else:
            pass

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
        print(entrance.id)
        storeroom = entrance.storeroom
        self.storeroom_id = storeroom.id
        self.manage_mode = storeroom.manage_mode
        print(storeroom.shelfs)

    def _get_user(self):
        user = User.by_code(code=self.user_code)
        if user is not None:
            self.user_id = user.uuid
        else:
            mylogger.error('get no user by code %s' % self.user_code)

    def _get_grid(self, eq_id, sensor_addr):
        grid = Grid.by_eqid_sensor(eq_id=eq_id, sensor_addr=sensor_addr)
        return grid

    def _get_history(self):
        pass

    def _exit_manage(self):
        """
        出库房管理
        1、解除库房：人的绑定；
        2、保存库存与工具包信息到DB。
        :return:
        """
        with self.lock:
            self.isrunning = False

    def check_inventory(self):
        """
        盘点
        :return:
        """
        pass


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
