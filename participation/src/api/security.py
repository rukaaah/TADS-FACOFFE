"""
Módulo: security.py
Descrição: Centraliza as barreiras de autenticação e controle de acesso (RBAC).
Responsável por interceptar as requisições, decodificar e validar o token JWT 
enviado no cabeçalho (Authorization: Bearer) e extrair a claim 'roles'. 
Também fornece as dependências para bloquear o acesso caso o usuário não possua 
o papel exigido pela rota (ex: MANAGER para criar cotas, PARTICIPANT para aderir).
"""
"""
Módulo: security.py
Descrição: Barreira de Identidade e Controlo de Acesso (RBAC).
Responsabilidade: Extrair o token JWT, decodificá-lo e validar se o utilizador possui
as permissões exigidas pelo contrato (api-docs.yaml).
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError # Biblioteca que instalámos no requirements.txt
from typing import List

# Intercetador nativo do FastAPI para extrair o Bearer Token do cabeçalho
security_scheme = HTTPBearer()

def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    """
    Extrai e decodifica o JWT para recuperar os dados do utilizador.
    """
    token = credentials.credentials
    
    try:
        # TODO EQUIPE: O Nginx já validou a assinatura do token na borda. 
        # Aqui podemos apenas decodificá-lo de forma passiva para ler o conteúdo (verify=False),
        # ou configurar a chave pública do Keycloak para verificação dupla (Mais seguro).
        # A claim 'sub' contém o userId e a claim 'roles' contém a lista de papéis.
        
        payload = jwt.decode(token, options={"verify_signature": False}) 
        return payload
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou corrompido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(required_roles: List[str]):
    """
    Injetor de dependência para verificar papéis (RBAC).
    Ref: api-docs.yaml -> x-authorization: scope: ROLE
    """
    def role_checker(payload: dict = Depends(get_current_user_payload)):
        # O Keycloak (conforme realm-facoffee.json) coloca as roles nesta claim
        user_roles = payload.get("roles", [])
        
        # Verifica se o utilizador tem PELO MENOS UMA das roles exigidas
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Nível de privilégio insuficiente."
            )
        
        return payload # Retorna o payload para que o router possa usar o userId, se precisar
    
    return role_checker

def require_manager_or_self(requested_user_id: str, payload: dict = Depends(get_current_user_payload)):
    """
    Validação de regras complexas.
    Ref: api-docs.yaml -> x-authorization: scope: ACCESS_RULE allow: [MANAGER_OR_SELF]
    """
    # TODO EQUIPE: Implementar esta lógica de negócio de segurança.
    # 1. Obter o userId do token (payload.get("sub"))
    # 2. Obter as roles do token (payload.get("roles", []))
    # 3. Se a role for "MANAGER", deixar passar.
    # 4. Se o userId do token for igual ao `requested_user_id` passado na URL, deixar passar.
    # 5. Se não for nenhum dos dois, lançar HTTPException 403 Forbidden.
    pass