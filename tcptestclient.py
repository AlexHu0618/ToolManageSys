import socket


def start_tcp_client(ip, port):
    # create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, 23))

    failed_count = 0
    while True:
        try:
            print("start connect to server ")
            s.connect((ip, port))
            break
        except socket.error:
            failed_count += 1
            # print("fail to connect to server %d times" % failed_count)
            if failed_count == 100:
                return

    try:
        while True:
            rsl = s.recv(1024)
            print(rsl)
            data = bytes.fromhex('01  06  02  00  01  02  03  04  78')
            s.send(data)
    except KeyboardInterrupt:
        s.shutdown(2)
        s.close()
    finally:
        s.close()


if __name__ == '__main__':
    start_tcp_client('10.0.174.128', 8809)
