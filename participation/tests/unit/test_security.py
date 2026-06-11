import pytest
from fastapi import HTTPException
from src.api.security import require_role, require_manager_or_self

def test_require_role_success():
    """Garante que a função permite acesso se o usuário tiver a role exigida."""
    payload_valido = {"sub": "usr_1", "roles": ["MANAGER", "USER"]}
    
    # O require_role retorna uma função (closure) que avalia o payload
    validador = require_role(["MANAGER"])
    
    # Se não levantar exceção, o teste passa e retorna o próprio payload
    resultado = validador(payload=payload_valido)
    assert resultado == payload_valido

def test_require_role_fails_with_403():
    """Garante que a função bloqueia (403) se o usuário não tiver a role."""
    payload_invalido = {"sub": "usr_2", "roles": ["PARTICIPANT"]}
    validador = require_role(["MANAGER"])
    
    with pytest.raises(HTTPException) as exc_info:
        validador(payload=payload_invalido)
        
    assert exc_info.value.status_code == 403
    assert "Acesso negado" in exc_info.value.detail

def test_require_manager_or_self_allows_manager():
    """Manager pode acessar recursos de qualquer outro usuário."""
    payload_manager = {"sub": "usr_admin", "roles": ["MANAGER"]}
    target_user_id = "usr_comum" # Tentando acessar dados de outro
    
    resultado = require_manager_or_self(payload_manager, target_user_id)
    assert resultado == payload_manager

def test_require_manager_or_self_allows_self():
    """Usuário comum pode acessar seus próprios recursos."""
    payload_comum = {"sub": "usr_123", "roles": ["PARTICIPANT"]}
    target_user_id = "usr_123" # Tentando acessar os próprios dados
    
    resultado = require_manager_or_self(payload_comum, target_user_id)
    assert resultado == payload_comum

def test_require_manager_or_self_blocks_others_with_403():
    """Usuário comum recebe 403 ao tentar acessar recursos de terceiros."""
    payload_comum = {"sub": "usr_123", "roles": ["PARTICIPANT"]}
    target_user_id = "usr_999" # Tentando acessar dados de outro
    
    with pytest.raises(HTTPException) as exc_info:
        require_manager_or_self(payload_comum, target_user_id)
        
    assert exc_info.value.status_code == 403
    assert "Apenas manager ou proprietário pode executar esta ação" in exc_info.value.detail