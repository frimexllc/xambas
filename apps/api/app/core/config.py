from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Xambas API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    mongo_uri: str = "mongodb://root:root@localhost:27017/?authSource=admin"
    mongo_db_name: str = "xambas_dev"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"
    payments_provider: str = "auto"
    default_country_code: str = "MX"
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    default_currency: str = "mxn"
    mercadopago_access_token: str = ""
    mercadopago_webhook_secret: str = ""
    otp_length: int = 6
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_provider: str = "dev"
    session_ttl_hours: int = 24
    expose_otp_in_dev: bool = True
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_verify_service_sid: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
