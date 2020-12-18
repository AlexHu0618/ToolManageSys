# 硬件产品基础结构体定义
# 包含初始化SDK,用户注册设备等相关结构体
from hkws.core.const import *
from hkws.core.type_map import *


# 设置sdk加载路劲
class NET_DVR_LOCAL_SDK_PATH(Structure):
    _fields_ = [
        ("sPath", h_BYTE * 256),
        ("byRes", h_BYTE * 128)
    ]


# 登录参数结构体
class NET_DVR_USER_LOGIN_INFO(Structure):
    _fields_ = [
        ("sDeviceAddress", h_BYTE * 129),  # 设备地址，IP或者普通域名
        ("byUseTransport", h_BYTE),  # 是否启用能力透传 0：不启动，默认  1：启动
        ("wPort", h_WORD),  # 设备端口号
        ("sUserName", h_BYTE * 64),  # 登录用户名
        ("sPassword", h_BYTE * 64),  # 登录密码
        # ("fLoginResultCallBack",)  #

        ("bUseAsynLogin", h_BOOL),  # 是否异步登录, 0:否 1:是
        ("byProxyType", h_BYTE),  # 代理服务器类型：0- 不使用代理，1- 使用标准代理，2- 使用EHome代理

        # 是否使用UTC时间：
        # 0 - 不进行转换，默认；
        # 1 - 输入输出UTC时间，SDK进行与设备时区的转换；
        # 2 - 输入输出平台本地时间，SDK进行与设备时区的转换
        ("byUseUTCTime", h_BYTE),
        # 登录模式(不同模式具体含义详见“Remarks”说明)：
        # 0- SDK私有协议，
        # 1- ISAPI协议，
        # 2- 自适应（设备支持协议类型未知时使用，一般不建议）
        ("byLoginMode", h_BYTE),
        # ISAPI协议登录时是否启用HTTPS(byLoginMode为1时有效)：
        # 0 - 不启用，
        # 1 - 启用，
        # 2 - 自适应（设备支持协议类型未知时使用，一般不建议）
        ("byHttps", h_BYTE),
        # 代理服务器序号，添加代理服务器信息时相对应的服务器数组下表值
        ("iProxyID", h_LONG),
        # 保留，置为0
        ("byRes3", h_BYTE * 120),
    ]


# 设备参数结构体。
class NET_DVR_DEVICEINFO_V30(Structure):
    _fields_ = [
        ("sSerialNumber", h_BYTE * 48),  # 序列号
        ("byAlarmInPortNum", h_BYTE),  # 模拟报警输入个数
        ("byAlarmOutPortNum", h_BYTE),  # 模拟报警输出个数
        ("byDiskNum", h_BYTE),  # 硬盘个数
        ("byDVRType", h_BYTE),  # 设备类型，详见下文列表
        ("byChanNum", h_BYTE),  # 设备模拟通道个数，数字(IP)通道最大个数为byIPChanNum + byHighDChanNum*256
        ("byStartChan", h_BYTE),  # 模拟通道的起始通道号，从1开始。数字通道的起始通道号见下面参数byStartDChan
        ("byAudioChanNum", h_BYTE),  # 设备语音对讲通道数
        ("byIPChanNum", h_BYTE),
        # 设备最大数字通道个数，低8位，搞8位见byHighDChanNum. 可以根据ip通道个数是否调用NET_DVR_GetDVRConfig (
        # 配置命令NET_DVR_GET_IPPARACFG_V40)获得模拟和数字通道的相关参数
        ("byZeroChanNum", h_BYTE),  # 零通道编码个数
        ("byMainProto", h_BYTE),  # 主码流传输协议类型： 0 - private, 1 - rtsp, 2- 同时支持私有协议和rtsp协议去留（默认采用私有协议取流）
        ("bySubProto", h_BYTE),  # 字码流传输协议类型： 0 - private , 1 - rtsp , 2 - 同时支持私有协议和rtsp协议取流 （默认采用私有协议取流）

        # 能力，位与结果为0表示不支持，1
        # 表示支持
        # bySupport & 0x1，表示是否支持智能搜索
        # bySupport & 0x2，表示是否支持备份
        # bySupport & 0x4，表示是否支持压缩参数能力获取
        # bySupport & 0x8, 表示是否支持双网卡
        # bySupport & 0x10, 表示支持远程SADP
        # bySupport & 0x20, 表示支持Raid卡功能
        # bySupport & 0x40, 表示支持IPSAN目录查找
        # bySupport & 0x80, 表示支持rtp over rtsp
        ("bySupport", h_BYTE),
        # 能力集扩充，位与结果为0表示不支持，1
        # 表示支持
        # bySupport1 & 0x1, 表示是否支持snmp
        # v30
        # bySupport1 & 0x2, 表示是否支持区分回放和下载
        # bySupport1 & 0x4, 表示是否支持布防优先级
        # bySupport1 & 0x8, 表示智能设备是否支持布防时间段扩展
        # bySupport1 & 0x10, 表示是否支持多磁盘数（超过33个）
        # bySupport1 & 0x20, 表示是否支持rtsp over http
        # bySupport1 & 0x80, 表示是否支持车牌新报警信息，且还表示是否支持NET_DVR_IPPARACFG_V40配置
        ("bySupport1", h_BYTE),
        # 能力集扩充，位与结果为0表示不支持，1
        # 表示支持
        # bySupport2 & 0x1, 表示解码器是否支持通过URL取流解码
        # bySupport2 & 0x2, 表示是否支持FTPV40
        # bySupport2 & 0x4, 表示是否支持ANR(断网录像)
        # bySupport2 & 0x20, 表示是否支持单独获取设备状态子项
        # bySupport2 & 0x40, 表示是否是码流加密设备
        ("bySupport2", h_BYTE),
        ("wDevType", h_WORD),  # 设备型号，详见下文列表
        # 能力集扩展，位与结果：0 - 不支持，1 - 支持
        # bySupport3 & 0x1, 表示是否支持多码流
        # bySupport3 & 0x4, 表示是否支持按组配置，具体包含通道图像参数、报警输入参数、IP报警输入 / 输出接入参数、用户参数、设备工作状态、JPEG抓图、定时和时间抓图、硬盘盘组管理等
        # bySupport3 & 0x20,表示是否支持通过DDNS域名解析取流
        ("bySupport3", h_BYTE),
        # 是否支持多码流，按位表示，位与结果：0 - 不支持，1 - 支持
        # byMultiStreamProto & 0x1, 表示是否支持码流3
        # byMultiStreamProto & 0x2, 表示是否支持码流4
        # byMultiStreamProto & 0x40, 表示是否支持主码流
        # byMultiStreamProto & 0x80, 表示是否支持子码流
        ("byMultiStreamProto", h_BYTE),
        ("byStartDChan", h_BYTE),  # 起始数字通道号，0表示无数字通道，比如DVR或IPC
        ("byStartDTalkChan", h_BYTE),  # 起始数字对讲通道号，区别于模拟对讲通道号，0表示无数字对讲通道
        ("byHighDChanNum", h_BYTE),  # 数字通道个数，高8位

        # 能力集扩展，按位表示，位与结果：0 - 不支持，1 - 支持
        # bySupport4 & 0x01, 表示是否所有码流类型同时支持RTSP和私有协议
        # bySupport4 & 0x10, 表示是否支持域名方式挂载网络硬盘
        ("bySupport4", h_BYTE),
        # 支持语种能力，按位表示，位与结果：0 - 不支持，1 - 支持
        # byLanguageType == 0，表示老设备，不支持该字段
        # byLanguageType & 0x1，表示是否支持中文
        # byLanguageType & 0x2，表示是否支持英文
        ("byLanguageType", h_BYTE),

        ("byVoiceInChanNum", h_BYTE),  # 音频输入通道数
        ("byStartVoiceInChanNo", h_BYTE),  # 音频输入起始通道号，0表示无效
        ("byRes3", h_BYTE * 2),  # 保留，置为0
        ("byMirrorChanNum", h_BYTE),  # 镜像通道个数，录播主机中用于表示导播通道
        ("wStartMirrorChanNo", h_WORD),  # 起始镜像通道号
        ("byRes2", h_BYTE * 2)]  # 保留，置为0


class NET_DVR_DEVICEINFO_V40(Structure):
    _fields_ = [
        ("struDeviceV30", NET_DVR_DEVICEINFO_V30),  # 设备参数
        ("bySupportLock", h_BYTE),  # 设备是否支持锁定功能，bySuportLock 为1时，dwSurplusLockTime和byRetryLoginTime有效
        ("byRetryLoginTime", h_BYTE),  # 剩余可尝试登陆的次数，用户名，密码错误时，此参数有效

        # 密码安全等级： 0-无效，1-默认密码，2-有效密码，3-风险较高的密码，
        # 当管理员用户的密码为出厂默认密码（12345）或者风险较高的密码时，建议上层客户端提示用户名更改密码
        ("byPasswordLevel", h_BYTE),

        ("byProxyType", h_BYTE),  # 代理服务器类型，0-不使用代理，1-使用标准代理，2-使用EHome代理
        # 剩余时间，单位：秒，用户锁定时次参数有效。在锁定期间，用户尝试登陆，不算用户名密码输入对错
        # 设备锁定剩余时间重新恢复到30分钟
        ("dwSurplusLockTime", h_DWORD),
        # 字符编码类型（SDK所有接口返回的字符串编码类型，透传接口除外）：
        # 0 - 无字符编码信息（老设备）
        # 1 - GB2312
        ("byCharEncodeType", h_BYTE),
        # 支持v50版本的设备参数获取，设备名称和设备类型名称长度扩展为64字节
        ("bySupportDev5", h_BYTE),
        # 登录模式（不同的模式具体含义详见"Remarks"说明：0- SDK私有协议，1- ISAPI协议）
        ("byLoginMode", h_BYTE),
        # 保留，置为0
        ("byRes2", h_BYTE * 253),
    ]


class NET_DVR_Login_V40(Structure):
    _fields_ = [
        ("pLoginInfo", NET_DVR_USER_LOGIN_INFO),
        ("lpDeviceInfo", NET_DVR_DEVICEINFO_V40)
    ]


# 设备激活参数结构体
class NET_DVR_ACTIVATECFG(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),
        ("sPassword", h_BYTE * PASSWD_LEN),
        ("byRes", h_BYTE * 108)
    ]


# SDK状态信息结构体
class NET_DVR_SDKSTATE(Structure):
    _fields_ = [
        ("dwTotalLoginNum", h_DWORD),  # 当前注册用户数
        ("dwTotalRealPlayNum", h_DWORD),  # 当前实时预览的路数
        ("dwTotalPlayBackNum", h_DWORD),  # 当前回放或下载的路数
        ("dwTotalAlarmChanNum", h_DWORD),  # 当前建立报警通道的路数
        ("dwTotalFormatNum", h_DWORD),  # 当前硬盘格式化的路数
        ("dwTotalFileSearchNum", h_DWORD),  # 当前文件搜索的路数
        ("dwTotalLogSearchNum", h_DWORD),  # 当前日志搜索的路数
        ("dwTotalSerialNum", h_DWORD),  # 当前建立透明通道的路数
        ("dwTotalUpgradeNum", h_DWORD),  # 当前升级的路数
        ("dwTotalVoiceComNum", h_DWORD),  # 当前语音转发的路数
        ("dwTotalBroadCastNum", h_DWORD),  # 当前语音广播的路数
        (" dwRes", h_DWORD*10),  # 保留，置为0
    ]

# SDK功能信息结构体
class NET_DVR_SDKABL(Structure):
    _fields_ = [
        ("dwMaxLoginNum", h_DWORD),  # 最大注册用户数
        ("dwMaxRealPlayNum", h_DWORD),  # 最大实时预览的路数
        ("dwMaxPlayBackNum", h_DWORD),  # 最大回放或下载的路数
        ("dwMaxAlarmChanNum", h_DWORD),  # 最大建立报警通道的路数
        ("dwMaxFormatNum", h_DWORD),  # 最大硬盘格式化的路数
        ("dwMaxFileSearchNum", h_DWORD),  # 最大文件搜索的路数
        ("dwMaxLogSearchNum", h_DWORD),  # 最大日志搜索的路数
        ("dwMaxSerialNum", h_DWORD),  # 最大建立透明通道的路数
        ("dwMaxUpgradeNum", h_DWORD),  # 最大升级的路数
        ("dwMaxVoiceComNum", h_DWORD),  # 最大语音转发的路数
        ("dwMaxBroadCastNum", h_DWORD),  # 最大语音广播的路数
        (" dwRes", h_DWORD*10),  # 保留，置为0
    ]

# 时间参数结构体
class NET_DVR_TIME(Structure):
    _fields_ = [
        ("dwYear", h_DWORD),  # 年
        ("dwMonth", h_DWORD),  # 月
        ("dwDay", h_DWORD),  # 日
        ("dwHour", h_DWORD),  # 时
        ("dwMinute", h_DWORD),  # 分
        ("dwSecond", h_DWORD)  # 秒
    ]

# 门禁主机报警事件信息结构体
class NET_DVR_ACS_EVENT_COND(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),  # 结构体大小
        ("dwMajor", h_DWORD),  # 报警主类型
        ("dwMinor", h_DWORD),  # 报警次类型
        ("struStartTime", NET_DVR_TIME),  # 开始时间
        ("struEndTime", NET_DVR_TIME),  # 结束时间
        ("byCardNo", h_BYTE * ACS_CARD_NO_LEN),  # 卡号（为空时默认全部）
        ("byName", h_BYTE * NAME_LEN),  # 持卡人姓名（为空时默认全部）
        ("byPicEnable", h_BYTE),  # 是否带图片，0-不带图片，1-带图片
        ("byTimeType", h_BYTE),  # 时间类型：0-设备本地时间（默认），1-UTC时间（struStartTime和struEndTime的时间）
        ("byRes2", h_BYTE * 2),  # 保留，置为0
        ("dwBeginSerialNo", h_DWORD),  # 起始流水号（起始流水号与结束流水号都为0默认全部）
        ("dwEndSerialNo", h_DWORD),  # 结束流水号（起始流水号与结束流水号都为0默认全部）
        ("dwIOTChannelNo", h_DWORD),  # IOT通道号，0-无效
        ("wInductiveEventType", h_WORD),  # 归纳事件类型，0-无效. 1) HIKVISION门禁主机：1-认证通过，2-认证失败，3-开门动作，4-关门动作，5-"门异常"，6-远程操作，7-校时事件，8-设备异常事件，9-设备恢复正常事件，10-报警事件，11-报警恢复事件，12-呼叫中心
        ("bySearchType", h_BYTE),  # 搜索方式：0-保留，1-按事件源搜索（此时通道号为非视频通道号），2-按监控点ID搜索
        ("byRes1", h_BYTE),  # 保留
        ("szMonitorID", h_BYTE * NET_SDK_MONITOR_ID_LEN),  # 监控点ID（由设备序列号、通道类型、编号组成，例如门禁点：设备序列号+“DOOR”+门编号）
        ("byEmployeeNo", h_BYTE * NET_SDK_EMPLOYEE_NO_LEN),  # 工号（人员ID）
        ("byRes", h_BYTE * 140)  # 保留，置为0
    ]

# IP地址结构体
class NET_DVR_IPADDR(Structure):
    _fields_ = [
        ("sIpV4", h_BYTE * 16),  # 设备IPv4地址
        ("sIpV6", h_BYTE * 128),  # 设备IPv6地址
    ]

# 门禁主机报警事件细节结构体
class NET_DVR_ACS_EVENT_DETAIL(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),  # 结构体大小
        ("byCardNo", h_BYTE * ACS_CARD_NO_LEN),  # 卡号（mac地址），为0无效
        ("byCardType", h_BYTE),  # 卡类型，1-普通卡，2-残疾人卡，3-黑名单卡，4-巡更卡，5-胁迫卡，6-超级卡，7-来宾卡，8-解除卡，为0无效
        ("byWhiteListNo", h_BYTE),  # 白名单单号,1-8，为0无效
        ("byReportChannel", h_BYTE),  # 报告上传通道，1-布防上传，2-中心组1上传，3-中心组2上传，为0无效
        ("byCardReaderKind", h_BYTE),  # 读卡器属于哪一类，0-无效，1-IC读卡器，2-身份证读卡器，3-二维码读卡器,4-指纹头
        ("dwCardReaderNo", h_DWORD),  # 读卡器编号，为0无效
        ("dwDoorNo", h_DWORD),  # 门编号（楼层编号），为0无效
        ("dwVerifyNo", h_DWORD),  # 多重卡认证序号，为0无效
        ("dwAlarmInNo", h_DWORD),  # 报警输入号，为0无效
        ("dwAlarmOutNo", h_DWORD),  # 报警输出号，为0无效
        ("dwCaseSensorNo", h_DWORD),  # 事件触发器编号
        ("dwRs485No", h_DWORD),  # RS485通道号，为0无效
        ("dwMultiCardGroupNo", h_DWORD),  # 群组编号
        ("wAccessChannel", h_WORD),  # 人员通道号
        ("byDeviceNo", h_BYTE),  # 设备编号
        ("byDistractControlNo", h_BYTE),  # 分控器编号，为0无效
        ("dwEmployeeNo", h_DWORD),  # 工号，为0无效
        ("wLocalControllerID", h_WORD),  # 就地控制器编号，0-门禁主机，1-64代表就地控制器
        ("byInternetAccess", h_BYTE),  # 网口ID：（1-上行网口1,2-上行网口2,3-下行网口1）
        ("byType", h_BYTE),  # 防区类型，0:即时防区,1-24小时防区,2-延时防区 ,3-内部防区，4-钥匙防区 5-火警防区 6-周界防区 7-24小时无声防区 8-24小时辅助防区，9-24小时震动防区,10-门禁紧急开门防区，11-门禁紧急关门防区 0xff-无
        ("byMACAddr", h_BYTE),  # 物理地址，为0无效
        ("bySwipeCardType", h_BYTE),  # 刷卡类型，0-无效，1-二维码
        ("byRes", h_BYTE),  # 保留，置为0
        ("dwSerialNo", h_DWORD),  # 事件流水号，为0无效
        ("byChannelControllerID", h_BYTE),  # 通道控制器ID，为0无效，1-主通道控制器，2-从通道控制器
        ("byChannelControllerLampID", h_BYTE),  # 通道控制器灯板ID，为0无效（有效范围1-255）
        ("byChannelControllerIRAdaptorID", h_BYTE),  # 通道控制器红外转接板ID，为0无效（有效范围1-255）
        ("byChannelControllerIREmitterID", h_BYTE),  # 通道控制器红外对射ID，为0无效（有效范围1-255）
        ("dwRecordChannelNum", h_DWORD),  # 录像通道数目
        ("pRecordChannelData", h_CHAR_P),  # 录像通道，大小为sizeof(DWORD)* dwRecordChannelNum
        ("byUserType", h_BYTE),  # 人员类型：0-无效，1-普通人（主人），2-来宾（访客），3-黑名单人，4-管理员
        ("byCurrentVerifyMode", h_BYTE),  # 读卡器当前验证方式：0-无效，1-休眠，2-刷卡+密码，3-刷卡，4-刷卡或密码，5-指纹，6-指纹+密码，7-指纹或刷卡，8-指纹+刷卡，9-指纹+刷卡+密码，10-人脸或指纹或刷卡或密码，11-人脸+指纹，12-人脸+密码，13-人脸+刷卡，14-人脸，15-工号+密码，16-指纹或密码，17-工号+指纹，18-工号+指纹+密码，19-人脸+指纹+刷卡，20-人脸+密码+指纹，21-工号+人脸，22-人脸或人脸+刷卡，23-指纹或人脸，24-刷卡或人脸或密码
        ("byRe2", h_BYTE * 2),  # 保留，置为0
        ("byEmployeeNo", h_BYTE),  # 工号（人员ID）（对于设备来说，如果使用了工号（人员ID）字段，byEmployeeNo一定要传递，如果byEmployeeNo可转换为dwEmployeeNo，那么该字段也要传递；对于上层平台或客户端来说，优先解析byEmployeeNo字段，如该字段为空，再考虑解析dwEmployeeNo字段）
        ("byRes", h_BYTE * 64)  # 保留，置为0
    ]

# 门禁主机报警事件配置结构体
class NET_DVR_ACS_EVENT_CFG(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),  # 结构体大小
        ("dwMajor", h_DWORD),  # 报警主类型
        ("dwMinor", h_DWORD),  # 报警次类型
        ("struTime", NET_DVR_TIME),  # 时间
        ("sNetUser", h_BYTE * MAX_NAMELEN),  # 网络用户名称
        ("struRemoteHostAddr", NET_DVR_IPADDR),  # 远程主机地址
        ("struAcsEventInfo", NET_DVR_ACS_EVENT_DETAIL),  # 详细参数
        ("dwPicDataLen", h_DWORD),  # 图片数据大小，不为0是表示后面带数据
        ("pPicData", h_CHAR_P),  # 图片数据
        ("wInductiveEventType", h_WORD),  # 归纳事件类型，0-无效，其他值参见Remarks说明，客户端判断该值为非0值后，报警类型通过归纳事件类型区分，否则通过原有报警主次类型（dwMajor、dwMinor）区分
        ("byTimeType", h_BYTE),  # 时间类型：0-设备本地时间（默认），1-UTC时间（struTime的时间）
        ("byRes", h_BYTE * 61)  # 保留，置为0
    ]

# 按卡号删除人脸参数条件结构体
class NET_DVR_FACE_PARAM_BYCARD(Structure):
    _fields_ = [
        ("byCardNo", h_BYTE * ACS_CARD_NO_LEN),
        ("byEnableCardReader", h_BYTE)
    ]

# 卡参数配置条件结构体
class NET_DVR_CARD_CFG_COND(Structure):
    _fields_ = [
        ("dwSize", h_DWORD),
        ("dwCardNum", h_DWORD),
        ("byCheckCardNo", h_BYTE),
        ("byRes1", h_BYTE * 3),
        ("wLocalControllerID", h_WORD),
        ("byRes2", h_BYTE * 2),
        ("dwLockID", h_DWORD),
        ("byRes3", h_BYTE * 20)
    ]