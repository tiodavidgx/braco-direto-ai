"""
Gerador de PDFs usando ReportLab
Modelos bonitos e profissionais para relatórios
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfgen import canvas
from datetime import datetime
from pathlib import Path

# Cores do tema
COR_PRIMARIA = colors.HexColor('#2563eb')  # Azul
COR_SECUNDARIA = colors.HexColor('#1e40af')  # Azul escuro
COR_SUCESSO = colors.HexColor('#10b981')  # Verde
COR_TEXTO = colors.HexColor('#1f2937')  # Cinza escuro
COR_TEXTO_CLARO = colors.HexColor('#6b7280')  # Cinza médio
COR_FUNDO_CABECALHO = colors.HexColor('#eff6ff')  # Azul claro
COR_BORDA = colors.HexColor('#e5e7eb')  # Cinza claro


class PDFHeaderFooter:
    """Classe para adicionar cabeçalho e rodapé em todas as páginas"""
    
    def __init__(self, title, subtitle=""):
        self.title = title
        self.subtitle = subtitle
    
    def header(self, canvas, doc):
        canvas.saveState()
        
        # Linha superior decorativa
        canvas.setStrokeColor(COR_PRIMARIA)
        canvas.setLineWidth(3)
        canvas.line(2*cm, A4[1] - 1.5*cm, A4[0] - 2*cm, A4[1] - 1.5*cm)
        
        # Título do documento
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(COR_PRIMARIA)
        canvas.drawString(2*cm, A4[1] - 2.2*cm, self.title)
        
        if self.subtitle:
            canvas.setFont('Helvetica', 10)
            canvas.setFillColor(COR_TEXTO_CLARO)
            canvas.drawString(2*cm, A4[1] - 2.7*cm, self.subtitle)
        
        canvas.restoreState()
    
    def footer(self, canvas, doc):
        canvas.saveState()
        
        # Linha inferior decorativa
        canvas.setStrokeColor(COR_BORDA)
        canvas.setLineWidth(1)
        canvas.line(2*cm, 2*cm, A4[0] - 2*cm, 2*cm)
        
        # Informações do rodapé
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(COR_TEXTO_CLARO)
        
        # Data de geração
        data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")
        canvas.drawString(2*cm, 1.5*cm, f"Gerado em: {data_geracao}")
        
        # Número da página
        page_num = canvas.getPageNumber()
        canvas.drawRightString(A4[0] - 2*cm, 1.5*cm, f"Página {page_num}")
        
        # Nome da empresa
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(COR_PRIMARIA)
        canvas.drawCentredString(A4[0] / 2, 1.5*cm, "Novo Mundo - Sistema de Gestão")
        
        canvas.restoreState()


def gerar_pdf_prestador(lote_data: dict, output_path: str):
    """
    Gera PDF bonito do relatório de prestador
    
    Args:
        lote_data: Dicionário com dados do lote e OS
        output_path: Caminho para salvar o PDF
    """
    
    # Criar documento
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=3.5*cm,
        bottomMargin=2.5*cm
    )
    
    # Container para elementos
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    style_titulo = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=COR_PRIMARIA,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulo
    style_subtitulo = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COR_TEXTO_CLARO,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Estilo para seção
    style_secao = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=COR_SECUNDARIA,
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    # Título principal
    elements.append(Paragraph("RELATÓRIO DE FECHAMENTO", style_titulo))
    elements.append(Paragraph(f"Prestador de Serviços", style_subtitulo))
    elements.append(Spacer(1, 0.5*cm))
    
    # Box de informações do prestador
    info_data = [
        ['Prestador:', lote_data.get('prestador_nome', 'N/A')],
        ['Período:', lote_data.get('periodo', 'N/A')],
        ['Lote ID:', str(lote_data.get('id', 'N/A'))],
        ['Data de Geração:', datetime.now().strftime("%d/%m/%Y")],
    ]
    
    info_table = Table(info_data, colWidths=[4*cm, 13*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), COR_FUNDO_CABECALHO),
        ('TEXTCOLOR', (0, 0), (0, -1), COR_SECUNDARIA),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, COR_BORDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Seção de Ordens de Serviço
    elements.append(Paragraph("Ordens de Serviço (OS)", style_secao))
    elements.append(Spacer(1, 0.3*cm))
    
    # Tabela de OS
    os_list = lote_data.get('os_list', [])
    
    if os_list:
        # Cabeçalho da tabela
        os_data = [['#', 'OS', 'Cliente', 'Serviço', 'Valor']]
        
        # Dados das OS
        for idx, os in enumerate(os_list, 1):
            os_data.append([
                str(idx),
                str(os.get('os_numero', 'N/A')),
                str(os.get('cliente_nome', 'N/A'))[:30],  # Limitar tamanho
                str(os.get('servico_descricao', 'N/A'))[:35],
                f"R$ {float(os.get('valor', 0)):.2f}"
            ])
        
        os_table = Table(os_data, colWidths=[1*cm, 2.5*cm, 5*cm, 6*cm, 2.5*cm])
        os_table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Corpo da tabela
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Coluna OS
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Coluna Valor
            
            # Bordas e padding
            ('GRID', (0, 0), (-1, -1), 0.5, COR_BORDA),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternância de cores nas linhas
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COR_FUNDO_CABECALHO]),
        ]))
        
        elements.append(os_table)
    else:
        elements.append(Paragraph("Nenhuma OS encontrada neste lote.", styles['Normal']))
    
    elements.append(Spacer(1, 0.8*cm))
    
    # Box de totais
    valor_total = float(lote_data.get('valor_total', 0))
    quantidade_os = len(os_list)
    
    totais_data = [
        ['Quantidade de OS:', str(quantidade_os)],
        ['Valor Total:', f"R$ {valor_total:.2f}"],
    ]
    
    totais_table = Table(totais_data, colWidths=[13*cm, 4*cm])
    totais_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COR_FUNDO_CABECALHO),
        ('TEXTCOLOR', (0, 0), (0, -1), COR_SECUNDARIA),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, COR_BORDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Destacar linha do valor total
        ('BACKGROUND', (0, -1), (-1, -1), COR_SUCESSO),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
    ]))
    
    elements.append(totais_table)
    elements.append(Spacer(1, 1*cm))
    
    # Instruções
    style_instrucoes = ParagraphStyle(
        'Instructions',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COR_TEXTO,
        spaceAfter=6,
        leading=14
    )
    
    elements.append(Paragraph("📋 <b>Próximos Passos:</b>", style_instrucoes))
    elements.append(Spacer(1, 0.2*cm))
    
    instrucoes_text = """
    1. Emita a Nota Fiscal referente aos serviços prestados no período<br/>
    2. Acesse o link de upload fornecido no email<br/>
    3. Anexe a Nota Fiscal em formato PDF<br/>
    4. Aguarde a confirmação de pagamento<br/>
    """
    
    elements.append(Paragraph(instrucoes_text, styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Observações
    obs_text = """
    <i>Este documento é um comprovante dos serviços prestados no período especificado. 
    Mantenha-o guardado para sua contabilidade.</i>
    """
    style_obs = ParagraphStyle(
        'Observation',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COR_TEXTO_CLARO,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(obs_text, style_obs))
    
    # Construir PDF com cabeçalho e rodapé
    header_footer = PDFHeaderFooter(
        "Relatório de Prestador",
        f"Período: {lote_data.get('periodo', 'N/A')}"
    )
    
    doc.build(
        elements,
        onFirstPage=lambda c, d: (header_footer.header(c, d), header_footer.footer(c, d)),
        onLaterPages=lambda c, d: (header_footer.header(c, d), header_footer.footer(c, d))
    )
    
    return output_path


def gerar_pdf_montador(envio_data: dict, output_path: str):
    """
    Gera PDF bonito do relatório de montador
    
    Args:
        envio_data: Dicionário com dados do envio e montagens
        output_path: Caminho para salvar o PDF
    """
    
    # Criar documento
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=3.5*cm,
        bottomMargin=2.5*cm
    )
    
    # Container para elementos
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=COR_PRIMARIA,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_subtitulo = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COR_TEXTO_CLARO,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    style_secao = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=COR_SECUNDARIA,
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    # Título principal
    elements.append(Paragraph("RELATÓRIO DE PAGAMENTO", style_titulo))
    elements.append(Paragraph(f"Montador", style_subtitulo))
    elements.append(Spacer(1, 0.5*cm))
    
    # Box de informações do montador
    percentual_comissao = float(envio_data.get('percentual_comissao', 0))
    
    info_data = [
        ['Montador:', envio_data.get('montador_nome', 'N/A')],
        ['Período:', envio_data.get('periodo', 'N/A')],
        ['ID do Envio:', str(envio_data.get('id', 'N/A'))],
        ['Comissão:', f"{percentual_comissao:.1f}%"],
        ['Data de Geração:', datetime.now().strftime("%d/%m/%Y")],
    ]
    
    info_table = Table(info_data, colWidths=[4*cm, 13*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), COR_FUNDO_CABECALHO),
        ('TEXTCOLOR', (0, 0), (0, -1), COR_SECUNDARIA),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, COR_BORDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Seção de Montagens
    elements.append(Paragraph("Montagens Realizadas", style_secao))
    elements.append(Spacer(1, 0.3*cm))
    
    # Tabela de montagens
    montagens = envio_data.get('montagens', [])
    
    if montagens and isinstance(montagens, list):
        # Cabeçalho da tabela
        montagens_data = [['#', 'Pedido', 'Cliente', 'Produto', 'Comissão']]
        
        # Dados das montagens
        for idx, montagem in enumerate(montagens, 1):
            montagens_data.append([
                str(idx),
                str(montagem.get('pedido', 'N/A')),
                str(montagem.get('cliente', 'N/A'))[:30],
                str(montagem.get('produto', 'N/A'))[:35],
                f"R$ {float(montagem.get('comissao', 0)):.2f}"
            ])
        
        montagens_table = Table(montagens_data, colWidths=[1*cm, 2.5*cm, 5*cm, 6*cm, 2.5*cm])
        montagens_table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Corpo da tabela
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            
            # Bordas e padding
            ('GRID', (0, 0), (-1, -1), 0.5, COR_BORDA),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternância de cores
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COR_FUNDO_CABECALHO]),
        ]))
        
        elements.append(montagens_table)
    else:
        elements.append(Paragraph("Nenhuma montagem encontrada neste período.", styles['Normal']))
    
    elements.append(Spacer(1, 0.8*cm))
    
    # Box de cálculos e totais
    total_comissoes = float(envio_data.get('total_comissoes', 0))
    auxilio_semanal = float(envio_data.get('auxilio_semanal', 0))
    valor_final = float(envio_data.get('valor_final', 0))
    quantidade_montagens = len(montagens) if isinstance(montagens, list) else 0
    
    calculos_data = [
        ['Quantidade de Montagens:', str(quantidade_montagens)],
        ['Total em Comissões:', f"R$ {total_comissoes:.2f}"],
        ['Auxílio Semanal:', f"R$ {auxilio_semanal:.2f}"],
        ['Valor Final a Receber:', f"R$ {valor_final:.2f}"],
    ]
    
    calculos_table = Table(calculos_data, colWidths=[13*cm, 4*cm])
    calculos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -2), COR_FUNDO_CABECALHO),
        ('TEXTCOLOR', (0, 0), (0, -1), COR_SECUNDARIA),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 11),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, COR_BORDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Destacar linha do valor final
        ('BACKGROUND', (0, -1), (-1, -1), COR_SUCESSO),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
    ]))
    
    elements.append(calculos_table)
    elements.append(Spacer(1, 1*cm))
    
    # Instruções
    style_instrucoes = ParagraphStyle(
        'Instructions',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COR_TEXTO,
        spaceAfter=6,
        leading=14
    )
    
    elements.append(Paragraph("📋 <b>Próximos Passos:</b>", style_instrucoes))
    elements.append(Spacer(1, 0.2*cm))
    
    instrucoes_text = """
    1. Emita a Nota Fiscal referente às montagens realizadas no período<br/>
    2. Acesse o link de upload fornecido no email<br/>
    3. Anexe a Nota Fiscal em formato PDF<br/>
    4. Aguarde a confirmação de pagamento<br/>
    """
    
    elements.append(Paragraph(instrucoes_text, styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Observações
    obs_text = """
    <i>Este documento é um comprovante das montagens realizadas no período especificado. 
    As comissões são calculadas de acordo com o percentual definido em seu cadastro.</i>
    """
    style_obs = ParagraphStyle(
        'Observation',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COR_TEXTO_CLARO,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(obs_text, style_obs))
    
    # Construir PDF
    header_footer = PDFHeaderFooter(
        "Relatório de Montador",
        f"Período: {envio_data.get('periodo', 'N/A')}"
    )
    
    doc.build(
        elements,
        onFirstPage=lambda c, d: (header_footer.header(c, d), header_footer.footer(c, d)),
        onLaterPages=lambda c, d: (header_footer.header(c, d), header_footer.footer(c, d))
    )
    
    return output_path
