# -*- coding: utf-8 -*-
# @Time    : 2/26/20 9:34 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: database.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.1.0

from uuid import uuid4
from datetime import datetime, date
from string import printable

from pbkdf2 import PBKDF2
from sqlalchemy.orm import relationship
from sqlalchemy import (Column, Integer, String, Table, BLOB, Boolean, DateTime, ForeignKey, Date, and_, or_)
from database.dbsession import Base
from database.dbsession import dbSession


class MyBase:
    def save(self):
        try:
            dbSession.add(self)  # self实例化对象代表就是u对象
            dbSession.commit()
            return 1
        except Exception as e:
            dbSession.rollback()
            print(e)
            return None

    # 定义静态类方法接收List参数
    @staticmethod
    def save_all(obj_list):
        try:
            dbSession.add_all(obj_list)
            dbSession.commit()
            return len(obj_list)
        except Exception as e:
            dbSession.rollback()
            print(e)
            return None

    # 定义删除方法
    def delete(self):
        try:
            dbSession.delete(self)
            dbSession.commit()
            return 1
        except Exception as e:
            dbSession.rollback()
            print(e)
            return None

    @staticmethod
    def delete_all(obj_list):
        try:
            [dbSession.delete(i) for i in obj_list]
            dbSession.commit()
            return 1
        except Exception as e:
            dbSession.rollback()
            print(e)
            return None

    def update(self, attr, value):
        try:
            self.__setattr__(attr, value)
            dbSession.commit()
            return 1
        except Exception as e:
            dbSession.rollback()
            print('DB update', e)
            return None

    @classmethod
    def by_name(cls, name):
        return dbSession.query(cls).filter_by(name=name).first()

    @classmethod
    def by_id(cls, id):
        return dbSession.query(cls).filter_by(id=id).first()

    @classmethod
    def by_code(cls, code):
        return dbSession.query(cls).filter_by(code=code).first()

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter_by(ip=ip, port=port).first()

    @classmethod
    def all(cls):
        return dbSession.query(cls).all()


role_user = Table('rela_role_user', Base.metadata,
                  Column('role_id', String(50), ForeignKey('role.uuid', ondelete='CASCADE', onupdate='CASCADE')),
                  Column('user_id', String(50), ForeignKey('user.uuid', ondelete='CASCADE', onupdate='CASCADE'))
                  )

entrance_user = Table('rela_entrance_user', Base.metadata,
                      Column('entrance_id', String(50), ForeignKey('entrance.id', ondelete='CASCADE', onupdate='CASCADE')),
                      Column('user_id', String(50), ForeignKey('user.uuid', ondelete='CASCADE', onupdate='CASCADE'))
                      )


class User(Base, MyBase):
    __tablename__ = 'user'
    uuid = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    login_name = Column(String(100), nullable=False)
    _password = Column('login_password', String(100))
    real_name = Column(String(100))
    code = Column(String(100), unique=True)  # 必须为数字型字符
    card_id = Column(String(100), default='')
    cellphone = Column(String(50))
    mail = Column(String(50))
    fingerprint = Column(BLOB)
    avatar = Column(BLOB)
    entrance_password = Column(String(100))
    register_time = Column(DateTime, default=datetime.now)
    last_login_time = Column(DateTime)
    roles = relationship('Role', secondary=role_user, back_populates='users')
    entrances = relationship('Entrance', secondary=entrance_user, back_populates='users')

    def _hash_password(self, password):
        return PBKDF2.crypt(password, iterations=0x2537)

    @property
    def login_password(self):
        return self._password

    @login_password.setter
    def login_password(self, password):
        self._password = self._hash_password(password)

    def auth_password(self, other_password):
        if self._password:
            return self.login_password == PBKDF2.crypt(other_password, self.login_password)
        else:
            return False

    # @property
    # def avatar(self):
    #     return self.avatar if self.avatar else "default_avatar.jpeg"
    #
    # @avatar.setter
    # def avatar(self, image_data):
    #     class ValidationError(Exception):
    #         def __init__(self, message):
    #             super(ValidationError, self).__init__(message)
    #     if 64 < len(image_data) < 1024 * 1024:
    #         import imghdr
    #         import os
    #         ext = imghdr.what("", h=image_data)
    #         print(ext)
    #         print(self.uuid)
    #         if ext in ['png', 'jpeg', 'gif', 'bmp'] and not self.is_xss_image(image_data):
    #             if self.avatar and os.path.exists("static/images/useravatars/" + self.avatar):
    #                 os.unlink("static/images/useravatars/" + self.avatar)
    #             file_path = str("static/images/useravatars/" + self.uuid + '.' + ext)
    #
    #             with open(file_path, 'wb') as f:
    #                 f.write(image_data)
    #
    #             self.avatar = self.uuid + '.' + ext
    #         else:
    #             raise ValidationError("not in ['png', 'jpeg', 'gif', 'bmp']")
    #     else:
    #         raise ValidationError("64 < len(image_data) < 1024 * 1024 bytes")
    #
    # def is_xss_image(self, data):
    #     return all([char in printable for char in data[:16]])

    @classmethod
    def all(cls):
        return dbSession.query(cls).all()

    @classmethod
    def by_uuid(cls, uuid):
        return dbSession.query(cls).filter_by(uuid=uuid).first()

    @classmethod
    def by_name(cls, name):
        return dbSession.query(cls).filter_by(login_name=name).first()

    @classmethod
    def by_card_id(cls, card_id):
        return dbSession.query(cls).filter_by(card_id=card_id).first()

    @property
    def locked(self):
        return self.is_locked



    @locked.setter
    def locked(self, value):
        assert isinstance(value, bool)
        self.is_locked = value

    def __repr__(self):
        return u'<User1 - id: %s  name: %s>' % (self.uuid, self.login_name)


class Role(Base, MyBase):
    __tablename__ = 'role'
    uuid = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False, default='common')
    level = Column(Integer, default=3)  # 1-super_admin; 2-admin; 3-common.
    users = relationship('User', secondary=role_user, back_populates='roles')

    @classmethod
    def by_name(cls, name):
        return dbSession.query(cls).filter_by(name=name).first()

    @classmethod
    def by_uuid(cls, uuid):
        return dbSession.query(cls).filter_by(uuid=uuid).first()

    @classmethod
    def by_level(cls, level):
        return dbSession.query(cls).filter_by(level=level).first()

    @classmethod
    def all(cls):
        return dbSession.query(cls).all()

    def update_users(self, users_id: list):
        for user in self.users:
            user.roles = []
        users = []
        for id in users_id:
            user = User.by_uuid(uuid=id)
            user.roles = [Role.by_uuid(uuid=self.uuid)]
            users.append(user)
        rsl = Role.save_all(users)
        return rsl

    def __repr__(self):
        return u'<Role - id: %s  name: %s>' % (self.uuid, self.name)


class Station(Base, MyBase):
    __tablename__ = 'station'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    location = Column(String(100))
    ip = Column(String(100))
    port = Column(Integer)

    storerooms = relationship('Storeroom', back_populates='station')


class Storeroom(Base, MyBase):
    __tablename__ = 'storeroom'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    location = Column(String(100))
    ip = Column(String(100))
    port = Column(Integer)
    manage_mode = Column(Integer, default=1)  # 1-模式1； 2-模式2；3-模式3；
    station_id = Column(String(50), ForeignKey('station.id'))

    station = relationship('Station', back_populates='storerooms')
    shelfs = relationship('Shelf', back_populates='storeroom')
    entrance = relationship('Entrance', back_populates='storeroom')
    channel_machines = relationship('ChannelMachine', back_populates='storeroom')
    inquiry_machines = relationship('InquiryMachine', back_populates='storeroom')
    code_scanners = relationship('CodeScanner', back_populates='storeroom')


class Entrance(Base, MyBase):
    __tablename__ = 'entrance'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    ip = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    name = Column(String(100))  # 设备名称
    code = Column(String(100))  # 设备编号
    login_name = Column(String(100))  # 登录用户名
    login_password = Column(String(100))  # 登录密码
    is_server = Column(Boolean, default=True)  # 是否作为服务端
    type = Column(Integer, default=1)  # 1-中控；2-海康威视
    status = Column(Integer, default=1)  # 0-离线；1-在线；
    last_offline_time = Column(DateTime, default=datetime.now)
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'), unique=True)

    storeroom = relationship('Storeroom', back_populates='entrance')
    users = relationship('User', secondary=entrance_user, back_populates='entrances')

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter(cls.ip == ip, cls.port == port).first()


class ChannelMachine(Base, MyBase):
    __tablename__ = 'channel_machine'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    ip = Column(String(100))
    port = Column(Integer)
    name = Column(String(100))
    code = Column(String(100))
    is_server = Column(Boolean, default=False)
    direction = Column(Integer, default=0)  # 0-进入；1-出去;2-in&out
    status = Column(Integer, default=1)  # 0-离线；1-在线；
    last_offline_time = Column(DateTime, default=datetime.now)
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'))

    storeroom = relationship('Storeroom', back_populates='channel_machines')

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter(cls.ip == ip, cls.port == port).first()


class CodeScanner(Base, MyBase):
    __tablename__ = 'code_scanner'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    ip = Column(String(100))
    port = Column(Integer)
    name = Column(String(100))
    code = Column(String(100))
    is_server = Column(Boolean, default=False)
    direction = Column(Integer, default=0)  # 0-进入；1-出去
    status = Column(Integer, default=1)  # 0-离线；1-在线；
    last_offline_time = Column(DateTime, default=datetime.now)
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'))

    storeroom = relationship('Storeroom', back_populates='code_scanners')

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter(cls.ip == ip, cls.port == port).first()


class Shelf(Base, MyBase):
    __tablename__ = 'shelf'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    type = Column(Integer)  # 1-重力；2-RFID
    row_num = Column(Integer, default=0)
    col_num = Column(Integer, default=0)
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'))

    storeroom = relationship('Storeroom', back_populates='shelfs')
    grids = relationship('Grid', back_populates='shelf')
    collectors = relationship('Collector', back_populates='shelf')
    indicators = relationship('Indicator', back_populates='shelf')


class Grid(Base, MyBase):
    __tablename__ = 'grid'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    collector_id = Column(String(50))
    sensor_addr = Column(String(10), default='01')  # '0xFF',RFID读写器地址号或重力传感器地址号
    row_num = Column(Integer, nullable=False)  # location
    col_num = Column(Integer, nullable=False)
    type = Column(Integer, default=1)  # 0-工具；1-仪器；2-耗材
    power = Column(Integer)
    is_have_case = Column(Boolean, default=False)
    weight_case = Column(Integer, default=0)
    status = Column(Integer, default=0)  # 0-离线；1-正常；2-传感器故障；3-位置错误；4-超过最大量程；
    total = Column(Integer, default=0)  # 重力格为总重量；RFID格为物资总个数；
    led_id = Column(String(50))
    led_addr = Column(String(10), default='01')  # '0xFF'
    antenna_num = Column(String(50))  # '00,01,02,03'
    is_multiple = Column(Boolean, default=False)
    min_inventory = Column(Integer, default=0)
    is_understock = Column(Boolean, default=False)
    shelf_id = Column(String(50), ForeignKey('shelf.id'))


    shelf = relationship('Shelf', back_populates='grids')
    goods = relationship('Goods', back_populates='grid')

    @classmethod
    def by_row_col(cls, shelf_id, row_num, col_num):
        return dbSession.query(cls).filter(cls.shelf_id == shelf_id, cls.row_num == row_num, cls.col_num == col_num).first()

    @classmethod
    def by_eqid_sensor(cls, eq_id, sensor_addr):
        return dbSession.query(cls).filter_by(collector_id=eq_id, sensor_addr=sensor_addr).first()

    @classmethod
    def by_eqid_antenna(cls, eq_id, antenna_num, addr_num):
        return dbSession.query(cls).filter(and_(cls.collector_id == eq_id, cls.sensor_addr == addr_num,
                                                cls.antenna_num.contains(antenna_num))).first()

    @classmethod
    def by_id_list(cls, id_list):
        return dbSession.query(cls).filter(cls.id.in_(id_list)).all()

    @classmethod
    def by_lcd_id(cls, lcd_id):
        return dbSession.query(cls).filter(cls.led_id == lcd_id).all()


class Collector(Base, MyBase):
    __tablename__ = 'collector'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    ip = Column(String(100))
    port = Column(Integer)
    is_server = Column(Boolean, default=False)
    type = Column(Integer)  # 1-重力； 2-RFIDR2000; 3-RFIDR2000FH；
    node_addrs = Column(String(100))  # 所连接的RFID读写器地址号或重力传感器地址号
    sensor_count = Column(Integer)  # 当前连接的传感器数量或天线数量
    status = Column(Integer, default=1)  # 0-离线；1-正常；
    last_offline_time = Column(DateTime, default=datetime.now)
    shelf_id = Column(String(50), ForeignKey('shelf.id'))

    shelf = relationship('Shelf', back_populates='collectors')

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter(cls.ip == ip, cls.port == port).first()


class Indicator(Base, MyBase):
    __tablename__ = 'indicator'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    ip = Column(String(100))
    port = Column(Integer)
    is_server = Column(Boolean, default=False)
    node_addrs = Column(String(100))  # 所连接的所有LED地址号
    module_count = Column(Integer, default=0)  # 当前连接的指示器模块数量
    status = Column(Integer, default=1)  # 0-离线；1-正常；
    last_offline_time = Column(DateTime, default=datetime.now)
    shelf_id = Column(String(50), ForeignKey('shelf.id'))

    shelf = relationship('Shelf', back_populates='indicators')

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter(cls.ip == ip, cls.port == port).first()


class Goods(Base, MyBase):
    __tablename__ = 'goods'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    parent_type = Column(String(100), default='')
    model_number = Column(String(100), default='')
    epc = Column(String(100), default=None)
    type = Column(Integer)  # 0-工具；1-仪器；2-耗材
    check_cycle = Column(Integer)  # months
    last_check_date = Column(Date, default=date.today)
    scrap_date = Column(Date)
    produce_date = Column(Date)
    monitor_way = Column(Integer)  # 1-重力；2-RFID
    weight = Column(Integer)  # 单个重量, 单位g
    count = Column(Integer, default=1)  # 数量
    status = Column(Integer, default=1)  # 1-正常；2-维修；3-检验；4-报废；
    is_in_store = Column(Boolean, default=True)  # RFID
    goods_pic = Column(BLOB)
    grid_id = Column(String(50), ForeignKey('grid.id'))

    grid = relationship('Grid', back_populates='goods')

    @classmethod
    def by_epc_list(cls, epcs: list):
        return dbSession.query(cls).filter(cls.epc.in_(epcs)).all()


class Toolkit(Base, MyBase):
    __tablename__ = 'toolkit'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    user_id = Column(String(100))
    goods_id = Column(String(100))
    count = Column(Integer)

    @classmethod
    def by_user(cls, user_id):
        return dbSession.query(cls, Goods).join(Goods, cls.goods_id == Goods.id).filter(cls.user_id == user_id).all()


class History_inbound_outbound(Base, MyBase):
    __tablename__ = 'history_inbound_outbound'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    user_id = Column(String(100))
    grid_id = Column(String(100))
    epc = Column(String(100))
    count = Column(Integer)
    outbound_datetime = Column(DateTime)
    inbound_datetime = Column(DateTime, default=None)
    status = Column(Integer, default=1)  # 0-已还；1-未还；2-催还;
    wrong_place_gid = Column(String(100), default=None)
    wrong_return_uid = Column(String(100), default=None)
    monitor_way = Column(Integer, default=2)  # 1-重力；2-RFID

    @classmethod
    def by_user_need_return(cls, user_id):
        return dbSession.query(cls).filter(and_(cls.user_id == user_id,
                                                or_(cls.status != 0, cls.wrong_place_gid.isnot(None)))).all()

    @classmethod
    def by_epc_need_return(cls, epc):
        return dbSession.query(cls).filter(cls.epc == epc, cls.status != 0).first()

    @classmethod
    def by_epcs_join_goods_tab(cls, epcs):
        return dbSession.query(cls).join(Goods, cls.epc == Goods.epc).filter(Goods.epc.in_(epcs)).all()


class InquiryMachine(Base, MyBase):
    __tablename__ = 'inquiry_machine'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    ip = Column(String(100))
    port = Column(Integer)
    name = Column(String(100))
    code = Column(String(100))
    direction = Column(Integer, default=0)  # 0-进入；1-出去
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'))

    storeroom = relationship('Storeroom', back_populates='inquiry_machines')
