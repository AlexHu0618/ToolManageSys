import socket
from threading import Thread
from queue import Queue
from operator import methodcaller
import time
from Object2 import GravityShelf, RfidR2000, Lcd, EntranceGuard
from myDB import MyDB

### {(ip, port): (thread, queuetask, queuersl), }
EQUIPMENTS = dict()


def connserver(servers):
    for k, v in servers.items():
        print("start to connect server ")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        failed_count = 0
        client_type = v
        queuetask = Queue(50)
        queuersl = Queue(50)
        thread = None
        while True:
            try:
                if client_type == 'guard':
                    thread = EntranceGuard(k, queuetask, queuersl)
                else:
                    s.connect(k)
                    if client_type == 'G':
                        thread = GravityShelf(s, queuetask, queuersl)
                    elif client_type == 'L':
                        thread = Lcd(s, queuetask, queuersl)
                    elif client_type == 'R':
                        thread = RfidR2000(s, queuetask, queuersl)
                    else:
                        pass
                if thread:
                    thread.daemon = True
                    thread.start()
                    EQUIPMENTS[k] = (thread, queuetask, queuersl, client_type)
                    print('客户端(%s)已成功连接。。' % str(k))
                break
            except socket.error:
                failed_count += 1
                # print("fail to connect to server %d times" % failed_count)
                if failed_count == 10:
                    print("fail to connect to server %s" % str(k))
                    break


def server(clients):
    # 创建socket对象
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 定义服务器的地址
    address = ('', 8809)
    server_sock.bind(address)

    # 监听请求
    server_sock.listen()

    # 建立长连接
    try:
        print('---多进程--等待客户端连接本服务器8809！--')
        while True:
            client_sock, addr = server_sock.accept()

            # 由于线程创建是在循环里创建和启动的
            # 因此每循环一次就会产生一个线程
            queuetask = Queue(50)
            queuersl = Queue(50)
            thread = None
            client_type = clients[addr] if addr in clients.keys() else None
            if client_type == 'G':
                thread = GravityShelf(client_sock, queuetask, queuersl)
            elif client_type == 'L':
                thread = Lcd(client_sock, queuetask, queuersl)
            elif client_type == 'R':
                thread = RfidR2000(client_sock, queuetask, queuersl)
            else:
                pass
            if thread:
                thread.daemon = True
                thread.start()
                EQUIPMENTS[addr] = (thread, queuetask, queuersl, client_type)
                print('客户端(%s)已成功连接。。' % str(addr))
    finally:
        server_sock.close()


def cmd():
    while True:
        time.sleep(1)
        for (k, v) in EQUIPMENTS.items():
            qt = v[1]
            qr = v[2]
            if v[3] == 'G':
                # qt.put('readAllInfo')
                qt.put(('readWeight', ('0a',)))
                print('send cmd to ', k)
            elif v[3] == 'R':
                qt.put(('getOutputPower', ()))
                print('send cmd to ', k)
            elif v[3] == 'L':
                qt.put(('onLed', (True,)))
                print('send cmd to ', k)
            elif v[3] == 'guard':
                qt.put(('getDeviceParam', ()))
                print('send cmd to ', k)
            else:
                pass
            if not qr.empty():
                data = qr.get()
                print(k, ' back data: ', data)
                if data == 'timeout':
                    print(k, ' timeout')
            else:
                print(k, ' qr is empty!')


if __name__ == '__main__':
    mydb = MyDB()
    try:
        rsl = mydb.getAllServers()
        server_registered = rsl if rsl else None
        print('server_registered: ', server_registered)
        if server_registered:
            connserver(server_registered)
        rsl = mydb.getAllClients()
        client_registered = rsl if rsl else None
        print('client_registered: ', client_registered)
        if client_registered:
            threadA = Thread(target=server, args=(client_registered,))
            threadA.start()
            cmd()
            threadA.join()
        else:
            cmd()
    except KeyboardInterrupt:
        mydb.close()
        print('stop')
    finally:
        mydb.close()
        print('stop')
