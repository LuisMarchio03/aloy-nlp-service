import google.generativeai as genai
import json
import logging
import time
from datetime import datetime
from app.core.config import AVAILABLE_INTENTS, settings

logger = logging.getLogger(__name__)

class CognitiveClassifier:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name)

    async def classify(self, user_message: str) -> dict:
        """
        Classifica a mensagem do usuário em uma das intenções disponíveis.
        Retorna um dicionário com a intenção, confiança e entidades.
        """
        intents_str = ", ".join([f'"{intent}"' for intent in AVAILABLE_INTENTS])
        
        system_prompt = f"""
        Você é o cérebro cognitivo do assistente ALOY. 
        Sua única tarefa é analisar a mensagem do usuário e extrair a intenção e entidades.
        As intenções possíveis são estritamente: {intents_str}.
        
        IMPORTANTE:
        - Para comandos de luz (ligar/desligar), use "turn_on_lights" ou "turn_off_lights".
        - Para buscas, use "web_search".
        - Para lembretes, use "set_reminder".
        - Para saudações como 'olá', 'oi', 'bom dia', use "greeting".
        - Se a mensagem for apenas conversação sem comando específico, use "conversational".
        - Sempre retorne um JSON válido.
        - Se não tiver certeza absoluta, use "unknown" com confiança baixa.

        O JSON deve seguir este formato:
        {{
            "intent": "nome_da_intencao",
            "confidence": 0.95,
            "entities": {{ "item": "valor" }}
        }}
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
            
            return {
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
            
        except Exception as e:
            logger.error(f"Erro ao classificar mensagem: {e}")
            return {
                "intent": "unknown", 
                "confidence": 0.0, 
                "entities": {}, 
                "metadata": {"error": str(e), "timestamp": datetime.now().isoformat()}
            }
