"""
Módulo: publisher.py
Descrição: O 'Megafone' do microsserviço. Envia eventos para o RabbitMQ com Fallback.
"""
import json
import pika
import os
import logging
from datetime import datetime, timezone

# ==========================================
# 1. CONFIGURAÇÃO DO LOGGER DE PRODUÇÃO
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Participation.Publisher")

# ==========================================
# CONFIGURAÇÕES DO RABBITMQ
# ==========================================
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "facoffee.events"
OUTBOX_FILE = "outbox_events_fallback.jsonl"


# ==========================================
# 2. O FALLBACK (OUTBOX PATTERN SIMPLIFICADO)
# ==========================================
def _save_to_outbox(payload: dict):
    """
    Se o RabbitMQ estiver fora do ar, salva o evento em um arquivo local seguro.
    Em um ambiente real, um worker leria esse arquivo a cada 5 minutos para reenviar.
    """
    try:
        # Abre o arquivo em modo "append" (adiciona no final sem apagar o que já tem)
        with open(OUTBOX_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        logger.warning(f"Fallback acionado: Evento {payload['type']} salvo no Outbox local com sucesso.")
    except Exception as e:
        logger.critical(f"FALHA CATASTRÓFICA: RabbitMQ caiu e o Outbox falhou! Erro: {str(e)}")


# ==========================================
# 3. O MEGAFONE PRINCIPAL
# ==========================================
def publish_event(routing_key: str, event_type: str, data: dict):
    """
    Grita um evento para o Exchange do RabbitMQ.
    """
    payload = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "participation-service",
        "routing_key": routing_key,
        "data": data
    }

    try:
        # Tenta conectar e publicar no RabbitMQ
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2, # Persistente
                content_type='application/json'
            )
        )
        connection.close()
        
        # Log de Sucesso!
        logger.info(f"Evento '{event_type}' publicado com sucesso no RabbitMQ (Exchange: {EXCHANGE_NAME}).")
        
    except Exception as e:
        # Log de Erro substituindo aquele print antigo
        logger.error(f"RabbitMQ Indisponível! Falha ao publicar '{event_type}'. Erro: {str(e)}")
        
        # Chama a nossa rota de escape
        _save_to_outbox(payload)