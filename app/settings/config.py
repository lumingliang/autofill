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

    # 数据库配置
    DB_TYPE: str = "sqlite"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root123456"
    MYSQL_DATABASE: str = "autofill"
    SQLITE_FILE_PATH: str = "db.sqlite3"

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

                # 加载数据库配置
                if "database" in config:
                    db_config = config["database"]
                    self.DB_TYPE = db_config.get("db_type", "sqlite")

                    if self.DB_TYPE == "mysql" and "mysql" in db_config:
                        mysql_config = db_config["mysql"]
                        self.MYSQL_HOST = mysql_config.get("host", "127.0.0.1")
                        self.MYSQL_PORT = mysql_config.get("port", 3306)
                        self.MYSQL_USER = mysql_config.get("user", "root")
                        self.MYSQL_PASSWORD = mysql_config.get("password", "root123456")
                        self.MYSQL_DATABASE = mysql_config.get("database", "autofill")

                    if self.DB_TYPE == "sqlite" and "sqlite" in db_config:
                        sqlite_config = db_config["sqlite"]
                        self.SQLITE_FILE_PATH = sqlite_config.get("file_path", "db.sqlite3")

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

            except Exception as e:
                print(f"Warning: Failed to load TOML config: {e}")

    def _init_tortoise_orm(self):
        """初始化 Tortoise ORM 配置"""
        sqlite_path = os.path.join(self.BASE_DIR, self.SQLITE_FILE_PATH)

        object.__setattr__(
            self,
            "TORTOISE_ORM",
            {
                "connections": {
                    # SQLite configuration
                    "sqlite": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {"file_path": sqlite_path},
                    },
                    # MySQL/MariaDB configuration
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
                        "default_connection": self.DB_TYPE,
                    },
                },
                "use_tz": False,
                "timezone": "Asia/Shanghai",
            },
        )


settings = Settings()
