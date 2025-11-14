from pathlib import Path

from pydantic import BaseModel, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class SqlAdmin(BaseModel):
    templates: Path = ROOT / "admin/templates/"
    jwt_secret: str
    secret: str


class LoggerConfig(BaseModel):
    filename: str = "app.log"
    log_level: str = "ERROR"


class RunConfig(BaseModel):
    host: str
    port: int = 8000


class SuperUser(BaseModel):
    email: str
    password: str


class AccessToken(BaseModel):
    lifetime_seconds: int = 3600
    reset_password_token_secret: str
    verification_token_secret: str


class ApiV1Prefix(BaseModel):
    prefix: str = "/v1"
    days: str = "/days"
    auth: str = "/auth"
    users: str = "/users"
    products: str = "/products"
    products_steps: str = "/products_steps"


class ApiPrefix(BaseModel):
    prefix: str = "/api"
    v1: ApiV1Prefix = ApiV1Prefix()

    @property
    def auth_url(self) -> str:
        parts = (self.prefix[1:], self.v1.prefix, self.v1.auth)
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
    token: str


class DbSettings(BaseSettings):
    user: str
    password: str
    host: str
    port: int
    database: str
    redis_host: str
    backups_dir: Path = ROOT / ".backups/"

    @property
    def url(self) -> PostgresDsn:
        return PostgresDsn(
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        )

    echo: bool = False
    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT.parent / ".env_dev",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )
    api: ApiPrefix = ApiPrefix()
    logger: LoggerConfig = LoggerConfig()
    sql_admin: SqlAdmin
    access_token: AccessToken
    db: DbSettings
    super_user: SuperUser
    email: EmailSettings
    yandex_disk: YandexDiskSettings
    run: RunConfig


# noinspection PyArgumentList
settings = Settings()  # type: ignore[call-arg]
