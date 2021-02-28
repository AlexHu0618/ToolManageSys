import socket
import threading
import time
from multiprocessing import Process
import os


# def start_tcp_client(ip, port):
#     # create socket
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind((ip, 23))
#
#     failed_count = 0
#     while True:
#         try:
#             print("start connect to server ")
#             s.connect((ip, port))
#             print('success conn to ', ip, port)
#             break
#         except socket.error:
#             failed_count += 1
#             # print("fail to connect to server %d times" % failed_count)
#             if failed_count == 100:
#                 return
#
#     while True:
#         try:
#             rsl = s.recv(1024)
#             print(rsl)
#             data = bytes.fromhex('01  06  02  00  01  02  03  04  78')
#             s.send(data)
#         except BrokenPipeError:
#             while True:
#                 print("start connect to server ")
#                 s.connect((ip, port))
#                 print('success conn to ', ip, port)
#                 break
#         except KeyboardInterrupt:
#             s.shutdown(2)
#             s.close()
#         finally:
#             s.close()
#
#
# if __name__ == '__main__':
#     start_tcp_client('192.168.8.221', 8809)


# class test(threading.Thread):
#     def __init__(self):
#         threading.Thread.__init__(self)
#         self.lock = threading.RLock()
#         self.isrunning = True
#         self.counter = 0
#
#     def run(self):
#         thr_ontime = threading.Thread(target=self.show)
#         thr_ontime.daemon = True
#         thr_ontime.start()
#         while self.isrunning:
#             time.sleep(6)
#             print('still running')
#         print('run() is broken')
#
#     def show(self):
#         while self.isrunning:
#             time.sleep(5)
#             self.counter += 1
#             print('5s later')
#             if self.counter > 5:
#                 print('counter > 5')
#                 with self.lock:
#                     self.isrunning = False
#         print('show() is broken')

class test1(Process):
    def __init__(self):
        super().__init__()

    def run(self):
        try:
            print('it is test1--', os.getpid())
            while True:
                time.sleep(1)
                print('test1 is to stop')
        except Exception as e:
            print(e)
        print('\033[1;33m', 'stop test1', '\033[0m')


class test2(Process):
    def __init__(self):
        super().__init__()

    def run(self):
        try:
            print('it is test2--', os.getpid())
            time.sleep(4)
            print('test2 is to stop')
        except Exception as e:
            print(e)
        print('\033[1;33m', 'stop test2', '\033[0m')


def task(a, b):
    print('*********times out*********')
    if pros['test1'].is_alive():
        print('is_alive test1')
    else:
        print('is_alive not test1')
    #     test11 = test1()
    #     test11.daemon = True
    #     test11.start()
    #     pros['test1'] = test11
    if pros['test2'].is_alive():
        print('is_alive test2')
    else:
        print('is_alive not test2')
        print(a, b)
        test22 = test2()
        test22.daemon = True
        test22.start()
        pros['test2'] = test22
    thd_timer1 = threading.Timer(interval=2, function=task, args=([a, b]))
    thd_timer1.start()


pros = dict()


if __name__ == '__main__':
    try:
        a = 1
        b = 3
        print('start main--', os.getpid())
        test13 = test1()
        test23 = test2()
        test13.daemon = True
        test23.daemon = True
        test13.start()
        pros['test1'] = test13
        test23.start()
        pros['test2'] = test23
        thd_timer = threading.Timer(interval=2, function=task, args=([a, b]))
        thd_timer.start()
        thd_timer.join()
        # test1.join()
        # print('test1 is over')
        # test2.join()
        # print('test2 is over')
    except Exception as e:
        print('over by exception')
    print('all is over')
