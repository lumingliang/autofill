"""
测试配置文件
存放公共配置和常量
"""
import os

# 测试服务器配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:9999")

# API 密钥
API_KEY = os.getenv("TEST_API_KEY", "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR")

# 默认请求头
def get_default_headers():
    """获取默认请求头"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

# 默认超时
DEFAULT_TIMEOUT = 60
SHORT_TIMEOUT = 10

# Agent 测试默认参数
DEFAULT_SYSTEM_PROMPT = """从客服与用户的对话记录中提取经销商查询参数。
需要识别：
1) 城市名称（如重庆、广州等）
2) 区域/地址关键词（如沙坪坝、海珠等）
3) 门店名称关键词（如海洋网、王朝网等）
将提取的参数填充到 curl 的 name、city、address 字段中。
如果某个参数未提及，保留为空字符串。"""

DEFAULT_EXPECTED_RESULT = "返回匹配用户需求的比亚迪经销商门店列表，包含门店名称、地址、电话等信息"
