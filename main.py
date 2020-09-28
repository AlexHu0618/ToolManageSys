from GatewayEpoll import GatewayEpoll
from Object import GravityShelf
from myLogger import mylogger
import queue
import threading
import time

QUEUE_SEND = queue.Queue(1000)
QUEUE_RECV = queue.Queue(1000)
ALL_ADDRS = list()


def senddata():
    g = GravityShelf(QUEUE_SEND)
    while True:
        print('All address: ', ALL_ADDRS)
        time.sleep(10)
        data = g.readWeight('01')
        print('put data: ', data)
        QUEUE_SEND.put({'addr': ('192.168.0.97', 26), 'data': data})


if __name__ == '__main__':
    shelfs = [{'addr': ('192.168.0.97', 26), 'type': 'GravityShelf'}, ]
    serverthread = GatewayEpoll('MyEpoll', ('0.0.0.0', 8809), 5, QUEUE_SEND, QUEUE_RECV, ALL_ADDRS)
    try:
        serverthread.start()
        threadB = threading.Thread(target=senddata)
        threadB.start()
        mylogger.info('Start PullServer')
        threadB.join()
        serverthread.join()
    except KeyboardInterrupt:
        serverthread.stop()
        mylogger.info('Stop PullServer')
