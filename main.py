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
        myserver.join()
    except KeyboardInterrupt:
        mydb.close()
        myserver.stop()
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

# ### 此法不通，设置后不在当前进程生效。
# def set_lib_path():
#     """
#     自动设置ZK与HK的链接库查找路径到全局变量LD_LIBRARY_PATH
#     :return:
#     """
#     path_cur = os.path.abspath(os.path.dirname(__file__))
#     # for ZK
#     zk_lib_path = path_cur + '/util/libs/zk_lib'
#     zk_cmd = 'export LD_LIBRARY_PATH=' + zk_lib_path + ':$LD_LIBRARY_PATH'
#     os.system(zk_cmd)
#     # for HK
#     hk_lib_path1 = path_cur + '/util/libs/hkvision_lib/'
#     hk_lib_path2 = path_cur + '/util/libs/hkvision_lib/HCNetSDKCom/'
#     hk_cmd1 = 'export LD_LIBRARY_PATH=' + hk_lib_path1 + ':$LD_LIBRARY_PATH'
#     hk_cmd2 = 'export LD_LIBRARY_PATH=' + hk_lib_path2 + ':$LD_LIBRARY_PATH'
#     os.system(hk_cmd1)
#     os.system(hk_cmd2)


# def test():
#     get_epcs()


if __name__ == '__main__':
    mylogger.info('START SERVER')
    main()
