import socket


def server():
    # 创建socket对象
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 定义服务器的地址
    address = ('', 8809)
    server_sock.bind(address)

    # 监听请求
    server_sock.listen()

    # 建立长连接
    try:
        print('---多进程--等待客户端连接本服务器8809！--')
        while True:
            client_sock, addr = server_sock.accept()
    finally:
        server_sock.close()





if __name__ == '__main__':

