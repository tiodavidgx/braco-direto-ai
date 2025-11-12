# 🔧 Guia de Integração Backend - Braço Direito

Este documento é um **guia prático** para o desenvolvedor backend implementar todas as APIs necessárias para o frontend funcionar completamente.

---

## 📋 Checklist de Implementação

### ✅ Básico (Prioridade Alta)

- [ ] Conexão com PostgreSQL
- [ ] Estrutura de tabelas criadas
- [ ] CORS configurado
- [ ] Endpoints de Dashboard
- [ ] Endpoints de Prestadores (CRUD)
- [ ] Endpoints de Montadores (CRUD)

### 🔄 Funcionalidades Principais

- [ ] Endpoints de Pagamentos
- [ ] Sistema de Jobs Automáticos
- [ ] Integração WhatsApp
- [ ] Sistema de Automação
- [ ] Integração Trello

### 🚀 Avançado

- [ ] Autenticação JWT
- [ ] Upload de Notas Fiscais
- [ ] Geração de PDFs
- [ ] Sistema de Logs
- [ ] Testes Automatizados

---

## 🗄️ 1. Estrutura do Banco de Dados

### Script SQL Completo

Execute este script para criar todas as tabelas:

```sql
-- Prestadores
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

-- Montadores
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

-- Lotes de Serviço
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
    
    -- Upload NF
    id_controle INTEGER,
    link_upload TEXT,
    validade_link DATE,
    status_api INTEGER DEFAULT 0,
    data_envio_api TIMESTAMP,
    nota_fiscal_path TEXT,
    api_message TEXT,
    upload_hash TEXT,
    
    -- Pagamento
    data_recebimento_nf TIMESTAMP,
    data_vencimento_pagamento DATE,
    pago BOOLEAN DEFAULT FALSE,
    data_pagamento TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- OS Enviadas
CREATE TABLE os_enviadas (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes_servico(id) ON DELETE CASCADE,
    os_numero TEXT NOT NULL UNIQUE,
    detalhes JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Envios Montagem
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
    
    -- Upload NF
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
    
    -- Pagamento
    data_recebimento_nf TIMESTAMP,
    data_vencimento_pagamento DATE,
    pago BOOLEAN DEFAULT FALSE,
    data_pagamento TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Templates WhatsApp
CREATE TABLE templates_whatsapp (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    variaveis TEXT[],
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Automação WhatsApp
CREATE TABLE automacao_whatsapp (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    evento TEXT NOT NULL,
    tipo_destinatario TEXT NOT NULL,
    template_id INTEGER REFERENCES templates_whatsapp(id),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Integrações Config
CREATE TABLE integracoes_config (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL,
    config JSONB NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Jobs Config
CREATE TABLE jobs_config (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    intervalo_minutos INTEGER NOT NULL,
    ultima_execucao TIMESTAMP,
    proxima_execucao TIMESTAMP,
    total_execucoes INTEGER DEFAULT 0,
    total_erros INTEGER DEFAULT 0,
    ultima_mensagem TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para Performance
CREATE INDEX idx_prestadores_nome ON prestadores(nome);
CREATE INDEX idx_montadores_nome ON montadores(nome);
CREATE INDEX idx_lotes_prestador ON lotes_servico(prestador_id);
CREATE INDEX idx_lotes_status ON lotes_servico(status);
CREATE INDEX idx_envios_montador ON envios_montagem(montador_id);
CREATE INDEX idx_os_enviadas_lote ON os_enviadas(lote_id);
```

### Dados Iniciais (Seeds)

```sql
-- Inserir jobs padrão
INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos) VALUES
('envio_relatorios_prestadores', 'Envia relatórios semanais para prestadores', true, 10080),
('envio_relatorios_montadores', 'Envia relatórios quinzenais para montadores', true, 20160),
('consulta_status_nf', 'Consulta status das notas fiscais na API DV', true, 60),
('notificacao_pagamentos_proximos', 'Notifica pagamentos próximos do vencimento', true, 1440),
('limpeza_links_expirados', 'Remove links de upload expirados', true, 1440);

-- Inserir configuração Trello (desativada)
INSERT INTO integracoes_config (nome, tipo, config, ativo) VALUES
('trello', 'trello', '{"api_key": "", "token": "", "board_id": "", "list_id": "", "criacao_automatica_card": false}', false);
```

---

## 🔌 2. Implementação dos Endpoints

### Estrutura de Arquivos Recomendada

```
backend_example/
├── app/
│   ├── main.py                    # Entry point, registra rotas
│   ├── database.py                # Conexão PostgreSQL
│   ├── config.py                  # Configurações (.env)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py           # GET /dashboard/stats, /pendencias
│   │   ├── prestadores.py         # CRUD prestadores
│   │   ├── montadores.py          # CRUD montadores
│   │   ├── pagamentos.py          # Gestão de pagamentos
│   │   ├── whatsapp.py            # Integração WhatsApp
│   │   ├── automacao.py           # Templates e gatilhos
│   │   ├── integracoes.py         # Trello e outras
│   │   └── jobs.py                # Gerenciamento de jobs
│   └── services/
│       ├── whatsapp_service.py    # Lógica WhatsApp
│       ├── trello_service.py      # Lógica Trello
│       └── email_service.py       # Envio de emails
├── requirements.txt
├── .env
└── README.md
```

---

## 📡 3. Endpoints Obrigatórios

### Dashboard

```python
# backend_example/app/routes/dashboard.py

from fastapi import APIRouter
from ..database import get_db_connection

router = APIRouter()

@router.get("/stats")
def get_dashboard_stats():
    """Retorna estatísticas do dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Prestadores ativos
    cursor.execute("SELECT COUNT(*) FROM prestadores")
    prestadores_ativos = cursor.fetchone()[0]
    
    # Montadores ativos
    cursor.execute("SELECT COUNT(*) FROM montadores WHERE ativo = true")
    montadores_ativos = cursor.fetchone()[0]
    
    # Pagamentos pendentes (soma)
    cursor.execute("""
        SELECT COALESCE(SUM(valor_total), 0) 
        FROM lotes_servico 
        WHERE pago = false
    """)
    pagamentos_pendentes = cursor.fetchone()[0]
    
    # NFs aguardando
    cursor.execute("""
        SELECT COUNT(*) 
        FROM lotes_servico 
        WHERE status = 'Aguardando NF'
    """)
    nfs_aguardando = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return {
        "prestadores_ativos": prestadores_ativos,
        "montadores_ativos": montadores_ativos,
        "pagamentos_pendentes": float(pagamentos_pendentes),
        "nfs_aguardando": nfs_aguardando,
        "lotes_mes_atual": 0,  # Implementar
        "crescimento_mensal": 0.0  # Implementar
    }
```

### Prestadores (CRUD Completo)

```python
# backend_example/app/routes/prestadores.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db_connection

router = APIRouter()

class PrestadorCreate(BaseModel):
    nome: str
    email: str
    fornecedor_id: Optional[str] = None
    telefone: Optional[str] = None
    regra_envio: Optional[str] = None
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: int = 10
    emails_adicionais: Optional[str] = None

@router.get("")
def listar_prestadores(
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    page: int = 1,
    limit: int = 10
):
    """Lista prestadores com filtros"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * limit
    where_clauses = []
    params = []
    
    if search:
        where_clauses.append("nome ILIKE %s")
        params.append(f"%{search}%")
    
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Total
    cursor.execute(f"SELECT COUNT(*) FROM prestadores{where_sql}", params)
    total = cursor.fetchone()[0]
    
    # Dados
    cursor.execute(f"""
        SELECT id, nome, email, fornecedor_id, telefone, regra_envio, 
               dias_envio, tempo_vencimento_dias, emails_adicionais,
               created_at, updated_at
        FROM prestadores
        {where_sql}
        ORDER BY nome
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    
    prestadores = []
    for row in cursor.fetchall():
        prestadores.append({
            "id": row[0],
            "nome": row[1],
            "email": row[2],
            "fornecedor_id": row[3],
            "telefone": row[4],
            "regra_envio": row[5],
            "dias_envio": row[6],
            "tempo_vencimento_dias": row[7],
            "emails_adicionais": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None
        })
    
    cursor.close()
    conn.close()
    
    return {
        "data": prestadores,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.post("")
def criar_prestador(prestador: PrestadorCreate):
    """Cria novo prestador"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO prestadores 
            (nome, email, fornecedor_id, telefone, regra_envio, dias_envio, 
             tempo_vencimento_dias, emails_adicionais)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            prestador.nome,
            prestador.email,
            prestador.fornecedor_id,
            prestador.telefone,
            prestador.regra_envio,
            prestador.dias_envio,
            prestador.tempo_vencimento_dias,
            prestador.emails_adicionais
        ))
        
        prestador_id = cursor.fetchone()[0]
        conn.commit()
        
        return {"id": prestador_id, "message": "Prestador criado com sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/{id}")
def buscar_prestador(id: int):
    """Busca prestador por ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM prestadores WHERE id = %s", (id,))
    row = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Prestador não encontrado")
    
    return {
        "id": row[0],
        "nome": row[1],
        "email": row[2],
        # ... demais campos
    }

@router.put("/{id}")
def atualizar_prestador(id: int, prestador: PrestadorCreate):
    """Atualiza prestador"""
    # Implementar UPDATE
    pass

@router.delete("/{id}")
def deletar_prestador(id: int):
    """Remove prestador"""
    # Implementar DELETE
    pass
```

### Pagamentos

```python
# backend_example/app/routes/pagamentos.py

from fastapi import APIRouter
from ..database import get_db_connection

router = APIRouter()

@router.get("/pendentes")
def listar_pagamentos_pendentes():
    """Lista todos os pagamentos pendentes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lotes de serviço
    cursor.execute("""
        SELECT id, prestador_nome, periodo, valor_total, 
               data_vencimento_pagamento, pago
        FROM lotes_servico
        WHERE pago = false
        ORDER BY data_vencimento_pagamento
    """)
    
    servicos = []
    for row in cursor.fetchall():
        servicos.append({
            "id": row[0],
            "prestador_nome": row[1],
            "periodo": row[2],
            "valor_total": float(row[3]),
            "data_vencimento": row[4].isoformat() if row[4] else None,
            "pago": row[5]
        })
    
    # Montagens
    cursor.execute("""
        SELECT id, montador_nome, periodo, valor_total, 
               data_vencimento_pagamento, pago
        FROM envios_montagem
        WHERE pago = false
        ORDER BY data_vencimento_pagamento
    """)
    
    montagens = []
    for row in cursor.fetchall():
        montagens.append({
            "id": row[0],
            "montador_nome": row[1],
            "periodo": row[2],
            "valor_total": float(row[3]) if row[3] else 0,
            "data_vencimento": row[4].isoformat() if row[4] else None,
            "pago": row[5]
        })
    
    cursor.close()
    conn.close()
    
    return {
        "servicos": servicos,
        "montagens": montagens
    }

@router.post("/marcar-todos-nao-pendentes-pagos")
def marcar_todos_nao_pendentes_pagos():
    """Marca todos não pendentes como pagos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    from datetime import datetime
    agora = datetime.now()
    
    # Marcar lotes
    cursor.execute("""
        UPDATE lotes_servico 
        SET pago = true, data_pagamento = %s
        WHERE pago = false AND data_vencimento_pagamento < %s
    """, (agora, agora.date()))
    lotes = cursor.rowcount
    
    # Marcar montagens
    cursor.execute("""
        UPDATE envios_montagem 
        SET pago = true, data_pagamento = %s
        WHERE pago = false AND data_vencimento_pagamento < %s
    """, (agora, agora.date()))
    montagens = cursor.rowcount
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        "total": lotes + montagens,
        "lotes": lotes,
        "montagens": montagens
    }

@router.post("/lote/{id}/marcar-pago")
def marcar_lote_pago(id: int):
    """Marca lote como pago"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    from datetime import datetime
    cursor.execute("""
        UPDATE lotes_servico 
        SET pago = true, data_pagamento = %s
        WHERE id = %s
    """, (datetime.now(), id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"message": "Lote marcado como pago"}
```

---

## 🔧 4. Frontend Services

### Como o Frontend Chama a API

Todos os serviços frontend usam a mesma estrutura:

```typescript
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export class APIClient {
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return response.json();
  }
  
  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return response.json();
  }
  
  // ... put, delete similares
}

export const apiClient = new APIClient();
```

### Serviços Implementados no Frontend

1. **`src/services/dashboard.service.ts`**
   - `getStats()` → `GET /dashboard/stats`
   - `getPendencias()` → `GET /dashboard/pendencias`

2. **`src/services/prestadores.service.ts`**
   - `getAll(filters)` → `GET /prestadores`
   - `getById(id)` → `GET /prestadores/{id}`
   - `create(data)` → `POST /prestadores`
   - `update(id, data)` → `PUT /prestadores/{id}`
   - `delete(id)` → `DELETE /prestadores/{id}`

3. **`src/services/montadores.service.ts`**
   - Similar ao prestadores

4. **`src/services/pagamentos.service.ts`**
   - `getTodosPagamentosPendentes()` → `GET /pagamentos/pendentes`
   - `marcarTodosNaoPendentesPagos()` → `POST /pagamentos/marcar-todos-nao-pendentes-pagos`
   - `marcarLoteComoPago(id)` → `POST /pagamentos/lote/{id}/marcar-pago`

5. **`src/services/whatsapp.service.ts`**
   - `getStatus()` → `GET /whatsapp/status`
   - `sendMessage(numero, mensagem)` → `POST /whatsapp/send`
   - `sendBulk(destinatarios, mensagem, delay)` → `POST /whatsapp/send-bulk`

6. **`src/services/automacao.service.ts`**
   - `getTemplates()` → `GET /automacao/templates`
   - `createTemplate(data)` → `POST /automacao/templates`
   - `getTriggers()` → `GET /automacao/triggers`

7. **`src/services/integracoes.service.ts`**
   - `getTrelloConfig()` → `GET /integracoes/trello/config`
   - `updateTrelloConfig(data)` → `POST /integracoes/trello/config`
   - `testTrelloConnection()` → `POST /integracoes/trello/test`

8. **`src/services/jobs.service.ts`**
   - `getStatus()` → `GET /jobs/status`
   - `startService()` → `POST /jobs/start`
   - `getJobs()` → `GET /jobs/config`
   - `updateJob(name, data)` → `PUT /jobs/config/{name}`

---

## 🚀 5. Como Testar a Integração

### 1. Iniciar Backend

```bash
cd backend_example
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Verificar Endpoints

```bash
# Dashboard
curl http://localhost:8000/api/v1/dashboard/stats

# Prestadores
curl http://localhost:8000/api/v1/prestadores

# WhatsApp Status
curl http://localhost:8000/api/v1/whatsapp/status

# Jobs
curl http://localhost:8000/api/v1/jobs/config
```

### 3. Testar no Frontend

Abra o navegador em `http://localhost:8080` e:
- Dashboard deve mostrar estatísticas
- Prestadores/Montadores devem carregar listas
- Pagamentos Vencidos deve listar
- WhatsApp deve mostrar status
- Jobs deve listar configurações

### 4. Ver Logs de Requisições

No console do navegador (F12), aba Network, veja:
- Status HTTP (200, 201, 404, 500)
- Payloads enviados e recebidos
- Erros de CORS

---

## ⚠️ Problemas Comuns

### CORS Error

**Problema:** `Access-Control-Allow-Origin`

**Solução:**
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Conexão com Banco

**Problema:** `psycopg2.OperationalError`

**Solução:**
```python
# Verificar .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=braco_direito
DB_USER=postgres
DB_PASS=sua_senha

# Testar conexão
psql -U postgres -d braco_direito
```

### Frontend não carrega dados

**Problema:** Endpoints retornam vazio

**Solução:**
```bash
# 1. Verificar se backend está rodando
lsof -i :8000

# 2. Verificar .env.local do frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1

# 3. Verificar logs do backend
# Deve mostrar requisições chegando
```

---

## 📞 Contato

Dúvidas sobre integração? 
- 📧 Email: ti@novomundo.com.br
- 📖 Docs: API_DOCUMENTATION.md

---

**Braço Direito** - Guia de Integração v1.0 🤝
