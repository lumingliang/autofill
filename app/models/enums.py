from enum import Enum, StrEnum


class EnumBase(Enum):
    @classmethod
    def get_member_values(cls):
        return [item.value for item in cls._member_map_.values()]

    @classmethod
    def get_member_names(cls):
        return [name for name in cls._member_names_]


class MethodType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class AIFillDataStatus(StrEnum):
    """AI填单数据处理状态"""
    PENDING = "pending"           # 待处理 - 已写入数据库，等待发送给Kafka
    QUEUED = "queued"             # 已入队 - 已发送到Kafka队列
    PROCESSING = "processing"     # 处理中 - 消费者正在处理
    COMPLETED = "completed"       # 已完成 - 成功获取Dify结果
    FAILED = "failed"             # 失败 - 处理过程中出错
    TIMEOUT = "timeout"           # 超时 - Dify请求超时
