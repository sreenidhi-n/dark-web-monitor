from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str

    # Elasticsearch
    elasticsearch_url: str = "http://elasticsearch:9200"

    # Tor
    tor_proxy: str = "socks5h://tor:9050"
    tor_control_port: int = 9051
    tor_control_password: str = ""
    crawl_timeout: int = 30
    circuit_rotate_every: int = 5

    # Auth
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Notifications
    slack_webhook_url: str = ""
    alert_webhook_url: str = ""

    # Logging
    log_level: str = "INFO"


settings = Settings()
