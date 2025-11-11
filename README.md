# 🤝 Braço Direito - Sistema de Gestão

Sistema moderno e profissional para gestão de prestadores, montadores e controle financeiro. Interface inspirada no Google Material Design.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![React](https://img.shields.io/badge/React-18.3.1-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![Backend](https://img.shields.io/badge/Backend-Python%20%2B%20FastAPI-green)

---

## 📋 Sobre o Sistema

O **Braço Direito** é uma solução completa para gestão de:

- 👥 **Prestadores** - Empresas que prestam serviços
- 🔧 **Montadores** - Profissionais de montagem
- 📦 **Lotes de Serviço** - Agrupamento de OS (Ordens de Serviço)
- 💰 **Pagamentos** - Controle financeiro e vencimentos
- 📄 **Notas Fiscais** - Upload e gestão de NFs
- 📱 **WhatsApp** - Notificações automáticas
- 📊 **Trello** - Integração para gestão de tarefas
- ⏰ **Jobs Automáticos** - Tarefas agendadas

---

## 🎨 Interface Moderna

Interface inspirada no **Google Material Design**:
- ✅ Design limpo e minimalista
- ✅ Componentes reutilizáveis
- ✅ Totalmente responsiva
- ✅ Navegação intuitiva com sidebar
- ✅ Cards e estatísticas em tempo real
- ✅ Animações suaves
- ✅ Modo escuro (dark mode)

---

## 🚀 Tecnologias

### Frontend
- **React 18** - Framework UI
- **TypeScript** - Tipagem estática
- **Vite** - Build tool
- **Tailwind CSS** - Estilização
- **Shadcn/ui** - Componentes UI
- **React Query** - Gerenciamento de estado e cache
- **React Router** - Roteamento

### Backend (Python)
- **FastAPI** - Framework web moderno
- **PostgreSQL** - Banco de dados
- **psycopg2** - Driver PostgreSQL
- **JWT** - Autenticação
- **python-dotenv** - Variáveis de ambiente

---

## 📁 Estrutura do Projeto

```
braco-direito/
├── frontend/                          # Interface React
│   ├── src/
│   │   ├── components/               # Componentes reutilizáveis
│   │   │   ├── ui/                  # Componentes Shadcn
│   │   │   ├── AppSidebar.tsx       # Sidebar de navegação
│   │   │   └── StatCard.tsx         # Card de estatísticas
│   │   ├── pages/                   # Páginas da aplicação
│   │   │   ├── Dashboard.tsx        # Dashboard principal
│   │   │   ├── Prestadores.tsx      # Gestão de prestadores
│   │   │   └── Montadores.tsx       # Gestão de montadores
│   │   ├── services/                # Camada de API
│   │   │   ├── api.ts              # Cliente base
│   │   │   └── prestadores.service.ts
│   │   ├── hooks/                   # Hooks customizados
│   │   ├── types/                   # Tipos TypeScript
│   │   └── lib/                     # Utilitários
│   └── ...
│
├── backend/                          # API Python (FastAPI)
│   ├── app/
│   │   ├── main.py                 # Entry point
│   │   ├── database.py             # Conexão com banco
│   │   ├── models/                 # Modelos de dados
│   │   ├── routes/                 # Endpoints da API
│   │   ├── services/               # Lógica de negócio
│   │   └── utils/                  # Utilitários
│   ├── migrations/                 # Scripts de migração
│   ├── tests/                      # Testes automatizados
│   ├── requirements.txt            # Dependências
│   └── .env                        # Variáveis de ambiente
│
├── BACKEND_DOCUMENTATION.md         # Documentação completa do backend
├── FRONTEND_BACKEND_INTEGRATION.md  # Guia de integração
└── README.md                        # Este arquivo
```

---

## ⚙️ Configuração e Instalação

### Pré-requisitos

- **Node.js 18+** e npm
- **Python 3.9+**
- **PostgreSQL 14+**
- **Git**

### 1. Clone o Repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd braco-direito
```

### 2. Configurar Frontend

```bash
# Instalar dependências
npm install

# Criar arquivo de configuração
cp .env.example .env.local

# Editar .env.local
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Iniciar desenvolvimento
npm run dev
```

O frontend estará disponível em: **http://localhost:8080**

### 3. Configurar Backend

```bash
# Criar ambiente virtual Python
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r backend/requirements.txt

# Criar arquivo .env no backend
cp backend/.env.example backend/.env

# Configurar banco de dados PostgreSQL
createdb braco_direito

# Executar migrations
python backend/migrations/run_migrations.py

# Iniciar servidor
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O backend estará disponível em: **http://localhost:8000**

Documentação da API: **http://localhost:8000/docs**

---

## 📚 Documentação Completa

- 📖 **[BACKEND_DOCUMENTATION.md](./BACKEND_DOCUMENTATION.md)** - Documentação completa do backend
  - Estrutura do banco de dados
  - Endpoints da API REST
  - Modelos de dados
  - Guia de implementação
  - Integrações (WhatsApp, Trello, Email)

- 🔗 **[FRONTEND_BACKEND_INTEGRATION.md](./FRONTEND_BACKEND_INTEGRATION.md)** - Guia de integração
  - Configuração do ambiente
  - Implementação da camada de API
  - Autenticação JWT
  - Hooks React Query
  - Tratamento de erros
  - Deploy em produção

---

## 🔧 Scripts Disponíveis

### Frontend

```bash
npm run dev          # Inicia servidor de desenvolvimento
npm run build        # Build de produção
npm run preview      # Preview do build
npm run lint         # Verifica código
```

### Backend

```bash
uvicorn app.main:app --reload              # Desenvolvimento
uvicorn app.main:app --workers 4           # Produção
python -m pytest                           # Executar testes
python migrations/run_migrations.py        # Executar migrations
```

---

## 🎯 Funcionalidades Principais

### ✅ Implementadas

- [x] Dashboard com estatísticas em tempo real
- [x] Gestão de Prestadores (CRUD completo)
- [x] Gestão de Montadores (CRUD completo)
- [x] Design system moderno (Google Material Design)
- [x] Navegação com sidebar responsiva
- [x] Componentes reutilizáveis (StatCard, Tables, etc.)
- [x] Estrutura de API pronta para integração
- [x] Documentação completa

### 🚧 Em Desenvolvimento (Backend Python)

- [ ] API REST com FastAPI
- [ ] Autenticação JWT
- [ ] Gestão de Lotes de Serviço
- [ ] Upload de Notas Fiscais
- [ ] Controle de Pagamentos
- [ ] Integração WhatsApp
- [ ] Integração Trello
- [ ] Jobs Automáticos
- [ ] Geração de PDFs (relatórios)

### 📅 Roadmap

- [ ] Sistema de notificações em tempo real
- [ ] Dashboard com gráficos avançados
- [ ] Filtros avançados e busca
- [ ] Exportação de dados (Excel, CSV)
- [ ] Auditoria e logs
- [ ] Configurações de sistema
- [ ] Múltiplos usuários e permissões

---

## 🔐 Segurança

- Autenticação via JWT
- Senhas criptografadas com bcrypt
- CORS configurado corretamente
- Validação de entrada de dados
- SQL injection prevention (psycopg2 parametrizado)
- Rate limiting (em produção)

---

## 🧪 Testes

```bash
# Frontend
npm run test

# Backend
python -m pytest

# Coverage
python -m pytest --cov=app
```

---

## 🤝 Como Contribuir

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Convenções de Código

### Frontend (TypeScript)
- Usar PascalCase para componentes
- Usar camelCase para funções e variáveis
- Usar types do TypeScript sempre que possível
- Comentar código complexo

### Backend (Python)
- Seguir PEP 8
- Usar snake_case para funções e variáveis
- Usar type hints
- Documentar funções com docstrings

---

## 🐛 Reportar Bugs

Encontrou um bug? Abra uma issue com:
- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs. atual
- Screenshots (se aplicável)
- Versão do sistema

---

## 📄 Licença

Este projeto é proprietário da **Novo Mundo**.

---

## 👥 Equipe

Desenvolvido pela equipe de TI da Novo Mundo.

---

## 📞 Suporte

Para dúvidas ou suporte:
- Email: ti@novomundo.com.br
- Documentação: [BACKEND_DOCUMENTATION.md](./BACKEND_DOCUMENTATION.md)
- Integração: [FRONTEND_BACKEND_INTEGRATION.md](./FRONTEND_BACKEND_INTEGRATION.md)

---

## 🔄 Histórico de Versões

### v1.0.0 (Novembro 2025)
- ✨ Interface inicial moderna e profissional
- 📚 Documentação completa do backend
- 🔗 Guia de integração frontend-backend
- 🎨 Design system inspirado no Google
- 👥 Módulos de Prestadores e Montadores
- 📊 Dashboard com estatísticas

---

**Braço Direito** - Sistema moderno de gestão para Novo Mundo 🤝
