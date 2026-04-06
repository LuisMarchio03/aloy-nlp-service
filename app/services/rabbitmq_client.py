import aio_pika
import json
import logging
import os

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self):
        # Lê a URL do .env/Docker, ou usa o localhost como fallback seguro
        self.url = os.getenv(
            "RABBITMQ_URL", 
            "amqp://aloy_admin:aloy_secret_pass@localhost:5672/"
        )
        self.connection = None
        self.channel = None
        self.exchange_name = "aloy_events"

    async def connect(self):
        """Estabelece conexão com o RabbitMQ e configura o Exchange."""
        try:
            self.connection = await aio_pika.connect_robust(self.url)
            self.channel = await self.connection.channel()
            
            # Cria um exchange do tipo 'topic' para que outros serviços escutem 
            # apenas o que lhes interessa (ex: tópicos de IoT, tópicos de Lembretes)
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
            )
            logger.info("✅ Conectado ao RabbitMQ com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar no RabbitMQ: {e}")

    async def publish_intent(self, intent_data: dict):
        """Publica a intenção extraída no barramento de eventos."""
        if not self.exchange:
            logger.warning("RabbitMQ não está conectado. Mensagem ignorada.")
            return

        # A chave de roteamento (ex: intent.turn_off_lights) permite 
        # que os microserviços filtrem o que querem ouvir
        intent_name = intent_data.get("intent", "unknown")
        routing_key = f"intent.{intent_name}"
        
        # Converte o dict para JSON em bytes
        message_body = json.dumps(intent_data).encode('utf-8')
        
        message = aio_pika.Message(
            body=message_body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Garante que a msg não se perca se o RabbitMQ reiniciar
        )

        await self.exchange.publish(message, routing_key=routing_key)
        logger.info(f"📨 Intenção publicada no RabbitMQ | Tópico: {routing_key}")

    async def close(self):
        """Encerra a conexão graciosamente."""
        if self.connection:
            await self.connection.close()
            logger.info("Conexão com RabbitMQ encerrada.")