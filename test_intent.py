import asyncio
import os
import sys

# Adiciona o diretório raiz ao sys.path para importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Define a variável de ambiente para carregar o .env
os.environ["GEMINI_API_KEY"] = "AIzaSyC8y7yP26Ex1JQAatdWZWe3xZzuJOhMkSg"

from app.services.intent import CognitiveClassifier

async def test_classify():
    classifier = CognitiveClassifier(model_name="gemini-1.5-flash") # Testando com um modelo válido se o 2.5 falhar
    
    test_messages = [
        "abrir spotify",
        "ligue as luzes da sala",
        "olá aloy",
        "como está o tempo hoje?"
    ]
    
    print(f"Testando com o modelo: {classifier.model_name}")
    for msg in test_messages:
        result = await classifier.classify(msg)
        print(f"Mensagem: '{msg}'")
        print(f"  Intent: {result['intent']} (Confiança: {result['confidence']})")
        print(f"  Entities: {result['entities']}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_classify())
