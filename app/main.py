from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from app.services.llm_engine import GeminiEngine
from app.services.rabbitmq_client import RabbitMQClient
from app.services.intent import CognitiveClassifier

import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instâncias dos serviços
mq_client = RabbitMQClient()
classifier = CognitiveClassifier(model_name="gemini-2.5-flash")
engine = GeminiEngine(model_name="gemini-2.5-flash")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mq_client.connect()
    yield
    await mq_client.close()

app = FastAPI(title="ALOY NLP Service", lifespan=lifespan)

# Modelos de Dados
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class IntentRequest(BaseModel):
    text: str

class IntentResponse(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any] = {}
    metadata: Dict[str, Any]

# --- ROTAS DO SISTEMA ---

@app.get("/v1/nlp/status", tags=["System"])
async def check_status():
    return {
        "status": "online", 
        "model": engine.model_name, 
        "backend": "gemini",
        "services": ["classifier", "chat_engine", "rabbitmq"]
    }

# --- ROTA DE CLASSIFICAÇÃO (INTERMEDIÁRIA) ---

@app.post("/v1/nlp/classify", response_model=IntentResponse, tags=["Cognitive"])
async def classify_endpoint(request: IntentRequest):
    """
    Rota pura de classificação. 
    Analisa o texto e retorna a intenção detectada sem executar ações.
    """
    try:
        result = await classifier.classify(request.text)
        return result
    except Exception as e:
        logger.error(f"Erro na rota de classificação: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao classificar: {str(e)}")

# --- ROTA DE PROCESSAMENTO COMPLETO (ROTEAMENTO) ---

@app.post("/v1/nlp/chat", tags=["NLP"])
async def chat_endpoint(request: ChatRequest):
    """
    Esta é a rota principal usada pelo CLI.
    Ela atua como um Roteador Inteligente (Intermediate Route):
    1. Classifica a mensagem.
    2. Se for um comando acionável, publica no RabbitMQ.
    3. Se for conversação, gera resposta via Gemini Chat.
    """
    logger.info(f"📥 Recebendo mensagem: '{request.message}'")
    
    try:
        # FASE 1: CLASSIFICAÇÃO
        intent_result = await classifier.classify(request.message)
        intent_name = intent_result.get("intent", "unknown")
        confidence = intent_result.get("confidence", 0.0)
        
        logger.info(f"🧠 Classificação: {intent_name} ({confidence*100:.1f}%)")

        # FASE 2: ROTEAMENTO (Dispatcher)
        # Intenções que devem ser tratadas como conversa natural
        chat_intents = ["conversational", "unknown"]
        
        # Se for um comando (não chat) e tiver confiança alta
        if intent_name not in chat_intents and confidence >= 0.50:
            logger.info(f"🚀 Roteando para RabbitMQ: {intent_name}")
            
            # Publica no barramento
            await mq_client.publish_intent(intent_result)
            
            # Retorna resposta de ação reconhecida
            async def action_ack():
                yield f"⚡ Com certeza! Entendi que você quer '{intent_name}'. Já estou processando o seu pedido."
                
            return StreamingResponse(action_ack(), media_type="text/plain")
            
    except Exception as e:
        logger.error(f"Erro no roteamento: {e}")
        # Se falhar a classificação, continuamos para o chat como fallback

    # FASE 3: CONVERSAÇÃO (Fallback ou Intenção Conversacional)
    logger.info(f"💬 Roteando para Gemini Chat")
    return StreamingResponse(
        engine.chat_stream(request.message, request.session_id),
        media_type="text/plain"
    )

# --- ROTA DE INTENÇÃO LEGADA (PARA COMPATIBILIDADE) ---

@app.post("/v1/nlp/intent", response_model=IntentResponse, tags=["NLP"])
async def intent_endpoint(request: IntentRequest):
    """Extrai intenção e publica diretamente no RabbitMQ."""
    try:
        result = await classifier.classify(request.text)
        await mq_client.publish_intent(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar intenção: {str(e)}")
