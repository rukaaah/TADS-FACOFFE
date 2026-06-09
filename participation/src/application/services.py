"""
Módulo: services.py
Descrição: Orquestra os casos de uso do subdomínio Participation.
Responsável por aplicar as regras de negócio e controlar o acesso a recursos.
"""

from src.api.security import require_manager_or_self


def validate_manager_or_self(payload: dict, resource_owner_id: str) -> dict:
    """
    Valida se o usuário atual é manager ou proprietário do recurso.
    O serviço deve buscar o dono do recurso no banco de dados e passar o ID alvo.
    """
    return require_manager_or_self(payload=payload, target_user_id=resource_owner_id)
