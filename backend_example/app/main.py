"""
Entry Point da API - Braço Direito
FastAPI Application

Este é o arquivo principal que inicia a aplicação FastAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes import prestadores, montadores, dashboard, relatorios, blacklist, pagamentos, whatsapp, automacao, integracoes, jobs

# Criar aplicação FastAPI
app = FastAPI(
    title="Braço Direito API",
    description="API para gestão de prestadores e montadores",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS (permitir requisições do frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Frontend em desenvolvimento
        "http://localhost:5173",  # Vite alternativo
        # Adicionar URL de produção aqui
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar banco de dados na inicialização
@app.on_event("startup")
async def startup_event():
    """Executado quando a aplicação inicia"""
    print("🚀 Iniciando Braço Direito API...")
    init_db()
    print("✅ Banco de dados inicializado")

# Rota raiz
@app.get("/")
def root():
    """Endpoint raiz - verifica se API está online"""
    return {
        "message": "Braço Direito API v1.0",
        "status": "online",
        "docs": "/docs"
    }

# Health check
@app.get("/health")
def health_check():
    """Endpoint para verificar saúde da API"""
    return {"status": "healthy"}

# Registrar rotas (endpoints)
app.include_router(
    dashboard.router, 
    prefix="/api/v1/dashboard", 
    tags=["Dashboard"]
)

app.include_router(
    prestadores.router, 
    prefix="/api/v1/prestadores", 
    tags=["Prestadores"]
)

app.include_router(
    montadores.router, 
    prefix="/api/v1/montadores", 
    tags=["Montadores"]
)

app.include_router(
    relatorios.router, 
    prefix="/api/v1/relatorios", 
    tags=["Relatórios"]
)

app.include_router(
    blacklist.router, 
    prefix="/api/v1/blacklist", 
    tags=["Blacklist"]
)

app.include_router(
    pagamentos.router, 
    prefix="/api/v1/pagamentos", 
    tags=["Pagamentos"]
)

app.include_router(
    whatsapp.router, 
    prefix="/api/v1/whatsapp", 
    tags=["WhatsApp"]
)

app.include_router(
    automacao.router, 
    prefix="/api/v1/automacao", 
    tags=["Automação"]
)

app.include_router(
    integracoes.router, 
    prefix="/api/v1/integracoes", 
    tags=["Integrações"]
)

app.include_router(
    jobs.router, 
    prefix="/api/v1/jobs", 
    tags=["Jobs"]
)

# Tratamento de erros globais
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Captura todos os erros não tratados"""
    import traceback
    print(f"❌ Erro não tratado: {exc}")
    traceback.print_exc()
    return {
        "detail": "Erro interno do servidor",
        "error": str(exc)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
