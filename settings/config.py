# @Contact : jthu4alex@163.com
# @FileName: config.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.1.0

import os
from ruamel import yaml
import ruamel
import warnings


class ConfigYaml(object):
    def __init__(self, file):
        """
        get target file
        :param file:
        """
        self.file = os.path.join(os.path.dirname(os.path.realpath(__file__)), file)

    def read_yaml_file(self, key=None):
        """
        to read yaml data
        :return:
        """
        warnings.simplefilter('ignore', ruamel.yaml.error.UnsafeLoaderWarning)
        with open(self.file, 'r', encoding='utf-8') as f:
            rsl = yaml.load_all(f.read())
            for i in rsl:
                if key is not None and key in i.keys():
                    return i[key]
                else:
                    return i

    def write_yaml_file(self, *data):
        """
        to write yaml data
        :param data:
        :return:
        """
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                yaml.dump_all(data,
                              f,
                              Dumper=yaml.RoundTripDumper)
                print("successful for writing!")
        except Exception as e:
            print(f"raise error{e}")
        finally:
            f.close()


config_parser = ConfigYaml('config.yml')


settings = dict(
    template_path=os.path.join(os.path.dirname(__file__), "../template"),
    static_path=os.path.join(os.path.dirname(__file__), "../static"),
    debug=True,
    cookie_secret='QQ23ti!#',  # cookie加密方式
    login_url='/login',  # auth  指定默认的路径
    xsrf_cookies=False,  # 防止跨域攻击
    # pycket配置信息
    pycket={
        'engine': 'redis',
        'storage': {
            'host': 'localhost',
            'port': 6379,
            'db_sessions': 1,
            'db_notifications': 11,
            'max_connections': 2 ** 31,
        },
        'cookies': {
            'expires_days': 1,  # 设置过期时间
            'max_age': 5000
        }
    }
)
