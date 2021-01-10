SUCCESS = 200
TIMEOUT = 201

ERR_EQUIPMENT_RESP = 301
QUEUE_RSL_EMPTY = 302
EQUIPMENT_OFFLINE = 303
EQUIPMENT_ONLINE = 304
EQUIPMENT_DATA_UPDATE = 305

TASK_HANDLE_ERR = 401
BTN_CONFIRM_FROM_WEB = 402
BTN_CHECK_FROM_WEB = 403
USER_ENTRANCE_SUCCESS = 404

# option code
ENTRANCE_ADD_USER = 2100
ENTRANCE_REDUCE_USER = 2101
GATEWAY_ADD_NEW_EQUIPMENT = 5100
GATEWAY_REDUCE_EQUIPMENT = 5101



class TransferPackage(object):
    def __init__(self, target=None, code=None, eq_type=None, data=dict(), source=None, msg_type=None, storeroom_id=None, eq_id=None):
        self.uuid = None
        self.target = target
        self.code = code  # 状态码
        self.equipment_type = eq_type  # 1-重力；2-RFID；3-门禁；4-通道机；5-人脸机;6-LCD;7-触摸屏终端;
        self.data = data
        self.source = source
        self.storeroom_id = storeroom_id
        self.equipment_id = eq_id
        self.msg_type = msg_type  # 0-cmd_equipment_control; 1-cmd_gateway_setting; 2-nitification; 3-data_update; 4-response.

    def to_dict(self):
        return {'uuid': self.uuid, 'msg_type': self.msg_type, 'target': self.target, 'source': self.source, 'code': self.code,
                'data': self.data, 'equipment_type': self.equipment_type, 'storeroom_id': self.storeroom_id,
                'equipment_id': self.equipment_id}
