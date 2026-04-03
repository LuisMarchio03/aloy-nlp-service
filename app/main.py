from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.llm_engine import GemmaEngine

app = FastAPI(title="ALOY NLP Service")
engine = GemmaEngine(model_name="gemma:2b")

# ---- Schemas de Entrada ----
class ChatRequest(BaseModel):
    message: str

class IntentRequest(BaseModel):
    text: str

# ---- Schemas de Saída ----
class IntentResponse(BaseModel):
    intent: str
    confidence: float
    metadata: Dict[str, Any]

# ---- Endpoints ----
@app.get("/v1/nlp/status", tags=["System"])
async def check_status():
    return {"status": "online", "model": engine.model_name, "backend": "ollama"}

@app.post("/v1/nlp/chat", tags=["NLP"])
async def chat_endpoint(request: ChatRequest):
    try:
        reply = await engine.chat(request.message)
        return {"response": reply}
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao processar a mensagem.")

# Note que adicionamos o response_model aqui
@app.post("/v1/nlp/intent", response_model=IntentResponse, tags=["NLP"])
async def intent_endpoint(request: IntentRequest):
    try:
        result = await engine.extract_intent(request.text)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao extrair intenção.")