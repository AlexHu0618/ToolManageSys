#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.options import define, options
from tornado.web import Application, RequestHandler
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

# 自定义配置项
define("port", type=int, default=8088)
define("debug", type=bool, default=True)


# 请求处理器
class IndexHandler(RequestHandler):
    def get(self):
        print("index handler get method")
        self.write("hello world")


class InitialHandler(RequestHandler):
    def get(self):
        print("Device initial")
        SN = self.get_query_argument('SN')
        pushver = self.get_query_argument('pushver')
        # options = self.get_query_argument('options')
        ip = self.request.remote_ip
        print(ip)
        print(SN, pushver)


# 创建应用
# 定义路由表
urls = [
    (r"/index", IndexHandler),
    (r"/iclock/cdata", InitialHandler)
]
# 定义应用配置
configs = dict(debug=options.debug)
# 指定路由和配置创建应用程序对象
app = Application(urls, configs)

# 程序主入口
if __name__ == "__main__":
    # 解析命令行参数
    options.parse_command_line()
    # 为应用创建HTTP服务器
    server = HTTPServer(app)
    print("http server start")
    # 为HTTP服务器设置监听端口
    server.listen(options.port)
    print("http server listen port %s" % options.port)
    # 开启事件循环接收客户端连接
    IOLoop.current().start()
