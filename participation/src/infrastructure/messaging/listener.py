import logging
from src.infrastructure.database.repositories import ParticipationRepository
from src.application.services import process_user_deactivation

# Configura um logger para podermos rastrear os eventos no terminal
logger = logging.getLogger(__name__)

def handle_user_deactivated_event(raw_event_payload: dict, repo: ParticipationRepository) -> None:
    """
    Listener para o canal 'users.deactivated'.
    Recebe o JSON do evento (dicionário) e traduz para o services.py
    """
    try:
        # 1. Validação (Fail-Fast): Garante que não é lixo de outro canal
        if raw_event_payload.get("eventType") != "UserDeactivated":
            logger.warning(f"Evento ignorado. Esperado 'UserDeactivated', recebido: {raw_event_payload.get('eventType')}")
            return

        # 2. Desempacota o envelope baseado no async-docs.yaml
        payload = raw_event_payload.get("payload", {})
        user_id = payload.get("userId")
        reason = payload.get("reason", "Motivo não informado no evento")

        if not user_id:
            logger.error("Evento corrompido: userId ausente no payload.")
            return

        logger.info(f"[EVENTO] Processando desativação para o usuário: {user_id}")

        # 3. Passa a bola para a Camada de Serviço (Regra de Negócio)
        process_user_deactivation(user_id=user_id, reason=reason, repo=repo)
        
        logger.info(f"[EVENTO] Usuário {user_id} processado com sucesso.")

    except Exception as e:
        logger.error(f"[EVENTO] Erro crítico ao processar UserDeactivated: {e}")
        raise  # Levanta o erro para que o RabbitMQ/Kafka saiba que falhou e tente de novo