#!/usr/bin/env python
# -*- coding:utf-8 -*-

import socket
import select
import queue
import threading
import time


class GatewayEpoll(threading.Thread):
    def __init__(self, name: str, addr: tuple, timeout: int, queuesend, queuerecv, alladdrs: list):
        threading.Thread.__init__(self)
        self.name = name
        self.serversocket = None
        self.timeout = timeout
        self.queuesend = queuesend
        self.queuerecv = queuerecv
        self.epoll = None
        self.message_queues = None
        self.fd_to_socket = None
        self.addr_fd_socket = dict()
        self.addr = addr
        self.alladdrs = alladdrs
        self.config()
        self.isrunning = True

    def config(self):
        # 创建socket对象
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置IP地址复用
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 绑定IP地址
        self.serversocket.bind(self.addr)
        # 监听，并设置最大连接数
        self.serversocket.listen(10)
        print("服务器启动成功，监听IP：", self.addr)
        # 服务端设置非阻塞
        self.serversocket.setblocking(False)
        # 创建epoll事件对象，后续要监控的事件添加到其中
        self.epoll = select.epoll()
        # 注册服务器监听fd到等待读事件集合
        self.epoll.register(self.serversocket.fileno(), select.EPOLLIN)
        # 保存连接客户端消息的字典，格式为{}
        self.message_queues = {}
        # 文件句柄到所对应对象的字典，格式为{句柄：对象}
        self.fd_to_socket = {self.serversocket.fileno(): self.serversocket, }

    def run(self):
        while self.isrunning:
            print("等待活动连接......")
            if not self.queuesend.empty():
                data = self.queuesend.get()
                sock = self.addr_fd_socket[data['addr']][1]
                fd = self.addr_fd_socket[data['addr']][0]
                if fd in self.fd_to_socket.keys():
                    self.message_queues[sock].put(data['data'])
                    self.epoll.modify(fd, select.EPOLLOUT)
            # 轮询注册的事件集合，返回值为[(文件句柄，对应的事件)，(...),....]
            events = self.epoll.poll(self.timeout)
            if not events:
                print("epoll超时无活动连接，重新轮询......")
                continue
            print("有", len(events), "个新事件，开始处理......")

            for fd, event in events:
                socket = self.fd_to_socket[fd]
                # 如果活动socket为当前服务器socket，表示有新连接
                if socket == self.serversocket:
                    connection, address = self.serversocket.accept()
                    print("新连接：", address)
                    # 新连接socket设置为非阻塞
                    connection.setblocking(False)
                    # 注册新连接fd到待读事件集合
                    self.epoll.register(connection.fileno(), select.EPOLLIN)
                    # 把新连接的文件句柄以及对象保存到字典
                    self.fd_to_socket[connection.fileno()] = connection
                    # 以新连接的对象为键值，值存储在队列中，保存每个连接的信息
                    self.message_queues[connection] = queue.Queue()
                    # ###
                    self.addr_fd_socket[address] = (connection.fileno(), connection)
                    self.alladdrs.append(address)
                # 关闭事件
                elif event & select.EPOLLHUP:
                    print('client close')
                    # 在epoll中注销客户端的文件句柄
                    self.epoll.unregister(fd)
                    # 关闭客户端的文件句柄
                    self.fd_to_socket[fd].close()
                    # 在字典中删除与已关闭客户端相关的信息
                    del self.fd_to_socket[fd]
                    # ##
                    del self.addr_fd_socket[socket.getpeername()]
                    self.alladdrs.remove(socket.getpeername())
                # 可读事件
                elif event & select.EPOLLIN:
                    # 接收数据
                    data = socket.recv(1024)
                    if data:
                        print("收到数据：", data, "客户端：", socket.getpeername())
                        # 将数据放入对应客户端的字典
                        # self.message_queues[socket].put(data)
                        # # 修改读取到消息的连接到等待写事件集合(即对应客户端收到消息后，再将其fd修改并加入写事件集合)
                        # self.epoll.modify(fd, select.EPOLLOUT)
                        # # ##
                        # self.queuerecv.put({'addr': socket.getpeername, 'data': data})
                    # 客户端主动关闭
                    else:
                        print('client close')
                        # 在epoll中注销客户端的文件句柄
                        self.epoll.unregister(fd)
                        # 关闭客户端的文件句柄
                        self.fd_to_socket[fd].close()
                        # 在字典中删除与已关闭客户端相关的信息
                        del self.fd_to_socket[fd]
                        # ##
                        del self.addr_fd_socket[socket.getpeername()]
                        self.alladdrs.remove(socket.getpeername())
                # 可写事件
                elif event & select.EPOLLOUT:
                    try:
                        # 从字典中获取对应客户端的信息
                        msg = self.message_queues[socket].get_nowait()
                    except queue.Empty:
                        print(socket.getpeername(), " queue empty")
                        # 修改文件句柄为读事件
                        self.epoll.modify(fd, select.EPOLLIN)
                    else:
                        print("发送数据：", msg, "to 客户端：", socket.getpeername())
                        # 发送数据
                        socket.send(msg)
        # 在epoll中注销服务端文件句柄
        self.epoll.unregister(self.serversocket.fileno())
        # 关闭epoll
        self.epoll.close()
        # 关闭服务器socket
        self.serversocket.close()
        print('Server has been closed!')

    def stop(self):
        self.isrunning = False


if __name__ == '__main__':
    try:
        threadA = MyEpollServer('myserver', ('192.168.8.221', 8809), 10)
        threadA.start()
        threadA.join()
    except KeyboardInterrupt:
        threadA.stop()
