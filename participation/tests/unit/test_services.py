import pytest
from unittest.mock import MagicMock
from src.application.services import create_quota, join_quota
from src.domain.exceptions import ValidationError, UserAlreadyHasActiveParticipationError
from src.api.schemas import CreateParticipationQuotaRequest, JoinParticipationQuotaRequest
from src.domain.models import ParticipationQuota, ParticipationMembership


def test_create_quota_rn01_fails_on_negative_amount():
    """
    Testa a RN01: O valor da cota deve ser maior ou igual a zero.
    """
    # Arrange (Prepara os dados)
    mock_repo = MagicMock()
    payload = CreateParticipationQuotaRequest.model_construct(
            name="Cota Teste",
            condition="DAILY",
            items="ALL",
            amount=-10.0,
            active=True
        )
    # Act & Assert (Executa e Valida se o erro estourou)
    with pytest.raises(ValidationError) as exc_info:
        create_quota(payload=payload, created_by="manager_1", repo=mock_repo)

    assert "O valor da cota não pode ser negativo." in str(exc_info.value)
    # Garante que o repositório não foi chamado para salvar lixo no banco
    mock_repo.save_quota.assert_not_called()

def test_join_quota_rn02_fails_if_already_active():
    """
    Testa a RN02: Um usuário não pode possuir múltiplas adesões ativas.
    """
    # Arrange
    mock_repo = MagicMock()
    # Simulamos que o repositório achou uma adesão ativa para este usuário
    mock_repo.get_active_participation_by_user.return_value = ParticipationMembership(
        id="part_001", user_id="usr_123", quota_id="quota_old", status="ACTIVE"
    )
    
    payload = JoinParticipationQuotaRequest(
        userId="usr_123",
        quotaId="quota_new",
        startCycle="2026-06"
    )

    # Act & Assert
    with pytest.raises(UserAlreadyHasActiveParticipationError):
        join_quota(payload=payload, repo=mock_repo)

from src.application.services import deactivate_quota
from src.domain.exceptions import ConflictError, QuotaHasActiveParticipationsError

def test_join_quota_fails_if_quota_is_inactive():
    """
    Testa Cenário de Borda: Aderir a uma cota inativa.
    """
    mock_repo = MagicMock()
    # Usuário não tem adesão ativa
    mock_repo.get_active_participation_by_user.return_value = None
    
    # Mas a cota retornada está inativa
    mock_cota = ParticipationQuota(id="quota_1", name="Cota", condition="DAILY", items="ALL", amount=10.0, status="INACTIVE", created_by="sys")
    mock_repo.get_quota_by_id.return_value = mock_cota
    mock_repo.save_participation.side_effect = lambda x: x

    payload = JoinParticipationQuotaRequest(userId="usr_123", quotaId="quota_1", startCycle="2026-06")

    # Verifica se a Regra de Negócio lança o erro de Conflito correto
    with pytest.raises(ConflictError) as exc_info:
        join_quota(payload=payload, repo=mock_repo)
        
    assert "não está ativa para novas adesões" in str(exc_info.value)


def test_deactivate_quota_rn03_fails_with_active_participations():
    """
    Testa Regras de Estado: Não pode inativar cota com adesões ativas (RN03).
    """
    mock_repo = MagicMock()
    mock_cota = ParticipationQuota(id="quota_1", name="Cota", condition="DAILY", items="ALL", amount=10.0, status="ACTIVE", created_by="sys")
    mock_repo.get_quota_by_id.return_value = mock_cota
    
    # Simula que o banco encontrou 2 pessoas ainda usando essa cota
    mock_repo.count_active_participations_by_quota.return_value = 2

    # Tenta desativar e espera a exceção específica do domínio
    with pytest.raises(QuotaHasActiveParticipationsError) as exc_info:
        deactivate_quota(quota_id="quota_1", repo=mock_repo)

    assert "Existem 2 participação(ões) ativa(s)" in str(exc_info.value)

def test_join_quota_rn04_generates_correct_snapshot():
    """Garante que a adesão salva uma cópia imutável (snapshot) da cota atual."""
    mock_repo = MagicMock()
    mock_repo.get_active_participation_by_user.return_value = None
    
    # O Pulo do Gato: Força o mock a devolver a própria entidade que recebeu
    mock_repo.save_participation.side_effect = lambda x: x
    
    cota_original = ParticipationQuota(
        id="quota_123", name="Cota 2026", condition="DAILY", 
        items="ALL", amount=150.0, status="ACTIVE", created_by="sys"
    )
    mock_repo.get_quota_by_id.return_value = cota_original

    payload = JoinParticipationQuotaRequest(
        userId="usr_001", quotaId="quota_123", startCycle="2026-01"
    )

    nova_adesao = join_quota(payload, mock_repo)

    snapshot = nova_adesao.quota_snapshot
    assert snapshot["quotaId"] == "quota_123"
    assert snapshot["name"] == "Cota 2026"
    assert snapshot["amount"] == 150.0    