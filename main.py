from myDB import MyDB
from myLogger import mylogger
from gateway_server import GatewayServer
import time
# from queue import Queue
from multiprocessing import Process, Queue
import socket


def task(q_task, q_rsl):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    addr = ('', 9999)
    server_sock.bind(addr)
    server_sock.listen()
    while True:
        client_sock, addr = server_sock.accept()
        print('new conn: ', addr)
        break
    while True:
        data = client_sock.recv(1024)
        cmd = str(data, encoding='utf8')
        print('cmd: ', cmd)
        q_task.put((cmd, ('192,168.0.120', 23, 'G', True)))
        if not q_rsl.empty():
            rsl = q_rsl.get()
            print(rsl)
        else:
            print('queue_rsl is None')


def main():
    mydb = MyDB()
    myserver = None
    q_task = Queue(50)
    q_rsl = Queue(50)
    try:
        rsl = mydb.getAllServers()
        server_registered = rsl if rsl else None
        print('server_registered: ', server_registered)
        rsl2 = mydb.getAllClients()
        client_registered = rsl2 if rsl2 else None
        print('client_registered: ', client_registered)
        # queue_task = Queue(50)
        # queue_rsl = Queue(50)
        myserver = GatewayServer(8809, server_registered, client_registered, q_task, q_rsl)
        myserver.start()
        p = Process(target=task, args=(q_task, q_rsl))
        p.daemon = True
        p.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mydb.close()
        myserver.stop()
        print('stop')
    finally:
        mydb.close()
        myserver.stop()
        print('stop')


if __name__ == '__main__':
    mylogger.info('START SERVER')
    main()
