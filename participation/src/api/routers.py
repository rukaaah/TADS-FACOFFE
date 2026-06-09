"""
Módulo: routers.py
Descrição: Mapeia e expõe os endpoints HTTP (rotas) do subdomínio Participation.
Atua estritamente como a porta de entrada da API: recebe as requisições HTTP, 
aciona a orquestração na camada de aplicação (services) e devolve as respostas 
com os códigos de status corretos (200, 201, 400, 404, 409). 
Nenhuma regra de negócio ou lógica de banco de dados deve existir aqui.
"""

from fastapi import APIRouter, Depends, Query, Path, status
from typing import Optional

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

# 2. Importar as barreiras de segurança (RBAC)
from src.api.security import require_role, require_manager_or_self

# 3. Importar os serviços da camada de aplicação (services)
# from src.application import services

router = APIRouter(prefix="/participation", tags=["Participation"])

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
    # Ninguém entra sem ter a role MANAGER!
    user_payload: dict = Depends(require_role(["MANAGER"])) 
):
    """
    Ref: api-docs.yaml -> POST /participation/quotas
    """
    # 1. Extrair informações do token validado
    # manager_id = user_payload.get("sub")
    
    # 2. Delegar para o serviço (Após a criação do serviço, descomentar a linha abaixo e remover o pass)
    # nova_cota = services.create_quota(payload=payload, created_by=manager_id)
    
    # 3. Retornar o resultado (O Pydantic garante que a estrutura está correta)
    # return nova_cota
    pass


# ==========================================
# TODO
# ==========================================

@router.get("/quotas", response_model=ParticipationQuotaPage)
def list_participation_quotas(
    # TODO EQUIPE: Receber as query parameters (active, condition, items, page, size)
    # Ref: api-docs.yaml -> GET /participation/quotas
    active: Optional[bool] = Query(None),
    condition: Optional[QuotaCondition] = Query(None),
    items: Optional[QuotaItems] = Query(None),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100)
):
    pass

@router.patch("/quotas/{quotaId}", response_model=ParticipationQuota)
def update_participation_quota(
    quotaId: str = Path(...),
    # TODO EQUIPE: Receber o payload (UpdateParticipationQuotaRequest)
    payload: UpdateParticipationQuotaRequest = None,
    # TODO EQUIPE: Proteger a rota para apenas MANAGER
    user_payload: dict = Depends(require_role(["MANAGER"]))
):
    pass

# TODO EQUIPE: Implementar DELETE /quotas/{quotaId}
# Restrição: Role MANAGER.
# Nota do Arquiteto: Lembrar que o serviço deve retornar erro 409 se houver adesões ativas.
@router.delete("/quotas/{quotaId}", response_model=ParticipationQuota, summary="Desativar cota de participação")
def deactivate_participation_quota(
    quotaId: str = Path(...),
    user_payload: dict = Depends(require_role(["MANAGER"]))
):
    pass

# TODO EQUIPE: Implementar POST /participations 
# Restrição: Role PARTICIPANT.
@router.post("/participations", response_model=Participation, status_code=status.HTTP_201_CREATED, summary="Aderir a uma cota de participação")
def join_participation_quota(
    payload: JoinParticipationQuotaRequest,
    user_payload: dict = Depends(require_role(["PARTICIPANT"]))
):
    pass

# TODO EQUIPE: Implementar GET /participations 
# Filtros: userId, quotaId, status, cycle, page, size.
@router.get("/participations", response_model=ParticipationPage, summary="Listar participações")
def list_participations(
    userId: Optional[str] = Query(None),
    quotaId: Optional[str] = Query(None),
    status: Optional[ParticipationStatus] = Query(None),
    cycle: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100)
):
    pass

# TODO EQUIPE: Implementar GET /participations/{participationId}
@router.get("/participations/{participationId}", response_model=Participation, summary="Obter participação por identificador")
def get_participation_by_id(
    participationId: str = Path(...)
):
    pass

# TODO EQUIPE: Implementar PATCH /participations/{participationId}
# Restrição: Role MANAGER_OR_SELF.
@router.patch("/participations/{participationId}", response_model=Participation, summary="Cancelar participação")
def cancel_participation(
    participationId: str = Path(...),
    payload: CancelParticipationRequest = None,
    user_payload: dict = Depends(require_manager_or_self)
):
    pass