"""
1、如果是第一次运行，需要先运行文件sys_conf.py进行系统环境配置；
2、若1无效，则手动把ZK与HK的链接库路径加入"LD_LIBRARY_PATH";
3、设置成功，方能运行本程序。
"""
from db.myDB import MyDB
from app.myLogger import mylogger
from app.gateway_server import GatewayServer
from multiprocessing import Queue, RLock
from app.task_controler import TaskControler
from database.db_handler import get_all_equipments, get_epcs
import time
import os
import threading

progress = dict()


def ontime_progress_monitor(q_task, q_rsl):
    print('*********times out progress monitor**********')
    if not progress['gateway_server'].is_alive():
        print('progress gateway_server is not alive')
        mylogger.error('progress gateway_server is not alive')
        rsl = get_all_equipments()
        servers_registered = dict()  # {addr: (type, storeroom_id, uuid)}
        clients_registered = dict()
        for r_id, s_c in rsl.items():
            temp_servers = {k: (v[0], r_id, v[1]) for k, v in s_c['servers'].items()}
            servers_registered.update(temp_servers)
            temp_clients = {k: (v[0], r_id, v[1]) for k, v in s_c['clients'].items()}
            clients_registered.update(temp_clients)
        myserver_demo = GatewayServer(port=8809, servers_registered=servers_registered,
                                      clients_registered=clients_registered, queue_task=q_task, queue_rsl=q_rsl)
        myserver_demo.daemon = True
        myserver_demo.start()
        progress['gateway_server'] = myserver_demo
        mylogger.info('progress gateway_server is start again')
    if not progress['task_controler'].is_alive():
        print('progress task_controler is not alive')
        mylogger.error('progress task_controler is not alive')
        mycontroler_demo = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        mycontroler_demo.daemon = True
        mycontroler_demo.start()
        progress['task_controler'] = mycontroler_demo
        mylogger.info('progress task_controler is start again')
    thd_timer1 = threading.Timer(interval=60, function=ontime_progress_monitor, args=([q_task, q_rsl]))
    thd_timer1.start()


def main():
    mydb = MyDB()
    myserver = None
    mycontroler = None
    thd_timer = None
    # task_controler与gateway_server交互的全局队列
    q_task = Queue(50)
    q_rsl = Queue(50)
    try:
        rsl = get_all_equipments()
        servers_registered = dict()  # {addr: (type, storeroom_id, uuid)}
        clients_registered = dict()
        for r_id, s_c in rsl.items():
            temp_servers = {k: (v[0], r_id, v[1]) for k, v in s_c['servers'].items()}
            servers_registered.update(temp_servers)
            temp_clients = {k: (v[0], r_id, v[1]) for k, v in s_c['clients'].items()}
            clients_registered.update(temp_clients)
        myserver = GatewayServer(port=8809, servers_registered=servers_registered, clients_registered=clients_registered,
                                 queue_task=q_task, queue_rsl=q_rsl)
        mycontroler = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        myserver.daemon = True
        mycontroler.daemon = True
        myserver.start()
        progress['gateway_server'] = myserver
        mycontroler.start()
        progress['task_controler'] = mycontroler
        thd_timer = threading.Timer(interval=60, function=ontime_progress_monitor, args=([q_task, q_rsl]))
        thd_timer.start()
        thd_timer.join()
    except KeyboardInterrupt:
        mydb.close()
        myserver.stop()
        mycontroler.stop()
        thd_timer.cancel()
        while mycontroler.is_alive() or myserver.is_alive():
            time.sleep(1)
            print('thread--mycontroler/myserver is still alive')
    except Exception as e:
        print('exception from main', e)
        mylogger.error('exception from main: %s' % e)


# def test():
#     get_epcs()


if __name__ == '__main__':
    mylogger.info('START SYSTEM')
    print('PID--main:', os.getpid())
    mylogger.info('PID--main: %d' % os.getpid())
    main()
    print('SYSTOM IS OVER')
    mylogger.info('SYSTOM IS OVER')
