# 硬件产品预警布放相关
from ..core.type_map import *
from ..model.base import NET_DVR_TIME, NET_DVR_IPADDR
from ..core.const import *


# 报警设备信息结构体
class NET_DVR_ALARMER(Structure):
    _fields_ = [
        ("byUserIDValid", h_BYTE),
        ("bySerialValid", h_BYTE),
        ("byVersionValid", h_BYTE),
        ("byDeviceNameValid", h_BYTE),
        ("byMacAddrValid", h_BYTE),

        ("byLinkPortValid", h_BYTE),
        ("byDeviceIPValid", h_BYTE),
        ("bySocketIPValid", h_BYTE),
        ("lUserID", h_BYTE),
        ("sSerialNumber", h_BYTE * 48),

        ("dwDeviceVersion", h_DWORD),
        ("sDeviceName", h_CHAR * 32),
        ("byMacAddr", h_CHAR * 6),
        ("wLinkPort", h_WORD),
        ("sDeviceIP", h_CHAR * 128),

        ("sSocketIP", h_CHAR * 128),
        ("byIpProtocol", h_BYTE),
        ("byRes2", h_BYTE * 11)
    ]


# 布防
class NET_DVR_SETUPALARM_PARAM(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),
        ("byLevel", h_BYTE),
        ("byAlarmInfoType", h_BYTE),
        ("byRetAlarmTypeV40", h_BYTE),
        ("byRetDevInfoVersion", h_BYTE),
        ("byRetVQDAlarmType", h_BYTE),
        ("byFaceAlarmDetection", h_BYTE),
        ("bySupport", h_BYTE),
        ("byBrokenNetHttp", h_BYTE),
        ("wTaskNo", h_WORD),
        ("byDeployType", h_BYTE),
        ("byRes1", h_BYTE * 3),
        ("byAlarmTypeURL", h_BYTE),
        ("byCustomCtrl", h_BYTE)
    ]


# 门禁主机事件信息
class NET_DVR_ACS_EVENT_INFO(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),  # 结构体大小
        ("byCardNo", h_BYTE * ACS_CARD_NO_LEN),  # 卡号
        ("byCardType", h_BYTE),  # 卡类型：1- 普通卡，2- 残疾人卡，3- 黑名单卡，4- 巡更卡，5- 胁迫卡，6- 超级卡，7- 来宾卡，8- 解除卡，为0表示无效
        ("byWhiteListNo", h_BYTE),  # 白名单单号，取值范围：1~8，0表示无效
        ("byReportChannel", h_BYTE),  # 报告上传通道：1- 布防上传，2- 中心组1上传，3- 中心组2上传，0表示无效
        ("byCardReaderKind", h_BYTE),  # 读卡器类型：0- 无效，1- IC读卡器，2- 身份证读卡器，3- 二维码读卡器，4- 指纹头
        ("dwCardReaderNo", h_DWORD),  # 读卡器编号，为0表示无效
        ("dwDoorNo", h_DWORD),  # 门编号（或者梯控的楼层编号），为0表示无效（当接的设备为人员通道设备时，门1为进方向，门2为出方向）
        ("dwVerifyNo", h_DWORD),  # 多重卡认证序号，为0表示无效
        ("dwAlarmInNo", h_DWORD),  # 报警输入号，为0表示无效
        ("dwAlarmOutNo", h_DWORD),  # 报警输出号，为0表示无效
        ("dwCaseSensorNo", h_DWORD),  # 事件触发器编号
        ("dwRs485No", h_DWORD),  # RS485通道号，为0表示无效
        ("dwMultiCardGroupNo", h_DWORD),  # 群组编号
        ("wAccessChannel", h_WORD),  # 人员通道号
        ("byDeviceNo", h_BYTE),  # 设备编号，为0表示无效
        ("byDistractControlNo", h_BYTE),  # 分控器编号，为0表示无效
        ("dwEmployeeNo", h_DWORD),  # 工号，为0无效
        ("wLocalControllerID", h_WORD),  # 就地控制器编号，0-门禁主机，1-255代表就地控制器
        ("byInternetAccess", h_BYTE),  # 网口ID：（1-上行网口1,2-上行网口2,3-下行网口1）
        ("byType", h_BYTE),  # 防区类型，0:即时防区,1-24小时防区,2-延时防区,3-内部防区,4-钥匙防区,5-火警防区,6-周界防区,7-24小时无声防区,8-24小时辅助防区,9-24小时震动防区,10-门禁紧急开门防区,11-门禁紧急关门防区，0xff-无
        ("byMACAddr", h_BYTE),  # 物理地址，为0无效
        ("bySwipeCardType", h_BYTE),  # 刷卡类型，0-无效，1-二维码
        ("byMask", h_BYTE),  # 是否带口罩：0-保留，1-未知，2-不戴口罩，3-戴口罩
        ("dwSerialNo", h_DWORD),  # 事件流水号，为0无效
        ("byChannelControllerID", h_BYTE),  # 通道控制器ID，为0无效，1-主通道控制器，2-从通道控制器
        ("byChannelControllerLampID", h_BYTE),  # 通道控制器灯板ID，为0无效（有效范围1-255）
        ("byChannelControllerIRAdaptorID", h_BYTE),  # 通道控制器红外转接板ID，为0无效（有效范围1-255）
        ("byChannelControllerIREmitterID", h_BYTE),  # 通道控制器红外对射ID，为0无效（有效范围1-255)
        ("byRes", h_BYTE * 4)  # 保留，置为0
    ]


# 门禁主机报警信息结构体
class NET_DVR_ACS_ALARM_INFO(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),  # 结构体大小
        ("dwMajor", h_DWORD),  # 报警主类型
        ("dwMinor", h_DWORD),  # 报警次类型
        ("struTime", NET_DVR_TIME),  # 报警时间
        ("sNetUser", h_BYTE * MAX_NAMELEN),  # 网络操作的用户名
        ("struRemoteHostAddr", NET_DVR_IPADDR),  # 远程主机地址
        ("struAcsEventInfo", NET_DVR_ACS_EVENT_INFO),  # 报警信息详细参数
        ("dwPicDataLen", h_DWORD),  # 图片数据大小，不为0是表示后面带数据
        ("pPicData", h_CHAR_P),  # 图片数据缓冲区
        ("wInductiveEventType", h_WORD),  # 归纳事件类型，0-无效，客户端判断该值为非0值后，报警类型通过归纳事件类型区分，否则通过原有报警主次类型（dwMajor、dwMinor）区分
        ("byPicTransType", h_BYTE),  # 图片数据传输方式: 0-二进制；1-url
        ("byRes1", h_BYTE),  # 保留，置为0
        ("dwIOTChannelNo", h_DWORD),  # IOT通道号
        ("pAcsEventInfoExtend", h_CHAR_P),  # byAcsEventInfoExtend为1时，表示指向一个NET_DVR_ACS_EVENT_INFO_EXTEND结构体
        ("byAcsEventInfoExtend", h_BYTE),  # pAcsEventInfoExtend是否有效：0-无效，1-有效
        ("byTimeType", h_BYTE),  # 时间类型：0-设备本地时间，1-UTC时间（struTime的时间）
        ("byRes2", h_BYTE),  # 保留，置为0
        ("byAcsEventInfoExtendV20", h_BYTE),  # pAcsEventInfoExtendV20是否有效：0-无效，1-有效
        ("pAcsEventInfoExtendV20", h_CHAR_P),  # byAcsEventInfoExtendV20为1时，表示指向一个NET_DVR_ACS_EVENT_INFO_EXTEND_V20结构体
        ("byRes", h_BYTE * 4)  # 保留，置为0
    ]












