# 📧 Sistema Completo de Envio de Relatórios

## 🎯 Visão Geral

Sistema completo para envio de relatórios de prestadores e montadores com:
- ✅ **Lançamento Manual** - Adicionar OS/montagens linha por linha
- ✅ **Importação Excel** - Upload de planilha completa
- ✅ **Edição em Tabela** - Modificar dados antes do envio
- ✅ **Envio de Email** - PDF anexo + link de upload NF
- ✅ **Notificação WhatsApp** - Mensagem automática
- ✅ **Histórico Completo** - Por prestador/montador

---

## 📊 Frontend: Estrutura da Página

### Componentes Principais

```typescript
// src/pages/EnvioRelatorios.tsx

1. Seletor de Tipo (Prestador/Montador)
2. Três Abas:
   - Lançamento Manual
   - Importar Excel  
   - Histórico
3. Tabela Editável
4. Configurações de Email
5. Checkbox WhatsApp
6. Botão de Envio
```

### Fluxo de Uso

```
1. Usuário seleciona Prestador ou Montador
2. Escolhe entre:
   a) Lançamento Manual → Adiciona linhas uma por uma
   b) Importar Excel → Faz upload de planilha
3. Sistema mostra preview dos dados
4. Usuário pode editar qualquer campo
5. Configura email (assunto, corpo, CC)
6. Marca/desmarca envio WhatsApp
7. Clica em "Enviar N Relatórios"
8. Sistema:
   - Agrupa por prestador/montador + período
   - Gera PDFs
   - Envia emails
   - Envia WhatsApp (se marcado)
   - Salva histórico
```

---

## 📤 Backend: Processamento de Envio em Lote

### Endpoint: POST `/api/v1/relatorios/enviar-lote`

```python
# backend/app/routes/relatorios.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
from datetime import datetime

router = APIRouter()

class ItemManual(BaseModel):
    os_numero: str = None
    boletim: str = None
    cliente: str
    localidade: str = None
    modalidade: str = None
    produto: str = None
    data_execucao: str
    valor: float
    valor_extra: float = 0
    comissao: float = 0

class EmailConfig(BaseModel):
    cc: str
    assunto: str
    corpo: str

class EnvioLoteRequest(BaseModel):
    tipo: str  # 'prestador' ou 'montador'
    dados: List[ItemManual]
    emailConfig: EmailConfig
    enviarWhatsApp: bool = True

@router.post("/enviar-lote")
async def enviar_relatorios_lote(request: EnvioLoteRequest):
    """
    Processa envio em lote de relatórios
    
    Fluxo:
    1. Recebe dados (manual ou Excel)
    2. Agrupa por prestador/montador + período
    3. Para cada grupo:
       - Gera PDF
       - Envia email
       - Envia WhatsApp (se habilitado)
       - Salva no banco
    4. Retorna relatório de sucesso/erro
    """
    
    from app.database import get_db_connection
    from app.services.pdf_service import gerar_pdf_relatorio
    from app.services.email_service import enviar_email
    from app.services.whatsapp_service import enviar_whatsapp
    import psycopg2.extras
    
    # Converter dados para DataFrame para facilitar agrupamento
    df = pd.DataFrame([item.dict() for item in request.dados])
    
    # Determinar coluna de agrupamento baseado no tipo
    if request.tipo == 'prestador':
        # Buscar nome do prestador baseado na OS (assumindo que OS tem identificação)
        # Você pode adicionar um campo 'nome_prestador' nos dados
        grupo_col = 'nome_prestador'
        item_col = 'os_numero'
    else:
        # Para montador, agrupar por identificador
        grupo_col = 'nome_montador'
        item_col = 'boletim'
    
    # Extrair período automaticamente das datas
    df['data_execucao'] = pd.to_datetime(df['data_execucao'])
    
    relatorio_envio = []
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Agrupar por entidade
        for nome_entidade, grupo in df.groupby(grupo_col):
            try:
                # Calcular período
                data_min = grupo['data_execucao'].min()
                data_max = grupo['data_execucao'].max()
                periodo = f"{data_min.strftime('%d/%m/%Y')} - {data_max.strftime('%d/%m/%Y')}"
                
                # Calcular total
                valor_total = grupo['valor'].sum() + grupo['valor_extra'].sum()
                
                if request.tipo == 'prestador':
                    # Buscar prestador
                    cur.execute(
                        "SELECT * FROM prestadores WHERE nome = %s",
                        (nome_entidade,)
                    )
                    entidade = cur.fetchone()
                    
                    if not entidade:
                        relatorio_envio.append({
                            "nome": nome_entidade,
                            "status": "❌ Prestador não encontrado",
                            "erro": True
                        })
                        continue
                    
                    # Criar lote
                    cur.execute("""
                        INSERT INTO lotes_servico 
                        (prestador_id, prestador_nome, periodo, valor_total, data_envio, status)
                        VALUES (%s, %s, %s, %s, NOW(), 'Em Aberto')
                        RETURNING id
                    """, (entidade['id'], nome_entidade, periodo, valor_total))
                    
                    lote_id = cur.fetchone()['id']
                    
                    # Salvar OS
                    for _, row in grupo.iterrows():
                        detalhes = row.to_dict()
                        # Converter timestamps para strings
                        detalhes['data_execucao'] = detalhes['data_execucao'].isoformat()
                        
                        cur.execute("""
                            INSERT INTO os_enviadas (lote_id, os_numero, detalhes)
                            VALUES (%s, %s, %s)
                        """, (lote_id, row[item_col], json.dumps(detalhes)))
                    
                    # Gerar PDF
                    pdf_path = gerar_pdf_relatorio(
                        template='invoice_template.html',
                        data={
                            'nome_prestador': nome_entidade,
                            'periodo': periodo,
                            'lote_id': lote_id,
                            'items': grupo.to_dict('records'),
                            'total_geral': valor_total
                        },
                        output_path=f'/tmp/relatorio_prestador_{lote_id}.pdf'
                    )
                    
                else:  # montador
                    # Buscar montador
                    cur.execute(
                        "SELECT * FROM montadores WHERE nome = %s",
                        (nome_entidade,)
                    )
                    entidade = cur.fetchone()
                    
                    if not entidade:
                        relatorio_envio.append({
                            "nome": nome_entidade,
                            "status": "❌ Montador não encontrado",
                            "erro": True
                        })
                        continue
                    
                    # Calcular comissões
                    grupo['comissao'] = grupo['valor'] * (entidade['percentual_comissao'] / 100)
                    total_comissao = grupo['comissao'].sum()
                    
                    # Criar envio de montagem
                    detalhes = {
                        'periodo_relatorio': periodo,
                        'items': grupo.to_dict('records'),
                        'total_comissao': total_comissao
                    }
                    
                    cur.execute("""
                        INSERT INTO envios_montagem 
                        (montador_id, montador_nome, periodo, data_envio, status, detalhes, valor_total)
                        VALUES (%s, %s, %s, NOW(), 'Em Aberto', %s, %s)
                        RETURNING id
                    """, (
                        entidade['id'],
                        nome_entidade,
                        periodo,
                        json.dumps(detalhes),
                        total_comissao
                    ))
                    
                    envio_id = cur.fetchone()['id']
                    
                    # Gerar PDF
                    pdf_path = gerar_pdf_relatorio(
                        template='montador_template.html',
                        data={
                            'nome_montador': nome_entidade,
                            'periodo_relatorio': periodo,
                            'percentual_comissao': entidade['percentual_comissao'],
                            'items': grupo.to_dict('records'),
                            'total_comissoes': total_comissao
                        },
                        output_path=f'/tmp/relatorio_montador_{envio_id}.pdf'
                    )
                
                # Preparar email
                from jinja2 import Template
                
                assunto = Template(request.emailConfig.assunto).render(
                    periodo=periodo,
                    nome_prestador=nome_entidade,
                    nome_montador=nome_entidade,
                    valor_total=valor_total
                )
                
                corpo = Template(request.emailConfig.corpo).render(
                    periodo=periodo,
                    nome_prestador=nome_entidade,
                    nome_montador=nome_entidade,
                    valor_total=valor_total,
                    link_upload="[Link será gerado automaticamente]"
                )
                
                # Enviar email
                enviar_email(
                    destinatario=entidade['email'],
                    assunto=assunto,
                    corpo_html=f"<p>{corpo.replace(chr(10), '<br>')}</p>",
                    pdf_path=pdf_path,
                    cc=request.emailConfig.cc.split(',') if request.emailConfig.cc else []
                )
                
                # Enviar WhatsApp (se habilitado)
                if request.enviarWhatsApp and entidade.get('telefone'):
                    enviar_whatsapp(
                        numero=entidade['telefone'],
                        mensagem=f"Olá! Seu relatório de {periodo} foi enviado por email. Valor: R$ {valor_total:.2f}",
                        media_path=pdf_path
                    )
                
                relatorio_envio.append({
                    "nome": nome_entidade,
                    "status": f"✅ Enviado (Lote #{lote_id if request.tipo == 'prestador' else envio_id})",
                    "erro": False,
                    "valor": valor_total
                })
                
            except Exception as e:
                relatorio_envio.append({
                    "nome": nome_entidade,
                    "status": f"❌ Erro: {str(e)}",
                    "erro": True
                })
    
    return {
        "sucesso": len([r for r in relatorio_envio if not r['erro']]),
        "erros": len([r for r in relatorio_envio if r['erro']]),
        "detalhes": relatorio_envio
    }
```

---

## 📋 Estrutura de Planilha Excel

### Para Prestadores

| nome_prestador | periodo | o_s | cliente | localidade | modalidade | data_execucao | valor_custo_prestador | valor_extra | motivo_extra |
|---|---|---|---|---|---|---|---|---|---|
| Prestadora ABC | 01/11 - 07/11 | OS001 | Cliente A | São Paulo | Instalação | 05/11/2025 | 500.00 | 50.00 | Hora extra |
| Prestadora ABC | 01/11 - 07/11 | OS002 | Cliente B | São Paulo | Reparo | 06/11/2025 | 350.00 | 0 | - |

**Colunas Obrigatórias:**
- `nome_prestador`
- `periodo`
- `o_s` (número da OS)
- `data_execucao`

### Para Montadores

| identificador_do_montador | identificador_boletim_montagem | data_da_montagem | media_de_valor_venda | nome_do_cliente | nome_produto |
|---|---|---|---|---|---|
| MONT001 | BOL001 | 05/11/2025 | 1500.00 | Cliente A | Cama Box |
| MONT001 | BOL002 | 06/11/2025 | 2000.00 | Cliente B | Guarda-Roupa |

**Colunas Obrigatórias:**
- `identificador_do_montador`
- `identificador_boletim_montagem`
- `data_da_montagem`
- `media_de_valor_venda`

---

## 🔄 Integração WhatsApp

```python
# app/services/whatsapp_service.py

import requests

def enviar_whatsapp(numero: str, mensagem: str, media_path: str = None):
    """
    Envia mensagem via WhatsApp
    Integração com whatsapp-web.js
    """
    
    payload = {
        "number": numero.replace("-", "").replace(" ", ""),
        "message": mensagem
    }
    
    if media_path:
        payload["media_path"] = media_path
    
    response = requests.post(
        "http://localhost:3000/send",
        json=payload
    )
    
    return response.status_code == 200
```

---

## 📊 Histórico de Envios

### Endpoint: GET `/api/v1/relatorios/historico`

```python
@router.get("/historico")
def obter_historico(tipo: str = "prestador", limite: int = 50):
    """Lista histórico de envios"""
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == 'prestador':
            cur.execute("""
                SELECT 
                    l.id,
                    l.prestador_nome as nome,
                    l.periodo,
                    l.valor_total,
                    l.data_envio,
                    l.status,
                    COUNT(o.id) as quantidade_os
                FROM lotes_servico l
                LEFT JOIN os_enviadas o ON o.lote_id = l.id
                GROUP BY l.id
                ORDER BY l.data_envio DESC
                LIMIT %s
            """, (limite,))
        else:
            cur.execute("""
                SELECT 
                    id,
                    montador_nome as nome,
                    periodo,
                    valor_total,
                    data_envio,
                    status,
                    quantidade_os
                FROM envios_montagem
                ORDER BY data_envio DESC
                LIMIT %s
            """, (limite,))
        
        return {"historico": cur.fetchall()}
```

---

## ✅ Checklist de Implementação

### Frontend
- [x] Página de envio de relatórios
- [x] Lançamento manual com tabela editável
- [x] Upload e leitura de Excel
- [x] Preview de dados
- [x] Configuração de email
- [x] Checkbox WhatsApp
- [x] Histórico de envios

### Backend
- [ ] Endpoint de envio em lote
- [ ] Processamento de agrupamento
- [ ] Geração de PDFs em lote
- [ ] Envio de emails em massa
- [ ] Integração WhatsApp
- [ ] Histórico por entidade
- [ ] Validação de OS/boletins duplicados

---

## 🆘 Troubleshooting

### Planilha não carrega
- Verificar formato (.xlsx ou .xls)
- Verificar nomes das colunas
- Colunas podem ter espaços e acentos (são normalizadas automaticamente)

### Email não envia
- Verificar token Microsoft Graph
- Verificar permissões Mail.Send
- Verificar email do prestador/montador no banco

### WhatsApp não envia
- Verificar se serviço WhatsApp está rodando (localhost:3000)
- Verificar telefone cadastrado
- Telefone deve estar no formato: 5511999999999

---

**Sistema Braço Direito** - Novo Mundo 🤝
