"""
Módulo: session.py
Descrição: Gerencia a conexão com o banco de dados exclusivo do serviço de 
Cotas e Adesões (Database per Service). Define a 'Engine' de conexão e 
disponibiliza sessões (transações) seguras para a camada de repositório.
Nenhum outro serviço tem acesso a essa string de conexão.
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Recupera a URL de conexão do ambiente (Docker/Produção) ou adota um fallback seguro local (SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///participation.db")

# Configurações específicas para o motor do banco de dados
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # Necessário para permitir que múltiplas threads acessem o banco de dados SQLite local durante o desenvolvimento
    connect_args = {"check_same_thread": False}

# Criação do Engine do SQLAlchemy. O pool de conexões e logs de eco podem ser configurados aqui.
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    echo=False
)

# Fábrica de sessões vinculada ao Engine.
# expire_on_commit=False impede que os atributos das entidades fiquem indisponíveis após um commit.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """
    Injetor de Dependência para o FastAPI.
    Garante que cada requisição HTTP receba uma sessão isolada e que a conexão
    seja fechada deterministicamente ao final do ciclo de vida da requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Gerenciador de Contexto para uso fora do escopo HTTP do FastAPI.
    Essencial para workers em background, scripts de migração ou consumidores
    de mensageria assíncrona (RabbitMQ), garantindo tratamento automático de rollback.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()