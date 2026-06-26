import secrets
from pydantic import EmailStr,model_validator
from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import (
    PostgresDsn,
    computed_field)
from typing import Literal
from typing import Self
from fastapi.templating import Jinja2Templates


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )
    PROJECT_NAME: str
    SECRET_KEY: str  = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENVIRONMENT: Literal["local","staging","production"] = "local"
    API_HOST: str = "http://localhost:8080"

    S3_BUCKET_NAME: str
    AWS_REGION: str
    AWS_PROFILE: str

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str =""
    POSTGRES_DB: str =""
    POSTGRES_PORT: int=5432

    @computed_field
    @property
    def sqlalchemy_database_uri(self)->PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS:bool = True
    SMTP_SSL:bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str|None = None
    SMTP_USER:str|None = None
    SMTP_PASSWORD:str|None = None
    EMAILS_FROM_EMAIL: EmailStr|None= None
    EMAILS_FROM_NAME: str|None=None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 1
    EMAIL_INVITATION_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEST_USER: EmailStr = "test@example.com"

    @computed_field
    @property
    def emails_enabled(self)->bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @computed_field
    @property
    def s3_bucket_enabled(self)->bool:
        return bool(self.S3_BUCKET_NAME and self.AWS_REGION)



settings = Settings()
templates=Jinja2Templates(directory="backend/templates")



