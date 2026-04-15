import google.generativeai as genai
import json
import logging
import time
from datetime import datetime
from app.core.config import AVAILABLE_INTENTS, settings

logger = logging.getLogger(__name__)

# Configuração global da API Key do Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("AVISO: GEMINI_API_KEY não está configurada!")

class GeminiEngine:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name)
        self.memory = {}

    async def chat_stream(self, user_message: str, session_id: str = "default"):
        """
        Inicia ou continua uma sessão de chat com o Gemini, mantendo o histórico.
        Gera a resposta em modo streaming (pedaços de texto).
        """
        if session_id not in self.memory:
            system_instruction = "Você é o ALOY, um assistente virtual inteligente, educado e prestativo. Responda de forma concisa."
            model_with_system = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_instruction
            )
            self.memory[session_id] = model_with_system.start_chat(history=[])

        chat_session = self.memory[session_id]

        try:
            response_stream = await chat_session.send_message_async(user_message, stream=True)
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Erro na comunicação com Gemini: {e}")
            yield "Desculpe, ocorreu um erro de ligação aos servidores de inteligência artificial."
