# Sistema de Notificações em Tempo Real

## 🎯 Funcionalidades Implementadas

Sistema de notificações flutuantes usando WebSocket que exibe alertas em tempo real quando:

1. **📄 Nota Fiscal Recebida** - Quando um prestador ou montador envia a NF via upload
2. **🔗 Integração com Trello** - Quando um card é criado no Trello automaticamente

## 🏗️ Arquitetura

### Backend

**Arquivo: `app/routes/notifications.py`**
- WebSocket endpoint: `/api/v1/ws/notifications`
- Classe `NotificationManager` para gerenciar conexões
- Método `send_notification()` para broadcast de mensagens

**Arquivo: `app/routes/upload_api.py`**
- Webhook `/api/v1/upload/webhook/nf-recebida`
- Recebe notificação da API externa quando NF é enviada
- Atualiza banco de dados e envia notificação em tempo real

**Arquivo: `app/services/trello_service.py`**
- Método `criar_card_download()` modificado
- Envia notificação quando card é criado no Trello

### Frontend

**Arquivo: `src/components/NotificationToast.tsx`**
- Componente individual de notificação flutuante
- Animações de entrada/saída
- Auto-close após 5 segundos
- Barra de progresso visual
- Ícones coloridos por tipo (success, info, warning, error)

**Arquivo: `src/components/NotificationContainer.tsx`**
- Container principal de notificações
- Gerencia conexão WebSocket
- Reconexão automática em caso de queda
- Mantém conexão viva com ping/pong
- Som sutil para cada notificação (opcional)

**Arquivo: `src/App.tsx`**
- `NotificationContainer` adicionado globalmente
- Disponível em todas as páginas

**Arquivo: `tailwind.config.ts`**
- Animação `animate-progress` para barra de progresso

## 🚀 Como Testar

### 1. Testar Conexão WebSocket

Abra o console do navegador e verifique:
```
✅ Conectado ao servidor de notificações
```

### 2. Testar Manualmente (Python)

Execute no backend:

```python
# No terminal do backend
cd backend_example
source venv/bin/activate
python

# No Python REPL
import asyncio
from app.routes.notifications import notification_manager

# Enviar notificação de teste
asyncio.run(notification_manager.send_notification(
    tipo="success",
    titulo="📄 Teste de Notificação",
    mensagem="Esta é uma notificação de teste!",
    dados={"teste": True}
))
```

### 3. Testar Upload de NF

1. Configure a API de upload em Integrações
2. Envie um relatório (prestador ou montador)
3. Simule o webhook de recebimento de NF:

```bash
curl -X POST http://localhost:8000/api/v1/upload/webhook/nf-recebida \
  -H "Content-Type: application/json" \
  -d '{
    "lote_id": 123,
    "tipo": "lote",
    "hash": "abc123",
    "nota_fiscal": "NF_TESTE_001.pdf",
    "data_upload": "2025-11-13T10:30:00"
  }'
```

Você verá uma notificação verde flutuante:
```
📄 Nota Fiscal Recebida
João Silva enviou a NF do período 11/2025
```

### 4. Testar Integração Trello

1. Configure o Trello em Integrações
2. Execute um job que cria cards no Trello
3. Quando o card for criado, verá notificação azul:

```
🔗 Integrado no Trello
Prestador João Silva - Lote #123
[Ver card no Trello →]
```

## 📋 Tipos de Notificação

| Tipo | Cor | Ícone | Uso |
|------|-----|-------|-----|
| `success` | Verde | ✓ | NF recebida, operação concluída |
| `info` | Azul | ℹ | Integração Trello, informações |
| `warning` | Amarelo | ⚠ | Avisos, atenção necessária |
| `error` | Vermelho | ✕ | Erros, falhas |

## 🎨 Características Visuais

- ✅ Posicionamento: canto superior direito
- ✅ Animação de slide-in pela direita
- ✅ Auto-close após 5 segundos
- ✅ Barra de progresso animada
- ✅ Cores diferentes por tipo
- ✅ Link clicável para card do Trello
- ✅ Formatação de valores em BRL
- ✅ Som sutil ao receber (opcional)
- ✅ Botão de fechar manual
- ✅ Empilhamento de múltiplas notificações

## 🔧 Configuração

### WebSocket URL

Frontend conecta em:
```
ws://localhost:8000/api/v1/ws/notifications
```

Para produção, alterar em `src/components/NotificationContainer.tsx`:
```typescript
const WS_URL = 'wss://seu-dominio.com/api/v1/ws/notifications';
```

### Webhook da API Externa

Configure a API externa para chamar:
```
POST http://seu-dominio.com/api/v1/upload/webhook/nf-recebida
```

## 🐛 Troubleshooting

### Notificações não aparecem

1. Verifique console do navegador:
   - Deve mostrar "✅ Conectado ao servidor de notificações"
   
2. Verifique backend está rodando:
   ```bash
   curl http://localhost:8000/health
   ```

3. Verifique logs do backend para erros no WebSocket

### Reconexão não funciona

- O sistema tenta reconectar a cada 5 segundos automaticamente
- Verifique se o backend não está bloqueando conexões WebSocket
- Em produção, configure proxy reverso (nginx) para WebSocket

### Som não toca

- Navegadores modernos bloqueiam áudio automático
- Usuário precisa interagir com página primeiro
- Som é opcional e falha silenciosamente se bloqueado

## 📊 Dados da Notificação

Estrutura JSON recebida via WebSocket:

```typescript
{
  tipo: 'success' | 'info' | 'warning' | 'error';
  titulo: string;
  mensagem: string;
  timestamp: string; // ISO format
  dados?: {
    lote_id?: number;
    tipo?: string;
    nome?: string;
    periodo?: string;
    valor?: number;
    nota_fiscal?: string;
    card_url?: string;
  };
}
```

## 🎯 Próximos Passos (Opcional)

- [ ] Histórico de notificações (salvar em banco)
- [ ] Centro de notificações (ver todas)
- [ ] Preferências de notificação por usuário
- [ ] Notificações push do navegador
- [ ] Badge de contador na sidebar
- [ ] Som personalizável
- [ ] Filtros de notificação
- [ ] Marca como lida/não lida
