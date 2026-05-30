# Sistema de Agendamento de Jobs

## Visão Geral

O sistema agora possui execução automática de jobs usando **APScheduler**, permitindo configurar intervalos personalizados para execução automática da consulta de notas fiscais.

## Arquitetura

### Componentes

1. **Scheduler Integrado** (`app/scheduler.py`)
   - Gerencia agendamento de jobs
   - Usa APScheduler com BackgroundScheduler
   - Executa dentro do processo principal da API
   - Persiste configurações no banco de dados

2. **Tabela de Configuração** (`jobs_config`)
   - Armazena configurações de cada job
   - Campos: nome, descricao, ativo, intervalo_minutos
   - Estatísticas: total_execucoes, total_erros, ultima_execucao

3. **API Endpoints** (`/jobs/*`)
   - Configuração de intervalos
   - Ativação/desativação de jobs
   - Execução manual para testes
   - Consulta de status e estatísticas

4. **Interface Web** (`/jobs`)
   - Card de agendamento automático
   - Card de execução manual
   - Visualização de estatísticas em tempo real

## Funcionalidades

### Execução Automática

O job de consulta de notas fiscais pode ser configurado para executar automaticamente em intervalos regulares:

- **Intervalo Mínimo**: 1 minuto (para testes)
- **Intervalo Recomendado**: 60 minutos (1 hora)
- **Intervalo Máximo**: 1440 minutos (24 horas)

### Execução Manual

Permite executar o job imediatamente para testes ou necessidades pontuais, sem afetar o agendamento automático.

### Monitoramento

O sistema registra:
- Total de execuções
- Total de erros
- Taxa de sucesso (%)
- Última execução (data/hora)
- Última mensagem (resultados ou erro)
- Próxima execução agendada

## Como Usar

### Configurar Execução Automática

1. Acesse `http://localhost:8080/jobs`
2. No card **"Agendamento Automático"**:
   - Ative o switch "Execução Automática"
   - Configure o intervalo desejado (em minutos)
   - Clique em "Salvar Configuração"

3. O scheduler será recarregado automaticamente
4. O job começará a executar no intervalo configurado

### Executar Manualmente

1. No card **"Execução Manual"**
2. Clique em "Executar Agora"
3. Aguarde a conclusão (atualiza a cada 5 segundos)
4. Veja os resultados em tempo real

## Fluxo de Execução

```
┌─────────────────────────────────────────────────────────────┐
│                     API Inicialização                        │
│  1. init_db() - Cria tabelas                                │
│  2. iniciar_scheduler() - Inicia APScheduler                │
│  3. criar_tabela_jobs_config() - Garante tabela existe      │
│  4. configurar_jobs() - Carrega config do BD e agenda jobs  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execução Agendada                         │
│  1. APScheduler dispara no intervalo configurado            │
│  2. executar_job_consulta_notas()                           │
│  3. processar_uploads_pendentes() - Job principal           │
│  4. Consulta API → Download arquivos → Cria Trello cards    │
│  5. atualizar_estatisticas_job() - Salva resultados         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Atualização de Configuração                  │
│  1. Usuario altera intervalo ou ativa/desativa              │
│  2. PUT /jobs/config/{nome} salva no BD                     │
│  3. recarregar_scheduler() reaplica configurações           │
│  4. Jobs são reagendados com novos parâmetros               │
└─────────────────────────────────────────────────────────────┘
```

## Banco de Dados

### Tabela: jobs_config

```sql
CREATE TABLE jobs_config (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    intervalo_minutos INTEGER DEFAULT 60,
    ultima_execucao TIMESTAMP,
    proxima_execucao TIMESTAMP,
    total_execucoes INTEGER DEFAULT 0,
    total_erros INTEGER DEFAULT 0,
    ultima_mensagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Job Padrão

```sql
INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos)
VALUES (
    'consulta_notas',
    'Consulta notas fiscais na API e cria cards no Trello',
    TRUE,
    60
);
```

## Endpoints da API

### GET /jobs/status
Retorna status de execução manual e scheduler integrado.

**Response:**
```json
{
  "manual_execution": {
    "consulta_notas": {
      "running": false,
      "last_run": "2025-11-12T14:30:00",
      "last_result": { ... },
      "error": null
    }
  },
  "scheduler": {
    "running": true,
    "jobs": [
      {
        "id": "consulta_notas",
        "name": "Consulta Notas Fiscais",
        "next_run": "2025-11-12T15:30:00"
      }
    ]
  }
}
```

### GET /jobs/config
Lista configurações de todos os jobs.

**Response:**
```json
[
  {
    "id": 1,
    "nome": "consulta_notas",
    "descricao": "Consulta notas fiscais na API...",
    "ativo": true,
    "intervalo_minutos": 60,
    "ultima_execucao": "2025-11-12T14:30:00",
    "proxima_execucao": "2025-11-12T15:30:00",
    "total_execucoes": 42,
    "total_erros": 1,
    "ultima_mensagem": "Processados: 3, Arquivos: 5, Downloads: 5, Erros: 0"
  }
]
```

### PUT /jobs/config/{job_name}
Atualiza configuração de um job e recarrega o scheduler.

**Request:**
```json
{
  "ativo": true,
  "intervalo_minutos": 30
}
```

**Response:**
```json
{
  "message": "Configuração atualizada"
}
```

### POST /jobs/consulta-notas/executar
Executa o job manualmente (não afeta agendamento).

**Response:**
```json
{
  "success": true,
  "message": "Job iniciado com sucesso",
  "status": "running"
}
```

### GET /jobs/consulta-notas/resultado
Retorna resultado da última execução manual.

**Response:**
```json
{
  "status": "completed",
  "last_run": "2025-11-12T14:30:00",
  "result": {
    "total_processados": 3,
    "arquivos_encontrados": 5,
    "downloads": 5,
    "erros": 0
  },
  "error": null
}
```

## Logging

O scheduler registra todas as ações:

- **INFO**: Execuções bem-sucedidas
- **ERROR**: Falhas de execução
- **WARNING**: Configurações problemáticas

Logs são salvos em:
- Console (stdout)
- Arquivo: `scheduler.log`

### Exemplo de Log

```
2025-11-12 14:30:00 - app.scheduler - INFO - 🔄 Iniciando job de consulta de notas...
2025-11-12 14:30:15 - app.scheduler - INFO - ✅ Job concluído: Processados: 3, Arquivos: 5, Downloads: 5, Erros: 0
```

## Tratamento de Erros

### Execuções Simultâneas
- Configurado `max_instances=1` no APScheduler
- Garante que apenas 1 instância do job execute por vez
- Se job ainda está rodando, próxima execução é pulada

### Falhas de Execução
- Erros são capturados e logados
- Estatísticas são atualizadas (total_erros++)
- Mensagem de erro é salva em ultima_mensagem
- Próxima execução continua normalmente

### Reinicialização da API
- Scheduler é iniciado automaticamente
- Configurações são carregadas do banco
- Jobs são reagendados com últimos parâmetros salvos

## Boas Práticas

### Intervalos Recomendados

- **Desenvolvimento/Testes**: 5-15 minutos
- **Produção Baixo Volume**: 30-60 minutos
- **Produção Alto Volume**: 15-30 minutos
- **Monitoramento Intensivo**: 5-10 minutos

### Monitoramento

1. Verifique taxa de sucesso regularmente
2. Investigue se total_erros aumentar rapidamente
3. Configure alertas se taxa de sucesso < 95%
4. Revise última_mensagem para entender problemas

### Performance

- Job usa threading para não bloquear API
- Consultas ao banco são otimizadas
- Downloads de arquivos são sequenciais (evita sobrecarga)
- Trello attachments têm retry logic (3 tentativas)

## Troubleshooting

### Job Não Está Executando

1. Verifique se está ativo: `GET /jobs/config`
2. Confirme scheduler rodando: `GET /jobs/status`
3. Revise logs: `GET /jobs/logs` ou arquivo `scheduler.log`
4. Teste execução manual para isolar problema

### Erros Frequentes

1. Verifique credenciais Trello em `/integracoes`
2. Confirme API externa está respondendo
3. Valide que lotes têm upload_hash preenchido
4. Revise permissões de diretório `uploads/`

### Scheduler Não Inicia

1. Verifique se APScheduler está instalado: `pip list | grep APScheduler`
2. Revise logs de inicialização do backend
3. Confirme banco de dados está acessível
4. Valide tabela jobs_config existe

## Atualizações Futuras

Funcionalidades planejadas:

- [ ] Múltiplos jobs (backup, limpeza, relatórios)
- [ ] Notificações por email quando job falha
- [ ] Dashboard com gráficos de execução
- [ ] Histórico completo de execuções (tabela jobs_execucoes)
- [ ] Retry automático em caso de falha
- [ ] Modo manutenção (pausar todos os jobs)
- [ ] API webhooks para integração externa
