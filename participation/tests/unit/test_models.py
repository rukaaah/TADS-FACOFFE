import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from src.domain.models import Base, ParticipationQuota, ParticipationMembership
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


# 1. Teste Automatizado para a Regra de Negócio de Cancelamento
def test_should_save_cancellation_metadata_successfully(db_session):
    """Garante que o banco possui e aceita as colunas de auditoria de cancelamento."""
    # Arrange (Prepara o ambiente)
    cota = ParticipationQuota(
        id="quota_001", name="Cota Teste", condition="DAILY", 
        items="ALL", amount=Decimal("50.00"), status="ACTIVE", created_by="manager"
    )
    db_session.add(cota)
    db_session.commit()

    # Act (Executa a ação)
    adesao = ParticipationMembership(
        id="part_001", user_id="usr_123", quota_id="quota_001",
        status="CANCELLED", start_cycle="2026-06", quota_snapshot={"amount": 50.00},
        cancellation_reason="Motivo de Auditoria",
        cancelled_by="usr_123"
    )
    db_session.add(adesao)
    db_session.commit()

    # Assert (Verifica se o resultado é o esperado de verdade)
    resultado = db_session.query(ParticipationMembership).filter_by(id="part_001").first()
    assert resultado is not None
    assert resultado.cancellation_reason == "Motivo de Auditoria"
    assert resultado.cancelled_by == "usr_123"


# 2. Teste de Regressão contra o Efeito Cascade (Delete Orphan)
def test_should_not_delete_memberships_when_quota_is_deleted(db_session):
    """Garante que o Soft Delete seja respeitado e a exclusão da cota NÃO apague o histórico."""
    # Arrange
    cota = ParticipationQuota(
        id="quota_001", name="Cota Teste", condition="DAILY", 
        items="ALL", amount=Decimal("50.00"), status="ACTIVE", created_by="manager"
    )
    db_session.add(cota)
    db_session.commit()

    adesao = ParticipationMembership(
        id="part_001", user_id="usr_123", quota_id="quota_001",
        status="ACTIVE", start_cycle="2026-06", quota_snapshot={"amount": 50.00}
    )
    db_session.add(adesao)
    db_session.commit()

    # Act - Deletando a cota fisicamente (Simulação de erro operacional)
    with pytest.raises(IntegrityError):
        db_session.delete(cota)
        db_session.commit()
        
    db_session.rollback()
    # Assert - A adesão PRECISA continuar existindo no banco de dados!
    total_adesoes_restantes = db_session.query(ParticipationMembership).count()
    
    # Se o cascade estiver errado, o total será 0 e o teste falhará no CI/CD acusando o erro
    assert total_adesoes_restantes == 1, "CRÍTICO: O relacionamento deletou em cascata as participações!"