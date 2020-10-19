import threading
from operator import methodcaller
import socket
from ctypes import *
import time
from app.myLogger import mylogger
from app.globalvar import *


class GravityShelf(threading.Thread):
    """
        1.frame: Addr + Func + Register + Data + Check
    """
    intervals = {'0': 0.0001, '1': 0.0002, '2': 0.0005, '3': 0.001, '4': 0.002, '5': 0.005, '6': 0.01, '7': 0.02,
                 '8': 0.05, '9': 0.1, 'a': 0.2, 'b': 0.5, 'c': 1, 'd': 2, 'e': 5, 'A': 0.2, 'B': 0.5, 'C': 1,
                 'D': 2, 'E': 5}

    def __init__(self, tcp_socket, queuetask, queuersl, event):
        threading.Thread.__init__(self)
        self.BUFFSIZE = 1024
        self.all_id = ()
        self.tcp_socket = tcp_socket
        self.addr_serial = {}
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.lock = threading.RLock()

    def run(self):
        cursec = 0
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    with self.lock:
                        task, args = self.queuetask.get()
                        rsl = methodcaller(task, *args)(self)
                        if rsl is not None:
                            self.queuersl.put(rsl)
                            self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        rsl = self.readAllInfo()
                        allg = {}
                        if rsl is not None:
                            for i in rsl:
                                g = self.readWeight(i)
                                allg[i] = g
                        print('G--getAllInfo: ', allg)
                    else:
                        pass
            except Exception as e:
                print(e)
                mylogger.error(e)

    def readWeight(self, addr='01'):
        cmd_f = bytes.fromhex(addr + '05 02 05')
        lcr = sum(cmd_f) % 256
        cmd = cmd_f + lcr.to_bytes(length=1, byteorder='big', signed=False)
        data = self.getData(cmd)
        if data is not None:
            if data[:3] == bytes.fromhex(addr + '0602'):
                interval = self.intervals[hex(data[4])[-1]]
                scale = int.from_bytes(data[5:8], byteorder='big', signed=False)
                value = scale * interval
                return value
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
        except socket.timeout:
            if multiframe and data_total:
                return data_total
            else:
                # print('G--Warning', '等待TCP消息回应超时')
                return TIMEOUT_EQUIPMENT
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


class RfidR2000(threading.Thread):
    """
        1.frame: Head(0xA0) + Len + Addr + Cmd + Data + Check
    """
    def __init__(self, tcp_socket, queuetask, queuersl, event):
        threading.Thread.__init__(self)
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr = '01'
        self.ant_count = 8
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.lock = threading.RLock()

    def run(self):
        cursec = 0
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        self.queuersl.put(rsl)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        rsl = self.inventory('00')
                        print('R--inventory: ', rsl)
                    else:
                        pass
            finally:
                self.lock.release()

    def check(self, cmd_f):
        # complement ---- (~sum + 1)
        cmd = bytes.fromhex(cmd_f)
        check = (sum(cmd) ^ 0xFF) + 1
        check_hex = bytes.fromhex(hex(check)[-2:])
        return check_hex

    def count_frame(self, data):
        if data[0:4] == bytes.fromhex('A0 04' + self.addr + '90'):
            return 1
        else:
            tag_count = int.from_bytes(data[4:6], byteorder='big', signed=False)
            return tag_count

    def getData(self, cmd, multiframe=False):
        self.tcp_socket.settimeout(1)
        data_total = []
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
                        print('count: ', count)
                        isfirst = False
                    if num == count:
                        break
                    data_total.append(data)
            else:
                data = self.tcp_socket.recv(self.BUFFSIZE)
        except socket.timeout:
            if multiframe and data_total:
                return data_total
            else:
                print('R--Warning', '等待TCP消息回应超时')
                return TIMEOUT_EQUIPMENT
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
        cmd_f = 'A0 04' + self.addr + '73' + addr_new
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        print(cmd)
        data = self.getData(cmd, False)
        if data[0:5] == bytes.fromhex('A0 04' + self.addr + '73 10'):
            self.addr = addr_new
            return SUCCESS
        else:
            return ERR_EQUIPMENT_RESP

    def setOutputPower(self, num='00', value=30):
        powers = self.getOutputPower()
        if powers:
            powers[int(num)] = value
            cmd_len = '0B' if self.ant_count == 8 else '07'
            cmd_f = 'A0 ' + cmd_len + self.addr + '76 ' + ' '.join(hex(p)[-2:] if p > 16 else ('0' + hex(p)[-1:]) for p in powers)
            print(cmd_f)
            check = self.check(cmd_f)
            cmd = bytes.fromhex(cmd_f) + check
            data = self.getData(cmd, False)
            print('cmd back:', data)
            if data[0:5] == bytes.fromhex('A0 04' + self.addr + '76 10'):
                return SUCCESS
            else:
                return ERR_EQUIPMENT_RESP
        else:
            return ERR_EQUIPMENT_RESP

    def getOutputPower(self):
        cmd_f = 'A0 03 ' + self.addr + ' 97' if self.ant_count == 8 else ' 77'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        # print('cmd back:', data)
        if data[0:4] == bytes.fromhex('A0 04' + self.addr + ' 97' if self.ant_count == 8 else ' 77'):
            power = data[4]
            return [power for i in range(self.ant_count)]
        elif data[0:4] == bytes.fromhex('A0' + ('0B' if self.ant_count == 8 else '07') + self.addr + ' 97' if self.ant_count == 8 else ' 77'):
            return [data[i+4] for i in range(self.ant_count)]
        else:
            return ERR_EQUIPMENT_RESP

    def getWorkAntenna(self):
        cmd_f = 'A0 03' + self.addr + '75'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        if data[0:4] == bytes.fromhex(('A0 04' + self.addr + '75')):
            ant_id = data[4]
            return ant_id
        else:
            return ERR_EQUIPMENT_RESP

    def setWorkAntenna(self, ant_id='00'):
        cmd_f = 'A0 04' + self.addr + '74' + ant_id
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        if data[0:5] == bytes.fromhex(('A0 04' + self.addr + '74 10')):
            return SUCCESS
        else:
            return ERR_EQUIPMENT_RESP

    def inventory(self, ant_id='00'):
        rsl = self.setWorkAntenna(ant_id)
        if rsl:
            cmd_repeat = '05'
            cmd_f = 'A0 04' + self.addr + '80' + cmd_repeat
            check = self.check(cmd_f)
            cmd = bytes.fromhex(cmd_f) + check
            data = self.getData(cmd, False)
            if data[0:5] == bytes.fromhex('A0 0C' + self.addr + '80' + ant_id):
                tag_count = int.from_bytes(data[5:7], byteorder='big', signed=False)
                # print('tag_count: ', tag_count)
                return tag_count
        else:
            return ERR_EQUIPMENT_RESP

    def getAndResetBuf(self):
        cmd_f = 'A0 03' + self.addr + '90'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, True)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('A0 04' + self.addr + '90'):
            print('ErrorCode: ', hex(data[4]))
            return ERR_EQUIPMENT_RESP
        else:
            frames = []
            length = int(data[1])
            print(length)
            tag_count = int.from_bytes(data[4:6], byteorder='big', signed=False)
            print(tag_count)
            start = 0
            for i in range(tag_count):
                end = start + length + 2
                frames.append(data[start:end])
                start = end
            print(frames)
            epcs = []
            for f in frames:
                data_len = f[6]
                epc = f[9:5 + data_len]
                print(epc)
                epcs.append(epc)
            return epcs

    def reset_inv_buf(self):
        cmd_f = 'A0 03 ' + self.addr + '93'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        print('cmd back:', data)


class RfidJH2880(object):
    """
        1.frame: Head(0xBB) + Type + Cmd + Len + Data + Check + End(0x7E)
    """
    def __init__(self, tcp_socket, addr='00'):
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr = addr

    def check(self, cmd_f):
        cmd = bytes.fromhex(cmd_f)
        check = sum(cmd) % 256
        check_hex = hex(check)[-2:]
        return check_hex

    def getData(self, cmd):
        self.tcp_socket.send(cmd)
        data = self.tcp_socket.recv(self.BUFFSIZE)
        return data

    def setOutputPower(self, value):
        temp = hex((value * 100) % 65536)[2:]
        power = temp if len(temp) > 3 else '0' + temp
        cmd_f = 'BB 00 B6 00 02' + power
        check = self.check(cmd_f)
        cmd = cmd_f + check + '7E'
        data = self.getData(cmd)
        print('cmd back:', data)
        if data.hex() == 'BB 01 B6 00 01 00 B8 7E':
            return True
        else:
            return False

    def getOutputPower(self):
        cmd = 'BB 00 B7 00 00 B7 7E'
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4].hex() == 'BB 01 B7 00 02':
            power = int.from_bytes(data[5:6], byteorder='big', signed=False)
            return power/100
        else:
            return None

    def setWorkAntenna(self, ant_id='00'):
        cmd_f = 'BB 00 0F 00 01' + ant_id
        check = self.check(cmd_f)
        cmd = cmd_f + check + '7E'
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4].hex() == 'BB 01 0F 00 01':
            return True
        else:
            return False

    def inventory(self, ant_id='00', time='00 0A'):
        """
        1. multi-inventory for specified antenna
        """
        rsl = self.setWorkAntenna(ant_id)
        if rsl:
            cmd_f = 'BB 00 27 00 03 22' + time
            check = self.check(cmd_f)
            cmd = cmd_f + check + '7E'
            self.tcp_socket.send(cmd)
            while True:
                data = self.tcp_socket.recv(self.BUFFSIZE)
                if data.hex() == 'BB 01 FF 00 01 15 16 7E':
                    break
                else:
                    if data[:2].hex() == 'BB 02 22':
                        pl = int.from_bytes(data[3:4], byteorder='big', signed=False)
                        rssi = data[5].hex()
                        pc = data[6:7].hex()
                        epc = data[8:(8 + pl - 5)]
                        print('rssi pc epc', rssi, pc, epc)
                        continue
                    else:
                        pass
        else:
            print('Fail to inventory')


class Lcd(threading.Thread):
    """
        1.frame: Head(0x7E) + Addr + Cmd + Len + Data + Check + End(0x68)
    """
    def __init__(self, tcp_socket, queuetask, queuersl, event):
        threading.Thread.__init__(self)
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.alladdrs = ('03', '04')
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.event = event
        self.lock = threading.RLock()

    def run(self):
        num = 0
        cursec = 0
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        self.queuersl.put(rsl)
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
                            if rsl:
                                print('L(%s)--showNum: %i' % (i, num))
                    else:
                        pass
            finally:
                self.lock.release()

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
            print('L--Warning', '等待TCP消息回应超时')
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
            return TIMEOUT_EQUIPMENT

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
            return TIMEOUT_EQUIPMENT

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

    def __init__(self, addr: tuple, queuetask, queuersl):
        threading.Thread.__init__(self)
        self.ip = addr[0]
        self.port = addr[1]
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.lock = threading.RLock()
        self.lib = EntranceGuard.lib
        self.handle = self.lib.Connect(b'protocol=TCP,ipaddress=' + bytes(self.ip, encoding='utf8') +
                                                b',port=' + bytes(str(self.port), encoding='utf8') +
                                                b',timeout=2000,passwd=')
        if self.handle == 0:
            print('Fail to Connect.')

    def run(self):
        cursec = 0
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        self.queuersl.put(rsl)
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        rsl = self.getNewEvent()
                        print('gate--getNewEvent: ', rsl)
                    else:
                        pass
            finally:
                self.lock.release()

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
                recode_list = last_record.split(b',')
                eventtype = recode_list[3]
                user = str(recode_list[0], encoding='gb18030')
                if eventtype == b'0':
                    print('\033[1;33m USER--', user, ' is authed....\033[0m')
                    resp = 'Auth: ' + str(last_record, encoding='gb18030')
                else:
                    print('\033[1;33m USER--', user, ' is non-authed....\033[0m')
                    resp = 'Non-auth: ' + str(last_record, encoding='gb18030')
                return resp
            else:
                return rsl
        else:
            return count

    def __del__(self):
        self.lib.Disconnect(self.handle)
