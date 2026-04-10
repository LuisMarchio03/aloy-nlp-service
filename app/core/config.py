# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    RABBITMQ_URL: str = "amqp://aloy_admin:aloy_secret_pass@localhost:5672/"

    class Config:
        env_file = ".env"

settings = Settings()

# Lista de intenções que o modelo deve tentar reconhecer
AVAILABLE_INTENTS = [
    "turn_on_lights",
    "turn_off_lights",
    "set_reminder",
    "web_search",
    "greeting",
    "play_music",
    "unknown"
]
