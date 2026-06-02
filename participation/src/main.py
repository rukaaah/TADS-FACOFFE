"""
Módulo: main.py
Descrição: Ponto de entrada (Entrypoint) do Microsserviço de Participation.
Responsabilidade: Inicializar a aplicação FastAPI e registrar os routers.
"""

from fastapi import FastAPI
from src.api.routers import router as participation_router

# Inicialização do aplicativo FastAPI com as informações do Swagger
app = FastAPI(
    title="FACOFFEE - Participation Service",
    description="Microsserviço responsável pela gestão de cotas e adesões dos participantes.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ---------------------------------------------------------
# REGISTRO DE ROTAS
# ---------------------------------------------------------
# Conectando o router que criamos em src/api/routers.py
app.include_router(participation_router, prefix="/api")

# ---------------------------------------------------------
# HEALTHCHECK (Exigência do API Gateway / Nginx)
# ---------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Verificação de saúde do serviço")
def health_check():
    """Endpoint utilizado pelo Nginx/Docker para saber se o serviço está vivo."""
    return {"status": "ok", "service": "participation"}