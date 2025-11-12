"""
Rotas de Relatórios e Envio de Email
Gera PDFs e envia por email usando Microsoft Graph API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import requests
from jinja2 import Template
from pathlib import Path
import base64
from datetime import datetime
from app.routes.auth import get_valid_access_token
from xhtml2pdf import pisa
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

router = APIRouter()

# Modelos
class EnvioRelatorioRequest(BaseModel):
    id: int
    tipo: str  # 'prestador' ou 'montador'

# Configuração Microsoft Graph
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

def check_os_sent(os_numbers):
    """
    Verifica quais O.S. já foram enviadas anteriormente
    
    Args:
        os_numbers: Lista de números de O.S.
    
    Returns:
        Lista de números de O.S. que já foram enviadas
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if not os_numbers:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT os_numero 
                FROM os_enviadas 
                WHERE os_numero = ANY(%s)
            """, (os_numbers,))
            
            sent_os = [row['os_numero'] for row in cur.fetchall()]
    
    return sent_os

def check_os_blacklist(os_numbers):
    """
    Verifica quais O.S. estão na blacklist
    
    Args:
        os_numbers: Lista de números de O.S.
    
    Returns:
        Lista de números de O.S. que estão na blacklist
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if not os_numbers:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT os_numero 
                FROM os_blacklist 
                WHERE os_numero = ANY(%s)
            """, (os_numbers,))
            
            blacklisted_os = [row['os_numero'] for row in cur.fetchall()]
    
    return blacklisted_os

def check_boletins_sent(boletins):
    """
    Verifica quais boletins já foram enviados anteriormente
    
    Args:
        boletins: Lista de identificadores de boletim
    
    Returns:
        Lista de boletins que já foram enviados
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if not boletins:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # No sistema original, boletins são armazenados no campo JSONB detalhes
            # Procurar nos detalhes de envios_montagem
            sent_boletins = []
            for boletim in boletins:
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM envios_montagem
                    WHERE detalhes @> %s
                """, (psycopg2.extras.Json({"items": [{"boletim": boletim}]}),))
                
                result = cur.fetchone()
                if result and result['count'] > 0:
                    sent_boletins.append(boletim)
            
            return sent_boletins

def check_boletins_blacklist(boletins):
    """
    Verifica quais boletins estão na blacklist
    
    Args:
        boletins: Lista de identificadores de boletim
    
    Returns:
        Lista de boletins que estão na blacklist
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if not boletins:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT boletim 
                FROM boletins_blacklist 
                WHERE boletim = ANY(%s)
            """, (boletins,))
            
            blacklisted_boletins = [row['boletim'] for row in cur.fetchall()]
    
    return blacklisted_boletins

# === ENDPOINTS DE VERIFICAÇÃO ===

@router.post("/verificar-os-enviadas")
def verificar_os_enviadas(request: dict):
    """
    Endpoint para verificar quais O.S. já foram enviadas
    
    Body:
        {
            "os_numbers": ["H55491", "H55498", ...]
        }
    
    Returns:
        Lista de números de O.S. que já foram enviadas
    """
    os_numbers = request.get('os_numbers', [])
    if not os_numbers:
        return []
    
    sent_os = check_os_sent(os_numbers)
    return sent_os

@router.post("/verificar-boletins-enviados")
def verificar_boletins_enviados(request: dict):
    """
    Endpoint para verificar quais boletins já foram enviados
    
    Body:
        {
            "boletins": ["H55491", "H55498", ...]
        }
    
    Returns:
        Lista de boletins que já foram enviados
    """
    boletins = request.get('boletins', [])
    if not boletins:
        return []
    
    sent_boletins = check_boletins_sent(boletins)
    return sent_boletins

def gerar_pdf_prestador(lote_data):
    """
    Gera PDF com design minimalista e profissional
    Layout clean, sem excessos, foco na informação
    """
    
    logo_path = Path(__file__).parent.parent / 'templates' / 'LOGO-NOVO-MUNDO-PEQUENA.png'
    
    # Pegar items
    os_list = lote_data.get('items', lote_data.get('os_list', []))
    
    # Formatar items
    items_fmt = []
    
    for item in os_list:
        data_exec = item.get('data_execucao')
        
        # Formatar data
        if hasattr(data_exec, 'strftime'):
            data_exec_str = data_exec.strftime('%d/%m/%Y')
        elif isinstance(data_exec, str):
            data_exec_str = data_exec
        else:
            data_exec_str = str(data_exec)
        
        items_fmt.append({
            "OS": item.get('o_s', item.get('OS', '')),
            "Cliente": item.get('cliente', item.get('Cliente', '-')),
            "Localidade": item.get('localidade', item.get('Localidade', '-')),
            "Modalidade": item.get('modalidade', item.get('Modalidade', '')),
            "Data_execucao": data_exec_str,
            "Valor": float(item.get('valor_custo_prestador', item.get('valor', 0))),
            "Valor_extra": float(item.get('valor_extra', 0)),
            "Motivo_valor_extra": item.get("motivo_extra", item.get("motivo_valor_extra", "-")),
            "Valor_total": float(item.get('valor_total', 0))
        })
    
    # Dados do relatório
    nome_prestador = lote_data.get('nome_prestador', 'N/A')
    periodo = lote_data.get('periodo', 'N/A')
    lote_id = lote_data.get('lote_id', 'N/A')
    total_geral = float(lote_data.get('total_geral', 0))
    
    # Criar PDF simples e clean
    pdf_path = f"/tmp/relatorio_prestador_{lote_id}.pdf"
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(A4),
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # === HEADER SIMPLES ===
    
    # Título principal - limpo
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Normal'],
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=colors.black,
        spaceAfter=15,
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph('RELATÓRIO DE FECHAMENTO PARA FATURAMENTO', titulo_style))
    
    # Info do prestador - uma linha só
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica',
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    info_text = f'Prestador: {nome_prestador} • Período: {periodo} • Lote: #{lote_id}'
    elements.append(Paragraph(info_text, info_style))
    
    # === TABELA CLEAN ===
    
    # Headers
    table_data = [[
        'O.S',
        'Cliente',
        'Localidade',
        'Modalidade de Serviço',
        'Data',
        'Valor (R$)',
        'Extra (R$)',
        'Motivo Extra',
        'Total (R$)'
    ]]
    
    # Adicionar dados
    for item in items_fmt:
        table_data.append([
            item['OS'],
            item['Cliente'],
            item['Localidade'],
            item['Modalidade'],
            item['Data_execucao'],
            f"{item['Valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"{item['Valor_extra']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            item['Motivo_valor_extra'],
            f"{item['Valor_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        ])
    
    # Larguras otimizadas
    col_widths = [18*mm, 35*mm, 28*mm, 60*mm, 20*mm, 25*mm, 25*mm, 35*mm, 25*mm]
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header clean
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Body clean
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # OS
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Data
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),  # Valores
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Bordas mínimas
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        
        # Linhas alternadas sutis
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
        
        # Padding consistente
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # === TOTAL CLEAN ===
    
    total_style = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.black,
        alignment=TA_RIGHT
    )
    
    total_formatado = f"{total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    elements.append(Paragraph(f'TOTAL GERAL: R$ {total_formatado}', total_style))
    
    # Logo no final se existir
    if logo_path.exists():
        elements.append(Spacer(1, 15))
        img = Image(str(logo_path), width=60, height=30)
        img.hAlign = 'RIGHT'
        elements.append(img)
    
    # Gerar PDF
    doc.build(elements)
    
    return pdf_path

def gerar_pdf_montador(envio_data):
    """
    Gera PDF do relatório de montador EXATAMENTE como no sistema original
    Usa xhtml2pdf com logo base64 (weasyprint não funciona no macOS sem bibliotecas do sistema)
    """
    
    template_path = Path(__file__).parent.parent / 'templates' / 'montador_template.html'
    logo_path = Path(__file__).parent.parent / 'templates' / 'LOGO-NOVO-MUNDO-PEQUENA.png'
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = Template(f.read())
    
    # Preparar dados EXATAMENTE como no original
    detalhes = envio_data.get('detalhes', envio_data)  # Se detalhes não existe, usar envio_data diretamente
    items_raw = detalhes.get('itens', detalhes.get('items', []))
    
    # Formatar items para o template
    items_para_pdf = []
    for item in items_raw:
        items_para_pdf.append({
            'boletim': item.get('boletim', item.get('identificador_boletim_montagem', '')),
            'data_montagem': item.get('data_montagem', item.get('data_da_montagem', '-')),
            'cliente': item.get('cliente', item.get('nome_do_cliente', '-')),
            'nome_produto': item.get('nome_produto', '-'),
            'valor_venda': float(item.get('valor_venda', item.get('media_de_valor_venda', 0))),
            'comissao_calculada': float(item.get('comissao_calculada', item.get('comissao', 0))),
            'comissao_editada': item.get('comissao_editada'),
            'adicional': float(item.get('adicional', 0))
        })
    
    # Contexto EXATAMENTE como no original
    ctx = {
        "nome_montador": envio_data.get('nome_montador', envio_data.get('montador_nome', 'N/A')),
        "periodo_relatorio": envio_data.get('periodo_relatorio', envio_data.get('periodo', 'N/A')),
        "percentual_comissao": float(envio_data.get('percentual_comissao', 0)),
        "items": items_para_pdf,
        "total_comissao": float(envio_data.get('total_comissao', 0)),
        "total_adicionais": float(envio_data.get('total_adicionais', 0)),
        "total_auxilio": float(envio_data.get('total_auxilio', 0)),
        "total_geral": float(envio_data.get('total_geral', envio_data.get('valor_total', 0)))
    }
    
    # Adicionar logo como base64
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
        ctx['logo_base64'] = logo_base64
    
    html_pdf = template.render(**ctx)
    
    # Gerar PDF usando xhtml2pdf
    pdf_path = f"/tmp/relatorio_montador_{envio_data.get('id', 'temp')}.pdf"
    
    with open(pdf_path, 'wb') as pdf_file:
        pisa_status = pisa.CreatePDF(html_pdf, dest=pdf_file, encoding='utf-8')
    
    if pisa_status.err:
        raise Exception(f"Erro ao gerar PDF: {pisa_status.err}")
    
    return pdf_path

def enviar_email_graph(destinatario: str, assunto: str, corpo_html: str, anexo_path: str = None):
    """
    Envia email usando Microsoft Graph API
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo_html: Corpo do email em HTML
        anexo_path: Caminho do arquivo PDF para anexar (opcional)
    """
    
    try:
        print(f"\n🔐 Obtendo token de acesso...")
        token = get_valid_access_token()
        print(f"   ✅ Token obtido: {token[:30]}...")
    except Exception as e:
        print(f"   ❌ Erro ao obter token: {e}")
        raise Exception(f"Erro ao obter token de autenticação: {e}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Construir mensagem
    message = {
        "subject": assunto,
        "body": {
            "contentType": "HTML",
            "content": corpo_html
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": destinatario
                }
            }
        ]
    }
    
    # Adicionar anexo se fornecido
    if anexo_path and Path(anexo_path).exists():
        print(f"   📎 Anexando PDF: {anexo_path}")
        with open(anexo_path, 'rb') as f:
            pdf_content = f.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        message["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": Path(anexo_path).name,
                "contentType": "application/pdf",
                "contentBytes": pdf_base64
            }
        ]
        print(f"   ✅ PDF anexado ({len(pdf_content)} bytes)")
    
    # Enviar email
    print(f"   📤 Enviando email via Microsoft Graph API...")
    print(f"      Para: {destinatario}")
    print(f"      Assunto: {assunto}")
    
    response = requests.post(
        f"{GRAPH_API_URL}/me/sendMail",
        headers=headers,
        json={"message": message, "saveToSentItems": "true"}
    )
    
    print(f"   📬 Resposta da API: Status {response.status_code}")
    
    if response.status_code != 202:
        print(f"   ❌ ERRO: {response.text}")
        raise Exception(f"Erro ao enviar email (HTTP {response.status_code}): {response.text}")
    
    print(f"   ✅ Email aceito pela Microsoft (202 Accepted)")
    return True

@router.post("/enviar")
def enviar_relatorio(request: EnvioRelatorioRequest):
    """
    Gera PDF e envia relatório por email
    
    Fluxo:
    1. Busca dados do lote/envio no banco
    2. Gera PDF com template
    3. Envia email com PDF anexo via Microsoft Graph
    4. Atualiza status no banco
    """
    
    from app.database import get_db_connection
    import psycopg2.extras
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            if request.tipo == 'prestador':
                # Buscar lote de prestador
                cur.execute("""
                    SELECT l.*, p.email, p.nome as prestador_nome
                    FROM lotes_servico l
                    JOIN prestadores p ON l.prestador_id = p.id
                    WHERE l.id = %s
                """, (request.id,))
                lote = cur.fetchone()
                
                if not lote:
                    raise HTTPException(status_code=404, detail="Lote não encontrado")
                
                # Buscar OS do lote
                cur.execute("""
                    SELECT * FROM os_enviadas 
                    WHERE lote_id = %s
                """, (request.id,))
                os_list = cur.fetchall()
                
                lote['os_list'] = os_list
                
                # Gerar PDF
                pdf_path = gerar_pdf_prestador(lote)
                
                # Montar corpo do email
                corpo_email = f"""
                <html>
                <body>
                    <h2>Relatório de Fechamento - {lote['periodo']}</h2>
                    <p>Olá {lote['prestador_nome']},</p>
                    <p>Segue em anexo o relatório de fechamento do período <strong>{lote['periodo']}</strong>.</p>
                    <p><strong>Valor Total:</strong> R$ {lote['valor_total']:.2f}</p>
                    <p><strong>Quantidade de OS:</strong> {len(os_list)}</p>
                    <hr>
                    <p>Para enviar a Nota Fiscal, acesse o link abaixo:</p>
                    <p><a href="{lote.get('link_upload', '#')}">Enviar Nota Fiscal</a></p>
                    <br>
                    <p>Atenciosamente,</p>
                    <p><strong>Novo Mundo</strong></p>
                </body>
                </html>
                """
                
                # Enviar email
                enviar_email_graph(
                    destinatario=lote['email'],
                    assunto=f"Relatório de Fechamento - {lote['periodo']}",
                    corpo_html=corpo_email,
                    anexo_path=pdf_path
                )
                
                # Atualizar status
                cur.execute("""
                    UPDATE lotes_servico 
                    SET status = 'Aguardando NF', 
                        data_envio = NOW(),
                        anexo_path = %s
                    WHERE id = %s
                """, (pdf_path, request.id))
                
            else:  # montador
                # Buscar envio de montador
                cur.execute("""
                    SELECT e.*, m.email, m.nome as montador_nome, m.percentual_comissao
                    FROM envios_montagem e
                    JOIN montadores m ON e.montador_id = m.id
                    WHERE e.id = %s
                """, (request.id,))
                envio = cur.fetchone()
                
                if not envio:
                    raise HTTPException(status_code=404, detail="Envio não encontrado")
                
                # Processar detalhes das montagens
                detalhes = envio.get('detalhes', {})
                
                # Gerar PDF
                pdf_path = gerar_pdf_montador(envio)
                
                # Enviar email
                corpo_email = f"""
                <html>
                <body>
                    <h2>Relatório de Pagamento de Montagem</h2>
                    <p>Olá {envio['montador_nome']},</p>
                    <p>Segue em anexo o relatório de pagamento do período <strong>{envio['periodo']}</strong>.</p>
                    <p><strong>Valor Total:</strong> R$ {envio['valor_total']:.2f}</p>
                    <hr>
                    <p>Para enviar a Nota Fiscal, acesse o link abaixo:</p>
                    <p><a href="{envio.get('link_upload', '#')}">Enviar Nota Fiscal</a></p>
                    <br>
                    <p>Atenciosamente,</p>
                    <p><strong>Novo Mundo</strong></p>
                </body>
                </html>
                """
                
                enviar_email_graph(
                    destinatario=envio['email'],
                    assunto=f"Relatório de Pagamento - {envio['periodo']}",
                    corpo_html=corpo_email,
                    anexo_path=pdf_path
                )
                
                # Atualizar status
                cur.execute("""
                    UPDATE envios_montagem 
                    SET status = 'Aguardando NF',
                        data_envio = NOW(),
                        anexo_path = %s
                    WHERE id = %s
                """, (pdf_path, request.id))
            
            return {
                "success": True,
                "message": "Relatório enviado com sucesso",
                "pdf_path": pdf_path
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pendentes")
def listar_relatorios_pendentes(tipo: str = "prestador"):
    """
    Lista relatórios pendentes de envio
    
    Args:
        tipo: 'prestador' ou 'montador'
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == 'prestador':
            # Buscar lotes sem envio ou com status 'Em Aberto'
            cur.execute("""
                SELECT 
                    l.id,
                    l.prestador_nome as nome,
                    p.email,
                    l.periodo,
                    l.valor_total,
                    COUNT(o.id) as quantidade_os
                FROM lotes_servico l
                JOIN prestadores p ON l.prestador_id = p.id
                LEFT JOIN os_enviadas o ON o.lote_id = l.id
                WHERE l.status = 'Em Aberto'
                GROUP BY l.id, l.prestador_nome, p.email, l.periodo, l.valor_total
                ORDER BY l.created_at DESC
            """)
        else:
            # Buscar envios de montadores pendentes
            cur.execute("""
                SELECT 
                    e.id,
                    e.montador_nome as nome,
                    m.email,
                    e.periodo,
                    e.valor_total,
                    e.quantidade_os as quantidade_montagens
                FROM envios_montagem e
                JOIN montadores m ON e.montador_id = m.id
                WHERE e.status = 'Em Aberto'
                ORDER BY e.created_at DESC
            """)
        
        pendentes = cur.fetchall()
        return {"data": pendentes}

@router.post("/enviar-lote")
def enviar_lote_relatorios(request: dict):
    """
    Envia múltiplos relatórios em lote via email com PDF anexado
    
    Body:
        {
            "tipo": "prestador" ou "montador",
            "dados": [...lista de registros...],
            "emailConfig": {...configurações de email...},
            "enviarWhatsApp": boolean
        }
    """
    from app.database import get_db_connection
    import psycopg2.extras
    import uuid
    
    tipo = request.get("tipo")
    dados = request.get("dados", [])
    email_config = request.get("emailConfig", {})
    enviar_whatsapp = request.get("enviarWhatsApp", False)
    
    if not dados:
        raise HTTPException(status_code=400, detail="Nenhum dado para enviar")
    
    sucesso = 0
    erros = 0
    ignorados = 0
    erros_detalhes = []
    os_status_list = []  # Lista para retornar status de cada O.S.
    
    print(f"\n{'='*50}")
    print(f"📧 ENVIANDO LOTE DE RELATÓRIOS COM PDF")
    print(f"{'='*50}")
    print(f"Tipo: {tipo}")
    print(f"Total de registros: {len(dados)}")
    
    # Verificar blacklist e envios anteriores
    if tipo == "prestador":
        # Coletar todas as O.S.
        all_os_numbers = [item.get("o_s", "") for item in dados if item.get("o_s")]
        
        # Verificar blacklist e envios anteriores
        sent_os = check_os_sent(all_os_numbers)
        blacklisted_os = check_os_blacklist(all_os_numbers)
        
        print(f"\n📊 VERIFICAÇÃO:")
        print(f"   Total de O.S.: {len(all_os_numbers)}")
        print(f"   Já enviadas: {len(sent_os)}")
        print(f"   Na blacklist: {len(blacklisted_os)}")
        
        # Adicionar status de cada O.S. para retornar ao frontend
        for os_num in all_os_numbers:
            if os_num in blacklisted_os:
                status = "Na blacklist"
            elif os_num in sent_os:
                status = "Já enviado"
            else:
                status = "Pendente"
            
            os_status_list.append({
                "os": os_num,
                "status": status
            })
        
        # Filtrar dados para enviar apenas os pendentes
        dados_filtrados = []
        for item in dados:
            os_num = item.get("o_s", "")
            if os_num in blacklisted_os:
                print(f"   ⚠️  O.S. {os_num} - Na blacklist (ignorada)")
                ignorados += 1
            elif os_num in sent_os:
                print(f"   ⚠️  O.S. {os_num} - Já enviada (ignorada)")
                ignorados += 1
            else:
                dados_filtrados.append(item)
        
        dados = dados_filtrados
        
        if not dados:
            print(f"\n⚠️  Nenhuma O.S. nova para enviar!")
            return {
                "sucesso": 0,
                "erros": 0,
                "ignorados": ignorados,
                "total": len(os_status_list),
                "os_status": os_status_list,
                "message": f"❌ {ignorados} O.S. ignoradas (já enviadas ou na blacklist). Nenhuma O.S. nova para enviar."
            }
        
        print(f"\n✅ {len(dados)} O.S. pendentes serão enviadas")
    
    else:  # montador
        # Coletar todos os boletins
        all_boletins = [item.get("identificador_boletim_montagem", "") for item in dados if item.get("identificador_boletim_montagem")]
        
        # Verificar blacklist e envios anteriores
        sent_boletins = check_boletins_sent(all_boletins)
        blacklisted_boletins = check_boletins_blacklist(all_boletins)
        
        print(f"\n📊 VERIFICAÇÃO:")
        print(f"   Total de boletins: {len(all_boletins)}")
        print(f"   Já enviados: {len(sent_boletins)}")
        print(f"   Na blacklist: {len(blacklisted_boletins)}")
        
        # Adicionar status de cada boletim para retornar ao frontend
        for boletim in all_boletins:
            if boletim in blacklisted_boletins:
                status = "Na blacklist"
            elif boletim in sent_boletins:
                status = "Já enviado"
            else:
                status = "Pendente"
            
            os_status_list.append({
                "boletim": boletim,
                "status": status
            })
        
        # Filtrar dados para enviar apenas os pendentes
        dados_filtrados = []
        for item in dados:
            boletim = item.get("identificador_boletim_montagem", "")
            if boletim in blacklisted_boletins:
                print(f"   ⚠️  Boletim {boletim} - Na blacklist (ignorado)")
                ignorados += 1
            elif boletim in sent_boletins:
                print(f"   ⚠️  Boletim {boletim} - Já enviado (ignorado)")
                ignorados += 1
            else:
                dados_filtrados.append(item)
        
        dados = dados_filtrados
        
        if not dados:
            print(f"\n⚠️  Nenhum boletim novo para enviar!")
            return {
                "sucesso": 0,
                "erros": 0,
                "ignorados": ignorados,
                "total": len(os_status_list),
                "os_status": os_status_list,
                "message": f"❌ {ignorados} boletins ignorados (já enviados ou na blacklist). Nenhum boletim novo para enviar."
            }
        
        print(f"\n✅ {len(dados)} boletins pendentes serão enviados")
    
    # Agrupar dados por destinatário (prestador ou montador)
    grupos = {}
    
    if tipo == "prestador":
        for item in dados:
            nome = item.get("nome_prestador")
            if nome not in grupos:
                grupos[nome] = []
            grupos[nome].append(item)
    else:  # montador
        for item in dados:
            nome = item.get("nome_do_montador")
            if nome not in grupos:
                grupos[nome] = []
            grupos[nome].append(item)
    
    # Enviar email para cada grupo
    for nome_destinatario, itens in grupos.items():
        try:
            # Buscar email do destinatário no banco
            with get_db_connection() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                if tipo == "prestador":
                    cur.execute("SELECT id, email FROM prestadores WHERE nome = %s", (nome_destinatario,))
                else:
                    cur.execute("SELECT id, email FROM montadores WHERE nome = %s", (nome_destinatario,))
                
                resultado = cur.fetchone()
                
                if not resultado:
                    print(f"❌ {nome_destinatario}: Email não encontrado no banco")
                    erros += len(itens)
                    erros_detalhes.append({
                        "nome": nome_destinatario,
                        "erro": "Email não encontrado no banco de dados"
                    })
                    continue
                
                destinatario_id = resultado["id"]
                email_destino = resultado["email"]
                
                # === CRIAR LOTE NO BANCO ANTES DO ENVIO ===
                total_geral = sum(float(item.get("valor_total", 0)) for item in itens)
                lote_id = None
                
                if tipo == "prestador":
                    periodo = itens[0].get("periodo", "N/A")
                    
                    # Criar lote de serviço
                    cur.execute("""
                        INSERT INTO lotes_servico 
                        (prestador_id, prestador_nome, periodo, valor_total, data_envio, status)
                        VALUES (%s, %s, %s, %s, NOW(), 'Em Aberto')
                        RETURNING id
                    """, (destinatario_id, nome_destinatario, periodo, total_geral))
                    lote_id = cur.fetchone()['id']
                    print(f"   ✅ Lote #{lote_id} criado no banco")
                    
                    # Inserir O.S. no lote
                    for item in itens:
                        os_numero = item.get('o_s', '')
                        if os_numero:
                            cur.execute("""
                                INSERT INTO os_enviadas (lote_id, os_numero, detalhes)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (os_numero) DO NOTHING
                            """, (lote_id, os_numero, psycopg2.extras.Json(item)))
                    
                else:  # montador
                    # Calcular período a partir das datas (como no sistema original)
                    from datetime import datetime, timedelta
                    datas = []
                    print(f"   🔍 DEBUG - Total de itens para montador: {len(itens)}")
                    for i, item in enumerate(itens):
                        data_str = item.get('data_da_montagem', '')
                        print(f"   🔍 DEBUG - Item {i+1} data_da_montagem raw: '{data_str}' (tipo: {type(data_str)})")
                        
                        if data_str:
                            try:
                                # Se for float/int, é número serial do Excel (dias desde 1899-12-30)
                                if isinstance(data_str, (int, float)):
                                    # Converter número serial do Excel para data
                                    excel_epoch = datetime(1899, 12, 30)
                                    data_obj = excel_epoch + timedelta(days=float(data_str))
                                    datas.append(data_obj)
                                    print(f"   ✅ Data Excel convertida: {data_obj.strftime('%d/%m/%Y')}")
                                else:
                                    # Tentar parsear como string
                                    data_str_clean = str(data_str).strip()
                                    if data_str_clean:
                                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y']:
                                            try:
                                                data_obj = datetime.strptime(data_str_clean.split('T')[0], fmt)
                                                datas.append(data_obj)
                                                print(f"   ✅ Data parseada: {data_obj.strftime('%d/%m/%Y')} (formato: {fmt})")
                                                break
                                            except:
                                                continue
                            except Exception as e:
                                print(f"   ⚠️ Erro ao parsear data '{data_str}': {e}")
                    
                    print(f"   🔍 DEBUG - Total de datas válidas parseadas: {len(datas)}")
                    if datas:
                        data_min = min(datas)
                        data_max = max(datas)
                        periodo_relatorio = f"{data_min.strftime('%d/%m/%Y')} - {data_max.strftime('%d/%m/%Y')}"
                        # Extrair período no formato MM/YYYY para a coluna periodo
                        periodo = f"{data_min.strftime('%m/%Y')}"
                    else:
                        # Se não houver datas válidas, usar mês/ano atual para API (exige MM/YYYY)
                        hoje = datetime.now()
                        periodo_relatorio = f"Sem data - {hoje.strftime('%m/%Y')}"
                        periodo = hoje.strftime('%m/%Y')  # API externa exige MM/YYYY
                    
                    # Buscar informações do montador para calcular comissões
                    cur.execute("SELECT percentual_comissao, auxilio_semanal FROM montadores WHERE id = %s", (destinatario_id,))
                    montador_info = cur.fetchone()
                    percentual_comissao = montador_info['percentual_comissao'] if montador_info else 0.05
                    auxilio_semanal = montador_info['auxilio_semanal'] if montador_info else 100.0
                    
                    # Calcular semanas trabalhadas (número de semanas únicas)
                    semanas_unicas = set()
                    for data in datas:
                        semanas_unicas.add(data.isocalendar()[1])  # semana do ano
                    total_auxilio = len(semanas_unicas) * auxilio_semanal
                    
                    # Helper para formatar data no JSON
                    def format_data_para_pdf(data_raw):
                        """Converte data (Excel serial ou string) para formato dd/mm/yyyy"""
                        if not data_raw:
                            return '-'
                        try:
                            if isinstance(data_raw, (int, float)):
                                # Número serial do Excel
                                from datetime import datetime, timedelta
                                excel_epoch = datetime(1899, 12, 30)
                                data_obj = excel_epoch + timedelta(days=float(data_raw))
                                return data_obj.strftime('%d/%m/%Y')
                            else:
                                # String - tentar parsear
                                from datetime import datetime
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                                    try:
                                        data_obj = datetime.strptime(str(data_raw).split('T')[0], fmt)
                                        return data_obj.strftime('%d/%m/%Y')
                                    except:
                                        continue
                        except:
                            pass
                        return str(data_raw)
                    
                    # Criar envio de montagem (salva detalhes em JSONB, não tabela separada)
                    detalhes_json = {
                        "nome_montador": nome_destinatario,
                        "periodo_relatorio": periodo_relatorio,
                        "percentual_comissao": percentual_comissao * 100,
                        "items": [
                            {
                                "boletim": item.get('identificador_boletim_montagem', ''),
                                "data_montagem": format_data_para_pdf(item.get('data_da_montagem', '')),
                                "cliente": item.get('nome_do_cliente', '-'),
                                "nome_produto": item.get('nome_produto', '-'),
                                "valor_venda": float(item.get('media_de_valor_venda', 0)),
                                "comissao_calculada": float(item.get('media_de_valor_venda', 0)) * percentual_comissao,
                                "comissao_editada": None,
                                "adicional": float(item.get('adicional', 0))
                            }
                            for item in itens
                        ],
                        "total_comissao": sum(float(item.get('media_de_valor_venda', 0)) * percentual_comissao for item in itens),
                        "total_adicionais": sum(float(item.get('adicional', 0)) for item in itens),
                        "total_auxilio": total_auxilio,
                        "total_geral": sum(float(item.get('media_de_valor_venda', 0)) * percentual_comissao for item in itens) + sum(float(item.get('adicional', 0)) for item in itens) + total_auxilio
                    }
                    
                    # Verificar se já existe envio para este período e atualizar ao invés de inserir
                    cur.execute("""
                        SELECT id FROM envios_montagem 
                        WHERE montador_id = %s 
                        AND detalhes->>'periodo_relatorio' = %s
                    """, (destinatario_id, periodo_relatorio))
                    
                    envio_existente = cur.fetchone()
                    if envio_existente:
                        # Atualizar registro existente
                        lote_id = envio_existente['id']
                        cur.execute("""
                            UPDATE envios_montagem 
                            SET periodo = %s, 
                                valor_total = %s, 
                                data_envio = NOW(), 
                                quantidade_os = %s, 
                                detalhes = %s
                            WHERE id = %s
                        """, (periodo, detalhes_json['total_geral'], len(itens), psycopg2.extras.Json(detalhes_json), lote_id))
                        print(f"   ✅ Envio #{lote_id} atualizado no banco (período: {periodo_relatorio})")
                    else:
                        # Criar novo registro
                        cur.execute("""
                            INSERT INTO envios_montagem 
                            (montador_id, montador_nome, periodo, valor_total, data_envio, status, quantidade_os, detalhes)
                            VALUES (%s, %s, %s, %s, NOW(), 'Em Aberto', %s, %s)
                            RETURNING id
                        """, (destinatario_id, nome_destinatario, periodo, detalhes_json['total_geral'], len(itens), psycopg2.extras.Json(detalhes_json)))
                        lote_id = cur.fetchone()['id']
                        print(f"   ✅ Envio #{lote_id} criado no banco (período: {periodo_relatorio})")
                
                conn.commit()
                
                # === ENVIAR PARA API PARA GERAR LINK ===
                if tipo == "montador":
                    try:
                        import requests
                        import time
                        API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
                        
                        # Preparar payload para API (usar ID com offset para montadores)
                        lote_id_api = 876231 + lote_id
                        
                        payload_api = {
                            "nome": nome_destinatario,
                            "email": email_destino,
                            "periodo": periodo,  # Já está no formato MM/YYYY
                            "valor_total": float(detalhes_json['total_geral']),
                            "quantidade_os": len(itens),
                            "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "lote_id": lote_id_api,
                            "tipo": "montagem"
                        }
                        
                        print(f"   📦 Payload: {payload_api}")
                        
                        headers_api = {
                            "Content-Type": "application/json; charset=utf-8",
                            "Accept": "application/json",
                            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                            "X-API-Key": API_UPLOAD_KEY
                        }
                        
                        print(f"   📤 Enviando para API para gerar link (ID: {lote_id_api})...")
                        response_api = requests.post(
                            API_UPLOAD_URL,
                            json=payload_api,
                            headers=headers_api,
                            timeout=10,
                            verify=False
                        )
                        
                        if response_api.status_code in [200, 201]:
                            resposta_api = response_api.json()
                            if resposta_api.get('success'):
                                id_controle_api = resposta_api.get('id_controle') or resposta_api.get('id')
                                link_upload = resposta_api.get('link')
                                
                                print(f"   ✅ Enviado para API - ID Controle: {id_controle_api}")
                                print(f"   ✅ Link gerado: {link_upload}")
                                
                                # Salvar id_controle e link no banco
                                with get_db_connection() as conn_update:
                                    cur_update = conn_update.cursor()
                                    cur_update.execute("""
                                        UPDATE envios_montagem 
                                        SET id_controle = %s, link_upload = %s, data_envio_api = NOW()
                                        WHERE id = %s
                                    """, (id_controle_api, link_upload, lote_id))
                                    conn_update.commit()
                            else:
                                print(f"   ⚠️ API retornou erro: {resposta_api.get('message')}")
                                print(f"   📦 Resposta completa: {resposta_api}")
                                link_upload = None
                        elif response_api.status_code == 409:
                            # Conflito - registro já existe, buscar link existente
                            resposta_api = response_api.json()
                            print(f"   ⚠️ Registro já existe na API (ID: {resposta_api.get('existing_id')})")
                            print(f"   🔍 Buscando link existente no banco...")
                            
                            # Buscar link do banco
                            with get_db_connection() as conn_link:
                                cur_link = conn_link.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                                cur_link.execute("""
                                    SELECT link_upload, id_controle 
                                    FROM envios_montagem 
                                    WHERE id = %s
                                """, (lote_id,))
                                registro_existente = cur_link.fetchone()
                                
                                if registro_existente and registro_existente['link_upload']:
                                    link_upload = registro_existente['link_upload']
                                    print(f"   ✅ Link recuperado do banco: {link_upload}")
                                else:
                                    print(f"   ⚠️ Link não encontrado no banco, será usado fallback")
                                    link_upload = None
                        else:
                            print(f"   ⚠️ API respondeu com status {response_api.status_code}")
                            print(f"   📦 Resposta: {response_api.text[:200]}")
                            link_upload = None
                    
                    except Exception as e:
                        print(f"   ⚠️ Erro ao chamar API: {e}")
                        link_upload = None
                else:
                    # Para prestadores, o link será gerado mais abaixo
                    link_upload = None
                
                # Preparar assunto e corpo do email
                assunto = email_config.get("assunto", "Relatório de Serviços")
                corpo = email_config.get("corpo", "Segue relatório em anexo.")
                
                # Gerar link de upload via API externa (SOMENTE SE NÃO FOI GERADO ACIMA para montador)
                if link_upload is None and tipo == "prestador":
                    id_controle_api = None
                    try:
                        import requests
                        API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
                        
                        # Preparar payload para API (usar lote_id real do banco)
                        payload_api = {
                            "nome": nome_destinatario,
                            "email": email_destino,
                            "periodo": periodo if "/" in periodo else f"{periodo}/2025",
                            "valor_total": detalhes_json['total_geral'] if tipo == "montador" else sum(float(item.get("valor_total", 0)) for item in itens),
                            "quantidade_os": len(itens),
                            "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "lote_id": lote_id,  # Usar ID real do banco
                            "tipo": tipo
                        }
                        
                        headers_api = {
                            "Content-Type": "application/json; charset=utf-8",
                            "Accept": "application/json",
                            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                            "X-API-Key": API_UPLOAD_KEY
                        }
                        
                        print(f"   📤 Gerando link de upload via API (Lote #{lote_id})...")
                        response_api = requests.post(
                            API_UPLOAD_URL,
                            json=payload_api,
                            headers=headers_api,
                            timeout=10,
                            verify=False
                        )
                        
                        if response_api.status_code in [200, 201]:
                            resposta_api = response_api.json()
                            if resposta_api.get('success'):
                                link_upload = resposta_api.get('link')
                                id_controle_api = resposta_api.get('id')
                                print(f"   ✅ Link gerado: {link_upload}")
                                
                                # Salvar link no lote
                                with get_db_connection() as conn_link:
                                    cur_link = conn_link.cursor()
                                    if tipo == "prestador":
                                        cur_link.execute("""
                                            UPDATE lotes_servico 
                                            SET link_upload = %s, id_controle = %s, data_envio_api = NOW()
                                            WHERE id = %s
                                        """, (link_upload, id_controle_api, lote_id))
                                    else:
                                        cur_link.execute("""
                                            UPDATE envios_montagem 
                                            SET link_upload = %s, id_controle = %s, data_envio_api = NOW()
                                            WHERE id = %s
                                        """, (link_upload, id_controle_api, lote_id))
                                    conn_link.commit()
                            else:
                                print(f"   ⚠️ API retornou erro: {resposta_api.get('message')}")
                        else:
                            print(f"   ⚠️ API respondeu com status {response_api.status_code}")
                    
                    except Exception as e:
                        print(f"   ⚠️ Erro ao gerar link (prestador): {e}")
                    
                    # Fallback se API falhar (SOMENTE para prestador)
                    if not link_upload:
                        link_upload = f"https://upload.novomundo.com.br/{uuid.uuid4().hex[:12]}"
                
                # Garantir que link_upload existe (fallback final SOMENTE se ainda não foi definido)
                # Para montador, o link já foi gerado no bloco acima (linhas 1018-1095)
                if not link_upload and tipo == "prestador":
                    link_upload = f"https://upload.novomundo.com.br/{uuid.uuid4().hex[:12]}"
                
                # Substituir variáveis no template
                if tipo == "prestador":
                    periodo = itens[0].get("periodo", "N/A")
                    assunto = assunto.replace("{{periodo}}", periodo)
                    assunto = assunto.replace("{{nome_prestador}}", nome_destinatario)
                    corpo = corpo.replace("{{periodo}}", periodo)
                    corpo = corpo.replace("{{nome_prestador}}", nome_destinatario)
                    corpo = corpo.replace("{{link_upload}}", link_upload)
                    
                    # Calcular total
                    total_geral = sum(float(item.get("valor_total", 0)) for item in itens)
                    
                    # Preparar dados para o PDF
                    lote_id_numero = f"{int(datetime.now().timestamp() * 1000) % 100000}"  # Número simples baseado em timestamp
                    
                    lote_data = {
                        "nome_prestador": nome_destinatario,
                        "periodo": periodo,
                        "lote_id": lote_id_numero,
                        "items": [
                            {
                                "o_s": item.get("o_s", ""),
                                "cliente": item.get("cliente", ""),
                                "localidade": item.get("localidade", ""),
                                "modalidade": item.get("modalidade", ""),
                                "data_execucao": item.get("data_execucao", ""),
                                "valor_custo_prestador": float(item.get('valor_custo_prestador', item.get('valor', 0))),
                                "valor_extra": float(item.get('valor_extra', 0)),
                                "motivo_extra": item.get("motivo_extra", "-"),
                                "valor_total": float(item.get('valor_total', 0))
                            }
                            for item in itens
                        ],
                        "total_geral": total_geral
                    }
                    
                    # Gerar PDF
                    print(f"   📄 Gerando PDF do prestador...")
                    pdf_path = gerar_pdf_prestador(lote_data)
                    
                else:  # montador
                    # DEBUG: Verificar valor do link_upload antes de usar no template
                    print(f"   🔍 DEBUG - link_upload antes do template: {link_upload}")
                    print(f"   🔍 DEBUG - tipo: {tipo}")
                    
                    # Substituir variáveis no template (usar periodo_relatorio do detalhes_json)
                    assunto = assunto.replace("{{periodo_relatorio}}", detalhes_json['periodo_relatorio'])
                    assunto = assunto.replace("{{nome_montador}}", nome_destinatario)
                    corpo = corpo.replace("{{periodo_relatorio}}", detalhes_json['periodo_relatorio'])
                    corpo = corpo.replace("{{nome_montador}}", nome_destinatario)
                    corpo = corpo.replace("{{link_upload}}", link_upload if link_upload else "LINK_NAO_DEFINIDO")
                    corpo = corpo.replace("{{link}}", link_upload if link_upload else "LINK_NAO_DEFINIDO")  # Compatibilidade com template original
                    
                    # Preparar dados para o PDF (usar detalhes_json já calculado)
                    envio_data = detalhes_json.copy()
                    
                    # Gerar PDF
                    print(f"   📄 Gerando PDF do montador...")
                    print(f"   � DEBUG - envio_data keys: {list(envio_data.keys())}")
                    print(f"   🔍 DEBUG - nome_montador: {envio_data.get('nome_montador')}")
                    print(f"   🔍 DEBUG - periodo_relatorio: {envio_data.get('periodo_relatorio')}")
                    print(f"   🔍 DEBUG - total items: {len(envio_data.get('items', []))}")
                    if envio_data.get('items'):
                        print(f"   🔍 DEBUG - primeiro item: {envio_data['items'][0]}")
                    print(f"   �🔗 Link que será usado no email: {link_upload}")
                    pdf_path = gerar_pdf_montador(envio_data)
                
                # Converter corpo para HTML
                corpo_html = corpo.replace("\n", "<br>").replace("**", "<strong>").replace("**", "</strong>")
                
                print(f"\n📧 Enviando para: {nome_destinatario} ({email_destino})")
                print(f"   Assunto: {assunto}")
                print(f"   Itens: {len(itens)}")
                print(f"   PDF: {pdf_path}")
                
                # Enviar email com PDF anexado
                enviar_email_graph(
                    destinatario=email_destino,
                    assunto=assunto,
                    corpo_html=f"<html><body>{corpo_html}</body></html>",
                    anexo_path=pdf_path
                )
                
                sucesso += len(itens)
                print(f"   ✅ Email enviado com sucesso com PDF anexado!")
                print(f"   ✅ Lote #{lote_id} registrado com {len(itens)} itens")
                
        except Exception as e:
            import traceback
            print(f"   ❌ Erro ao enviar para {nome_destinatario}: {str(e)}")
            print(f"   Stack trace: {traceback.format_exc()}")
            erros += len(itens)
            erros_detalhes.append({
                "nome": nome_destinatario,
                "erro": str(e)
            })
    
    print(f"{'='*50}\n")
    
    resultado = {
        "sucesso": sucesso,
        "erros": erros,
        "ignorados": ignorados,
        "total": len(dados) + ignorados,
        "os_status": os_status_list
    }
    
    if erros > 0:
        resultado["warning"] = f"{erros} envios falharam"
        resultado["detalhes_erros"] = erros_detalhes
    
    if ignorados > 0:
        if sucesso > 0:
            resultado["message"] = f"✅ {sucesso} emails enviados com sucesso! {ignorados} itens ignorados (já enviados ou na blacklist)."
        else:
            resultado["warning"] = f"⚠️ {ignorados} itens ignorados (já enviados ou na blacklist)"
    elif sucesso > 0:
        resultado["message"] = f"✅ {sucesso} emails enviados com sucesso com PDF anexado!"
    
    return resultado


# ===== HISTÓRICO DE ENVIOS =====

@router.get("/historico")
def get_historico_envios(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: 'prestador' ou 'montador'"),
    status: Optional[str] = Query(None, description="Filtrar por status")
):
    """
    Retorna histórico de todos os envios (lotes de serviço e envios de montagem)
    
    Query Params:
        tipo: Filtro opcional - 'prestador' ou 'montador' ou None para todos
        status: Filtro opcional - status específico ou None para todos
    
    Returns:
        Lista de envios com informações completas
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    historico = []
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar lotes de serviço (prestadores)
        if tipo is None or tipo == "prestador":
            query_prestador = """
                SELECT 
                    l.id,
                    l.prestador_id,
                    l.prestador_nome,
                    l.periodo,
                    l.valor_total,
                    l.data_envio,
                    l.status,
                    l.conversation_id,
                    l.anexo_path,
                    l.link_upload,
                    l.validade_link,
                    l.id_controle,
                    l.status_api,
                    l.nota_fiscal_path,
                    COUNT(os.id) as quantidade_os,
                    'prestador' as tipo
                FROM lotes_servico l
                LEFT JOIN os_enviadas os ON os.lote_id = l.id
            """
            
            if status:
                query_prestador += " WHERE l.status = %s"
                cur.execute(query_prestador + " GROUP BY l.id ORDER BY l.data_envio DESC", (status,))
            else:
                cur.execute(query_prestador + " GROUP BY l.id ORDER BY l.data_envio DESC")
            
            lotes_prestador = cur.fetchall()
            
            for lote in lotes_prestador:
                historico.append(dict(lote))
        
        # Buscar envios de montagem (montadores)
        if tipo is None or tipo == "montador":
            query_montador = """
                SELECT 
                    em.id,
                    em.montador_id,
                    m.nome as montador_nome,
                    em.periodo,
                    em.valor_total,
                    em.data_envio,
                    em.status,
                    em.conversation_id,
                    em.anexo_path,
                    em.link_upload,
                    em.validade_link,
                    em.id_controle,
                    em.status_api,
                    em.nota_fiscal_path,
                    em.quantidade_os,
                    'montador' as tipo
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
            """
            
            if status:
                query_montador += " WHERE em.status = %s"
                cur.execute(query_montador + " ORDER BY em.data_envio DESC", (status,))
            else:
                cur.execute(query_montador + " ORDER BY em.data_envio DESC")
            
            envios_montador = cur.fetchall()
            
            for envio in envios_montador:
                historico.append(dict(envio))
    
    # Ordenar por data de envio (mais recente primeiro)
    historico.sort(key=lambda x: x['data_envio'], reverse=True)
    
    return historico


@router.get("/historico/{lote_id}/os")
def get_os_by_lote(lote_id: int, tipo: str = Query(..., description="Tipo: 'prestador' ou 'montador'")):
    """
    Retorna todas as O.S. de um lote específico
    
    Args:
        lote_id: ID do lote
        tipo: 'prestador' ou 'montador'
    
    Returns:
        Lista de O.S. ou boletins do lote
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == "prestador":
            # Buscar O.S. do lote
            cur.execute("""
                SELECT 
                    os.id,
                    os.os_numero,
                    os.detalhes,
                    l.prestador_nome
                FROM os_enviadas os
                JOIN lotes_servico l ON l.id = os.lote_id
                WHERE os.lote_id = %s
                ORDER BY os.os_numero
            """, (lote_id,))
        else:
            # Buscar boletins do envio de montagem (estão no JSONB detalhes)
            cur.execute("""
                SELECT 
                    em.id,
                    em.montador_nome,
                    em.detalhes
                FROM envios_montagem em
                WHERE em.id = %s
            """, (lote_id,))
            
            result = cur.fetchone()
            if result and result.get('detalhes'):
                # Extrair items do JSONB
                items_list = result['detalhes'].get('items', [])
                return [
                    {
                        'id': idx,
                        'boletim': item.get('boletim', ''),
                        'data_montagem': item.get('data_montagem', ''),
                        'cliente': item.get('cliente', ''),
                        'nome_produto': item.get('nome_produto', ''),
                        'montador_nome': result['montador_nome']
                    }
                    for idx, item in enumerate(items_list)
                ]
            return []
        
        items = cur.fetchall()
    
    return [dict(item) for item in items]


@router.delete("/historico-envios/prestador/{lote_id}")
async def deletar_lote_prestador(lote_id: int):
    """
    Deleta um lote de prestador e todos os registros relacionados (O.S. enviadas)
    Segue exatamente o comportamento do sistema original (database.py - delete_lote_servico)
    """
    from app.database import get_db_connection
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Deletar notificações relacionadas primeiro (como no sistema original)
            cur.execute('DELETE FROM notificacoes WHERE lote_id = %s', (lote_id,))
            
            # Deletar cards do Trello relacionados (se a tabela existir)
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'trello_cards'
                )
            """)
            if cur.fetchone()[0]:
                cur.execute('DELETE FROM trello_cards WHERE lote_id = %s', (lote_id,))
            
            # Deletar o lote (os_enviadas já tem ON DELETE CASCADE no banco)
            cur.execute('DELETE FROM lotes_servico WHERE id = %s RETURNING id', (lote_id,))
            deleted = cur.fetchone()
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Lote não encontrado")
            
            conn.commit()
            
        return {"success": True, "message": f"Lote #{lote_id} e todas as O.S. relacionadas foram excluídos"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar lote: {str(e)}")


@router.delete("/historico-envios/montador/{envio_id}")
async def deletar_envio_montador(envio_id: int):
    """
    Deleta um envio de montagem
    Segue exatamente o comportamento do sistema original (database.py - delete_envio_montagem)
    """
    from app.database import get_db_connection
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Deletar notificações relacionadas primeiro (como no sistema original)
            cur.execute('DELETE FROM notificacoes WHERE lote_id = %s AND tipo LIKE %s', (envio_id, '%montagem%'))
            
            # Deletar cards do Trello relacionados (se a tabela existir)
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'trello_cards'
                )
            """)
            if cur.fetchone()[0]:
                cur.execute('DELETE FROM trello_cards WHERE lote_id = %s', (envio_id,))
            
            # Deletar o envio de montagem
            cur.execute('DELETE FROM envios_montagem WHERE id = %s RETURNING id', (envio_id,))
            deleted = cur.fetchone()
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Envio não encontrado")
            
            conn.commit()
            
        return {"success": True, "message": f"Envio de montagem #{envio_id} excluído com sucesso"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar envio: {str(e)}")
