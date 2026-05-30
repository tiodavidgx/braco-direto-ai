# WhatsApp Service

Serviço Node.js para integração com WhatsApp Web usando whatsapp-web.js

## Instalação

```bash
cd whatsapp-service
npm install
```

## Uso

```bash
npm start
```

O serviço será iniciado em `http://localhost:3000`

## Endpoints

- `GET /` - Página inicial com status
- `GET /status` - Status da conexão (JSON)
- `GET /info` - Informações do usuário conectado
- `GET /qr` - Visualizar QR Code para autenticação
- `POST /send` - Enviar mensagem individual
- `POST /send-bulk` - Enviar mensagens em massa
- `POST /disconnect` - Desconectar WhatsApp

## Como Conectar

1. Inicie o serviço: `npm start`
2. Acesse: http://localhost:3000/qr
3. Escaneie o QR Code com WhatsApp
4. Aguarde a mensagem "WhatsApp conectado e pronto!"

## Exemplos de Uso

### Enviar Mensagem Individual

```bash
curl -X POST http://localhost:3000/send \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "message": "Olá! Mensagem de teste."
  }'
```

### Enviar Mensagens em Massa

```bash
curl -X POST http://localhost:3000/send-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "numbers": ["5511999999999", "5511988888888"],
    "message": "Mensagem para todos!",
    "delay": 3000
  }'
```

## Notas

- O serviço mantém a sessão autenticada em `./.wwebjs_auth`
- Não é necessário escanear o QR Code toda vez, apenas na primeira vez
- O delay padrão entre mensagens em massa é 3000ms (3 segundos)
