# app/core/config.py

import os
import json
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    RABBITMQ_URL: str = "amqp://aloy_admin:aloy_secret_pass@localhost:5672/"

    class Config:
        env_file = ".env"

settings = Settings()

def load_available_intents():
    """Lê as intenções do arquivo intents.json."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "intents.json")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar intents.json: {e}")
        return []

# Carregado uma vez na inicialização
AVAILABLE_INTENTS_DATA = load_available_intents()
AVAILABLE_INTENTS = [i["intent"] for i in AVAILABLE_INTENTS_DATA]
