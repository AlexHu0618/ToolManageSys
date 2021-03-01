from .models2 import Storeroom, Goods, History_inbound_outbound, Grid
import copy
import re
from app.myLogger import mylogger


def get_all_equipments():
    """
    1、分别获取门禁、扫码枪、通道机、采集器、LED；
    :return: 
    """
    # {'storeroom_id': {'clients': {equipment_addr: (type, uuid), }, 'servers': {equipment_addr: (type, uuid), }}, }
    storeroom_equipment_dict = dict()
    all_stroerooms = Storeroom.all()
    if all_stroerooms is not None:
        for storeroom in all_stroerooms:
            clients_servers = {'clients': dict(), 'servers': dict()}
            get_all_entrances(storeroom=storeroom, clients_servers=clients_servers)
            get_all_code_scanners(storeroom=storeroom, clients_servers=clients_servers)
            get_all_channel_machine(storeroom=storeroom, clients_servers=clients_servers)
            get_all_collectors(storeroom=storeroom, clients_servers=clients_servers)
            get_all_led(storeroom=storeroom, clients_servers=clients_servers)
            if clients_servers['clients'] is not None or clients_servers['servers'] is not None:
                storeroom_equipment_dict[storeroom.id] = clients_servers
    return storeroom_equipment_dict


def get_all_entrances(storeroom, clients_servers):
    type_name = {1: 'entrance_zk', 2: 'entrance_hk'}
    entrances = storeroom.entrance
    if entrances is not None:
        for entrance in entrances:
            if check_ip(entrance.ip):
                if entrance.is_server is True:
                    clients_servers['servers'][(entrance.ip, entrance.port)] = (type_name[entrance.type], entrance.id)
                else:
                    clients_servers['clients'][(entrance.ip, entrance.port)] = (type_name[entrance.type], entrance.id)
            else:
                mylogger.warning('wrong IP of entrance ip--%s' % entrance.ip)


def get_all_code_scanners(storeroom, clients_servers):
    scanners = storeroom.code_scanners
    if scanners is not None:
        for scanner in scanners:
            if check_ip(scanner.ip):
                if scanner.is_server is True:
                    clients_servers['servers'][(scanner.ip, scanner.port)] = ('code_scan', scanner.id)
                else:
                    clients_servers['clients'][(scanner.ip, scanner.port)] = ('code_scan', scanner.id)
            else:
                mylogger.warning('wrong IP of code_scanner ip--%s' % scanner.ip)


def get_all_collectors(storeroom, clients_servers):
    type_name = {1: 'gravity', 2: 'rfid2000', 3: 'rfid2000fh'}
    shelfs = storeroom.shelfs
    if shelfs is not None:
        for shelf in shelfs:
            collectors = shelf.collectors
            if collectors is not None:
                for collector in collectors:
                    if check_ip(collector.ip):
                        if collector.is_server is True:
                            clients_servers['servers'][(collector.ip, collector.port)] = (type_name[collector.type], collector.id)
                        else:
                            clients_servers['clients'][(collector.ip, collector.port)] = (type_name[collector.type], collector.id)
                    else:
                        mylogger.warning('wrong IP of collector ip--%s' % collector.ip)

                        
def get_all_channel_machine(storeroom, clients_servers):
    channels = storeroom.channel_machines
    if channels is not None:
        for channel in channels:
            if check_ip(channel.ip):
                if channel.is_server is True:
                    clients_servers['servers'][(channel.ip, channel.port)] = ('channel_machine', channel.id)
                else:
                    clients_servers['clients'][(channel.ip, channel.port)] = ('channel_machine', channel.id)
            else:
                mylogger.warning('wrong IP of channel_machine ip--%s' % channel.ip)


def get_all_led(storeroom, clients_servers):
    shelfs = storeroom.shelfs
    if shelfs is not None:
        for shelf in shelfs:
            indicators = shelf.indicators
            if indicators is not None:
                for indicator in indicators:
                    if check_ip(indicator.ip):
                        if indicator.is_server is True:
                            clients_servers['servers'][(indicator.ip, indicator.port)] = ('led', indicator.id)
                        else:
                            clients_servers['clients'][(indicator.ip, indicator.port)] = ('led', indicator.id)
                    else:
                        mylogger.warning('wrong IP of led ip--%s' % indicator.ip)


def check_ip(ip: str):
    compile_ip = re.compile(
        '^(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')
    if compile_ip.match(ip):
        return True
    else:
        return False


def get_epcs():
    # epcs = ['E200001B190D01322730658E', 'E200001A50110141044072D2', '201909250000000000000013', '201909250000000000000006']
    # epc = Goods.by_rfid_uid(epcs=epcs)
    # print([e.rfid_uid for e in epc])
    eq_id = 'a0c7c6b4-c246-42ff-83a0-53d3bf1ca9f5'
    ant_num = '03'
    grid = Grid.by_eqid_antenna(eq_id=eq_id, antenna_num=ant_num)
    print(grid.antenna_num)
