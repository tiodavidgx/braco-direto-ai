# Sistema Interno de Upload de Notas Fiscais

## Visão Geral

O sistema foi migrado de uma API externa (`api.link.dev.br`) para um sistema interno, mantendo compatibilidade com uploads antigos.

## Arquitetura

### Fluxo de Upload

```
┌──────────────────┐      ┌─────────────────┐      ┌──────────────────┐
│ Envio Relatório  │──────│ Gera Link       │──────│ Página Upload    │
│ (relatorios.py)  │      │ (interno)       │      │ (/upload/nf/:hash)│
└──────────────────┘      └─────────────────┘      └──────────────────┘
                                                           │
                                                           ▼
┌──────────────────┐      ┌─────────────────┐      ┌──────────────────┐
│ Job Consulta     │──────│ Verifica fonte  │──────│ Processa Upload  │
│ (consultar_notas)│      │ interno/externo │      │ (upload_nf.py)   │
└──────────────────┘      └─────────────────┘      └──────────────────┘
```

## Arquivos Criados/Modificados

### Novos Arquivos

1. **`criar_tabela_uploads_nf.sql`** - Schema do banco para sistema interno
   - Tabela `uploads_nf`: Controle de links de upload
   - Tabela `uploads_nf_arquivos`: Arquivos enviados
   - View `v_uploads_pendentes`: Uploads aguardando NF
   - Função `gerar_hash_upload()`: Gera hash único

2. **`add_coluna_fonte.sql`** - Migração para compatibilidade
   - Adiciona coluna `fonte` em `lotes_servico` e `envios_montagem`
   - Valores: `'interno'`, `'api_externa'`, `NULL` (legado)

3. **`app/utils/link_upload_interno.py`** - Utilitário de links internos
   - `gerar_link_upload_interno()`: Cria link no sistema interno
   - `verificar_link_interno()`: Verifica status do link
   - `consultar_uploads_internos_pendentes()`: Lista pendentes
   - `gerar_link_upload()`: Wrapper que escolhe interno/externo

4. **`app/routes/upload_nf.py`** - API pública de upload
   - `GET /upload/nf/{hash}/info`: Informações do upload
   - `POST /upload/nf/{hash}/upload`: Enviar arquivos
   - `GET /internal/uploads/pendentes`: Lista pendentes
   - `POST /internal/uploads/criar-link`: Cria novo link

5. **`src/pages/UploadNF.tsx`** - Página pública de upload
   - Interface drag-and-drop
   - Preview de arquivos
   - Validação (10MB, PDF/XML/JPG/PNG)
   - Sem necessidade de login

### Arquivos Modificados

1. **`app/routes/relatorios.py`**
   - Usa `gerar_link_upload()` do sistema interno
   - Marca envios com `fonte='interno'`

2. **`app/jobs/consultar_notas.py`**
   - Verifica coluna `fonte` para decidir onde consultar
   - Sistema interno: consulta `uploads_nf`
   - Sistema externo: consulta `api.link.dev.br`
   - Arquivos internos são copiados, externos são baixados

3. **`app/main.py`**
   - Registra router `upload_nf`

4. **`src/App.tsx`**
   - Adiciona rota pública `/upload/nf/:hash`

## Compatibilidade

### Envios Antigos (API Externa)
- Coluna `fonte` = `NULL` ou `'api_externa'`
- Job continua consultando `api.link.dev.br`
- Download via HTTP

### Envios Novos (Sistema Interno)
- Coluna `fonte` = `'interno'`
- Job consulta tabela `uploads_nf`
- Arquivos já estão no servidor (cópia local)

## Configuração

### Variáveis de Ambiente

```bash
# URL base do frontend (para links de upload)
FRONTEND_URL=http://localhost:5173

# Em produção:
FRONTEND_URL=https://seu-dominio.com
```

### Banco de Dados

Executar os SQLs na ordem:

```bash
psql -U david -d email -f criar_tabela_uploads_nf.sql
psql -U david -d email -f add_coluna_fonte.sql
```

## Uso

### Gerar Link de Upload (Backend)

```python
from app.utils.link_upload_interno import gerar_link_upload

# Para prestador
resultado = gerar_link_upload(
    nome="João Silva",
    email="joao@email.com",
    periodo="01/2025",
    valor_total=5000.00,
    quantidade_os=10,
    lote_id=123,
    tipo='prestador',
    usar_interno=True
)

# resultado = {
#     "success": True,
#     "link": "http://localhost:5173/upload/nf/abc123...",
#     "hash": "abc123...",
#     "id_controle": 1,
#     "validade_link": "2025-02-23 10:30:00"
# }
```

### Acessar Página de Upload

O prestador/montador acessa o link recebido por email:
```
http://localhost:5173/upload/nf/abc123def456...
```

### Verificar Uploads Pendentes

```python
from app.utils.link_upload_interno import consultar_uploads_internos_pendentes

pendentes = consultar_uploads_internos_pendentes(tipo='prestador')
```

## Fluxo Completo

1. **Envio de Relatório**
   - Backend gera lote/envio
   - Gera link interno (`gerar_link_upload_interno`)
   - Marca `fonte='interno'`
   - Envia email com link

2. **Upload pelo Usuário**
   - Acessa `/upload/nf/{hash}`
   - Faz upload dos arquivos
   - Backend salva em `uploads_nf_arquivos`
   - Dispara notificações (WebSocket, WhatsApp, Trello)

3. **Job de Consulta**
   - Busca registros pendentes
   - Verifica `fonte`:
     - `'interno'`: consulta `uploads_nf`
     - outro: consulta API externa
   - Processa arquivos encontrados
   - Cria notificações

## Notas

- O sistema interno NÃO usa a coluna `validade_link` como texto; usa `data_expiracao` como timestamp
- Arquivos são salvos em `uploads/lote_{id}` ou `uploads/montagem_{id}`
- A página de upload não requer autenticação (link com hash é a autenticação)
