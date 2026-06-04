from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MQTT
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_user: str
    mqtt_pass: str

    # InfluxDB
    influx_url: str
    influx_token: str
    influx_org: str
    influx_bucket: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Telegram
    telegram_token: str
    gestor_chat_id: str

    # API
    api_key: str

    # CORS — JSON array no .env: ["http://localhost:3000"]
    cors_origins: list[str] = ["http://localhost:3000"]

    # Lógica
    timeout_sala: int = 30  # segundos sem movimento para disparar alerta

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
