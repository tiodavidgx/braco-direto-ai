"""
Entry Point da API - Braço Direito
FastAPI Application

Este é o arquivo principal que inicia a aplicação FastAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes import prestadores, montadores, dashboard, relatorios, blacklist, pagamentos, whatsapp, automacao, integracoes, jobs, auth, upload_api, notifications, upload_nf, user_auth

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
        "http://localhost:8080",  # Frontend em desenvolvimento (legado)
        "http://localhost:5173",  # Vite alternativo
        "http://localhost:3080",  # Frontend nova porta
        "http://72.60.244.138",   # VPS IP direto
        "http://suportedg.site",  # Produção HTTP
        "https://suportedg.site", # Produção HTTPS
        "http://www.suportedg.site",
        "https://www.suportedg.site",
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
    
    # Iniciar scheduler de jobs
    try:
        from app.scheduler import iniciar_scheduler
        iniciar_scheduler()
        print("✅ Scheduler de jobs iniciado")
    except Exception as e:
        print(f"⚠️  Erro ao iniciar scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Executado quando a aplicação encerra"""
    try:
        from app.scheduler import parar_scheduler
        parar_scheduler()
        print("🛑 Scheduler de jobs parado")
    except Exception as e:
        print(f"⚠️  Erro ao parar scheduler: {e}")

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
# Rotas de autenticação de usuários (públicas)
app.include_router(
    user_auth.router,
    prefix="/api/v1/user-auth",
    tags=["Autenticação de Usuários"]
)

app.include_router(
    auth.router, 
    prefix="/api/v1/auth", 
    tags=["Autenticação Microsoft"]
)

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

app.include_router(
    upload_api.router, 
    prefix="/api/v1/upload", 
    tags=["Upload API"]
)

app.include_router(
    notifications.router, 
    prefix="/api/v1", 
    tags=["Notificações"]
)

# Upload de NF - Rotas públicas (sem auth)
app.include_router(
    upload_nf.router, 
    prefix="/api/v1/upload-nf", 
    tags=["Upload NF"]
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
