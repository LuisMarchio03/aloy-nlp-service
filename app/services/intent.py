import google.generativeai as genai
import json
import logging
import time
from datetime import datetime
from app.core.config import AVAILABLE_INTENTS_DATA, settings

logger = logging.getLogger(__name__)

class CognitiveClassifier:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        # Garante configuração da API Key
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(self.model_name)

    async def classify(self, user_message: str) -> dict:
        """
        Classifica a mensagem do usuário em uma das intenções disponíveis.
        Retorna um dicionário com a intenção, confiança e entidades.
        """
        
        # Constrói a lista de intenções com descrições para o prompt
        intents_description = ""
        for item in AVAILABLE_INTENTS_DATA:
            intents_description += f"- Intent: {item['intent']}\n"
            intents_description += f"  Description: {item['description']}\n"
            if item.get('examples'):
                intents_description += f"  Examples: {', '.join(item['examples'])}\n"
            if item.get('parameters'):
                intents_description += f"  Parameters: {json.dumps(item['parameters'])}\n"
            intents_description += "\n"

        system_prompt = f"""
        Você é o cérebro cognitivo do assistente ALOY. 
        Sua tarefa é analisar a mensagem do usuário e extrair a intenção e as entidades relevantes.
        
        Abaixo estão as intenções que você pode reconhecer:
        {intents_description}
        
        REGRAS CRÍTICAS:
        1. Escolha a intenção que melhor se adapta à mensagem.
        2. Se a mensagem não se encaixar em nenhuma intenção de comando, use "conversational".
        3. Se for uma saudação, use "greeting".
        4. Sempre retorne apenas um JSON válido no formato abaixo.
        5. Extraia parâmetros para o campo 'entities' se eles forem mencionados.

        O JSON de saída deve ser EXATAMENTE assim:
        {{
            "intent": "nome_da_intencao",
            "confidence": 0.95,
            "entities": {{ "parametro": "valor" }}
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
