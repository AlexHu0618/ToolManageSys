from myDB import MyDB
from myLogger import mylogger
from gateway_server import GatewayServer


def main():
    mydb = MyDB()
    myserver = None
    try:
        rsl = mydb.getAllServers()
        server_registered = rsl if rsl else None
        print('server_registered: ', server_registered)
        rsl2 = mydb.getAllClients()
        client_registered = rsl2 if rsl2 else None
        print('client_registered: ', client_registered)
        myserver = GatewayServer(8809, server_registered, client_registered)
        myserver.daemon = True
        myserver.start()
    except KeyboardInterrupt:
        mydb.close()
        myserver.stop()
        print('stop')
    finally:
        mydb.close()
        myserver.stop()
        print('stop')


if __name__ == '__main__':
    mylogger.info('START SERVER')
    main()
