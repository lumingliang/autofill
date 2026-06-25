import os
import toml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类 - 使用 pydantic_settings 最佳实践"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )
    
    # 基础配置
    VERSION: str = "0.1.0"
    APP_TITLE: str = "Vue FastAPI Admin"
    PROJECT_NAME: str = "Vue FastAPI Admin"
    APP_DESCRIPTION: str = "Description"
    DEBUG: bool = False
    
    # 路径配置
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    
    # CORS 配置
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # 安全配置
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    
    # 数据库配置
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root123456"
    MYSQL_DATABASE: str = "autofill"
    
    # Redis 配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_KEY_PREFIX: str = "autofill"

    # seekdb 配置
    SEEKDB_ENABLED: bool = True
    SEEKDB_MODE: str = "embedded"  # embedded 或 remote
    # 嵌入式模式配置
    SEEKDB_PATH: str = "./data/seekdb.db"
    SEEKDB_DEFAULT_DATABASE: str = "autofill"
    # 远程模式配置
    SEEKDB_HOST: str = "127.0.0.1"
    SEEKDB_PORT: int = 2881
    SEEKDB_USER: str = "root"
    SEEKDB_PASSWORD: str = ""
    SEEKDB_DATABASE: str = "autofill"

    # Dify 配置
    DIFY_TIMEOUT: float = 60.0

    # Agent V2 配置
    AGENT_MODEL: str = "qwen3.6-plus-2026-04-02"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    AGENT_TEMPERATURE: float = 0.7
    AGENT_MAX_ITERATIONS: int = 10

    # Agent 配置（skill 和 mcp 基础路径列表，按优先级从高到低）
    AGENT_BASE_DIR: list = [".trae"]

    # 上传配置
    UPLOAD_DIR: str = "./uploads"
    AVATAR_DIR: str = "./uploads/avatars"
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    MAX_FILE_SIZE: int = 5
    FILE_URL_PREFIX: str = "/uploads"
    BASE_URL: str = "http://localhost:8000"

    # API管理配置 - 排除的API tags（这些tags的API不会被纳入权限管理）
    # 默认排除公开API、文件上传等不需要权限控制的接口
    EXCLUDE_API_TAGS: list = ["公开接口", "文件上传", "open", "upload"]

    # 审计日志配置 - 排除的API路径（这些路径不记录审计日志的入参和出参）
    # 用于排除导出、导入等大内容接口
    AUDIT_LOG_EXCLUDE_PATHS: list = ["/api/v1/autofill/rule/export", "/api/v1/autofill/rule/import"]

    # 日志参数长度限制配置（防止日志过大）
    # 单个字段值最大长度（字符数），超过则截断
    LOG_MAX_FIELD_LENGTH: int = 2000
    # 请求/响应体最大长度（字符数），超过则截断
    LOG_MAX_BODY_LENGTH: int = 50000  # 50KB
    # 响应体大小限制（用于判断是否记录响应内容）
    LOG_RESPONSE_SIZE_LIMIT: int = 100000  # 100KB

    # 中间件配置 - 日志跳过路径（这些路径不记录系统日志）
    LOG_SKIP_PATHS: list = ["/docs", "/openapi.json", "/redoc", "/health", "/uploads/"]

    # 中间件配置 - 敏感字段列表（日志中会被替换为***）
    LOG_SENSITIVE_FIELDS: list = ["password", "token", "secret", "key", "auth", "authorization", "cookie"]

    # ==================== 接口鉴权分类配置 ====================
    # 1. Open 接口 - 只走 autofill_auth，中间件不处理
    # 这些接口在 app/api/v1/open/ 目录下，使用 API Key 认证
    # 路径前缀: /api/v1/open/
    # 中间件通过路径前缀 /api/v1/open/ 自动识别，无需在此配置

    # 2. 后台接口无需鉴权 - 不需要 is_authed 验证（基于路径配置）
    # 注意：子应用挂载后，docs 和 openapi.json 路径会加上前缀
    # Internal API: /api/v1/docs, /api/v1/openapi.json
    # Open API: /api/v1/open/docs, /api/v1/open/openapi.json
    NO_AUTH_PATHS: list = [
        "/api/v1/base/access_token",
        "/docs",  # 兼容旧路径
        "/openapi.json",  # 兼容旧路径
        "/api/v1/docs",  # Internal API Swagger UI
        "/api/v1/openapi.json",  # Internal API OpenAPI JSON
        "/api/v1/open/docs",  # Open API Swagger UI
        "/api/v1/open/openapi.json",  # Open API OpenAPI JSON
        "/redoc",
        "/static",
    ]

    # 3. 后台接口无需权限认证(has_permission) - 只需要 is_authed（基于前缀配置）
    # 这些接口只需要登录，不需要具体的权限码
    BASE_API_PREFIXES: list = [
        "/api/v1/base/",
    ]

    # 中间件配置 - 审计日志特殊路径
    AUDIT_LOG_SPECIAL_PATHS: list = ["/api/v1/auditlog/list"]

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    LOG_MAX_BYTES: int = 10
    LOG_BACKUP_COUNT: int = 5
    LOG_CONSOLE_OUTPUT: bool = True
    LOG_FILE_OUTPUT: bool = True
    LOG_FORMAT: str = "json"
    LOG_ENABLE_REQUEST_ID: bool = True
    
    # 复合配置（从 TOML 加载后填充）
    TORTOISE_ORM: dict = {}
    LITELLM_CONFIG: dict = {}
    STRUCTURED_OUTPUT_CONFIG: dict = {}
    
    @classmethod
    def load_from_toml(cls, config_path: str = "config.toml") -> "Settings":
        """从 TOML 配置文件加载配置并返回 Settings 实例"""
        instance = cls()
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = toml.load(f)
                
                # 加载数据库配置
                if "database" in config and "mysql" in config["database"]:
                    db_config = config["database"]["mysql"]
                    instance.MYSQL_HOST = db_config.get("host", instance.MYSQL_HOST)
                    instance.MYSQL_PORT = db_config.get("port", instance.MYSQL_PORT)
                    instance.MYSQL_USER = db_config.get("user", instance.MYSQL_USER)
                    instance.MYSQL_PASSWORD = db_config.get("password", instance.MYSQL_PASSWORD)
                    instance.MYSQL_DATABASE = db_config.get("database", instance.MYSQL_DATABASE)
                
                # 加载应用配置
                if "app" in config:
                    app_config = config["app"]
                    instance.DEBUG = app_config.get("debug", instance.DEBUG)
                    instance.SECRET_KEY = app_config.get("secret_key", instance.SECRET_KEY)
                    instance.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = app_config.get(
                        "jwt_access_token_expire_minutes", 
                        instance.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                    )
                    
                    if "cors" in app_config:
                        cors_config = app_config["cors"]
                        instance.CORS_ORIGINS = cors_config.get("origins", instance.CORS_ORIGINS)
                        instance.CORS_ALLOW_CREDENTIALS = cors_config.get("allow_credentials", instance.CORS_ALLOW_CREDENTIALS)
                        instance.CORS_ALLOW_METHODS = cors_config.get("allow_methods", instance.CORS_ALLOW_METHODS)
                        instance.CORS_ALLOW_HEADERS = cors_config.get("allow_headers", instance.CORS_ALLOW_HEADERS)
                
                # 加载上传配置
                if "upload" in config:
                    upload_config = config["upload"]
                    instance.UPLOAD_DIR = upload_config.get("upload_dir", instance.UPLOAD_DIR)
                    instance.AVATAR_DIR = upload_config.get("avatar_dir", instance.AVATAR_DIR)
                    extensions = upload_config.get("allowed_extensions", instance.ALLOWED_EXTENSIONS)
                    instance.ALLOWED_EXTENSIONS = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
                    instance.MAX_FILE_SIZE = upload_config.get("max_file_size", instance.MAX_FILE_SIZE)
                    instance.FILE_URL_PREFIX = upload_config.get("file_url_prefix", instance.FILE_URL_PREFIX)
                
                # 加载 Redis 配置
                if "redis" in config:
                    redis_config = config["redis"]
                    instance.REDIS_HOST = redis_config.get("host", instance.REDIS_HOST)
                    instance.REDIS_PORT = redis_config.get("port", instance.REDIS_PORT)
                    instance.REDIS_PASSWORD = redis_config.get("password", instance.REDIS_PASSWORD)
                    instance.REDIS_DB = redis_config.get("db", instance.REDIS_DB)
                    instance.REDIS_KEY_PREFIX = redis_config.get("key_prefix", instance.REDIS_KEY_PREFIX)

                # 加载 seekdb 配置
                if "seekdb" in config:
                    seekdb_config = config["seekdb"]
                    instance.SEEKDB_ENABLED = seekdb_config.get("enabled", instance.SEEKDB_ENABLED)
                    instance.SEEKDB_MODE = seekdb_config.get("mode", instance.SEEKDB_MODE)
                    # 嵌入式模式配置
                    instance.SEEKDB_PATH = seekdb_config.get("db_path", instance.SEEKDB_PATH)
                    instance.SEEKDB_DEFAULT_DATABASE = seekdb_config.get("default_database", instance.SEEKDB_DEFAULT_DATABASE)
                    # 远程模式配置
                    instance.SEEKDB_HOST = seekdb_config.get("host", instance.SEEKDB_HOST)
                    instance.SEEKDB_PORT = seekdb_config.get("port", instance.SEEKDB_PORT)
                    instance.SEEKDB_USER = seekdb_config.get("user", instance.SEEKDB_USER)
                    instance.SEEKDB_PASSWORD = seekdb_config.get("password", instance.SEEKDB_PASSWORD)
                    instance.SEEKDB_DATABASE = seekdb_config.get("database", instance.SEEKDB_DATABASE)

                # 加载 Dify 配置
                if "dify" in config:
                    dify_config = config["dify"]
                    instance.DIFY_TIMEOUT = dify_config.get("dify_timeout", instance.DIFY_TIMEOUT)

                # 加载 Agent 配置
                if "agent" in config:
                    agent_config = config["agent"]
                    base_dir = agent_config.get("base_dir", instance.AGENT_BASE_DIR)
                    # 支持单个字符串或列表，统一为列表并按优先级排序
                    if isinstance(base_dir, str):
                        instance.AGENT_BASE_DIR = [base_dir]
                    elif isinstance(base_dir, list):
                        instance.AGENT_BASE_DIR = base_dir
                    else:
                        instance.AGENT_BASE_DIR = [".trae"]

                # 加载日志配置
                if "logging" in config:
                    log_config = config["logging"]
                    instance.LOG_LEVEL = log_config.get("level", instance.LOG_LEVEL)
                    log_file = log_config.get("log_file", instance.LOG_FILE)
                    if log_file.startswith("./") or log_file.startswith("../"):
                        instance.LOG_FILE = os.path.join(instance.BASE_DIR, log_file)
                    else:
                        instance.LOG_FILE = log_file
                    instance.LOG_MAX_BYTES = log_config.get("max_bytes", instance.LOG_MAX_BYTES)
                    instance.LOG_BACKUP_COUNT = log_config.get("backup_count", instance.LOG_BACKUP_COUNT)
                    instance.LOG_CONSOLE_OUTPUT = log_config.get("console_output", instance.LOG_CONSOLE_OUTPUT)
                    instance.LOG_FILE_OUTPUT = log_config.get("file_output", instance.LOG_FILE_OUTPUT)
                    instance.LOG_FORMAT = log_config.get("format", instance.LOG_FORMAT)
                    instance.LOG_ENABLE_REQUEST_ID = log_config.get("enable_request_id", instance.LOG_ENABLE_REQUEST_ID)
                
                # 加载 LiteLLM 配置
                if "litellm" in config:
                    litellm_config = config["litellm"]
                    instance.LITELLM_CONFIG = {
                        "base_url": litellm_config.get("base_url", "http://localhost:4000"),
                        "master_key": litellm_config.get("master_key", ""),
                        "timeout": litellm_config.get("timeout", 300)
                    }
                
                # 加载结构化输出配置
                if "structured_output" in config:
                    so_config = config["structured_output"]
                    instance.STRUCTURED_OUTPUT_CONFIG = {
                        "failed_threshold": so_config.get("failed_threshold", 2),
                        "auto_update_capabilities": so_config.get("auto_update_capabilities", True),
                        "default_method_priority": so_config.get("default_method_priority", [
                            "with_structured_output",
                            "bind_tools_stream",
                            "custom_fc_non_stream",
                            "custom_fc_stream",
                            "pydantic_parser",
                            "json_parser"
                        ]),
                        "enable_fallback": so_config.get("enable_fallback", True),
                        "max_attempt_methods": so_config.get("max_attempt_methods", 6)
                    }

                # 加载API管理配置（排除的tags）
                if "api_management" in config:
                    api_config = config["api_management"]
                    if "exclude_tags" in api_config:
                        instance.EXCLUDE_API_TAGS = api_config["exclude_tags"]

                # 加载审计日志配置（排除的路径）
                if "audit_log" in config:
                    audit_config = config["audit_log"]
                    if "exclude_paths" in audit_config:
                        instance.AUDIT_LOG_EXCLUDE_PATHS = audit_config["exclude_paths"]

                # 加载日志参数长度限制配置
                if "logging" in config:
                    log_config = config["logging"]
                    instance.LOG_MAX_FIELD_LENGTH = log_config.get("max_field_length", instance.LOG_MAX_FIELD_LENGTH)
                    instance.LOG_MAX_BODY_LENGTH = log_config.get("max_body_length", instance.LOG_MAX_BODY_LENGTH)
                    instance.LOG_RESPONSE_SIZE_LIMIT = log_config.get("response_size_limit", instance.LOG_RESPONSE_SIZE_LIMIT)
                    # 加载中间件配置
                    if "skip_paths" in log_config:
                        instance.LOG_SKIP_PATHS = log_config["skip_paths"]
                    if "sensitive_fields" in log_config:
                        instance.LOG_SENSITIVE_FIELDS = log_config["sensitive_fields"]

                # 加载审计日志中间件配置
                if "audit_log_middleware" in config:
                    audit_mw_config = config["audit_log_middleware"]
                    if "special_paths" in audit_mw_config:
                        instance.AUDIT_LOG_SPECIAL_PATHS = audit_mw_config["special_paths"]

            except Exception as e:
                print(f"Warning: Failed to load TOML config: {e}")
        
        # 初始化 Tortoise ORM 配置
        instance._init_tortoise_orm()
        
        return instance
    
    def _init_tortoise_orm(self):
        """初始化 Tortoise ORM 配置"""
        object.__setattr__(
            self,
            "TORTOISE_ORM",
            {
                "connections": {
                    "mysql": {
                        "engine": "tortoise.backends.mysql",
                        "credentials": {
                            "host": self.MYSQL_HOST,
                            "port": self.MYSQL_PORT,
                            "user": self.MYSQL_USER,
                            "password": self.MYSQL_PASSWORD,
                            "database": self.MYSQL_DATABASE,
                        },
                    },
                },
                "apps": {
                    "models": {
                        "models": ["app.models", "aerich.models"],
                        "default_connection": "mysql",
                    },
                },
                "use_tz": False,
                "timezone": "Asia/Shanghai",
            }
        )


# 创建全局单例实例
settings = Settings.load_from_toml()

