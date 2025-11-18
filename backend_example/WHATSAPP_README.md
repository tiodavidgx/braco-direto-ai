# 📱 Integração WhatsApp - Braço Direto AI

## ✅ Sistema Totalmente Integrado

A integração WhatsApp está completamente integrada ao sistema. Não é necessário rodar servidores externos manualmente!

## 🚀 Como Usar

### 1. Instalar Dependências (Apenas uma vez)

```bash
cd backend_example
./setup_whatsapp.sh
```

Ou manualmente:
```bash
cd backend_example
npm install
```

### 2. Acessar a Interface

1. Acesse: http://localhost:8080/whatsapp
2. Clique no botão **"Iniciar Servidor WhatsApp"**
3. Aguarde o QR Code aparecer na tela
4. Escaneie o QR Code com WhatsApp
5. Pronto! ✅

## 📋 Funcionalidades

### Página WhatsApp (`/whatsapp`)
- ✅ Iniciar/Parar servidor pela interface
- ✅ Visualizar QR Code diretamente na página
- ✅ Enviar mensagens individuais
- ✅ Envio em massa (múltiplos números)
- ✅ Enviar para Prestadores
- ✅ Enviar para Montadores

### Página Automação (`/automacao`)
- ✅ Gerenciar templates de mensagens
- ✅ Configurar gatilhos automáticos
- ✅ Templates para Prestadores e Montadores

## 🔧 Estrutura Técnica

### Backend
- **FastAPI** (Python) - API principal
- **Node.js + Express** - Servidor WhatsApp
- **whatsapp-web.js** - Cliente WhatsApp Web

### Arquivos Importantes
- `backend_example/whatsapp_server.js` - Servidor WhatsApp
- `backend_example/app/routes/whatsapp.py` - Rotas da API
- `src/pages/WhatsApp.tsx` - Interface de envio
- `src/pages/Automacao.tsx` - Interface de automação

## 📊 Banco de Dados

Tabelas WhatsApp:
- `templates_whatsapp` - Templates de mensagens
- `automacao_whatsapp` - Configuração de gatilhos
- `notificacoes_whatsapp` - Histórico de envios
- `whatsapp_queue` - Fila de processamento

## 🎯 Automações Pré-configuradas

1. **Envio de Relatório para Prestador**
   - Gatilho: `envio_email_prestador`
   - Template: Notificação com link para upload de NF

2. **Confirmação de NF Recebida (Prestador)**
   - Gatilho: `nf_recebida_prestador`
   - Template: Confirmação de recebimento

3. **Envio de Relatório para Montador**
   - Gatilho: `envio_email_montador`
   - Template: Notificação de novo relatório

4. **Confirmação de NF Recebida (Montador)**
   - Gatilho: `nf_recebida_montador`
   - Template: Confirmação de recebimento

## 🔒 Segurança

- As credenciais do WhatsApp são salvas localmente em `.wwebjs_auth/`
- Não é necessário escanear o QR Code toda vez
- A sessão persiste entre reinicializações

## 🛠️ Comandos Úteis

### Iniciar apenas o servidor WhatsApp (via terminal)
```bash
cd backend_example
node whatsapp_server.js
```

### Parar o servidor
Use o botão "Parar Servidor" na interface ou:
```bash
pkill -f whatsapp_server.js
```

### Ver logs do servidor
Os logs aparecem no terminal onde o servidor foi iniciado

## 📝 Variáveis Disponíveis nos Templates

### Templates de Prestador
- `{{nome_prestador}}` - Nome do prestador
- `{{periodo}}` - Período do serviço
- `{{valor}}` - Valor total
- `{{link}}` - Link para upload de NF
- `{{numero_nf}}` - Número da nota fiscal
- `{{data_recebimento}}` - Data de recebimento da NF

### Templates de Montador
- `{{nome_montador}}` - Nome do montador
- `{{periodo_relatorio}}` - Período do relatório
- `{{valor_total}}` - Valor total
- `{{quantidade_os}}` - Quantidade de OSs
- `{{numero_nf}}` - Número da nota fiscal
- `{{data_recebimento}}` - Data de recebimento da NF

## ❓ Troubleshooting

### Servidor não inicia
1. Verifique se Node.js está instalado: `node --version`
2. Execute: `cd backend_example && npm install`
3. Tente iniciar manualmente: `node whatsapp_server.js`

### QR Code não aparece
1. Pare o servidor
2. Delete a pasta `.wwebjs_auth/`
3. Inicie novamente

### Mensagens não são enviadas
1. Verifique se o WhatsApp está conectado (aba Status)
2. Confirme que o número está no formato correto: `5511999999999`
3. Verifique os logs do servidor

## 🎉 Pronto!

O sistema está totalmente integrado e pronto para uso. Acesse http://localhost:8080/whatsapp e comece a enviar mensagens!
