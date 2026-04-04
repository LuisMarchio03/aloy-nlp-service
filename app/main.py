# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse # Importante adicionar isso
from pydantic import BaseModel
from typing import Dict, Any
from app.services.llm_engine import GemmaEngine

app = FastAPI(title="ALOY NLP Service")
engine = GemmaEngine(model_name="gemma:2b")

# ---- Schemas de Entrada ----
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default" # Permite múltiplas conversas simultâneas

class IntentRequest(BaseModel):
    text: str

# ---- Schemas de Saída ----
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
    # Usamos o StreamingResponse para retornar os dados conforme são gerados
    return StreamingResponse(
        engine.chat_stream(request.message, request.session_id),
        media_type="text/plain"
    )

@app.post("/v1/nlp/intent", response_model=IntentResponse, tags=["NLP"])
async def intent_endpoint(request: IntentRequest):
    try:
        result = await engine.extract_intent(request.text)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao extrair intenção.")