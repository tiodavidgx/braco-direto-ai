# 🔐 Configuração Rápida - Email Microsoft

## 📋 Passo a Passo Simplificado

### 1️⃣ Acesse o Portal Azure
👉 **https://portal.azure.com/**

### 2️⃣ Registre o Aplicativo

1. No menu, procure por **"App registrations"** ou **"Registros de aplicativo"**
2. Clique em **"+ New registration"** ou **"+ Novo registro"**
3. Preencha:
   - **Nome**: `Braco Direto Email` (ou qualquer nome)
   - **Supported account types**: Escolha uma opção:
     - ✅ **"Accounts in this organizational directory only"** (se for só sua empresa)
     - ✅ **"Accounts in any organizational directory"** (se for várias empresas)
   - **Redirect URI**:
     - Tipo: **Web**
     - URL: `http://localhost:8080/auth/callback`
4. Clique em **"Register"** ou **"Registrar"**

### 3️⃣ Copie o Client ID

Na página que abrir, você verá:
- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

📝 **Copie esses dois valores!**

### 4️⃣ Configure Permissões (API Permissions)

1. No menu lateral, clique em **"API permissions"** ou **"Permissões de API"**
2. Clique em **"+ Add a permission"** ou **"+ Adicionar permissão"**
3. Escolha **"Microsoft Graph"**
4. Escolha **"Delegated permissions"** ou **"Permissões delegadas"**
5. Procure e marque:
   - ✅ **`Mail.Send`** (enviar emails)
   - ✅ **`User.Read`** (ler dados do usuário)
6. Clique em **"Add permissions"** ou **"Adicionar permissões"**
7. **(Opcional)** Clique em **"Grant admin consent"** para aprovar para todos

### 5️⃣ Gere o Client Secret

1. No menu lateral, clique em **"Certificates & secrets"** ou **"Certificados e segredos"**
2. Na aba **"Client secrets"**, clique em **"+ New client secret"** ou **"+ Novo segredo do cliente"**
3. Preencha:
   - **Description**: `Braco Direto Secret`
   - **Expires**: Escolha a validade (recomendo **24 months**)
4. Clique em **"Add"** ou **"Adicionar"**
5. ⚠️ **COPIE O VALOR AGORA!** (só aparece uma vez)
   - **Value**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` 

### 6️⃣ Configure o Backend

Abra o arquivo `.env` e cole os valores:

```bash
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MICROSOFT_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/callback
```

Se for usar com **qualquer conta Microsoft** (não só sua empresa), use:
```bash
MICROSOFT_TENANT_ID=common
```

### 7️⃣ Reinicie o Backend

```bash
# Mate o processo atual
lsof -ti:8000 | xargs kill -9

# No diretório backend_example
cd backend_example
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8️⃣ Teste o Sistema

1. Abra o navegador: **http://localhost:8080/email-config**
2. Clique em **"Conectar com Microsoft"**
3. Você será **redirecionado** para a página de login da Microsoft
4. Faça login com sua conta Office 365
5. Aceite as permissões
6. Você será **redirecionado de volta** para o sistema
7. Status deve mostrar **"Conectado"** ✅

---

## 🎯 Fluxo Simplificado

```
┌─────────────────────┐
│  Usuário clica em   │
│ "Conectar Microsoft"│
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Redireciona para   │
│  login.microsoft... │ (Página da Microsoft)
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│   Usuário faz login │
│   e autoriza o app  │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Volta para sistema │
│  /auth/callback     │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│   ✅ CONECTADO!     │
└─────────────────────┘
```

---

## ❓ Problemas Comuns

### Erro: "Invalid redirect URI"
- Certifique-se que configurou: `http://localhost:8080/auth/callback`
- Não use HTTPS no localhost

### Erro: "Admin consent required"
- Peça ao admin da empresa para aprovar no Azure Portal
- Ou use `MICROSOFT_TENANT_ID=common` (se for conta pessoal)

### Backend não reiniciou
```bash
# Force o kill
pkill -f uvicorn

# Suba novamente
cd backend_example
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📝 Resumo dos Valores Necessários

| Variável | Onde encontrar |
|----------|----------------|
| `MICROSOFT_CLIENT_ID` | Azure Portal > App Registration > Overview > Application (client) ID |
| `MICROSOFT_CLIENT_SECRET` | Azure Portal > App Registration > Certificates & secrets > Client secrets > Value |
| `MICROSOFT_TENANT_ID` | Azure Portal > App Registration > Overview > Directory (tenant) ID ou use `common` |
| `MICROSOFT_REDIRECT_URI` | Sempre: `http://localhost:8080/auth/callback` |

---

**🚀 Pronto! Depois de configurar, o sistema funcionará exatamente como o anterior: clica no botão → redireciona para Microsoft → faz login → volta conectado!**
