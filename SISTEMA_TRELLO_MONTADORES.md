# Sistema de Trello para Montadores

## ✅ Implementação Completa

Sistema automático que processa montadores, baixa arquivos da API e cria cards no Trello com anexos.

---

## 🎯 Funcionalidades

### 1. Script Standalone
- **Arquivo**: `sistema_original/criar_cards_trello_montadores.py`
- **Função**: Processa montadores sem cards Trello
- **Ações**:
  - Consulta API para cada montador
  - Baixa arquivos para `uploads/montagem_{id}/`
  - Cria card no Trello com anexos
  - Salva referência na tabela `trello_cards`
  - **Envia notificação WebSocket em tempo real** 🔔

### 2. Endpoint API Backend
- **POST** `/api/v1/jobs/trello-montadores/executar` - Executa job manualmente
- **GET** `/api/v1/jobs/trello-montadores/resultado` - Retorna resultado da última execução

### 3. Interface Web (Jobs)
- Acesse: `http://localhost:8080/jobs`
- Card **"Cards Trello - Montadores"**
- Botão "Processar Montadores"
- Visualização de logs em tempo real

### 4. Scheduler Automático
- Executa a cada **15 minutos** (configurável)
- Gerenciado por `backend_example/app/scheduler.py`
- Job: `trello_montadores`

---

## 🚀 Como Usar

### Execução Manual (Via Interface)

1. Acesse `http://localhost:8080/jobs`
2. Localize o card **"Cards Trello - Montadores"**
3. Clique em **"Processar Montadores"**
4. Acompanhe o progresso em tempo real

### Execução Manual (Via Terminal)

```bash
cd /Users/david/Documents/GitHub/braco-direto-ai/sistema_original
python3 criar_cards_trello_montadores.py
```

### Execução Manual (Via API)

```bash
curl -X POST http://localhost:8000/api/v1/jobs/trello-montadores/executar
```

---

## ⚙️ Configuração do Scheduler

### Ativar/Desativar Job

```sql
UPDATE jobs_config 
SET ativo = TRUE 
WHERE nome = 'trello_montadores';
```

### Alterar Intervalo

```sql
UPDATE jobs_config 
SET intervalo_minutos = 10 
WHERE nome = 'trello_montadores';
```

Depois, recarregue o scheduler via interface ou:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/scheduler/reload
```

---

## 📊 Banco de Dados

### Tabela `jobs_config`

```sql
SELECT * FROM jobs_config WHERE nome = 'trello_montadores';
```

Campos:
- `ativo` - Job está ativo?
- `intervalo_minutos` - Intervalo de execução (padrão: 15 min)
- `ultima_execucao` - Timestamp da última execução
- `total_execucoes` - Contador de execuções
- `total_erros` - Contador de erros

### Tabela `trello_cards`

```sql
SELECT * FROM trello_cards WHERE tipo = 'montador';
```

Campos:
- `lote_id` - ID do envio (100000+)
- `card_id` - ID do card no Trello
- `card_url` - URL do card
- `tipo` - 'montador' ou 'prestador'

---

## 🔔 Notificações

### Como Funcionam

1. Montador anexa arquivo via link
2. Job detecta novo arquivo
3. Cria card no Trello
4. **Envia notificação WebSocket**
5. Frontend exibe toast flutuante

### Webhook Endpoint

```
POST http://localhost:8000/api/v1/webhook/nota-fiscal-recebida
```

Payload:
```json
{
  "lote_id": 100013,
  "tipo": "montador",
  "nome": "DAVID DIAS",
  "data_upload": "2025-11-14T16:33:58"
}
```

---

## 📁 Estrutura de Arquivos

```
sistema_original/
├── criar_cards_trello_montadores.py  ← Script principal
├── consulta_nf_client.py            ← Cliente API
├── trello_integration.py            ← Integração Trello
└── database.py                      ← Funções de banco

backend_example/app/
├── scheduler.py                     ← Scheduler automático
└── routes/
    └── jobs.py                      ← Endpoints API

uploads/
└── montagem_{id}/                   ← Arquivos baixados
    └── *.png, *.pdf, etc.
```

---

## 🔍 Logs e Debugging

### Logs do Scheduler

```bash
tail -f backend_example/scheduler.log
```

### Logs do Script

Executar manualmente e ver output:
```bash
python3 sistema_original/criar_cards_trello_montadores.py
```

### Verificar Status

```bash
curl http://localhost:8000/api/v1/jobs/status
```

---

## ✨ Diferenças vs Prestadores

| Característica | Prestadores | Montadores |
|---------------|-------------|------------|
| Job | `consulta_notas` | `trello_montadores` |
| Intervalo Padrão | 60 min | 15 min |
| IDs | 1, 2, 3... | 100000+ |
| Pasta Upload | `lote_{id}` | `montagem_{id}` |
| Tabela Principal | `lotes_servico` | `envios_montagem` |
| Campo Tipo | `'prestador'` | `'montador'` |

---

## 🎉 Teste de Funcionamento

### 1. Criar Envio Teste

1. Acesse `http://localhost:8080/envio-montadores`
2. Preencha dados do montador
3. Gere PDF
4. Clique em "Enviar"
5. Copie o link gerado

### 2. Anexar Arquivo

1. Abra o link em navegador
2. Faça upload de arquivo
3. Aguarde processamento

### 3. Verificar Criação do Card

**Opção 1 - Automático (aguardar até 15 min)**
- Aguarde próxima execução do scheduler

**Opção 2 - Manual (imediato)**
- Acesse `http://localhost:8080/jobs`
- Clique "Processar Montadores"
- OU execute: `python3 sistema_original/criar_cards_trello_montadores.py`

### 4. Verificar Notificação

- Você deve ver um toast flutuante no canto da tela
- Mensagem: "Nova nota fiscal recebida - NOME DO MONTADOR"

### 5. Verificar Card no Trello

- Acesse seu board do Trello
- Card deve ter:
  - ✅ Label verde
  - 📎 Arquivo anexado
  - ☑️ Checklist com item do arquivo

---

## 🐛 Troubleshooting

### Notificações não aparecem

1. Verificar WebSocket conectado (console do navegador)
2. Verificar backend rodando na porta 8000
3. Verificar endpoint webhook: `POST /api/v1/webhook/nota-fiscal-recebida`

### Cards não são criados

1. Verificar Trello configurado: `SELECT * FROM integracoes WHERE tipo = 'trello'`
2. Verificar credenciais válidas
3. Executar script manual para ver logs detalhados

### Job não executa automaticamente

1. Verificar scheduler rodando: `curl http://localhost:8000/api/v1/jobs/scheduler/status`
2. Verificar job ativo: `SELECT * FROM jobs_config WHERE nome = 'trello_montadores'`
3. Verificar logs: `tail -f backend_example/scheduler.log`

---

## 📝 Notas Importantes

- ✅ Sistema completo e funcional
- ✅ Notificações em tempo real implementadas
- ✅ Interface web para controle manual
- ✅ Scheduler automático configurado
- ✅ Logs detalhados para debugging
- ✅ Integração idêntica aos prestadores (mas funcionando!)

## 🎯 Próximos Passos (Opcional)

1. Investigar por que `job_consultar_notas.py` falha para montadores
2. Consolidar em um único job (prestadores + montadores)
3. Adicionar filtros na interface para montadores vs prestadores
4. Dashboard de estatísticas de processamento

---

**Sistema implementado e testado com sucesso! 🎉**
