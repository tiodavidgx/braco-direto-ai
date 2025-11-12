"""
Rotas de Relatórios e Envio de Email
Gera PDFs e envia por email usando Microsoft Graph API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from pathlib import Path
import base64
from datetime import datetime
from app.utils.pdf_generator import gerar_pdf_prestador, gerar_pdf_montador

router = APIRouter()

# Modelos
class EnvioRelatorioRequest(BaseModel):
    id: int
    tipo: str  # 'prestador' ou 'montador'

# Configuração Microsoft Graph
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

def get_access_token():
    """
    Obter token de acesso do Microsoft Graph
    Em produção, implementar fluxo OAuth2 completo
    """
    # TODO: Implementar autenticação OAuth2
    # Por enquanto, retornar token mock
    return "TOKEN_AQUI"

# As funções de geração de PDF agora estão em app/utils/pdf_generator.py

def enviar_email_graph(destinatario: str, assunto: str, corpo_html: str, anexo_path: str = None):
    """
    Envia email usando Microsoft Graph API
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo_html: Corpo do email em HTML
        anexo_path: Caminho do arquivo PDF para anexar (opcional)
    """
    
    token = get_access_token()
    
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
    
    # Enviar email
    response = requests.post(
        f"{GRAPH_API_URL}/me/sendMail",
        headers=headers,
        json={"message": message, "saveToSentItems": "true"}
    )
    
    if response.status_code != 202:
        raise Exception(f"Erro ao enviar email: {response.text}")
    
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
