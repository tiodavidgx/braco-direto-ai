"""
Rotas de Relatórios e Envio de Email
Gera PDFs e envia por email usando Microsoft Graph API
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional
import os
import requests
from jinja2 import Template
from pathlib import Path
import base64
from datetime import datetime, timedelta
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

def converter_data_excel(data_value):
    """
    Converte data do Excel (número serial) ou outros formatos para dd/mm/yyyy
    Excel armazena datas como dias desde 30/12/1899
    """
    if data_value is None or data_value == '':
        return ''
    
    # Se já é um objeto datetime
    if hasattr(data_value, 'strftime'):
        return data_value.strftime('%d/%m/%Y')
    
    # Se é número (int ou float) - número serial do Excel
    if isinstance(data_value, (int, float)):
        try:
            # Excel date serial number (dias desde 30/12/1899)
            excel_epoch = datetime(1899, 12, 30)
            dt = excel_epoch + timedelta(days=float(data_value))
            return dt.strftime('%d/%m/%Y')
        except:
            return str(data_value)
    
    # Se é string
    if isinstance(data_value, str):
        data_str = data_value.strip()
        
        # Se é string numérica (ex: "45983")
        if data_str.replace('.', '').isdigit():
            try:
                excel_epoch = datetime(1899, 12, 30)
                dt = excel_epoch + timedelta(days=float(data_str))
                return dt.strftime('%d/%m/%Y')
            except:
                pass
        
        # Se é formato ISO (2025-11-03 ou 2025-11-03T00:00:00)
        if '-' in data_str:
            try:
                dt = datetime.strptime(data_str.split('T')[0], '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
            except:
                pass
        
        # Se já está no formato correto dd/mm/yyyy
        if '/' in data_str:
            return data_str
    
    return str(data_value)

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
        
        # Usar função de conversão de data do Excel
        data_exec_str = converter_data_excel(data_exec)
        
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
        'Data de\nExecução',
        'Valor\n(R$)',
        'Valor\nExtra (R$)',
        'Motivo Valor\nExtra',
        'Valor\nTotal (R$)'
    ]]
    
    # Estilo para células com texto longo (permite quebra de linha)
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Helvetica',
        leading=9,
        wordWrap='CJK'
    )
    
    # Adicionar dados
    for item in items_fmt:
        table_data.append([
            item['OS'],
            Paragraph(str(item['Cliente'] or '-'), cell_style),
            Paragraph(str(item['Localidade'] or '-'), cell_style),
            Paragraph(str(item['Modalidade'] or '-'), cell_style),
            item['Data_execucao'],
            f"{item['Valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"{item['Valor_extra']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            Paragraph(str(item['Motivo_valor_extra'] or '-'), cell_style),
            f"{item['Valor_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        ])
    
    # Larguras otimizadas para caber em A4 landscape (267mm útil) - Total: 235mm (margem extra)
    col_widths = [15*mm, 28*mm, 22*mm, 45*mm, 17*mm, 20*mm, 20*mm, 45*mm, 23*mm]
    
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
            'motivo_valor_extra': item.get('motivo_valor_extra', item.get('motivo', '')),
            'tipo_servico': item.get('tipo_servico', 'MONTAGEM')
        })
    
    # Contexto para o template
    ctx = {
        "nome_montador": envio_data.get('nome_montador', envio_data.get('montador_nome', 'N/A')),
        "periodo_relatorio": envio_data.get('periodo_relatorio', envio_data.get('periodo', 'N/A')),
        "percentual_comissao": float(envio_data.get('percentual_comissao', 0)),
        "percentual_montagem": float(envio_data.get('percentual_montagem', 0.05)),
        "percentual_assistencia": float(envio_data.get('percentual_assistencia', 0.05)),
        "percentual_desmontagem": float(envio_data.get('percentual_desmontagem', 0.05)),
        "items": items_para_pdf,
        "total_comissao": float(envio_data.get('total_comissao', 0)),
        "total_montagem": float(envio_data.get('total_montagem', 0)),
        "total_assistencia": float(envio_data.get('total_assistencia', 0)),
        "total_desmontagem": float(envio_data.get('total_desmontagem', 0)),
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

def enviar_email_graph(destinatario: str, assunto: str, corpo_html: str, anexo_path: str = None, cc: str = None):
    """
    Envia email usando Microsoft Graph API
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo_html: Corpo do email em HTML
        anexo_path: Caminho do arquivo PDF para anexar (opcional)
        cc: Email(s) para cópia (opcional) - separados por vírgula ou ponto-e-vírgula
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
    
    # Adicionar CC se fornecido
    if cc and cc.strip():
        # Separar múltiplos emails por vírgula ou ponto-e-vírgula
        cc_emails = [e.strip() for e in cc.replace(';', ',').split(',') if e.strip()]
        if cc_emails:
            message["ccRecipients"] = [
                {"emailAddress": {"address": email}} for email in cc_emails
            ]
            print(f"      CC: {', '.join(cc_emails)}")
    
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
                    data_exec = converter_data_excel(os_item.get('data_execucao', ''))
                    
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
                    data_montagem = converter_data_excel(montagem.get('data_montagem', ''))
                    
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
                        "cliente": montagem.get('cliente', '') or '-',
                        "nome_produto": montagem.get('produto', '') or '-',
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
    
    print(f"\n{'='*60}")
    print(f"� REQUISIÇÃO RECEBIDA - enviar-lote")
    print(f"   Tipo: {tipo}")
    print(f"   Total de registros: {len(dados)}")
    print(f"   enviarWhatsApp: {enviar_whatsapp}")
    
    # Debug dos dados recebidos
    for i, item in enumerate(dados[:5]):  # Mostrar até 5 primeiros
        print(f"\n   📋 Registro {i+1}:")
        print(f"      identificador_do_montador: {item.get('identificador_do_montador', 'NÃO ENCONTRADO')}")
        print(f"      nome_do_montador: {item.get('nome_do_montador', 'NÃO ENCONTRADO')}")
        print(f"      boletim: {item.get('identificador_boletim_montagem', 'NÃO ENCONTRADO')}")
    print(f"{'='*60}\n")
    
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
    else:  # montador - agrupar por identificador
        for item in dados:
            identificador = item.get("identificador_do_montador")
            if identificador not in grupos:
                grupos[identificador] = []
            grupos[identificador].append(item)
    
    # Enviar email para cada grupo
    for chave_destinatario, itens in grupos.items():
        nome_destinatario = str(chave_destinatario)  # Inicializar com a chave
        try:
            # DEBUG: Verificar se motivo_valor_extra está nos itens
            if tipo == "montador":
                print(f"\n🔍 DEBUG - Itens recebidos para identificador {chave_destinatario}:")
                for idx, item in enumerate(itens):
                    print(f"   Item {idx+1}: adicional={item.get('adicional', 0)}, motivo={item.get('motivo_valor_extra', 'N/A')}")
            
            # Buscar email do destinatário no banco
            with get_db_connection() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                if tipo == "prestador":
                    cur.execute("SELECT id, email, tempo_vencimento_dias, nome FROM prestadores WHERE nome = %s", (chave_destinatario,))
                else:
                    # Buscar montador pelo identificador
                    cur.execute("SELECT id, email, tempo_vencimento_dias, nome FROM montadores WHERE identificador = %s", (chave_destinatario,))
                
                resultado = cur.fetchone()
                
                if not resultado:
                    print(f"❌ Identificador {chave_destinatario}: Montador não encontrado no banco")
                    erros += len(itens)
                    erros_detalhes.append({
                        "identificador": chave_destinatario,
                        "erro": "Montador não encontrado no banco de dados pelo identificador"
                    })
                    continue
                
                destinatario_id = resultado["id"]
                nome_destinatario = resultado["nome"]  # Pegar o nome do banco
                email_destino = resultado["email"]
                tempo_vencimento_dias = resultado.get("tempo_vencimento_dias")
                
                # === CRIAR LOTE NO BANCO ANTES DO ENVIO ===
                total_geral = sum(float(item.get("valor_total", 0)) for item in itens)
                lote_id = None
                custos_extras_ids = []  # Inicializar vazio para todos os tipos
                
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
                    
                    # === BUSCAR CUSTOS EXTRAS PENDENTES PARA ESTE MONTADOR ===
                    custos_extras_total = 0
                    custos_extras_ids = []
                    
                    # Buscar o identificador do montador
                    cur.execute("SELECT identificador FROM montadores WHERE id = %s", (destinatario_id,))
                    montador_info_ident = cur.fetchone()
                    identificador_montador = montador_info_ident['identificador'] if montador_info_ident else str(destinatario_id)
                    
                    print(f"   🔍 Buscando custos extras para montador ID={destinatario_id}, identificador={identificador_montador}")
                    
                    # Buscar por identificador do montador OU montador_id
                    cur.execute("""
                        SELECT id, identificador_boletim, valor, motivo 
                        FROM custos_extras 
                        WHERE (identificador_montador = %s OR montador_id = %s) AND status = 'pendente'
                    """, (identificador_montador, destinatario_id))
                    custos_extras_montador = cur.fetchall()
                    
                    # Também buscar pelos boletins que estão sendo enviados
                    boletins_envio = [item.get('identificador_boletim_montagem', '') for item in itens if item.get('identificador_boletim_montagem')]
                    if boletins_envio:
                        placeholders = ','.join(['%s'] * len(boletins_envio))
                        cur.execute(f"""
                            SELECT id, identificador_boletim, valor, motivo 
                            FROM custos_extras 
                            WHERE identificador_boletim IN ({placeholders}) AND status = 'pendente'
                        """, boletins_envio)
                        custos_extras_boletins = cur.fetchall()
                    else:
                        custos_extras_boletins = []
                    
                    # Combinar resultados únicos (evitar duplicados)
                    custos_extras_dict = {}
                    for ce in list(custos_extras_montador) + list(custos_extras_boletins):
                        if ce['id'] not in custos_extras_dict:
                            custos_extras_dict[ce['id']] = ce
                    
                    custos_extras_list = list(custos_extras_dict.values())
                    # NÃO marcar todos como processados de cara - apenas os que forem realmente aplicados
                    custos_extras_ids_aplicados = set()
                    
                    # Criar mapa de custos extras por boletim
                    custos_extras_por_boletim = {}
                    for ce in custos_extras_list:
                        boletim = ce['identificador_boletim'].strip() if ce['identificador_boletim'] else ''
                        if boletim not in custos_extras_por_boletim:
                            custos_extras_por_boletim[boletim] = []
                        custos_extras_por_boletim[boletim].append(ce)
                    
                    # Aplicar custos extras diretamente nos items_processados
                    # EXCETO para boletins de ajuste (A-*) que já vêm do frontend com o valor
                    for item in items_processados:
                        boletim_item = item['boletim']
                        # Pular boletins de ajuste - eles já vêm com o valor do frontend
                        if boletim_item.startswith('A-'):
                            continue
                        if boletim_item in custos_extras_por_boletim:
                            for ce in custos_extras_por_boletim[boletim_item]:
                                # Somar ao adicional existente
                                item['adicional'] = float(item.get('adicional', 0)) + float(ce['valor'])
                                # Concatenar motivo (se já tiver motivo, adicionar separado por "; ")
                                motivo_existente = item.get('motivo_valor_extra', '')
                                motivo_novo = ce['motivo']
                                if motivo_existente and motivo_novo:
                                    item['motivo_valor_extra'] = f"{motivo_existente}; {motivo_novo}"
                                elif motivo_novo:
                                    item['motivo_valor_extra'] = motivo_novo
                                custos_extras_ids_aplicados.add(ce['id'])
                                print(f"      ✅ Aplicado custo extra no boletim {boletim_item}: +R$ {float(ce['valor']):.2f} ({ce['motivo']})")
                    
                    # === ADICIONAR BOLETINS DE AJUSTE (A-YYYY-XXXX) COMO ITENS SEPARADOS ===
                    # Apenas se não existirem já nos items_processados (evita duplicação quando vem do frontend)
                    boletins_existentes = set(item['boletim'] for item in items_processados)
                    
                    for boletim_ajuste, custos_ajuste in custos_extras_por_boletim.items():
                        # Verificar se é um boletim de ajuste (começa com A-) E não existe ainda
                        if boletim_ajuste.startswith('A-') and boletim_ajuste not in boletins_existentes:
                            for ce in custos_ajuste:
                                # Criar item fictício para o boletim de ajuste
                                item_ajuste = {
                                    "boletim": boletim_ajuste,
                                    "data_montagem": datetime.now().strftime("%d/%m/%Y"),
                                    "cliente": "AJUSTE",
                                    "nome_produto": ce['motivo'],
                                    "valor_venda": 0,
                                    "comissao_calculada": 0,
                                    "comissao_editada": None,
                                    "adicional": float(ce['valor']),
                                    "motivo_valor_extra": ce['motivo'],
                                    "tipo_servico": "MONTAGEM"
                                }
                                items_processados.append(item_ajuste)
                                custos_extras_ids_aplicados.add(ce['id'])
                                print(f"      ✅ Adicionado boletim de ajuste {boletim_ajuste}: +R$ {float(ce['valor']):.2f} ({ce['motivo']})")
                    
                    # Também marcar boletins de ajuste que JÁ vieram do frontend (já existiam nos items)
                    for item in items_processados:
                        boletim_item = item.get('boletim', '')
                        if boletim_item.startswith('A-') and boletim_item in custos_extras_por_boletim:
                            for ce in custos_extras_por_boletim[boletim_item]:
                                custos_extras_ids_aplicados.add(ce['id'])
                    
                    # Só marcar como processado os custos extras que foram realmente aplicados
                    custos_extras_ids = list(custos_extras_ids_aplicados)
                    
                    # Recalcular total de adicionais após aplicar custos extras
                    total_adicionais = sum(float(item.get('adicional', 0)) for item in items_processados)
                    custos_extras_total = total_adicionais  # Agora está incluído no total_adicionais
                    
                    if custos_extras_ids:
                        print(f"   💰 {len(custos_extras_ids)} custos extras aplicados nos items (de {len(custos_extras_list)} encontrados)")
                    
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
                        API_UPLOAD_URL = "https://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = os.getenv("API_UPLOAD_KEY", "")
                        
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
                
                # Preparar assunto, corpo e CC do email
                assunto = email_config.get("assunto", "Relatório de Serviços")
                corpo = email_config.get("corpo", "Segue relatório em anexo.")
                cc_email = email_config.get("cc", "")
                
                # Gerar link de upload via API externa (SOMENTE SE NÃO FOI GERADO ACIMA para montador)
                if link_upload is None and tipo == "prestador":
                    id_controle_api = None
                    try:
                        import requests
                        import re
                        API_UPLOAD_URL = "https://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = os.getenv("API_UPLOAD_KEY", "")
                        
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
                                "data_execucao": converter_data_excel(item.get("data_execucao", "")),
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
                        data_exec = converter_data_excel(item.get('data_execucao', ''))
                        
                        items_fmt.append({
                            "OS": item.get('o_s', ''),
                            "Cliente": item.get('cliente', '-'),
                            "Localidade": item.get('localidade', '-'),
                            "Modalidade": item.get('modalidade', ''),
                            "Data_execucao": data_exec,
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
            if cc_email:
                print(f"   CC: {cc_email}")
            
            # Enviar email com PDF anexado
            enviar_email_graph(
                destinatario=email_destino,
                assunto=assunto,
                corpo_html=f"<html><body>{corpo_html}</body></html>",
                anexo_path=pdf_path,
                cc=cc_email
            )
            
            sucesso += len(itens)
            print(f"   ✅ Email enviado com sucesso com PDF anexado!")
            print(f"   ✅ Lote #{lote_id} registrado com {len(itens)} itens")
            
            # === MARCAR CUSTOS EXTRAS COMO PROCESSADOS ===
            if tipo == "montador" and custos_extras_ids:
                try:
                    with get_db_connection() as conn_custos:
                        cur_custos = conn_custos.cursor()
                        placeholders = ','.join(['%s'] * len(custos_extras_ids))
                        cur_custos.execute(f"""
                            UPDATE custos_extras 
                            SET status = 'processado', processado_em = NOW() 
                            WHERE id IN ({placeholders})
                        """, custos_extras_ids)
                        conn_custos.commit()
                        print(f"   ✅ {len(custos_extras_ids)} custos extras marcados como processados")
                except Exception as e:
                    print(f"   ⚠️ Erro ao marcar custos extras como processados: {e}")
            
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
            nome_erro = nome_destinatario if 'nome_destinatario' in dir() else chave_destinatario
            print(f"   ❌ Erro ao enviar para {nome_erro}: {str(e)}")
            print(f"   Stack trace: {traceback.format_exc()}")
            erros += len(itens)
            erros_detalhes.append({
                "nome": nome_erro,
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
                        'cliente': item.get('cliente', item.get('nome_do_cliente', '')) or '-',
                        'nome_produto': item.get('nome_produto', '') or '-',
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


@router.get("/historico/buscar")
def buscar_os_ou_boletim(q: str = Query(..., description="Número da OS ou boletim para buscar")):
    """
    Busca uma O.S. ou boletim e retorna o lote correspondente
    
    Args:
        q: Número da O.S. ou boletim (busca parcial)
    
    Returns:
        Lista de lotes que contêm a O.S. ou boletim buscado
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Termo de busca deve ter pelo menos 2 caracteres")
    
    termo = q.strip().lower()
    resultados = []
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Buscar nas O.S. enviadas (prestadores)
        cur.execute("""
            SELECT 
                os.os_numero,
                os.lote_id,
                l.prestador_nome,
                l.periodo,
                l.valor_total,
                l.data_envio,
                l.status,
                'prestador' as tipo
            FROM os_enviadas os
            JOIN lotes_servico l ON l.id = os.lote_id
            WHERE LOWER(os.os_numero) LIKE %s
            ORDER BY l.data_envio DESC
        """, (f"%{termo}%",))
        
        for row in cur.fetchall():
            resultados.append({
                'lote_id': row['lote_id'],
                'tipo': 'prestador',
                'nome': row['prestador_nome'],
                'periodo': row['periodo'],
                'valor_total': float(row['valor_total']) if row['valor_total'] else 0,
                'data_envio': row['data_envio'].isoformat() if row['data_envio'] else None,
                'status': row['status'],
                'item_encontrado': row['os_numero'],
                'tipo_item': 'OS'
            })
        
        # 2. Buscar nos envios de montagem (boletins estão no JSONB detalhes)
        cur.execute("""
            SELECT 
                em.id,
                em.montador_nome,
                em.periodo,
                em.valor_total,
                em.data_envio,
                em.status,
                em.detalhes
            FROM envios_montagem em
            WHERE em.detalhes IS NOT NULL
            ORDER BY em.data_envio DESC
        """)
        
        for row in cur.fetchall():
            detalhes = row.get('detalhes', {}) or {}
            items = detalhes.get('items', [])
            
            for item in items:
                boletim = str(item.get('boletim', item.get('identificador_boletim_montagem', ''))).lower()
                if termo in boletim:
                    resultados.append({
                        'lote_id': row['id'],
                        'tipo': 'montador',
                        'nome': row['montador_nome'],
                        'periodo': row['periodo'],
                        'valor_total': float(row['valor_total']) if row['valor_total'] else 0,
                        'data_envio': row['data_envio'].isoformat() if row['data_envio'] else None,
                        'status': row['status'],
                        'item_encontrado': item.get('boletim', item.get('identificador_boletim_montagem', '')),
                        'tipo_item': 'Boletim'
                    })
                    break  # Só precisamos saber que este lote contém o boletim
    
    # Remover duplicatas (mesmo lote pode aparecer mais de uma vez se busca for muito ampla)
    lotes_vistos = set()
    resultados_unicos = []
    for r in resultados:
        chave = f"{r['tipo']}_{r['lote_id']}"
        if chave not in lotes_vistos:
            lotes_vistos.add(chave)
            resultados_unicos.append(r)
    
    return resultados_unicos


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
    Também reabre os custos extras que foram processados nesse envio
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Primeiro, buscar os detalhes do envio para obter os boletins
            cur.execute('SELECT detalhes, montador_id FROM envios_montagem WHERE id = %s', (envio_id,))
            envio = cur.fetchone()
            
            if not envio:
                raise HTTPException(status_code=404, detail="Envio não encontrado")
            
            # Extrair boletins dos items do envio
            boletins = []
            montador_id = envio.get('montador_id')
            if envio.get('detalhes') and envio['detalhes'].get('items'):
                boletins = [item.get('boletim') for item in envio['detalhes']['items'] if item.get('boletim')]
            
            print(f"🗑️ Excluindo envio #{envio_id} - Boletins: {boletins}")
            
            # Reabrir custos extras relacionados aos boletins deste envio
            if boletins:
                placeholders = ','.join(['%s'] * len(boletins))
                cur.execute(f"""
                    UPDATE custos_extras 
                    SET status = 'pendente', processado_em = NULL 
                    WHERE identificador_boletim IN ({placeholders}) AND status = 'processado'
                    RETURNING id, identificador_boletim
                """, boletins)
                reabertos = cur.fetchall()
                if reabertos:
                    print(f"   ✅ {len(reabertos)} custos extras reabertos: {[r['identificador_boletim'] for r in reabertos]}")
            
            # Também reabrir custos extras pelo montador_id (caso existam sem boletim específico)
            if montador_id:
                cur.execute("""
                    UPDATE custos_extras 
                    SET status = 'pendente', processado_em = NULL 
                    WHERE montador_id = %s AND status = 'processado' 
                      AND (identificador_boletim IS NULL OR identificador_boletim = '')
                    RETURNING id
                """, (montador_id,))
                reabertos_montador = cur.fetchall()
                if reabertos_montador:
                    print(f"   ✅ {len(reabertos_montador)} custos extras do montador reabertos")
            
            # Deletar notificações relacionadas primeiro (por lote_id e por envio_montagem_id)
            cur.execute('DELETE FROM notificacoes WHERE lote_id = %s AND tipo LIKE %s', (envio_id, '%montagem%'))
            cur.execute('DELETE FROM notificacoes WHERE envio_montagem_id = %s', (envio_id,))
            
            # Deletar cards do Trello relacionados (se a tabela existir)
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'trello_cards'
                )
            """)
            if cur.fetchone()['exists']:
                cur.execute('DELETE FROM trello_cards WHERE lote_id = %s', (envio_id,))
                cur.execute('DELETE FROM trello_cards WHERE envio_montagem_id = %s', (envio_id,))
            
            # Deletar o envio de montagem
            cur.execute('DELETE FROM envios_montagem WHERE id = %s RETURNING id', (envio_id,))
            deleted = cur.fetchone()
            
            conn.commit()
            
        return {"success": True, "message": f"Envio de montagem #{envio_id} excluído com sucesso. Custos extras reabertos."}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar envio: {str(e)}")


# ===== DOWNLOAD DE RELATÓRIO PDF =====

@router.get("/download-relatorio/{tipo}/{lote_id}")
def download_relatorio_pdf(tipo: str, lote_id: int):
    """
    Gera ou retorna o PDF do relatório enviado por email
    
    Args:
        tipo: 'prestador' ou 'montador'
        lote_id: ID do lote/envio
    
    Returns:
        PDF do relatório
    """
    from fastapi.responses import FileResponse
    from app.database import get_db_connection
    import psycopg2.extras
    import os
    import tempfile
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == "prestador":
            # Buscar lote de prestador
            cur.execute("""
                SELECT l.*, p.email
                FROM lotes_servico l
                LEFT JOIN prestadores p ON p.id = l.prestador_id
                WHERE l.id = %s
            """, (lote_id,))
            
            lote = cur.fetchone()
            if not lote:
                raise HTTPException(status_code=404, detail="Lote não encontrado")
            
            # Buscar O.S. do lote
            cur.execute("""
                SELECT os_numero, detalhes
                FROM os_enviadas
                WHERE lote_id = %s
                ORDER BY os_numero
            """, (lote_id,))
            os_list = cur.fetchall()
            
            # Verificar se já existe PDF salvo
            pdf_path = None
            nome_arquivo_limpo = lote['prestador_nome'].replace(' ', '_').replace('/', '_').replace('\\', '_')
            pdf_filename = f"Relatorio_{nome_arquivo_limpo}_{lote_id}.pdf"
            
            # Pasta de uploads - Path(__file__) = app/routes/relatorios.py
            # .parent.parent.parent = backend_example/
            uploads_dir = Path(__file__).parent.parent.parent / 'uploads' / 'relatorios'
            uploads_dir.mkdir(parents=True, exist_ok=True)
            permanent_path = uploads_dir / pdf_filename
            
            # Verificar se existe o PDF original no /tmp/ (enviado por email)
            tmp_path = Path(tempfile.gettempdir()) / pdf_filename
            # Também verificar versão com _temp
            nome_arquivo_temp = f"Relatorio_{nome_arquivo_limpo}_temp.pdf"
            tmp_path_temp = Path(tempfile.gettempdir()) / nome_arquivo_temp
            
            # Se existir no tmp, copiar para permanente
            if tmp_path.exists() and not permanent_path.exists():
                import shutil
                shutil.copy(tmp_path, permanent_path)
            elif tmp_path_temp.exists() and not permanent_path.exists():
                import shutil
                shutil.copy(tmp_path_temp, permanent_path)
            
            # Se não existe em lugar nenhum, gerar o PDF
            if not permanent_path.exists():
                # Carregar template - Path(__file__) = app/routes/relatorios.py
                # Então .parent.parent = app/, e templates está em app/templates/
                template_path = Path(__file__).parent.parent / 'templates' / 'invoice_template.html'
                
                if not template_path.exists():
                    raise HTTPException(status_code=500, detail=f"Template de relatório não encontrado em {template_path}")
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_str = f.read()
                template = Template(template_str)
                
                # Logo
                logo_path = Path(__file__).parent.parent / 'templates' / 'hapvida-novo-mundo.png'
                
                logo_data_uri = ""
                if logo_path.exists():
                    with open(logo_path, 'rb') as f:
                        logo_b64 = base64.b64encode(f.read()).decode('utf-8')
                        logo_data_uri = f"data:image/png;base64,{logo_b64}"
                
                # Formatar itens
                items_fmt = []
                for os_item in os_list:
                    detalhes = os_item.get('detalhes', {}) or {}
                    items_fmt.append({
                        "OS_numero": os_item['os_numero'],
                        "Cliente": detalhes.get('cliente', detalhes.get('Cliente', '-')),
                        "Data_execucao": detalhes.get('data_execucao', detalhes.get('Data_execucao', '-')),
                        "Valor": f"{float(detalhes.get('valor_custo_prestador', detalhes.get('valor_total', 0))):.2f}",
                        "Valor_extra": f"{float(detalhes.get('valor_extra', 0)):.2f}",
                        "Motivo_valor_extra": detalhes.get('motivo_extra', '-'),
                        "Valor_total": f"{float(detalhes.get('valor_total', detalhes.get('valor_custo_prestador', 0))):.2f}"
                    })
                
                context = {
                    "nome_prestador": lote['prestador_nome'],
                    "periodo": lote['periodo'],
                    "lote_id": lote['id'],
                    "items": items_fmt,
                    "total_geral": f"{float(lote['valor_total']):.2f}",
                    "logo_url": logo_data_uri
                }
                
                html_content = template.render(**context)
                
                # Gerar PDF
                try:
                    from weasyprint import HTML
                    HTML(string=html_content).write_pdf(str(permanent_path))
                except ImportError:
                    # Fallback para xhtml2pdf
                    from xhtml2pdf import pisa
                    with open(permanent_path, 'wb') as pdf_file:
                        pisa.CreatePDF(html_content, dest=pdf_file)
            
            return FileResponse(
                path=str(permanent_path),
                filename=pdf_filename,
                media_type='application/pdf'
            )
            
        else:  # montador
            # Buscar envio de montador
            cur.execute("""
                SELECT em.*, m.nome as montador_nome, m.email, m.cpf_cnpj,
                       m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
                WHERE em.id = %s
            """, (lote_id,))
            
            envio = cur.fetchone()
            if not envio:
                raise HTTPException(status_code=404, detail="Envio não encontrado")
            
            # Verificar se já existe PDF salvo
            nome_arquivo_limpo = envio['montador_nome'].replace(' ', '_').replace('/', '_').replace('\\', '_')
            pdf_filename = f"Relatorio_{nome_arquivo_limpo}_{lote_id}.pdf"
            
            # Pasta de uploads - backend_example/uploads/relatorios
            uploads_dir = Path(__file__).parent.parent.parent / 'uploads' / 'relatorios'
            uploads_dir.mkdir(parents=True, exist_ok=True)
            permanent_path = uploads_dir / pdf_filename
            
            if not permanent_path.exists():
                # Gerar PDF do montador
                envio_data = dict(envio)
                envio_data['id'] = lote_id
                
                try:
                    pdf_path = gerar_pdf_montador(envio_data)
                    # Copiar para pasta permanente
                    import shutil
                    shutil.copy(pdf_path, permanent_path)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
            
            return FileResponse(
                path=str(permanent_path),
                filename=pdf_filename,
                media_type='application/pdf'
            )


# ============================================================================
# ENDPOINTS DE EDIÇÃO E REENVIO DE RELATÓRIOS
# ============================================================================

@router.get("/envio/{envio_id}/editar-detalhes")
def get_envio_para_editar(envio_id: int, tipo: str = Query(..., description="Tipo: 'prestador' ou 'montador'")):
    """
    Retorna os detalhes completos de um envio para edição
    Inclui os items atuais e dados do montador para adicionar novos
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == "montador":
            # Buscar envio de montador
            cur.execute("""
                SELECT em.*, m.nome as montador_nome, m.email, m.telefone, m.identificador,
                       m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
                WHERE em.id = %s
            """, (envio_id,))
            
            envio = cur.fetchone()
            if not envio:
                raise HTTPException(status_code=404, detail="Envio não encontrado")
            
            # Extrair items do detalhes JSONB
            detalhes = envio.get('detalhes', {}) or {}
            items_atuais = detalhes.get('items', [])
            
            # Adicionar índice para identificação
            for idx, item in enumerate(items_atuais):
                item['idx'] = idx
                item['selecionado'] = True
            
            # Nota: No sistema atual, os boletins não são armazenados em tabela separada
            # Eles vêm direto do Excel no momento do envio
            # Por isso, não há como buscar "boletins disponíveis" para adicionar
            # A funcionalidade de edição permite apenas REMOVER items do envio existente
            boletins_disponiveis = []
            
            return {
                'envio_id': envio_id,
                'tipo': 'montador',
                'montador_id': envio['montador_id'],
                'montador_nome': envio['montador_nome'],
                'email': envio['email'],
                'telefone': envio.get('telefone'),
                'periodo': envio['periodo'],
                'valor_total': float(envio['valor_total'] or 0),
                'quantidade_os': envio['quantidade_os'],
                'data_envio': envio['data_envio'].isoformat() if envio['data_envio'] else None,
                'status': envio['status'],
                'items_atuais': items_atuais,
                'boletins_disponiveis': boletins_disponiveis,
                'percentuais': {
                    'montagem': float(envio['percentual_montagem'] or 0),
                    'assistencia': float(envio['percentual_assistencia'] or 0),
                    'desmontagem': float(envio['percentual_desmontagem'] or 0)
                }
            }
        else:
            # Para prestador - estrutura similar
            cur.execute("""
                SELECT l.*, p.nome as prestador_nome, p.email
                FROM lotes_servico l
                JOIN prestadores p ON p.id = l.prestador_id
                WHERE l.id = %s
            """, (envio_id,))
            
            lote = cur.fetchone()
            if not lote:
                raise HTTPException(status_code=404, detail="Lote não encontrado")
            
            # Buscar OS do lote
            cur.execute("""
                SELECT id, os_numero, detalhes
                FROM os_enviadas
                WHERE lote_id = %s
            """, (envio_id,))
            
            os_items = cur.fetchall()
            items_atuais = []
            for os_item in os_items:
                detalhes = os_item.get('detalhes', {}) or {}
                items_atuais.append({
                    'id': os_item['id'],
                    'os_numero': os_item['os_numero'],
                    'cliente': detalhes.get('cliente', detalhes.get('Cliente', '-')),
                    'servico': detalhes.get('servico', detalhes.get('Servico', '-')),
                    'valor_total': detalhes.get('valor_total', detalhes.get('valor_custo_prestador', 0)),
                    'selecionado': True
                })
            
            return {
                'envio_id': envio_id,
                'tipo': 'prestador',
                'prestador_id': lote['prestador_id'],
                'prestador_nome': lote['prestador_nome'],
                'email': lote['email'],
                'periodo': lote['periodo'],
                'valor_total': float(lote['valor_total'] or 0),
                'quantidade_os': lote['quantidade_os'],
                'data_envio': lote['data_envio'].isoformat() if lote['data_envio'] else None,
                'status': lote['status'],
                'items_atuais': items_atuais,
                'os_disponiveis': []  # TODO: implementar busca de OS disponíveis se necessário
            }


@router.put("/envio/{envio_id}/editar-reenviar")
async def editar_e_reenviar_envio(envio_id: int, request: Request):
    """
    Edita um envio (adiciona/remove items) e reenvia o relatório por email
    
    Body esperado:
    {
        "tipo": "montador" ou "prestador",
        "items_selecionados": [...],  // items que devem permanecer no envio
        "email_destino": "email@exemplo.com"  // opcional, usa o cadastrado se não informado
    }
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    data = await request.json()
    tipo = data.get('tipo')
    items_selecionados = data.get('items_selecionados', [])
    email_destino_override = data.get('email_destino')
    
    if not items_selecionados:
        raise HTTPException(status_code=400, detail="Pelo menos um item deve ser selecionado")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == "montador":
            # Buscar envio e dados do montador
            cur.execute("""
                SELECT em.*, m.nome as montador_nome, m.email, m.telefone, m.identificador,
                       m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem,
                       m.tempo_vencimento_dias
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
                WHERE em.id = %s
            """, (envio_id,))
            
            envio = cur.fetchone()
            if not envio:
                raise HTTPException(status_code=404, detail="Envio não encontrado")
            
            email_destino = email_destino_override or envio['email']
            nome_destinatario = envio['montador_nome']
            
            # Percentuais - converter Decimal para float
            percentual_montagem = float(envio['percentual_montagem'] or 0)
            percentual_assistencia = float(envio['percentual_assistencia'] or 0)
            percentual_desmontagem = float(envio['percentual_desmontagem'] or 0)
            
            # Função para formatar data
            def format_data_para_pdf(data_raw):
                if not data_raw:
                    return ''
                if isinstance(data_raw, str):
                    formatos = ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']
                    for fmt in formatos:
                        try:
                            data_obj = datetime.strptime(str(data_raw).split('T')[0], fmt)
                            return data_obj.strftime('%d/%m/%Y')
                        except:
                            continue
                return str(data_raw)
            
            # Processar items e calcular totais
            items_processados = []
            total_montagem = 0
            total_assistencia = 0
            total_desmontagem = 0
            total_auxilio = 0
            
            for item in items_selecionados:
                # Pode vir do envio existente (já processado) ou novo (raw)
                tipo_servico = item.get('tipo_servico', 'MONTAGEM').upper()
                
                # Determinar valor_venda (pode estar em diferentes campos)
                valor_venda = float(item.get('valor_venda', item.get('media_de_valor_venda', 0)))
                
                # Determinar percentual baseado no tipo
                if 'ASSIST' in tipo_servico or 'TECNICA' in tipo_servico:
                    percentual = percentual_assistencia
                    tipo_servico = 'ASSISTENCIA_TECNICA'
                elif 'DESMONT' in tipo_servico:
                    percentual = percentual_desmontagem
                    tipo_servico = 'DESMONTAGEM'
                else:
                    percentual = percentual_montagem
                    tipo_servico = 'MONTAGEM'
                
                # Use comissão existente se disponível, senão calcule
                if item.get('comissao_editada') is not None:
                    comissao = float(item['comissao_editada'])
                elif item.get('comissao_calculada') is not None:
                    comissao = float(item['comissao_calculada'])
                else:
                    comissao = valor_venda * percentual
                
                # Somar ao total correto
                if tipo_servico == 'MONTAGEM':
                    total_montagem += comissao
                elif tipo_servico == 'ASSISTENCIA_TECNICA':
                    total_assistencia += comissao
                elif tipo_servico == 'DESMONTAGEM':
                    total_desmontagem += comissao
                
                items_processados.append({
                    "boletim": item.get('boletim', item.get('identificador_boletim_montagem', '')),
                    "data_montagem": format_data_para_pdf(item.get('data_montagem', item.get('data_da_montagem', ''))),
                    "cliente": item.get('cliente', item.get('nome_do_cliente', '-')),
                    "nome_produto": item.get('nome_produto', '-'),
                    "valor_venda": valor_venda,
                    "comissao_calculada": comissao,
                    "comissao_editada": item.get('comissao_editada'),
                    "adicional": float(item.get('adicional', 0)),
                    "motivo_valor_extra": item.get('motivo_valor_extra', item.get('motivo', '')),
                    "tipo_servico": tipo_servico
                })
            
            total_adicionais = sum(float(item.get('adicional', 0)) for item in items_processados)
            total_comissoes = total_montagem + total_assistencia + total_desmontagem
            
            # === BUSCAR CUSTOS EXTRAS PENDENTES PARA ESTE MONTADOR (reenvio) ===
            custos_extras_ids = []
            montador_id = envio['montador_id']
            identificador_montador = envio.get('identificador', str(montador_id))
            
            print(f"   🔍 [Reenvio] Buscando custos extras para montador ID={montador_id}, identificador={identificador_montador}")
            
            # Buscar por identificador do montador OU montador_id
            cur.execute("""
                SELECT id, identificador_boletim, valor, motivo 
                FROM custos_extras 
                WHERE (identificador_montador = %s OR montador_id = %s) AND status = 'pendente'
            """, (identificador_montador, montador_id))
            custos_extras_montador = cur.fetchall()
            
            # Também buscar pelos boletins que estão sendo reenviados
            boletins_envio = [item.get('boletim', '') for item in items_processados if item.get('boletim')]
            if boletins_envio:
                placeholders = ','.join(['%s'] * len(boletins_envio))
                cur.execute(f"""
                    SELECT id, identificador_boletim, valor, motivo 
                    FROM custos_extras 
                    WHERE identificador_boletim IN ({placeholders}) AND status = 'pendente'
                """, boletins_envio)
                custos_extras_boletins = cur.fetchall()
            else:
                custos_extras_boletins = []
            
            # Combinar resultados únicos (evitar duplicados)
            custos_extras_dict_ce = {}
            for ce in list(custos_extras_montador) + list(custos_extras_boletins):
                if ce['id'] not in custos_extras_dict_ce:
                    custos_extras_dict_ce[ce['id']] = ce
            
            custos_extras_list = list(custos_extras_dict_ce.values())
            custos_extras_ids_aplicados = set()
            
            # Criar mapa de custos extras por boletim
            custos_extras_por_boletim = {}
            for ce in custos_extras_list:
                boletim = ce['identificador_boletim'].strip() if ce['identificador_boletim'] else ''
                if boletim not in custos_extras_por_boletim:
                    custos_extras_por_boletim[boletim] = []
                custos_extras_por_boletim[boletim].append(ce)
            
            # Aplicar custos extras diretamente nos items_processados
            # EXCETO para boletins de ajuste (A-*) que já vêm do frontend com o valor
            for item in items_processados:
                boletim_item = item['boletim']
                if boletim_item.startswith('A-'):
                    continue
                if boletim_item in custos_extras_por_boletim:
                    for ce in custos_extras_por_boletim[boletim_item]:
                        item['adicional'] = float(item.get('adicional', 0)) + float(ce['valor'])
                        motivo_existente = item.get('motivo_valor_extra', '')
                        motivo_novo = ce['motivo']
                        if motivo_existente and motivo_novo:
                            item['motivo_valor_extra'] = f"{motivo_existente}; {motivo_novo}"
                        elif motivo_novo:
                            item['motivo_valor_extra'] = motivo_novo
                        custos_extras_ids_aplicados.add(ce['id'])
                        print(f"      ✅ [Reenvio] Aplicado custo extra no boletim {boletim_item}: +R$ {float(ce['valor']):.2f} ({ce['motivo']})")
            
            # Adicionar boletins de ajuste (A-YYYY-XXXX) como itens separados
            boletins_existentes = set(item['boletim'] for item in items_processados)
            
            for boletim_ajuste, custos_ajuste in custos_extras_por_boletim.items():
                if boletim_ajuste.startswith('A-') and boletim_ajuste not in boletins_existentes:
                    for ce in custos_ajuste:
                        item_ajuste = {
                            "boletim": boletim_ajuste,
                            "data_montagem": datetime.now().strftime("%d/%m/%Y"),
                            "cliente": "AJUSTE",
                            "nome_produto": ce['motivo'],
                            "valor_venda": 0,
                            "comissao_calculada": 0,
                            "comissao_editada": None,
                            "adicional": float(ce['valor']),
                            "motivo_valor_extra": ce['motivo'],
                            "tipo_servico": "MONTAGEM"
                        }
                        items_processados.append(item_ajuste)
                        custos_extras_ids_aplicados.add(ce['id'])
                        print(f"      ✅ [Reenvio] Adicionado boletim de ajuste {boletim_ajuste}: +R$ {float(ce['valor']):.2f} ({ce['motivo']})")
            
            # Marcar boletins de ajuste que já vieram do frontend
            for item in items_processados:
                boletim_item = item.get('boletim', '')
                if boletim_item.startswith('A-') and boletim_item in custos_extras_por_boletim:
                    for ce in custos_extras_por_boletim[boletim_item]:
                        custos_extras_ids_aplicados.add(ce['id'])
            
            custos_extras_ids = list(custos_extras_ids_aplicados)
            
            # Recalcular totais após aplicar custos extras
            total_adicionais = sum(float(item.get('adicional', 0)) for item in items_processados)
            
            if custos_extras_ids:
                print(f"   💰 [Reenvio] {len(custos_extras_ids)} custos extras aplicados nos items (de {len(custos_extras_list)} encontrados)")
            
            # Calcular período baseado nas datas dos items
            datas = []
            for item in items_processados:
                data_str = item.get('data_montagem', '')
                if data_str:
                    try:
                        data_obj = datetime.strptime(data_str, '%d/%m/%Y')
                        datas.append(data_obj)
                    except:
                        pass
            
            if datas:
                min_data = min(datas)
                max_data = max(datas)
                periodo_relatorio = f"{min_data.strftime('%d/%m/%Y')} a {max_data.strftime('%d/%m/%Y')}"
                periodo_mes = max_data.strftime('%m/%Y')
            else:
                periodo_relatorio = envio['periodo']
                periodo_mes = envio['periodo']
            
            # Montar detalhes JSON atualizado
            detalhes_json = {
                "nome_montador": nome_destinatario,
                "periodo_relatorio": periodo_relatorio,
                "percentual_montagem": percentual_montagem,
                "percentual_assistencia": percentual_assistencia,
                "percentual_desmontagem": percentual_desmontagem,
                "items": items_processados,
                "total_montagem": total_montagem,
                "total_assistencia": total_assistencia,
                "total_desmontagem": total_desmontagem,
                "total_comissao": total_comissoes,
                "total_adicionais": total_adicionais,
                "total_auxilio": total_auxilio,
                "total_geral": total_comissoes + total_adicionais + total_auxilio,
                "revisado": True,
                "data_revisao": datetime.now().isoformat()
            }
            
            # Atualizar o envio no banco
            cur.execute("""
                UPDATE envios_montagem 
                SET 
                    valor_total = %s,
                    quantidade_os = %s,
                    detalhes = %s,
                    periodo = %s
                WHERE id = %s
            """, (
                detalhes_json['total_geral'],
                len(items_processados),
                psycopg2.extras.Json(detalhes_json),
                periodo_mes,
                envio_id
            ))
            
            conn.commit()
            print(f"✅ Envio #{envio_id} atualizado com {len(items_processados)} items")
            
            # Gerar PDF atualizado (mesmo motor do envio original)
            from app.routes.relatorios import gerar_pdf_montador_html_template
            
            envio_data = detalhes_json.copy()
            envio_data['id'] = envio_id
            
            try:
                pdf_path = gerar_pdf_montador_html_template(envio_data)
                print(f"✅ PDF gerado: {pdf_path}")
            except Exception as e:
                print(f"❌ Erro ao gerar PDF com WeasyPrint: {e}")
                # Fallback para xhtml2pdf
                try:
                    from app.routes.relatorios import gerar_pdf_montador
                    pdf_path = gerar_pdf_montador(envio_data)
                    print(f"✅ PDF gerado (fallback pisa): {pdf_path}")
                except Exception as e2:
                    print(f"❌ Erro ao gerar PDF (fallback): {e2}")
                    raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
            
            # Gerar novo link via API externa com valores ATUALIZADOS
            import requests
            link_upload = None
            try:
                API_UPLOAD_URL = "https://api.link.dev.br/dvprocessamento/"
                API_UPLOAD_KEY = os.getenv("API_UPLOAD_KEY", "")
                
                # Gerar um lote_id único para a revisão (base + timestamp para não conflitar)
                # Isso garante que a API cria um NOVO registro com os valores atualizados
                import time
                revisao_lote_id = int(f"{envio_id}{int(time.time()) % 100000}")
                
                print(f"   🆔 ID revisão para API: {revisao_lote_id} (envio original: {envio_id})")
                
                payload_api = {
                    "nome": nome_destinatario,
                    "email": email_destino,
                    "periodo": periodo_mes,
                    "valor_total": float(detalhes_json['total_geral']),
                    "quantidade_os": len(items_processados),
                    "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "lote_id": revisao_lote_id,
                    "tipo": "montagem"
                }
                
                print(f"   📦 Payload API: {payload_api}")
                
                headers_api = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                    "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                    "X-API-Key": API_UPLOAD_KEY
                }
                
                print(f"   📤 Gerando novo link via API...")
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
                        upload_hash = resposta_api.get('hash')
                        validade_link = resposta_api.get('validade_link')
                        id_controle_api = resposta_api.get('id_controle') or resposta_api.get('id')
                        
                        print(f"   ✅ Novo link gerado: {link_upload}")
                        
                        # Atualizar link no banco
                        cur.execute("""
                            UPDATE envios_montagem 
                            SET link_upload = %s, upload_hash = %s, validade_link = %s, id_controle = %s
                            WHERE id = %s
                        """, (link_upload, upload_hash, validade_link, id_controle_api, envio_id))
                        conn.commit()
                elif response_api.status_code == 409:
                    # Conflito - usar link existente da resposta
                    try:
                        resposta_api = response_api.json()
                        link_upload = resposta_api.get('link')
                        print(f"   ⚠️ Usando link da resposta 409: {link_upload}")
                    except:
                        print(f"   ⚠️ 409 sem JSON válido")
                else:
                    print(f"   ⚠️ API retornou status {response_api.status_code}")
                    try:
                        print(f"   ⚠️ Resposta: {response_api.text[:200]}")
                    except:
                        pass
            except Exception as e:
                print(f"   ⚠️ Erro ao gerar link via API: {e}")
            
            # Fallback: se não conseguiu link da API, buscar do banco
            if not link_upload:
                try:
                    cur.execute("SELECT link_upload FROM envios_montagem WHERE id = %s", (envio_id,))
                    row_link = cur.fetchone()
                    if row_link and row_link.get('link_upload'):
                        link_upload = row_link['link_upload']
                        print(f"   ✅ Link recuperado do banco: {link_upload}")
                    else:
                        print(f"   ⚠️ Nenhum link encontrado no banco")
                except Exception as e:
                    print(f"   ⚠️ Erro ao buscar link do banco: {e}")
            
            # Buscar configuração de email
            cur.execute("SELECT * FROM email_config LIMIT 1")
            email_config_row = cur.fetchone()
            
            if not email_config_row:
                raise HTTPException(status_code=500, detail="Configuração de email não encontrada")
            
            # Buscar template de email (tabela pode não existir)
            template = None
            try:
                cur.execute("SELECT * FROM email_templates WHERE tipo = 'montador' AND ativo = true LIMIT 1")
                template = cur.fetchone()
            except Exception as e:
                print(f"⚠️ Tabela email_templates não encontrada: {e}")
                # Resetar cursor após erro
                conn.rollback()
            
            if template:
                assunto = template['assunto'].replace("{{periodo_relatorio}}", periodo_relatorio)
                corpo = template['corpo'].replace("{{periodo_relatorio}}", periodo_relatorio)
                assunto = assunto.replace("{{nome_montador}}", nome_destinatario)
                corpo = corpo.replace("{{nome_montador}}", nome_destinatario)
                # Substituir link de upload
                link_para_email = link_upload if link_upload else "#"
                corpo = corpo.replace("{{link_upload}}", link_para_email)
                corpo = corpo.replace("{{link}}", link_para_email)
                # Marcar como revisado
                assunto = f"[REVISADO] {assunto}"
            else:
                link_texto = f"<br><br><strong>Link para envio de NF:</strong> <a href='{link_upload}'>{link_upload}</a>" if link_upload else ""
                assunto = f"[REVISADO] Relatório de Comissões - {periodo_relatorio}"
                corpo = f"Prezado(a) {nome_destinatario},\n\nSegue em anexo o relatório **REVISADO** de comissões referente ao período {periodo_relatorio}.{link_texto}"
            
            # Converter corpo para HTML (mesmo do fluxo original)
            corpo_html = corpo.replace("\n", "<br>").replace("**", "<strong>").replace("**", "</strong>")
            
            # Enviar email
            from app.routes.relatorios import enviar_email_graph
            
            cc_email = email_config_row.get('cc', email_config_row.get('cc_email'))
            
            try:
                sucesso = enviar_email_graph(
                    destinatario=email_destino,
                    assunto=assunto,
                    corpo_html=f"<html><body>{corpo_html}</body></html>",
                    anexo_path=pdf_path,
                    cc=cc_email
                )
                
                if sucesso:
                    print(f"✅ Email enviado para {email_destino}")
                else:
                    raise HTTPException(status_code=500, detail="Falha ao enviar email")
                    
            except Exception as e:
                print(f"❌ Erro ao enviar email: {e}")
                raise HTTPException(status_code=500, detail=f"Erro ao enviar email: {str(e)}")
            
            # === MARCAR CUSTOS EXTRAS COMO PROCESSADOS (reenvio) ===
            if custos_extras_ids:
                try:
                    placeholders_ce = ','.join(['%s'] * len(custos_extras_ids))
                    cur.execute(f"""
                        UPDATE custos_extras 
                        SET status = 'processado', processado_em = NOW() 
                        WHERE id IN ({placeholders_ce})
                    """, custos_extras_ids)
                    conn.commit()
                    print(f"   ✅ [Reenvio] {len(custos_extras_ids)} custos extras marcados como processados")
                except Exception as e:
                    print(f"   ⚠️ [Reenvio] Erro ao marcar custos extras como processados: {e}")
            
            return {
                "success": True,
                "message": f"Envio #{envio_id} atualizado e reenviado com sucesso!",
                "envio_id": envio_id,
                "quantidade_items": len(items_processados),
                "valor_total": detalhes_json['total_geral'],
                "email_enviado_para": email_destino,
                "link_upload": link_upload
            }
        
        else:
            # TODO: Implementar para prestador se necessário
            raise HTTPException(status_code=501, detail="Edição de envio de prestador ainda não implementada")

