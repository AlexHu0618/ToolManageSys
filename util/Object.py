# define all the object for TCP client
import select

# class Equipment:
#     def __init__(self, str: ipaddr, port, str: type):
#         pass


class GravityShelf(object):
    """
        1.frame: Addr + Func + Register + Data + Check
    """
    intervals = {'0': 0.0001, '1': 0.0002, '2': 0.0005, '3': 0.001, '4': 0.002, '5': 0.005, '6': 0.01, '7': 0.02,
                 '8': 0.05, '9': 0.1, 'a': 0.2, 'b': 0.5, 'c': 1, 'd': 2, 'e': 5, 'A': 0.2, 'B': 0.5, 'C': 1,
                 'D': 2, 'E': 5}

    def __init__(self, tcp_socket):
        self.BUFFSIZE = 1024
        self.all_id = ()
        self.tcp_socket = tcp_socket
        self.addr_serial = {}

    def readWeight(self, addr: str):
        cmd_f = bytes.fromhex(addr + '05 02 05')
        lcr = sum(cmd_f) % 256
        cmd = cmd_f + lcr.to_bytes(length=1, byteorder='big', signed=False)
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[:3] == bytes.fromhex(addr + '0602'):
            interval = self.intervals[hex(data[4])[-1]]
            print(interval)
            scale = int.from_bytes(data[5:8], byteorder='big', signed=False)
            print(scale)
            value = scale * interval
            return value

    def getData(self, cmd):
        self.tcp_socket.send(cmd)
        print('waitting for cmd return')
        total_data = []
        self.tcp_socket.settimeout(1)

        try:
            while True:
                data = self.tcp_socket.recv(self.BUFFSIZE)
                if not data:
                    break
                else:
                    print(data)
                    total_data.append(data)
        except Exception as e:
            print(e)
        if len(total_data) == 1:
            return total_data[0]
        else:
            return total_data

    def readAllInfo(self):
        cmd = b'\x00\x05\x02\x05\x0C'
        data = self.getData(cmd)
        print('info back:', data)
        if data:
            for i in range(1, 64):
                if data[1:2] == bytes.fromhex('06 05'):
                    id = data[7:10]
                    self.all_id += id
            return self.all_id
        else:
            return 'timeout'

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
            return True
        else:
            print('failed')
            return False

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


class RfidR2000(object):
    """
        1.frame: Head(0xA0) + Len + Addr + Cmd + Data + Check
    """
    def __init__(self, tcp_socket):
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr = '01'
        self.ant_count = 8

    def check(self, cmd_f):
        # complement ---- (~sum + 1)
        cmd = bytes.fromhex(cmd_f)
        check = (sum(cmd) ^ 0xFF) + 1
        check_hex = bytes.fromhex(hex(check)[-2:])
        return check_hex

    def getData(self, cmd, timeout=1):
        self.tcp_socket.send(cmd)
        print('cmd sent: ', cmd)
        print('waitting for cmd return')
        total_data = []
        self.tcp_socket.settimeout(timeout)

        try:
            data = self.tcp_socket.recv(self.BUFFSIZE)
            total_data.append(data)
            # while True:
            #     data = self.tcp_socket.recv(self.BUFFSIZE)
            #     if not data:
            #         break
            #     else:
            #         print(data)
            #         total_data.append(data)
        except Exception as e:
            print(e)
        if len(total_data) == 1:
            return total_data[0]
        else:
            return total_data

    def setReaderAddr(self, addr_new):
        cmd_f = 'A0 04' + self.addr + '73' + addr_new
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        print(cmd)
        data = self.getData(cmd)
        if data[0:5] == bytes.fromhex('A0 04' + self.addr + '73 10'):
            self.addr = addr_new
            return True
        else:
            return False

    def setOutputPower(self, num='00', value=30):
        powers = self.getOutputPower()
        if powers:
            powers[int(num)] = value
            cmd_len = '0B' if self.ant_count == 8 else '07'
            cmd_f = 'A0 ' + cmd_len + self.addr + '76 ' + ' '.join(hex(p)[-2:] if p > 16 else ('0' + hex(p)[-1:]) for p in powers)
            print(cmd_f)
            check = self.check(cmd_f)
            cmd = bytes.fromhex(cmd_f) + check
            data = self.getData(cmd)
            print('cmd back:', data)
            if data[0:5] == bytes.fromhex('A0 04' + self.addr + '76 10'):
                return True
            else:
                return False
        else:
            return False

    def getOutputPower(self):
        cmd_f = 'A0 03 ' + self.addr + ' 97' if self.ant_count == 8 else ' 77'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('A0 04' + self.addr + ' 97' if self.ant_count == 8 else ' 77'):
            power = data[4]
            return [power for i in range(self.ant_count)]
        elif data[0:4] == bytes.fromhex('A0' + ('0B' if self.ant_count == 8 else '07') + self.addr + ' 97' if self.ant_count == 8 else ' 77'):
            return [data[i+4] for i in range(self.ant_count)]
        else:
            return []

    def getWorkAntenna(self):
        cmd_f = 'A0 03' + self.addr + '75'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        print(cmd)
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex(('A0 04' + self.addr + '75')):
            ant_id = data[4]
            return ant_id
        else:
            print('Fail to setWorkAntenna')
            return None

    def setWorkAntenna(self, ant_id='00'):
        cmd_f = 'A0 04' + self.addr + '74' + ant_id
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:5] == bytes.fromhex(('A0 04' + self.addr + '74 10')):
            return True
        else:
            print('Fail to setWorkAntenna')
            return False

    def inventory(self, ant_id='00'):
        # rsl = self.setWorkAntenna(ant_id)
        rsl = True
        if rsl:
            cmd_repeat = '05'
            cmd_f = 'A0 04' + self.addr + '80' + cmd_repeat
            check = self.check(cmd_f)
            cmd = bytes.fromhex(cmd_f) + check
            data = self.getData(cmd, 5)
            print('cmd back:', data)
            if data[0:5] == bytes.fromhex('A0 0C' + self.addr + '80' + ant_id):
                tag_count = int.from_bytes(data[5:7], byteorder='big', signed=False)
                return tag_count
        else:
            print('Fail to inventory')
            return None

    def getAndResetBuf(self):
        cmd_f = 'A0 03' + self.addr + '90'
        check = self.check(cmd_f)
        cmd = bytes.fromhex(cmd_f) + check
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('A0 04' + self.addr + '90'):
            print('ErrorCode: ', hex(data[4]))
            return None
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
        data = self.getData(cmd)
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


class Lcd(object):
    """
        1.frame: Head(0x7E) + Addr + Cmd + Len + Data + Check + End(0x68)
    """
    def __init__(self, tcp_socket):
        self.tcp_socket = tcp_socket
        self.BUFFSIZE = 1024
        self.addr = '00'

    def check(self, cmd_f):
        if isinstance(cmd_f, bytes):
            cmd = cmd_f
        else:
            cmd = bytes.fromhex(cmd_f)
        check = sum(cmd) % 256
        print(check)
        check_hex = hex(check)[-2:] if check > 15 else '0' + hex(check)[-1:]
        return check_hex

    def getData(self, cmd):
        self.tcp_socket.send(cmd)
        print('cmd sent: ', cmd)
        print('waitting for cmd return')
        total_data = []

        self.tcp_socket.settimeout(1)

        try:
            while True:
                data = self.tcp_socket.recv(self.BUFFSIZE)
                if not data:
                    break
                else:
                    total_data.append(data)
        except Exception as e:
            print(e)
        if len(total_data) == 1:
            return total_data[0]
        else:
            return total_data[-1]

    def checkBtn(self):
        cmd_f = '7E' + self.addr + '00 00'
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('7E' + self.addr + '00 01'):
            return True if data[4] == 1 else False
        else:
            return False

    def onLed(self, activate=True, pos='up'):
        cmd_acti = '01' if activate else '00'
        cmd_pos = '01' if pos == 'up' else '02'
        cmd_f = '7E' + self.addr + '01 02' + cmd_pos + cmd_acti
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('7E' + self.addr + '01 01'):
            return True if data[4] == 0 else False
        else:
            return False

    def showNum(self, num: int):
        number = num if num < 1000 else 999
        cmd_num = str(number).zfill(4)
        cmd_f = '7E' + self.addr + '02 02' + cmd_num
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        print(cmd)
        data = self.getData(bytes.fromhex(cmd))
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('7E' + self.addr + '02 01'):
            return True if data[4] == 0 else False
        else:
            return False

    def onBacklight(self, activate=True):
        cmd_data = '01' if activate else '00'
        cmd_f = '7E' + self.addr + '04 01' + cmd_data
        check = self.check(cmd_f)
        cmd = cmd_f + check + '68'
        data = self.getData(bytes.fromhex(cmd))
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('7E' + self.addr + '04 01'):
            return True if data[4] == 0 else False
        else:
            return False

    def showText(self, contents=[]):
        content = [bytes(cont, 'gb2312') if cont else b'' for cont in contents]
        cmd_l1 = b'\x01' + (len(content[0]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[0] + b'\x00'
        cmd_l2 = b'\x02' + (len(content[1]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[1] + b'\x00'
        cmd_l3 = b'\x03' + (len(content[2]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[2] + b'\x00'
        cmd_l4 = b'\x04' + (len(content[3]) + 1).to_bytes(length=1, byteorder='big', signed=False) + content[3] + b'\x00'
        length = len(cmd_l1 + cmd_l2 + cmd_l3 + cmd_l4)
        cmd_len = hex(length)[-2:] if length > 15 else ('0' + hex(length)[-1:])
        cmd_f = bytes.fromhex('7E' + self.addr + '03' + cmd_len) + cmd_l1 + cmd_l2 + cmd_l3 + cmd_l4
        print(cmd_f)
        check = self.check(cmd_f)
        cmd = cmd_f + bytes.fromhex(check + '68')
        data = self.getData(cmd)
        print('cmd back:', data)
        if data[0:4] == bytes.fromhex('7E' + self.addr + '03 01'):
            return True if data[4] == 0 else False
        else:
            return False



# class RfidJH2880:
#     """
#         1.frame: Head(0xE1) + Addr + Cmd + Len + Data + Check
#         2.respose: Head(0xE1) + Addr + Cmd + Len + Code + Data + Check
#     """
#     def __init__(self, addr, tcp_socket):
#         self.tcp_socket = tcp_socket
#         self.BUFFSIZE = 1024
#         self.addr = addr
#
#     def crc16(self, cmd_f):
#         cmd = bytes.fromhex(cmd_f)
#         check = sum(cmd) % 65536
#         check_hex = hex(check)[2:]
#         return check_hex if len(check_hex) > 3 else '0' + check_hex
#
#     def getData(self, cmd):
#         self.tcp_socket.send(cmd)
#         data = self.tcp_socket.recv(self.BUFFSIZE)
#         return data
#
#     def isReady(self):
#         cmd_f = 'E1' + self.addr + '01 00'
#         check = self.crc16(cmd_f)
#         cmd = cmd_f + check
#         data = self.getData(cmd)
#         print('cmd back:', data)
#         if data[0:3].hex() == ('E1' + self.addr + '01 01'):
#             if data[4].hex() == '28':
#                 return True
#             else:
#                 return False
#         else:
#             return False
