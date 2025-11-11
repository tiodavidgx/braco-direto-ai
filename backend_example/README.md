# Backend Python - Braço Direito

API REST desenvolvida com FastAPI para o sistema Braço Direito.

## 🚀 Início Rápido

### 1. Criar Ambiente Virtual

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# OU
venv\Scripts\activate  # Windows
```

### 2. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
# Editar .env com suas configurações
```

### 4. Criar Banco de Dados

```bash
createdb braco_direito
```

### 5. Inicializar Banco

```bash
python app/database.py
```

### 6. Executar Servidor

```bash
# Desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📂 Estrutura

```
backend_example/
├── app/
│   ├── main.py              # Entry point
│   ├── database.py          # Conexão com banco
│   └── routes/              # Endpoints
│       ├── dashboard.py
│       ├── prestadores.py
│       └── montadores.py
├── requirements.txt         # Dependências
├── .env.example            # Exemplo de configuração
└── README.md               # Este arquivo
```

## 📚 Endpoints

Acesse a documentação interativa:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testar

```bash
# Verificar se está online
curl http://localhost:8000/

# Listar prestadores
curl http://localhost:8000/api/v1/prestadores

# Ver documentação
open http://localhost:8000/docs
```

## 📖 Documentação Completa

Consulte `BACKEND_DOCUMENTATION.md` na raiz do projeto para documentação detalhada.
