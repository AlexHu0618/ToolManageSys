SUCCESS = 200
TIMEOUT_EQUIPMENT = 201
ERR_EQUIPMENT_RESP = 202
QUEUE_RSL_EMPTY = 203
EQUIPMENT_OFFLINE = 204
EQUIPMENT_ONLINE = 205
EQUIPMENT_DATA_UPDATE = 206


class TransferPackage(object):
    def __init__(self, target=None, code=None, eq_type=None, data=dict(), source=None, msg_type=None):
        self.uuid = None
        self.target = target
        self.code = code
        self.equipment_type = eq_type  # 1-重力；2-RFID；3-门禁；4-通道机；5-人脸机
        self.data = data
        self.source = source
        self.msg_type = msg_type  # 0-cmd_equipment_control; 1-cmd_gateway_setting; 2-nitification; 3-response.

    def get_all(self):
        return {'uuid': self.uuid, 'msg_type': self.msg_type, 'target': self.target, 'source': self.source, 'code': self.code,
                'data': self.data, 'equipment_type': self.equipment_type}
