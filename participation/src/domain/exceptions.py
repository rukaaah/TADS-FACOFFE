"""
Módulo: exceptions.py
Descrição: Centraliza todos os erros personalizados do domínio de Cotas e Adesões.
Em vez de lançar erros genéricos de HTTP (como 400 ou 404) dentro das regras de 
negócio, o serviço lança estas exceções puras. A camada de API (routers) ficará 
responsável por capturar (catch) esses erros de domínio e traduzi-los para os 
códigos HTTP corretos do contrato OpenAPI.
"""

from typing import Any, Dict, Optional


class DomainError(Exception):
	"""Erro base para o domínio.

	A camada de API deve interceptar instâncias de `DomainError` e traduzi-las
	para respostas HTTP apropriadas. Guardamos uma `code` curta e um
	`http_status` sugerido para facilitar essa tradução.
	"""

	code: str = "domain_error"
	http_status: int = 400

	def __init__(self, message: str, *, code: Optional[str] = None, payload: Optional[Dict[str, Any]] = None):
		super().__init__(message)
		self.message = message
		if code:
			self.code = code
		self.payload = payload or {}

	def to_dict(self) -> Dict[str, Any]:
		return {"error": {"code": self.code, "message": self.message, "payload": self.payload}}


class NotFoundError(DomainError):
	code = "not_found"
	http_status = 404


class ConflictError(DomainError):
	code = "conflict"
	http_status = 409


class ValidationError(DomainError):
	code = "validation_error"
	http_status = 400


class UnauthorizedError(DomainError):
	code = "unauthorized"
	http_status = 401


class ForbiddenError(DomainError):
	code = "forbidden"
	http_status = 403


class RepositoryError(DomainError):
	code = "repository_error"
	http_status = 500
