"""
Módulo: models.py
Descrição: Define as Entidades de Domínio e o esquema do Banco de Dados Isolado 
(Database per Service). Aqui mapeamos como os dados de Cotas e Participações 
são estruturados, tipados e salvos no banco. Nenhuma outra tabela externa 
(como Usuários ou Financeiro) pode existir ou ser referenciada diretamente aqui.
"""

import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Numeric, DateTime, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Classe base do SQLAlchemy 2.0 para todos os modelos do subdomínio Participation."""
    pass


class ParticipationQuota(Base):
    """
    Entidade: Cota de Participação
    Mapeamento: Refere-se à Seção 4.1 do documento SAD.md.
    """
    __tablename__ = "participation_quotas"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)  
    items: Mapped[str] = mapped_column(String(50), nullable=False)      
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)     
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    memberships: Mapped[list["ParticipationMembership"]] = relationship(
        "ParticipationMembership", 
        back_populates="quota"
    )


class ParticipationMembership(Base):
    """
    Entidade: Adesão/Participação
    Mapeamento: Refere-se à Seção 4.2 do documento SAD.md.
    """
    __tablename__ = "participation_memberships"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True) 
    quota_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("participation_quotas.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False) 
    start_cycle: Mapped[str] = mapped_column(String(7), nullable=False) 
    end_cycle: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    
    quota_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    quota: Mapped["ParticipationQuota"] = relationship(
        "ParticipationQuota", 
        back_populates="memberships"
    )