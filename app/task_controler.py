from multiprocessing import Process
import threading
import socket
import time
from .globalvar import *
import struct
from app.myLogger import mylogger
from database.models import Equipment


class TaskControler(Process):
    def __init__(self, queue_task, queue_rsl):
        super().__init__()
        self.sock = None
        self.q_task = queue_task  # 从web接收的数据包队列
        self.q_rsl = queue_rsl  # 发送到web的数据包队列
        self.isrunning = True
        self.storeroom_user_dict = dict()  # 当前进入此库房的人 {库房addr：人uuid}
        self.lock_storeroom_user = threading.RLock()

    def run(self):
        thread_conn = threading.Thread(target=self._monitorconn)
        thread_send = threading.Thread(target=self._send_data)
        thread_conn.daemon = True
        thread_send.daemon = True
        thread_conn.start()
        thread_send.start()
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
                    print('waitting for new connection')
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

    def _send_data(self):
        """
        1、从队列获取package；
        2、分析包并触发相应处理程序；
        3、发送package。
        :return:
        """
        while self.isrunning:
            try:
                if not self.q_rsl.empty():
                    transfer_package = self.q_rsl.get()
                    data_dict = transfer_package.to_dict()
                    # self._analyze_pkg(package=data_dict)
                    data_send = bytes('{}'.format(data_dict), encoding='utf-8')
                    print(data_send)
                    if self.sock:
                        self.sock.send(data_send)
            except (OSError, BrokenPipeError):
                continue
            except Exception as e:
                print(e)
                mylogger.error(e)
                continue

    def _analyze_pkg(self, package: dict):
        try:
            if package['msg_type'] == 3 and package['eq_type'] in (3, 5):
                addr = package['source']
                user_code = package['data']['rsl'][0]
                with self.lock_storeroom_user:
                    if addr not in self.storeroom_user_dict.keys():
                        self.storeroom_user_dict[addr] = user_code
                        thread_enter = threading.Thread(target=self._enter_manage)
                        thread_enter.daemon = True
                        thread_enter.start()
                    else:
                        self.storeroom_user_dict[addr] = user_code
            else:
                pass
        except Exception as e:
            mylogger.error(e)

    def stop(self):
        self.isrunning = False

    def _enter_manage(self):
        """
        进库房管理
        1、发送进入通知发送到web；
        2、先判断库房的管理模式；
        3、从DB获取该库房的所有货架addr，以及user的工具包
        4、查询工具包中物资点亮LCD；
        5、循环监听发送数据包中该库房所有货架的数值变化，变化值发送到web；
        6、等待退出条件（web确认/超时/新门禁通知）退出该循环；
        7、调用出库管理。
        :return:
        """
        cur_store_change = {}  # grid: value

    def exit_manage(self):
        """
        出库房管理
        1、解除库房：人的绑定；
        2、保存库存与工具包信息到DB。
        :return:
        """
        pass

    def check_inventory(self):
        """
        盘点
        :return:
        """
        pass


class StoreroomManager(threading.Thread):
    def __init__(self, addr):
        self.addr = addr

    def run(self):
        """
        循环获取货架状态变化并发送到web
        :return:
        """
        pass

    def _get_toolkit_data(self, user):
        """
        从DB获取当前用户的工具包数据
        :param user:
        :return:
        """
        pass

    def _get_all_shelfs(self, storeroom_id):
        """
        从DB获取该库房的所有货架数据
        :param storeroom_id:
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
