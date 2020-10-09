import socket
import sys
from Object import RfidR2000, Lcd

receive_count: int = 0


def start_tcp_client(ip, port):
    # create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    failed_count = 0
    while True:
        try:
            print("start connect to server ")
            s.connect((ip, port))
            break
        except socket.error:
            failed_count += 1
            print("fail to connect to server %d times" % failed_count)
            if failed_count == 100:
                return

    # send and receive
    while True:
        print("connect success")
        r2000 = RfidR2000(tcp_socket=s)
        lcd = Lcd(tcp_socket=s)

        # get the socket send buffer size and receive buffer size
        s_send_buffer_size = s.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        s_receive_buffer_size = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

        print("client TCP send buffer size is %d" % s_send_buffer_size)
        print("client TCP receive buffer size is %d" % s_receive_buffer_size)

        while True:
            # rsl = lcd.checkBtn()
            # print(rsl)
            # rsl = lcd.ledOn(False, 'down')
            # print(rsl)
            # rsl = lcd.showNum(256)
            # print(rsl)
            # rsl = lcd.onBacklight(True)
            # print(rsl)
            # text = ['控制', '电子标签地址: 88', '7e 01 02 01 01 83', 'oooo!']
            # rsl = lcd.showText(text)
            # print(rsl)
            # break
            rsl = r2000.getWorkAntenna()
            print(rsl)
            rsl = r2000.getOutputPower()
            print(rsl)
            # rsl = r2000.setOutputPower('00', 25)
            # print(rsl)
            # r2000.reset_inv_buf()
            rsl = r2000.inventory()
            print(rsl)
            # rsl = r2000.getAndResetBuf()
            # print(rsl)
            break
        break

    s.close()


if __name__ == '__main__':
    start_tcp_client('192.168.0.117', 26)
