# -*- coding: utf-8 -*-
# @Time    : 9/7/20 3:15 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: config.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.0.0

logconfigs = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },

    "handlers": {

        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },

        "info_file_handler": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "INFO",
            "formatter": "simple",
            "filename": "./logs/info.log",
            "when": "midnight",
            "backupCount": 20,
            "encoding": "utf8",
            "filters": [
                "filter_by_name",
            ]
        },

        "error_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "simple",
            "filename": "./logs/errors.log",
            "maxBytes": 1024*1024*10,      # 日志大小10M
            "backupCount": 20,             # 最多保存20份日志，写完时轮转
            "encoding": "utf8"
        }
    },

    "filters": {
        "filter_by_name": {
            "class": "logging.Filter",
            "name": "root"
        }
    },

    "loggers": {
        "mymodule": {
            "level": "INFO",
            "handlers": [
                "info_file_handler",
                "error_file_handler"
            ],
            "propagate": "no"
        }
    },

        "root": {
            "level": "INFO",
            "handlers": [
                # "console",
                "info_file_handler",
                "error_file_handler"
            ]
        }
}