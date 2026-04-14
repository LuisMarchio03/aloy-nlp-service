TPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager

# IMPORTAÇÃO ATUALIZADA
from app.services.llm_engine import GeminiEngine
from app.services.rabbitmq_client import RabbitMQClient

mq_client = RabbitMQClient()
# INSTÂNCIA ATUALIZADA (O Flash é o modelo ideal por ser rápido e barato/gratuito)
engine = GeminiEngine(model_name="gemini-2.5-flash")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mq_client.connect()
    yield
    await mq_client.close()

app = FastAPI(title="ALOY NLP Service", lifespan=lifespan)

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

# ROTA ATUALIZADA
@app.get("/v1/nlp/status", tags=["System"])
async def check_status():
    return {"status": "online", "model": engine.model_name, "backend": "gemini"}

@app.post("/v1/nlp/chat", tags=["NLP"])
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        engine.chat_stream(request.message, request.session_id),
        media_type="text/plain"
    )

@app.post("/v1/nlp/intent", response_model=IntentResponse, tags=["NLP"])
async def intent_endpoint(request: IntentRequest):
    try:
        result = await engine.extract_intent(request.text)
        await mq_client.publish_intent(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar intenção: {str(e)}")
