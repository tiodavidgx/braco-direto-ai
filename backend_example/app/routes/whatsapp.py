from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
from datetime import datetime
import psycopg2.extras
from app.database import get_db_connection
from app.utils.whatsapp_automation import formatar_telefone_whatsapp
import subprocess
import os
import signal
import time

router = APIRouter()

WHATSAPP_BASE_URL = "http://localhost:3000"
WHATSAPP_PROCESS = None
# whatsapp.py está em: backend_example/app/routes/whatsapp.py
# server.js está em: whatsapp-service/server.js
# Precisamos subir 3 níveis para chegar à raiz e entrar em whatsapp-service
WHATSAPP_SERVER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
    "whatsapp-service", 
    "server.js"
)


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
        response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2)
        data = response.json()
        data['server_running'] = True
        return data
    except:
        return {
            "status": "error", 
            "error": "Serviço não está rodando",
            "server_running": False
        }


@router.post("/start-server")
def start_whatsapp_server():
    """Inicia o servidor WhatsApp"""
    global WHATSAPP_PROCESS
    
    # Verificar se já está rodando
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=1)
        if response.status_code == 200:
            return {
                "success": True,
                "message": "Servidor WhatsApp já está rodando",
                "already_running": True
            }
    except:
        pass
    
    try:
        # Configurar PATH para incluir caminhos comuns do Node.js
        env = os.environ.copy()
        env['PATH'] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
        
        # Verificar se o Node.js está instalado
        print("🔍 Verificando Node.js...")
        node_check = subprocess.run(["node", "--version"], capture_output=True, text=True, env=env)
        print(f"   Node version: {node_check.stdout.strip()}")
        if node_check.returncode != 0:
            raise HTTPException(status_code=500, detail="Node.js não está instalado")
        
        # Verificar se as dependências estão instaladas
        print(f"🔍 Verificando node_modules em: {os.path.dirname(WHATSAPP_SERVER_PATH)}")
        node_modules_path = os.path.join(os.path.dirname(WHATSAPP_SERVER_PATH), "node_modules")
        print(f"   Path: {node_modules_path}")
        print(f"   Exists: {os.path.exists(node_modules_path)}")
        if not os.path.exists(node_modules_path):
            raise HTTPException(
                status_code=500, 
                detail="Dependências não instaladas. Execute: cd backend_example && npm install"
            )
        
        # Verificar se o arquivo existe
        print(f"🔍 Verificando whatsapp_server.js: {WHATSAPP_SERVER_PATH}")
        print(f"   Exists: {os.path.exists(WHATSAPP_SERVER_PATH)}")
        if not os.path.exists(WHATSAPP_SERVER_PATH):
            raise HTTPException(status_code=500, detail=f"Arquivo não encontrado: {WHATSAPP_SERVER_PATH}")
        
        # Iniciar servidor WhatsApp em background
        print("🚀 Iniciando servidor WhatsApp...")
        print(f"   Comando: node {WHATSAPP_SERVER_PATH}")
        print(f"   Diretório: {os.path.dirname(WHATSAPP_SERVER_PATH)}")
        
        WHATSAPP_PROCESS = subprocess.Popen(
            ["node", WHATSAPP_SERVER_PATH],
            cwd=os.path.dirname(WHATSAPP_SERVER_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=env  # Usar o ambiente modificado com PATH correto
        )
        print(f"   PID: {WHATSAPP_PROCESS.pid}")
        
        # Aguardar um pouco para o servidor iniciar
        print("⏳ Aguardando servidor inicializar...")
        time.sleep(3)
        
        # Verificar se o processo está vivo
        poll_result = WHATSAPP_PROCESS.poll()
        if poll_result is not None:
            # Processo morreu
            stdout, stderr = WHATSAPP_PROCESS.communicate()
            error_msg = stderr.decode('utf-8') if stderr else "Sem mensagem de erro"
            print(f"❌ Processo morreu com código: {poll_result}")
            print(f"   STDERR: {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=f"Servidor falhou ao iniciar: {error_msg}"
            )
        
        # Verificar se iniciou
        print("🔍 Verificando se servidor respondeu...")
        try:
            response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2)
            if response.status_code == 200:
                print("   ✅ Servidor respondendo!")
                return {
                    "success": True,
                    "message": "Servidor WhatsApp iniciado com sucesso",
                    "pid": WHATSAPP_PROCESS.pid
                }
        except Exception as check_error:
            print(f"   ⚠️ Servidor não respondeu ainda: {check_error}")
        
        return {
            "success": True,
            "message": "Servidor WhatsApp está inicializando...",
            "pid": WHATSAPP_PROCESS.pid if WHATSAPP_PROCESS else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Erro ao iniciar servidor:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar servidor: {str(e)}")


@router.post("/stop-server")
def stop_whatsapp_server():
    """Para o servidor WhatsApp"""
    global WHATSAPP_PROCESS
    
    try:
        # Tentar parar gracefully via API
        try:
            requests.post(f"{WHATSAPP_BASE_URL}/disconnect", timeout=2)
        except:
            pass
        
        # Encontrar e matar o processo
        try:
            # No macOS/Linux, procurar pelo processo node rodando server.js (whatsapp-service)
            result = subprocess.run(
                ["pgrep", "-f", "whatsapp-service/server.js"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        os.kill(int(pid), signal.SIGTERM)
                        
                return {
                    "success": True,
                    "message": f"Servidor WhatsApp parado (PIDs: {', '.join(pids)})"
                }
        except Exception as e:
            print(f"Erro ao parar processo: {e}")
        
        # Se temos referência ao processo
        if WHATSAPP_PROCESS:
            WHATSAPP_PROCESS.terminate()
            WHATSAPP_PROCESS.wait(timeout=5)
            WHATSAPP_PROCESS = None
            
            return {
                "success": True,
                "message": "Servidor WhatsApp parado"
            }
        
        return {
            "success": True,
            "message": "Nenhum processo encontrado"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao parar servidor: {str(e)}")


@router.get("/info")
def get_info():
    """Obtém informações do usuário conectado"""
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/info", timeout=2)
        return response.json()
    except:
        return {"success": False, "error": "Não foi possível obter informações"}


@router.post("/send")
def send_message(request: SendMessageRequest):
    """Envia uma mensagem individual"""
    try:
        # Aplicar formatação do telefone (remover 9º dígito)
        telefone_formatado = formatar_telefone_whatsapp(request.number)
        print(f"📞 WhatsApp Send - Telefone: {request.number} -> {telefone_formatado}")
        
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send",
            json={"number": telefone_formatado, "message": request.message},
            timeout=30
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk")
def send_bulk(request: SendBulkRequest):
    """Envia mensagens em massa"""
    try:
        # Aplicar formatação em todos os telefones (remover 9º dígito)
        telefones_formatados = [formatar_telefone_whatsapp(n) for n in request.numbers]
        print(f"📞 WhatsApp Bulk Send - {len(telefones_formatados)} telefones formatados")
        
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send-bulk",
            json={
                "numbers": telefones_formatados,
                "message": request.message,
                "delay": request.delay
            },
            timeout=300
        )
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
