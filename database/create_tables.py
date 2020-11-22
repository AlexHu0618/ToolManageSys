# -*- coding: utf-8 -*-
# @Time    : 2/25/20 10:51 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: create_tables.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.1.0

from database.dbsession import engine
from database.dbsession import Base


def create_tables():
    print('------------create_all-------------')
    Base.metadata.create_all(engine)
    print('------------create_end-------------')
