from db.myDB import MyDB
from app.myLogger import mylogger
from app.gateway_server import GatewayServer
import time
from multiprocessing import Queue
from app.task_controler import TaskControler


# class TransferPackage(object):
#     def __init__(self, target=None):
#         self.target = target
#         self.code = None
#         self.data = dict()
#
#
# def task(q_task, q_rsl):
#     server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     addr = ('', 9999)
#     server_sock.bind(addr)
#     server_sock.listen()
#     while True:
#         client_sock, addr = server_sock.accept()
#         print('new conn: ', addr)
#         break
#     while True:
#         data = client_sock.recv(1024)
#         if data == b'exit':
#             break
#         else:
#             cmds = data.split(b'\r\n')
#             target = eval(cmds[0])
#             tp = TransferPackage(target=target)
#             tp.data['func'] = str(cmds[1], encoding='utf8')
#             tp.data['args'] = eval(cmds[2])
#             q_task.put(tp)
#             time.sleep(1)
#             if not q_rsl.empty():
#                 rsl = q_rsl.get()
#             else:
#                 rsl = QUEUE_RSL_EMPTY
#                 print('queue_rsl is None')
#             print('\033[1;36m', rsl, '\033[0m')
#             resp = bytes(str(rsl), encoding='utf8')
#             client_sock.send(resp)
#     client_sock.close()


def main():
    mydb = MyDB()
    myserver = None
    mycontroler = None
    q_task = Queue(50)
    q_rsl = Queue(50)
    try:
        rsl = mydb.getAllServers()
        # rsl = None
        server_registered = rsl if rsl else None
        print('server_registered: ', server_registered)
        rsl2 = mydb.getAllClients()
        # rsl2 = {('192.168.8.221', 23): 'G'}
        client_registered = rsl2 if rsl2 else None
        print('client_registered: ', client_registered)
        myserver = GatewayServer(8809, server_registered, client_registered, q_task, q_rsl)
        myserver.start()
        mycontroler = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        mycontroler.start()
        while True:
            time.sleep(1)
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
