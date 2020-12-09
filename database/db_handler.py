from .models2 import Storeroom, Goods, History_inbound_outbound, Grid
import copy


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
    entrance = storeroom.entrance
    if entrance is not None:
        if entrance.is_server is True:
            clients_servers['servers'][(entrance.ip, entrance.port)] = ('entrance', entrance.id)
        else:
            clients_servers['clients'][(entrance.ip, entrance.port)] = ('entrance', entrance.id)


def get_all_code_scanners(storeroom, clients_servers):
    scanners = storeroom.code_scanners
    if scanners is not None:
        for scanner in scanners:
            if scanner.is_server is True:
                clients_servers['servers'][(scanner.ip, scanner.port)] = ('code_scan', scanner.id)
            else:
                clients_servers['clients'][(scanner.ip, scanner.port)] = ('code_scan', scanner.id)


def get_all_collectors(storeroom, clients_servers):
    type_name = {1: 'gravity', 2: 'rfid2000', 3: 'rfid2000fh'}
    shelfs = storeroom.shelfs
    if shelfs is not None:
        for shelf in shelfs:
            collectors = shelf.collectors
            if collectors is not None:
                for collector in collectors:
                    if collector.is_server is True:
                        clients_servers['servers'][(collector.ip, collector.port)] = (type_name[collector.type], collector.id)
                    else:
                        clients_servers['clients'][(collector.ip, collector.port)] = (type_name[collector.type], collector.id)

                        
def get_all_channel_machine(storeroom, clients_servers):
    channels = storeroom.channel_machines
    if channels is not None:
        for channel in channels:
            if channel.is_server is True:
                clients_servers['servers'][(channel.ip, channel.port)] = ('channel_machine', channel.id)
            else:
                clients_servers['clients'][(channel.ip, channel.port)] = ('channel_machine', channel.id)


def get_all_led(storeroom, clients_servers):
    shelfs = storeroom.shelfs
    if shelfs is not None:
        for shelf in shelfs:
            indicators = shelf.indicators
            if indicators is not None:
                for indicator in indicators:
                    if indicator.is_server is True:
                        clients_servers['servers'][(indicator.ip, indicator.port)] = ('led', indicator.id)
                    else:
                        clients_servers['clients'][(indicator.ip, indicator.port)] = ('led', indicator.id)


def get_epcs():
    # epcs = ['E200001B190D01322730658E', 'E200001A50110141044072D2', '201909250000000000000013', '201909250000000000000006']
    # epc = Goods.by_rfid_uid(epcs=epcs)
    # print([e.rfid_uid for e in epc])
    eq_id = 'a0c7c6b4-c246-42ff-83a0-53d3bf1ca9f5'
    ant_num = '03'
    grid = Grid.by_eqid_antenna(eq_id=eq_id, antenna_num=ant_num)
    print(grid.antenna_num)
