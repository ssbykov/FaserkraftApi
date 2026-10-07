import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parent.parent


class SqlAdmin(BaseModel):
    templates: Path = ROOT / "admin/templates/"
    jwt_secret: str
    secret: str


class LoggerConfig(BaseModel):
    filename: str = "app.log"
    log_level: str = os.getenv("LOG_LEVEL", "ERROR").upper()


class RunConfig(BaseModel):
    host: str
    port: int


class SuperUser(BaseModel):
    email: str
    password: str


class AccessToken(BaseModel):
    lifetime_seconds: int = 3600
    reset_password_token_secret: str
    verification_token_secret: str


class AppUpdate(BaseModel):
    release_dir: Path = Path("releases")
    release_file: str = str(Path("releases") / "release.json")


class ApiV1Prefix(BaseModel):
    prefix: str = "/v1"
    days: str = "/days"
    auth: str = "/auth"
    users: str = "/users"
    update: str = "/app-update"
    products: str = "/products"
    processes: str = "/processes"
    packaging: str = "/packaging"
    orders: str = "/orders"
    step_definitions: str = "/step_definitions"
    employees: str = "/employees"
    products_steps: str = "/products_steps"
    inventories: str = "/inventories"


class ApiPrefix(BaseModel):
    prefix: str = "/api"
    v1: ApiV1Prefix = Field(default_factory=ApiV1Prefix)

    @property
    def auth_url(self) -> str:
        parts = (
            self.prefix[1:],
            self.v1.prefix,
            self.v1.auth,
        )
        return "".join(parts)

    @property
    def token_url(self) -> str:
        return self.auth_url + "/login"


class EmailSettings(BaseModel):
    host: str
    port: int
    password: str
    admin_email: str


class YandexDiskSettings(BaseModel):
    client_id: str
    client_secret: str
    refresh_token: str


class DbSettings(BaseSettings):
    user: str
    password: str
    host: str
    port: int
    database: str

    redis_host: str
    redis_db: str

    backups_dir: Path = ROOT / ".backups/"
    echo: bool = False

    naming_convention: dict[str, str] = Field(
        default_factory=lambda: {
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": (
                "fk_%(table_name)s_%(column_0_name)s_"
                "%(referred_table_name)s"
            ),
            "pk": "pk_%(table_name)s",
        }
    )

    @property
    def url(self) -> PostgresDsn:
        return PostgresDsn(
            f"postgresql+asyncpg://"
            f"{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT.parent / ".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
        extra="forbid",
    )

    api: ApiPrefix = Field(default_factory=ApiPrefix)
    logger: LoggerConfig = Field(default_factory=LoggerConfig)
    app_update: AppUpdate = Field(default_factory=AppUpdate)

    sql_admin: SqlAdmin
    access_token: AccessToken
    db: DbSettings
    super_user: SuperUser
    email: EmailSettings
    yandex_disk: YandexDiskSettings
    run: RunConfig

    # Алиасы сохраняют текущие имена ADMIN_* в .env.
    admin_cookie_secure: bool = Field(
        default=True,
        validation_alias="ADMIN_COOKIE_SECURE",
    )

    admin_allowed_origins: str = Field(
        default="",
        validation_alias="ADMIN_ALLOWED_ORIGINS",
    )

    admin_session_max_age: int = Field(
        default=3600,
        gt=0,
        validation_alias="ADMIN_SESSION_MAX_AGE",
    )

    admin_idle_timeout: int = Field(
        default=900,
        gt=0,
        validation_alias="ADMIN_IDLE_TIMEOUT",
    )


ENV_MAP = {
    "dev": ROOT.parent / ".env_dev",
    "prod": ROOT.parent / ".env",
}


@lru_cache
def get_settings() -> Settings:
    env = os.getenv("APP_ENV", "prod")
    env_file = ENV_MAP.get(env, ENV_MAP["prod"])

    return Settings(_env_file=env_file)  # type: ignore[call-arg]


settings = get_settings()