# app/services/llm_engine.py

from ollama import AsyncClient
import json
import logging
import time
from datetime import datetime
from app.core.config import AVAILABLE_INTENTS

logger = logging.getLogger(__name__)

class GemmaEngine:
    def __init__(self, model_name: str = "gemma:2b"):
        self.model_name = model_name
        self.client = AsyncClient()
        # Dicionário em memória para guardar o histórico: { "session_id": [mensagens] }
        self.memory = {}

    async def chat_stream(self, user_message: str, session_id: str = "default"):
        """Gera uma resposta em linguagem natural com streaming e memória."""
        
        # 1. Inicializa a memória da sessão se não existir
        if session_id not in self.memory:
            self.memory[session_id] = [
                {'role': 'system', 'content': 'Você é o ALOY, um assistente virtual inteligente, educado e prestativo. Responda de forma concisa.'}
            ]

        # 2. Adiciona a nova mensagem do usuário ao histórico
        self.memory[session_id].append({'role': 'user', 'content': user_message})

        try:
            # 3. Chama o Ollama com stream=True
            response_stream = await self.client.chat(
                model=self.model_name,
                messages=self.memory[session_id],
                stream=True
            )

            full_response = ""
            
            # 4. Entrega os pedaços da resposta (chunks) em tempo real
            async for chunk in response_stream:
                content = chunk['message']['content']
                full_response += content
                yield content

            # 5. Salva a resposta completa do assistente na memória para dar contexto futuro
            self.memory[session_id].append({'role': 'assistant', 'content': full_response})

            # 6. Otimização: Limita o histórico para não estourar a janela de contexto (mantém as últimas 10 mensagens + system prompt)
            if len(self.memory[session_id]) > 11:
                self.memory[session_id] = [self.memory[session_id][0]] + self.memory[session_id][-10:]

        except Exception as e:
            logger.error(f"Erro na comunicação com Ollama: {e}")
            yield "Desculpe, ocorreu um erro ao processar sua mensagem."

    async def extract_intent(self, user_message: str) -> dict:
        """Analisa a frase e extrai a intenção e as entidades no formato JSON."""
        
        intents_str = ", ".join([f'"{intent}"' for intent in AVAILABLE_INTENTS])
        
        # Prompt atualizado para extração de Entidades (NER)
        system_prompt = f"""
        Você é o cérebro cognitivo do assistente ALOY.
        Sua única tarefa é analisar a mensagem do usuário e retornar APENAS um objeto JSON.
        Não adicione explicações ou texto fora do JSON.
        
        As intenções possíveis são: {intents_str}.
        
        Regras de Entidades: Extraia locais, tempos, datas e ações cruciais. Se não houver, retorne {{}}.

        EXEMPLOS DE COMPORTAMENTO:
        
        Usuário: "ALOY, me lembre de apagar as luzes da garagem daqui a 45 minutos"
        {{
            "intent": "set_reminder",
            "confidence": 0.98,
            "entities": {{"action": "apagar as luzes", "location": "garagem", "time": "45 minutos"}}
        }}
        
        Usuário: "liga a luz da sala"
        {{
            "intent": "turn_on_lights",
            "confidence": 0.99,
            "entities": {{"location": "sala"}}
        }}
        
        Usuário: "bom dia aloy"
        {{
            "intent": "greeting",
            "confidence": 0.99,
            "entities": {{}}
        }}

        Agora é a sua vez. Analise a próxima mensagem e responda APENAS com o JSON válido.
        """

        start_time = time.perf_counter()

        try:
            response = await self.client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                format='json'
            )
            
            end_time = time.perf_counter()
            processing_time_ms = round((end_time - start_time) * 1000, 2)
            
            llm_result = json.loads(response['message']['content'])
            
            # Monta a resposta garantindo que o campo entities sempre exista
            final_response = {
                "intent": llm_result.get("intent", "unknown"),
                "confidence": llm_result.get("confidence", 0.0),
                "entities": llm_result.get("entities", {}), # <- CAPTURANDO AS ENTIDADES
                "metadata": {
                    "model": self.model_name,
                    "backend": "ollama",
                    "processing_time_ms": processing_time_ms,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return final_response
            
        except json.JSONDecodeError:
            logger.error("O modelo não retornou um JSON válido.")
            return {"intent": "unknown", "confidence": 0.0, "entities": {}, "metadata": {"error": "Invalid JSON"}}
        except Exception as e:
            logger.error(f"Erro ao extrair intenção: {e}")
            raise e