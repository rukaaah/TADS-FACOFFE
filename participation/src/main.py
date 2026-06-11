"""
Módulo: main.py
Descrição: Ponto de entrada (Entrypoint) do Microsserviço de Participation.
Responsabilidade: Inicializar a aplicação FastAPI, configurar banco de dados, 
registrar handlers de erro globais e os routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Importações das camadas do sistema
from src.api.routers import router as participation_router
from src.domain.exceptions import DomainError
from src.infrastructure.database.session import engine
from src.domain.models import Base

# ---------------------------------------------------------
# GERENCIAMENTO DO CICLO DE VIDA (LIFESPAN)
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado antes da aplicação começar a receber requisições.
    Garante que o banco de dados exclusivo do serviço (Database per Service)
    esteja criado e sincronizado.
    """
    # Cria as tabelas definidas em models.py se elas ainda não existirem
    Base.metadata.create_all(bind=engine)
    
    yield  # A API fica rodando neste ponto
    
    # Aqui entraria a lógica de encerramento seguro (shutdown), se necessário

# Inicialização do aplicativo FastAPI
app = FastAPI(
    title="FACOFFEE - Participation Service",
    description="Microsserviço responsável pela gestão de cotas e adesões dos participantes.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ---------------------------------------------------------
# TRATAMENTO DE EXCEÇÕES GLOBAIS (ERROR HANDLERS)
# ---------------------------------------------------------
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """
    Intercepta instâncias de `DomainError` e suas subclasses (como NotFoundError e ConflictError) 
    lançadas pela camada de serviços e as traduz para uma resposta HTTP apropriada.
    """
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_dict()
    )

# ---------------------------------------------------------
# REGISTRO DE ROTAS
# ---------------------------------------------------------
# Conectando o router que expõe os endpoints sob responsabilidade de Participation
app.include_router(participation_router, prefix="/api")

# ---------------------------------------------------------
# HEALTHCHECK (Exigência do API Gateway / Nginx)
# ---------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Verificação de saúde do serviço")
def health_check():
    """Endpoint utilizado pelo Nginx/Docker para saber se o serviço está vivo."""
    return {"status": "ok", "service": "participation"}