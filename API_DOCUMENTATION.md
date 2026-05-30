# 📡 Documentação Completa da API - Braço Direito

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Configuração](#configuração)
3. [Autenticação](#autenticação)
4. [Endpoints](#endpoints)
   - [Dashboard](#dashboard)
   - [Prestadores](#prestadores)
   - [Montadores](#montadores)
   - [Pagamentos](#pagamentos)
   - [WhatsApp](#whatsapp)
   - [Automação](#automação)
   - [Integrações](#integrações)
   - [Jobs](#jobs)
5. [Códigos de Status](#códigos-de-status)
6. [Tratamento de Erros](#tratamento-de-erros)

---

## 🎯 Visão Geral

API REST desenvolvida com **FastAPI** para o sistema Braço Direito.

### Base URL

```
http://localhost:8000/api/v1
```

### Formato de Resposta

Todas as respostas são em JSON:

```json
{
  "data": [...],
  "message": "Sucesso",
  "status": 200
}
```

---

## ⚙️ Configuração

### Backend (.env)

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
SECRET_KEY=sua_chave_secreta_jwt_complexa
DEBUG=True

# CORS
FRONTEND_URL=http://localhost:8080

# WhatsApp
WHATSAPP_BASE_URL=http://localhost:3000

# Trello
TRELLO_API_KEY=sua_trello_api_key
TRELLO_TOKEN=seu_trello_token
TRELLO_BOARD_ID=id_do_board
TRELLO_LIST_ID=id_da_lista

# Email
CLIENT_ID=seu_client_id_azure
TENANT_ID=seu_tenant_id

# API DV
DV_API_URL=http://api.link.dev.br/dvprocessamento/
DV_API_KEY=<SUA_API_KEY_AQUI>
```

### Frontend (.env.local)

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 🔐 Autenticação

### JWT Token

```http
Authorization: Bearer <token>
```

### Obter Token (Futuro)

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "usuario@email.com",
  "password": "senha123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 📡 Endpoints

### 📊 Dashboard

#### GET `/dashboard/stats`

Estatísticas gerais do sistema.

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

Lista pendências do dia.

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
- `search` (string, opcional): Filtro por nome
- `ativo` (boolean, opcional): Filtrar ativos/inativos
- `page` (number, opcional): Página (default: 1)
- `limit` (number, opcional): Itens por página (default: 10)

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
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 24,
  "page": 1,
  "pages": 3
}
```

#### GET `/prestadores/{id}`

Busca um prestador por ID.

**Response:**
```json
{
  "id": 1,
  "nome": "Prestadora ABC Ltda",
  "email": "contato@abc.com",
  "fornecedor_id": "FOR123",
  "telefone": "(11) 98765-4321",
  "regra_envio": "Semanal",
  "dias_envio": "Segunda-feira",
  "tempo_vencimento_dias": 10,
  "emails_adicionais": "financeiro@abc.com"
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
  "message": "Prestador criado com sucesso"
}
```

#### PUT `/prestadores/{id}`

Atualiza um prestador.

**Request Body:**
```json
{
  "nome": "Prestadora Atualizada",
  "email": "novo@email.com"
}
```

**Response:** `200 OK`

#### DELETE `/prestadores/{id}`

Remove um prestador.

**Response:** `204 No Content`

---

### 🔧 Montadores

#### GET `/montadores`

Lista todos os montadores.

**Query Parameters:**
- `search` (string, opcional)
- `ativo` (boolean, opcional)
- `page` (number, opcional)
- `limit` (number, opcional)

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
      "dias_envio": "1, 15",
      "tempo_vencimento_dias": 10,
      "emails_adicionais": "financeiro@montador.com"
    }
  ],
  "total": 18,
  "page": 1,
  "pages": 2
}
```

#### GET `/montadores/{id}`

Busca um montador por ID.

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

### 💰 Pagamentos

#### GET `/pagamentos/pendentes`

Lista todos os pagamentos pendentes (lotes e montagens).

**Response:**
```json
{
  "servicos": [
    {
      "id": 1,
      "prestador_nome": "Prestadora ABC",
      "periodo": "01/11/2025 - 07/11/2025",
      "valor_total": 15480.50,
      "data_vencimento": "2025-11-25",
      "dias_ate_vencimento": 10,
      "pago": false
    }
  ],
  "montagens": [
    {
      "id": 1,
      "montador_nome": "João Silva",
      "periodo": "Novembro/2025",
      "valor_total": 2500.00,
      "data_vencimento": "2025-11-30",
      "dias_ate_vencimento": 15,
      "pago": false
    }
  ]
}
```

#### POST `/pagamentos/marcar-todos-nao-pendentes-pagos`

Marca todos os pagamentos não pendentes como pagos.

**Response:**
```json
{
  "total": 25,
  "lotes": 15,
  "montagens": 10
}
```

#### POST `/pagamentos/desmarcar-todos-pagos`

Desmarca todos os pagamentos como não pagos.

**Response:**
```json
{
  "total": 25,
  "lotes": 15,
  "montagens": 10
}
```

#### POST `/pagamentos/lote/{id}/marcar-pago`

Marca um lote específico como pago.

**Response:**
```json
{
  "message": "Lote marcado como pago",
  "id": 1
}
```

#### POST `/pagamentos/montagem/{id}/marcar-pago`

Marca uma montagem específica como paga.

**Response:**
```json
{
  "message": "Montagem marcada como paga",
  "id": 1
}
```

---

### 📱 WhatsApp

#### GET `/whatsapp/status`

Verifica o status da conexão WhatsApp.

**Response:**
```json
{
  "connected": true,
  "phone": "+55 11 98765-4321",
  "battery": 85
}
```

#### GET `/whatsapp/info`

Informações detalhadas do WhatsApp.

**Response:**
```json
{
  "connected": true,
  "phone": "+55 11 98765-4321",
  "platform": "Android",
  "battery": 85,
  "plugged": true
}
```

#### POST `/whatsapp/send`

Envia uma mensagem individual.

**Request Body:**
```json
{
  "numero": "5511987654321",
  "mensagem": "Olá! Esta é uma mensagem de teste."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Mensagem enviada com sucesso"
}
```

#### POST `/whatsapp/send-bulk`

Envia mensagens em massa.

**Request Body:**
```json
{
  "destinatarios": [
    {
      "numero": "5511987654321",
      "nome": "João Silva"
    },
    {
      "numero": "5511987654322",
      "nome": "Maria Santos"
    }
  ],
  "mensagem": "Olá {nome}! Esta é uma mensagem personalizada.",
  "delay_segundos": 3
}
```

**Response:**
```json
{
  "total": 2,
  "sucesso": 2,
  "falhas": 0,
  "detalhes": [
    {
      "numero": "5511987654321",
      "nome": "João Silva",
      "sucesso": true
    },
    {
      "numero": "5511987654322",
      "nome": "Maria Santos",
      "sucesso": true
    }
  ]
}
```

---

### 🤖 Automação

#### GET `/automacao/templates`

Lista todos os templates de mensagens.

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "nome": "Envio Relatório Prestador",
      "tipo": "prestador",
      "mensagem": "Olá {nome}! Seu relatório está pronto.",
      "variaveis": ["nome", "periodo", "valor"],
      "ativo": true,
      "created_at": "2025-11-01T10:00:00Z"
    }
  ]
}
```

#### POST `/automacao/templates`

Cria um novo template.

**Request Body:**
```json
{
  "nome": "Novo Template",
  "tipo": "prestador",
  "mensagem": "Olá {nome}! Aqui está seu relatório do período {periodo}.",
  "variaveis": ["nome", "periodo"],
  "ativo": true
}
```

**Response:** `201 Created`

#### PUT `/automacao/templates/{id}`

Atualiza um template.

**Request Body:**
```json
{
  "nome": "Template Atualizado",
  "mensagem": "Nova mensagem {nome}",
  "ativo": false
}
```

**Response:** `200 OK`

#### DELETE `/automacao/templates/{id}`

Remove um template.

**Response:** `204 No Content`

#### GET `/automacao/triggers`

Lista todos os gatilhos automáticos.

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "nome": "Notificar Email Enviado",
      "evento": "email_enviado",
      "tipo_destinatario": "prestador",
      "template_id": 1,
      "ativo": true,
      "created_at": "2025-11-01T10:00:00Z"
    }
  ]
}
```

#### POST `/automacao/triggers`

Cria um novo gatilho.

**Request Body:**
```json
{
  "nome": "Notificar NF Recebida",
  "evento": "nf_recebida",
  "tipo_destinatario": "prestador",
  "template_id": 2,
  "ativo": true
}
```

**Response:** `201 Created`

---

### 🔗 Integrações

#### GET `/integracoes/trello/config`

Obtém configuração do Trello.

**Response:**
```json
{
  "api_key": "sua_trello_api_key",
  "token": "seu_trello_token",
  "board_id": "id_do_board",
  "list_id": "id_da_lista",
  "ativo": true,
  "criacao_automatica_card": true
}
```

#### POST `/integracoes/trello/config`

Atualiza configuração do Trello.

**Request Body:**
```json
{
  "api_key": "nova_api_key",
  "token": "novo_token",
  "board_id": "novo_board_id",
  "list_id": "nova_list_id",
  "ativo": true,
  "criacao_automatica_card": true
}
```

**Response:**
```json
{
  "message": "Configuração atualizada com sucesso"
}
```

#### POST `/integracoes/trello/test`

Testa a conexão com Trello.

**Response:**
```json
{
  "success": true,
  "message": "Conexão com Trello OK",
  "board_name": "Meu Board Trello"
}
```

---

### ⏰ Jobs

#### GET `/jobs/status`

Verifica status do serviço de jobs.

**Response:**
```json
{
  "running": true,
  "pid": 12345
}
```

#### POST `/jobs/start`

Inicia o serviço de jobs.

**Response:**
```json
{
  "message": "Serviço iniciado",
  "pid": 12345
}
```

#### POST `/jobs/stop`

Para o serviço de jobs.

**Response:**
```json
{
  "message": "Serviço parado"
}
```

#### POST `/jobs/reload`

Recarrega configurações do serviço.

**Response:**
```json
{
  "message": "Configurações recarregadas"
}
```

#### GET `/jobs/config`

Lista configurações de todos os jobs.

**Response:**
```json
[
  {
    "id": 1,
    "nome": "envio_relatorios_prestadores",
    "descricao": "Envia relatórios semanais para prestadores",
    "ativo": true,
    "intervalo_minutos": 1440,
    "ultima_execucao": "2025-11-11T10:30:00Z",
    "proxima_execucao": "2025-11-12T10:30:00Z",
    "total_execucoes": 45,
    "total_erros": 2,
    "ultima_mensagem": "Executado com sucesso"
  }
]
```

#### PUT `/jobs/config/{job_name}`

Atualiza configuração de um job.

**Request Body:**
```json
{
  "ativo": true,
  "intervalo_minutos": 2880
}
```

**Response:**
```json
{
  "message": "Configuração atualizada"
}
```

#### GET `/jobs/logs`

Retorna logs recentes do scheduler.

**Response:**
```json
{
  "logs": "[2025-11-11 10:30:00] Iniciando job: envio_relatorios_prestadores\n[2025-11-11 10:30:05] Job concluído com sucesso\n..."
}
```

---

## 📊 Códigos de Status

| Código | Significado |
|--------|-------------|
| 200 | OK - Sucesso |
| 201 | Created - Recurso criado |
| 204 | No Content - Sucesso sem retorno |
| 400 | Bad Request - Requisição inválida |
| 401 | Unauthorized - Não autenticado |
| 403 | Forbidden - Sem permissão |
| 404 | Not Found - Recurso não encontrado |
| 422 | Unprocessable Entity - Validação falhou |
| 500 | Internal Server Error - Erro no servidor |

---

## ⚠️ Tratamento de Erros

### Formato de Erro

```json
{
  "detail": "Mensagem de erro descritiva",
  "status": 400,
  "errors": {
    "campo": ["Mensagem de validação"]
  }
}
```

### Exemplos de Erros

#### Validação

```json
{
  "detail": "Erro de validação",
  "status": 422,
  "errors": {
    "email": ["Email inválido"],
    "nome": ["Campo obrigatório"]
  }
}
```

#### Recurso Não Encontrado

```json
{
  "detail": "Prestador não encontrado",
  "status": 404
}
```

#### Autenticação

```json
{
  "detail": "Token inválido ou expirado",
  "status": 401
}
```

---

## 🧪 Testando a API

### Com cURL

```bash
# Listar prestadores
curl http://localhost:8000/api/v1/prestadores

# Criar prestador
curl -X POST http://localhost:8000/api/v1/prestadores \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Novo Prestador",
    "email": "novo@email.com"
  }'

# Verificar status WhatsApp
curl http://localhost:8000/api/v1/whatsapp/status

# Listar jobs
curl http://localhost:8000/api/v1/jobs/config
```

### Com Swagger UI

Acesse: `http://localhost:8000/docs`

### Com ReDoc

Acesse: `http://localhost:8000/redoc`

---

## 📦 Estrutura das Tabelas do Banco

### `prestadores`
- id, nome, email, fornecedor_id, telefone
- regra_envio, dias_envio, emails_adicionais
- tempo_vencimento_dias, created_at, updated_at

### `montadores`
- id, nome, identificador, email, telefone
- percentual_comissao, auxilio_semanal, ativo
- fornecedor_id, regra_envio, dias_envio
- tempo_vencimento_dias, emails_adicionais
- created_at, updated_at

### `lotes_servico`
- id, prestador_id, prestador_nome, periodo
- valor_total, data_envio, status
- id_controle, link_upload, validade_link
- data_recebimento_nf, data_vencimento_pagamento
- pago, data_pagamento

### `envios_montagem`
- id, montador_id, montador_nome, periodo
- data_envio, status, quantidade_os, valor_total
- data_recebimento_nf, data_vencimento_pagamento
- pago, data_pagamento

### `templates_whatsapp`
- id, nome, tipo, mensagem, variaveis
- ativo, created_at, updated_at

### `automacao_whatsapp`
- id, nome, evento, tipo_destinatario
- template_id, ativo, created_at

### `integracoes_config`
- id, nome, tipo, config (JSONB)
- ativo, created_at, updated_at

### `jobs_config`
- id, nome, descricao, ativo
- intervalo_minutos, ultima_execucao
- proxima_execucao, total_execucoes
- total_erros, ultima_mensagem

---

## 🚀 Deploy

### Produção

```bash
# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Usar Gunicorn (recomendado)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📞 Suporte

- **Documentação Backend**: BACKEND_DOCUMENTATION.md
- **Integração**: FRONTEND_BACKEND_INTEGRATION.md
- **Guia Rápido**: QUICKSTART.md
- **Email**: ti@novomundo.com.br

---

**Braço Direito API** - Documentação v1.0 🤝
