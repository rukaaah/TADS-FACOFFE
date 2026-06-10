"""
Módulo: services.py
Descrição: Orquestra os Casos de Uso (Use Cases) e centraliza as regras de negócio 
do subdomínio Participation. Atua como o "motor lógico" da aplicação: recebe os 
comandos da camada HTTP (routers), aplica as validações de elegibilidade exigidas 
(como bloqueio de adesão duplicada ou valor negativo) e interage com a camada de 
infraestrutura (banco de dados/repositórios) para salvar ou consultar as informações. 
É estritamente nesta camada que as Regras de Negócio (RN01 a RN04) são executadas.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Tuple, List

from src.api.schemas import (
    CreateParticipationQuotaRequest,
    UpdateParticipationQuotaRequest,
    JoinParticipationQuotaRequest,
    CancelParticipationRequest,
    PageMetadata
)
from src.domain.models import ParticipationQuota, ParticipationMembership
from src.domain.exceptions import (
    NotFoundError,
    ValidationError,
    UserAlreadyHasActiveParticipationError,
    QuotaHasActiveParticipationsError,
    ConflictError
)
from src.infrastructure.database.repositories import ParticipationRepository

# ==========================================
# UTILITÁRIOS
# ==========================================
def _generate_id(prefix: str) -> str:
    """Gera um identificador único curto (ex: quota_a1b2c3d4)."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _build_page_metadata(total_elements: int, page: int, size: int) -> PageMetadata:
    """Monta a estrutura de metadados de paginação exigida pelo contrato."""
    total_pages = math.ceil(total_elements / size) if size > 0 else 0
    return PageMetadata(
        page=page,
        size=size,
        totalElements=total_elements,
        totalPages=total_pages
    )

# ==========================================
# DOMÍNIO DE COTAS (QUOTAS)
# ==========================================
def create_quota(
    payload: CreateParticipationQuotaRequest, 
    created_by: str, 
    repo: ParticipationRepository
) -> ParticipationQuota:
    """Cria uma nova cota de participação."""
    
    # RN01 — Valor da Cota (Validação de Domínio adicional)
    if payload.amount < 0:
        raise ValidationError("O valor da cota não pode ser negativo.")

    nova_cota = ParticipationQuota(
        id=_generate_id("quota"),
        name=payload.name,
        description=payload.description,
        condition=payload.condition.value,
        items=payload.items.value,
        amount=payload.amount,
        status="ACTIVE" if payload.active else "INACTIVE",
        created_by=created_by
    )
    return repo.save_quota(nova_cota)


def list_quotas(
    active: bool | None,
    condition: str | None,
    items: str | None,
    page: int,
    size: int,
    repo: ParticipationRepository
) -> Tuple[List[ParticipationQuota], PageMetadata]:
    """Lista cotas com paginação e filtros."""
    skip = page * size
    
    # Extrai .value dos Enums do Pydantic se eles forem fornecidos
    cond_str = condition.value if condition else None
    items_str = items.value if items else None
    
    quotas, total = repo.list_quotas(
        active=active, condition=cond_str, items=items_str, skip=skip, limit=size
    )
    
    page_meta = _build_page_metadata(total, page, size)
    return quotas, page_meta


def get_quota(quota_id: str, repo: ParticipationRepository) -> ParticipationQuota:
    """Busca cota e garante que exista."""
    cota = repo.get_quota_by_id(quota_id)
    if not cota:
        raise NotFoundError(f"Cota com identificador '{quota_id}' não encontrada.")
    return cota


def update_quota(
    quota_id: str, 
    payload: UpdateParticipationQuotaRequest, 
    repo: ParticipationRepository
) -> ParticipationQuota:
    """Atualiza dados de uma cota existente."""
    cota = get_quota(quota_id, repo)

    if payload.name is not None:
        cota.name = payload.name
    if payload.description is not None:
        cota.description = payload.description
    if payload.condition is not None:
        cota.condition = payload.condition.value
    if payload.items is not None:
        cota.items = payload.items.value
    if payload.amount is not None:
        if payload.amount < 0:
            raise ValidationError("O valor da cota não pode ser negativo.")
        cota.amount = payload.amount
        
    # CORREÇÃO: Evita a porta dos fundos reaproveitando a RN03
    if payload.active is not None:
        if payload.active is False and cota.status == "ACTIVE":
            return deactivate_quota(quota_id, repo)
        elif payload.active is True:
            cota.status = "ACTIVE"

    return repo.save_quota(cota)


def deactivate_quota(quota_id: str, repo: ParticipationRepository) -> ParticipationQuota:
    """Realiza remoção lógica da cota garantindo a RN03."""
    cota = get_quota(quota_id, repo)
    
    if cota.status == "INACTIVE":
        return cota # Já está inativa, operação idempotente

    # RN03 — Desativação de Cota (Não pode se houver participações ativas)
    active_count = repo.count_active_participations_by_quota(quota_id)
    if active_count > 0:
        raise QuotaHasActiveParticipationsError(
            f"Não é possível desativar a cota. Existem {active_count} participação(ões) ativa(s) vinculada(s)."
        )

    cota.status = "INACTIVE"
    return repo.save_quota(cota)


# ==========================================
# DOMÍNIO DE ADESÕES (PARTICIPATIONS)
# ==========================================
def join_quota(
    payload: JoinParticipationQuotaRequest, 
    repo: ParticipationRepository
) -> ParticipationMembership:
    """Realiza a adesão de um usuário a uma cota (RN02 e RN04)."""
    
    # RN02 — Adesão Única Ativa
    adesao_ativa = repo.get_active_participation_by_user(payload.userId)
    if adesao_ativa:
        raise UserAlreadyHasActiveParticipationError(
            f"Usuário '{payload.userId}' já possui participação ativa na cota '{adesao_ativa.quota_id}'."
        )

    cota = get_quota(payload.quotaId, repo)
    if cota.status != "ACTIVE":
        raise ConflictError(f"A cota '{cota.id}' não está ativa para novas adesões.")

    # RN04 — Snapshot da Cota
    snapshot = {
        "quotaId": cota.id,
        "name": cota.name,
        "condition": cota.condition,
        "items": cota.items,
        "amount": float(cota.amount)
    }

    nova_adesao = ParticipationMembership(
        id=_generate_id("part"),
        user_id=payload.userId,
        quota_id=cota.id,
        status="ACTIVE",
        start_cycle=payload.startCycle,
        quota_snapshot=snapshot
    )
    
    return repo.save_participation(nova_adesao)


def list_participations(
    user_id: str | None,
    quota_id: str | None,
    status: str | None,
    cycle: str | None,
    page: int,
    size: int,
    repo: ParticipationRepository
) -> Tuple[List[ParticipationMembership], PageMetadata]:
    """Lista adesões com filtros."""
    skip = page * size
    status_str = status.value if status else None
    
    participations, total = repo.list_participations(
        user_id=user_id, quota_id=quota_id, status=status_str, cycle=cycle, skip=skip, limit=size
    )
    
    page_meta = _build_page_metadata(total, page, size)
    return participations, page_meta


def get_participation(participation_id: str, repo: ParticipationRepository) -> ParticipationMembership:
    """Busca participação por ID."""
    participation = repo.get_participation_by_id(participation_id)
    if not participation:
        raise NotFoundError(f"Participação com identificador '{participation_id}' não encontrada.")
    return participation


# CORREÇÃO: Tipagem do CancelParticipationRequest tornou-se obrigatória
def cancel_participation(
    participation_id: str, 
    payload: CancelParticipationRequest,
    repo: ParticipationRepository
) -> ParticipationMembership:
    """Realiza o cancelamento de uma participação ativa."""
    adesao = get_participation(participation_id, repo)
    
    if adesao.status == "CANCELLED":
        return adesao # Idempotência

    adesao.status = "CANCELLED"
    adesao.cancelled_at = datetime.now(timezone.utc)
    
    # CORREÇÃO: Populando as colunas de auditoria conforme exigência do Contrato
    adesao.cancellation_reason = payload.reason
    adesao.cancelled_by = payload.requestedBy
    
    if payload.effectiveCycle:
        adesao.end_cycle = payload.effectiveCycle

    return repo.save_participation(adesao)

# ==========================================
# HOOKS DE INTEGRAÇÃO (RABBITMQ CONSUMERS)
# ==========================================
def process_user_deactivation(
    user_id: str,
    reason: str,
    repo: ParticipationRepository
) -> None:
    """
    CORREÇÃO: Reage ao evento da fila 'users.deactivated' cancelando 
    automaticamente todas as participações ativas do usuário.
    """
    participacoes_ativas = repo.get_all_active_participations_by_user(user_id)

    for participacao in participacoes_ativas:
        participacao.status = "CANCELLED"
        participacao.cancelled_at = datetime.now(timezone.utc)
        
        # Auditoria forçada pelo evento da fila
        participacao.cancellation_reason = f"Automático via Evento (Deactivated): {reason}"
        participacao.cancelled_by = "SYSTEM_EVENT"
        
        repo.save_participation(participacao)