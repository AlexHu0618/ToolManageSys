# -*- coding: utf-8 -*-
# @Time    : 2/24/20 5:19 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: dbsession.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.1.0

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from settings.config import config_parser as conpar

CONF = conpar.read_yaml_file('mysql')
DB_URI = 'mysql+pymysql://{}:{}@{}:{}/{}?charset={}'.format(CONF['user'], CONF['password'], CONF['host'],
                                                            CONF['port'], CONF['database'], CONF['charset'])

# 创建一个engine引擎
engine = create_engine(DB_URI, echo=False, pool_size=200, pool_recycle=-1, pool_pre_ping=True)
# sessionmaker生成一个session类
Session = sessionmaker(bind=engine)
# 创建一个session实例
# dbSession = Session()
dbSession = scoped_session(Session)
# 创建一个模型基类
Base = declarative_base(engine)
