from multiprocessing import Process
import threading
import socket
import time
from globalvar import *


class TransferPackage(object):
    def __init__(self, target=None):
        self.target = target
        self.code = None
        self.data = dict()


class TaskControler(Process):
    def __init__(self, queue_task, queue_rsl):
        super().__init__()
        self.sock = None
        self.q_task = queue_task
        self.q_rsl = queue_rsl
        self.isrunning = True

    def run(self):
        thread_conn = threading.Thread(target=self._monitorconn)
        thread_conn.daemon = True
        thread_conn.start()
        while self.isrunning:
            pass

    def _monitorconn(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = ('', 9999)
        server_sock.bind(addr)
        server_sock.listen(1)
        while self.isrunning:
            try:
                while True:
                    print('waitting for connection')
                    client_sock, addr = server_sock.accept()
                    print('new conn: ', addr)
                    break
                while True:
                    data = client_sock.recv(1024)
                    if data == b'exit':
                        break
                    else:
                        cmds = data.split(b'\r\n')
                        target = eval(cmds[0])
                        tp = TransferPackage(target=target)
                        tp.data['func'] = str(cmds[1], encoding='utf8')
                        tp.data['args'] = eval(cmds[2])
                        self.q_task.put(tp)
                        time.sleep(1)
                        if not self.q_rsl.empty():
                            rsl = self.q_rsl.get()
                        else:
                            rsl = QUEUE_RSL_EMPTY
                            print('queue_rsl is None')
                        print('\033[1;36m', rsl, '\033[0m')
                        resp = bytes(str(rsl), encoding='utf8')
                        client_sock.send(resp)
            except (OSError, BrokenPipeError):
                print('client: ', addr, 'was offline\r\n try to reconnect')
                continue
            except Exception as e:
                print(e)
                break
        server_sock.close()

    def stop(self):
        self.isrunning = False
