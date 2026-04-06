from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager # NOVO IMPORT

from app.services.llm_engine import GemmaEngine
from app.services.rabbitmq_client import RabbitMQClient # NOVO IMPORT

# ---- Gerenciamento de Ciclo de Vida ----
mq_client = RabbitMQClient()
engine = GemmaEngine(model_name="gemma:2b")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa quando o servidor FastAPI Iniciar
    await mq_client.connect()
    yield
    # Executa quando o servidor FastAPI Desligar
    await mq_client.close()

# Inicializa o FastAPI com o lifespan
app = FastAPI(title="ALOY NLP Service", lifespan=lifespan)

# ---- Schemas de Entrada / Saída ----
# ... (mantenha seus schemas ChatRequest, IntentRequest, IntentResponse iguais) ...

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

# ---- Endpoints ----
@app.get("/v1/nlp/status", tags=["System"])
async def check_status():
    return {"status": "online", "model": engine.model_name, "backend": "ollama"}

@app.post("/v1/nlp/chat", tags=["NLP"])
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        engine.chat_stream(request.message, request.session_id),
        media_type="text/plain"
    )

@app.post("/v1/nlp/intent", response_model=IntentResponse, tags=["NLP"])
async def intent_endpoint(request: IntentRequest):
    try:
        # 1. A IA processa e extrai as informações
        result = await engine.extract_intent(request.text)
        
        # 2. Publica no RabbitMQ (Disparo assíncrono super rápido)
        await mq_client.publish_intent(result)
        
        # 3. Retorna a resposta para a interface
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao processar e publicar intenção.")