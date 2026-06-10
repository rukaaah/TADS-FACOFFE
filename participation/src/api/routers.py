"""
Módulo: routers.py
Descrição: Mapeia e expõe os endpoints HTTP (rotas) do subdomínio Participation.
Atua estritamente como a porta de entrada da API: recebe as requisições HTTP, 
aciona a orquestração na camada de aplicação (services) e devolve as respostas 
com os códigos de status corretos (200, 201, 400, 404, 409). 
Nenhuma regra de negócio ou lógica de banco de dados deve existir aqui.
"""

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from typing import dict
from sqlalchemy.orm import Session

from src.api.schemas import (
    ErrorResponse,
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

# 2. Importar as barreiras de segurança (RBAC)
from src.api.security import require_role, get_current_user_payload
from src.infrastructure.database.repositories import ParticipationRepository
from src.infrastructure.database.session import get_db

# 3. Importar os serviços da camada de aplicação (services)
from src.application import services
from src.domain import exceptions

router = APIRouter(tags=["Participation"])


# =========================================================================
# DEPENDÊNCIA AUTOMÁTICA DO REPOSITÓRIO
# =========================================================================
def get_repo(db: Session = Depends(get_db)) -> ParticipationRepository:
    # participations/Abre a sessão do banco e instancia o repositório pronto para as rotas.
    return ParticipationRepository(db)


# ==========================================
# ROTAS DE COTAS (QUOTAS)
# ==========================================
@router.post(
    "/participations/quotas", 
    response_model=ParticipationQuota, 
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cota de participação"
)
def create_participation_quota(
    payload: CreateParticipationQuotaRequest,
    # Ninguém entra sem ter a role MANAGER!
    user_payload: dict = Depends(require_role(["MANAGER"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        # 1. Extrair informações do token validado
        manager_id = user_payload.get("sub")
        return services.create_quota(payload=payload, created_by=manager_id, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/participations/quotas", response_model=ParticipationQuotaPage, summary="Listar cotas de participação com paginação")
def list_participation_quotas(
    active: bool | None = Query(None, description="Filtrar por status ativo/inativo"),
    condition: QuotaCondition | None = Query(None, description="Filtrar por tipo de condição"),
    items: QuotaItems | None = Query(None, description="Filtrar por itens inclusos"),
    page: int = Query(0, ge=0, description="Número da página (0-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Quantidade de itens por página"),
    repo: ParticipationRepository = Depends(get_repo)
):
    quotas, page_meta = services.list_quotas(
        active=active, condition=condition, items=items, page=page, size=size, repo=repo
    )
    return ParticipationQuotaPage(items=quotas, page=page_meta)

@router.patch("/quotas/{quotaId}", response_model=ParticipationQuota)
def update_participation_quota(
    quotaId: str = Path(...),
    payload: UpdateParticipationQuotaRequest = ...,
    user_payload: dict = Depends(require_role(["MANAGER"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        return services.update_quota(quota_id=quotaId, payload=payload, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

# Restrição: Role MANAGER.
# Nota do Arquiteto: Lembrar que o serviço deve retornar erro 409 se houver adesões ativas.
@router.delete("/quotas/{quotaId}", response_model=ParticipationQuota, summary="Desativar cota de participação")
def deactivate_participation_quota(
    quotaId: str = Path(...),
    user_payload: dict = Depends(require_role(["MANAGER"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        return services.deactivate_quota(quota_id=quotaId, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

# Restrição: Role PARTICIPANT.
@router.post("/participations", response_model=Participation, status_code=status.HTTP_201_CREATED, summary="Aderir a uma cota de participação")
def join_participation_quota(
    payload: JoinParticipationQuotaRequest,
    user_payload: dict = Depends(require_role(["PARTICIPANT"])),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        return services.join_quota(payload=payload, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/participations", response_model=ParticipationPage, summary="Listar participações")
def list_participations(
    userId: str | None = Query(None),
    quotaId: str | None = Query(None),
    status: str | None = Query(None),
    cycle: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        participations, page_meta = services.list_participations(
            user_id=userId, quota_id=quotaId, status=status, cycle=cycle, page=page, size=size, repo=repo
        )
        return ParticipationPage(items=participations, page=page_meta)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/participations/{participationId}", response_model=Participation, summary="Obter participação por identificador")
def get_participation_by_id(
    participationId: str = Path(...),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        return services.get_participation(participation_id=participationId, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

# Restrição: Role MANAGER_OR_SELF.
@router.patch("/participations/{participationId}", response_model=Participation, summary="Cancelar participação")
def cancel_participation(
    participationId: str = Path(...),
    payload: CancelParticipationRequest = ...,
    user_payload: dict = Depends(get_current_user_payload),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        return services.cancel_participation(participation_id=participationId, payload=payload, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

@router.get("/quotas/{quotaId}", response_model=ParticipationQuota, summary="Obter cota de participação por identificador")
def get_quota_by_id(
    quotaId: str = Path(..., description="ID da cota a ser localizada"),
    repo: ParticipationRepository = Depends(get_repo)
):
    try:
        return services.get_quota(quota_id=quotaId, repo=repo)
    except exceptions.DomainError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))