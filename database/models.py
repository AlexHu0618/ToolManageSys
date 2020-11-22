# -*- coding: utf-8 -*-
# @Time    : 2/26/20 9:34 PM
# @Author  : Alex Hu
# @Contact : jthu4alex@163.com
# @FileName: database.py
# @Software: PyCharm
# @Blog    : http://www.gzrobot.net/aboutme
# @version : 0.1.0

from uuid import uuid4
from datetime import datetime
from string import printable

from pbkdf2 import PBKDF2
from sqlalchemy.orm import relationship
from sqlalchemy import (Column, Integer, String, Table, BLOB, Boolean, DateTime, ForeignKey, Date)
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
            print(e)
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
    def all(cls):
        return dbSession.query(cls).all()


role_user = Table('rela_role_user', Base.metadata,
                  Column('role_id', String(50), ForeignKey('role.uuid', ondelete='CASCADE', onupdate='CASCADE')),
                  Column('user_id', String(50), ForeignKey('user.uuid', ondelete='CASCADE', onupdate='CASCADE'))
                  )


class User(Base, MyBase):
    __tablename__ = 'user'
    uuid = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    login_name = Column(String(100), nullable=False)
    _password = Column('login_password', String(100))
    real_name = Column(String(100))
    code = Column(String(100))
    card_id = Column(String(100), default='')
    cellphone = Column(String(50))
    mail = Column(String(50))
    fingerprint = Column(BLOB)
    avatar = Column(BLOB)
    register_time = Column(DateTime, default=datetime.now)
    last_login_time = Column(DateTime)
    roles = relationship('Role', secondary=role_user, back_populates='users')

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

    @property
    def avatar(self):
        return self.avatar if self.avatar else "default_avatar.jpeg"

    @avatar.setter
    def avatar(self, image_data):
        class ValidationError(Exception):
            def __init__(self, message):
                super(ValidationError, self).__init__(message)
        if 64 < len(image_data) < 1024 * 1024:
            import imghdr
            import os
            ext = imghdr.what("", h=image_data)
            print(ext)
            print(self.uuid)
            if ext in ['png', 'jpeg', 'gif', 'bmp'] and not self.is_xss_image(image_data):
                if self.avatar and os.path.exists("static/images/useravatars/" + self.avatar):
                    os.unlink("static/images/useravatars/" + self.avatar)
                file_path = str("static/images/useravatars/" + self.uuid + '.' + ext)

                with open(file_path, 'wb') as f:
                    f.write(image_data)

                self.avatar = self.uuid + '.' + ext
            else:
                raise ValidationError("not in ['png', 'jpeg', 'gif', 'bmp']")
        else:
            raise ValidationError("64 < len(image_data) < 1024 * 1024 bytes")

    def is_xss_image(self, data):
        return all([char in printable for char in data[:16]])

    @classmethod
    def all(cls):
        return dbSession.query(cls).all()

    @classmethod
    def by_uuid(cls, uuid):
        return dbSession.query(cls).filter_by(uuid=uuid).first()

    @classmethod
    def by_name(cls, name):
        return dbSession.query(cls).filter_by(login_name=name).first()

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
    level = Column(Integer, nullable=False)  # 1-super_admin; 2-admin; 3-common.
    users = relationship('User', secondary=role_user, back_populates='roles')

    @classmethod
    def by_name(cls, name):
        return dbSession.query(cls).filter_by(name=name).first()

    @classmethod
    def by_uuid(cls, uuid):
        return dbSession.query(cls).filter_by(uuid=uuid).first()

    @classmethod
    def all(cls):
        return dbSession.query(cls).all()

    def update_users(self, users_id: list):
        for user in self.users:
            user.roles = []
        users = []
        for id in users_id:
            user = User.by_uuid(uuid=id)
            print(user.roles)
            user.roles = [Role.by_uuid(uuid=self.uuid)]
            users.append(user)
            print(user.roles)
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
    station_id = Column(String(50), ForeignKey('station.id'))

    station = relationship('Station', back_populates='storerooms')
    shelfs = relationship('Shelf', back_populates='storeroom')
    equipments = relationship('Equipment', back_populates='storeroom')


class Shelf(Base, MyBase):
    __tablename__ = 'shelf'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    type = Column(Integer)  # 1-重力；2-RFID
    row_num = Column(Integer)
    col_num = Column(Integer)
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'))

    storeroom = relationship('Storeroom', back_populates='shelfs')
    grids = relationship('Grid', back_populates='shelf')


class Grid(Base, MyBase):
    __tablename__ = 'grid'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    sensor_addr = Column(String(10), nullable=False)  # '0xFF'
    row_num = Column(Integer, nullable=False)  # location
    col_num = Column(Integer, nullable=False)
    type = Column(Integer, default=1)  # 0-工具；1-仪器；2-耗材
    power = Column(Integer)
    is_have_case = Column(Boolean, default=False)
    weight_case = Column(Integer, default=0)
    status = Column(Integer, default=0)  # 0-离线；1-正常；2-故障；
    total = Column(Integer, default=0)
    led_ip = Column(String(50))
    led_addr = Column(String(50))
    shelf_id = Column(String(50), ForeignKey('shelf.id'))
    equipment_id = Column(String(50), ForeignKey('equipment.id'))

    shelf = relationship('Shelf', back_populates='grids')
    equipment = relationship('Equipment', back_populates='grids')

    @classmethod
    def by_row_col(cls, shelf_id, row_num, col_num):
        return dbSession.query(cls).filter(cls.shelf_id == shelf_id, cls.row_num == row_num, cls.col_num == col_num).first()


class Equipment(Base, MyBase):
    __tablename__ = 'equipment'
    id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    ip = Column(String(100))
    port = Column(Integer)
    is_server = Column(Boolean, default=False)
    type = Column(Integer)  # 1-重力；2-RFID；3-门禁；4-通道机；5-人脸机
    status = Column(Integer, default=0)  # 0-离线；1-在线；
    in_out = Column(Integer, default=None)  # 0-入库方向；1-出库方向；
    last_offline_time = Column(DateTime, default=datetime.now)
    storeroom_id = Column(String(50), ForeignKey('storeroom.id'))

    storeroom = relationship('Storeroom', back_populates='equipments')
    grids = relationship('Grid', back_populates='equipment')

    @classmethod
    def by_addr(cls, ip, port):
        return dbSession.query(cls).filter(cls.ip == ip, cls.port == port).first()


# class Goods(Base, MyBase):
#     __tablename__ = 'goods'
#     id = Column(String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid4()))
#     name = Column(String(100), nullable=False)
#     code = Column(String(100), nullable=False)
#     model = Column(String(100))
#     type = Column(Integer)  # # 0-工具；1-仪器；2-耗材
#     check_cycle = Column(Integer)  # months
#     scrap_cycle = Column(Integer)  # months
#     date_produce = Column(Date)
#     monitor_way = Column(Integer)  # 1-重力；2-RFID
#     weight = Column(Integer)  # 单位g
#     is_need_check = Column(Boolean)
#     status = Column(Integer)  # 1-在库；2-出库；3-维修；4-检验；5-报废；
#     goods_pic = Column(BLOB)
#
#
# class Toolkit(Base, MyBase):
#     __tablename__ = 'toolkit'
