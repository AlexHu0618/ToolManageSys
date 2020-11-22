from .models2 import Storeroom
import copy


def get_all_equipments():
    # {store_id: {'client': {equipment_addr: type}, 'server': {equipment_addr: type}}, }
    storeroom_equipment_dict = dict()
    all_stroerooms = Storeroom.all()
    if all_stroerooms is not None:
        for sr in all_stroerooms:
            client = dict()
            server = dict()
            get_all_entrances(storeroom=sr, client=client, server=server)
            get_all_code_scanners(storeroom=sr, client=client, server=server)
            get_all_shelfs(storeroom=sr, client=client, server=server)
            client_server = dict()
            if client is not None:
                client_server['client'] = copy.deepcopy(client)
            if server is not None:
                client_server['server'] = copy.deepcopy(server)
            if client_server is not None:
                storeroom_equipment_dict[sr.id] = client_server
    return storeroom_equipment_dict


def get_all_entrances(storeroom, client, server):
    entrance = storeroom.entrance
    if entrance is not None:
        if entrance.is_server is True:
            server[(entrance.ip, entrance.port)] = 'guard'
        else:
            client[(entrance.ip, entrance.port)] = 'guard'


def get_all_code_scanners(storeroom, client, server):
    scanner = storeroom.code_scanners
    if scanner is not None:
        for sn in scanner:
            if sn.is_server is True:
                server[(sn.ip, sn.port)] = 'code_scan'
            else:
                client[(sn.ip, sn.port)] = 'code_scan'


def get_all_shelfs(storeroom, client, server):
    shelfs = storeroom.shelfs
    if shelfs is not None:
        for sh in shelfs:
            collectors = sh.collectors
            if collectors is not None:
                for col in collectors:
                    if col.is_server is True:
                        server[(col.ip, col.port)] = 'gravity' if col.type == 1 else 'rfid'
                    else:
                        client[(col.ip, col.port)] = 'gravity' if col.type == 1 else 'rfid'