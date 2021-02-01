import socket
import threading
import time


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


class test(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.lock = threading.RLock()
        self.isrunning = True
        self.counter = 0

    def run(self):
        thr_ontime = threading.Thread(target=self.show)
        thr_ontime.daemon = True
        thr_ontime.start()
        while self.isrunning:
            time.sleep(6)
            print('still running')
        print('run() is broken')

    def show(self):
        while self.isrunning:
            time.sleep(5)
            self.counter += 1
            print('5s later')
            if self.counter > 5:
                print('counter > 5')
                with self.lock:
                    self.isrunning = False
        print('show() is broken')


if __name__ == '__main__':
    thr = test()
    thr.start()
    thr.join()
