import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.domain.models import Base, ParticipationQuota, ParticipationMembership
from src.infrastructure.database.repositories import ParticipationRepository

# ==========================================
# FIXTURES (Setup do Banco em Memória)
# ==========================================
@pytest.fixture
def db_session():
    """Cria um banco SQLite em memória limpo para cada teste."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def repo(db_session):
    """Injeta a sessão limpa no repositório."""
    return ParticipationRepository(db_session)

# ==========================================
# TESTES DE COTAS (QUOTAS)
# ==========================================
def test_save_and_get_quota(repo):
    """Testa se consegue salvar e recuperar uma cota do banco[cite: 8]."""
    cota = ParticipationQuota(
        id="quota_123",
        name="Cota Teste",
        condition="DAILY",
        items="ALL",
        amount=50.0,
        status="ACTIVE",
        created_by="manager_1"
    )
    repo.save_quota(cota)
    
    recuperada = repo.get_quota_by_id("quota_123")
    assert recuperada is not None
    assert recuperada.name == "Cota Teste"
    assert recuperada.amount == 50.0

def test_list_quotas_with_filters(repo):
    """Testa a listagem e os filtros dinâmicos de cotas[cite: 8]."""
    cota1 = ParticipationQuota(id="q1", name="C1", condition="DAILY", items="ALL", amount=10, status="ACTIVE", created_by="m1")
    cota2 = ParticipationQuota(id="q2", name="C2", condition="SPORADIC", items="COFFEE", amount=20, status="INACTIVE", created_by="m1")
    repo.save_quota(cota1)
    repo.save_quota(cota2)

    # Filtra apenas ativas
    ativas, total_ativas = repo.list_quotas(active=True, condition=None, items=None, skip=0, limit=10)
    assert total_ativas == 1
    assert ativas[0].id == "q1"

    # Filtra por condição SPORADIC
    sporadic, total_sporadic = repo.list_quotas(active=None, condition="SPORADIC", items=None, skip=0, limit=10)
    assert total_sporadic == 1
    assert sporadic[0].id == "q2"

# ==========================================
# TESTES DE ADESÕES (PARTICIPATIONS)
# ==========================================
def test_get_active_participation_by_user(repo):
    """Testa a busca de adesão ativa por usuário (Base para RN02)[cite: 8]."""
    cota = ParticipationQuota(id="q1", name="C1", condition="DAILY", items="ALL", amount=10, status="ACTIVE", created_by="m1")
    repo.save_quota(cota)
    
    adesao = ParticipationMembership(
        id="part_1",
        user_id="usr_999",
        quota_id="q1",
        status="ACTIVE",
        start_cycle="2026-06",
        quota_snapshot={"name": "C1"}
    )
    repo.save_participation(adesao)

    ativa = repo.get_active_participation_by_user("usr_999")
    assert ativa is not None
    assert ativa.id == "part_1"
    assert ativa.status == "ACTIVE"

def test_count_active_participations_by_quota(repo):
    """Testa a contagem de adesões vinculadas a uma cota (Base para RN03)[cite: 8]."""
    cota = ParticipationQuota(id="q1", name="C1", condition="DAILY", items="ALL", amount=10, status="ACTIVE", created_by="m1")
    repo.save_quota(cota)
    
    repo.save_participation(ParticipationMembership(id="p1", user_id="u1", quota_id="q1", status="ACTIVE", start_cycle="2026-06", quota_snapshot={}))
    repo.save_participation(ParticipationMembership(id="p2", user_id="u2", quota_id="q1", status="CANCELLED", start_cycle="2026-06", quota_snapshot={}))

    # Deve contar apenas a ACTIVE
    total = repo.count_active_participations_by_quota("q1")
    assert total == 1