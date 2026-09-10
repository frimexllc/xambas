from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Xambas API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    mongo_uri: str = "mongodb://root:root@localhost:27018/?authSource=admin"
    mongo_db_name: str = "xambas_dev"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:4173,http://localhost:4174,http://localhost:4175,http://localhost:4176"
    client_app_url: str = "http://localhost:4173"
    provider_app_url: str = "http://localhost:4174"
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
    groq_api_key: str = ""
    groq_vision_model: str = "qwen/qwen3.6-27b"
    emergent_llm_key: str = ""
    integration_proxy_url: str = "https://integrations.emergentagent.com"
    storage_app_name: str = "xambas"
    storage_provider: str = "emergent"  # emergent | r2 | local
    storage_local_dir: str = ""  # solo para storage_provider=local; por defecto <cwd>/.storage
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
