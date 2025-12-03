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
from app.utils.whatsapp_automation import enviar_notificacao_whatsapp

router = APIRouter()

# Modelos
class EnvioRelatorioRequest(BaseModel):
    id: int
    tipo: str  # 'prestador' ou 'montador'

# Configuração Microsoft Graph
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

def normalize_os_number(value):
    """
    Normaliza o número da O.S. para comparação
    Remove espaços, converte para string, lowercase e remove .0 final (comum em Excel)
    """
    if value is None:
        return ""
    
    s = str(value).strip().lower()
    
    # Remover .0 final se existir (conversão de float do Excel)
    if s.endswith('.0'):
        s = s[:-2]
        
    return s

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
    
    # Converter todos os números para string e normalizar
    os_numbers_str = [normalize_os_number(os) for os in os_numbers if os]
    
    # Remover duplicatas e vazios
    os_numbers_str = list(set([os for os in os_numbers_str if os]))
    
    if not os_numbers_str:
        return []
    
    print(f"\n🔍 check_os_sent - Verificando {len(os_numbers_str)} O.S.")
    print(f"   Primeiras 5 O.S. a verificar: {os_numbers_str[:5]}")
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Usar ANY com array para performance
            cur.execute("""
                SELECT DISTINCT LOWER(TRIM(os_numero)) as os_numero
                FROM os_enviadas 
                WHERE LOWER(TRIM(os_numero)) = ANY(%s)
            """, (os_numbers_str,))
            
            sent_os = [row['os_numero'] for row in cur.fetchall()]
            
            # Também verificar se existe alguma O.S. com .0 no banco que corresponda
            # (caso o banco tenha salvo errado anteriormente)
            if not sent_os and any(not x.endswith('.0') for x in os_numbers_str):
                 # Se não achou nada, tenta ver se no banco está salvo com .0
                 os_with_dot_zero = [f"{x}.0" for x in os_numbers_str]
                 cur.execute("""
                    SELECT DISTINCT LOWER(TRIM(os_numero)) as os_numero
                    FROM os_enviadas 
                    WHERE LOWER(TRIM(os_numero)) = ANY(%s)
                """, (os_with_dot_zero,))
                 
                 # Se achou com .0, precisamos retornar a versão normalizada (sem .0) para o match funcionar
                 found_with_dot = [row['os_numero'] for row in cur.fetchall()]
                 for os_dot in found_with_dot:
                     if os_dot.endswith('.0'):
                         sent_os.append(os_dot[:-2])
                     else:
                         sent_os.append(os_dot)
    
    print(f"   ✅ Encontradas {len(sent_os)} O.S. já enviadas")
    if sent_os:
        print(f"   Primeiras 5 já enviadas: {sent_os[:5]}")
    
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
    
    # Converter todos os números para string
    os_numbers_str = [str(os) for os in os_numbers]
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT os_numero 
                FROM os_blacklist 
                WHERE os_numero = ANY(%s)
            """, (os_numbers_str,))
            
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
    
    # Converter todos os boletins para string
    boletins_str = [str(b).strip() for b in boletins if b]
    
    if not boletins_str:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar boletins nos detalhes JSONB de forma eficiente
            # Usa jsonb_array_elements para extrair items e verificar boletim
            sent_boletins = []
            
            for boletim in boletins_str:
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM envios_montagem,
                    jsonb_array_elements(detalhes->'items') as item
                    WHERE item->>'boletim' = %s
                """, (boletim,))
                
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
    
    # Converter todos os boletins para string
    boletins_str = [str(b) for b in boletins]
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT boletim 
                FROM boletins_blacklist 
                WHERE boletim = ANY(%s)
            """, (boletins_str,))
            
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

# === ENDPOINTS DE CONFIGURAÇÃO DE EMAIL ===

@router.get("/email-config/{tipo}")
def get_email_config(tipo: str):
    """
    Busca a última configuração de email salva para o tipo (prestador ou montador)
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if tipo not in ['prestador', 'montador']:
        raise HTTPException(status_code=400, detail="Tipo deve ser 'prestador' ou 'montador'")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT assunto, corpo, cc, atualizado_em
            FROM email_config
            WHERE tipo = %s
        """, (tipo,))
        
        config = cur.fetchone()
        
        if not config:
            # Retornar config padrão se não existir
            if tipo == "prestador":
                return {
                    "assunto": "Novo Mundo Resolve | Nota Fiscal | Período: {{periodo}} | Prestador: {{nome_prestador}}",
                    "corpo": """Segue a relação de boletins para emissão da nota fiscal de serviços entre **{{periodo}}**.

📎 Para anexar a Nota Fiscal, acesse o link abaixo:
{{link_upload}}

⚠️ Este link é válido por 30 dias.

Obrigado.""",
                    "cc": "projetos.qualidade@novomundo.com.br"
                }
            else:
                return {
                    "assunto": "Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}",
                    "corpo": """Olá, {{nome_montador}},

Segue em anexo o seu relatório de pagamento de montagens referente ao período de **{{periodo_relatorio}}**.

📎 **Link para upload de documentos:** {{link_upload}}

Qualquer dúvida, estamos à disposição.""",
                    "cc": "projetos.qualidade@novomundo.com.br"
                }
        
        return dict(config)

@router.post("/email-config/{tipo}")
def save_email_config(tipo: str, config: dict):
    """
    Salva a configuração de email para o tipo (prestador ou montador)
    
    Body:
        {
            "assunto": "...",
            "corpo": "...",
            "cc": "..."
        }
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if tipo not in ['prestador', 'montador']:
        raise HTTPException(status_code=400, detail="Tipo deve ser 'prestador' ou 'montador'")
    
    assunto = config.get('assunto', '')
    corpo = config.get('corpo', '')
    cc = config.get('cc', '')
    
    if not assunto or not corpo:
        raise HTTPException(status_code=400, detail="Assunto e corpo são obrigatórios")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Inserir ou atualizar
        cur.execute("""
            INSERT INTO email_config (tipo, assunto, corpo, cc, atualizado_em)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (tipo) 
            DO UPDATE SET 
                assunto = EXCLUDED.assunto,
                corpo = EXCLUDED.corpo,
                cc = EXCLUDED.cc,
                atualizado_em = NOW()
        """, (tipo, assunto, corpo, cc))
        
        conn.commit()
    
    return {"success": True, "message": "Configuração salva com sucesso"}

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
    
    # Criar nome do arquivo com nome do prestador
    nome_arquivo_limpo = nome_prestador.replace(' ', '_').replace('/', '_')
    pdf_path = f"/tmp/Relatorio_{nome_arquivo_limpo}_{lote_id}.pdf"
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

def gerar_pdf_montador_html_template(envio_data):
    """
    Gera PDF do montador usando template HTML original com WeasyPrint
    """
    from jinja2 import Template
    from pathlib import Path
    
    # Fix para macOS e WeasyPrint (carregar bibliotecas do Homebrew)
    import sys
    import os
    if sys.platform == 'darwin':
        try:
            # Patch para ctypes.util.find_library para ajudar o CFFI a encontrar as bibliotecas
            import ctypes.util
            original_find_library = ctypes.util.find_library
            
            def patched_find_library(name):
                # Mapeamento de nomes que o WeasyPrint procura para os caminhos do Homebrew
                # O WeasyPrint procura por 'gobject-2.0-0', 'pango-1.0-0', etc.
                
                # Normalizar nome (remover sufixo -0 se existir para busca no dicionário)
                base_name = name
                if name.endswith('-0'):
                    base_name = name[:-2]
                
                # Caminhos comuns no Homebrew
                homebrew_lib = '/opt/homebrew/lib'
                
                # Tentar mapeamento direto
                candidates = [
                    os.path.join(homebrew_lib, f"lib{name}.dylib"),
                    os.path.join(homebrew_lib, f"lib{base_name}.dylib"),
                    os.path.join(homebrew_lib, f"lib{base_name}.0.dylib")
                ]
                
                for path in candidates:
                    if os.path.exists(path):
                        return path
                
                return original_find_library(name)
            
            ctypes.util.find_library = patched_find_library
            
        except Exception as e:
            print(f"Erro ao aplicar patch no find_library: {e}")

    from weasyprint import HTML
    import tempfile
    import base64
    from datetime import datetime, timedelta
    
    template_path = Path(__file__).parent.parent / "templates" / "montador_template.html"
    template_content = template_path.read_text(encoding='utf-8')
    template = Template(template_content)
    
    # Formatar datas nos items
    items = envio_data.get('items', [])
    for item in items:
        data_raw = item.get('data_montagem', item.get('data_da_montagem', '-'))
        if isinstance(data_raw, (int, float)):
            # Se for timestamp do Excel (dias desde 1900-01-01)
            base_date = datetime(1899, 12, 30)
            item['data_montagem'] = (base_date + timedelta(days=data_raw)).strftime('%d/%m/%Y')
        elif hasattr(data_raw, 'strftime'):
            # Se for datetime/date
            item['data_montagem'] = data_raw.strftime('%d/%m/%Y')
        else:
            # Se já for string
            item['data_montagem'] = str(data_raw)
    
    # Carregar logo e converter para base64
    logo_path = Path(__file__).parent.parent / "templates" / "LOGO-NOVO-MUNDO-PEQUENA.png"
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
            envio_data['logo_url'] = f"data:image/png;base64,{logo_base64}"
    else:
        envio_data['logo_url'] = ""
    
    # Renderizar HTML e converter para PDF
    html_content = template.render(**envio_data)
    
    # Criar nome do arquivo com nome do montador
    import os
    nome_montador = envio_data.get('nome_montador', envio_data.get('montador_nome', 'N/A'))
    lote_id = envio_data.get('id', 'temp')
    nome_arquivo_limpo = nome_montador.replace(' ', '_').replace('/', '_')
    pdf_filename = f"Relatorio_{nome_arquivo_limpo}_{lote_id}.pdf"
    pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
    
    HTML(string=html_content).write_pdf(pdf_path)
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
        # Formatar data corretamente
        data_raw = item.get('data_montagem', item.get('data_da_montagem', '-'))
        if isinstance(data_raw, (int, float)):
            # Se for timestamp do Excel (dias desde 1900-01-01)
            from datetime import datetime, timedelta
            base_date = datetime(1899, 12, 30)  # Excel conta a partir de 30/12/1899
            data_formatada = (base_date + timedelta(days=data_raw)).strftime('%d/%m/%Y')
        elif hasattr(data_raw, 'strftime'):
            # Se for datetime/date
            data_formatada = data_raw.strftime('%d/%m/%Y')
        else:
            # Se já for string ou '-'
            data_formatada = str(data_raw)
        
        items_para_pdf.append({
            'boletim': item.get('boletim', item.get('identificador_boletim_montagem', '')),
            'data_montagem': data_formatada,
            'cliente': item.get('cliente', item.get('nome_do_cliente', '-')),
            'nome_produto': item.get('nome_produto', '-'),
            'valor_venda': float(item.get('valor_venda', item.get('media_de_valor_venda', 0))),
            'comissao_calculada': float(item.get('comissao_calculada', item.get('comissao', 0))),
            'comissao_editada': item.get('comissao_editada'),
            'adicional': float(item.get('adicional', 0)),
            'motivo_valor_extra': item.get('motivo_valor_extra', item.get('motivo', ''))
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
    
    # Criar nome do arquivo com nome do montador
    nome_montador = envio_data.get('nome_montador', envio_data.get('montador_nome', 'N/A'))
    lote_id = envio_data.get('id', 'temp')
    nome_arquivo_limpo = nome_montador.replace(' ', '_').replace('/', '_')
    pdf_path = f"/tmp/Relatorio_{nome_arquivo_limpo}_{lote_id}.pdf"
    
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
                
                # Gerar PDF usando template HTML original
                from jinja2 import Template
                from pathlib import Path
                import base64
                
                template_path = Path(__file__).parent.parent / "templates" / "invoice_template.html"
                template_content = template_path.read_text(encoding='utf-8')
                template = Template(template_content)
                
                # Carregar logo e converter para base64
                logo_path = Path(__file__).parent.parent / "templates" / "LOGO-NOVO-MUNDO-PEQUENA.png"
                if logo_path.exists():
                    with open(logo_path, 'rb') as f:
                        logo_base64 = base64.b64encode(f.read()).decode('utf-8')
                        logo_data_uri = f"data:image/png;base64,{logo_base64}"
                else:
                    logo_data_uri = ""
                
                # Preparar dados para o template
                items_fmt = []
                for os_item in os_list:
                    data_exec = os_item.get('data_execucao', '')
                    if hasattr(data_exec, 'strftime'):
                        data_exec = data_exec.strftime('%d/%m/%Y')
                    
                    items_fmt.append({
                        "OS": os_item.get('o_s', ''),
                        "Cliente": os_item.get('cliente', '-'),
                        "Localidade": os_item.get('localidade', '-'),
                        "Modalidade": os_item.get('modalidade', ''),
                        "Data_execucao": str(data_exec),
                        "Valor": f"{float(os_item.get('valor_custo_prestador', 0)):.2f}",
                        "Valor_extra": f"{float(os_item.get('valor_extra', 0)):.2f}",
                        "Motivo_valor_extra": os_item.get('motivo_extra', '-'),
                        "Valor_total": f"{float(os_item.get('valor_total', 0)):.2f}"
                    })
                
                context = {
                    "nome_prestador": lote['prestador_nome'],
                    "periodo": lote['periodo'],
                    "lote_id": lote['id'],
                    "items": items_fmt,
                    "total_geral": f"{float(lote['valor_total']):.2f}",
                    "logo_url": logo_data_uri
                }
                
                # Renderizar HTML
                html_content = template.render(**context)
                
                # Converter HTML para PDF usando WeasyPrint
                # from weasyprint import HTML  # DESABILITADO - precisa de libs do sistema
                import tempfile
                import os
                
                # Criar nome do arquivo com nome do prestador
                nome_arquivo_limpo = lote['prestador_nome'].replace(' ', '_').replace('/', '_')
                pdf_filename = f"Relatorio_{nome_arquivo_limpo}_{lote['id']}.pdf"
                pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
                
                # Gerar PDF a partir do HTML
                # HTML(string=html_content).write_pdf(pdf_path)  # DESABILITADO
                
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
                # Buscar envio de montador com os 3 percentuais
                cur.execute("""
                    SELECT e.*, m.email, m.nome as montador_nome, 
                           m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem,
                           m.auxilio_semanal
                    FROM envios_montagem e
                    JOIN montadores m ON e.montador_id = m.id
                    WHERE e.id = %s
                """, (request.id,))
                envio = cur.fetchone()
                
                if not envio:
                    raise HTTPException(status_code=404, detail="Envio não encontrado")
                
                # Buscar montagens do envio
                cur.execute("""
                    SELECT * FROM montagens_enviadas 
                    WHERE envio_id = %s
                """, (request.id,))
                montagens = cur.fetchall()
                
                # Gerar PDF usando template HTML original
                from jinja2 import Template
                from pathlib import Path
                
                template_path = Path(__file__).parent.parent / "templates" / "montador_template.html"
                template_content = template_path.read_text(encoding='utf-8')
                template = Template(template_content)
                
                # Preparar dados para o template
                items_fmt = []
                total_montagem = 0
                total_assistencia = 0
                total_desmontagem = 0
                total_adicionais = 0
                
                # Converter percentuais para float
                percentual_montagem = float(envio.get('percentual_montagem', 0.05))
                percentual_assistencia = float(envio.get('percentual_assistencia', 0.05))
                percentual_desmontagem = float(envio.get('percentual_desmontagem', 0.05))
                
                for montagem in montagens:
                    data_montagem = montagem.get('data_montagem', '')
                    if hasattr(data_montagem, 'strftime'):
                        data_montagem = data_montagem.strftime('%d/%m/%Y')
                    
                    valor_venda = float(montagem.get('valor_venda', 0))
                    tipo_servico = montagem.get('tipo_servico', 'MONTAGEM')
                    adicional = float(montagem.get('valor_adicional', 0))
                    motivo_extra = montagem.get('motivo_valor_extra', montagem.get('motivo', ''))
                    
                    # Calcular comissão com base no tipo de serviço
                    if tipo_servico == "ASSISTENCIA_TECNICA":
                        comissao_calculada = valor_venda * percentual_assistencia
                        total_assistencia += comissao_calculada
                    elif tipo_servico == "DESMONTAGEM":
                        comissao_calculada = valor_venda * percentual_desmontagem
                        total_desmontagem += comissao_calculada
                    else:  # MONTAGEM
                        comissao_calculada = valor_venda * percentual_montagem
                        total_montagem += comissao_calculada
                    
                    comissao_editada = montagem.get('comissao_editada')
                    
                    items_fmt.append({
                        "boletim": montagem.get('boletim_montagem', ''),
                        "data_montagem": str(data_montagem),
                        "tipo_servico": tipo_servico,
                        "cliente": montagem.get('cliente', ''),
                        "nome_produto": montagem.get('produto', ''),
                        "valor_venda": valor_venda,
                        "comissao_calculada": comissao_calculada,
                        "comissao_editada": comissao_editada,
                        "adicional": adicional,
                        "motivo_valor_extra": motivo_extra
                    })
                    
                    total_adicionais += adicional
                
                total_auxilio = float(envio.get('auxilio_semanal', 0))
                total_comissao = total_montagem + total_assistencia + total_desmontagem
                total_geral = total_comissao + total_adicionais + total_auxilio
                
                context = {
                    "nome_montador": envio['montador_nome'],
                    "periodo_relatorio": envio['periodo'],
                    "items": items_fmt,
                    "percentual_montagem": percentual_montagem,
                    "percentual_assistencia": percentual_assistencia,
                    "percentual_desmontagem": percentual_desmontagem,
                    "total_montagem": total_montagem,
                    "total_assistencia": total_assistencia,
                    "total_desmontagem": total_desmontagem,
                    "total_comissao": total_comissao,
                    "total_adicionais": total_adicionais,
                    "total_auxilio": total_auxilio,
                    "total_geral": total_geral
                }
                
                # Renderizar HTML
                html_content = template.render(**context)
                
                # Converter HTML para PDF usando WeasyPrint
                # from weasyprint import HTML  # DESABILITADO - precisa de libs do sistema
                import tempfile
                import os
                
                # Criar nome do arquivo com nome do montador
                nome_arquivo_limpo = envio['montador_nome'].replace(' ', '_').replace('/', '_')
                pdf_filename = f"Relatorio_{nome_arquivo_limpo}_{envio['id']}.pdf"
                pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
                
                # Gerar PDF a partir do HTML
                # HTML(string=html_content).write_pdf(pdf_path)  # DESABILITADO
                
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
    
    print(f"🔍 DEBUG - enviarWhatsApp recebido: {enviar_whatsapp} (tipo: {type(enviar_whatsapp)})")
    
    if not dados:
        raise HTTPException(status_code=400, detail="Nenhum dado para enviar")
    
    # Se não vier emailConfig no request, buscar do banco
    if not email_config or not email_config.get('assunto') or not email_config.get('corpo'):
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT assunto, corpo, cc
                FROM email_config
                WHERE tipo = %s
            """, (tipo,))
            
            config_db = cur.fetchone()
            if config_db:
                email_config = dict(config_db)
                print(f"📧 Usando configuração de email salva do banco")
    
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
        print(f"   Já enviadas: {len(sent_os)} → {sent_os}")
        print(f"   Na blacklist: {len(blacklisted_os)} → {blacklisted_os}")
        
        # Adicionar status de cada O.S. para retornar ao frontend
        for os_num_raw in all_os_numbers:
            os_num = normalize_os_number(os_num_raw)
            
            if os_num in blacklisted_os:
                status = "Na blacklist"
            elif os_num in sent_os:
                status = "Já enviado"
            else:
                status = "Pendente"
            
            os_status_list.append({
                "os": os_num_raw,
                "status": status
            })
        
        # Filtrar dados para enviar apenas os pendentes
        dados_filtrados = []
        for item in dados:
            os_num = normalize_os_number(item.get("o_s", ""))
            
            if os_num in blacklisted_os:
                print(f"   ⚠️  O.S. {item.get('o_s')} - Na blacklist (ignorada)")
                ignorados += 1
            elif os_num in sent_os:
                print(f"   ⚠️  O.S. {item.get('o_s')} - Já enviada (ignorada)")
                ignorados += 1
            else:
                print(f"   ✅ O.S. {item.get('o_s')} - Pendente (será enviada)")
                dados_filtrados.append(item)
        
        print(f"\n🔍 FILTRO FINAL:")
        print(f"   Total original: {len(dados)}")
        print(f"   Total filtrado: {len(dados_filtrados)}")
        print(f"   Ignorados: {ignorados}")
        
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
        print(f"   Já enviados: {len(sent_boletins)} → {sent_boletins}")
        print(f"   Na blacklist: {len(blacklisted_boletins)} → {blacklisted_boletins}")
        
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
                print(f"   ✅ Boletim {boletim} - Pendente (será enviado)")
                dados_filtrados.append(item)
        
        print(f"\n🔍 FILTRO FINAL:")
        print(f"   Total original: {len(dados)}")
        print(f"   Total filtrado: {len(dados_filtrados)}")
        print(f"   Ignorados: {ignorados}")
        
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
            # DEBUG: Verificar se motivo_valor_extra está nos itens
            if tipo == "montador":
                print(f"\n🔍 DEBUG - Itens recebidos para {nome_destinatario}:")
                for idx, item in enumerate(itens):
                    print(f"   Item {idx+1}: adicional={item.get('adicional', 0)}, motivo={item.get('motivo_valor_extra', 'N/A')}")
            
            # Buscar email do destinatário no banco
            with get_db_connection() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                if tipo == "prestador":
                    cur.execute("SELECT id, email, tempo_vencimento_dias FROM prestadores WHERE nome = %s", (nome_destinatario,))
                else:
                    cur.execute("SELECT id, email, tempo_vencimento_dias FROM montadores WHERE nome = %s", (nome_destinatario,))
                
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
                tempo_vencimento_dias = resultado.get("tempo_vencimento_dias")
                
                # === CRIAR LOTE NO BANCO ANTES DO ENVIO ===
                total_geral = sum(float(item.get("valor_total", 0)) for item in itens)
                lote_id = None
                
                if tipo == "prestador":
                    periodo = itens[0].get("periodo", "N/A")
                    
                    # Calcular data de vencimento se tempo_vencimento_dias estiver definido
                    data_vencimento = None
                    if tempo_vencimento_dias:
                        from datetime import timedelta
                        data_vencimento = datetime.now().date() + timedelta(days=tempo_vencimento_dias)
                    
                    # Criar lote de serviço
                    cur.execute("""
                        INSERT INTO lotes_servico 
                        (prestador_id, prestador_nome, periodo, valor_total, data_envio, data_vencimento_pagamento, status)
                        VALUES (%s, %s, %s, %s, NOW(), %s, 'Em Aberto')
                        RETURNING id
                    """, (destinatario_id, nome_destinatario, periodo, total_geral, data_vencimento))
                    lote_id = cur.fetchone()['id']
                    print(f"   ✅ Lote #{lote_id} criado no banco")
                    
                    # Inserir O.S. no lote
                    for item in itens:
                        os_numero = normalize_os_number(item.get('o_s', ''))
                        if os_numero:
                            cur.execute("""
                                INSERT INTO os_enviadas (lote_id, os_numero, detalhes)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (os_numero) DO NOTHING
                            """, (lote_id, os_numero, psycopg2.extras.Json(item)))
                    
                else:  # montador
                    # Calcular período a partir das datas (como no sistema original)
                    from datetime import timedelta
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
                    cur.execute("""
                        SELECT percentual_montagem, percentual_assistencia, percentual_desmontagem, auxilio_semanal 
                        FROM montadores 
                        WHERE id = %s
                    """, (destinatario_id,))
                    montador_info = cur.fetchone()
                    percentual_montagem = float(montador_info['percentual_montagem']) if montador_info else 0.05
                    percentual_assistencia = float(montador_info['percentual_assistencia']) if montador_info else 0.05
                    percentual_desmontagem = float(montador_info['percentual_desmontagem']) if montador_info else 0.05
                    auxilio_semanal = float(montador_info['auxilio_semanal']) if montador_info else 100.0
                    
                    # Calcular semanas trabalhadas (número de semanas únicas)
                    semanas_unicas = set()
                    for data in datas:
                        semanas_unicas.add(data.isocalendar()[1])  # semana do ano
                    total_auxilio = len(semanas_unicas) * auxilio_semanal
                    
                    # Helper para formatar data no JSON
                    def format_data_para_pdf(data_raw):
                        """Converte data (Excel serial ou string) para formato dd/mm/yyyy"""
                        if not data_raw or data_raw == '':
                            return '-'
                        
                        # Se já for string formatada, retornar direto
                        if isinstance(data_raw, str) and '/' in data_raw:
                            return data_raw
                            
                        try:
                            if isinstance(data_raw, (int, float)):
                                # Número serial do Excel
                                from datetime import timedelta
                                excel_epoch = datetime(1899, 12, 30)
                                data_obj = excel_epoch + timedelta(days=float(data_raw))
                                resultado = data_obj.strftime('%d/%m/%Y')
                                print(f"   🔄 Convertendo data Excel {data_raw} → {resultado}")
                                return resultado
                            elif isinstance(data_raw, str):
                                # Tentar converter string numérica do Excel
                                try:
                                    data_num = float(data_raw)
                                    from datetime import timedelta
                                    excel_epoch = datetime(1899, 12, 30)
                                    data_obj = excel_epoch + timedelta(days=data_num)
                                    resultado = data_obj.strftime('%d/%m/%Y')
                                    print(f"   🔄 Convertendo string Excel '{data_raw}' → {resultado}")
                                    return resultado
                                except ValueError:
                                    # Não é número, tentar parsear como data
                                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                                        try:
                                            data_obj = datetime.strptime(str(data_raw).split('T')[0], fmt)
                                            return data_obj.strftime('%d/%m/%Y')
                                        except:
                                            continue
                        except Exception as e:
                            print(f"   ⚠️ Erro ao converter data '{data_raw}': {e}")
                        
                        return str(data_raw)
                    
                    # Criar envio de montagem (salva detalhes em JSONB, não tabela separada)
                    # Processar items e calcular totais por tipo de serviço
                    items_processados = []
                    total_montagem = 0
                    total_assistencia = 0
                    total_desmontagem = 0
                    
                    for item in itens:
                        tipo_servico = item.get('tipo_servico', 'MONTAGEM').upper()
                        valor_venda = float(item.get('media_de_valor_venda', 0))
                        
                        # Determinar percentual baseado no tipo (converter Decimal para float)
                        if 'ASSIST' in tipo_servico or 'TECNICA' in tipo_servico:
                            percentual = float(percentual_assistencia)
                            tipo_servico = 'ASSISTENCIA_TECNICA'
                        elif 'DESMONT' in tipo_servico:
                            percentual = float(percentual_desmontagem)
                            tipo_servico = 'DESMONTAGEM'
                        else:
                            percentual = float(percentual_montagem)
                            tipo_servico = 'MONTAGEM'
                        
                        comissao = valor_venda * percentual
                        
                        # Somar ao total correto
                        if tipo_servico == 'MONTAGEM':
                            total_montagem += comissao
                        elif tipo_servico == 'ASSISTENCIA_TECNICA':
                            total_assistencia += comissao
                        elif tipo_servico == 'DESMONTAGEM':
                            total_desmontagem += comissao
                        
                        items_processados.append({
                            "boletim": item.get('identificador_boletim_montagem', ''),
                            "data_montagem": format_data_para_pdf(item.get('data_da_montagem', '')),
                            "cliente": item.get('nome_do_cliente', '-'),
                            "nome_produto": item.get('nome_produto', '-'),
                            "valor_venda": valor_venda,
                            "comissao_calculada": comissao,
                            "comissao_editada": None,
                            "adicional": float(item.get('adicional', 0)),
                            "motivo_valor_extra": item.get('motivo_valor_extra', item.get('motivo', '')),
                            "tipo_servico": tipo_servico
                        })
                    
                    total_adicionais = sum(float(item.get('adicional', 0)) for item in itens)
                    total_comissoes = total_montagem + total_assistencia + total_desmontagem
                    
                    detalhes_json = {
                        "nome_montador": nome_destinatario,
                        "periodo_relatorio": periodo_relatorio,
                        "percentual_montagem": percentual_montagem,  # Já como decimal (ex: 0.05)
                        "percentual_assistencia": percentual_assistencia,  # Já como decimal
                        "percentual_desmontagem": percentual_desmontagem,  # Já como decimal
                        "items": items_processados,
                        "total_montagem": total_montagem,
                        "total_assistencia": total_assistencia,
                        "total_desmontagem": total_desmontagem,
                        "total_comissao": total_comissoes,
                        "total_adicionais": total_adicionais,
                        "total_auxilio": total_auxilio,
                        "total_geral": total_comissoes + total_adicionais + total_auxilio
                    }
                    
                    # Calcular data de vencimento se tempo_vencimento_dias estiver definido
                    data_vencimento_montador = None
                    if tempo_vencimento_dias:
                        from datetime import timedelta
                        data_vencimento_montador = datetime.now().date() + timedelta(days=tempo_vencimento_dias)
                    
                    # SEMPRE criar novo registro (não reutilizar por período)
                    # Cada envio deve ter seu próprio lote e link único
                    cur.execute("""
                        INSERT INTO envios_montagem 
                        (montador_id, montador_nome, periodo, valor_total, data_envio, data_vencimento_pagamento, status, quantidade_os, detalhes)
                        VALUES (%s, %s, %s, %s, NOW(), %s, 'Em Aberto', %s, %s)
                        RETURNING id
                    """, (destinatario_id, nome_destinatario, periodo, detalhes_json['total_geral'], data_vencimento_montador, len(itens), psycopg2.extras.Json(detalhes_json)))
                    lote_id = cur.fetchone()['id']
                    print(f"   ✅ Novo envio #{lote_id} criado no banco (período: {periodo_relatorio})")

                
                conn.commit()
                
                # === ENVIAR PARA API PARA GERAR LINK ===
                if tipo == "montador":
                    try:
                        import requests
                        import time
                        API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
                        
                        # ID do banco já começa em 100000+ (sequence configurada)
                        # Usar diretamente sem offset adicional
                        print(f"   🆔 ID para API: {lote_id}")
                        
                        payload_api = {
                            "nome": nome_destinatario,
                            "email": email_destino,
                            "periodo": periodo,  # Já está no formato MM/YYYY
                            "valor_total": float(detalhes_json['total_geral']),
                            "quantidade_os": len(itens),
                            "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "lote_id": lote_id,
                            "tipo": "montagem"
                        }
                        
                        print(f"   📦 Payload: {payload_api}")
                        
                        headers_api = {
                            "Content-Type": "application/json; charset=utf-8",
                            "Accept": "application/json",
                            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                            "X-API-Key": API_UPLOAD_KEY
                        }
                        
                        print(f"   📤 Enviando para API para gerar link (ID: {lote_id})...")
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
                                upload_hash = resposta_api.get('hash')  # ✅ CRÍTICO: Pegar o hash da resposta
                                validade_link = resposta_api.get('validade_link')  # ✅ Pegar validade do link
                                
                                print(f"   ✅ Enviado para API - ID Controle: {id_controle_api}")
                                print(f"   ✅ Link gerado: {link_upload}")
                                print(f"   ✅ Hash: {upload_hash}")
                                print(f"   ✅ Validade: {validade_link}")
                                
                                # Salvar id_controle, link, hash e validade no banco
                                with get_db_connection() as conn_update:
                                    cur_update = conn_update.cursor()
                                    cur_update.execute("""
                                        UPDATE envios_montagem 
                                        SET id_controle = %s, link_upload = %s, upload_hash = %s, validade_link = %s, data_envio_api = NOW()
                                        WHERE id = %s
                                    """, (id_controle_api, link_upload, upload_hash, validade_link, lote_id))
                                    conn_update.commit()
                            else:
                                print(f"   ⚠️ API retornou erro: {resposta_api.get('message')}")
                                print(f"   📦 Resposta completa: {resposta_api}")
                                link_upload = None
                        elif response_api.status_code == 409:
                            # Conflito - registro já existe
                            resposta_api = response_api.json()
                            link_existente = resposta_api.get('link')
                            hash_existente = resposta_api.get('hash')
                            id_controle_existente = resposta_api.get('id_controle') or resposta_api.get('existing_id')
                            
                            print(f"   ⚠️ Registro já existe na API (ID Controle: {id_controle_existente})")
                            
                            if link_existente:
                                # API retornou o link existente na resposta de conflito
                                link_upload = link_existente
                                upload_hash = hash_existente
                                id_controle_api = id_controle_existente
                                print(f"   ✅ Link recuperado da resposta: {link_upload}")
                                
                                # Atualizar banco com os dados recuperados
                                with get_db_connection() as conn_update:
                                    cur_update = conn_update.cursor()
                                    cur_update.execute("""
                                        UPDATE envios_montagem 
                                        SET id_controle = %s, link_upload = %s, upload_hash = %s
                                        WHERE id = %s
                                    """, (id_controle_api, link_upload, upload_hash, lote_id))
                                    conn_update.commit()
                            else:
                                # Se não veio link na resposta, buscar do banco
                                print(f"   🔍 Buscando link existente no banco...")
                                with get_db_connection() as conn_link:
                                    cur_link = conn_link.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                                    cur_link.execute("""
                                        SELECT link_upload, id_controle, upload_hash
                                        FROM envios_montagem 
                                        WHERE id = %s
                                    """, (lote_id,))
                                    registro_existente = cur_link.fetchone()
                                    
                                    if registro_existente and registro_existente['link_upload']:
                                        link_upload = registro_existente['link_upload']
                                        upload_hash = registro_existente['upload_hash']
                                        print(f"   ✅ Link recuperado do banco: {link_upload}")
                                    else:
                                        print(f"   ❌ Link não encontrado! Tentando recriar na API...")
                                        # Tentar com ID diferente (adicionar timestamp)
                                        import time
                                        lote_id_novo = int(f"{lote_id}{int(time.time()) % 1000}")
                                        payload_api["lote_id"] = lote_id_novo
                                        
                                        response_retry = requests.post(
                                            API_UPLOAD_URL,
                                            json=payload_api,
                                            headers=headers_api,
                                            timeout=10,
                                            verify=False
                                        )
                                        
                                        if response_retry.status_code in [200, 201]:
                                            resposta_retry = response_retry.json()
                                            if resposta_retry.get('success'):
                                                link_upload = resposta_retry.get('link')
                                                upload_hash = resposta_retry.get('hash')
                                                id_controle_api = resposta_retry.get('id_controle')
                                                print(f"   ✅ Novo link gerado: {link_upload}")
                                                
                                                # Atualizar banco
                                                with get_db_connection() as conn_update:
                                                    cur_update = conn_update.cursor()
                                                    cur_update.execute("""
                                                        UPDATE envios_montagem 
                                                        SET id_controle = %s, link_upload = %s, upload_hash = %s
                                                        WHERE id = %s
                                                    """, (id_controle_api, link_upload, upload_hash, lote_id))
                                                    conn_update.commit()
                                            else:
                                                link_upload = None
                                        else:
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
                        import re
                        API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
                        
                        # Extrair mês/ano do período (API exige formato MM/AAAA)
                        periodo_api = periodo
                        if "/" in periodo and len(periodo) > 7:
                            # Se for range de datas (ex: "05/10/2025 – 22/10/2025"), extrair a primeira data
                            match = re.search(r'(\d{2})/(\d{2})/(\d{4})', periodo)
                            if match:
                                dia, mes, ano = match.groups()
                                periodo_api = f"{mes}/{ano}"  # Formato MM/AAAA
                            else:
                                # Fallback: pegar só MM/AAAA se já estiver nesse formato
                                match = re.search(r'(\d{2})/(\d{4})', periodo)
                                if match:
                                    periodo_api = periodo
                                else:
                                    # Último fallback: usar mês/ano atual
                                    periodo_api = datetime.now().strftime("%m/%Y")
                        elif "/" not in periodo:
                            # Se não tem barra, assumir que é só o ano
                            periodo_api = f"{periodo}/2025"
                        
                        print(f"   📅 Período original: {periodo}")
                        print(f"   📅 Período para API: {periodo_api}")
                        
                        # Preparar payload para API (usar lote_id real do banco)
                        payload_api = {
                            "nome": nome_destinatario,
                            "email": email_destino,
                            "periodo": periodo_api,
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
                        print(f"   📦 Payload enviado: {payload_api}")
                        
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
                                id_controle_api = resposta_api.get('id_controle') or resposta_api.get('id')
                                upload_hash = resposta_api.get('hash')  # ✅ CRÍTICO: Pegar o hash da resposta
                                print(f"   ✅ Link gerado: {link_upload}")
                                print(f"   ✅ ID Controle: {id_controle_api}")
                                print(f"   ✅ Hash: {upload_hash}")
                                
                                # Salvar link, id_controle e hash no lote
                                with get_db_connection() as conn_link:
                                    cur_link = conn_link.cursor()
                                    if tipo == "prestador":
                                        cur_link.execute("""
                                            UPDATE lotes_servico 
                                            SET link_upload = %s, id_controle = %s, upload_hash = %s, data_envio_api = NOW()
                                            WHERE id = %s
                                        """, (link_upload, id_controle_api, upload_hash, lote_id))
                                    else:
                                        cur_link.execute("""
                                            UPDATE envios_montagem 
                                            SET link_upload = %s, id_controle = %s, upload_hash = %s, data_envio_api = NOW()
                                            WHERE id = %s
                                        """, (link_upload, id_controle_api, upload_hash, lote_id))
                                    conn_link.commit()
                            else:
                                print(f"   ⚠️ API retornou erro: {resposta_api.get('message')}")
                                print(f"   📋 Resposta completa da API: {resposta_api}")
                                link_upload = None
                        else:
                            print(f"   ⚠️ API respondeu com status {response_api.status_code}")
                            print(f"   📋 Resposta completa da API: {response_api.text}")
                            link_upload = None
                    
                    except Exception as e:
                        print(f"   ⚠️ Erro ao gerar link (prestador): {e}")
                        import traceback
                        traceback.print_exc()
                        link_upload = None
                
                # Verificar se conseguiu gerar o link
                if not link_upload:
                    raise Exception("Falha ao gerar link de upload via API externa")
                
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
                    
                    # Gerar PDF usando template HTML original
                    print(f"   📄 Gerando PDF do prestador...")
                    
                    # Configurar caminhos das bibliotecas para WeasyPrint (macOS)
                    import os
                    import sys
                    import ctypes.util
                    
                    # Monkey patch para ctypes.util.find_library encontrar libs do Homebrew
                    _original_find_library = ctypes.util.find_library
                    
                    def _custom_find_library(name):
                        # Primeiro tenta o método original
                        result = _original_find_library(name)
                        if result:
                            return result
                        
                        # Se não encontrou, procura no Homebrew
                        homebrew_paths = [
                            f"/opt/homebrew/lib/lib{name}.dylib",
                            f"/opt/homebrew/opt/glib/lib/lib{name}.dylib",
                            f"/opt/homebrew/opt/pango/lib/lib{name}.dylib",
                            f"/opt/homebrew/opt/cairo/lib/lib{name}.dylib",
                            f"/opt/homebrew/opt/gdk-pixbuf/lib/lib{name}.dylib",
                        ]
                        
                        for path in homebrew_paths:
                            if os.path.exists(path):
                                return path
                        
                        return None
                    
                    ctypes.util.find_library = _custom_find_library
                    
                    from jinja2 import Template
                    from pathlib import Path
                    from weasyprint import HTML
                    import tempfile
                    import base64
                    
                    template_path = Path(__file__).parent.parent / "templates" / "invoice_template.html"
                    template_content = template_path.read_text(encoding='utf-8')
                    template = Template(template_content)
                    
                    # Carregar logo e converter para base64
                    logo_path = Path(__file__).parent.parent / "templates" / "LOGO-NOVO-MUNDO-PEQUENA.png"
                    if logo_path.exists():
                        with open(logo_path, 'rb') as f:
                            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
                            logo_data_uri = f"data:image/png;base64,{logo_base64}"
                    else:
                        logo_data_uri = ""
                    
                    # Preparar dados para o template
                    items_fmt = []
                    for item in itens:
                        data_exec = item.get('data_execucao', '')
                        if hasattr(data_exec, 'strftime'):
                            data_exec = data_exec.strftime('%d/%m/%Y')
                        
                        items_fmt.append({
                            "OS": item.get('o_s', ''),
                            "Cliente": item.get('cliente', '-'),
                            "Localidade": item.get('localidade', '-'),
                            "Modalidade": item.get('modalidade', ''),
                            "Data_execucao": str(data_exec),
                            "Valor": f"{float(item.get('valor_custo_prestador', item.get('valor', 0))):.2f}",
                            "Valor_extra": f"{float(item.get('valor_extra', 0)):.2f}",
                            "Motivo_valor_extra": item.get('motivo_extra', '-'),
                            "Valor_total": f"{float(item.get('valor_total', 0)):.2f}"
                        })
                    
                    context = {
                        "nome_prestador": nome_destinatario,
                        "periodo": periodo,
                        "lote_id": lote_id,
                        "items": items_fmt,
                        "total_geral": f"{total_geral:.2f}",
                        "logo_url": logo_data_uri
                    }
                    
                    # Renderizar HTML e converter para PDF
                    html_content = template.render(**context)
                    
                    # Criar nome do arquivo com nome do prestador
                    import os
                    nome_arquivo_limpo = nome_destinatario.replace(' ', '_').replace('/', '_')
                    pdf_filename = f"Relatorio_{nome_arquivo_limpo}_{lote_id}.pdf"
                    pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
                    
                    HTML(string=html_content).write_pdf(pdf_path)
                
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
                    pdf_path = gerar_pdf_montador_html_template(envio_data)
            
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
            
            # Enviar notificação WhatsApp se habilitado
            try:
                if enviar_whatsapp:
                    print(f"   📱 Enviando notificação WhatsApp...")
                    evento = 'envio_email_prestador' if tipo == 'prestador' else 'envio_email_montador'
                    
                    # Preparar variáveis para o template
                    if tipo == 'prestador':
                        valor_para_whatsapp = str(total_geral)
                        periodo_para_whatsapp = periodo
                    else:
                        valor_para_whatsapp = str(detalhes_json.get('total_geral', 0))
                        periodo_para_whatsapp = detalhes_json.get('periodo_relatorio', '')
                    
                    variaveis = {
                        'periodo': periodo_para_whatsapp,
                        'valor': valor_para_whatsapp,
                        'link': link_upload if link_upload else "",
                    }
                    
                    if tipo == 'prestador':
                        variaveis['nome_prestador'] = nome_destinatario
                    else:
                        variaveis['nome_montador'] = nome_destinatario
                    
                    resultado_whatsapp = enviar_notificacao_whatsapp(
                        evento=evento,
                        destinatario_id=destinatario_id,
                        tipo=tipo,
                        variaveis=variaveis
                    )
                    
                    if resultado_whatsapp.get('success'):
                        if resultado_whatsapp.get('queued'):
                            print(f"   ✅ WhatsApp enfileirado (servidor offline)")
                        else:
                            print(f"   ✅ WhatsApp enviado com sucesso!")
                    else:
                        print(f"   ⚠️ WhatsApp não enviado: {resultado_whatsapp.get('message')}")
            except Exception as e:
                print(f"   ⚠️ Erro ao enviar WhatsApp: {str(e)}")
                # Não falha o envio do email se WhatsApp der erro
                
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
            
            items = cur.fetchall()
            
            # Extrair campos do JSONB detalhes para facilitar acesso no frontend
            result = []
            for item in items:
                detalhes = item.get('detalhes', {}) or {}
                
                result.append({
                    'id': item['id'],
                    'os_numero': item['os_numero'],
                    'prestador_nome': item['prestador_nome'],
                    'cliente': detalhes.get('cliente', detalhes.get('Cliente', '')),
                    'servico': detalhes.get('servico', detalhes.get('Servico', detalhes.get('tipo_servico', detalhes.get('modalidade', '')))),
                    'endereco': detalhes.get('endereco', detalhes.get('Endereco', '')),
                    'valor_total': detalhes.get('valor_total', detalhes.get('valor_custo_prestador', detalhes.get('valor', 0))),
                    'valor_extra': detalhes.get('valor_extra', 0),
                    'detalhes': detalhes  # Manter detalhes completo como fallback
                })
            
            return result
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
                        'boletim': item.get('boletim', item.get('identificador_boletim_montagem', '')),
                        'data_montagem': item.get('data_montagem', item.get('data_da_montagem', '')),
                        'cliente': item.get('cliente', item.get('nome_do_cliente', '')),
                        'nome_produto': item.get('nome_produto', ''),
                        'valor_venda': item.get('valor_venda', item.get('media_de_valor_venda', 0)),
                        'comissao_calculada': item.get('comissao_calculada', item.get('comissao', 0)),
                        'comissao_editada': item.get('comissao_editada'),
                        'adicional': item.get('adicional', 0),
                        'motivo_valor_extra': item.get('motivo_valor_extra', item.get('motivo', '')),
                        'montador_nome': result['montador_nome']
                    }
                    for idx, item in enumerate(items_list)
                ]
            return []


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
