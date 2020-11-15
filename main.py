from db.myDB import MyDB
from app.myLogger import mylogger
from app.gateway_server import GatewayServer
import time
from multiprocessing import Queue
from app.task_controler import TaskControler


def main():
    mydb = MyDB()
    myserver = None
    mycontroler = None
    # task_controler与gateway_server交互的全局队列
    q_task = Queue(50)
    q_rsl = Queue(50)
    try:
        rsl = mydb.getAllServers()
        server_registered = rsl if rsl else None
        print('server_registered: ', server_registered)
        rsl2 = mydb.getAllClients()
        client_registered = rsl2 if rsl2 else None
        print('client_registered: ', client_registered)
        myserver = GatewayServer(8809, server_registered, client_registered, q_task, q_rsl)
        myserver.start()
        mycontroler = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        mycontroler.start()
        while True:
            # time.sleep(1)
            pass
    except KeyboardInterrupt:
        mydb.close()
        myserver.stop()
        mycontroler.stop()
        print('stop')
    finally:
        mydb.close()
        myserver.stop()
        mycontroler.stop()
        print('stop')


if __name__ == '__main__':
    mylogger.info('START SERVER')
    main()
