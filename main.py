"""
如果是第一次运行，需要先运行文件sys_conf.py进行系统环境配置, 再运行本文件；
"""
from db.myDB import MyDB
from app.myLogger import mylogger
from app.gateway_server import GatewayServer
from multiprocessing import Queue, RLock
from app.task_controler import TaskControler
from database.db_handler import get_all_equipments, get_epcs
import time


def main():
    mydb = MyDB()
    myserver = None
    mycontroler = None
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
        myserver.start()
        mycontroler.start()
        mycontroler.join()
        # while True:
        #     pass
    except KeyboardInterrupt:
        # mydb.close()
        # myserver.stop()
        mycontroler.stop()
        while mycontroler.is_alive():
            time.sleep(1)
            print('thread is still alive')
    except Exception as e:
        print(e)
        mylogger.error(e)
    # finally:
    #     mydb.close()
    #     myserver.stop()
    #     mycontroler.stop()
    #     print('stop')


def test():
    get_epcs()


if __name__ == '__main__':
    mylogger.info('START SERVER')
    main()
    # test()
