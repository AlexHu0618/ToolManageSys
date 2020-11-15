SUCCESS = 200
TIMEOUT_EQUIPMENT = 201
ERR_EQUIPMENT_RESP = 202
QUEUE_RSL_EMPTY = 203


class TransferPackage(object):
    def __init__(self, target=None):
        self.uuid = None
        self.target = target
        self.code = None
        self.data = dict()
        self.source = None
        self.type = None  # 0-command; 1-data; 2-nitification.
