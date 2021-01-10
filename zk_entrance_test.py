from ctypes import *
import time


# buff = create_string_buffer("b".encode('utf-8'), 1024)
# rsl = comm.GetDeviceParam(handle, byref(buff), 1024, bytes('IPAddress,ReaderCount,MThreshold'.encode('utf-8')))
# print(buff.value)
###############################################
# get auth event
def get_auth_event():
    if handle != 0:
        rsl1 = comm.GetDeviceDataCount(handle, bytes('transaction'.encode('utf-8')))
        print(rsl1)
        size = rsl1 * 2000
        buff2 = create_string_buffer("q".encode('utf-8'), size)
        filter1 = b'Index=' + bytes(str(rsl1), encoding='utf8')
        rsl = comm.GetDeviceData(handle, byref(buff2), size, bytes('transaction'.encode('utf-8')), b'*', filter1, b'')
        print(rsl)
        print(str(buff2.value, encoding='gb18030'))
##########################################
# # get userauthorize
def get_userauthorize():
    rsl = comm.GetDeviceDataCount(handle, bytes('userauthorize'.encode('utf-8')))
    print(rsl)
    size = rsl * 2000
    buff = create_string_buffer("q".encode('utf-8'), size)
    user = '7777'
    filter = b'Pin=' + bytes(user, encoding='utf8')
    rsl = comm.GetDeviceData(handle, byref(buff), size, bytes('userauthorize'.encode('utf-8')), b'*', filter, b'')
    print('rsl = ', rsl)
    print(str(buff.value, encoding='gb18030'))
# ######################################
# get fingerprint
def get_fingerprint():
    rsl = comm.GetDeviceDataCount(handle, bytes('templatev10'.encode('utf-8')))
    print(rsl)
    size = rsl * 2000
    buff = create_string_buffer("q".encode('utf-8'), size)
    user = '7777'
    filter = b'Pin=' + bytes(user, encoding='utf8')
    rsl = comm.GetDeviceData(handle, byref(buff), size, bytes('templatev10'.encode('utf-8')), b'*', filter, b'')
    print('rsl = ', rsl)
    print(str(buff.value, encoding='gb18030'))
##########################################
# get user
def get_user():
    rsl1 = comm.GetDeviceDataCount(handle, bytes('user'.encode('utf-8')))
    print(rsl1)
    size = rsl1 * 2000
    buff2 = create_string_buffer("q".encode('utf-8'), size)
    user = '7777'
    filter1 = b'Pin=' + bytes(user, encoding='utf8')
    rsl = comm.GetDeviceData(handle, byref(buff2), size, bytes('user'.encode('utf-8')), b'*', filter1, b'')
    print('rsl = ', rsl)
    print(str(buff2.value, encoding='gb18030'))
##########################################
# # set user
def set_user():
    p_table = create_string_buffer(b'user')
    data = 'Pin=7777\tCardNo=12345\tName=test\tDisable=0'
    str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
    rsl = comm.SetDeviceData(handle, p_table, str_buf, b'')
    print(rsl)
    if rsl == 0:
        print('success to set user')
    else:
        print('fail to set user')
# ###################################################
# # set fingerprint
def set_fingerprint():
    username = '7777'
    finger_id = 6  # 0~9
    with open("/home/alex/ZKFingerSDK/C++/data/template.txt", "r") as f:  # 打开文件
        template = f.read()  # 读取文件
    data = 'Pin=' + username + '\tFingerID=' + str(finger_id) + '\tTemplate=' + template + '\tValid=1'
    p_table = create_string_buffer(b'templatev10')
    str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
    rsl = comm.SetDeviceData(handle, p_table, str_buf, b'')
    print(rsl)
    if rsl == 0:
        print('success to set fingerprint')
    else:
        print('fail to set fingerprint')
# ##############################################
# # set userauthorize
def set_userauthorize():
    p_table = create_string_buffer(b'userauthorize')
    data = 'Pin=7777\tAuthorizeTimezoneId=1\tAuthorizeDoorId=1'
    str_buf = create_string_buffer(bytes(data, encoding='utf-8'))
    rsl = comm.SetDeviceData(handle, p_table, str_buf, b'')
    print(rsl)
    if rsl == 0:
        print('success to set userauthorize')
    else:
        print('fail to set userauthorize')
# #############################################
# delete user
def delete_user():
    tables = [b'userauthorize', b'user', b'templatev10']
    rsl_all = True
    pin = '7777'
    filter2 = b'Pin=' + bytes(pin, encoding='utf8')
    for t in tables:
        p_table = create_string_buffer(t)
        rsl = comm.DeleteDeviceData(handle, p_table, filter2, b'')
        print(rsl)
        if rsl < 0:
            rsl_all = False
    print('success' if rsl_all else 'false')



# import socket
# import sys
#
#
# def main():
#     server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     addr = ('192.168.8.221', 9999)
#     server_sock.bind(addr)
#     try:
#         server_sock.listen(1)
#     except Exception as e:
#         print(e)
#         print("fail to listen on port %s" % e)
#         sys.exit(1)
#     while True:
#         print('here')
#         client_sock, addr = server_sock.accept()
#         print(addr)
#         break
#     client_sock.close()
#
#
if __name__ == '__main__':

    comm = cdll.LoadLibrary("/home/alex/C++/libs/libplcommpro.so")

    handle = comm.Connect(b'protocol=TCP,ipaddress=192.168.0.201,port=4370,timeout=2000,passwd=')
    print(handle)

    # comm1 = cdll.LoadLibrary("/home/alex/C++/libs/libplcommpro.so")
    # handle1 = comm1.Connect(b'protocol=TCP,ipaddress=192.168.0.202,port=4370,timeout=2000,passwd=')
    # print(handle1)
    get_auth_event()
    time.sleep(10)
    get_auth_event()
    # get_user()
    # get_userauthorize()
    # get_fingerprint()
    #
    # set_user()
    # set_userauthorize()
    # set_fingerprint()

    # delete_user()
    if handle != 0:
        comm.Disconnect(handle)

    # comm1.Disconnect(handle1)
