# Configuração de Autenticação Microsoft OAuth2

Este documento explica como configurar a autenticação Microsoft para envio de emails.

## 📋 Pré-requisitos

- Conta Microsoft 365 (Office 365)
- Acesso ao Azure Portal
- Permissões para criar registros de aplicativos no Azure AD

## 🔧 Passo a Passo

### 1. Criar Registro de Aplicativo no Azure

1. Acesse o [Azure Portal](https://portal.azure.com/)
2. Navegue para **Azure Active Directory** > **App registrations**
3. Clique em **New registration**

### 2. Configurar o Aplicativo

**Nome do aplicativo:**
```
Braço Direito - Envio de Emails
```

**Tipos de conta com suporte:**
- Selecione: **Contas somente neste diretório organizacional** (se for uso interno)
- OU: **Contas em qualquer diretório organizacional** (para multi-tenant)

**URI de redirecionamento:**
- Tipo: **Web**
- URL: `http://localhost:8080/auth/callback`
- Para produção, adicione também: `https://seudominio.com/auth/callback`

Clique em **Registrar**

### 3. Configurar Permissões (API Permissions)

Após criar o app, vá em **API permissions**:

1. Clique em **Add a permission**
2. Selecione **Microsoft Graph**
3. Escolha **Delegated permissions**
4. Adicione as seguintes permissões:
   - `Mail.Send` - Enviar emails como o usuário
   - `User.Read` - Ler informações básicas do usuário

5. Clique em **Add permissions**
6. Clique em **Grant admin consent** (se você tiver permissões de admin)

### 4. Criar Client Secret

1. Vá em **Certificates & secrets**
2. Clique em **New client secret**
3. Adicione uma descrição: `Braço Direito Secret`
4. Escolha a validade (recomendado: 24 meses)
5. Clique em **Add**
6. **IMPORTANTE:** Copie o valor do secret IMEDIATAMENTE (ele só aparece uma vez!)

### 5. Coletar Informações

Você precisará de três informações:

**Client ID (Application ID):**
- Encontrado na página **Overview** do seu app
- Exemplo: `d6c7e7f3-25e7-4764-ad85-04edc46668c5`

**Client Secret (Value):**
- O valor que você copiou no passo anterior
- Exemplo: `AbC~123XyZ...`

**Tenant ID (Directory ID):**
- Também na página **Overview**
- Exemplo: `65fe7112-9a31-472e-98eb-6cb243ccdf94`

### 6. Configurar Backend

Edite o arquivo `.env` no diretório `backend_example/`:

```bash
# Microsoft OAuth2 (para envio de emails)
MICROSOFT_CLIENT_ID=seu_client_id_aqui
MICROSOFT_CLIENT_SECRET=seu_client_secret_aqui
MICROSOFT_TENANT_ID=seu_tenant_id_aqui
MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/callback
```

**Para produção:**
```bash
MICROSOFT_REDIRECT_URI=https://seudominio.com/auth/callback
```

### 7. Reiniciar Backend

```bash
cd backend_example
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Autenticar no Frontend

1. Acesse `http://localhost:8080/email-config`
2. Clique em **Conectar com Microsoft**
3. Faça login com sua conta Microsoft 365
4. Autorize as permissões solicitadas
5. Você será redirecionado de volta e verá "Conectado"

## ✅ Verificação

Após conectar, você verá:
- ✅ Status: **Conectado**
- 📧 Conta: **seu-email@dominio.com**
- ⏰ Token expira em: **[data/hora]**

## 🔄 Renovação Automática

O sistema renova o token automaticamente quando:
- O token está próximo de expirar (5 minutos antes)
- Você tenta enviar um email e o token está expirado

## 🚨 Troubleshooting

### Erro: "AADSTS50011: The reply URL specified in the request does not match"

**Solução:**
1. Vá no Azure Portal > seu App > **Authentication**
2. Adicione exatamente a URL: `http://localhost:8080/auth/callback`
3. Para produção: `https://seudominio.com/auth/callback`

### Erro: "Insufficient privileges to complete the operation"

**Solução:**
1. Verifique se as permissões `Mail.Send` e `User.Read` foram adicionadas
2. Clique em **Grant admin consent** no Azure Portal
3. Se não tiver permissões de admin, peça para o administrador aprovar

### Erro: "The client secret has expired"

**Solução:**
1. Crie um novo client secret no Azure Portal
2. Atualize o `.env` com o novo secret
3. Reinicie o backend

### Token expirando muito rápido

**Solução:**
- Os tokens da Microsoft expiram em 1 hora por padrão
- O refresh token permite renovação por até 90 dias
- O sistema renova automaticamente usando o refresh token

## 🌐 Uso em Produção

### Configurações Adicionais para Produção:

1. **URI de Redirecionamento:**
   ```bash
   MICROSOFT_REDIRECT_URI=https://seudominio.com/auth/callback
   ```

2. **Azure Portal:**
   - Adicione a URL de produção em **Authentication** > **Redirect URIs**
   - Configure domínio personalizado se necessário

3. **Segurança:**
   - Use HTTPS em produção (obrigatório)
   - Mantenha o Client Secret seguro (use variáveis de ambiente)
   - Configure CSP headers apropriados
   - Monitore o uso da API Graph

## 📚 Recursos Adicionais

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [OAuth 2.0 Authorization Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [Microsoft Graph Mail API](https://docs.microsoft.com/en-us/graph/api/user-sendmail)

## 🆘 Suporte

Se encontrar problemas:
1. Verifique os logs do backend
2. Confirme que todas as variáveis de ambiente estão configuradas
3. Teste a autenticação no Azure Portal
4. Verifique se as permissões foram concedidas corretamente
