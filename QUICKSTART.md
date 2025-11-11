# ⚡ Guia Rápido - Braço Direito

Comece a trabalhar com o sistema em **5 minutos**!

---

## 🎯 Para Desenvolvedores Frontend

### 1. Iniciar o Frontend (Interface)

```bash
# Instalar dependências (primeira vez)
npm install

# Criar arquivo de configuração
cp .env.example .env.local

# Iniciar servidor de desenvolvimento
npm run dev
```

✅ **Pronto!** Acesse: http://localhost:8080

---

## 🐍 Para Desenvolvedores Backend (Python)

### 1. Preparar Ambiente Python

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente
source venv/bin/activate  # Mac/Linux
# OU
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Banco de Dados

```bash
# Criar banco PostgreSQL
createdb braco_direito

# Copiar arquivo de configuração
cp .env.example .env

# Editar .env e configurar credenciais do banco
```

Exemplo de `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=braco_direito
DB_USER=postgres
DB_PASS=sua_senha
SECRET_KEY=chave_secreta_complexa_aqui
```

### 3. Executar Migrations

```bash
# Criar estrutura do banco
python migrations/run_migrations.py
```

### 4. Iniciar Backend

```bash
# Servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ **Pronto!** Acesse:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

## 🔗 Conectar Frontend ao Backend

### Frontend: Configurar URL da API

Edite `.env.local`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Backend: Configurar CORS

Edite `app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # URL do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🧪 Testar a Integração

### 1. Backend Rodando?

```bash
curl http://localhost:8000/
```

Deve retornar: `{"message": "Braço Direito API v1.0"}`

### 2. Frontend Conectando?

Abra o navegador em http://localhost:8080 e verifique o console (F12).

---

## 📂 Estrutura de Arquivos Importantes

```
braco-direito/
├── frontend/
│   ├── src/
│   │   ├── pages/              # Páginas da aplicação
│   │   ├── components/         # Componentes reutilizáveis
│   │   ├── services/           # ⭐ Camada de API
│   │   └── types/              # ⭐ Tipos TypeScript
│   └── .env.local              # ⭐ Configuração
│
└── backend/
    ├── app/
    │   ├── main.py             # ⭐ Entry point
    │   ├── database.py         # ⭐ Conexão com banco
    │   ├── routes/             # ⭐ Endpoints da API
    │   └── models/             # ⭐ Modelos de dados
    └── .env                    # ⭐ Configuração
```

---

## 🎨 Como Criar uma Nova Página

### 1. Criar o Componente

```typescript
// src/pages/MinhaNovaPage.tsx
export default function MinhaNovaPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold">Minha Nova Página</h1>
      <p className="text-muted-foreground">Conteúdo aqui</p>
    </div>
  );
}
```

### 2. Adicionar Rota

```typescript
// src/App.tsx
import MinhaNovaPage from "./pages/MinhaNovaPage";

// Adicionar dentro de <Routes>
<Route path="/minha-pagina" element={<MinhaNovaPage />} />
```

### 3. Adicionar ao Menu

```typescript
// src/components/AppSidebar.tsx
const menuItems = [
  {
    title: "Principal",
    items: [
      // ... itens existentes
      { title: "Minha Página", url: "/minha-pagina", icon: Star },
    ],
  },
];
```

---

## 🔌 Como Criar um Novo Endpoint

### 1. Backend: Criar Rota

```python
# backend/app/routes/meus_dados.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def listar_meus_dados():
    return {"data": [{"id": 1, "nome": "Exemplo"}]}

@router.post("/")
def criar_meu_dado(nome: str):
    return {"id": 2, "nome": nome, "message": "Criado!"}
```

### 2. Backend: Registrar Rota

```python
# backend/app/main.py
from app.routes import meus_dados

app.include_router(
    meus_dados.router, 
    prefix="/api/v1/meus-dados", 
    tags=["Meus Dados"]
)
```

### 3. Frontend: Criar Serviço

```typescript
// src/services/meus-dados.service.ts
import { apiClient } from './api';

export const meusDadosService = {
  async getAll() {
    return apiClient.get('/meus-dados');
  },
  
  async create(nome: string) {
    return apiClient.post('/meus-dados', { nome });
  },
};
```

### 4. Frontend: Usar no Componente

```typescript
// src/pages/MinhaPage.tsx
import { useEffect, useState } from 'react';
import { meusDadosService } from '@/services/meus-dados.service';

export default function MinhaPage() {
  const [dados, setDados] = useState([]);

  useEffect(() => {
    meusDadosService.getAll()
      .then(response => setDados(response.data))
      .catch(error => console.error(error));
  }, []);

  return (
    <div>
      {dados.map(item => (
        <div key={item.id}>{item.nome}</div>
      ))}
    </div>
  );
}
```

---

## 🎨 Usar Componentes do Design System

### Cards

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Meu Card</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Conteúdo do card</p>
  </CardContent>
</Card>
```

### Botões

```typescript
import { Button } from "@/components/ui/button";

<Button>Primário</Button>
<Button variant="secondary">Secundário</Button>
<Button variant="outline">Outline</Button>
<Button variant="destructive">Deletar</Button>
```

### Tabelas

```typescript
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Nome</TableHead>
      <TableHead>Email</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>João Silva</TableCell>
      <TableCell>joao@email.com</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Notificações (Toast)

```typescript
import { toast } from "sonner";

// Sucesso
toast.success("Operação realizada com sucesso!");

// Erro
toast.error("Erro ao processar operação");

// Aviso
toast.warning("Atenção!");

// Info
toast.info("Informação importante");
```

---

## 🐛 Problemas Comuns

### "Cannot connect to backend"

✅ **Solução:**
1. Verifique se o backend está rodando: `lsof -i :8000`
2. Verifique o `.env.local` do frontend
3. Verifique CORS no backend

### "Token inválido"

✅ **Solução:**
```typescript
// Limpar token e fazer login novamente
localStorage.removeItem('auth_token');
```

### "Database connection error"

✅ **Solução:**
1. Verifique se PostgreSQL está rodando
2. Verifique credenciais no `.env` do backend
3. Teste conexão: `psql -U postgres -d braco_direito`

---

## 📚 Próximos Passos

1. ✅ Leia a documentação completa: [BACKEND_DOCUMENTATION.md](./BACKEND_DOCUMENTATION.md)
2. ✅ Entenda a integração: [FRONTEND_BACKEND_INTEGRATION.md](./FRONTEND_BACKEND_INTEGRATION.md)
3. ✅ Explore os componentes Shadcn/ui
4. ✅ Implemente autenticação JWT
5. ✅ Adicione testes automatizados

---

## 🆘 Precisa de Ajuda?

- 📖 Leia a documentação completa
- 🐛 Reporte bugs abrindo uma issue
- 💬 Pergunte ao time de TI

---

**Braço Direito** - Sistema moderno de gestão 🤝
