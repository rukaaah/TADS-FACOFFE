"""
Módulo: consumer.py
Descrição: Worker de Mensageria Assíncrona (Asynchronous Messaging).
Roda em uma thread/processo de segundo plano para escutar o RabbitMQ.
Seu objetivo principal é reagir a eventos (como 'UserDeactivated') disparados 
por outros domínios, garantindo que as participações sejam canceladas 
automaticamente sem depender de chamadas síncronas.
"""

import asyncio
import json
import logging
import os
from typing import Any

from aio_pika import connect_robust, IncomingMessage
from aio_pika.exceptions import AMQPConnectionError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.infrastructure.database.session import get_db_context
from src.infrastructure.database.repositories import ParticipationRepository
from src.infrastructure.messaging.listener import handle_user_deactivated_event

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "users.deactivated")
RETRY_ATTEMPTS = int(os.getenv("RABBITMQ_RETRY_ATTEMPTS", "5"))


async def _process_message(message: IncomingMessage) -> None:
    async with message.process(requeue=True):
        try:
            raw_payload = json.loads(message.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            logger.error(f"Falha ao desserializar mensagem: {error}")
            return

        with get_db_context() as db:
            repo = ParticipationRepository(db)
            handle_user_deactivated_event(raw_payload, repo)

        logger.info("Mensagem processada e confirmada com sucesso.")


@retry(
    retry=retry_if_exception_type(AMQPConnectionError),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    reraise=True,
)
async def _connect_and_consume() -> None:
    logger.info(f"Conectando ao RabbitMQ em '{RABBITMQ_URL}'")
    connection = await connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        logger.info(f"Consumidor ativo na fila '{QUEUE_NAME}'. Aguardando eventos...")
        await queue.consume(_process_message)

        # Mantém o worker vivo enquanto a conexão estiver aberta.
        await asyncio.Future()


async def start_consumer() -> None:
    try:
        await _connect_and_consume()
    except Exception as error:
        logger.exception(f"Consumidor finalizado com erro: {error}")
        raise


def main() -> None:
    asyncio.run(start_consumer())


if __name__ == "__main__":
    main()
