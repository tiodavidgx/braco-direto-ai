# 🎯 Documento de Handoff - Braço Direito

## Para o Desenvolvedor Backend

Olá! Este documento contém tudo que você precisa para conectar o backend Python ao novo frontend React.

---

## 📦 O Que Foi Feito

### ✅ Frontend React (100% Completo)

Desenvolvido um frontend moderno e profissional com:

- **10 páginas completas:**
  1. Dashboard (estatísticas e pendências)
  2. Prestadores (CRUD completo)
  3. Montadores (CRUD completo)
  4. Pagamentos Vencidos (gestão de pagamentos)
  5. WhatsApp (envio individual, por lista, em massa)
  6. Automação (templates e gatilhos)
  7. Integrações (Trello e futuras)
  8. Jobs Automáticos (gerenciamento de tarefas agendadas)
  9. Envio de Relatórios (interface pronta)
  10. Histórico de Envios (interface pronta)

- **8 serviços de API (`src/services/`):**
  - `api.ts` - Cliente HTTP base
  - `dashboard.service.ts`
  - `prestadores.service.ts`
  - `montadores.service.ts`
  - `pagamentos.service.ts`
  - `whatsapp.service.ts`
  - `automacao.service.ts`
  - `integracoes.service.ts`
  - `jobs.service.ts`

- **Design system completo:**
  - Google Material Design
  - Componentes Shadcn/ui
  - Responsivo e acessível
  - Dark mode

---

## 🎯 O Que Você Precisa Fazer

### 1️⃣ Criar Estrutura do Banco (30min)

Execute o script SQL completo que está em **`INTEGRATION_GUIDE.md`** seção "Estrutura do Banco".

Cria 9 tabelas:
- `prestadores`
- `montadores`
- `lotes_servico`
- `os_enviadas`
- `envios_montagem`
- `templates_whatsapp`
- `automacao_whatsapp`
- `integracoes_config`
- `jobs_config`

### 2️⃣ Implementar Backend FastAPI (4-6 horas)

Já existe uma estrutura base em `backend_example/`. Você precisa:

1. **Configurar `.env`** (copiar de `.env.example`)
2. **Implementar rotas** (exemplos prontos no guia):
   - `app/routes/dashboard.py` → Estatísticas e pendências
   - `app/routes/prestadores.py` → CRUD prestadores
   - `app/routes/montadores.py` → CRUD montadores
   - `app/routes/pagamentos.py` → Gestão de pagamentos
   - `app/routes/whatsapp.py` → Integração WhatsApp
   - `app/routes/automacao.py` → Templates e gatilhos
   - `app/routes/integracoes.py` → Trello
   - `app/routes/jobs.py` → Gerenciamento de jobs

3. **Registrar rotas em `app/main.py`**
4. **Configurar CORS** para aceitar frontend

### 3️⃣ Testar Integração (1 hora)

1. Iniciar backend: `uvicorn app.main:app --reload`
2. Iniciar frontend: `npm run dev`
3. Testar todas as páginas no navegador
4. Verificar console (F12) para erros

---

## 📚 Documentação Disponível

### 🔥 Documento Principal (COMECE AQUI!)

**`INTEGRATION_GUIDE.md`** - Guia completo de integração
- ✅ Checklist de implementação
- ✅ Scripts SQL prontos
- ✅ Código Python de exemplo para TODOS os endpoints
- ✅ Como testar
- ✅ Solução de problemas comuns

### 📡 Referência da API

**`API_DOCUMENTATION.md`** - Documentação completa de endpoints
- Todos os endpoints documentados
- Request/Response examples
- Códigos de status
- Como usar cURL e Swagger

### 📖 Documentação Técnica

**`BACKEND_DOCUMENTATION.md`** - Arquitetura e detalhes técnicos
- Estrutura do sistema
- Integrações externas (WhatsApp, Trello, Email)
- Modelos de dados

**`FRONTEND_BACKEND_INTEGRATION.md`** - Como funciona a integração
- Camada de serviços do frontend
- Autenticação JWT (futuro)
- React Query hooks

**`QUICKSTART.md`** - Guia rápido
- Como rodar tudo em 5 minutos
- Comandos básicos

---

## 🔌 Como o Frontend Chama o Backend

### Configuração

O frontend está configurado para chamar:

```
Base URL: http://localhost:8000/api/v1
```

Configurado em `.env.local`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Exemplo de Chamada

```typescript
// Frontend (src/services/prestadores.service.ts)
export const prestadoresService = {
  async getAll(filters?: PrestadoresFilters) {
    return apiClient.get<PrestadoresResponse>('/prestadores', filters);
  }
}
```

Isso chama:
```
GET http://localhost:8000/api/v1/prestadores?search=...&page=1&limit=10
```

### O Backend Deve Responder

```python
# Backend (app/routes/prestadores.py)
@router.get("")
def listar_prestadores(search: Optional[str] = None, page: int = 1, limit: int = 10):
    # ... sua lógica aqui
    return {
        "data": [...],
        "total": 100,
        "page": 1,
        "pages": 10
    }
```

---

## 🎨 Estrutura de Arquivos

### Frontend (React)

```
src/
├── pages/                    # 10 páginas completas
│   ├── Dashboard.tsx
│   ├── Prestadores.tsx
│   ├── Montadores.tsx
│   ├── PagamentosVencidos.tsx
│   ├── WhatsApp.tsx
│   ├── Automacao.tsx
│   ├── Integracoes.tsx
│   ├── Jobs.tsx
│   ├── EnvioRelatorios.tsx
│   └── HistoricoEnvios.tsx
│
├── services/                 # Comunicação com API
│   ├── api.ts               # ⭐ Cliente HTTP base
│   ├── dashboard.service.ts
│   ├── prestadores.service.ts
│   ├── montadores.service.ts
│   ├── pagamentos.service.ts
│   ├── whatsapp.service.ts
│   ├── automacao.service.ts
│   ├── integracoes.service.ts
│   └── jobs.service.ts
│
├── types/                    # TypeScript types
│   ├── prestador.ts
│   ├── montador.ts
│   └── pagamento.ts
│
└── components/              # Componentes reutilizáveis
    ├── ui/                 # Shadcn components
    ├── AppSidebar.tsx
    └── StatCard.tsx
```

### Backend (Python) - A IMPLEMENTAR

```
backend_example/
├── app/
│   ├── main.py              # ⭐ Entry point (registrar rotas aqui)
│   ├── database.py          # ⭐ Conexão PostgreSQL
│   ├── config.py            # Configurações do .env
│   │
│   └── routes/              # ⭐ Endpoints (implementar aqui)
│       ├── dashboard.py     # GET /stats, /pendencias
│       ├── prestadores.py   # CRUD prestadores
│       ├── montadores.py    # CRUD montadores
│       ├── pagamentos.py    # GET /pendentes, POST /marcar-pago
│       ├── whatsapp.py      # GET /status, POST /send
│       ├── automacao.py     # Templates e triggers
│       ├── integracoes.py   # Trello config
│       └── jobs.py          # Gerenciamento jobs
│
├── requirements.txt         # Dependências Python
├── .env                     # ⭐ Configurações (copiar de .env.example)
└── README.md
```

---

## ✅ Checklist de Implementação

### Fase 1: Setup Básico (1 hora)

- [ ] Criar banco de dados PostgreSQL: `createdb braco_direito`
- [ ] Executar script SQL (INTEGRATION_GUIDE.md)
- [ ] Configurar `.env` no backend
- [ ] Instalar dependências: `pip install -r requirements.txt`
- [ ] Testar conexão com banco

### Fase 2: Endpoints Essenciais (3 horas)

- [ ] Implementar `dashboard.py`
  - [ ] GET `/dashboard/stats`
  - [ ] GET `/dashboard/pendencias`
- [ ] Implementar `prestadores.py`
  - [ ] GET `/prestadores` (com filtros)
  - [ ] GET `/prestadores/{id}`
  - [ ] POST `/prestadores`
  - [ ] PUT `/prestadores/{id}`
  - [ ] DELETE `/prestadores/{id}`
- [ ] Implementar `montadores.py` (igual prestadores)
- [ ] Implementar `pagamentos.py`
  - [ ] GET `/pagamentos/pendentes`
  - [ ] POST `/pagamentos/marcar-todos-nao-pendentes-pagos`
  - [ ] POST `/pagamentos/lote/{id}/marcar-pago`

### Fase 3: Funcionalidades Avançadas (2-3 horas)

- [ ] Implementar `whatsapp.py`
  - [ ] GET `/whatsapp/status`
  - [ ] POST `/whatsapp/send`
  - [ ] POST `/whatsapp/send-bulk`
- [ ] Implementar `automacao.py`
  - [ ] CRUD templates
  - [ ] CRUD triggers
- [ ] Implementar `integracoes.py`
  - [ ] GET/POST `/integracoes/trello/config`
  - [ ] POST `/integracoes/trello/test`
- [ ] Implementar `jobs.py`
  - [ ] GET `/jobs/status`
  - [ ] POST `/jobs/start`, `/jobs/stop`
  - [ ] GET `/jobs/config`
  - [ ] PUT `/jobs/config/{name}`

### Fase 4: Testes (1 hora)

- [ ] Testar todos os endpoints com cURL
- [ ] Verificar Swagger docs: `http://localhost:8000/docs`
- [ ] Testar integração com frontend
- [ ] Verificar logs de erro
- [ ] Confirmar CORS funcionando

---

## 🐛 Problemas Comuns e Soluções

### ❌ CORS Error no Frontend

**Erro:** `Access-Control-Allow-Origin`

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

### ❌ Banco de Dados não Conecta

**Erro:** `psycopg2.OperationalError: could not connect`

**Solução:**
1. Verificar PostgreSQL rodando: `pg_isready`
2. Verificar credenciais no `.env`
3. Testar manualmente: `psql -U postgres -d braco_direito`

### ❌ Frontend Não Recebe Dados

**Erro:** Páginas carregam vazias

**Solução:**
1. Abrir console (F12) → aba Network
2. Ver se requisições chegam (devem aparecer)
3. Ver status HTTP (200 = OK, 404/500 = erro)
4. Verificar formato da resposta (deve ser JSON)

### ❌ Endpoint Retorna 404

**Erro:** `404 Not Found`

**Solução:**
1. Verificar rota registrada em `app/main.py`:
```python
app.include_router(prestadores.router, prefix="/api/v1/prestadores", tags=["Prestadores"])
```
2. URL deve ser: `http://localhost:8000/api/v1/prestadores` (com `/api/v1`)

---

## 🚀 Como Rodar Tudo

### Terminal 1: Backend

```bash
cd backend_example
source venv/bin/activate  # Mac/Linux
# ou venv\Scripts\activate  # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend em: http://localhost:8000
✅ Docs em: http://localhost:8000/docs

### Terminal 2: Frontend

```bash
npm run dev
```

✅ Frontend em: http://localhost:8080

### Testar

1. Abrir http://localhost:8080
2. Navegar pelas páginas
3. Ver console (F12) para erros
4. Testar funcionalidades

---

## 📊 Endpoints que o Frontend Chama

### Dashboard
- `GET /dashboard/stats` → Estatísticas
- `GET /dashboard/pendencias` → Pendências do dia

### Prestadores
- `GET /prestadores` → Listar (com filtros)
- `GET /prestadores/{id}` → Buscar um
- `POST /prestadores` → Criar
- `PUT /prestadores/{id}` → Atualizar
- `DELETE /prestadores/{id}` → Deletar

### Montadores
- Mesmos endpoints dos prestadores

### Pagamentos
- `GET /pagamentos/pendentes` → Todos pendentes
- `POST /pagamentos/marcar-todos-nao-pendentes-pagos` → Marcar múltiplos
- `POST /pagamentos/lote/{id}/marcar-pago` → Marcar lote
- `POST /pagamentos/montagem/{id}/marcar-pago` → Marcar montagem

### WhatsApp
- `GET /whatsapp/status` → Status conexão
- `GET /whatsapp/info` → Info detalhada
- `POST /whatsapp/send` → Enviar mensagem
- `POST /whatsapp/send-bulk` → Enviar em massa

### Automação
- `GET /automacao/templates` → Listar templates
- `POST /automacao/templates` → Criar template
- `PUT /automacao/templates/{id}` → Atualizar template
- `DELETE /automacao/templates/{id}` → Deletar template
- `GET /automacao/triggers` → Listar gatilhos
- `POST /automacao/triggers` → Criar gatilho

### Integrações
- `GET /integracoes/trello/config` → Config Trello
- `POST /integracoes/trello/config` → Atualizar config
- `POST /integracoes/trello/test` → Testar conexão

### Jobs
- `GET /jobs/status` → Status serviço
- `POST /jobs/start` → Iniciar serviço
- `POST /jobs/stop` → Parar serviço
- `POST /jobs/reload` → Recarregar config
- `GET /jobs/config` → Listar jobs
- `PUT /jobs/config/{name}` → Atualizar job
- `GET /jobs/logs` → Ver logs

---

## 💡 Dicas Importantes

### 1. Use os Exemplos Prontos

O arquivo `INTEGRATION_GUIDE.md` tem código Python pronto para copiar e adaptar.

### 2. Teste Endpoint por Endpoint

Não implemente tudo de uma vez. Teste cada endpoint conforme implementa:

```bash
curl http://localhost:8000/api/v1/prestadores
```

### 3. Use o Swagger

FastAPI gera docs automáticas: `http://localhost:8000/docs`

Você pode testar todos os endpoints direto no navegador!

### 4. Veja os Services do Frontend

Os arquivos em `src/services/` mostram exatamente como o frontend chama cada endpoint.

### 5. Formato das Respostas

O frontend espera respostas específicas. Veja exemplos em `API_DOCUMENTATION.md`.

---

## 📞 Suporte

Dúvidas? Consulte os documentos:

1. **INTEGRATION_GUIDE.md** → Como implementar (com código)
2. **API_DOCUMENTATION.md** → Referência de endpoints
3. **BACKEND_DOCUMENTATION.md** → Arquitetura e integrações

---

## 🎉 Resumo

**O QUE ESTÁ PRONTO:**
- ✅ Frontend 100% completo (10 páginas)
- ✅ Services prontos para chamar API
- ✅ Design system completo
- ✅ Documentação detalhada

**O QUE VOCÊ PRECISA FAZER:**
1. Executar script SQL (cria estrutura do banco)
2. Implementar endpoints FastAPI (código de exemplo pronto)
3. Testar integração
4. 🚀 Deploy!

**TEMPO ESTIMADO:** 6-8 horas para implementação completa

---

**Boa sorte! 🤝**

Se precisar de ajuda, consulte os documentos ou entre em contato.

Desenvolvido com ❤️ pela equipe de TI da Novo Mundo.
