import pytest
from unittest.mock import MagicMock, patch
from src.infrastructure.messaging.listener import handle_user_deactivated_event
import logging

@patch("src.infrastructure.messaging.listener.process_user_deactivation")
def test_listener_processes_valid_event_successfully(mock_process, caplog):
    caplog.set_level(logging.INFO) # <-- ADICIONE ESTA LINHA
    
    repo_mock = MagicMock()
    payload_valido = {
        "eventId": "123",
        "eventType": "UserDeactivated",
        "payload": {"userId": "usr_123", "reason": "Demissão"}
    }
    
    handle_user_deactivated_event(payload_valido, repo_mock)
    assert "processado com sucesso" in caplog.text

@patch("src.infrastructure.messaging.listener.process_user_deactivation")
def test_listener_ignores_wrong_event_type(mock_process, caplog):
    """Garante que eventos de outros canais são ignorados silenciosamente (Fail-Fast)[cite: 10]."""
    repo_mock = MagicMock()
    payload_errado = {
        "eventId": "123",
        "eventType": "UserCreated",  # Evento não monitorado por este worker
        "payload": {"userId": "usr_1"}
    }
    
    handle_user_deactivated_event(payload_errado, repo_mock)
    
    # Validações
    mock_process.assert_not_called()
    assert "Evento ignorado" in caplog.text

@patch("src.infrastructure.messaging.listener.process_user_deactivation")
def test_listener_fails_on_missing_userid(mock_process, caplog):
    """Garante que payloads malformados não quebram o sistema, apenas registram erro[cite: 10]."""
    repo_mock = MagicMock()
    payload_corrompido = {
        "eventId": "123",
        "eventType": "UserDeactivated",
        "payload": {"reason": "Sem ID"} # Faltando o userId
    }
    
    handle_user_deactivated_event(payload_corrompido, repo_mock)
    
    mock_process.assert_not_called()
    assert "Evento corrompido" in caplog.text

@patch("src.infrastructure.messaging.listener.process_user_deactivation")
def test_listener_processes_valid_event_successfully(mock_process):
    """Garante o Caminho Feliz: Evento válido chama o serviço de domínio corretamente[cite: 10]."""
    repo_mock = MagicMock()
    payload_valido = {
        "eventId": "123",
        "eventType": "UserDeactivated",
        "payload": {"userId": "usr_123", "reason": "Demissão"}
    }
    
    handle_user_deactivated_event(payload_valido, repo_mock)
    
    # Verifica se delegou para o serviço com os argumentos certos
    mock_process.assert_called_once_with(
        user_id="usr_123",
        reason="Demissão",
        repo=repo_mock
    )

@patch("src.infrastructure.messaging.listener.process_user_deactivation")
def test_listener_raises_exception_to_nack_rabbitmq(mock_process):
    """
    Garante que se o banco/serviço falhar, o erro sobe para o aio_pika,
    garantindo que o RabbitMQ saiba da falha[cite: 10].
    """
    repo_mock = MagicMock()
    payload_valido = {
        "eventType": "UserDeactivated",
        "payload": {"userId": "usr_123"}
    }
    
    # Força a camada de serviço a estourar um erro genérico
    mock_process.side_effect = Exception("Erro fatal no banco")
    
    # A exceção deve vazar da função para a infraestrutura lidar
    with pytest.raises(Exception) as exc_info:
        handle_user_deactivated_event(payload_valido, repo_mock)
        
    assert "Erro fatal no banco" in str(exc_info.value)