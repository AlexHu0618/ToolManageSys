import threading

# queueoperation = {'type': 'GravityShelf', 'addr': ('192.168.0.220', 23), 'operation': 'read', 'thread': < >}


class ProtocolParser(threading.Thread):
    def __init__(self, name: str, queueoperation, queuesend, queuerecv):
        self.name = name
        self.isrunning = True
        self.queuesend = queuesend
        self.queuerecv = queuerecv
        self.threadin = None

    def run(self):
        """
        1、判断指令类型与方向，并送入相对应的子解析器；
        2、把解析后的指令放入发送队列或者返回相应操作指令线程；
        :return:
        """
        while self.isrunning:
            pass

    def stop(self):
        self.isrunning = False
