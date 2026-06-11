"""
Módulo: routers.py
Descrição: Mapeia e expõe os endpoints HTTP (rotas) do subdomínio Participation.
Atua estritamente como a porta de entrada da API: recebe as requisições HTTP, 
aciona a orquestração na camada de aplicação (services), mapeia os objetos de 
domínio para schemas Pydantic e devolve as respostas com os códigos corretos.
"""

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timezone

from src.api.schemas import (
    CreateParticipationQuotaRequest,
    UpdateParticipationQuotaRequest,
    ParticipationQuota,
    ParticipationQuotaPage,
    JoinParticipationQuotaRequest,
    CancelParticipationRequest,
    Participation,
    ParticipationPage,
    QuotaCondition,
    QuotaItems,
    ParticipationStatus,
)
from src.api.security import require_role, get_current_user_payload, require_manager_or_self
from src.infrastructure.database.repositories import ParticipationRepository
from src.infrastructure.database.session import get_db
from src.application import services
from src.domain import exceptions

router = APIRouter(prefix="/participation", tags=["Participation"])

# ==========================================
# INJEÇÃO DE DEPENDÊNCIA (REPOSITÓRIO)
# ==========================================
def get_repo(session: Session = Depends(get_db)) -> ParticipationRepository:
    """Instancia o repositório injetando a sessão de banco de dados gerada na requisição."""
    return ParticipationRepository(session)

# ==========================================
# FUNÇÕES DE MAPEAMENTO (ANTI-CORRUPTION LAYER)
# ==========================================
def ensure_tz(dt):
    """Garante que a data tem fuso horário UTC (resolve problema do SQLite)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def map_quota(cota) -> ParticipationQuota:
    """Converte a entidade de domínio (snake_case) para o schema da API (camelCase)."""
    return ParticipationQuota(
        id=cota.id,
        name=cota.name,
        description=cota.description,
        condition=cota.condition,
        items=cota.items,
        amount=float(cota.amount),
        status=cota.status,
        createdBy=cota.created_by,
        createdAt=ensure_tz(cota.created_at),
        updatedAt=ensure_tz(cota.updated_at)
    )

def map_participation(part) -> Participation:
    """Converte a entidade de domínio (snake_case) para o schema da API (camelCase)."""
    return Participation(
        id=part.id,
        userId=part.user_id,
        quotaId=part.quota_id,
        status=part.status,
        startCycle=part.start_cycle,
        endCycle=part.end_cycle,
        quotaSnapshot=part.quota_snapshot,
        createdAt=ensure_tz(part.created_at),
        updatedAt=ensure_tz(part.updated_at),
        cancelledAt=ensure_tz(part.cancelled_at)
    )

# ==========================================
# ROTAS DE COTAS (QUOTAS)
# ==========================================
@router.post(
    "/quotas", 
    response_model=ParticipationQuota, 
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cota de participação"
)
def create_participation_quota(
    payload: CreateParticipationQuotaRequest,
    user_payload: dict = Depends(require_role(["MANAGER"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        manager_id = user_payload.get("sub")
        nova_cota = services.create_quota(payload=payload, created_by=manager_id, repo=repo)
        return map_quota(nova_cota)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/quotas", response_model=ParticipationQuotaPage, summary="Listar cotas de participação")
def list_participation_quotas(
    active: Optional[bool] = Query(None),
    condition: Optional[QuotaCondition] = Query(None),
    items: Optional[QuotaItems] = Query(None),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        quotas, page_meta = services.list_quotas(
            active=active, condition=condition, items=items, page=page, size=size, repo=repo
        )
        return ParticipationQuotaPage(
            items=[map_quota(q) for q in quotas],
            page=page_meta
        )
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/quotas/{quotaId}", response_model=ParticipationQuota, summary="Obter cota por identificador")
def get_quota_by_id(
    quotaId: str = Path(...),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        cota = services.get_quota(quota_id=quotaId, repo=repo)
        return map_quota(cota)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.patch("/quotas/{quotaId}", response_model=ParticipationQuota, summary="Atualizar cota de participação")
def update_participation_quota(
    quotaId: str = Path(...),
    payload: UpdateParticipationQuotaRequest = ...,
    user_payload: dict = Depends(require_role(["MANAGER"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        cota_atualizada = services.update_quota(quota_id=quotaId, payload=payload, repo=repo)
        return map_quota(cota_atualizada)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.delete("/quotas/{quotaId}", response_model=ParticipationQuota, summary="Desativar cota de participação")
def deactivate_participation_quota(
    quotaId: str = Path(...),
    user_payload: dict = Depends(require_role(["MANAGER"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        cota_desativada = services.deactivate_quota(quota_id=quotaId, repo=repo)
        return map_quota(cota_desativada)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

# ==========================================
# ROTAS DE ADESÕES (PARTICIPATIONS)
# ==========================================
@router.post(
    "/participations", 
    response_model=Participation, 
    status_code=status.HTTP_201_CREATED, 
    summary="Aderir a uma cota de participação"
)
def join_participation_quota(
    payload: JoinParticipationQuotaRequest,
    user_payload: dict = Depends(require_role(["PARTICIPANT"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        nova_adesao = services.join_quota(payload=payload, repo=repo)
        return map_participation(nova_adesao)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/participations", response_model=ParticipationPage, summary="Listar participações")
def list_participations(
    userId: Optional[str] = Query(None),
    quotaId: Optional[str] = Query(None),
    status: Optional[ParticipationStatus] = Query(None),
    cycle: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        participations, page_meta = services.list_participations(
            user_id=userId, quota_id=quotaId, status=status, cycle=cycle, page=page, size=size, repo=repo
        )
        return ParticipationPage(
            items=[map_participation(p) for p in participations],
            page=page_meta
        )
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/participations/{participationId}", response_model=Participation, summary="Obter participação por identificador")
def get_participation_by_id(
    participationId: str = Path(...),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        participacao = services.get_participation(participation_id=participationId, repo=repo)
        return map_participation(participacao)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.patch("/participations/{participationId}", response_model=Participation, summary="Cancelar participação")
def cancel_participation(
    participationId: str = Path(...),
    payload: CancelParticipationRequest = ...,
    user_payload: dict = Depends(get_current_user_payload),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        adesao_alvo = services.get_participation(participation_id=participationId, repo=repo)
        
        # Validando se quem está a tentar cancelar é o gestor ou o próprio dono da adesão
        require_manager_or_self(payload=user_payload, target_user_id=adesao_alvo.user_id)
        
        adesao_cancelada = services.cancel_participation(participation_id=participationId, payload=payload, repo=repo)
        return map_participation(adesao_cancelada)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))