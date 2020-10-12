from ctypes import *

comm = cdll.LoadLibrary("/home/alex/C++/libs/libplcommpro.so")

handle = comm.Connect(b'protocol=TCP,ipaddress=192.168.0.201,port=4370,timeout=2000,passwd=')
# buff = create_string_buffer("b".encode('utf-8'), 1024)
# rsl = comm.GetDeviceParam(handle, byref(buff), 1024, bytes('IPAddress,ReaderCount,MThreshold'.encode('utf-8')))
# print(buff.value)
rsl = comm.GetDeviceDataCount(handle, bytes('templatev10'.encode('utf-8')))
print(rsl)
size = rsl * 2000
buff2 = create_string_buffer("q".encode('utf-8'), size)
rsl = comm.GetDeviceData(handle, byref(buff2), size, bytes('templatev10'.encode('utf-8')), b'*', b'Pin=666', b'')
# print(rsl)
# print(buff2.value)
print(str(buff2.value, encoding='gb18030'))
# buff3 = create_string_buffer("q".encode('utf-8'), 102400)
# rsl = comm.GetRTLog(handle, byref(buff3), 102400)
# print(rsl)
# print(buff3.value)
comm.Disconnect(handle)
