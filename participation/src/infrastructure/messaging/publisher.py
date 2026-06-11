"""
Módulo: publisher.py
Descrição: O 'Megafone' do microsserviço. Envia eventos para o RabbitMQ.
"""
import json
import pika
import os
from datetime import datetime, timezone

# Variáveis de ambiente (Configure isso no seu .env ou docker-compose)
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "facoffee.events"

def publish_event(routing_key: str, event_type: str, data: dict):
    """
    Grita um evento para o Exchange do RabbitMQ.
    """
    try:
        # 1. Monta o payload padronizado do evento
        payload = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "participation-service",
            "data": data
        }

        # 2. Conecta no RabbitMQ (Abre o megafone)
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        # 3. Garante que o Exchange existe (Topic é o ideal para microsserviços)
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)

        # 4. Publica a mensagem
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2, # Faz a mensagem sobreviver se o RabbitMQ reiniciar (Persistent)
                content_type='application/json'
            )
        )
        
        # 5. Fecha a conexão
        connection.close()
        
    except Exception as e:
        # Nota do Arquiteto: Em produção, você logaria esse erro e usaria um fallback 
        # (Outbox Pattern), mas para o MVP, vamos apenas dar um print.
        print(f"Erro ao publicar evento {event_type} no RabbitMQ: {str(e)}")