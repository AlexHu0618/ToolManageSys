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


class GravityShelf(threading.Thread):
    """
        1.frame: Addr + Func + Register + Data + Check
        2、地址从1-63，地址0用于广播，按地址大小进行返回；
    """
    intervals = {'0': 0.0001, '1': 0.0002, '2': 0.0005, '3': 0.001, '4': 0.002, '5': 0.005, '6': 0.01, '7': 0.02,
                 '8': 0.05, '9': 0.1, 'a': 0.2, 'b': 0.5, 'c': 1, 'd': 2, 'e': 5, 'A': 0.2, 'B': 0.5, 'C': 1,
                 'D': 2, 'E': 5}

    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid):
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

    def run(self):
        data_buff = {}
        self._initial_data(data_buff)
        cursec = 0
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=200, eq_type=1, data={'rsl': rsl}, source=self.addr, msg_type=4,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec % 10 == 0:
                        self.check_data_update(data_buff=data_buff)
                    else:
                        pass
            except Exception as e:
                print(e)
                mylogger.error(e)
        print('网络断开啦，子线程%s要关闭了！' % threading.current_thread().name)

    def _initial_data(self, data_buff: dict):
        rsl = self.readAllInfo()
        for i in rsl:
            g = self.readWeight(i)
            data_buff[i] = g
        print('GravityShelf--', self.uuid, ' initial: ', data_buff)

    def check_data_update(self, data_buff):
        rsl = self.readAllInfo()
        allg = {}
        if rsl is not None and len(rsl) >= len(data_buff):
            for i in rsl:
                g = self.readWeight(i)
                if i not in data_buff.keys() or g != data_buff[i] and (abs(g - data_buff[i]) > 5):
                    print('g - data_buff[i] ', g, data_buff[i])
                    data = {'addr_num': i, 'value': g - data_buff[i], 'is_increased': True if g - data_buff[i] > 0 else False}
                    pkg = TransferPackage(code=206, eq_type=1, data=data, source=self.addr, msg_type=3,
                                          storeroom_id=self.storeroom_id, eq_id=self.uuid)
                    self.queue_push_data.put(pkg)
                    data_buff[i] = g
                    # print('Gravity data update--', data)
                allg[i] = g
            # print(time.asctime(), 'G--getAllInfo: ', allg)

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
                print('G--Warning', '等待TCP消息回应超时')
                self.timeout_count += 1
                if self.timeout_count > 5:
                    self.isrunning = False
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
        if datas is not None:
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
            return ERR_EQUIPMENT_RESP

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

    def run(self):
        self._initial_data()
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=200, eq_type=2, data={'rsl': rsl}, source=self.addr, msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
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
                print(diff_epcs)
                if diff_epcs:
                    is_increase = True if len(rsl_data) > len(self.data_buff) else False
                    diff = [epc_ant for epc_ant in rsl_data if epc_ant[0] in diff_epcs] if is_increase else [epc_ant for epc_ant in self.data_buff if epc_ant[0] in diff_epcs]
                    data = {'epcs': diff, 'is_increase': is_increase}
                    pkg = TransferPackage(code=206, eq_type=2, data=data, source=self.addr, msg_type=3,
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
                print('R--Warning', '等待TCP消息回应超时')
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

    def getAndResetBuf(self):
        cmd_f = 'A0 03' + self.addr_num + '90'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, True)
        # print('cmd back:', data)
        if data != b'':
            if data[0:4] == bytes.fromhex('A0 04' + self.addr_num + '90'):
                print('ErrorCode: ', hex(data[4]))
                return None
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
                    epc_ant = (epc, ant)
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


class Lcd(threading.Thread):
    """
        1.frame: Head(0x7E) + Addr + Cmd + Len + Data + Check + End(0x68)
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, storeroom_id, uuid):
        threading.Thread.__init__(self)
        self.addr = addr
        self.storeroom_id = storeroom_id
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.alladdrs = ('03', '04')
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
                        pkg = TransferPackage(code=200, eq_type=1, data={'rsl': rsl}, source=self.addr, msg_type=6,
                                              storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        num = num + 1 if num < 1000 else 0
                        for i in self.alladdrs:
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


class EntranceGuard(threading.Thread):
    lib = cdll.LoadLibrary("/home/alex/C++/libs/libplcommpro.so")

    def __init__(self, addr: tuple, queuetask, queuersl, queue_push_data, storeroom_id, uuid):
        threading.Thread.__init__(self)
        self.ip = addr[0]
        self.port = addr[1]
        self.storeroom_id = storeroom_id
        self.uuid = uuid
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()
        self.current_data = None
        self.lib = EntranceGuard.lib
        self.handle = self.lib.Connect(b'protocol=TCP,ipaddress=' + bytes(self.ip, encoding='utf8') +
                                       b',port=' + bytes(str(self.port), encoding='utf8') +
                                       b',timeout=2000,passwd=')

    def run(self):
        cursec = 0
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=200, eq_type=3, data={'rsl': rsl}, source=(self.ip, self.port),
                                              msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                        self.queuersl.put(pkg)
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        rsl = self.getNewEvent()
                        if rsl:
                            if self.current_data is not None:
                                if rsl != self.current_data:
                                    data = {'user': rsl[0], 'raw': rsl}
                                    pkg = TransferPackage(code=206, eq_type=3, data=data, source=(self.ip, self.port),
                                                          msg_type=3, storeroom_id=self.storeroom_id, eq_id=self.uuid)
                                    self.queue_push_data.put(pkg)
                                    print('gate--getNewEvent: ', rsl)
                                    with self.lock:
                                        self.current_data = copy.deepcopy(rsl)
                            else:
                                with self.lock:
                                    self.current_data = copy.deepcopy(rsl)
                        elif rsl is not None:
                            # 非注册用户
                            pass
                        else:
                            # 读取错误
                            with self.lock:
                                self.isrunning = False
                    else:
                        pass
            except Exception as e:
                print('except from EntranceGuard--', e)
                mylogger.error(e)
                break
        self.lib.Disconnect(self.handle)

    @staticmethod
    def conn(ip: str, port: int):
        handle = EntranceGuard.lib.Connect(b'protocol=TCP,ipaddress=' + bytes(ip, encoding='utf8') +
                                       b',port=' + bytes(str(port), encoding='utf8') +
                                       b',timeout=2000,passwd=')
        if handle == 0:
            print('Fail to Connect.')
            return None
        else:
            return handle

    @staticmethod
    def disconn(handle):
        EntranceGuard.lib.Disconnect(handle)

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
                    mylogger.warning('(%s, %d)--GetDeviceData() get no registerd user' % (self.ip, self.port))
                    return []
            else:
                mylogger.error('(%s, %d)--GetDeviceData() get error code %d' % (self.ip, self.port, rsl))
                return None
        else:
            mylogger.error('(%s, %d)--GetDeviceDataCount() get error code %d' % (self.ip, self.port, count))
            return None

    def add_new_user(self, user_code, fingerprint_template, username=''):
        """
        1、设置user表；
        2、设置templatev10表；
        3、设置userauthorize表；
        :param user_code:
        :param username:
        :param fingerprint_template:
        :return:
        """
        # set user
        p_table = create_string_buffer(b'user')
        data = 'Pin=%s\tName=%s\tDisable=0' % (user_code, username)
        str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
        rsl_user = self.lib.SetDeviceData(self.handle, p_table, str_buf, b'')

        # set fingerprint
        finger_id = 3  # 0~9, default=3
        # with open(fpath_template, "r") as f:  # 打开文件
        #     template = f.read()  # 读取文件
        template = fingerprint_template
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
        self.lib.Disconnect(self.handle)


class HIKVision(threading.Thread):
    pass


class CodeScanner(threading.Thread):
    pass


class ChannelMachine(threading.Thread):
    pass


class RfidR2000FH(threading.Thread):
    """
    1、RFID R2000跳频版
    2、frame struct: Head(0x5A) + MSG_type + Addr + Len + Data + Check(CRC16)
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data, storeroom_id, uuid):
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
        self.data_buff = list()  # [(epc, ant), ]
        self.timeout_counter = 0

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
                        pkg = TransferPackage(code=200, eq_type=2, data={'rsl': rsl}, source=self.addr, msg_type=4, storeroom_id=self.storeroom_id, eq_id=self.uuid)
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
                print('R2000FH old EPCs: ', self.data_buff)
                print('R2000FH new EPCs: ', self.current_epcs)
                if self.current_epcs is not None:
                    diff_epcs = list(set(epc[0] for epc in self.current_epcs) ^ set(epc[0] for epc in self.data_buff))
                    print('R2000FH diff_epcs--', diff_epcs)
                    if diff_epcs:
                        is_increase = True if len(self.current_epcs) > len(self.data_buff) else False
                        diff = [epc_ant for epc_ant in self.current_epcs if epc_ant[0] in diff_epcs] if is_increase else [epc_ant for epc_ant in self.data_buff if epc_ant[0] in diff_epcs]
                        data = {'epcs': diff, 'is_increase': is_increase}
                        pkg = TransferPackage(code=206, eq_type=2, data=data, source=self.addr, msg_type=3,
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
                    self.timeout_counter = 0
                    self._analyze_recv_data(data=data)
                except socket.timeout:
                    # print('RFID2000FH times out')
                    self.timeout_counter += 1
                    if self.timeout_counter > 20:
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
        while end < len_all_data:
            head = data[start:start + 5]
            if head == bytes.fromhex('5A 00 01 12 00'):
                len_data = int.from_bytes(data[(start + 5):(start + 7)], byteorder='big', signed=False)
                len_epc = int.from_bytes(data[(start + 7):(start + 9)], byteorder='big', signed=False)
                epc = data[(start + 9):(start + 9 + len_epc)]
                ant = data[(start + 9 + len_epc + 2):(start + 9 + len_epc + 2 + 1)]
                print('(EPC, ant)--(%s, %s)' % (epc, ant))
                with self.lock:
                    if epc not in [epc_ant[0] for epc_ant in self.current_epcs]:
                        self.current_epcs.append((epc, ant))
                # if (epc, ant) not in self.current_epcs.copy():
                #     self.current_epcs.append((epc, ant))
                start += (5 + 2 + len_data + 2)
                end = start
            elif head == bytes.fromhex('5A 00 01 12 02'):
                start += (5 + 5)
                end = start
            else:
                break

    def get_current_epc(self):
        print(self.data_buff)
        return self.data_buff

    def _inventory_once(self):
        cmd = bytes.fromhex('5A 00 01 02 10 00 05 00 00 00 FF 00 D4 68')
        self.q_cmd.put(cmd)
        thd_auto_inventory = threading.Timer(interval=5, function=self._inventory_once)
        thd_auto_inventory.start()

    def _inventory(self):
        cmd = bytes.fromhex('5A 00 01 02 10 00 05 00 00 00 FF 01 C4 49')
        self.q_cmd.put(cmd)
        time.sleep(1)
        self._stop()
        thd_auto_inventory = threading.Timer(interval=2, function=self._inventory)
        thd_auto_inventory.start()

    def _stop(self):
        cmd = bytes.fromhex('5A 00 01 02 FF 00 00 88 5A')
        self.q_cmd.put(cmd)
