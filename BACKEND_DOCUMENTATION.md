# Documentação Backend - Braço Direito

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
4. [APIs REST](#apis-rest)
5. [Configuração do Ambiente](#configuração-do-ambiente)
6. [Guia de Implementação](#guia-de-implementação)
7. [Integrações](#integrações)
8. [Segurança](#segurança)

---

## 🎯 Visão Geral

O **Braço Direito** é um sistema de gestão de prestadores e montadores com foco em:
- Gestão de lotes de serviço e OS (Ordens de Serviço)
- Controle de pagamentos e notas fiscais
- Integração com WhatsApp e Trello
- Automação de jobs e relatórios

### Tecnologias Backend

- **Python 3.9+**
- **PostgreSQL** (Banco de dados principal)
- **FastAPI** (Framework web - recomendado)
- **psycopg2** (Driver PostgreSQL)
- **python-dotenv** (Gerenciamento de variáveis de ambiente)

---

## 🏗️ Arquitetura

```
backend/
├── app/
│   ├── main.py                 # Entry point da aplicação
│   ├── config.py               # Configurações
│   ├── database.py             # Conexão com banco
│   ├── models/                 # Modelos de dados
│   │   ├── prestador.py
│   │   ├── montador.py
│   │   └── lote.py
│   ├── routes/                 # Endpoints da API
│   │   ├── prestadores.py
│   │   ├── montadores.py
│   │   ├── lotes.py
│   │   └── dashboard.py
│   ├── services/               # Lógica de negócio
│   │   ├── email_service.py
│   │   ├── whatsapp_service.py
│   │   └── nf_service.py
│   └── utils/                  # Utilitários
│       ├── pdf_generator.py
│       └── validators.py
├── migrations/                 # Scripts de migração
├── tests/                      # Testes automatizados
├── requirements.txt            # Dependências
└── .env                        # Variáveis de ambiente
```

---

## 🗄️ Estrutura do Banco de Dados

### Tabela: `prestadores`

```sql
CREATE TABLE prestadores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    fornecedor_id TEXT UNIQUE,
    telefone TEXT,
    regra_envio TEXT,
    dias_envio TEXT,
    emails_adicionais TEXT,
    tempo_vencimento_dias INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `montadores`

```sql
CREATE TABLE montadores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    identificador TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    telefone TEXT,
    percentual_comissao REAL NOT NULL,
    auxilio_semanal REAL NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    fornecedor_id TEXT UNIQUE,
    regra_envio TEXT,
    dias_envio TEXT,
    emails_adicionais TEXT,
    tempo_vencimento_dias INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `lotes_servico`

```sql
CREATE TABLE lotes_servico (
    id SERIAL PRIMARY KEY,
    prestador_id INTEGER REFERENCES prestadores(id),
    prestador_nome TEXT,
    periodo TEXT NOT NULL,
    valor_total REAL NOT NULL,
    data_envio TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'Em Aberto',
    conversation_id TEXT,
    anexo_path TEXT,
    
    -- Campos de upload NF
    id_controle INTEGER,
    link_upload TEXT,
    validade_link DATE,
    status_api INTEGER DEFAULT 0,
    data_envio_api TIMESTAMP,
    nota_fiscal_path TEXT,
    api_message TEXT,
    upload_hash TEXT,
    
    -- Campos de pagamento
    data_recebimento_nf TIMESTAMP,
    data_vencimento_pagamento DATE,
    pago BOOLEAN DEFAULT FALSE,
    data_pagamento TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `os_enviadas`

```sql
CREATE TABLE os_enviadas (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes_servico(id) ON DELETE CASCADE,
    os_numero TEXT NOT NULL UNIQUE,
    detalhes JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `envios_montagem`

```sql
CREATE TABLE envios_montagem (
    id SERIAL PRIMARY KEY,
    montador_id INTEGER REFERENCES montadores(id),
    montador_nome TEXT,
    periodo TEXT,
    data_envio TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'Em Aberto',
    detalhes JSONB,
    conversation_id TEXT,
    anexo_path TEXT,
    quantidade_os INTEGER,
    valor_total NUMERIC(10, 2),
    
    -- Campos de upload NF
    id_controle INTEGER,
    link_upload TEXT,
    validade_link DATE,
    status_api INTEGER DEFAULT 0,
    data_envio_api TIMESTAMP,
    nota_fiscal_path TEXT,
    api_message TEXT,
    upload_hash TEXT,
    status_arquivo INTEGER DEFAULT 0,
    data_ultima_consulta TIMESTAMP,
    
    -- Campos de pagamento
    data_recebimento_nf TIMESTAMP,
    data_vencimento_pagamento DATE,
    pago BOOLEAN DEFAULT FALSE,
    data_pagamento TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔌 APIs REST

### Base URL

```
http://localhost:8000/api/v1
```

### Autenticação

Todas as rotas devem usar autenticação JWT:

```python
# Header
Authorization: Bearer <token>
```

---

### 📊 Dashboard

#### GET `/dashboard/stats`

Retorna estatísticas gerais do sistema.

**Response:**
```json
{
  "prestadores_ativos": 24,
  "montadores_ativos": 18,
  "pagamentos_pendentes": 45280.50,
  "nfs_aguardando": 12,
  "lotes_mes_atual": 38,
  "crescimento_mensal": 12.5
}
```

#### GET `/dashboard/pendencias`

Lista todas as pendências do dia.

**Response:**
```json
{
  "pendencias": [
    {
      "id": 1,
      "tipo": "prestador",
      "nome": "Prestadora ABC Ltda",
      "acao": "Envio de relatório semanal",
      "data_vencimento": "2025-11-11",
      "status": "urgent"
    }
  ]
}
```

---

### 👥 Prestadores

#### GET `/prestadores`

Lista todos os prestadores.

**Query Parameters:**
- `search` (opcional): Filtro por nome
- `ativo` (opcional): Filtrar por status
- `page` (opcional): Número da página
- `limit` (opcional): Itens por página

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "nome": "Prestadora ABC Ltda",
      "email": "contato@abc.com",
      "fornecedor_id": "FOR123",
      "telefone": "(11) 98765-4321",
      "regra_envio": "Semanal",
      "dias_envio": "Segunda-feira",
      "tempo_vencimento_dias": 10,
      "emails_adicionais": "financeiro@abc.com",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 24,
  "page": 1,
  "pages": 3
}
```

#### POST `/prestadores`

Cria um novo prestador.

**Request Body:**
```json
{
  "nome": "Prestadora Nova",
  "email": "contato@nova.com",
  "fornecedor_id": "FOR999",
  "telefone": "(11) 99999-9999",
  "regra_envio": "Semanal",
  "dias_envio": "Terça-feira",
  "tempo_vencimento_dias": 10,
  "emails_adicionais": "financeiro@nova.com"
}
```

**Response:** `201 Created`
```json
{
  "id": 25,
  "nome": "Prestadora Nova",
  "message": "Prestador criado com sucesso"
}
```

#### PUT `/prestadores/{id}`

Atualiza um prestador existente.

**Response:** `200 OK`

#### DELETE `/prestadores/{id}`

Remove um prestador.

**Response:** `204 No Content`

---

### 🔧 Montadores

#### GET `/montadores`

Lista todos os montadores.

**Query Parameters:**
- `search` (opcional)
- `ativo` (opcional): true/false
- `page` (opcional)
- `limit` (opcional)

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "nome": "João Silva",
      "identificador": "MONT001",
      "email": "joao.silva@email.com",
      "telefone": "(11) 98765-1111",
      "percentual_comissao": 5.5,
      "auxilio_semanal": 150.00,
      "ativo": true,
      "fornecedor_id": "MONT001",
      "regra_envio": "Quinzenal",
      "dias_envio": "1, 15"
    }
  ],
  "total": 18,
  "page": 1,
  "pages": 2
}
```

#### POST `/montadores`

Cria um novo montador.

**Request Body:**
```json
{
  "nome": "Maria Santos",
  "identificador": "MONT999",
  "email": "maria@email.com",
  "telefone": "(11) 98765-2222",
  "percentual_comissao": 6.0,
  "auxilio_semanal": 150.00,
  "ativo": true,
  "regra_envio": "Mensal (Dia Fixo)",
  "dias_envio": "5"
}
```

**Response:** `201 Created`

#### PUT `/montadores/{id}`

Atualiza um montador.

#### DELETE `/montadores/{id}`

Remove um montador.

---

### 📦 Lotes de Serviço

#### GET `/lotes`

Lista lotes de serviço.

**Query Parameters:**
- `prestador_id` (opcional)
- `status` (opcional): Em Aberto, Aguardando NF, Pago
- `periodo` (opcional)
- `page`, `limit`

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "prestador_id": 1,
      "prestador_nome": "Prestadora ABC Ltda",
      "periodo": "01/11/2025 - 07/11/2025",
      "valor_total": 15480.50,
      "data_envio": "2025-11-08T10:30:00Z",
      "status": "Aguardando NF",
      "link_upload": "https://api.link.dev.br/upload/abc123",
      "validade_link": "2025-11-18",
      "quantidade_os": 12,
      "data_vencimento_pagamento": "2025-11-25"
    }
  ]
}
```

#### POST `/lotes`

Cria um novo lote de serviço.

**Request Body:**
```json
{
  "prestador_id": 1,
  "periodo": "01/11/2025 - 07/11/2025",
  "valor_total": 15480.50,
  "os_list": [
    {
      "os_numero": "OS001",
      "cliente": "Cliente A",
      "localidade": "São Paulo",
      "modalidade": "Instalação",
      "data_execucao": "2025-11-05",
      "valor": 500.00,
      "valor_extra": 50.00,
      "motivo_valor_extra": "Horário noturno"
    }
  ]
}
```

**Response:** `201 Created`

#### GET `/lotes/{id}`

Detalhes de um lote específico.

#### PUT `/lotes/{id}/status`

Atualiza o status de um lote.

**Request Body:**
```json
{
  "status": "Pago",
  "data_pagamento": "2025-11-20T14:30:00Z"
}
```

---

### 💰 Pagamentos

#### GET `/pagamentos/vencidos`

Lista pagamentos vencidos.

**Response:**
```json
{
  "data": [
    {
      "id": 5,
      "tipo": "prestador",
      "nome": "Serviços XYZ",
      "periodo": "15/10/2025 - 31/10/2025",
      "valor_total": 8500.00,
      "data_vencimento": "2025-11-10",
      "dias_atraso": 1,
      "lote_id": 5
    }
  ]
}
```

#### POST `/pagamentos/{lote_id}/marcar-pago`

Marca um lote como pago.

---

### 📄 Notas Fiscais

#### POST `/notas-fiscais/gerar-link`

Gera link de upload para nota fiscal.

**Request Body:**
```json
{
  "lote_id": 1,
  "tipo": "prestador"
}
```

**Response:**
```json
{
  "id_controle": 12345,
  "link_upload": "https://api.link.dev.br/upload/hash123",
  "validade_link": "2025-11-20",
  "upload_hash": "hash123"
}
```

#### GET `/notas-fiscais/consultar/{upload_hash}`

Consulta status de upload de NF.

**Response:**
```json
{
  "status_api": 1,
  "status_arquivo": 1,
  "nota_fiscal_path": "/downloads/nf_12345.pdf",
  "data_recebimento": "2025-11-15T10:00:00Z"
}
```

---

### 📊 Relatórios

#### POST `/relatorios/gerar-pdf`

Gera relatório PDF para prestador ou montador.

**Request Body:**
```json
{
  "tipo": "prestador",
  "lote_id": 1
}
```

**Response:** PDF file

---

### 📱 WhatsApp

#### POST `/whatsapp/enviar`

Envia mensagem via WhatsApp.

**Request Body:**
```json
{
  "numero": "5511987654321",
  "mensagem": "Olá! Seu relatório está disponível.",
  "media_path": "/path/to/pdf.pdf"
}
```

#### GET `/whatsapp/status`

Verifica status da conexão WhatsApp.

---

## ⚙️ Configuração do Ambiente

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Arquivo `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=braco_direito
DB_USER=postgres
DB_PASS=sua_senha

# API
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=sua_chave_secreta_jwt
DEBUG=True

# Email (Microsoft Graph)
CLIENT_ID=seu_client_id_azure
TENANT_ID=seu_tenant_id
AUTHORITY=https://login.microsoftonline.com/{TENANT_ID}

# API DV Processamento (Upload NF)
DV_API_URL=http://api.link.dev.br/dvprocessamento/
DV_API_KEY=<SUA_API_KEY_AQUI>

# WhatsApp
WHATSAPP_BASE_URL=http://localhost:3000

# Trello
TRELLO_API_KEY=sua_api_key
TRELLO_TOKEN=seu_token
TRELLO_BOARD_ID=id_do_board
TRELLO_LIST_ID=id_da_lista

# Jobs
SCHEDULER_ENABLED=True
```

### 3. Banco de Dados

```bash
# Criar banco
createdb braco_direito

# Executar migrations
python migrations/run_migrations.py
```

---

## 🚀 Guia de Implementação

### Estrutura Recomendada

#### 1. `app/main.py` (FastAPI)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import prestadores, montadores, lotes, dashboard
from app.database import init_db

app = FastAPI(title="Braço Direito API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # URL do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar banco
@app.on_event("startup")
async def startup():
    init_db()

# Rotas
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(prestadores.router, prefix="/api/v1/prestadores", tags=["Prestadores"])
app.include_router(montadores.router, prefix="/api/v1/montadores", tags=["Montadores"])
app.include_router(lotes.router, prefix="/api/v1/lotes", tags=["Lotes"])

@app.get("/")
def root():
    return {"message": "Braço Direito API v1.0"}
```

#### 2. `app/database.py`

```python
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from app.config import settings

@contextmanager
def get_db_connection():
    """Context manager para conexão com banco"""
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASS
    )
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Inicializa tabelas do banco"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        # Execute migrations aqui
        cur.execute("CREATE TABLE IF NOT EXISTS prestadores (...)")
        # ... demais tabelas
```

#### 3. `app/routes/prestadores.py`

```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.prestador import Prestador, PrestadorCreate
from app.database import get_db_connection
import psycopg2.extras

router = APIRouter()

@router.get("/", response_model=dict)
def listar_prestadores(
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """Lista prestadores com paginação e filtros"""
    offset = (page - 1) * limit
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query base
        query = "SELECT * FROM prestadores WHERE 1=1"
        params = []
        
        # Filtros
        if search:
            query += " AND nome ILIKE %s"
            params.append(f"%{search}%")
        
        if ativo is not None:
            query += " AND ativo = %s"
            params.append(ativo)
        
        # Count total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cur.execute(count_query, params)
        total = cur.fetchone()['count']
        
        # Query com paginação
        query += " ORDER BY nome ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        prestadores = cur.fetchall()
        
        return {
            "data": prestadores,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }

@router.post("/", status_code=201)
def criar_prestador(prestador: PrestadorCreate):
    """Cria novo prestador"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO prestadores 
                (nome, email, fornecedor_id, telefone, regra_envio, dias_envio, tempo_vencimento_dias, emails_adicionais)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    prestador.nome,
                    prestador.email,
                    prestador.fornecedor_id,
                    prestador.telefone,
                    prestador.regra_envio,
                    prestador.dias_envio,
                    prestador.tempo_vencimento_dias,
                    prestador.emails_adicionais
                )
            )
            prestador_id = cur.fetchone()[0]
            return {"id": prestador_id, "message": "Prestador criado com sucesso"}
        except psycopg2.IntegrityError as e:
            raise HTTPException(status_code=400, detail="Fornecedor ID ou Nome já existe")
```

#### 4. `app/models/prestador.py`

```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class PrestadorBase(BaseModel):
    nome: str
    email: EmailStr
    fornecedor_id: Optional[str] = None
    telefone: Optional[str] = None
    regra_envio: Optional[str] = None
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: int = 10
    emails_adicionais: Optional[str] = None

class PrestadorCreate(PrestadorBase):
    pass

class Prestador(PrestadorBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

---

## 🔐 Segurança

### JWT Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

def create_access_token(data: dict):
    """Cria token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica token JWT"""
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
```

### Uso nas Rotas

```python
@router.get("/", dependencies=[Depends(verify_token)])
def listar_prestadores():
    # Rota protegida
    pass
```

---

## 🔗 Integrações

### WhatsApp (whatsapp-web.js)

```python
import requests

class WhatsAppService:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def enviar_mensagem(self, numero: str, mensagem: str, media_path: str = None):
        """Envia mensagem via WhatsApp"""
        url = f"{self.base_url}/send"
        
        payload = {
            "number": numero,
            "message": mensagem
        }
        
        if media_path:
            payload["media_path"] = media_path
        
        response = requests.post(url, json=payload)
        return response.json()
```

### Trello

```python
import requests

class TrelloService:
    def __init__(self, api_key: str, token: str):
        self.api_key = api_key
        self.token = token
        self.base_url = "https://api.trello.com/1"
    
    def criar_card(self, list_id: str, nome: str, descricao: str):
        """Cria card no Trello"""
        url = f"{self.base_url}/cards"
        
        params = {
            "key": self.api_key,
            "token": self.token,
            "idList": list_id,
            "name": nome,
            "desc": descricao
        }
        
        response = requests.post(url, params=params)
        return response.json()
```

---

## 📝 Exemplo Completo: Frontend → Backend

### Frontend (React)

```typescript
// src/services/api.ts
const API_BASE_URL = "http://localhost:8000/api/v1";

export async function getPrestadores(search?: string) {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  
  const response = await fetch(`${API_BASE_URL}/prestadores?${params}`, {
    headers: {
      "Authorization": `Bearer ${localStorage.getItem("token")}`,
    },
  });
  
  if (!response.ok) throw new Error("Erro ao buscar prestadores");
  return response.json();
}

export async function createPrestador(data: PrestadorCreate) {
  const response = await fetch(`${API_BASE_URL}/prestadores`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${localStorage.getItem("token")}`,
    },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) throw new Error("Erro ao criar prestador");
  return response.json();
}
```

### Backend (FastAPI)

Já implementado nos exemplos acima.

---

## 🧪 Testes

```python
# tests/test_prestadores.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_listar_prestadores():
    response = client.get("/api/v1/prestadores")
    assert response.status_code == 200
    assert "data" in response.json()

def test_criar_prestador():
    data = {
        "nome": "Teste Prestador",
        "email": "teste@email.com",
        "fornecedor_id": "TEST123"
    }
    response = client.post("/api/v1/prestadores", json=data)
    assert response.status_code == 201
```

---

## 🚀 Deploy

### Produção (Docker)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=braco_direito
      - DB_USER=postgres
      - DB_PASS=postgres
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=braco_direito
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 📞 Suporte

Para dúvidas sobre a implementação, consulte:
- Documentação FastAPI: https://fastapi.tiangolo.com
- PostgreSQL: https://www.postgresql.org/docs/
- Python psycopg2: https://www.psycopg.org/docs/

---

**Versão:** 1.0.0  
**Data:** Novembro 2025  
**Sistema:** Braço Direito - Novo Mundo
