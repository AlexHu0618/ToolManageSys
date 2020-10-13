# from ctypes import *
#
# comm = cdll.LoadLibrary("/home/alex/C++/libs/libplcommpro.so")
#
# handle = comm.Connect(b'protocol=TCP,ipaddress=192.168.0.201,port=4370,timeout=2000,passwd=')
# # buff = create_string_buffer("b".encode('utf-8'), 1024)
# # rsl = comm.GetDeviceParam(handle, byref(buff), 1024, bytes('IPAddress,ReaderCount,MThreshold'.encode('utf-8')))
# # print(buff.value)
# rsl1 = comm.GetDeviceDataCount(handle, bytes('transaction'.encode('utf-8')))
# print(rsl1)
# size = rsl1 * 2000
# buff2 = create_string_buffer("q".encode('utf-8'), size)
# filter1 = b'Index=' + bytes(str(rsl1), encoding='utf8')
# rsl = comm.GetDeviceData(handle, byref(buff2), size, bytes('transaction'.encode('utf-8')), b'*', filter1, b'')
# # print(rsl)
# print(buff2.value)
# print(str(buff2.value, encoding='gb18030'))
# # buff3 = create_string_buffer("q".encode('utf-8'), 102400)
# # rsl = comm.GetRTLog(handle, byref(buff3), 102400)
# # print(rsl)
# # print(buff3.value)
# comm.Disconnect(handle)


import socket
import sys


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    addr = ('192.168.8.221', 9999)
    server_sock.bind(addr)
    try:
        server_sock.listen(1)
    except Exception as e:
        print(e)
        print("fail to listen on port %s" % e)
        sys.exit(1)
    while True:
        print('here')
        client_sock, addr = server_sock.accept()
        print(addr)
        break
    client_sock.close()


if __name__ == '__main__':
    main()
