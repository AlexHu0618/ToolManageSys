import threading
import socket
import time
from queue import Queue
from binascii import *
from crcmod import *
from app.myLogger import mylogger
from settings.config import config_parser as conpar


class ChannelMachineR2000FH(threading.Thread):
    def __init__(self, s, addr):
        threading.Thread.__init__(self)
        self.tcp_socket = s
        self.addr = addr
        self.isrunning = True
        self.q_cmd = Queue(50)
        self.tcp_socket.settimeout(1)
        self.current_epcs = list()
        self.lock = threading.RLock()
        self.data_buff = list()  # [(epc, ant, addr_num), ]
        self.timeout_counter = 0
        self.is_rs485 = True
        self.addr_nums = ['01']
        self.is_online = {num: False for num in self.addr_nums}
        self.update_interval = 10

    def run(self):
        """
        1、主线程负责外部指令处理以及接收处理，子线程负责数据发送；
        2、使用生产消费者模式；
        3、每隔5s从设备读取一次数据更新；
        :return:
        """
        self.stop_running()
        self.tcp_socket.settimeout(1)
        thd_send = threading.Thread(target=self._send_recv)
        # thd_auto_inventory = threading.Timer(interval=5, function=self._inventory_once)
        thd_send.daemon = True
        thd_send.start()
        # thd_auto_inventory.start()
        # self._inventory()
        second_interval = conpar.read_yaml_file('configuration')['cm_r2000fh_update_interval']
        self.update_interval = second_interval if second_interval > 5 else 5
        thread_ontime = threading.Timer(interval=self.update_interval, function=self._check_data_update)
        thread_ontime.daemon = True
        thread_ontime.start()
        self.stop_running()
        while self.isrunning:
            try:
                # if not self.queuetask.empty():
                #     task, args = self.queuetask.get()
                #     rsl = methodcaller(task, *args)(self)
                #     if rsl is not None:
                #         pkg = TransferPackage(code=SUCCESS, eq_type=4, data={'rsl': rsl}, source=self.addr, msg_type=4,
                #                               storeroom_id=self.storeroom_id, eq_id=self.uuid)
                #         self.queuersl.put(pkg)
                #         self.event.set()
                # else:
                #     time.sleep(1)
                time.sleep(1)
                self.start_running()
                time.sleep(30)
                self.stop_running()
                break
            except KeyboardInterrupt:
                self._stop()
                self.tcp_socket.shutdown(2)
                self.tcp_socket.close()
        print('thread CM_R2000FH is closed.....')

    def start_running(self):
        self._inventory()
        print('start inv')

    def stop_running(self):
        self._stop()
        print('stop inv')

    def _check_data_update(self):
        start = time.time()
        try:
            with self.lock:
                print('CM_R2000FH old EPCs: ', self.data_buff)
                print('CM_R2000FH new EPCs: ', self.current_epcs)
                if self.current_epcs is not None:
                    print(time.asctime(), 'CM_R2000RH(%s, %d) exception:' % (self.addr[0], self.addr[1]), self.current_epcs)
                    diff_epcs = list(set(epc[0] for epc in self.current_epcs) ^ set(epc[0] for epc in self.data_buff))
                    print('CM_R2000FH diff_epcs--', diff_epcs)
                    if diff_epcs:
                        is_increase = True if len(self.current_epcs) > len(self.data_buff) else False
                        diff = [epc_ant for epc_ant in self.current_epcs if
                                epc_ant[0] in diff_epcs] if is_increase else [epc_ant for epc_ant in self.data_buff if
                                                                              epc_ant[0] in diff_epcs]
                        data = {'epcs': diff, 'is_increase': is_increase}
                        # pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=4, data=data, source=self.addr,
                        #                       msg_type=3, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        # self.queue_push_data.put(pkg)
                    self.data_buff.clear()
                    self.data_buff = [epc_ant for epc_ant in self.current_epcs]
                    self.current_epcs.clear()
        except Exception as e:
            print('CM_R2000RH(%s, %d) exception: %s' % (self.addr[0], self.addr[1], e))
            mylogger.error('CM_R2000RH(%s, %d) exception: %s' % (self.addr[0], self.addr[1], e))
        end = time.time()
        start_end = end - start
        interval = round((self.update_interval - start_end), 2)

        thread_ontime = threading.Timer(interval=interval, function=self._check_data_update)
        thread_ontime.daemon = True
        thread_ontime.start()

    def _send_recv(self):
        while self.isrunning:
            if not self.q_cmd.empty():
                cmd = self.q_cmd.get()
                self.tcp_socket.send(cmd)
            else:
                try:
                    data = self.tcp_socket.recv(1024)
                    # print('RH2000--', data)
                    self.timeout_counter = 0
                    self._analyze_recv_data(data=data)
                except socket.timeout:
                    self.timeout_counter += 1
                    if self.timeout_counter > 20:
                        print('CM_R2000FH--%s times out' % str(self.addr))
                        with self.lock:
                            self.isrunning = False
                    continue
                except (OSError, BrokenPipeError):
                    print('Error', 'TCP连接已断开')
                    self.is_running = False
                except AttributeError:
                    print('Error', 'TCP未连接')
                    self.is_running = False
                except Exception as e:
                    print('Error', repr(e))

    def _analyze_recv_data(self, data):
        len_all_data = len(data)
        start = 0
        end = 0
        mask = '32' if self.is_rs485 else '12'
        hold_bit = 1 if self.is_rs485 else 0
        epcs = list()
        while end < len_all_data:
            head = data[start:start + 5]
            if head == bytes.fromhex('5A 00 01 %s 00' % mask):
                addr_num = data[(start + 5): (start + 6)] if self.is_rs485 else b'\x00'
                len_data = int.from_bytes(data[(start + 5 + hold_bit):(start + 7 + hold_bit)], byteorder='big',
                                          signed=False)
                len_epc = int.from_bytes(data[(start + hold_bit + 7):(start + hold_bit + 9)], byteorder='big',
                                         signed=False)
                epc = data[(start + hold_bit + 9):(start + hold_bit + 9 + len_epc)]
                ant = data[(start + 9 + len_epc + 2 + hold_bit):(start + 9 + len_epc + 2 + 1 + hold_bit)]
                print('(EPC, ant, addr_num)--(%s, %s, %s)' % (epc, ant, addr_num))
                epcs.append((epc, ant, addr_num))
                # with self.lock:
                #     if epc not in [epc_ant[0] for epc_ant in self.current_epcs]:
                #         self.current_epcs.append((epc, ant, addr_num))
                start += (5 + 2 + len_data + 2 + hold_bit)
                end = start
            elif head == bytes.fromhex('5A 00 01 %s 02' % mask):
                start += (5 + 5 + hold_bit)
                end = start
            else:
                break
        if len(epcs) > 0:
            print(epcs)
            data = {'epcs': epcs, 'is_increase': True}
            # pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=4, data=data, source=self.addr, msg_type=3,
            #                       storeroom_id=self.storeroom_id, eq_id=self.uuid)
            # self.queue_push_data.put(pkg)

    def get_current_epc(self):
        print(self.data_buff)
        return self.data_buff

    def _crc16(self, cmd_f: str):
        crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)  # CRC16-CCITT
        # crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000) #CRC16-Modbus
        data = cmd_f.replace(" ", "")
        readcrcout = hex(crc16(unhexlify(data))).upper()
        str_list = list(readcrcout)
        if len(str_list) == 5:
            str_list.insert(2, '0')  # 位数不足补0
        crc_data = "".join(str_list)
        return crc_data

    def _inventory_once(self):
        if self.is_rs485:
            cmd = bytes()
            for addr in self.addr_nums:
                cmd_temp = '5A 00 01 22 10 ' + addr + ' 00 05 00 00 00 FF 00'
                crc16 = self._crc16(cmd_temp[2:])
                cmd += bytes.fromhex(cmd_temp + crc16[-4:])
        else:
            cmd = bytes.fromhex('5A 00 01 02 10 00 05 00 00 00 FF 00 D4 68')
        self.q_cmd.put(cmd)
        thd_auto_inventory = threading.Timer(interval=5, function=self._inventory_once)
        thd_auto_inventory.start()

    def _inventory(self):
        if self.is_rs485:
            cmd = bytes()
            for addr in self.addr_nums:
                cmd_temp = '5A 00 01 22 10 ' + addr + ' 00 05 00 00 00 FF 01'
                crc16 = self._crc16(cmd_temp[2:])
                cmd += bytes.fromhex(cmd_temp + crc16[-4:])
        else:
            cmd = bytes.fromhex('5A 00 01 02 10 00 05 00 00 00 FF 01 C4 49')
        self.q_cmd.put(cmd)
        print(cmd.hex())
        # time.sleep(1)
        # self._stop()
        # thd_auto_inventory = threading.Timer(interval=2, function=self._inventory)
        # thd_auto_inventory.start()

    def _stop(self):
        if self.is_rs485:
            cmd = bytes()
            for addr in self.addr_nums:
                cmd_temp = '5A 00 01 22 FF ' + addr + ' 00 00'
                crc16 = self._crc16(cmd_temp[2:])
                cmd += bytes.fromhex(cmd_temp + crc16[-4:])
        else:
            cmd = bytes.fromhex('5A 00 01 02 FF 00 00 88 5A')
        self.q_cmd.put(cmd)
        print(cmd.hex())


class test:

    def add(self):
        print('add')
        return 1

    def test(self):
        from operator import methodcaller
        task, args = ('add', ())
        rsl = methodcaller(task, *args)(self)
        print(rsl)


if __name__ == '__main__':

    # test = test()
    # test.test()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    addr = ('', 8809)
    server_sock.bind(addr)
    # 监听请求
    server_sock.listen()
    # 建立长连接
    try:
        print('--等待客户端连接本服务器8809！--')
        while True:
            client_sock, client_addr = server_sock.accept()
            print('connected in CLIENT--', client_addr)
            thr = ChannelMachineR2000FH(client_sock, client_addr)
            if thr is not None:
                thr.daemon = True
                thr.start()
                thr.join()
                break
            server_sock.shutdown(socket.SHUT_RDWR)
            server_sock.close()
    except KeyboardInterrupt:
        server_sock.shutdown(socket.SHUT_RDWR)
        server_sock.close()
    # finally:
    #     server_sock.shutdown(socket.SHUT_RDWR)
    #     server_sock.close()

