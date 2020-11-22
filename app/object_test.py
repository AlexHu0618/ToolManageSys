import threading
from operator import methodcaller
import socket
from ctypes import *
import time
from app.myLogger import mylogger
from app.globalvar import *
import copy


class GravityShelf(threading.Thread):
    """
        1.frame: Addr + Func + Register + Data + Check
    """
    # intervals = {'0': 0.0001, '1': 0.0002, '2': 0.0005, '3': 0.001, '4': 0.002, '5': 0.005, '6': 0.01, '7': 0.02,
    #              '8': 0.05, '9': 0.1, 'a': 0.2, 'b': 0.5, 'c': 1, 'd': 2, 'e': 5, 'A': 0.2, 'B': 0.5, 'C': 1,
    #              'D': 2, 'E': 5}

    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data):
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
        self.frequency = 1  # secends

    def run(self):
        cursec = 0
        current_data = {}
        while self.isrunning:
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=200, eq_type=1, data={'rsl': rsl}, source=self.addr, msg_type=4)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    time.sleep(30)
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        rsl = cursec
                        allg = {}
                        if rsl is not None and rsl % 10 == 0:
                            allg[str(rsl)] = rsl
                            if allg != current_data:
                                current_data.update(allg)
                                pkg = TransferPackage(code=206, eq_type=1, data=allg, source=self.addr, msg_type=3)
                                self.queue_push_data.put(pkg)
                                # print(time.asctime(), 'G--getAllInfo: ', allg)
                    else:
                        pass
            except Exception as e:
                print(e)
                mylogger.error(e)
        print('网络断开啦，子线程%s要关闭了！' % threading.current_thread().name)


class RfidR2000(threading.Thread):
    """
        1.frame: Head(0xA0) + Len + Addr + Cmd + Data + Check
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event, queue_push_data):
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
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()

    def run(self):
        cursec = 0
        current_data = {}
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=200, eq_type=2, data={'rsl': rsl}, source=self.addr, msg_type=4)
                        self.queuersl.put(pkg)
                        self.event.set()
                else:
                    localtime = time.localtime(time.time())
                    if localtime.tm_sec != cursec:
                        cursec = localtime.tm_sec
                        rsl0 = self.inventory('00')
                        rsl1 = self.inventory('01')
                        rsl2 = self.inventory('02')
                        rsl3 = self.inventory('03')
                        rsl = {'00': rsl0, '01': rsl1, '02': rsl2, '03': rsl3}
                        if rsl != current_data:
                            current_data.update(rsl)
                            pkg = TransferPackage(code=206, eq_type=2, data={'rsl': rsl}, source=self.addr, msg_type=3)
                            self.queue_push_data.put(pkg)
                        # print('R--inventory: ', rsl)
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
        if data[0:4] == bytes.fromhex('A0 04' + self.addr_num + '90'):
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
            return SUCCESS
        else:
            return ERR_EQUIPMENT_RESP

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
                # print('tag_count: ', tag_count)
                return tag_count
        else:
            return ERR_EQUIPMENT_RESP

    def getAndResetBuf(self):
        cmd_f = 'A0 03' + self.addr_num + '90'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, True)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('A0 04' + self.addr_num + '90'):
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
        cmd_f = 'A0 03 ' + self.addr_num + '93'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd, False)
        print('cmd back:', data)


class Lcd(threading.Thread):
    """
        1.frame: Head(0x7E) + Addr + Cmd + Len + Data + Check + End(0x68)
    """
    def __init__(self, addr, tcp_socket, queuetask, queuersl, event):
        threading.Thread.__init__(self)
        self.addr = addr
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
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        pkg = TransferPackage(code=200, eq_type=1, data={'rsl': rsl}, source=self.addr, msg_type=6)
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

    def __init__(self, addr: tuple, queuetask, queuersl, queue_push_data):
        threading.Thread.__init__(self)
        self.ip = addr[0]
        self.port = addr[1]
        self.isrunning = True
        self.queuetask = queuetask
        self.queuersl = queuersl
        self.queue_push_data = queue_push_data
        self.lock = threading.RLock()

    def run(self):
        while self.isrunning:
            self.lock.acquire()
            try:
                if not self.queuetask.empty():
                    task, args = self.queuetask.get()
                    rsl = methodcaller(task, *args)(self)
                    if rsl is not None:
                        self.queuersl.put(rsl)
                else:
                    time.sleep(40)
                    pkg = TransferPackage(code=206, eq_type=3, data={'user': 'sdsdfs'}, source=(self.ip, self.port), msg_type=3)
                    self.queue_push_data.put(pkg)
            finally:
                self.lock.release()
