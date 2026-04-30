import os
import typing

import toml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    APP_TITLE: str = "Vue FastAPI Admin"
    PROJECT_NAME: str = "Vue FastAPI Admin"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    DEBUG: bool = True

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"  # openssl rand -hex 32
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # 数据库配置 - 仅支持 MySQL
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root123456"
    MYSQL_DATABASE: str = "autofill"

    # Redis配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_KEY_PREFIX: str = "autofill"

    # Dify AI 服务配置
    DIFY_TIMEOUT: float = 60.0

    # LiteLLM 配置
    LITELLM_CONFIG: dict = {}

    # 结构化输出配置
    STRUCTURED_OUTPUT_CONFIG: dict = {}

    # 上传配置
    UPLOAD_DIR: str = "./uploads"
    AVATAR_DIR: str = "./uploads/avatars"
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    MAX_FILE_SIZE: int = 5  # MB
    FILE_URL_PREFIX: str = "/uploads"
    BASE_URL: str = "http://localhost:8000"  # 用于构建完整文件URL

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    LOG_MAX_BYTES: int = 10  # MB
    LOG_BACKUP_COUNT: int = 5
    LOG_CONSOLE_OUTPUT: bool = True
    LOG_FILE_OUTPUT: bool = True
    LOG_FORMAT: str = "json"  # text 或 json
    LOG_ENABLE_REQUEST_ID: bool = True

    # Tortoise ORM 配置（会在初始化时生成）
    TORTOISE_ORM: dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_toml_config()
        self._init_tortoise_orm()

    def _load_toml_config(self):
        """从 TOML 配置文件加载配置"""
        config_path = os.path.join(self.BASE_DIR, "config.toml")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = toml.load(f)

                # 加载数据库配置 - 仅 MySQL
                if "database" in config and "mysql" in config["database"]:
                    mysql_config = config["database"]["mysql"]
                    self.MYSQL_HOST = mysql_config.get("host", "127.0.0.1")
                    self.MYSQL_PORT = mysql_config.get("port", 3306)
                    self.MYSQL_USER = mysql_config.get("user", "root")
                    self.MYSQL_PASSWORD = mysql_config.get("password", "root123456")
                    self.MYSQL_DATABASE = mysql_config.get("database", "autofill")

                # 加载应用配置
                if "app" in config:
                    app_config = config["app"]
                    self.DEBUG = app_config.get("debug", True)
                    self.SECRET_KEY = app_config.get("secret_key", self.SECRET_KEY)
                    self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = app_config.get(
                        "jwt_access_token_expire_minutes", 10080
                    )

                    # CORS 配置
                    if "cors" in app_config:
                        cors_config = app_config["cors"]
                        self.CORS_ORIGINS = cors_config.get("origins", ["*"])
                        self.CORS_ALLOW_CREDENTIALS = cors_config.get("allow_credentials", True)
                        self.CORS_ALLOW_METHODS = cors_config.get("allow_methods", ["*"])
                        self.CORS_ALLOW_HEADERS = cors_config.get("allow_headers", ["*"])

                # 加载上传配置
                if "upload" in config:
                    upload_config = config["upload"]
                    self.UPLOAD_DIR = upload_config.get("upload_dir", "./uploads")
                    self.AVATAR_DIR = upload_config.get("avatar_dir", "./uploads/avatars")
                    # 确保扩展名带有点号
                    extensions = upload_config.get("allowed_extensions", [".jpg", ".jpeg", ".png", ".gif", ".webp"])
                    self.ALLOWED_EXTENSIONS = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
                    self.MAX_FILE_SIZE = upload_config.get("max_file_size", 5)
                    self.FILE_URL_PREFIX = upload_config.get("file_url_prefix", "/uploads")

                # 加载Redis配置
                if "redis" in config:
                    redis_config = config["redis"]
                    self.REDIS_HOST = redis_config.get("host", "127.0.0.1")
                    self.REDIS_PORT = redis_config.get("port", 6379)
                    self.REDIS_PASSWORD = redis_config.get("password", "")
                    self.REDIS_DB = redis_config.get("db", 0)
                    self.REDIS_KEY_PREFIX = redis_config.get("key_prefix", "autofill")

                # 加载Dify配置
                if "dify" in config:
                    dify_config = config["dify"]
                    self.DIFY_TIMEOUT = dify_config.get("dify_timeout", 60.0)

                # 加载日志配置
                if "logging" in config:
                    logging_config = config["logging"]
                    self.LOG_LEVEL = logging_config.get("level", "INFO")
                    # 将相对路径转换为基于项目根目录的绝对路径
                    log_file = logging_config.get("log_file", "./logs/app.log")
                    if log_file.startswith("./") or log_file.startswith("../"):
                        self.LOG_FILE = os.path.join(self.BASE_DIR, log_file)
                    else:
                        self.LOG_FILE = log_file
                    self.LOG_MAX_BYTES = logging_config.get("max_bytes", 10)
                    self.LOG_BACKUP_COUNT = logging_config.get("backup_count", 5)
                    self.LOG_CONSOLE_OUTPUT = logging_config.get("console_output", True)
                    self.LOG_FILE_OUTPUT = logging_config.get("file_output", True)
                    self.LOG_FORMAT = logging_config.get("format", "json")
                    self.LOG_ENABLE_REQUEST_ID = logging_config.get("enable_request_id", True)

                # 加载 LiteLLM 配置
                if "litellm" in config:
                    litellm_config = config["litellm"]
                    self.LITELLM_CONFIG = {
                        "base_url": litellm_config.get("base_url", "http://localhost:4000"),
                        "master_key": litellm_config.get("master_key", ""),
                        "timeout": litellm_config.get("timeout", 60)
                    }

                # 加载结构化输出配置
                if "structured_output" in config:
                    so_config = config["structured_output"]
                    self.STRUCTURED_OUTPUT_CONFIG = {
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

            except Exception as e:
                print(f"Warning: Failed to load TOML config: {e}")

    def _init_tortoise_orm(self):
        """初始化 Tortoise ORM 配置 - 仅 MySQL"""
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
            },
        )


settings = Settings()
