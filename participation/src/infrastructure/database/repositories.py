"""
Módulo: repositories.py
Descrição: Implementa o padrão Repository. Isola todas as queries e operações 
de I/O (CRUD) do banco de dados. A camada de serviços (`services.py`) não deve 
escrever SQL ou saber como os dados são salvos; ela apenas chama os métodos 
deste arquivo (ex: `salvar_cota`, `buscar_participacoes_ativas`).
"""

from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.domain.models import ParticipationQuota, ParticipationMembership
from src.domain.exceptions import RepositoryError


class ParticipationRepository:
    """
    Repositório para gerenciar operações de banco de dados das entidades 
    ParticipationQuota e ParticipationMembership de forma centralizada.
    """
    
    def __init__(self, session: Session):
        self.session = session

    # ==========================================
    # DOMÍNIO DE COTAS (QUOTAS)
    # ==========================================
    def save_quota(self, quota: ParticipationQuota) -> ParticipationQuota:
        """Salva uma nova cota ou atualiza uma existente (Upsert implícito pela Session)."""
        try:
            self.session.add(quota)
            self.session.flush() # Sincroniza com o banco para gerar campos padrão (ex: created_at)
            return quota
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro de I/O ao salvar a cota: {str(e)}")

    def get_quota_by_id(self, quota_id: str) -> Optional[ParticipationQuota]:
        """Busca uma cota específica pelo seu identificador."""
        try:
            stmt = select(ParticipationQuota).where(ParticipationQuota.id == quota_id)
            return self.session.scalars(stmt).first()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao buscar a cota por ID: {str(e)}")

    def list_quotas(
        self, 
        active: Optional[bool], 
        condition: Optional[str], 
        items: Optional[str], 
        skip: int, 
        limit: int
    ) -> Tuple[List[ParticipationQuota], int]:
        """
        Lista as cotas com filtros opcionais.
        Retorna uma tupla: (lista_de_cotas, total_de_registros_sem_paginacao)
        O total é essencial para montar os metadados PageMetadata do contrato da API.
        """
        try:
            query = select(ParticipationQuota)
            count_query = select(func.count()).select_from(ParticipationQuota)

            filters = []
            if active is not None:
                status_filter = "ACTIVE" if active else "INACTIVE"
                filters.append(ParticipationQuota.status == status_filter)
            if condition:
                filters.append(ParticipationQuota.condition == condition)
            if items:
                filters.append(ParticipationQuota.items == items)

            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))

            total_elements = self.session.scalar(count_query) or 0

            query = query.offset(skip).limit(limit)
            quotas = list(self.session.scalars(query).all())

            return quotas, total_elements
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao listar cotas filtradas: {str(e)}")


    # ==========================================
    # DOMÍNIO DE ADESÕES (PARTICIPATIONS)
    # ==========================================
    def save_participation(self, participation: ParticipationMembership) -> ParticipationMembership:
        """Salva uma nova adesão ou atualiza uma existente no banco."""
        try:
            self.session.add(participation)
            self.session.flush()
            return participation
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro de I/O ao salvar a participação: {str(e)}")

    def get_participation_by_id(self, participation_id: str) -> Optional[ParticipationMembership]:
        """Busca uma adesão pelo seu ID."""
        try:
            stmt = select(ParticipationMembership).where(ParticipationMembership.id == participation_id)
            return self.session.scalars(stmt).first()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao buscar a participação por ID: {str(e)}")

    def get_active_participation_by_user(self, user_id: str) -> Optional[ParticipationMembership]:
        """
        Busca uma participação ativa de um usuário específico.
        Fundamental para a regra de negócio RN02 (Adesão Única Ativa).
        """
        try:
            stmt = select(ParticipationMembership).where(
                and_(
                    ParticipationMembership.user_id == user_id,
                    ParticipationMembership.status == "ACTIVE"
                )
            )
            return self.session.scalars(stmt).first()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao buscar participações ativas do usuário: {str(e)}")

    def count_active_participations_by_quota(self, quota_id: str) -> int:
        """
        Conta adesões ativas amarradas a uma cota.
        Fundamental para a regra de negócio RN03 (Proibição de desativar cota em uso).
        """
        try:
            stmt = select(func.count()).select_from(ParticipationMembership).where(
                and_(
                    ParticipationMembership.quota_id == quota_id,
                    ParticipationMembership.status == "ACTIVE"
                )
            )
            return self.session.scalar(stmt) or 0
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao contar participações ativas na cota: {str(e)}")

    def list_participations(
        self,
        user_id: Optional[str],
        quota_id: Optional[str],
        status: Optional[str],
        cycle: Optional[str],
        skip: int,
        limit: int
    ) -> Tuple[List[ParticipationMembership], int]:
        """
        Lista adesões aplicando filtros dinâmicos de Query Params.
        """
        try:
            query = select(ParticipationMembership)
            count_query = select(func.count()).select_from(ParticipationMembership)

            filters = []
            if user_id:
                filters.append(ParticipationMembership.user_id == user_id)
            if quota_id:
                filters.append(ParticipationMembership.quota_id == quota_id)
            if status:
                filters.append(ParticipationMembership.status == status)
            if cycle:
                # Retorna a participação se ela esteva ativa no ciclo pesquisado:
                # O start_cycle tem que ser menor ou igual ao ciclo pesquisado E
                # O end_cycle não existir (None) ou for maior ou igual ao ciclo pesquisado.
                filters.append(
                    and_(
                        ParticipationMembership.start_cycle <= cycle,
                        or_(
                            ParticipationMembership.end_cycle.is_(None),
                            ParticipationMembership.end_cycle >= cycle
                        )
                    )
                )

            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))

            total_elements = self.session.scalar(count_query) or 0

            query = query.offset(skip).limit(limit)
            participations = list(self.session.scalars(query).all())

            return participations, total_elements
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao listar participações: {str(e)}")

    def get_all_active_participations_by_user(self, user_id: str) -> List[ParticipationMembership]:
        """
        Retorna todas as participações ativas do usuário. 
        Usado principalmente pelo RabbitMQ Consumer ao receber 'UserDeactivated' para cancelar cotas.
        """
        try:
            stmt = select(ParticipationMembership).where(
                and_(
                    ParticipationMembership.user_id == user_id,
                    ParticipationMembership.status == "ACTIVE"
                )
            )
            return list(self.session.scalars(stmt).all())
        except SQLAlchemyError as e:
            raise RepositoryError(f"Erro ao buscar adesões para cancelamento em lote: {str(e)}")