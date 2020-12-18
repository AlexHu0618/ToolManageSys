import pymysql
from settings.config import config_parser as conpar


class MyDB(object):
    def __init__(self):
        CONF = conpar.read_yaml_file('mysql')
        self.__db = pymysql.connect(CONF['host'], CONF['user'], CONF['password'], CONF['database'])
        self.__cursor = self.__db.cursor()

    def getAllClients(self):
        sql = 'select * from %s where isserver=0' % ('equipments_registered_info_test')

        try:
            self.__cursor.execute(sql)
            rsl = self.__cursor.fetchall()
            data_back = {(i[1], i[2]): i[3] for i in rsl}
            return data_back
        except Exception as e:
            print(e)
            self.__db.rollback()
            return None

    def getAllServers(self):
        sql = "select * from %s where isserver=1" % ('equipments_registered_info_test')

        try:
            self.__cursor.execute(sql)
            rsl = self.__cursor.fetchall()
            data_back = {(i[1], i[2]): i[3] for i in rsl}
            return data_back
        except Exception as e:
            print(e)
            self.__db.rollback()
            return None

    def close(self):
        self.__db.close()

