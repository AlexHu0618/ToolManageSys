# 只要连接断开就会退出线程

import threading
from operator import methodcaller
import socket
from ctypes import *
import time
from app.myLogger import mylogger
from app.globalvar import *
import copy
from queue import Queue
import os
from binascii import *
from crcmod import *
import datetime

from util.hkws import base_adapter
from util.hkws.model import alarm
from util.hkws.model.base import *
from threading import RLock

from database.models2 import Entrance, User, Role
from settings.config import config_parser as conpar


class GravityShelf(threading.Thread):
    """
        1.frame: Addr + Func + Register + Data + Check
        2、地址从1-63，地址0用于广播，按地址大小进行返回；
    """
    intervals = {'0': 0.0001, '1': 0.0002, '2': 0.0005, '3': 0.001, '4': 0.002, '5': 0.005, '6': 0.01, '7': 0.02,
                 '8': 0.05, '9': 0.1, 'a': 0.2, 'b': 0.5, 'c': 1, 'd': 2, 'e': 5, 'A': 0.2, 'B': 0.5, 'C': 1,
                 'D': 2, 'E': 5}

    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid, addr_nums):
        threading.Thread.__init__(self)
        self.BUFFSIZE = 1024
        self.all_id = ()
        self.tcp_socket = tcp_socket
        self.addr_serial = {}
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.queue_push_data = queue_push_data
        self.addr = addr
        self.storeroom_id = storeroom_id
        self.frequency = 1  # secends
        self.uuid = uuid
        self.timeout_count = 0
        self.addr_nums = addr_nums
        self.precision = 10  # g

    def run(self):
        self.precision = conpar.read_yaml_file('configuration')['gravity_precision']
        data_buff = {}
        self._initial_data(data_buff)
        cursec = 0
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=SUCCESS, eq_type=1, data={'rsl': rsl}, source=self.addr, msg_type=4,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec % 10 == 0:
                        self._check_data_update(data_buff=data_buff)
                        time.sleep(1)
                    else:
                        pass
            except Exception as e:
                print(e)
                mylogger.error(e)
        print('网络断开啦，子线程%s要关闭了！' % threading.current_thread().name)

    def _initial_data(self, data_buff: dict):
        rsl = self.readAllInfo()
        if rsl is not None:
            for i in rsl:
                g = self.readWeight(i)
                data_buff[i] = g
            print('GravityShelf--', self.uuid, ' initial: ', data_buff)

    def _check_data_update(self, data_buff):
        rsl = self.readAllInfo()
        all_weight = {}
        if rsl is not None and len(rsl) >= len(data_buff):
            for i in rsl:
                curr_weight = self.readWeight(i)
                if i not in data_buff.keys() or curr_weight != data_buff[i] and (abs(curr_weight - data_buff[i]) > self.precision):
                    print('(curr_weight - data_buff[i])--%d - %d = %d' % (curr_weight, data_buff[i], (curr_weight - data_buff[i])))
                    data = {'addr_num': i, 'value': curr_weight - data_buff[i], 'is_increased': True if curr_weight - data_buff[i] > 0 else False, 'total': curr_weight}
                    pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=1, data=data, source=self.addr, msg_type=3,
                                          storeroom_id=self.storeroom_id, eq_id=self.uuid)
                    self.queue_push_data.put(pkg)
                    data_buff[i] = curr_weight
                    # print('Gravity data update--', data)
                all_weight[i] = curr_weight
            print(time.asctime(), 'G--getAllInfo: ', all_weight)

    def readWeight(self, addr='01'):
        cmd_f = bytes.fromhex(addr + '05 02 05')
        lcr = sum(cmd_f) % 256
        cmd = cmd_f + lcr.to_bytes(length=1, byteorder='big', signed=False)
        data = self.getData(cmd)
        code = data.hex()[9]
        if data is not None:
            if data[:3] == bytes.fromhex(addr + '0602'):
                interval = self.intervals[code] if code in self.intervals.keys() else 1
                scale = int.from_bytes(data[5:8], byteorder='big', signed=False)
                value = int(scale * interval * 1000)
                return value
            else:
                return ERR_EQUIPMENT_RESP
        else:
            return ERR_EQUIPMENT_RESP

    def getData(self, cmd, multiframe=False):
        self.tcp_socket.settimeout(1)
        data_total = []
        try:
            self.tcp_socket.send(cmd)

            if multiframe:
                # 等待最多64个地址返回，平均一个返回10ms
                time.sleep(0.15)
                data = self.tcp_socket.recv(self.BUFFSIZE)
                data_total.append(data)
            else:
                data = self.tcp_socket.recv(self.BUFFSIZE)
            self.timeout_count = 0
        except socket.timeout:
            if multiframe and data_total:
                return data_total
            else:
                self.timeout_count += 1
                if self.timeout_count > 5:
                    self.isrunning = False
                    print('G--%s 等待TCP消息回应超时' % str(self.addr))
                return TIMEOUT
        except (OSError, BrokenPipeError):
            print('Error', 'TCP连接已断开')
            self.isrunning = False
            return None
        except AttributeError:
            print('Error', 'TCP未连接')
            self.isrunning = False
            return None
        except Exception as e:
            print('Error', repr(e))
            return None
        else:
            if len(data) == 0:
                print('Error', 'TCP客户端已断开连接')
                return None
            else:
                return data if not multiframe else data_total

    def readAllInfo(self):
        cmd = b'\x00\x05\x02\x05\x0C'
        datas = self.getData(cmd, True)
        # print('info back:', datas)
        all_id = ()
        if datas is not None and datas != TIMEOUT:
            newdatas = []
            # 防止tcp的粘包问题
            for data in datas:
                d = [data[i * 9:(i + 1) * 9] for i in range(0, int(len(data) / 9))]
                newdatas += d
            for data in newdatas:
                if data[1:3] == bytes.fromhex('06 02'):
                    # bytes to str in hex: b'\01'--'01'
                    id = data[0:1].hex()
                    all_id += (id,)
            self.all_id = all_id
            return self.all_id
        else:
            return None

    def setAddr(self, addr_old, addr_new):
        self.getAllSerials()
        cmd_f = bytes.fromhex('00 63 11') + self.addr_serial[int(addr_old, 16)] + bytes.fromhex(addr_new)
        lcr = sum(cmd_f) % 256
        cmd = cmd_f + lcr.to_bytes(length=1, byteorder='big', signed=False)
        print(cmd)
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[:4] == bytes.fromhex(addr_new + '64 11 05'):
            print('success')
            return SUCCESS
        else:
            print('failed')
            return ERR_EQUIPMENT_RESP

    def getAllSerials(self):
        cmd = b'\x00\x05\x05\x05\x0F'
        data = self.getData(cmd)
        print('data back:', data)
        data_len = len(data)
        if data_len:
            for d in data:
                if d[1:3] == bytes.fromhex('06 05'):
                    self.addr_serial[d[0]] = d[7:11]
                else:
                    pass
            print(self.addr_serial)
        else:
            pass

    def setParam(self):
        cmd_f = b'\x00\x63\x23\x31\x55\x00\x4e\x20'
        lcr = sum(cmd_f) % 256
        cmd = cmd_f + lcr.to_bytes(length=1, byteorder='big', signed=False)
        data = self.getData(cmd, True)
        print('cmd back:', data)
        # if data[:4] == bytes.fromhex(addr_new + '64 11 05'):
        #     print('success')
        #     return SUCCESS
        # else:
        #     print('failed')
        #     return ERR_EQUIPMENT_RESP


    def getAllParams(self):
        cmd = b'\x00\x05\x23\x05\x2D'
        datas = self.getData(cmd, True)
        print('getAllParams:', datas)
        # all_id = ()
        # if datas is not None:
        #     newdatas = []
        #     # 防止tcp的粘包问题
        #     for data in datas:
        #         d = [data[i * 9:(i + 1) * 9] for i in range(0, int(len(data) / 9))]
        #         newdatas += d
        #     for data in newdatas:
        #         if data[1:3] == bytes.fromhex('06 23'):
        #             # bytes to str in hex: b'\01'--'01'
        #             id = data[0:1].hex()
        #             all_id += (id,)
        #     self.all_id = all_id
        #     return self.all_id
        # else:
        #     return ERR_EQUIPMENT_RESP


class RfidR2000(threading.Thread):
    """
    1、RFID R2000普通版
    2、frame struct: Head(0xA0) + Len + Addr + Cmd + Data + Check
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid):
        threading.Thread.__init__(self)
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr_num = '01'
        self.ant_count = 8
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.addr = addr
        self.storeroom_id = storeroom_id
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()
        self.uuid = uuid
        self.ants = ['00', '01', '02', '03', '04', '05', '06', '07']
        self.data_buff = list()
        self.timeout_count = 0

    def run(self):
        self._initial_data()
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=SUCCESS, eq_type=2, data={'rsl': rsl}, source=self.addr, msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec % 10 == 0:
                        self._check_data_update()
                        # print('R--inventory: ', rsl)
                    else:
                        pass
            except Exception as e:
                print(e)
            finally:
                self.lock.release()
            # time.sleep(10)
            # print('RFID_R2000 back data, storeroom_id= ', self.storeroom_id)

    def _initial_data(self):
        self.reset_inv_buf()
        for ant in self.ants.copy():
            rsl = self.inventory(ant_id=ant)
            if rsl == -1:
                self.ants.remove(ant)
        rsl_data = self.getAndResetBuf()
        if rsl_data is not None:
            self.data_buff += rsl_data
        print('R2000--', self.uuid, ' current EPCs: ', self.data_buff)

    def _check_data_update(self):
        try:
            for ant in self.ants:
                rsl = self.inventory(ant_id=ant)
            rsl_data = self.getAndResetBuf()
            # print('old EPCs: ', self.data_buff)
            # print('new EPCs: ', rsl_data)
            if rsl_data is not None:
                diff_epcs = list(set(epc[0] for epc in rsl_data) ^ set(epc[0] for epc in self.data_buff))
                # print(diff_epcs)
                if diff_epcs:
                    is_increase = True if len(rsl_data) > len(self.data_buff) else False
                    diff = [epc_ant for epc_ant in rsl_data if epc_ant[0] in diff_epcs] if is_increase else [epc_ant for epc_ant in self.data_buff if epc_ant[0] in diff_epcs]
                    data = {'epcs': diff, 'is_increase': is_increase}
                    pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=2, data=data, source=self.addr, msg_type=3,
                                          storeroom_id=self.storeroom_id, eq_id=self.uuid)
                    self.queue_push_data.put(pkg)
                    self.data_buff = rsl_data
        except Exception as e:
            print('R2000 exception: ', e)

    def check(self, cmd_f):
        # complement ---- (~sum + 1)
        cmd = bytes.fromhex(cmd_f)
        check = (sum(cmd) ^ 0xFF) + 1
        check_hex = bytes.fromhex(hex(check)[-2:])
        return check_hex

    def count_frame(self, data):
        if data[0:4] == bytes.fromhex('A0 04' + self.addr_num + '90'):
            return 1
        else:
            tag_count = int.from_bytes(data[4:6], byteorder='big', signed=False)
            all_bytes = (int(data[1]) + 2) * tag_count
            frame_count = all_bytes // self.BUFFSIZE
            return frame_count if all_bytes % self.BUFFSIZE == 0 else frame_count + 1

    def getData(self, cmd, multiframe=False):
        self.tcp_socket.settimeout(1)
        data_total = b''
        try:
            self.tcp_socket.send(cmd)
            # print('RFID2000 cmd send: ', cmd)

            if multiframe:
                isfirst = True
                num = 0
                count = 0
                while True:
                    data = self.tcp_socket.recv(self.BUFFSIZE)
                    num += 1
                    if isfirst:
                        count = self.count_frame(data)
                        # print('count: ', count)
                        isfirst = False
                        data_total += data
                    if num == count:
                        break
            else:
                data = self.tcp_socket.recv(self.BUFFSIZE)
        except socket.timeout:
            if multiframe and data_total:
                return data_total
            else:
                self.timeout_count += 1
                if self.timeout_count > 60:
                    self.isrunning = False
                    print('R--%s 等待TCP消息回应超时' % str(self.addr))
                return TIMEOUT
        except (OSError, BrokenPipeError):
            print('Error', 'TCP连接已断开')
            self.isrunning = False
            return None
        except AttributeError:
            print('Error', 'TCP未连接')
            self.isrunning = False
            return None
        except Exception as e:
            print('Error', repr(e))
            return None
        else:
            if len(data) == 0:
                print('Error', 'TCP客户端已断开连接')
                return None
            else:
                return data if not multiframe else data_total

    def setReaderAddr(self, addr_new):
        cmd_f = 'A0 04' + self.addr_num + '73' + addr_new
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        print(cmd)
        data = self.getData(cmd, False)
        if data[0:5] == bytes.fromhex('A0 04' + self.addr_num + '73 10'):
            self.addr_num = addr_new
            return SUCCESS
        else:
            return ERR_EQUIPMENT_RESP

    def setOutputPower(self, num='00', value=30):
        powers = self.getOutputPower()
        if powers:
            powers[int(num)] = value
            cmd_len = '0B' if self.ant_count == 8 else '07'
            cmd_f = 'A0 ' + cmd_len + self.addr_num + '76 ' + ' '.join(hex(p)[-2:] if p > 16 else ('0' + hex(p)[-1:]) for p in powers)
            print(cmd_f)
            check = self.check(cmd_f)
            cmd = bytes.fromhex(cmd_f) + check
            data = self.getData(cmd, False)
            print('cmd back:', data)
            if data[0:5] == bytes.fromhex('A0 04' + self.addr_num + '76 10'):
                return SUCCESS
            else:
                return ERR_EQUIPMENT_RESP
        else:
            return ERR_EQUIPMENT_RESP

    def getOutputPower(self):
        cmd_f = 'A0 03 ' + self.addr_num + ' 97' if self.ant_count == 8 else ' 77'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        # print('cmd back:', data)
        if data[0:4] == bytes.fromhex('A0 04' + self.addr_num + ' 97' if self.ant_count == 8 else ' 77'):
            power = data[4]
            return [power for i in range(self.ant_count)]
        elif data[0:4] == bytes.fromhex('A0' + ('0B' if self.ant_count == 8 else '07') + self.addr_num + ' 97' if self.ant_count == 8 else ' 77'):
            return [data[i+4] for i in range(self.ant_count)]
        else:
            return ERR_EQUIPMENT_RESP

    def getWorkAntenna(self):
        cmd_f = 'A0 03' + self.addr_num + '75'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        print(data)
        if data[0:4] == bytes.fromhex(('A0 04' + self.addr_num + '75')):
            ant_id = data[4]
            return ant_id
        else:
            return ERR_EQUIPMENT_RESP

    def setWorkAntenna(self, ant_id='00'):
        cmd_f = 'A0 04' + self.addr_num + '74' + ant_id
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        if data is not None and data != TIMEOUT:
            if data[0:5] == bytes.fromhex(('A0 04' + self.addr_num + '74 10')):
                return True
        else:
            return False

    def inventory(self, ant_id='00'):
        rsl = self.setWorkAntenna(ant_id)
        if rsl:
            cmd_repeat = '05'
            cmd_f = 'A0 04' + self.addr_num + '80' + cmd_repeat
            check = self.check(cmd_f)
            cmd = bytes.fromhex(cmd_f) + check
            data = self.getData(cmd, False)
            if data != TIMEOUT or data is not None:
                if data[0:5] == bytes.fromhex('A0 0C' + self.addr_num + '80' + ant_id):
                    tag_count = int.from_bytes(data[5:7], byteorder='big', signed=False)
                    # print('ant(%s) tag_count: %d' % (data[4], tag_count))
                    return tag_count
                elif data[0:5] == bytes.fromhex('A0 04' + self.addr_num + '80 22'):
                    return -1
                else:
                    return None
            else:
                return None
        else:
            return None

    def getAndResetBuf(self):
        cmd_f = 'A0 03' + self.addr_num + '90'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, True)
        # print('cmd back:', data)
        if data != b'' and data != TIMEOUT:
            if data[0:4] == bytes.fromhex('A0 04' + self.addr_num + '90'):
                mylogger.warning('%s ErrorCode: %s' % (str(self.addr), hex(data[4])))
                return []
            elif data[0:4] == bytes.fromhex('A0 04' + self.addr_num + '93'):
                return None
            else:
                # 截取每条数据
                frames = []
                length = int(data[1])
                tag_count = int.from_bytes(data[4:6], byteorder='big', signed=False)
                start = 0
                for i in range(tag_count):
                    end = start + length + 2
                    frames.append(data[start:end])
                    start = end
                # 提取EPC
                epcs = []
                for f in frames:
                    data_len = f[6]
                    epc = f[9:5 + data_len]
                    mask = b'\x03'
                    freq_ant = f[7 + data_len + 1:7 + data_len + 2]
                    ant = bytes([freq_ant[0] & mask[0]])
                    epc_ant = (epc, ant, self.addr_num)
                    epcs.append(epc_ant)
                self.reset_inv_buf()
                return epcs
        else:
            return None

    def reset_inv_buf(self):
        cmd_f = 'A0 03 ' + self.addr_num + '93'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        # print('cmd back:', data)


# class RfidJH2880(object):
#     """
#         (未经过测试)
#         1.frame: Head(0xBB) + Type + Cmd + Len + Data + Check + End(0x7E)
#     """
#     def __init__(self, tcp_socket, addr='00'):
#         self.tcp_socket = tcp_socket
#         self.BUFFSIZE = 1024
#         self.addr = addr
#
#     def check(self, cmd_f):
#         cmd = bytes.fromhex(cmd_f)
#         check = sum(cmd) % 256
#         check_hex = hex(check)[-2:]
#         return check_hex
#
#     def getData(self, cmd):
#         self.tcp_socket.send(cmd)
#         data = self.tcp_socket.recv(self.BUFFSIZE)
#         return data
#
#     def setOutputPower(self, value):
#         temp = hex((value * 100) % 65536)[2:]
#         power = temp if len(temp) > 3 else '0' + temp
#         cmd_f = 'BB 00 B6 00 02' + power
#         check = self.check(cmd_f)
#         cmd = cmd_f + check + '7E'
#         data = self.getData(cmd)
#         print('cmd back:', data)
#         if data.hex() == 'BB 01 B6 00 01 00 B8 7E':
#             return True
#         else:
#             return False
#
#     def getOutputPower(self):
#         cmd = 'BB 00 B7 00 00 B7 7E'
#         data = self.getData(cmd)
#         print('cmd back:', data)
#         if data[0:4].hex() == 'BB 01 B7 00 02':
#             power = int.from_bytes(data[5:6], byteorder='big', signed=False)
#             return power/100
#         else:
#             return None
#
#     def setWorkAntenna(self, ant_id='00'):
#         cmd_f = 'BB 00 0F 00 01' + ant_id
#         check = self.check(cmd_f)
#         cmd = cmd_f + check + '7E'
#         data = self.getData(cmd)
#         print('cmd back:', data)
#         if data[0:4].hex() == 'BB 01 0F 00 01':
#             return True
#         else:
#             return False
#
#     def inventory(self, ant_id='00', time='00 0A'):
#         """
#         1. multi-inventory for specified antenna
#         """
#         rsl = self.setWorkAntenna(ant_id)
#         if rsl:
#             cmd_f = 'BB 00 27 00 03 22' + time
#             check = self.check(cmd_f)
#             cmd = cmd_f + check + '7E'
#             self.tcp_socket.send(cmd)
#             while True:
#                 data = self.tcp_socket.recv(self.BUFFSIZE)
#                 if data.hex() == 'BB 01 FF 00 01 15 16 7E':
#                     break
#                 else:
#                     if data[:2].hex() == 'BB 02 22':
#                         pl = int.from_bytes(data[3:4], byteorder='big', signed=False)
#                         rssi = data[5].hex()
#                         pc = data[6:7].hex()
#                         epc = data[8:(8 + pl - 5)]
#                         print('rssi pc epc', rssi, pc, epc)
#                         continue
#                     else:
#                         pass
#         else:
#             print('Fail to inventory')


class Indicator(threading.Thread):
    """
        1.frame: Head(0x7E) + Addr + Cmd + Len + Data + Check + End(0x68)
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, storeroom_id, uuid, addr_nums):
        threading.Thread.__init__(self)
        self.addr = addr
        self.storeroom_id = storeroom_id
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr_nums = addr_nums
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.lock = threading.RLock()
        self.uuid = uuid

    def run(self):
        num = 0
        cursec = 0
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=SUCCESS, eq_type=1, data={'rsl': rsl}, source=self.addr, msg_type=6,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        num = num + 1 if num < 1000 else 0
                        for i in self.addr_nums:
                            rsl = self.showNum(num, i)
                            activate = True if num % 2 == 0 else False
                            self.onLed(activate=activate, pos='up', addr=i)
                            self.onLed(activate=not activate, pos='down', addr=i)
                            # if rsl:
                            #     print('L(%s)--showNum: %i' % (i, num))
                    else:
                        pass
            except Exception as e:
                print(e)
                mylogger.error(e)
        print('网络断开啦，子线程%s要关闭了！' % threading.current_thread().name)

    def check(self, cmd_f):
        if isinstance(cmd_f, bytes):
            cmd = cmd_f
        else:
            cmd = bytes.fromhex(cmd_f)
        check = sum(cmd) % 256
        check_hex = hex(check)[-2:] if check > 15 else '0' + hex(check)[-1:]
        return check_hex

    def getData(self, cmd):
        self.tcp_socket.settimeout(1)
        try:
            self.tcp_socket.send(cmd)
            data = self.tcp_socket.recv(self.BUFFSIZE)
            # print('LCD BACK DATA: ', data)
        except socket.timeout:
            # print('L--Warning', '等待TCP消息回应超时')
            return None
        except (OSError, BrokenPipeError):
            print('Error', 'TCP连接已断开')
            return None
        except AttributeError:
            print('Error', 'TCP未连接')
            return None
        except Exception as e:
            print('Error', repr(e))
            return None
        else:
            if len(data) == 0:
                print('Error', 'TCP客户端已断开连接')
                return None
            else:
                return data

    def checkBtn(self, addr='01'):
        cmd_f = '7E' + addr + '00 00'
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        if data[0:4] == bytes.fromhex('7E' + addr + '00 01'):
            return SUCCESS if data[4] == 1 else ERR_EQUIPMENT_RESP
        else:
            return ERR_EQUIPMENT_RESP

    def onLed(self, activate=True, pos='up', addr='01'):
        cmd_acti = '01' if activate else '00'
        cmd_pos = '01' if pos == 'up' else '02'
        cmd_f = '7E' + addr + '01 02' + cmd_pos + cmd_acti
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        if data is not None:
            if data[0:4] == bytes.fromhex('7E' + addr + '01 01'):
                return SUCCESS if data[4] == 0 else ERR_EQUIPMENT_RESP
            else:
                return ERR_EQUIPMENT_RESP
        else:
            return TIMEOUT

    def showNum(self, num: int, addr='01'):
        number = num if num < 1000 else 999
        cmd_num = str(number).zfill(4)
        cmd_f = '7E' + addr + '02 02' + cmd_num
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        if data is not None:
            if data[0:4] == bytes.fromhex('7E' + addr + '02 01'):
                return SUCCESS if data[4] == 0 else ERR_EQUIPMENT_RESP
            else:
                return ERR_EQUIPMENT_RESP
        else:
            return TIMEOUT

    def onBacklight(self, activate=True, addr='01'):
        cmd_data = '01' if activate else '00'
        cmd_f = '7E' + addr + '04 01' + cmd_data
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        if data[0:4] == bytes.fromhex('7E' + addr + '04 01'):
            return SUCCESS if data[4] == 0 else ERR_EQUIPMENT_RESP
        else:
            return ERR_EQUIPMENT_RESP

    def showText(self, contents=[], addr='01'):
        content = [bytes(cont, 'gb2312') if cont else b'' for cont in contents]
        cmd_l1 = b'\x01' + (len(content[0]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[0] + b'\x00'
        cmd_l2 = b'\x02' + (len(content[1]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[1] + b'\x00'
        cmd_l3 = b'\x03' + (len(content[2]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[2] + b'\x00'
        cmd_l4 = b'\x04' + (len(content[3]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[3] + b'\x00'
        length = len(cmd_l1 + cmd_l2 + cmd_l3 + cmd_l4)
        cmd_len = hex(length)[-2:] if length > 15 else ('0' + hex(length)[-1:])
        cmd_f = bytes.fromhex('7E' + addr + '03' + cmd_len) + cmd_l1 + cmd_l2 + cmd_l3 + cmd_l4
        print(cmd_f)
        check = self.check(cmd_f)
        cmd = cmd_f + bytes.fromhex(check + '68')
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('7E' + addr + '03 01'):
            return SUCCESS if data[4] == 0 else ERR_EQUIPMENT_RESP
        else:
            return ERR_EQUIPMENT_RESP


class EntranceZK(threading.Thread):
    """
    中控门禁网络断开后会自动重连，重连后返回最后一个刷门禁的事件
    """
    path_cur = os.path.abspath(os.path.dirname(__file__))
    lib = cdll.LoadLibrary(path_cur + "/../util/libs/zk_lib/libplcommpro.so")
    counter = 0

    def __init__(self, addr: tuple, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid):
        threading.Thread.__init__(self)
        self.ip = addr[0]
        self.port = addr[1]
        self.storeroom_id = storeroom_id
        self.uuid = uuid
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()
        self.current_data = None
        self.is_online = False
        self.lib = EntranceZK.lib
        self.handle = self.lib.Connect(b'protocol=TCP,ipaddress=' + bytes(self.ip, encoding='utf8') +
                                  b',port=' + bytes(str(self.port), encoding='utf8') +
                                  b',timeout=1000,passwd=')
        EntranceZK.counter += 1

    def run(self):
        """
        每隔10s刷新一次数据
        :return:
        """
        print('handle========', self.handle)
        if self.handle > 0:
            self.is_online = True
            cursec = 0
            while self.isrunning:
                try:
                    if not self.queuetask.empty():
                        task, args = self.queuetask.get()
                        rsl = methodcaller(task, *args)(self)
                        if rsl is not None:
                            pkg = TransferPackage(code=SUCCESS, eq_type=3, data={'rsl': rsl}, source=(self.ip, self.port),
                                                  msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                            self.queuersl.put(pkg)
                            self.event.set()
                    else:
                        localtime = time.localtime(time.time())
                        if localtime.tm_sec != cursec:
                            cursec = localtime.tm_sec
                            rsl = self.getNewEvent()
                            if rsl is not None:
                                if len(rsl) > 0:
                                    if self.current_data is not None:
                                        if rsl != self.current_data:
                                            data = {'user': rsl[0], 'raw': rsl}
                                            pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=3, data=data, source=(self.ip, self.port),
                                                                  msg_type=3, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                                            self.queue_push_data.put(pkg)
                                            print('gate--getNewEvent: ', rsl)
                                            with self.lock:
                                                self.current_data = copy.deepcopy(rsl)
                                    else:
                                        with self.lock:
                                            self.current_data = copy.deepcopy(rsl)
                                else:
                                    # 非注册用户
                                    pass
                                # 若为离线状态，则更新为在线
                                if not self.is_online:
                                    print('Entrance_zk--(%s, %d) was online' % (self.ip, self.port))
                                    mylogger.info('Entrance_zk--(%s, %d) was online' % (self.ip, self.port))
                                    self.is_online = True
                                    self._update_status_db(is_online=True)
                            else:
                                # 读取错误,所有错误码均作为离线处理
                                if self.is_online:
                                    print('Entrance_zk--(%s, %d) was offline' % (self.ip, self.port))
                                    mylogger.error('Entrance_zk--(%s, %d) was offline' % (self.ip, self.port))
                                    self.is_online = False
                                    self._update_status_db(is_online=False)
                        else:
                            pass
                except Exception as e:
                    print('except from EntranceZK--', e)
                    mylogger.error(e)
                    break
            mylogger.warning('Entrance_zk (%s, %d) try to offline' % (self.ip, self.port))
            self.lib.Disconnect(self.handle)
        elif self.handle < 0:
            self.lib.Disconnect(self.handle)
        else:
            mylogger.warning('Fail to init Entreance_zk connect (%s, %d)' % (self.ip, self.port))

    def _update_status_db(self, is_online: bool):
        entrance = Entrance.by_addr(self.ip, self.port)
        if entrance is not None:
            entrance.update('status', int(is_online))
            cur_dt = str(datetime.datetime.now())
            entrance.update('last_offline_time', cur_dt)
        else:
            mylogger.warning('Not found object(%s,%d) from DB-entrance while updating' % (self.ip, self.port))

    # def _conn(self):
    #     handle = self.lib.Connect(b'protocol=TCP,ipaddress=' + bytes(self.ip, encoding='utf8') +
    #                               b',port=' + bytes(str(self.port), encoding='utf8') +
    #                               b',timeout=2000,passwd=')
    #     self.handle = handle
    #     return True if handle > 0 else False

    # @staticmethod
    # def conn(ip: str, port: int):
    #     handle = EntranceZK.lib.Connect(b'protocol=TCP,ipaddress=' + bytes(ip, encoding='utf8') +
    #                                    b',port=' + bytes(str(port), encoding='utf8') +
    #                                    b',timeout=2000,passwd=')
    #     if handle == 0:
    #         print('Fail to Connect.')
    #         return None
    #     else:
    #         return handle
    #
    # @staticmethod
    # def disconn(handle):
    #     EntranceZK.lib.Disconnect(handle)

    def getDeviceParam(self):
        buff = create_string_buffer("b".encode('utf-8'), 1024)
        rsl = self.lib.GetDeviceParam(self.handle, byref(buff), 1024, bytes('IPAddress,ReaderCount,MThreshold'.encode('utf-8')))
        if rsl == 0:
            return buff.value
        else:
            return rsl

    def getNewEvent(self):
        count = self.lib.GetDeviceDataCount(self.handle, bytes('transaction'.encode('utf-8')))
        if count >= 0:
            size = count * 2000
            buff = create_string_buffer("q".encode('utf-8'), size)
            filter1 = b'Index=' + bytes(str(count), encoding='utf8')
            rsl = self.lib.GetDeviceData(self.handle, byref(buff), size, bytes('transaction'.encode('utf-8')), b'*', filter1, b'')
            if rsl >= 0:
                last_record = buff.value.split(b'\r\n')[1]
                # print(last_record)
                recode_list = last_record.split(b',')
                eventtype = recode_list[3]
                user = str(recode_list[0], encoding='gb18030')
                if eventtype == b'0':
                    # print('\033[1;33m USER--', user, ' is authed....\033[0m')
                    resp = 'Auth: ' + str(last_record, encoding='gb18030')
                    return [user, resp]
                else:
                    # 非注册用户
                    mylogger.warning('(%s, %d)--GetDeviceData() get no registerd user' % (self.ip, self.port))
                    return []
            else:
                mylogger.error('(%s, %d)--GetDeviceData() get error code %d' % (self.ip, self.port, rsl))
                return None
        else:
            mylogger.error('(%s, %d)--GetDeviceDataCount() get error code %d' % (self.ip, self.port, count))
            return None

    def add_new_user(self, user_code, fingerprint_template: bytes, username='', card_num=''):
        """
        1、设置user表；
        2、设置templatev10表；
        3、设置userauthorize表；
        :param user_code:
        :param username:
        :param fingerprint_template:
        :param card_num:
        :return:
        """
        # set user
        p_table = create_string_buffer(b'user')
        data = 'Pin=%s\tCardNo=%s\tName=%s\tDisable=0' % (user_code, card_num, username)
        str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
        rsl_user = self.lib.SetDeviceData(self.handle, p_table, str_buf, b'')

        # set fingerprint
        finger_id = 3  # 0~9, default=3
        # with open(fpath_template, "r") as f:  # 打开文件
        #     template = f.read()  # 读取文件
        template = str(fingerprint_template, encoding='utf-8')
        data = 'Pin=%s\tFingerID=%d\tTemplate=%s\tValid=1' % (user_code, finger_id, template)
        p_table = create_string_buffer(b'templatev10')
        str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
        rsl_fgp = self.lib.SetDeviceData(self.handle, p_table, str_buf, b'')

        # set userauthorize
        p_table = create_string_buffer(b'userauthorize')
        data = 'Pin=%s\tAuthorizeTimezoneId=1\tAuthorizeDoorId=1' % user_code
        str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
        rsl_auth = self.lib.SetDeviceData(self.handle, p_table, str_buf, b'')

        if rsl_user == 0 and rsl_fgp == 0 and rsl_auth == 0:
            return True
        else:
            return False

    def delete_user(self, user_code: str):
        """
        1、只要任意一个表删除成功即认为删除成功；
        :param user_code:
        :return:
        """
        tables = [b'user', b'fingerprint', b'userauthorize']
        rsl_all = False
        pin = user_code
        filter2 = b'Pin=' + bytes(pin, encoding='utf8')
        for t in tables:
            p_table = create_string_buffer(t)
            rsl = self.lib.DeleteDeviceData(self.handle, p_table, filter2, b'')
            if rsl >= 0:
                rsl_all = True
        return rsl_all

    def __del__(self):
        EntranceZK.counter -= 1
        print('EntranceZK.counter==========', EntranceZK.counter)


# class HKVision(threading.Thread):
#     ip_obj_dic = {}  # {ip: {'obj': obj, 'user_id': user_id}}
#     adapter = None
#     obj_counter = 0
# 
#     def __init__(self, addr, queuetask, queuersl, queue_push_data, storeroom_id, uuid):
#         threading.Thread.__init__(self)
#         self.ip = addr[0]
#         self.port = addr[1]
#         self.username = 'admin'
#         self.password = 'abcd1234'
#         self.storeroom_id = storeroom_id
#         self.uuid = uuid
#         self.queuetask = queuetask
#         self.queuersl = queuersl
#         self.queue_push_data = queue_push_data
#         self.user_id = None
#         self.isrunning = True
#         self.lock = RLock()
#         HKVision.ip_obj_dic[self.ip] = {'obj': self}
#         HKVision.obj_counter += 1
#         self.alarm_handle = None
# 
#     def run(self):
#         try:
#             # print('thread name--', threading.current_thread().name)
#             if self._login():
#                 self._set_exception_cb()
#                 self._get_alarm()
#                 print('Hkvision success')
#                 while self.isrunning:
#                     time.sleep(10)
#                 self._close_alarm()
#                 HKVision.adapter.logout(self.user_id)
#             else:
#                 print('SDK init failed')
#         except Exception as e:
#             mylogger.error('Hkvision %s got exception' % self.ip)
#         finally:
#             self._del_self()
# 
#     def _del_self(self):
#         # print('del obj')
#         # print('thread name--', threading.current_thread().name)
#         if self.ip in HKVision.ip_obj_dic.keys():
#             del HKVision.ip_obj_dic[self.ip]
#             HKVision.obj_counter -= 1
#         if HKVision.obj_counter == 0 and HKVision.adapter is not None:
#             HKVision.adapter.sdk_clean()
# 
#     def _login(self):
#         """
#         1、如果未初始化SDK适配器，则加载并初始化；
#         2、用户登录门禁主机；
#         :return:
#         """
#         if HKVision.adapter is None:
#             HKVision.adapter = base_adapter.BaseAdapter()
#             # rsl = HKVision.adapter.add_init_sdk()
#             # if not rsl:
#             #     print('Fail to initial SDK')
#             #     return False
#         userId = HKVision.adapter.common_start(ip=self.ip, port=self.port, user=self.username, password=self.password)
#         if userId < 0:
#             mylogger.warning('Fail to init Entreance_hk connect (%s, %d)' % (self.ip, self.port))
#             return False
#         self.user_id = userId
#         HKVision.ip_obj_dic[self.ip]['user_id'] = self.user_id
#         print('Entrance_hk--(%s, %d) was online' % (self.ip, self.port))
#         mylogger.info('Entrance_hk--(%s, %d) was online' % (self.ip, self.port))
#         return True
# 
#     def _get_alarm(self):
#         data = HKVision.adapter.setup_alarm_chan_v31(self.message_call_back, self.user_id)
#         # print("设置回调函数结果", data)
#         # 布防
#         alarm_result = self.adapter.setup_alarm_chan_v41(self.user_id)
#         # print("设置人脸v41布防结果", alarm_result)
#         self.alarm_handle = alarm_result
# 
#     def _close_alarm(self):
#         HKVision.adapter.close_alarm(self.alarm_handle)
# 
#     def _set_exception_cb(self):
#         rsl = HKVision.adapter.set_exceptioln_call_back(None, None, self.exception_call_back, self.user_id)
#         # print('set_exception_cb', rsl)
# 
#     @staticmethod
#     @CFUNCTYPE(h_BOOL, h_LONG, POINTER(alarm.NET_DVR_ALARMER), POINTER(h_CHAR), h_DWORD, h_VOID_P)
#     def message_call_back(lCommand,
#                           pAlarmer,
#                           pAlarmInfo,
#                           dwBufLen,
#                           pUser):
#         # print("lCommand:{},pAlarmer:{},pAlarmInfo:{},dwBufLen:{}".format(lCommand, pAlarmer, pAlarmInfo, dwBufLen))
#         if lCommand == 0x5002:
#             # 门禁主机报警信息
#             # print('Command=', lCommand)
#             alarmer = alarm.NET_DVR_ALARMER()
#             memmove(pointer(alarmer), pAlarmer, sizeof(alarmer))
#             ip = bytearray(alarmer.sDeviceIP).decode(encoding='utf-8')
#             # print('IP--', ip)
#             alarm_info = alarm.NET_DVR_ACS_ALARM_INFO()
#             memmove(pointer(alarm_info), pAlarmInfo, sizeof(alarm_info))
#             major_code = alarm_info.dwMajor
#             minor_code = alarm_info.dwMinor
#             if major_code == 5 and minor_code == 38:
#                 # print(hex(alarm_info.dwMajor))
#                 # print(hex(alarm_info.dwMinor))
#                 cardno = bytearray(alarm_info.struAcsEventInfo.byCardNo).decode(encoding='utf-8')
#                 user_code = alarm_info.struAcsEventInfo.dwEmployeeNo
#                 # print('user--%s(CARD--%s) was in' % (user_code, cardno))
#                 # print(alarm_info.byAcsEventInfoExtend)
#                 # print(alarm_info.byAcsEventInfoExtendV20)
#                 HKVision.ip_obj_dic[ip]['obj'].set_auth_info(user_code, cardno)
#                 # # 退出该IP的海康威视对象
#                 # if user_code == 1 or user_code == '1':
#                 #     HKVision.ip_obj_dic[ip]['obj'].stop()
#         return True
# 
#     @staticmethod
#     @CFUNCTYPE(None, h_DWORD, h_BYTE, h_BYTE, h_VOID_P)
#     def exception_call_back(dwType,
#                             lUserID,
#                             lHandle,
#                             pUser):
#         # print(hex(dwType), lUserID, lHandle, pUser)
#         if hex(dwType) == '0x8000':
#             # 网络断开异常
#             for k, v in HKVision.ip_obj_dic.items():
#                 if v['user_id'] == lUserID:
#                     v['obj'].stop()
# 
#     def set_auth_info(self, user_code, cardno):
#         print('(userCode, cardNo)--(%s, %s) was in!' % (user_code, cardno))
#         data = {'user': str(user_code), 'card_id': str(cardno)}
#         pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=5, data=data, source=(self.ip, self.port),
#                               msg_type=3, storeroom_id=self.storeroom_id, eq_id=self.uuid)
#         self.queue_push_data.put(pkg)
# 
#     def stop(self):
#         with self.lock:
#             self.isrunning = False
#         print('Entrance_hk--(%s, %d) was offline' % (self.ip, self.port))
#         mylogger.warning('Entrance_hk--(%s, %d) was offline' % (self.ip, self.port))


class CodeScanner(threading.Thread):
    pass


class ChannelMachineR2000FH(threading.Thread):
    """
       1、RFID R2000跳频版
       2、frame struct: Head(0x5A) + MSG_type + Addr + Len + Data + Check(CRC16)
       """

    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid, addr_nums):
        threading.Thread.__init__(self)
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr_num = b'\x01'
        self.ant_count = 8
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.addr = addr  # (ip, port)
        self.storeroom_id = storeroom_id
        self.uuid = uuid
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()
        self.q_cmd = Queue(50)
        self.current_epcs = list()
        self.data_buff = list()  # [(epc, ant, addr_num), ]
        self.timeout_counter = 0
        self.is_rs485 = True
        self.addr_nums = addr_nums

    def run(self):
        """
        1、主线程负责外部指令处理以及接收处理，子线程负责数据发送；
        2、使用生产消费者模式；
        3、每隔5s从设备读取一次数据更新；
        :return:
        """
        self.tcp_socket.settimeout(1)
        thd_send = threading.Thread(target=self._send_recv)
        # thd_auto_inventory = threading.Timer(interval=5, function=self._inventory_once)
        thd_send.daemon = True
        thd_send.start()
        # thd_auto_inventory.start()
        self._inventory()
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=SUCCESS, eq_type=4, data={'rsl': rsl}, source=self.addr, msg_type=4,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec % 10 == 0:
                        # self._check_data_update()
                        time.sleep(1)
                        # print('R--inventory: ', rsl)
                    else:
                        pass
            except KeyboardInterrupt:
                self.tcp_socket.shutdown(2)
                self.tcp_socket.close()
        print('thread R2000FH is closed.....')

    def start(self):
        self._inventory()

    def stop(self):
        self._stop()

    def _check_data_update(self):
        try:
            with self.lock:
                print('R2000FH old EPCs: ', self.data_buff)
                print('R2000FH new EPCs: ', self.current_epcs)
                if self.current_epcs is not None:
                    diff_epcs = list(set(epc[0] for epc in self.current_epcs) ^ set(epc[0] for epc in self.data_buff))
                    print('R2000FH diff_epcs--', diff_epcs)
                    if diff_epcs:
                        is_increase = True if len(self.current_epcs) > len(self.data_buff) else False
                        diff = [epc_ant for epc_ant in self.current_epcs if
                                epc_ant[0] in diff_epcs] if is_increase else [epc_ant for epc_ant in self.data_buff if
                                                                              epc_ant[0] in diff_epcs]
                        data = {'epcs': diff, 'is_increase': is_increase}
                        pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=4, data=data, source=self.addr, msg_type=3,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queue_push_data.put(pkg)
                    self.data_buff.clear()
                    self.data_buff = [epc_ant for epc_ant in self.current_epcs]
                    self.current_epcs.clear()
        except Exception as e:
            print('R2000FH exception: ', e)

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
                        print('R2000FH--%s times out' % str(self.addr))
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
            pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=4, data=data, source=self.addr, msg_type=3,
                                  storeroom_id=self.storeroom_id, eq_id=self.uuid)
            self.queue_push_data.put(pkg)

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


class RfidR2000FH(threading.Thread):
    """
    1、RFID R2000跳频版
    2、frame struct: Head(0x5A) + MSG_type + Addr + Len + Data + Check(CRC16)
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid, addr_nums):
        threading.Thread.__init__(self)
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr_num = b'\x01'
        self.ant_count = 8
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.addr = addr  # (ip, port)
        self.storeroom_id = storeroom_id
        self.uuid = uuid
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()
        self.q_cmd = Queue(50)
        self.current_epcs = list()
        self.data_buff = list()  # [(epc, ant, addr_num), ]
        self.timeout_counter = 0
        self.is_rs485 = True
        self.addr_nums = addr_nums
        self.all_epc = list()

    def run(self):
        """
        1、主线程负责外部指令处理以及接收处理，子线程负责数据发送；
        2、使用生产消费者模式；
        3、每隔5s从设备读取一次数据更新；
        :return:
        """
        self.tcp_socket.settimeout(1)
        thd_send = threading.Thread(target=self._send_recv)
        thd_auto_inventory = threading.Timer(interval=5, function=self._inventory_once)
        thd_send.daemon = True
        thd_send.start()
        thd_auto_inventory.start()
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=SUCCESS, eq_type=2, data={'rsl': rsl}, source=self.addr, msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec % 10 == 0:
                        self._check_data_update()
                        time.sleep(1)
                        # print('R--inventory: ', rsl)
                    else:
                        pass
            except KeyboardInterrupt:
                self.tcp_socket.shutdown(2)
                self.tcp_socket.close()
        print('thread R2000FH is closed.....')

    def _check_data_update(self):
        try:
            with self.lock:
                # print('R2000FH old EPCs: ', self.data_buff)
                # print('R2000FH new EPCs: ', self.current_epcs)
                if self.current_epcs is not None:
                    diff_epcs = list(set(epc[0] for epc in self.current_epcs) ^ set(epc[0] for epc in self.data_buff))
                    # print('R2000FH diff_epcs--', diff_epcs)
                    if diff_epcs:
                        is_increase = True if len(self.current_epcs) > len(self.data_buff) else False
                        diff = [epc_ant for epc_ant in self.current_epcs if epc_ant[0] in diff_epcs] if is_increase else [epc_ant for epc_ant in self.data_buff if epc_ant[0] in diff_epcs]
                        data = {'epcs': diff, 'is_increase': is_increase}
                        pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=2, data=data, source=self.addr, msg_type=3,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queue_push_data.put(pkg)
                        self.all_epc.clear()
                        self.all_epc.extend([epc[0] for epc in self.current_epcs])
                    self.data_buff.clear()
                    self.data_buff = [epc_ant for epc_ant in self.current_epcs]
                    self.current_epcs.clear()
            print('R2000FH all_epc--', self.all_epc)
        except Exception as e:
            print('R2000FH exception: ', e)

    def _send_recv(self):
        while self.isrunning:
            if not self.q_cmd.empty():
                cmd = self.q_cmd.get()
                self.tcp_socket.send(cmd)
            else:
                try:
                    data = self.tcp_socket.recv(1024)
                    self.timeout_counter = 0
                    self._analyze_recv_data(data=data)
                except socket.timeout:
                    self.timeout_counter += 1
                    if self.timeout_counter > 20:
                        print('R2000FH--%s times out' % str(self.addr))
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
        while end < len_all_data:
            head = data[start:start + 5]
            if head == bytes.fromhex('5A 00 01 %s 00' % mask):
                addr_num = data[(start + 5): (start + 6)] if self.is_rs485 else b'\x00'
                len_data = int.from_bytes(data[(start + 5 + hold_bit):(start + 7 + hold_bit)], byteorder='big', signed=False)
                len_epc = int.from_bytes(data[(start + hold_bit + 7):(start + hold_bit + 9)], byteorder='big', signed=False)
                epc = data[(start + hold_bit + 9):(start + hold_bit + 9 + len_epc)]
                ant = data[(start + 9 + len_epc + 2 + hold_bit):(start + 9 + len_epc + 2 + 1 + hold_bit)]
                # print('(EPC, ant, addr_num)--(%s, %s, %s)' % (epc, ant, addr_num))
                with self.lock:
                    if epc not in [epc_ant[0] for epc_ant in self.current_epcs]:
                        self.current_epcs.append((epc, ant, addr_num))
                # if (epc, ant) not in self.current_epcs.copy():
                #     self.current_epcs.append((epc, ant))
                start += (5 + 2 + len_data + 2 + hold_bit)
                end = start
            elif head == bytes.fromhex('5A 00 01 %s 02' % mask):
                start += (5 + 5 + hold_bit)
                end = start
            else:
                break

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
        
        
class HKVision(threading.Thread):
    """
    使用非回调函数的版本 
    """
    ip_obj_dic = {}  # {ip: {'obj': obj, 'user_id': user_id}}
    adapter = None
    obj_counter = 0

    def __init__(self, addr, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid):
        threading.Thread.__init__(self)
        self.ip = addr[0]
        self.port = addr[1]
        self.username = 'admin'
        self.password = 'abcd1234'
        self.storeroom_id = storeroom_id
        self.uuid = uuid
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.queue_push_data = queue_push_data
        self.user_id = None
        self.isrunning = True
        self.lock = RLock()
        HKVision.ip_obj_dic[self.ip] = {'obj': self}
        HKVision.obj_counter += 1
        self.alarm_handle = None
        self.remote_handle = None
        self.all_user = list()  # [(card_num: bytes, code: int), ]
        self.all_user_temp = list()
        self.interval = 20
        self.finger_print_callback = None
        self.face_callback = None
        self.str_entrance_pw = None
        self.usertype = 3
        self.fp_temp = bytearray()
        self.face_temp = bytearray()
        self.lock = RLock()
        
    def run(self):
        """
        1、初始化当前门禁的用户数据，从DB获取；
        2、定时查询门禁用户卡数据，如有新增用户就查询指纹数据与人脸数据并存入DB创建用户并绑定该门禁，修改all_users；
        3、若有删除用户，删除门禁人脸、指纹与卡数据，并在DB解绑用户与门禁关系，修改all_users；
        4、接收并处理web指令，调用增加或删除用户操作；
        5、设置布防功能实时监听门禁认证通过事件；
        :return:
        """
        self._init()
        try:
            if self._login():
                self._get_alarm()
                # self._set_exception_cb()
                thd = threading.Timer(interval=self.interval, function=self.check_users_from_terminal)
                thd.daemon = True
                thd.start()

                while self.isrunning:
                    time.sleep(2)
                    if not self.queuetask.empty():
                        task, args = self.queuetask.get()
                        rsl = methodcaller(task, *args)(self)
                        if rsl is not None:
                            pkg = TransferPackage(code=SUCCESS, eq_type=3, data={'rsl': rsl}, source=(self.ip, self.port),
                                                  msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                            self.queuersl.put(pkg)
                            self.event.set()
                self._close_alarm()
                HKVision.adapter.logout(self.user_id)
            else:
                print('SDK init failed')
                time.sleep(10)
        except KeyboardInterrupt:
            with self.lock:
                self.isrunning = False
        except Exception as e:
            print(e)
        finally:
            self._del_self()

    def _init(self):
        """
        1、从DB获取该库房的用户；
        :return:
        """
        self.interval = conpar.read_yaml_file('configuration')['hkvision_user_update_interval']
        entrance = Entrance.by_addr(self.ip, self.port)
        if entrance:
            users = entrance.users
            if users:
                for u in users:
                    self.all_user.append((bytes(u.card_id, encoding='utf-8'), int(u.code)))
            # user = User.by_code('666')
            # entrance.users = [user]
            # entrance.save()
        else:
            print('Fail to init all users in entrance(%s, %d)' % (self.ip, self.port))
            mylogger.warning('Fail to init all users in entrance(%s, %d)' % (self.ip, self.port))

    def save_new_user_to_db(self, user_code, card_num, finger_print=None, face_img=None, pw=None, usertype=3):
        """
        1、用户不存在DB，则创建；存在，则判断是否增加指纹和人脸属性；
        2、绑定用户与门禁。
        :return:
        """
        time_curr = datetime.datetime.now()
        user = User.by_code(user_code)
        if not user:
            user = User(login_name=user_code, code=user_code, card_id=card_num, fingerprint=finger_print, avatar=face_img,
                        register_time=time_curr, entrance_password=pw)
            role = Role.by_level(level=usertype)
            user.roles.append(role)
            user.save()
        else:
            if user.entrance_password is None and pw is not None:
                user.update('entrance_password', pw)
            if user.fingerprint is None and len(finger_print) > 0:
                print('update finger')
                user.update('fingerprint', finger_print)
            if user.avatar is None and len(face_img) > 0:
                print('update face')
                user.update('avatar', face_img)
        entrance = Entrance.by_addr(self.ip, self.port)
        if entrance:
            entrance.users.append(user)
            entrance.save()
        else:
            mylogger.warning('Fail to relate entrance(%s, %d)--user(card:%s)' % (self.ip, self.port, user.card_id))

    def build_new_user_to_terminal(self, uuid: str):
        """
        1、设置卡参数；
        2、设置指纹参数；
        3、设置人脸参数;
        4、绑定用户与门禁到DB。
        :return:
        """
        user = User.by_uuid(uuid=uuid)
        bycardno = bytes(user.card_id, encoding='utf-8')
        byname = bytes(user.login_name, encoding='utf-8')
        bycardpw = bytes(user.entrance_password, encoding='utf-8') if user.entrance_password else None
        role = user.roles
        rsl_card = self._set_card_info(bycardno=bycardno, code=int(user.code), byname=byname, bypw=bycardpw, usertype=role[0])
        fingerprint = bytearray(user.fingerprint)  # bytes--bytearray
        rsl_fp = self._set_fingerprint_info(bycardno=bycardno, fp_data=fingerprint)
        face_data = bytearray(user.avatar)
        rsl_face = self._set_face_info(bycardno=bycardno, face=face_data)
        entrance = Entrance.by_addr(self.ip, self.port)
        entrance.users.append(user)
        entrance.save()
        with self.lock:
            self.all_user.append((bycardno, int(user.code)))
        if rsl_card and (rsl_fp and rsl_face):
            mylogger.info('HK entrance--(%s, %d) was success to build new user--%s' % (self.ip, self.port, bycardno))
            return True
        else:
            mylogger.warning('HK entrance--(%s, %d) was failed to build new user--%s' % (self.ip, self.port, bycardno))
            return False

    def del_user_from_web(self, card_num: str):
        """
        1、设置卡参数（byCardValid = 0）进行删除；管理员不能删除
        2、解除用户与门禁绑定关系。
        :param user_code:
        :param card_num:
        :return:
        """
        bycardno = bytes(card_num, encoding='utf-8')
        if self._del_card_info(bycardno=bycardno):
            user_db = User.by_card_id(card_id=card_num)
            if user_db:
                entrance = Entrance.by_addr(self.ip, self.port)
                entrance.users.remove(user_db)
                entrance.save()
            with self.lock:
                for user in self.all_user.copy():
                    if user[0] == bycardno:
                        self.all_user.remove(user)
            print('success to del user from web')
            mylogger.info('HK entrance--(%s, %d) was success to delete user--%s' % (self.ip, self.port, card_num))
            return True
        else:
            print('Fail to del user from web')
            mylogger.warning('HK entrance--(%s, %d) was failed to delete user--%s' % (self.ip, self.port, card_num))
            return False

    # def del_user_from_terminal(self):
    #     """
    #     从DB解除用户与门禁绑定
    #     :return:
    #     """
    #     pass

    def _del_self(self):
        if self.ip in HKVision.ip_obj_dic.keys():
            del HKVision.ip_obj_dic[self.ip]
            HKVision.obj_counter -= 1
        if HKVision.obj_counter == 0 and HKVision.adapter is not None:
            HKVision.adapter.sdk_clean()
        mylogger.info('HK entrance object--(%s, %d) was deleted' % (self.ip, self.port))

    def _login(self):
        """
        1、如果未初始化SDK适配器，则加载并初始化；
        2、用户登录门禁主机；
        :return:
        """
        if HKVision.adapter is None:
            HKVision.adapter = base_adapter.BaseAdapter()
            # rsl = HKVision.adapter.add_init_sdk()
            # if not rsl:
            #     print('Fail to initial SDK')
            #     return False
        userId = HKVision.adapter.common_start(ip=self.ip, port=self.port, user=self.username, password=self.password)
        if userId < 0:
            print('Failed to login')
            mylogger.warning('Fail to login HK entrance--(%s, %d)' % (self.ip, self.port))
            return False
        self.user_id = userId
        HKVision.ip_obj_dic[self.ip]['user_id'] = self.user_id
        return True

    def _get_alarm(self):
        rsl = HKVision.adapter.setup_alarm_chan_v31(self.message_call_back, self.user_id)
        print("设置回调函数结果", rsl)
        if not rsl:
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed to setup alarm callback function, error_code--%d' % (self.ip, self.port, err_code))
        # 布防
        alarm_result = self.adapter.setup_alarm_chan_v41(self.user_id)
        print("设置人脸v41布防结果", alarm_result)
        if alarm_result == -1:
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed to setup alarm, error_code--%d' % (self.ip, self.port, err_code))
        else:
            self.alarm_handle = alarm_result

    def _close_alarm(self):
        HKVision.adapter.close_alarm(self.alarm_handle)

    def _set_exception_cb(self):
        rsl = HKVision.adapter.set_exceptioln_call_back(None, None, self.exception_call_back, self.user_id)
        print('set_exception_cb', rsl)

    def _get_all_card_info(self):
        """
        获取门禁终端当前所有卡号与工号；
        :return:
        """
        flag = False
        self.all_user_temp.clear()
        card_cfg = NET_DVR_CARD_COND()
        card_cfg.dwSize = sizeof(card_cfg)
        card_cfg.dwCardNum = int('0xffffffff', 16)
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_GET_CARD, byref(card_cfg),
                                         sizeof(card_cfg), None, None)
        if handle == -1:
            print('fail to get all card info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to get all card info, error_code--%d' % (self.ip, self.port, err_code))
            if err_code == 7:
                mylogger.warning('HK entrance--(%s, %d) network was broken' % (self.ip, self.port))
                self.isrunning = False
        else:
            card_record = NET_DVR_CARD_RECORD()
            while True:
                rsl_getnext = HKVision.adapter.call_cpp('NET_DVR_GetNextRemoteConfig', handle, byref(card_record), sizeof(card_record))
                if rsl_getnext == -1:
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed to get next card info, error_code--%d' % (self.ip, self.port, err_code))
                    break
                elif rsl_getnext == 1000:
                    card_num = bytearray(card_record.byCardNo).decode(encoding='utf-8').strip(b'\x00'.decode())
                    self.all_user_temp.append((bytes(card_num, encoding='utf-8'), card_record.dwEmployeeNo))
                    # print('users--', card_record.dwEmployeeNo, card_num, card_record.byUserType, card_record.byCardType, card_record.byLeaderCard)
                elif rsl_getnext == 1001:
                    continue
                elif rsl_getnext == 1002:
                    flag = True
                    break
                else:
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            # print('stop remote ' + 'success' if rsl_stop else 'failed')
            # print('all_user--', self.all_user)
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to get all card info' % (self.ip, self.port))
        return flag

    def _del_card_info(self, bycardno: bytes):
        """
        删除卡号对应的所有信息，包括指纹和人脸；
        :param bycardno:
        :return:
        """
        flag = False
        card_num = bytearray(bycardno).decode(encoding='utf-8').strip(b'\x00'.decode())
        card_cfg = NET_DVR_CARD_COND()
        card_cfg.dwSize = sizeof(card_cfg)
        card_cfg.dwCardNum = int('0x00000001', 16)
        inbuff_ref = byref(card_cfg)
        user_data = create_string_buffer(bytes(self.ip, encoding='utf-8'))
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, 2562, inbuff_ref,
                                           sizeof(card_cfg), None, None)
        if handle == -1:
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to delete card(%s) info, error_code--%d' % (self.ip, self.port, card_num, err_code))
        else:
            send_cfg = NET_DVR_CARD_SEND_DATA()
            send_cfg.dwSize = sizeof(send_cfg)
            memmove(send_cfg.byCardNo, bycardno, len(bycardno))
            inbuff_ref = byref(send_cfg)
            status = NET_DVR_CARD_STATUS()
            outbuff_ref = byref(status)
            outdata_len = h_DWORD()
            while True:
                rsl_send = HKVision.adapter.call_cpp('NET_DVR_SendWithRecvRemoteConfig', handle, inbuff_ref, sizeof(send_cfg),
                                                      outbuff_ref, sizeof(status), byref(outdata_len))
                # print(status.byStatus, status.dwErrorCode)
                if rsl_send == -1:
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for SendWithRecvRemoteConfig to delete card(%s) info, error_code--%d' % (self.ip, self.port, card_num, err_code))
                elif rsl_send == 1000 and status.byStatus == 1:
                    print('success to del card--%s' % card_num)
                    flag = True
                elif rsl_send == 1001:
                    continue
                elif rsl_send == 1002:
                    print('success to delete card')
                    flag = True
                    break
                else:
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to delete card(%s) info' % (self.ip, self.port, card_num))
        return flag

    def _get_card_info(self, bycardno: bytes):
        """
        获取单个卡信息
        :param bycardno:
        :return:
        """
        flag = False
        self.str_entrance_pw = None
        self.usertype = 3
        card_cfg = NET_DVR_CARD_COND()
        card_cfg.dwSize = sizeof(card_cfg)
        card_cfg.dwCardNum = int('0x00000001', 16)
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_GET_CARD,
                                            byref(card_cfg), sizeof(card_cfg), None, None)
        if handle == -1:
            print('fail to get single card info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to get card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
        else:
            card_send = NET_DVR_CARD_SEND_DATA()
            card_send.dwSize = sizeof(card_send)
            memmove(card_send.byCardNo, bycardno, len(bycardno))
            card_record = NET_DVR_CARD_RECORD()
            outdata_len = h_DWORD()
            while True:
                rsl_recv = HKVision.adapter.call_cpp('NET_DVR_SendWithRecvRemoteConfig', handle, byref(card_send),
                                                      sizeof(card_send), byref(card_record), sizeof(card_record),
                                                      byref(outdata_len))
                print(rsl_recv)
                if rsl_recv == -1:
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for SendWithRecvRemoteConfig to get card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
                    break
                elif rsl_recv == 1000:
                    card_num = bytearray(card_record.byCardNo).decode(encoding='utf-8').strip(b'\x00'.decode())
                    self.str_entrance_pw = bytearray(card_record.byCardPassword).decode(encoding='utf-8').strip(b'\x00'.decode())
                    # print(card_record.byUserType)
                    self.usertype = 2 if card_record.byUserType == 1 else 3  # 0-common; 1-admin
                    # print('users--', card_record.dwEmployeeNo, card_num, self.str_entrance_pw, self.usertype)
                elif rsl_recv == 1001:
                    continue
                elif rsl_recv == 1002:
                    print('success to get single card info')
                    flag = True
                    break
                else:
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to get card(%s) info' % (self.ip, self.port, bycardno))
        return flag

    def _set_card_info(self, bycardno: bytes, code: int, byname: bytes, bypw: bytes, usertype: int):
        flag = False
        card_cfg = NET_DVR_CARD_COND()
        card_cfg.dwSize = sizeof(card_cfg)
        card_cfg.dwCardNum = int('0x00000001', 16)
        inbuff_ref = byref(card_cfg)
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_SET_CARD, inbuff_ref,
                                            sizeof(card_cfg), None, None)
        if handle == -1:
            print('fail to set card info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to set card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
        else:
            card_record = NET_DVR_CARD_RECORD()
            card_record.dwSize = sizeof(card_record)
            memmove(card_record.byCardNo, bycardno, len(bycardno))
            if bypw is not None:
                memmove(card_record.byCardPassword, bypw, len(bypw))
            card_record.dwEmployeeNo = code
            card_record.byCardType = 1
            card_record.byUserType = 0 if usertype == 3 else 1
            if byname is not None:
                memmove(card_record.byName, byname, len(byname))
            status = NET_DVR_CARD_STATUS()
            outdata_len = h_DWORD()
            while True:
                rsl_send = HKVision.adapter.call_cpp('NET_DVR_SendWithRecvRemoteConfig', handle, byref(card_record),
                                                      sizeof(card_record), byref(status), sizeof(status), byref(outdata_len))
                # print(status.byStatus, status.dwErrorCode)
                if rsl_send == -1:
                    print('fail to send card info')
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for SendWithRecvRemoteConfig to set card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
                    break
                elif rsl_send == 1000 and status.byStatus == 1:
                    print('success to set card--%s' % bycardno)
                    flag = True
                elif rsl_send == 1001:
                    continue
                elif rsl_send == 1002:
                    print('success to get fp')
                    flag = True
                    break
                else:
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to set card(%s) info' % (self.ip, self.port, bycardno))
        return flag

    def _get_fingerprint_info(self, bycardno: bytes):
        flag = False
        fp_cfg = NET_DVR_FINGERPRINT_COND()
        fp_cfg.dwSize = sizeof(fp_cfg)
        fp_cfg.dwFingerprintNum = int('0xffffffff', 16)
        memmove(fp_cfg.byCardNo, bycardno, len(bycardno))
        fp_cfg.dwEnableReaderNo = 1
        fp_cfg.byFingerPrintID = 0xff
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_GET_FINGERPRINT,
                                            byref(fp_cfg), sizeof(fp_cfg), None, None)
        if handle == -1:
            print('fail to get fingerprint info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to get fingerprint of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
        else:
            fp_record = NET_DVR_FINGERPRINT_RECORD()
            while True:
                rsl_getnext = HKVision.adapter.call_cpp('NET_DVR_GetNextRemoteConfig', handle, byref(fp_record),
                                                         sizeof(fp_record))
                if rsl_getnext == -1:
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for GetNextRemoteConfig to get fingerprint of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
                    break
                elif rsl_getnext == 1000:
                    card_num = bytearray(fp_record.byCardNo).decode(encoding='utf-8').strip(b'\x00'.decode())
                    finger_data = bytearray(fp_record.byFingerData)
                    self.fp_temp.clear()
                    self.fp_temp.extend(finger_data)
                elif rsl_getnext == 1001:
                    continue
                elif rsl_getnext == 1002:
                    print('success to get fp')
                    flag = True
                    break
                else:
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to get fingerprint of card(%s) info' % (self.ip, self.port, bycardno))
        return flag

    def _set_fingerprint_info(self, bycardno: bytes, fp_data: bytearray):
        flag = False
        fp_cfg = NET_DVR_FINGERPRINT_COND()
        fp_cfg.dwSize = sizeof(fp_cfg)
        fp_cfg.dwFingerprintNum = int('0x00000001', 16)
        memmove(fp_cfg.byCardNo, bycardno, len(bycardno))
        fp_cfg.dwEnableReaderNo = 1
        fp_cfg.byFingerPrintID = 1
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_SET_FINGERPRINT,
                                            byref(fp_cfg), sizeof(fp_cfg), None, None)
        if handle == -1:
            print('fail to set fingerprint info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to set fingerprint of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
        else:
            for i in range(100, 200):
                fp_data[i] = 11
            finger_data = bytes(fp_data)
            fp_record = NET_DVR_FINGERPRINT_RECORD()
            fp_record.dwSize = sizeof(fp_record)
            memmove(fp_record.byCardNo, bycardno, len(bycardno))
            fp_record.dwFingerPrintLen = 512
            fp_record.dwEnableReaderNo = 1
            fp_record.byFingerPrintID = 1
            fp_record.byFingerType = 0
            memmove(fp_record.byFingerData, finger_data, 512)

            # finger_d = bytearray(fp_record.byFingerData)
            # print('fp data--', finger_d)
            # print(fp_record.dwFingerPrintLen)

            status = NET_DVR_FINGERPRINT_STATUS()
            outdata_len = h_DWORD()
            while True:
                rsl_send = HKVision.adapter.call_cpp('NET_DVR_SendWithRecvRemoteConfig', handle, byref(fp_record),
                                                      sizeof(fp_record), byref(status), sizeof(status), byref(outdata_len))
                card_num = bytearray(status.byCardNo).decode(encoding='utf-8').strip(b'\x00'.decode())
                # print(card_num)
                # print(status.byRecvStatus, status.byCardReaderRecvStatus)
                # print(status.dwCardReaderNo)
                # print('rsl_send', rsl_send)
                if rsl_send == -1:
                    print('fail to send fingerprint info')
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for SendWithRecvRemoteConfig to set fingerprint of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
                    break
                elif rsl_send == 1000 and (status.byRecvStatus == 0 and status.byCardReaderRecvStatus == 1):
                    print('success to set fingerprint to card--%s' % bycardno)
                    flag = True
                elif rsl_send == 1001:
                    continue
                elif rsl_send == 1002:
                    print('success to get fp')
                    flag = True
                    break
                else:
                    print('fail to set fingerprint to card--%s' % bycardno)
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to set fingerprint of card(%s) info' % (self.ip, self.port, bycardno))
        return flag

    def _get_face_info(self, bycardno):
        flag = False
        face_cfg = NET_DVR_FACE_COND()
        face_cfg.dwSize = sizeof(face_cfg)
        face_cfg.dwFaceNum = int('0xffffffff', 16)
        memmove(face_cfg.byCardNo, bycardno, len(bycardno))
        face_cfg.dwEnableReaderNo = 1
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_GET_FACE,
                                            byref(face_cfg), sizeof(face_cfg), None, None)
        if handle == -1:
            print('fail to get face info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to get face of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
        else:
            face_record = NET_DVR_FACE_RECORD()
            while True:
                rsl_getnext = HKVision.adapter.call_cpp('NET_DVR_GetNextRemoteConfig', handle, byref(face_record),
                                                         sizeof(face_record))
                if rsl_getnext == -1:
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for GetNextRemoteConfig to get face of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
                    break
                elif rsl_getnext == 1000:
                    card_num = bytearray(face_record.byCardNo).decode(encoding='utf-8').strip(b'\x00'.decode())
                    facelen = face_record.dwFaceLen
                    print('dwFaceLen--', facelen)
                    if facelen > 0:
                        face_data = create_string_buffer("q".encode('utf-8'), facelen)
                        memmove(pointer(face_data), face_record.pFaceBuffer, facelen)
                        # print(bytearray(face_data))
                        self.face_temp.clear()
                        self.face_temp.extend(face_data)
                        flag = True
                elif rsl_getnext == 1001:
                    continue
                elif rsl_getnext == 1002:
                    print('success to get face')
                    flag = True
                    break
                else:
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to get face of card(%s) info' % (self.ip, self.port, bycardno))
        return flag

    def _set_face_info(self, bycardno: bytes, face: bytearray):
        flag = False
        face_cfg = NET_DVR_FACE_COND()
        face_cfg.dwSize = sizeof(face_cfg)
        face_cfg.dwFaceNum = int('0x00000001', 16)
        # memmove(face_cfg.byCardNo, bycardno, len(bycardno))
        face_cfg.dwEnableReaderNo = 1
        handle = HKVision.adapter.call_cpp('NET_DVR_StartRemoteConfig', self.user_id, NET_DVR_SET_FACE,
                                            byref(face_cfg), sizeof(face_cfg), None, None)
        if handle == -1:
            print('fail to set fingerprint info')
            err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
            print('err_code', err_code)
            mylogger.warning('HK entrance--(%s, %d) was failed for StartRemoteConfig to set face of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
        else:
            print('success remote')
            face_data = bytes(face)
            face_record = NET_DVR_FACE_RECORD()
            face_record.dwSize = sizeof(face_record)
            memmove(face_record.byCardNo, bycardno, len(bycardno))
            face_record.dwFaceLen = len(face_data)
            face_record.dwEnableReaderNo = 0

            face_record.pFaceBuffer = cast(face_data, POINTER(h_BYTE))

            # face_d = create_string_buffer("q".encode('utf-8'), face_record.dwFaceLen)
            # memmove(face_d, face_record.pFaceBuffer, face_record.dwFaceLen)

            status = NET_DVR_FACE_STATUS()
            outdata_len = h_DWORD()
            while True:
                rsl_send = HKVision.adapter.call_cpp('NET_DVR_SendWithRecvRemoteConfig', handle, byref(face_record),
                                                      sizeof(face_record), byref(status), sizeof(status),
                                                      byref(outdata_len))
                card_num = bytearray(status.byCardNo).decode(encoding='utf-8').strip(b'\x00'.decode())
                if rsl_send == -1:
                    print('fail to send face info')
                    err_code = HKVision.adapter.call_cpp('NET_DVR_GetLastError')
                    print('err_code', err_code)
                    mylogger.warning('HK entrance--(%s, %d) was failed for SendWithRecvRemoteConfig to set face of card(%s) info, error_code--%d' % (self.ip, self.port, bycardno, err_code))
                    break
                elif rsl_send == 1000 and status.byRecvStatus == 1:
                    print('success to set face to card--%s' % bycardno)
                    flag = True
                elif rsl_send == 1001:
                    continue
                elif rsl_send == 1002:
                    print('success to set face')
                    flag = True
                    break
                else:
                    print('fail to set face to card--%s' % bycardno)
                    break
            rsl_stop = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', handle)
            print('stop remote ' + 'success' if rsl_stop else 'failed')
        if flag is not True:
            mylogger.warning('HK entrance--(%s, %d) was failed to set face of card(%s) info' % (self.ip, self.port, bycardno))
        return flag

    def check_users_from_terminal(self):
        """
        1、若有新增用户就获取工号和卡号;
        2、若用户不在DB，获取指纹和人脸, 添加用户到DB；
        3、若用户在DB, 绑定用户到门禁;
        4、若减少用户，则解除用户与门禁绑定关系；
        :param employee_code:
        :param card_num:
        :return:
        """
        if self._get_all_card_info():
            # print(self.all_user)
            # print(self.all_user_temp)
            with self.lock:
                user_increased = list(set(self.all_user_temp).difference(set(self.all_user)))  # someone not in self.all_user
                user_reduced = list(set(self.all_user).difference(set(self.all_user_temp)))
            if user_increased:
                for user in user_increased:
                    self._get_card_info(user[0])
                    self._get_fingerprint_info(user[0])
                    self._get_face_info(user[0])
                    self.save_new_user_to_db(user_code=str(user[1]), card_num=str(user[0], encoding='utf-8'),
                                             finger_print=self.fp_temp, face_img=self.face_temp,
                                             pw=self.str_entrance_pw, usertype=self.usertype)
                    with self.lock:
                        self.all_user.append(user)
                    print('add new user to DB--', user)
                    mylogger.info('HK entrance--(%s, %d) add new user(code:%s)' % (self.ip, self.port, str(user[1])))
            if user_reduced:
                for user in user_reduced:
                    user_db = User.by_code(code=str(user[1]))
                    if user_db:
                        entrance = Entrance.by_addr(self.ip, self.port)
                        entrance.users.remove(user_db)
                        entrance.save()
                        with self.lock:
                            self.all_user.remove(user)
                    print('del user--(%s, %d) in entrance--(%s, %d)' % (user[0], user[1], self.ip, self.port))
                    mylogger.info('HK entrance--(%s, %d) reduce user(code:%d)' % (self.ip, self.port, user[1]))
        else:
            pass
        thd = threading.Timer(interval=self.interval, function=self.check_users_from_terminal)
        thd.daemon = True
        thd.start()

    # def stop_remote(self):
    #     rsl = HKVision.adapter.call_cpp('NET_DVR_StopRemoteConfig', self.remote_handle)
    #     print('stop remote ' + 'success' if rsl else 'failed')
    #     print('all_user--', self.all_user)

    @staticmethod
    @CFUNCTYPE(h_BOOL, h_LONG, POINTER(alarm.NET_DVR_ALARMER), POINTER(h_CHAR), h_DWORD, h_VOID_P)
    def message_call_back(lCommand,
                          pAlarmer,
                          pAlarmInfo,
                          dwBufLen,
                          pUser):
        print("lCommand:{},pAlarmer:{},pAlarmInfo:{},dwBufLen:{}".format(lCommand, pAlarmer, pAlarmInfo, dwBufLen))
        if lCommand == 0x5002:
            # 门禁主机报警信息
            # print('Command=', lCommand)
            alarmer = alarm.NET_DVR_ALARMER()
            memmove(pointer(alarmer), pAlarmer, sizeof(alarmer))
            ip = bytearray(alarmer.sDeviceIP).decode(encoding='utf-8')
            print('IP--', ip)
            alarm_info = alarm.NET_DVR_ACS_ALARM_INFO()
            memmove(pointer(alarm_info), pAlarmInfo, sizeof(alarm_info))
            major_code = alarm_info.dwMajor
            minor_code = alarm_info.dwMinor
            if major_code == 5 and minor_code == 38:
                # print(hex(alarm_info.dwMajor))
                # print(hex(alarm_info.dwMinor))
                cardno = bytearray(alarm_info.struAcsEventInfo.byCardNo).decode(encoding='utf-8')
                user_code = alarm_info.struAcsEventInfo.dwEmployeeNo
                # print('user--%s(CARD--%s) was in' % (user_code, cardno))
                # print(alarm_info.byAcsEventInfoExtend)
                # print(alarm_info.byAcsEventInfoExtendV20)
                HKVision.ip_obj_dic[ip]['obj'].set_auth_info(user_code, cardno)
                # if user_code == 1 or user_code == '1':
                #     HKVision.ip_obj_dic[ip]['obj'].stop()
        return True

    @staticmethod
    @CFUNCTYPE(None, h_DWORD, h_BYTE, h_BYTE, h_VOID_P)
    def exception_call_back(dwType,
                            lUserID,
                            lHandle,
                            pUser):
        # print(time.localtime())
        # print(hex(dwType), lUserID, lHandle, pUser)
        if hex(dwType) == '0x8000':
            # 网络断开异常
            for k, v in HKVision.ip_obj_dic.items():
                if v['user_id'] == lUserID:
                    v['obj'].stop()

    def set_auth_info(self, user_code, cardno):
        print('(userCode, cardNo)--(%s, %s) was in!' % (user_code, cardno))
        data = {'user': str(user_code), 'card_id': str(cardno)}
        pkg = TransferPackage(code=EQUIPMENT_DATA_UPDATE, eq_type=5, data=data, source=(self.ip, self.port),
                              msg_type=3, storeroom_id=self.storeroom_id, eq_id=self.uuid)
        self.queue_push_data.put(pkg)
        print('put to queue')

    def stop(self):
        with self.lock:
            self.isrunning = False
        print('Entrance_hk--(%s, %d) was offline' % (self.ip, self.port))
        mylogger.warning('Entrance_hk--(%s, %d) was offline' % (self.ip, self.port))
