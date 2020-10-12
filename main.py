from myDB import MyDB
from myLogger import mylogger
from gateway_server import GatewayServer
import time
from queue import Queue
from multiprocessing import Process


def task():
    time.sleep(10)


def main():
    mydb = MyDB()
    myserver = None
    try:
        rsl = mydb.getAllServers()
        server_registered = rsl if rsl else None
        print('server_registered: ', server_registered)
        rsl2 = mydb.getAllClients()
        client_registered = rsl2 if rsl2 else None
        print('client_registered: ', client_registered)
        queue_task = Queue(50)
        queue_rsl = Queue(50)
        myserver = GatewayServer(8809, server_registered, client_registered, queue_task, queue_rsl)
        myserver.start()
        time.sleep(10)
        queue_task.put(('add_new', ('192,168.0.120', 23, 'G', True)))
        time.sleep(10)
        if not queue_rsl.empty():
            rsl = queue_rsl.get()
            print(rsl)
        else:
            print('queue_rsl is None')
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
