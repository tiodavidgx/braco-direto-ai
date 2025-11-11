# 📧 Integração de Email - Microsoft Graph API

## 🎯 Visão Geral

O sistema **Braço Direito** envia relatórios automaticamente por email para prestadores e montadores usando **Microsoft Graph API** (Office 365).

### Funcionalidades
- ✅ Geração automática de PDFs com relatórios
- ✅ Envio de emails com anexos via Microsoft Graph
- ✅ Templates HTML personalizáveis
- ✅ Link para upload de Nota Fiscal incluído
- ✅ Controle de status de envio

---

## 🔐 Configuração Microsoft Graph API

### 1. Criar Aplicação no Azure

1. Acesse: https://portal.azure.com
2. Vá em **Azure Active Directory** → **App registrations**
3. Clique em **New registration**
4. Preencha:
   - **Name**: Braço Direito Email
   - **Supported account types**: Single tenant
   - **Redirect URI**: http://localhost:8000/auth/callback
5. Copie o **Application (client) ID** e **Directory (tenant) ID**

### 2. Configurar Permissões

1. Na aplicação criada, vá em **API permissions**
2. Adicione as seguintes permissões (Delegated):
   - `Mail.Send`
   - `Mail.ReadWrite`
   - `User.Read`
3. Clique em **Grant admin consent**

### 3. Criar Client Secret

1. Vá em **Certificates & secrets**
2. Clique em **New client secret**
3. Copie o valor do secret (só aparece uma vez!)

### 4. Configurar .env

```env
# Microsoft Graph
CLIENT_ID=seu_client_id_aqui
TENANT_ID=seu_tenant_id_aqui
CLIENT_SECRET=seu_client_secret_aqui
AUTHORITY=https://login.microsoftonline.com/{TENANT_ID}
```

---

## 🚀 Implementação Backend

### Autenticação OAuth2

```python
# app/auth/microsoft.py
from msal import ConfidentialClientApplication
import os

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTHORITY = os.getenv('AUTHORITY')
SCOPES = ['https://graph.microsoft.com/.default']

def get_access_token():
    """Obtém token de acesso para Microsoft Graph"""
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    
    result = app.acquire_token_for_client(scopes=SCOPES)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Erro ao obter token: {result.get('error_description')}")
```

### Envio de Email com Anexo

```python
# app/services/email_service.py
import requests
import base64
from pathlib import Path

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

def enviar_email(destinatario: str, assunto: str, corpo_html: str, pdf_path: str = None):
    """Envia email via Microsoft Graph"""
    
    token = get_access_token()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    message = {
        "subject": assunto,
        "body": {
            "contentType": "HTML",
            "content": corpo_html
        },
        "toRecipients": [
            {"emailAddress": {"address": destinatario}}
        ]
    }
    
    # Adicionar anexo PDF
    if pdf_path and Path(pdf_path).exists():
        with open(pdf_path, 'rb') as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        message["attachments"] = [{
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": Path(pdf_path).name,
            "contentType": "application/pdf",
            "contentBytes": pdf_base64
        }]
    
    response = requests.post(
        f"{GRAPH_API_URL}/me/sendMail",
        headers=headers,
        json={"message": message, "saveToSentItems": "true"}
    )
    
    if response.status_code != 202:
        raise Exception(f"Erro: {response.text}")
    
    return True
```

### Geração de PDF

```python
# app/services/pdf_service.py
from jinja2 import Template
from weasyprint import HTML
from pathlib import Path

def gerar_pdf_relatorio(template_name: str, data: dict, output_path: str):
    """Gera PDF a partir de template HTML"""
    
    template_path = Path(__file__).parent.parent / 'templates' / template_name
    
    with open(template_path, 'r') as f:
        template = Template(f.read())
    
    html_content = template.render(**data)
    HTML(string=html_content).write_pdf(output_path)
    
    return output_path
```

---

## 📋 Fluxo Completo de Envio

```python
# app/routes/relatorios.py
@router.post("/enviar")
def enviar_relatorio(lote_id: int, tipo: str):
    """
    Fluxo completo:
    1. Buscar dados do banco
    2. Gerar PDF
    3. Enviar email
    4. Atualizar status
    """
    
    # 1. Buscar dados
    lote = get_lote(lote_id)
    
    # 2. Gerar PDF
    pdf_path = gerar_pdf_relatorio(
        template_name='invoice_template.html',
        data={
            'nome_prestador': lote['prestador_nome'],
            'periodo': lote['periodo'],
            'items': lote['os_list'],
            'total_geral': lote['valor_total']
        },
        output_path=f'/tmp/relatorio_{lote_id}.pdf'
    )
    
    # 3. Preparar corpo do email
    corpo_email = f"""
    <html>
    <body>
        <h2>Relatório de Fechamento</h2>
        <p>Olá {lote['prestador_nome']},</p>
        <p>Segue em anexo o relatório do período {lote['periodo']}.</p>
        <p><strong>Valor Total:</strong> R$ {lote['valor_total']:.2f}</p>
        <hr>
        <p><a href="{lote['link_upload']}">Enviar Nota Fiscal</a></p>
        <p>Atenciosamente,<br><strong>Novo Mundo</strong></p>
    </body>
    </html>
    """
    
    # 4. Enviar email
    enviar_email(
        destinatario=lote['email'],
        assunto=f"Relatório de Fechamento - {lote['periodo']}",
        corpo_html=corpo_email,
        pdf_path=pdf_path
    )
    
    # 5. Atualizar status
    update_status(lote_id, 'Aguardando NF')
    
    return {"success": True, "message": "Relatório enviado!"}
```

---

## 🎨 Templates HTML

### Template de Prestador

Usar o arquivo `invoice_template.html` fornecido pelo sistema original.

### Template de Montador

Usar o arquivo `montador_template.html` fornecido.

---

## 🔄 Alternativa: Usar Resend.com

Se preferir **não usar Microsoft Graph**, pode usar **Resend.com**:

```python
from resend import Resend

resend = Resend(os.getenv('RESEND_API_KEY'))

def enviar_email_resend(destinatario: str, assunto: str, html: str, pdf_path: str):
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    resend.emails.send({
        "from": "Novo Mundo <noreply@seudominio.com>",
        "to": destinatario,
        "subject": assunto,
        "html": html,
        "attachments": [{
            "filename": "relatorio.pdf",
            "content": pdf_content
        }]
    })
```

**Vantagens Resend:**
- ✅ Mais simples de configurar
- ✅ Melhor entrega (deliverability)
- ✅ API mais moderna

**Desvantagens:**
- ❌ Pago (após limite gratuito)
- ❌ Precisa validar domínio

---

## 📊 Frontend: Integração

```typescript
// src/services/relatorios.service.ts
export const relatoriosService = {
  async enviarRelatorio(id: number, tipo: 'prestador' | 'montador') {
    return apiClient.post('/relatorios/enviar', { id, tipo });
  },

  async listarPendentes(tipo: 'prestador' | 'montador') {
    return apiClient.get('/relatorios/pendentes', { tipo });
  },
};
```

---

## ✅ Checklist de Implementação

- [ ] Criar aplicação no Azure AD
- [ ] Configurar permissões (Mail.Send)
- [ ] Gerar Client Secret
- [ ] Configurar variáveis no .env
- [ ] Implementar autenticação OAuth2
- [ ] Implementar função de envio de email
- [ ] Testar envio de email simples
- [ ] Adicionar suporte a anexos PDF
- [ ] Integrar com geração de relatórios
- [ ] Testar fluxo completo

---

## 🧪 Testando

```bash
# 1. Testar obtenção de token
python -c "from app.auth.microsoft import get_access_token; print(get_access_token())"

# 2. Testar envio de email (sem anexo)
curl -X POST http://localhost:8000/api/v1/relatorios/enviar \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "tipo": "prestador"}'

# 3. Verificar logs
tail -f logs/email.log
```

---

## 🆘 Troubleshooting

### Erro: "AADSTS70011: Invalid scope"

**Solução:** Usar `https://graph.microsoft.com/.default` como scope.

### Erro: "403 Forbidden"

**Solução:** Verificar se admin consent foi dado no Azure AD.

### Email não chega

**Soluções:**
1. Verificar caixa de spam
2. Validar domínio de envio
3. Verificar logs do Graph API
4. Testar com outro email

---

## 📚 Recursos

- [Microsoft Graph API Docs](https://learn.microsoft.com/en-us/graph/api/user-sendmail)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [WeasyPrint Docs](https://doc.courtbouillon.org/weasyprint/)

---

**Sistema Braço Direito** - Novo Mundo 🤝
