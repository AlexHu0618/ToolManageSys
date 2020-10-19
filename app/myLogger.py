# -*- coding: utf-8 -*-
# @Time    : 9/7/20 3:15 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: myLogger.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.0.0

from config import config
import logging
import logging.config


def setup_logging():
    if "logconfigs" in dir(config):  # 如果配置文件中有配置变量就读取，否则使用默认配置
        logging.config.dictConfig(config.logconfigs)
    else:
        print("The default logging config was used!")
        logging.basicConfig(level=logging.DEBUG,
                            format='[%(asctime)s] %(levelname)s [%(funcName)s: %(filename)s, %(lineno)d] %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', filename='logging.log', filemode='a')
    return logging.getLogger()


mylogger = setup_logging()
