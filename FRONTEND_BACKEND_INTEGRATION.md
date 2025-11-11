# 🔗 Integração Frontend-Backend - Braço Direito

Este documento explica como conectar o frontend React (interface moderna) ao backend Python (FastAPI).

---

## 📋 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Interface Moderna (Vite + React + TypeScript)       │   │
│  │  - Dashboard                                         │   │
│  │  - Gestão de Prestadores                            │   │
│  │  - Gestão de Montadores                             │   │
│  │  - Controle Financeiro                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Client Layer (src/services/api.ts)             │   │
│  │  - HTTP Requests (fetch/axios)                      │   │
│  │  - Authentication (JWT)                             │   │
│  │  - Error Handling                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (Python)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                │   │
│  │  - RESTful API Endpoints                            │   │
│  │  - JWT Authentication                               │   │
│  │  - Business Logic                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PostgreSQL Database                                │   │
│  │  - Prestadores, Montadores                          │   │
│  │  - Lotes, OS, Pagamentos                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Configuração do Ambiente

### 1. Backend (Python + FastAPI)

#### Instalar Dependências

```bash
cd backend
pip install -r requirements.txt
```

#### Arquivo `requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
pydantic==2.4.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
requests==2.31.0
jinja2==3.1.2
weasyprint==60.1
```

#### Criar `.env` no Backend

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
SECRET_KEY=chave_secreta_jwt_complexa_aqui
DEBUG=True

# CORS (Frontend URL)
FRONTEND_URL=http://localhost:8080

# Email (Microsoft Graph)
CLIENT_ID=seu_client_id_azure
TENANT_ID=seu_tenant_id

# API DV Processamento
DV_API_URL=http://api.link.dev.br/dvprocessamento/
DV_API_KEY=DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6

# WhatsApp
WHATSAPP_BASE_URL=http://localhost:3000

# Trello
TRELLO_API_KEY=sua_api_key
TRELLO_TOKEN=seu_token
TRELLO_BOARD_ID=id_do_board
TRELLO_LIST_ID=id_da_lista
```

#### Iniciar Backend

```bash
# Desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

O backend estará disponível em: `http://localhost:8000`

Documentação automática: `http://localhost:8000/docs`

---

### 2. Frontend (React + Vite)

#### Instalar Dependências

```bash
npm install
```

#### Criar `.env.local` no Frontend

```env
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Se usar HTTPS em produção
# VITE_API_BASE_URL=https://api.seudomain.com/api/v1
```

#### Iniciar Frontend

```bash
npm run dev
```

O frontend estará disponível em: `http://localhost:8080`

---

## 🔌 Implementação da Camada de API

### Estrutura de Arquivos Frontend

```
src/
├── services/
│   ├── api.ts                    # Cliente base da API
│   ├── prestadores.service.ts    # Serviço de prestadores
│   ├── montadores.service.ts     # Serviço de montadores
│   ├── lotes.service.ts          # Serviço de lotes
│   ├── dashboard.service.ts      # Serviço do dashboard
│   └── auth.service.ts           # Serviço de autenticação
├── types/
│   ├── prestador.ts
│   ├── montador.ts
│   └── lote.ts
└── hooks/
    ├── use-prestadores.ts
    ├── use-montadores.ts
    └── use-dashboard.ts
```

### 1. Cliente Base da API (`src/services/api.ts`)

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem('auth_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
      throw new APIError(
        error.detail || error.message || 'Erro na requisição',
        response.status,
        error
      );
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseURL}${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse<T>(response);
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse<T>(response);
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }
}

export const apiClient = new APIClient();
```

---

### 2. Serviço de Prestadores (`src/services/prestadores.service.ts`)

```typescript
import { apiClient } from './api';
import { Prestador, PrestadorCreate, PrestadorUpdate } from '@/types/prestador';

export interface PrestadoresResponse {
  data: Prestador[];
  total: number;
  page: number;
  pages: number;
}

export interface PrestadoresFilters {
  search?: string;
  ativo?: boolean;
  page?: number;
  limit?: number;
}

export const prestadoresService = {
  async getAll(filters?: PrestadoresFilters): Promise<PrestadoresResponse> {
    return apiClient.get<PrestadoresResponse>('/prestadores', filters);
  },

  async getById(id: number): Promise<Prestador> {
    return apiClient.get<Prestador>(`/prestadores/${id}`);
  },

  async create(data: PrestadorCreate): Promise<{ id: number; message: string }> {
    return apiClient.post('/prestadores', data);
  },

  async update(id: number, data: PrestadorUpdate): Promise<Prestador> {
    return apiClient.put(`/prestadores/${id}`, data);
  },

  async delete(id: number): Promise<void> {
    return apiClient.delete(`/prestadores/${id}`);
  },
};
```

---

### 3. Types (`src/types/prestador.ts`)

```typescript
export interface Prestador {
  id: number;
  nome: string;
  email: string;
  fornecedor_id?: string;
  telefone?: string;
  regra_envio?: string;
  dias_envio?: string;
  tempo_vencimento_dias: number;
  emails_adicionais?: string;
  created_at: string;
  updated_at: string;
}

export interface PrestadorCreate {
  nome: string;
  email: string;
  fornecedor_id?: string;
  telefone?: string;
  regra_envio?: string;
  dias_envio?: string;
  tempo_vencimento_dias?: number;
  emails_adicionais?: string;
}

export interface PrestadorUpdate extends Partial<PrestadorCreate> {}
```

---

### 4. Hook com React Query (`src/hooks/use-prestadores.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { prestadoresService, PrestadoresFilters } from '@/services/prestadores.service';
import { PrestadorCreate, PrestadorUpdate } from '@/types/prestador';
import { toast } from 'sonner';

export function usePrestadores(filters?: PrestadoresFilters) {
  return useQuery({
    queryKey: ['prestadores', filters],
    queryFn: () => prestadoresService.getAll(filters),
  });
}

export function usePrestador(id: number) {
  return useQuery({
    queryKey: ['prestador', id],
    queryFn: () => prestadoresService.getById(id),
    enabled: !!id,
  });
}

export function useCreatePrestador() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PrestadorCreate) => prestadoresService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prestadores'] });
      toast.success('Prestador criado com sucesso!');
    },
    onError: (error: Error) => {
      toast.error(`Erro ao criar prestador: ${error.message}`);
    },
  });
}

export function useUpdatePrestador() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PrestadorUpdate }) =>
      prestadoresService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prestadores'] });
      toast.success('Prestador atualizado com sucesso!');
    },
    onError: (error: Error) => {
      toast.error(`Erro ao atualizar prestador: ${error.message}`);
    },
  });
}

export function useDeletePrestador() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => prestadoresService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prestadores'] });
      toast.success('Prestador removido com sucesso!');
    },
    onError: (error: Error) => {
      toast.error(`Erro ao remover prestador: ${error.message}`);
    },
  });
}
```

---

### 5. Uso nos Componentes

```typescript
// src/pages/Prestadores.tsx
import { useState } from 'react';
import { usePrestadores, useCreatePrestador } from '@/hooks/use-prestadores';
import { Button } from '@/components/ui/button';

export default function Prestadores() {
  const [searchTerm, setSearchTerm] = useState('');
  
  // Buscar prestadores
  const { data, isLoading, error } = usePrestadores({
    search: searchTerm,
    page: 1,
    limit: 10,
  });

  // Criar prestador
  const createMutation = useCreatePrestador();

  const handleCreate = async () => {
    await createMutation.mutateAsync({
      nome: 'Novo Prestador',
      email: 'novo@email.com',
      fornecedor_id: 'FOR123',
    });
  };

  if (isLoading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error.message}</div>;

  return (
    <div>
      <h1>Prestadores</h1>
      <Button onClick={handleCreate}>Criar Novo</Button>
      
      {data?.data.map((prestador) => (
        <div key={prestador.id}>
          <h3>{prestador.nome}</h3>
          <p>{prestador.email}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔐 Autenticação

### Backend: Geração de Token JWT

```python
# app/auth.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "sua_chave_secreta_complexa"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

# Rota de login
@app.post("/auth/login")
def login(username: str, password: str):
    # Validar usuário e senha
    # ...
    
    token = create_access_token({"sub": username, "user_id": 1})
    return {"access_token": token, "token_type": "bearer"}
```

### Frontend: Serviço de Autenticação

```typescript
// src/services/auth.service.ts
import { apiClient } from './api';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    
    // Salvar token no localStorage
    localStorage.setItem('auth_token', response.access_token);
    
    return response;
  },

  logout() {
    localStorage.removeItem('auth_token');
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('auth_token');
  },

  getToken(): string | null {
    return localStorage.getItem('auth_token');
  },
};
```

---

## ⚠️ Tratamento de Erros

```typescript
// src/services/api.ts (adicionar)

export function handleAPIError(error: unknown) {
  if (error instanceof APIError) {
    if (error.status === 401) {
      // Token expirado ou inválido
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
      toast.error('Sessão expirada. Faça login novamente.');
    } else if (error.status === 403) {
      toast.error('Você não tem permissão para esta ação.');
    } else if (error.status === 404) {
      toast.error('Recurso não encontrado.');
    } else if (error.status >= 500) {
      toast.error('Erro no servidor. Tente novamente mais tarde.');
    } else {
      toast.error(error.message);
    }
  } else {
    toast.error('Erro inesperado. Tente novamente.');
    console.error('Erro não tratado:', error);
  }
}
```

---

## 🧪 Testando a Integração

### 1. Testar Backend

```bash
# Verificar se API está respondendo
curl http://localhost:8000/

# Testar endpoint de prestadores (com autenticação)
curl -X GET http://localhost:8000/api/v1/prestadores \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"

# Ver documentação interativa
open http://localhost:8000/docs
```

### 2. Testar Frontend

```typescript
// src/pages/TestAPI.tsx
import { useEffect } from 'react';
import { prestadoresService } from '@/services/prestadores.service';

export default function TestAPI() {
  useEffect(() => {
    async function testAPI() {
      try {
        const result = await prestadoresService.getAll();
        console.log('✅ API funcionando:', result);
      } catch (error) {
        console.error('❌ Erro na API:', error);
      }
    }
    
    testAPI();
  }, []);

  return <div>Teste de API - Ver console</div>;
}
```

---

## 🚀 Deploy em Produção

### Backend

```bash
# Usando Docker
docker build -t braco-direito-api .
docker run -p 8000:8000 --env-file .env braco-direito-api

# Ou diretamente
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
# Build de produção
npm run build

# Servir com nginx, Apache, ou similar
# Os arquivos estarão em dist/
```

### Configurar CORS no Backend

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://seudominio.com"],  # URL do frontend em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 Checklist de Integração

- [ ] Backend rodando em `http://localhost:8000`
- [ ] Frontend rodando em `http://localhost:8080`
- [ ] Arquivo `.env` configurado no backend
- [ ] Arquivo `.env.local` configurado no frontend
- [ ] CORS configurado corretamente
- [ ] Banco de dados PostgreSQL rodando
- [ ] Migrations executadas
- [ ] Token JWT sendo gerado corretamente
- [ ] Requisições GET/POST/PUT/DELETE funcionando
- [ ] Tratamento de erros implementado
- [ ] Loading states nos componentes
- [ ] Toasts/notificações funcionando

---

## 🆘 Troubleshooting

### Erro: CORS Policy

**Problema:** Frontend não consegue fazer requisições ao backend.

**Solução:**
```python
# app/main.py - Verificar se CORS está configurado
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Erro: 401 Unauthorized

**Problema:** Token JWT não está sendo enviado ou é inválido.

**Solução:**
```typescript
// Verificar se token está no localStorage
console.log(localStorage.getItem('auth_token'));

// Verificar headers da requisição
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
};
```

### Erro: Connection Refused

**Problema:** Backend não está rodando ou porta incorreta.

**Solução:**
```bash
# Verificar se backend está rodando
lsof -i :8000

# Iniciar backend
uvicorn app.main:app --reload
```

---

## 📚 Recursos Adicionais

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Última atualização:** Novembro 2025  
**Versão:** 1.0.0
