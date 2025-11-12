"""
Rotas de Relatórios e Envio de Email
Gera PDFs e envia por email usando Microsoft Graph API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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
    detalhes = envio_data.get('detalhes', {})
    items_raw = detalhes.get('itens', detalhes.get('items', []))
    
    # Formatar items para o template
    items_para_pdf = []
    for item in items_raw:
        items_para_pdf.append({
            'boletim': item.get('boletim', item.get('identificador_boletim_montagem')),
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
        "nome_montador": envio_data.get('montador_nome', envio_data.get('nome_montador', 'N/A')),
        "periodo_relatorio": envio_data.get('periodo', 'N/A'),
        "percentual_comissao": float(envio_data.get('percentual_comissao', 0)),
        "items": items_para_pdf,
        "total_comissao": float(detalhes.get('total_comissao', envio_data.get('total_comissao', 0))),
        "total_adicionais": float(detalhes.get('total_adicionais', envio_data.get('total_adicionais', 0))),
        "total_auxilio": float(detalhes.get('total_auxilio', envio_data.get('total_auxilio', 0))),
        "total_geral": float(envio_data.get('valor_total', envio_data.get('total_geral', 0)))
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
    erros_detalhes = []
    
    print(f"\n{'='*50}")
    print(f"📧 ENVIANDO LOTE DE RELATÓRIOS COM PDF")
    print(f"{'='*50}")
    print(f"Tipo: {tipo}")
    print(f"Total de registros: {len(dados)}")
    
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
                    cur.execute("SELECT email FROM prestadores WHERE nome = %s", (nome_destinatario,))
                else:
                    cur.execute("SELECT email FROM montadores WHERE nome = %s", (nome_destinatario,))
                
                resultado = cur.fetchone()
                
                if not resultado:
                    print(f"❌ {nome_destinatario}: Email não encontrado no banco")
                    erros += len(itens)
                    erros_detalhes.append({
                        "nome": nome_destinatario,
                        "erro": "Email não encontrado no banco de dados"
                    })
                    continue
                
                email_destino = resultado["email"]
                
                # Preparar assunto e corpo do email
                assunto = email_config.get("assunto", "Relatório de Serviços")
                corpo = email_config.get("corpo", "Segue relatório em anexo.")
                
                # Gerar link de upload via API externa
                link_upload = None
                try:
                    import requests
                    API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
                    API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
                    
                    periodo = itens[0].get("periodo", "N/A")
                    total_geral = sum(float(item.get("valor_total", 0)) for item in itens)
                    
                    # Preparar payload para API
                    lote_id_temp = hash(f"{nome_destinatario}_{periodo}") % 1000000
                    
                    payload_api = {
                        "nome": nome_destinatario,
                        "email": email_destino,
                        "periodo": periodo if "/" in periodo else f"{periodo}/2025",
                        "valor_total": total_geral,
                        "quantidade_os": len(itens),
                        "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "lote_id": lote_id_temp,
                        "tipo": tipo
                    }
                    
                    headers_api = {
                        "Content-Type": "application/json; charset=utf-8",
                        "Accept": "application/json",
                        "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                        "X-API-Key": API_UPLOAD_KEY
                    }
                    
                    print(f"   📤 Gerando link de upload via API...")
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
                            print(f"   ✅ Link gerado: {link_upload}")
                        else:
                            print(f"   ⚠️ API retornou erro: {resposta_api.get('message')}")
                    else:
                        print(f"   ⚠️ API respondeu com status {response_api.status_code}")
                
                except Exception as e:
                    print(f"   ⚠️ Erro ao gerar link: {e}")
                
                # Fallback se API falhar
                if not link_upload:
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
                    periodo = itens[0].get("periodo", "N/A")
                    
                    # Calcular totais
                    total_comissao = sum(float(item.get("comissao", 0)) for item in itens)
                    total_adicionais = sum(float(item.get("adicional", 0)) for item in itens)
                    total_auxilio = 0  # Pode ser configurável
                    total_geral = total_comissao + total_adicionais + total_auxilio
                    
                    # Gerar link de upload via API externa
                    link_upload = None
                    try:
                        import requests
                        API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
                        API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
                        
                        # ID com offset para montadores
                        lote_id_temp = 876231 + (hash(f"{nome_destinatario}_{periodo}") % 1000000)
                        
                        payload_api = {
                            "nome": nome_destinatario,
                            "email": email_destino,
                            "periodo": periodo if "/" in periodo else f"{periodo}/2025",
                            "valor_total": total_geral,
                            "quantidade_os": len(itens),
                            "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "lote_id": lote_id_temp,
                            "tipo": "montagem"
                        }
                        
                        headers_api = {
                            "Content-Type": "application/json; charset=utf-8",
                            "Accept": "application/json",
                            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                            "X-API-Key": API_UPLOAD_KEY
                        }
                        
                        print(f"   📤 Gerando link de upload via API (montador)...")
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
                                print(f"   ✅ Link gerado: {link_upload}")
                            else:
                                print(f"   ⚠️ API retornou erro: {resposta_api.get('message')}")
                        else:
                            print(f"   ⚠️ API respondeu com status {response_api.status_code}")
                    
                    except Exception as e:
                        print(f"   ⚠️ Erro ao gerar link: {e}")
                    
                    # Fallback se API falhar
                    if not link_upload:
                        link_upload = f"https://upload.novomundo.com.br/{uuid.uuid4().hex[:12]}"
                    
                    assunto = assunto.replace("{{periodo_relatorio}}", periodo)
                    assunto = assunto.replace("{{nome_montador}}", nome_destinatario)
                    corpo = corpo.replace("{{periodo_relatorio}}", periodo)
                    corpo = corpo.replace("{{nome_montador}}", nome_destinatario)
                    corpo = corpo.replace("{{link_upload}}", link_upload)
                    
                    # Preparar dados para o PDF
                    envio_data = {
                        "nome_montador": nome_destinatario,
                        "periodo_relatorio": periodo,
                        "items": [
                            {
                                "boletim": item.get("identificador_boletim_montagem", ""),
                                "data_montagem": item.get("data_da_montagem", ""),
                                "cliente": item.get("nome_do_cliente", ""),
                                "nome_produto": item.get("nome_produto", ""),
                                "valor_venda": float(item.get("media_de_valor_venda", 0)),
                                "comissao": float(item.get("comissao", 0)),
                                "adicional": float(item.get("adicional", 0))
                            }
                            for item in itens
                        ],
                        "total_comissao": total_comissao,
                        "total_adicionais": total_adicionais,
                        "total_auxilio": total_auxilio,
                        "total_geral": total_geral
                    }
                    
                    # Gerar PDF
                    print(f"   📄 Gerando PDF do montador...")
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
        "total": len(dados)
    }
    
    if erros > 0:
        resultado["warning"] = f"{erros} envios falharam"
        resultado["detalhes_erros"] = erros_detalhes
    
    if sucesso > 0:
        resultado["message"] = f"✅ {sucesso} emails enviados com sucesso com PDF anexado!"
    
    return resultado
