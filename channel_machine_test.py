import threading
import socket
import time
from queue import Queue
from binascii import *
from crcmod import *


class Rfid2000FH(threading.Thread):
    def __init__(self, s):
        threading.Thread.__init__(self)
        self._socket = s
        self.is_running = True
        self.q_cmd = Queue(50)
        self._socket.settimeout(1)
        self.current_epcs = list()
        self.lock = threading.RLock()
        self.is_rs485 = True
        self.addr_nums = ['01']
        self.is_online = {num: False for num in self.addr_nums}

    def run(self):
        """
        1、主线程负责外部指令处理以及接收处理，子线程负责数据发送；
        2、使用生产消费者模式；
        :return:
        """
        print('thread start')
        thd_send = threading.Thread(target=self._send_recv)
        check_online = threading.Timer(interval=5, function=self._check_online)
        thd_send.daemon = True
        thd_send.start()
        # check_online.start()
        self._inventory()
        while self.is_running:
            try:
                print(self.current_epcs)
                time.sleep(10)
            except KeyboardInterrupt:
                self._stop()
                self._socket.shutdown(2)
                self._socket.close()

    def _crc16(self, cmd_f: str):
        crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)  # CRC16-CCITT
        # crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000) #CRC16-Modbus
        data = cmd_f.replace(" ", "")
        readcrcout = hex(crc16(unhexlify(data))).upper()
        str_list = list(readcrcout)
        if len(str_list) == 5:
            str_list.insert(2, '0')  # 位数不足补0
        crc_data = "".join(str_list)
        # print(crc_data)
        return crc_data

    def _check_online(self):
        with self.lock:
            for k in self.is_online.keys():
                self.is_online[k] = False
        if self.is_rs485:
            cmd = bytes()
            for addr in self.addr_nums:
                cmd_temp = '5A 00 01 21 16 ' + addr + ' 00 00'
                crc16 = self._crc16(cmd_temp[2:])
                cmd += bytes.fromhex(cmd_temp + crc16[-4:])
        else:
            cmd = bytes.fromhex('5A 00 01 21 16 01 00 00 EC 4B')
        self.q_cmd.put(cmd)
        time.sleep(1)
        for k, v in self.is_online.items():
            if not v:
                print('%s is offline' % k)
        check_online = threading.Timer(interval=5, function=self._check_online)
        check_online.start()

    def _send_recv(self):
        while True:
            if not self.q_cmd.empty():
                cmd = self.q_cmd.get()
                self._socket.send(cmd)
            else:
                try:
                    data = self._socket.recv(1024)
                    # print(data)
                    self._analyze_recv_data(data=data)
                except socket.timeout:
                    print('times out')
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
        while end < len_all_data:
            head = data[start:start + 5]
            if head == bytes.fromhex('5A 00 01 %s 00' % mask):
                addr_num = data[(start + 5): (start + 6)] if self.is_rs485 else b'\x00'
                len_data = int.from_bytes(data[(start + 5 + hold_bit):(start + 7 + hold_bit)], byteorder='big', signed=False)
                len_epc = int.from_bytes(data[(start + hold_bit + 7):(start + hold_bit + 9)], byteorder='big', signed=False)
                epc = data[(start + hold_bit + 9):(start + hold_bit + 9 + len_epc)]
                ant = data[(start + 9 + len_epc + 2 + hold_bit):(start + 9 + len_epc + 2 + 1 + hold_bit)]
                print('(EPC, ant, addr_num)--(%s, %s, %s)' % (epc, ant, addr_num))
                with self.lock:
                    if epc not in [epc_ant[0] for epc_ant in self.current_epcs]:
                        self.current_epcs.append((epc, ant, addr_num))
                    # if epc in self.current_epcs.keys():
                    #     if ant in self.current_epcs[epc]:
                    #         self.current_epcs[epc][ant] += 1 if self.current_epcs[epc][ant] < 255 else 0
                    #     else:
                    #         self.current_epcs[epc][ant] = 1
                    # else:
                    #     self.current_epcs[epc] = {ant: 1}
                start += (5 + 2 + len_data + 2 + hold_bit)
                end = start
            elif head == bytes.fromhex('5A 00 01 %s 02' % mask):
                start += (5 + 5 + hold_bit)
                end = start
            elif head == bytes.fromhex('5A 00 01 21 16'):
                print('data=', data)
                num = data[8:9].hex()
                with self.lock:
                    self.is_online[num] = True
                print('%s it is online' % num)
                print(self.is_online)
                break
            else:
                break

    def _get_current_epc(self):
        print(self.current_epcs)
        with self.lock:
            self.current_epcs.clear()

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
        time.sleep(1)
        self._stop()
        thd_auto_inventory = threading.Timer(interval=2, function=self._inventory)
        thd_auto_inventory.start()

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


if __name__ == '__main__':
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
            if client_addr == ('192.168.0.97', 23):
                thr = Rfid2000FH(client_sock)
                if thr is not None:
                    thr.daemon = True
                    thr.start()
    finally:
        server_sock.close()
