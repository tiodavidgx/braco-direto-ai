from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
from datetime import datetime
import psycopg2.extras
from app.database import get_db_connection
from app.routes._auth_deps import get_current_user, require_admin
from app.utils.whatsapp_http import WA_HEADERS
import subprocess
import os
import signal
import time

# Todo o router exige usuário autenticado por padrão.
# Endpoints administrativos (start/stop/restart) adicionam require_admin.
router = APIRouter(dependencies=[Depends(get_current_user)])

WHATSAPP_BASE_URL = os.getenv("WHATSAPP_BASE_URL", "http://localhost:14003")
# O serviço WhatsApp (Baileys) roda via systemd: braco-whatsapp.service
# Diretório: /var/www/braco-direto-ai/whatsapp-service/server-baileys.js


class SendMessageRequest(BaseModel):
    number: str
    message: str


class SendBulkRequest(BaseModel):
    numbers: List[str]
    message: str
    delay: int = 3000


class TemplateCreate(BaseModel):
    nome: str
    tipo: str
    template: str
    variaveis: Optional[str] = None
    ativo: bool = True


class TemplateUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    template: Optional[str] = None
    variaveis: Optional[str] = None
    ativo: Optional[bool] = None


class AutomacaoCreate(BaseModel):
    evento: str
    template_id: str
    condicoes: Optional[str] = None
    ativo: bool = True


class AutomacaoUpdate(BaseModel):
    evento: Optional[str] = None
    template_id: Optional[str] = None
    condicoes: Optional[str] = None
    ativo: Optional[bool] = None


@router.get("/status")
def get_status():
    """Verifica status da conexão WhatsApp"""
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=5, headers=WA_HEADERS)
        data = response.json()
        data['server_running'] = True
        return data
    except Exception as e:
        return {
            "status": "error", 
            "error": f"Serviço não está rodando: {str(e)}",
            "server_running": False
        }


@router.get("/qr")
def get_qr_code():
    """Obtém o QR Code para conexão do WhatsApp"""
    try:
        # Primeiro verificar status
        status_response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=5, headers=WA_HEADERS)
        status_data = status_response.json()
        
        if status_data.get('status') == 'connected':
            return {
                "success": True,
                "status": "connected",
                "qr_code": None,
                "message": "WhatsApp já está conectado",
                "info": status_data.get('info')
            }
        
        if not status_data.get('hasQrCode'):
            return {
                "success": False,
                "status": status_data.get('status', 'unknown'),
                "qr_code": None,
                "message": "QR Code ainda não disponível. Aguarde..."
            }
        
        # Buscar QR Code da página HTML e extrair o base64
        qr_response = requests.get(f"{WHATSAPP_BASE_URL}/qr", timeout=5, headers=WA_HEADERS)
        html = qr_response.text
        
        # Extrair QR Code base64 do HTML
        import re
        match = re.search(r'src="(data:image/png;base64,[^"]+)"', html)
        if match:
            qr_base64 = match.group(1)
            return {
                "success": True,
                "status": "qr_ready",
                "qr_code": qr_base64,
                "message": "Escaneie o QR Code com seu WhatsApp"
            }
        
        return {
            "success": False,
            "status": "qr_not_found",
            "qr_code": None,
            "message": "QR Code não encontrado na resposta"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "qr_code": None,
            "message": f"Erro ao obter QR Code: {str(e)}"
        }


@router.post("/start-server")
def start_whatsapp_server(admin: dict = Depends(require_admin)):
    """Inicia o servidor WhatsApp via systemd"""
    # Verificar se já está rodando
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2, headers=WA_HEADERS)
        if response.status_code == 200:
            return {
                "success": True,
                "message": "Servidor WhatsApp já está rodando",
                "already_running": True
            }
    except:
        pass
    
    try:
        # Iniciar via systemd (usar caminho completo)
        result = subprocess.run(
            ["/usr/bin/systemctl", "start", "braco-whatsapp"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro ao iniciar serviço: {result.stderr}"
            )
        
        # Aguardar um pouco para o servidor iniciar
        time.sleep(3)
        
        # Verificar se iniciou
        try:
            response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2, headers=WA_HEADERS)
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Servidor WhatsApp iniciado com sucesso"
                }
        except:
            pass
        
        return {
            "success": True,
            "message": "Servidor WhatsApp está inicializando..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar servidor: {str(e)}")


@router.post("/stop-server")
def stop_whatsapp_server(admin: dict = Depends(require_admin)):
    """Para o servidor WhatsApp via systemd"""
    try:
        # Parar via systemd (usar caminho completo)
        result = subprocess.run(
            ["/usr/bin/systemctl", "stop", "braco-whatsapp"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro ao parar serviço: {result.stderr}"
            )
        
        return {
            "success": True,
            "message": "Servidor WhatsApp parado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao parar servidor: {str(e)}")


@router.post("/restart-server")
def restart_whatsapp_server(admin: dict = Depends(require_admin)):
    """Reinicia o servidor WhatsApp via systemd"""
    try:
        # Reiniciar via systemd (usar caminho completo)
        result = subprocess.run(
            ["/usr/bin/systemctl", "restart", "braco-whatsapp"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro ao reiniciar serviço: {result.stderr}"
            )
        
        # Aguardar um pouco
        time.sleep(3)
        
        return {
            "success": True,
            "message": "Servidor WhatsApp reiniciado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao reiniciar servidor: {str(e)}")


@router.get("/info")
def get_info():
    """Obtém informações do usuário conectado"""
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/info", timeout=2, headers=WA_HEADERS)
        return response.json()
    except:
        return {"success": False, "error": "Não foi possível obter informações"}


@router.post("/send")
def send_message(request: SendMessageRequest):
    """Envia uma mensagem individual"""
    try:
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send",
            json={"number": request.number, "message": request.message},
            timeout=30, headers=WA_HEADERS)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk")
def send_bulk(request: SendBulkRequest):
    """Envia mensagens em massa"""
    try:
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send-bulk",
            json={
                "numbers": request.numbers,
                "message": request.message,
                "delay": request.delay
            },
            timeout=300, headers=WA_HEADERS)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ TEMPLATES ============

@router.get("/templates")
def get_templates(tipo: Optional[str] = None):
    """Lista todos os templates de WhatsApp"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo:
            cur.execute("""
                SELECT * FROM templates_whatsapp 
                WHERE tipo = %s
                ORDER BY id
            """, (tipo,))
        else:
            cur.execute("SELECT * FROM templates_whatsapp ORDER BY id")
        
        return cur.fetchall()


@router.get("/templates/{template_id}")
def get_template(template_id: int):
    """Obtém um template específico"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM templates_whatsapp WHERE id = %s", (template_id,))
        template = cur.fetchone()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        return template


@router.post("/templates")
def create_template(template: TemplateCreate):
    """Cria um novo template"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO templates_whatsapp (nome, tipo, template, variaveis, ativo)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """, (template.nome, template.tipo, template.template, template.variaveis, template.ativo))
        
        new_template = cur.fetchone()
        conn.commit()
        return new_template


@router.put("/templates/{template_id}")
def update_template(template_id: int, template: TemplateUpdate):
    """Atualiza um template existente"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar template existente
        cur.execute("SELECT * FROM templates_whatsapp WHERE id = %s", (template_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        # Preparar campos para atualização
        update_fields = []
        values = []
        
        if template.nome is not None:
            update_fields.append("nome = %s")
            values.append(template.nome)
        if template.tipo is not None:
            update_fields.append("tipo = %s")
            values.append(template.tipo)
        if template.template is not None:
            update_fields.append("template = %s")
            values.append(template.template)
        if template.variaveis is not None:
            update_fields.append("variaveis = %s")
            values.append(template.variaveis)
        if template.ativo is not None:
            update_fields.append("ativo = %s")
            values.append(template.ativo)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        update_fields.append("atualizado_em = CURRENT_TIMESTAMP")
        values.append(template_id)
        
        cur.execute(f"""
            UPDATE templates_whatsapp 
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """, values)
        
        updated_template = cur.fetchone()
        conn.commit()
        return updated_template


@router.delete("/templates/{template_id}")
def delete_template(template_id: int):
    """Deleta um template"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM templates_whatsapp WHERE id = %s RETURNING id", (template_id,))
        deleted = cur.fetchone()
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        conn.commit()
        return {"message": "Template deletado com sucesso"}


# ============ AUTOMAÇÕES ============

@router.get("/automacoes")
def get_automacoes():
    """Lista todas as automações"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT a.*, t.nome as template_nome
            FROM automacao_whatsapp a
            LEFT JOIN templates_whatsapp t ON a.template_id = t.id::text
            ORDER BY a.id
        """)
        return cur.fetchall()


@router.get("/automacoes/{automacao_id}")
def get_automacao(automacao_id: int):
    """Obtém uma automação específica"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT a.*, t.nome as template_nome
            FROM automacao_whatsapp a
            LEFT JOIN templates_whatsapp t ON a.template_id = t.id::text
            WHERE a.id = %s
        """, (automacao_id,))
        automacao = cur.fetchone()
        
        if not automacao:
            raise HTTPException(status_code=404, detail="Automação não encontrada")
        
        return automacao


@router.post("/automacoes")
def create_automacao(automacao: AutomacaoCreate):
    """Cria uma nova automação"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO automacao_whatsapp (evento, template_id, condicoes, ativo)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (automacao.evento, automacao.template_id, automacao.condicoes, automacao.ativo))
        
        new_automacao = cur.fetchone()
        conn.commit()
        return new_automacao


@router.put("/automacoes/{automacao_id}")
def update_automacao(automacao_id: int, automacao: AutomacaoUpdate):
    """Atualiza uma automação existente"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar automação existente
        cur.execute("SELECT * FROM automacao_whatsapp WHERE id = %s", (automacao_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Automação não encontrada")
        
        # Preparar campos para atualização
        update_fields = []
        values = []
        
        if automacao.evento is not None:
            update_fields.append("evento = %s")
            values.append(automacao.evento)
        if automacao.template_id is not None:
            update_fields.append("template_id = %s")
            values.append(automacao.template_id)
        if automacao.condicoes is not None:
            update_fields.append("condicoes = %s")
            values.append(automacao.condicoes)
        if automacao.ativo is not None:
            update_fields.append("ativo = %s")
            values.append(automacao.ativo)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        update_fields.append("atualizado_em = CURRENT_TIMESTAMP")
        values.append(automacao_id)
        
        cur.execute(f"""
            UPDATE automacao_whatsapp 
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """, values)
        
        updated_automacao = cur.fetchone()
        conn.commit()
        return updated_automacao


@router.delete("/automacoes/{automacao_id}")
def delete_automacao(automacao_id: int):
    """Deleta uma automação"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM automacao_whatsapp WHERE id = %s RETURNING id", (automacao_id,))
        deleted = cur.fetchone()
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Automação não encontrada")
        
        conn.commit()
        return {"message": "Automação deletada com sucesso"}


# ============ HISTÓRICO ============

@router.get("/notificacoes")
def get_notificacoes(limit: int = 100):
    """Lista histórico de notificações enviadas"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT n.*, 
                   p.nome as prestador_nome,
                   m.nome as montador_nome
            FROM notificacoes_whatsapp n
            LEFT JOIN prestadores p ON n.prestador_id = p.id
            LEFT JOIN montadores m ON n.montador_id = m.id
            ORDER BY n.data_envio DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


@router.get("/crm-historico")
def get_crm_historico(limit: int = 100):
    """Lista histórico de notificações CRM enviadas via WhatsApp"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT l.*, u.nome as destinatario_nome
            FROM crm_whatsapp_log l
            LEFT JOIN users u ON u.id = l.destinatario_id
            ORDER BY l.criado_em DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


# ============ PROCESSAMENTO DE FILA ============

@router.post("/processar-fila")
def processar_fila(limite: int = 50):
    """Processa mensagens pendentes na fila de WhatsApp"""
    from app.utils.whatsapp_automation import processar_fila_whatsapp
    
    try:
        resultado = processar_fila_whatsapp(limite)
        return {
            "success": True,
            "processados": resultado.get('processados', 0),
            "enviados": resultado.get('enviados', 0),
            "erros": resultado.get('erros', 0),
            "message": resultado.get('message', 'Fila processada')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
