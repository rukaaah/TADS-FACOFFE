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
    # ... importar os restantes schemas necessários
)

# 2. Importar as barreiras de segurança (RBAC)
from src.api.security import require_role, require_manager_or_self

# 3. Importar os serviços da camada de aplicação (services)
# from src.application import services

router = APIRouter(prefix="/participation", tags=["Participation"])

# ==========================================
# EXEMPLO DE ROTA: Criar cota de participação (POST /quotas)
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
):
    pass

@router.patch("/quotas/{quotaId}", response_model=ParticipationQuota)
def update_participation_quota(
    quotaId: str = Path(...),
    # TODO EQUIPE: Receber o payload (UpdateParticipationQuotaRequest)
    # TODO EQUIPE: Proteger a rota para apenas MANAGER
):
    pass

# TODO EQUIPE: Implementar DELETE /quotas/{quotaId}
# Restrição: Role MANAGER.
# Nota do Arquiteto: Lembrar que o serviço deve retornar erro 409 se houver adesões ativas.

# TODO EQUIPE: Implementar POST /participations 
# Restrição: Role PARTICIPANT.

# TODO EQUIPE: Implementar GET /participations 
# Filtros: userId, quotaId, status, cycle, page, size.

# TODO EQUIPE: Implementar GET /participations/{participationId}

# TODO EQUIPE: Implementar PATCH /participations/{participationId}
# Restrição: Role MANAGER_OR_SELF.