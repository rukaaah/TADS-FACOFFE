"""
Módulo: security.py
Descrição: Controle de autenticação e autorização para o subdomínio Participation.
Responsável por extrair o JWT do cabeçalho Authorization: Bearer, obter as claims
necessárias e fornecer dependências de RBAC para as rotas.
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import List, Optional

security_scheme = HTTPBearer()


def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> dict:
    """
    Retorna as claims do JWT sem verificar a assinatura localmente.
    """
    token = credentials.credentials

    try:
        payload = jwt.get_unverified_claims(token)
        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou corrompido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_roles: List[str]):
    """
    Dependência para garantir que o usuário tenha pelo menos uma role exigida.
    """
    def role_checker(payload: dict = Depends(get_current_user_payload)):
        user_roles = payload.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Nível de privilégio insuficiente.",
            )

        return payload

    return role_checker


def require_manager_or_self(payload: dict, target_user_id: Optional[str]) -> dict:
    """
    Valida se o usuário atual é manager ou proprietário do recurso.
    """
    token_user_id = payload.get("sub")
    if token_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não contém identificador de usuário.",
        )

    if "MANAGER" in payload.get("roles", []):
        return payload

    if target_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador do recurso não fornecido para validação.",
        )

    if token_user_id == target_user_id:
        return payload

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado. Apenas manager ou proprietário pode executar esta ação.",
    )
