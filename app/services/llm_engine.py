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
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name)
        self.memory = {}

    async def chat_stream(self, user_message: str, session_id: str = "default"):
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

    async def extract_intent(self, user_message: str) -> dict:
        intents_str = ", ".join([f'"{intent}"' for intent in AVAILABLE_INTENTS])
        
        system_prompt = f"""
        Você é o cérebro cognitivo do assistente ALOY.
        Sua única tarefa é analisar a mensagem do usuário e retornar APENAS um objeto JSON.
        As intenções possíveis são: {intents_str}.
        O JSON deve ter estritamente as chaves: "intent", "confidence" (float) e "entities" (dicionário).
        """

        json_model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        start_time = time.perf_counter()

        try:
            response = await json_model.generate_content_async(user_message)
            end_time = time.perf_counter()
            processing_time_ms = round((end_time - start_time) * 1000, 2)
            
            llm_result = json.loads(response.text)
            
            final_response = {
                "intent": llm_result.get("intent", "unknown"),
                "confidence": llm_result.get("confidence", 0.0),
                "entities": llm_result.get("entities", {}),
                "metadata": {
                    "model": self.model_name,
                    "backend": "gemini",
                    "processing_time_ms": processing_time_ms,
                    "timestamp": datetime.now().isoformat()
                }
            }
            return final_response
            
        except Exception as e:
            logger.error(f"Erro ao extrair intenção: {e}")
            return {"intent": "unknown", "confidence": 0.0, "entities": {}, "metadata": {"error": str(e)}}
