from multiprocessing import Process
import threading
import socket
import time
# from app.globalvar import *
from concurrent.futures import ThreadPoolExecutor
import struct


class TaskControler(Process):
    def __init__(self, queue_task, queue_rsl):
        super().__init__()
        self.sock = None
        self.q_task = queue_task
        self.q_rsl = queue_rsl
        self.isrunning = True

    def run(self):
        thread_conn = threading.Thread(target=self._monitorconn)
        thread_result = threading.Thread(target=self._return_result)
        thread_conn.daemon = True
        thread_result.daemon = True
        thread_conn.start()
        thread_result.start()
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
                    print('waitting for new connection')
                    client_sock, addr = server_sock.accept()
                    self.sock = client_sock
                    print('new conn: ', addr)
                    break
                while True:
                    # data = client_sock.recv(1024)
                    length_data = client_sock.recv(4)
                    if length_data == b'exit':
                        break
                    elif len(length_data) == 0:
                        print('client: ', addr, ' was offline')
                        raise BrokenPipeError
                    else:
                        # self.puttask(data=data)
                        length = struct.unpack('i', length_data)[0]
                        data = client_sock.recv(length)
                        print(time.asctime(), 'recv: ', data)
                        client_sock.send(b'I got the command')
                # with ThreadPoolExecutor(max_workers=5) as tpool:
                #     while True:
                #         data = client_sock.recv(1024)
                #         if data == b'exit':
                #             break
                #         elif len(data) == 0:
                #             print('client: ', addr, ' was offline')
                #             raise BrokenPipeError
                #         else:
                #             self.waitfor_resp(data=data, clientsock=client_sock)
            except (OSError, BrokenPipeError):
                continue
            except Exception as e:
                print(e)
                break
        server_sock.close()

    def waitfor_resp(self, data, clientsock):
        cmds = data.split(b'\r\n')
        target = eval(cmds[0])
        tp = TransferPackage(target=target)
        tp.data['func'] = str(cmds[1], encoding='utf8')
        tp.data['args'] = eval(cmds[2])
        self.q_task.put(tp)
        time.sleep(0.5)
        if not self.q_rsl.empty():
            # rsl = self.q_rsl.get()
            self._return_result()
        else:
            rsl = QUEUE_RSL_EMPTY
            print('queue_rsl is None')
        print('\033[1;36m', rsl, '\033[0m')
        resp = bytes(str(rsl), encoding='utf8')
        clientsock.send(resp)

    def puttask(self, data):
        # package to transferpackage and put into task queue
        cmds = data.split(b'\r\n')
        if len(cmds) > 2:
            target = eval(cmds[0])
            tp = TransferPackage(target=target)
            tp.data['func'] = str(cmds[1], encoding='utf8')
            tp.data['args'] = eval(cmds[2])
        else:
            tp = TransferPackage()
            tp.data['func'] = str(cmds[0], encoding='utf8')
            tp.data['args'] = eval(cmds[1])
        self.q_task.put(tp)

    def _return_result(self):
        while self.isrunning:
            try:
                transfer_package = self.q_rsl.get()
                target = transfer_package.target
                data = transfer_package.data['rsl']
                resp = 'target:' + str(target) + ', data: ' + str(data)
                self.sock.send(bytes(resp, encoding='utf8'))
            except (OSError, BrokenPipeError):
                continue
            except Exception as e:
                print(e)
                break

    def stop(self):
        self.isrunning = False


if __name__ == '__main__':
    from queue import Queue

    mycontroler = None
    q_task = Queue(50)
    q_rsl = Queue(50)
    try:
        mycontroler = TaskControler(queue_task=q_task, queue_rsl=q_rsl)
        mycontroler.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mycontroler.stop()
        print('stop')
    finally:
        mycontroler.stop()
        print('stop')