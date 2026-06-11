"""
Entry Point da API - Braço Direito
FastAPI Application

Este é o arquivo principal que inicia a aplicação FastAPI.
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.database import init_db
from app.utils.rate_limit import limiter
from app.routes import prestadores, montadores, dashboard, relatorios, blacklist, pagamentos, whatsapp, automacao, integracoes, jobs, auth, upload_api, notifications, sistema_auth, custos_extras, mms, pre_cadastro, gestao_pagamentos, lancamentos_motorista, dados_bot, crm, montagem, ingestao, ingestao_sync, terceirizadas, aprovacoes, auto_envio_routes, email_templates

# Carregar .env do diretório do projeto (backend_example/) independente do CWD
_env_path = Path(__file__).resolve().parent.parent / '.env'
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv(find_dotenv())

ENV = os.getenv("ENV", "development").lower()
IS_PROD = ENV in ("production", "prod")

# Criar aplicação FastAPI — desabilita docs em produção para não vazar schema
app = FastAPI(
    title="Braço Direito API",
    description="API para gestão de prestadores e montadores",
    version="1.0.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# --- CORS (DEVE ser o primeiro middleware para interceptar preflight OPTIONS) ---
# Lista explícita de origens autorizadas. Em dev, inclui localhost.
_default_origins = [
    "https://suportedg.site",
    "https://www.suportedg.site",
]
if not IS_PROD:
    _default_origins += [
        "http://localhost:14002",
        "http://localhost:5173",
        "http://127.0.0.1:14002",
        "http://127.0.0.1:5173",
    ]

_extra_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
cors_origins = list({*_default_origins, *_extra_origins})

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-API-Key", "X-Setup-Token"],
)

# Rate limiter (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# --- Security Headers middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if IS_PROD:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)

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
app.include_router(
    sistema_auth.router, 
    prefix="/api/v1/sistema", 
    tags=["Sistema - Autenticação"]
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
    custos_extras.router, 
    prefix="/api/v1/custos-extras", 
    tags=["Custos Extras"]
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

app.include_router(
    mms.router, 
    prefix="/api/v1/mms", 
    tags=["MMS - Limpeza de Dados"]
)

app.include_router(
    pre_cadastro.router, 
    prefix="/api/v1/pre-cadastro-montadores", 
    tags=["Pré-Cadastro Montadores"]
)

app.include_router(
    gestao_pagamentos.router, 
    prefix="/api/v1/gestao-pagamentos", 
    tags=["Gestão de Pagamentos"]
)

app.include_router(
    lancamentos_motorista.router, 
    prefix="/api/v1/lancamentos-motorista", 
    tags=["Lançamentos Motorista"]
)

app.include_router(
    montagem.router,
    prefix="/api/v1/montagem",
    tags=["Acompanhamento Montagem"]
)

app.include_router(
    dados_bot.router, 
    prefix="/api/v1/dados-bot", 
    tags=["Dados Bot"]
)

app.include_router(
    ingestao.router, 
    prefix="/api/v1/ingestao", 
    tags=["Ingestão de Boletins"]
)

app.include_router(
    ingestao_sync.router, 
    prefix="/api/v1/ingestao", 
    tags=["Sync de Boletins"]
)

app.include_router(
    crm.router, 
    prefix="/api/v1/crm", 
    tags=["CRM"]
)

app.include_router(
    terceirizadas.router, 
    prefix="/api/v1/terceirizadas", 
    tags=["Terceirizadas"]
)

app.include_router(
    aprovacoes.router, 
    prefix="/api/v1/aprovacoes", 
    tags=["Aprovações"]
)

app.include_router(
    auto_envio_routes.router, 
    prefix="/api/v1/auto-envio", 
    tags=["Envio Automático"]
)

app.include_router(
    email_templates.router,
    prefix="/api/v1/email-templates",
    tags=["Templates de Email"]
)

# Tratamento de erros globais
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura todos os erros não tratados"""
    import traceback
    print(f"❌ Erro não tratado: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor",
            "error": str(exc) if not IS_PROD else "Erro interno"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=14001)
