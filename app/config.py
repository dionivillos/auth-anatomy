from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./auth-anatomy.db"
    secure_cookies: bool = False

    # SMTP (Mailpit locally; see docker-compose.yml). Module 03+.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "noreply@auth-anatomy.local"


settings = Settings()
