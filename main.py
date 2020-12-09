from db.myDB import MyDB
from app.myLogger import mylogger
from app.gateway_server import GatewayServer
from multiprocessing import Queue, RLock
from app.task_controler import TaskControler
from database.db_handler import get_all_equipments, get_epcs


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
        # print('servers_registered: ', servers_registered)
        # print('clients_registered: ', clients_registered)
        # # rsl = mydb.getAllServers()
        # # server_registered = rsl if rsl else None
        # # print('server_registered: ', server_registered)
        # # rsl2 = mydb.getAllClients()
        # # client_registered = rsl2 if rsl2 else None
        # # print('client_registered: ', client_registered)
        # # server_registered = {('192.168.0.201', 4370): 'entrance', ('192.168.0.117', 23): 'led'}
        # # client_registered = {('192.168.0.97', 26): 'gravity'}
        myserver = GatewayServer(port=8809, servers_registered=servers_registered, clients_registered=clients_registered,
                                 queue_task=q_task, queue_rsl=q_rsl)
        myserver.start()
        mycontroler = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        mycontroler.start()
        while True:
            pass
    except KeyboardInterrupt:
        # mydb.close()
        # myserver.stop()
        # mycontroler.stop()
        # print('stop')
        print('keyboard interrupt')
    except Exception as e:
        print(e)
        mylogger.error(e)
    finally:
        mydb.close()
        myserver.stop()
        mycontroler.stop()
        print('stop')


def test():
    get_epcs()


if __name__ == '__main__':
    mylogger.info('START SERVER')
    main()
    # test()
