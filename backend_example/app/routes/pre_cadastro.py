"""
Rotas de Pré-Cadastro de Montadores (Onboarding)
Permite criar e gerenciar cadastros em andamento de montadores
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import psycopg2.extras
import os
import uuid
import asyncio
import requests
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user
from app.routes.notifications import notification_manager

router = APIRouter()

# Diretório para uploads
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "pre_cadastro")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# URL do servidor WhatsApp
WHATSAPP_SERVER_URL = os.getenv("WHATSAPP_SERVER_URL", "http://localhost:3000")


def enviar_notificacao_async(tipo: str, titulo: str, mensagem: str, dados: dict = None):
    """Envia notificação via WebSocket de forma assíncrona"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(notification_manager.send_notification(tipo, titulo, mensagem, dados))
        else:
            loop.run_until_complete(notification_manager.send_notification(tipo, titulo, mensagem, dados))
    except RuntimeError:
        # Se não há loop, criar um novo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(notification_manager.send_notification(tipo, titulo, mensagem, dados))


def enviar_whatsapp_gatilho(evento: str, variaveis: dict, telefones: List[str]):
    """
    Envia mensagem WhatsApp baseado no gatilho configurado.
    
    Args:
        evento: Nome do evento (ex: 'pre_cadastro_enviado_revisao')
        variaveis: Dicionário com as variáveis para substituir no template
        telefones: Lista de telefones para enviar
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Buscar configuração do gatilho
            cur.execute("""
                SELECT a.*, t.template 
                FROM automacao_whatsapp a
                LEFT JOIN templates_whatsapp t ON t.id::text = a.template_id
                WHERE a.evento = %s AND a.ativo = true
            """, (evento,))
            
            gatilho = cur.fetchone()
            
            if not gatilho or not gatilho.get('template'):
                print(f"[WhatsApp] Gatilho '{evento}' não configurado ou sem template")
                return
            
            # Substituir variáveis no template
            mensagem = gatilho['template']
            for chave, valor in variaveis.items():
                mensagem = mensagem.replace(f"{{{{{chave}}}}}", str(valor) if valor else "")
            
            # Enviar para cada telefone
            for telefone in telefones:
                if not telefone:
                    continue
                    
                # Formatar telefone (remover caracteres especiais, adicionar código do país)
                telefone_limpo = ''.join(filter(str.isdigit, telefone))
                if len(telefone_limpo) == 11:  # DDD + número
                    telefone_limpo = '55' + telefone_limpo
                elif len(telefone_limpo) == 10:  # DDD + número fixo
                    telefone_limpo = '55' + telefone_limpo
                
                try:
                    print(f"[WhatsApp] Enviando para {telefone_limpo}: {mensagem[:50]}...")
                    response = requests.post(
                        f"{WHATSAPP_SERVER_URL}/send",
                        json={
                            "number": telefone_limpo,
                            "message": mensagem
                        },
                        timeout=10
                    )
                    if response.status_code == 200:
                        print(f"[WhatsApp] ✅ Mensagem enviada para {telefone_limpo}")
                    else:
                        print(f"[WhatsApp] ❌ Erro ao enviar para {telefone_limpo}: {response.text}")
                except Exception as e:
                    print(f"[WhatsApp] Erro de conexão ao enviar para {telefone_limpo}: {e}")
                    
    except Exception as e:
        print(f"[WhatsApp] Erro ao processar gatilho '{evento}': {e}")


def buscar_usuarios_com_permissao(conn, permissao: str) -> List[dict]:
    """Busca usuários que possuem determinada permissão"""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT id, nome, email, telefone 
        FROM users 
        WHERE ativo = true AND ({permissao} = true OR role = 'admin')
    """)
    return [dict(u) for u in cur.fetchall()]


def sortear_responsavel(conn) -> Optional[dict]:
    """
    Sorteia aleatoriamente um revisor ativo para ser responsável pelo card.
    Retorna dict com id, nome e telefone do responsável ou None se não houver revisores.
    """
    import random
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.id, u.nome, u.telefone
        FROM revisores_pre_cadastro r
        JOIN users u ON u.id = r.user_id
        WHERE r.ativo = true AND u.ativo = true
    """)
    revisores = cur.fetchall()
    
    if not revisores:
        return None
    
    return dict(random.choice(revisores))


class PreCadastroCreate(BaseModel):
    tipo_pessoa: str  # PF ou PJ
    nome: str
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    filial: Optional[str] = None
    cidade: Optional[str] = None
    endereco: Optional[str] = None
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    pix: str = ""  # Obrigatório
    percentual_montagem: float = 5.0
    percentual_assistencia: float = 5.0
    percentual_desmontagem: float = 5.0
    auxilio_semanal: float = 100.0
    observacoes: Optional[str] = None
    etapa_atual: int = 1
    # Novos campos - Envio Automático
    envio_automatico: bool = True
    dia_fechamento: int = 25
    dias_envio_mes: Optional[List[int]] = None
    prazo_pagamento_dias: int = 10
    email_responsavel_nm: Optional[str] = None
    # Novos campos - Terceirizada
    tipo_pagamento: str = "novo_mundo"
    terceirizada_id: Optional[int] = None
    # Template de email
    email_template_id: Optional[int] = None


class PreCadastroUpdate(BaseModel):
    tipo_pessoa: Optional[str] = None
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    filial: Optional[str] = None
    cidade: Optional[str] = None
    endereco: Optional[str] = None
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    pix: Optional[str] = None
    percentual_montagem: Optional[float] = None
    percentual_assistencia: Optional[float] = None
    percentual_desmontagem: Optional[float] = None
    auxilio_semanal: Optional[float] = None
    status: Optional[str] = None
    etapa_atual: Optional[int] = None
    observacoes: Optional[str] = None
    # Campos de conclusão
    id_montador: Optional[str] = None
    numero_fornecedor: Optional[str] = None
    re: Optional[str] = None
    # Novos campos - Envio Automático
    envio_automatico: Optional[bool] = None
    dia_fechamento: Optional[int] = None
    dias_envio_mes: Optional[List[int]] = None
    prazo_pagamento_dias: Optional[int] = None
    email_responsavel_nm: Optional[str] = None
    # Novos campos - Terceirizada
    tipo_pagamento: Optional[str] = None
    terceirizada_id: Optional[int] = None
    # Template de email
    email_template_id: Optional[int] = None


@router.get("")
def listar_pre_cadastros(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos os pré-cadastros.
    Admin ou usuário com pode_revisao_cadastro vê todos.
    Operador vê apenas os seus.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                pc.*
            FROM pre_cadastro_montadores pc
            WHERE 1=1
        """
        params = []
        
        # Admin ou quem tem permissão de pré-cadastro ou revisão vê todos
        is_admin = current_user.get('role') == 'admin'
        pode_revisar = current_user.get('pode_revisao_cadastro', False)
        pode_criar = current_user.get('pode_pre_cadastro', False)
        
        # Operadores sem permissão veem apenas seus cadastros
        if not is_admin and not pode_revisar and not pode_criar:
            query += " AND pc.criado_por = %s"
            params.append(current_user['id'])
        
        if status:
            query += " AND pc.status = %s"
            params.append(status)
        
        if search:
            query += " AND (pc.nome ILIKE %s OR pc.cpf_cnpj ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY pc.updated_at DESC"
        
        cur.execute(query, params)
        cadastros = cur.fetchall()
        
        return {"data": [dict(c) for c in cadastros], "total": len(cadastros)}


@router.get("/estatisticas")
def obter_estatisticas(current_user: dict = Depends(get_current_user)):
    """Retorna estatísticas dos pré-cadastros"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Admin ou quem tem permissão de pré-cadastro ou revisão vê todos
        is_admin = current_user.get('role') == 'admin'
        pode_revisar = current_user.get('pode_revisao_cadastro', False)
        pode_criar = current_user.get('pode_pre_cadastro', False)
        
        # Filtro por usuário se não tiver permissão
        user_filter = ""
        params = []
        if not is_admin and not pode_revisar and not pode_criar:
            user_filter = " WHERE criado_por = %s"
            params = [current_user['id']]
        
        cur.execute(f"""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'rascunho') as rascunhos,
                COUNT(*) FILTER (WHERE status = 'aguardando_docs') as aguardando_docs,
                COUNT(*) FILTER (WHERE status = 'em_analise') as em_analise,
                COUNT(*) FILTER (WHERE status = 'aprovado') as aprovados,
                COUNT(*) FILTER (WHERE status = 'convertido') as convertidos,
                COUNT(*) FILTER (WHERE status = 'rejeitado') as rejeitados,
                COUNT(*) as total
            FROM pre_cadastro_montadores
            {user_filter}
        """, params)
        
        stats = cur.fetchone()
        return dict(stats)


@router.get("/{id}")
def obter_pre_cadastro(id: int, current_user: dict = Depends(get_current_user)):
    """Obtém um pré-cadastro específico"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT pc.*
            FROM pre_cadastro_montadores pc
            WHERE pc.id = %s
        """, (id,))
        
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        # Verificar permissão (admin pode ver todos, operador só os seus)
        is_admin = current_user.get('role') == 'admin'
        if not is_admin and cadastro['criado_por'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Sem permissão para acessar este cadastro")
        
        return dict(cadastro)


@router.post("")
def criar_pre_cadastro(
    dados: PreCadastroCreate,
    current_user: dict = Depends(get_current_user)
):
    """Cria um novo pré-cadastro"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            INSERT INTO pre_cadastro_montadores (
                tipo_pessoa, nome, cpf_cnpj, email, telefone,
                filial, cidade, endereco,
                banco, agencia, conta, tipo_conta, pix,
                percentual_montagem, percentual_assistencia, percentual_desmontagem,
                auxilio_semanal, observacoes, etapa_atual,
                criado_por, criado_por_nome, status
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, 'rascunho'
            ) RETURNING *
        """, (
            dados.tipo_pessoa, dados.nome, dados.cpf_cnpj, dados.email, dados.telefone,
            dados.filial, dados.cidade, dados.endereco,
            dados.banco, dados.agencia, dados.conta, dados.tipo_conta, dados.pix,
            dados.percentual_montagem, dados.percentual_assistencia, dados.percentual_desmontagem,
            dados.auxilio_semanal, dados.observacoes, dados.etapa_atual,
            current_user.get('id'), current_user.get('nome', current_user.get('email'))
        ))
        
        cadastro = cur.fetchone()
        conn.commit()
        
        return dict(cadastro)


@router.put("/{id}")
def atualizar_pre_cadastro(
    id: int,
    dados: PreCadastroUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Atualiza um pré-cadastro existente"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe e permissão
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        is_admin = current_user.get('role') == 'admin'
        if not is_admin and cadastro['criado_por'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Sem permissão para editar este cadastro")
        
        # Construir query de update dinâmica
        update_fields = []
        params = []
        
        dados_dict = dados.dict(exclude_unset=True)
        for field, value in dados_dict.items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        update_fields.append("updated_at = NOW()")
        
        params.append(id)
        
        cur.execute(f"""
            UPDATE pre_cadastro_montadores
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """, params)
        
        cadastro_atualizado = cur.fetchone()
        conn.commit()
        
        # GATILHO 1: Notificação quando pré-cadastro é enviado para revisão
        status_anterior = cadastro.get('status')
        status_novo = cadastro_atualizado.get('status')
        
        if status_anterior != 'aguardando_docs' and status_novo == 'aguardando_docs':
            nome_montador = cadastro_atualizado.get('nome', 'Sem nome')
            criado_por_nome = cadastro_atualizado.get('criado_por_nome', 'Usuário')
            
            # Sortear responsável aleatoriamente
            responsavel = sortear_responsavel(conn)
            if responsavel:
                cur.execute("""
                    UPDATE pre_cadastro_montadores
                    SET responsavel_id = %s, responsavel_nome = %s
                    WHERE id = %s
                """, (responsavel['id'], responsavel['nome'], id))
                conn.commit()
                
                # Atualizar dados locais
                cadastro_atualizado = dict(cadastro_atualizado)
                cadastro_atualizado['responsavel_id'] = responsavel['id']
                cadastro_atualizado['responsavel_nome'] = responsavel['nome']
            
            enviar_notificacao_async(
                tipo="info",
                titulo="📋 Novo Pré-Cadastro para Revisão",
                mensagem=f"O pré-cadastro de {nome_montador} foi enviado para revisão por {criado_por_nome}." + (f" Responsável: {responsavel['nome']}" if responsavel else ""),
                dados={
                    "tipo_notificacao": "pre_cadastro_enviado_revisao",
                    "pre_cadastro_id": id,
                    "nome_montador": nome_montador,
                    "criado_por": criado_por_nome,
                    "responsavel_id": responsavel['id'] if responsavel else None,
                    "responsavel_nome": responsavel['nome'] if responsavel else None
                }
            )
            
            # GATILHO WHATSAPP: Notificar APENAS o responsável sorteado
            if responsavel and responsavel.get('telefone'):
                enviar_whatsapp_gatilho(
                    evento='pre_cadastro_enviado_revisao',
                    variaveis={
                        'nome_montador': nome_montador,
                        'criado_por': criado_por_nome,
                        'responsavel': responsavel['nome']
                    },
                    telefones=[responsavel['telefone']]
                )
        
        return dict(cadastro_atualizado) if isinstance(cadastro_atualizado, dict) else dict(cadastro_atualizado)


@router.post("/{id}/upload/{tipo_documento}")
async def upload_documento(
    id: int,
    tipo_documento: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload de documento para um pré-cadastro
    tipo_documento: comprovante_endereco, comprovante_bancario, documento_pessoal, comprovante_mei
    """
    tipos_validos = ['comprovante_endereco', 'comprovante_bancario', 'documento_pessoal', 'comprovante_mei']
    if tipo_documento not in tipos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido. Use: {tipos_validos}")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe e permissão
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        is_admin = current_user.get('role') == 'admin'
        if not is_admin and cadastro['criado_por'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Sem permissão")
        
        # Salvar arquivo
        ext = os.path.splitext(file.filename)[1] if file.filename else '.pdf'
        filename = f"{id}_{tipo_documento}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Atualizar banco - também limpa o status/motivo quando um novo documento é enviado
        campo = f"doc_{tipo_documento}"
        campo_status = f"doc_{tipo_documento}_status"
        campo_motivo = f"doc_{tipo_documento}_motivo"
        cur.execute(f"""
            UPDATE pre_cadastro_montadores
            SET {campo} = %s, {campo_status} = NULL, {campo_motivo} = NULL, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (f"/uploads/pre_cadastro/{filename}", id))
        
        cadastro_atualizado = cur.fetchone()
        conn.commit()
        
        return {
            "message": "Documento enviado com sucesso",
            "arquivo": f"/uploads/pre_cadastro/{filename}",
            "cadastro": dict(cadastro_atualizado)
        }


@router.delete("/{id}")
def excluir_pre_cadastro(id: int, current_user: dict = Depends(get_current_user)):
    """Exclui um pré-cadastro (apenas admin ou criador)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        is_admin = current_user.get('role') == 'admin'
        if not is_admin and cadastro['criado_por'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Sem permissão")
        
        # Não permitir excluir se já foi convertido
        if cadastro['status'] == 'convertido':
            raise HTTPException(status_code=400, detail="Não é possível excluir um cadastro já convertido")
        
        cur.execute("DELETE FROM pre_cadastro_montadores WHERE id = %s", (id,))
        conn.commit()
        
        return {"message": "Pré-cadastro excluído com sucesso"}


class ConcluirCadastroRequest(BaseModel):
    id_montador: str
    numero_fornecedor: str
    re: str


@router.post("/{id}/concluir")
def concluir_cadastro(
    id: int,
    dados: ConcluirCadastroRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Conclui o pré-cadastro, salvando ID montador, número fornecedor, RE e quem concluiu.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        if cadastro['status'] == 'convertido':
            raise HTTPException(status_code=400, detail="Este cadastro já foi concluído")
        
        # Atualizar com os dados de conclusão
        cur.execute("""
            UPDATE pre_cadastro_montadores
            SET status = 'convertido',
                id_montador = %s,
                numero_fornecedor = %s,
                re = %s,
                concluido_por = %s,
                concluido_por_nome = %s,
                concluido_em = NOW(),
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (
            dados.id_montador,
            dados.numero_fornecedor,
            dados.re,
            current_user.get('id'),
            current_user.get('nome', current_user.get('email')),
            id
        ))
        
        cadastro_atualizado = cur.fetchone()
        conn.commit()
        
        # GATILHO 3: Notificação quando cadastro é concluído
        nome_montador = cadastro_atualizado.get('nome', 'Sem nome')
        concluido_por_nome = current_user.get('nome', current_user.get('email', 'Revisor'))
        criado_por_id = cadastro.get('criado_por')
        criado_por_nome = cadastro.get('criado_por_nome', 'Usuário')
        
        enviar_notificacao_async(
            tipo="success",
            titulo="✅ Cadastro de Montador Concluído!",
            mensagem=f"O cadastro de {nome_montador} foi concluído com sucesso por {concluido_por_nome}. ID: {dados.id_montador}",
            dados={
                "tipo_notificacao": "cadastro_concluido",
                "pre_cadastro_id": id,
                "nome_montador": nome_montador,
                "id_montador": dados.id_montador,
                "numero_fornecedor": dados.numero_fornecedor,
                "re": dados.re,
                "concluido_por": concluido_por_nome,
                "criado_por_id": criado_por_id,
                "criado_por_nome": criado_por_nome
            }
        )
        
        # GATILHO WHATSAPP: Notificar quem criou o pré-cadastro sobre a conclusão
        if criado_por_id:
            cur.execute("SELECT telefone FROM users WHERE id = %s AND ativo = true", (criado_por_id,))
            criador = cur.fetchone()
            if criador and criador.get('telefone'):
                enviar_whatsapp_gatilho(
                    evento='cadastro_montador_concluido',
                    variaveis={
                        'nome_montador': nome_montador,
                        'id_montador': dados.id_montador or '',
                        'numero_fornecedor': dados.numero_fornecedor or '',
                        're': dados.re or '',
                        'concluido_por': concluido_por_nome
                    },
                    telefones=[criador['telefone']]
                )
        
        return {
            "message": "Cadastro concluído com sucesso!",
            "cadastro": dict(cadastro_atualizado)
        }


class RevisaoDocumentoRequest(BaseModel):
    tipo_documento: str  # documento_pessoal, comprovante_endereco, comprovante_bancario, comprovante_mei
    status: str  # aprovado, recusado
    motivo: Optional[str] = None


@router.post("/{id}/revisar-documento")
def revisar_documento(
    id: int,
    dados: RevisaoDocumentoRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Revisa um documento do pré-cadastro (aprovar ou recusar com motivo).
    Qualquer usuário autenticado pode revisar documentos.
    """
    tipos_validos = ['documento_pessoal', 'comprovante_endereco', 'comprovante_bancario', 'comprovante_mei']
    if dados.tipo_documento not in tipos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido. Use: {tipos_validos}")
    
    if dados.status not in ['aprovado', 'recusado']:
        raise HTTPException(status_code=400, detail="Status deve ser 'aprovado' ou 'recusado'")
    
    if dados.status == 'recusado' and not dados.motivo:
        raise HTTPException(status_code=400, detail="Motivo é obrigatório quando o documento é recusado")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        # Verificar se o documento existe
        campo_doc = f"doc_{dados.tipo_documento}"
        if not cadastro.get(campo_doc):
            raise HTTPException(status_code=400, detail="Este documento não foi enviado")
        
        # Atualizar status e motivo do documento
        campo_status = f"doc_{dados.tipo_documento}_status"
        campo_motivo = f"doc_{dados.tipo_documento}_motivo"
        
        # Se aprovado, limpar o motivo
        motivo = dados.motivo if dados.status == 'recusado' else None
        
        cur.execute(f"""
            UPDATE pre_cadastro_montadores
            SET {campo_status} = %s, {campo_motivo} = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (dados.status, motivo, id))
        
        cadastro_atualizado = cur.fetchone()
        
        # Se algum documento foi recusado, atualizar status geral para pendente
        # para que o montador saiba que precisa reenviar
        if dados.status == 'recusado':
            cur.execute("""
                UPDATE pre_cadastro_montadores
                SET status = 'aguardando_docs'
                WHERE id = %s AND status NOT IN ('convertido', 'rejeitado')
            """, (id,))
            
            # GATILHO 2: Notificação quando documento é recusado (pendência)
            nome_montador = cadastro_atualizado.get('nome', 'Sem nome')
            revisor_nome = current_user.get('nome', current_user.get('email', 'Revisor'))
            criado_por_id = cadastro.get('criado_por')
            
            # Mapeamento de nomes amigáveis para tipos de documento
            nomes_documentos = {
                'documento_pessoal': 'Documento Pessoal (RG/CPF/CNH)',
                'comprovante_endereco': 'Comprovante de Endereço',
                'comprovante_bancario': 'Comprovante Bancário',
                'comprovante_mei': 'Comprovante MEI'
            }
            nome_doc = nomes_documentos.get(dados.tipo_documento, dados.tipo_documento)
            
            enviar_notificacao_async(
                tipo="warning",
                titulo="⚠️ Documento Recusado - Ação Necessária",
                mensagem=f"O documento '{nome_doc}' do cadastro de {nome_montador} foi recusado. Motivo: {dados.motivo}",
                dados={
                    "tipo_notificacao": "documento_recusado",
                    "pre_cadastro_id": id,
                    "nome_montador": nome_montador,
                    "tipo_documento": dados.tipo_documento,
                    "motivo": dados.motivo,
                    "revisor": revisor_nome,
                    "criado_por_id": criado_por_id
                }
            )
            
            # GATILHO WHATSAPP: Notificar quem criou o pré-cadastro sobre a pendência
            if criado_por_id:
                cur.execute("SELECT telefone FROM users WHERE id = %s AND ativo = true", (criado_por_id,))
                criador = cur.fetchone()
                if criador and criador.get('telefone'):
                    enviar_whatsapp_gatilho(
                        evento='documento_recusado_pre_cadastro',
                        variaveis={
                            'nome_montador': nome_montador,
                            'tipo_documento': nome_doc,
                            'motivo': dados.motivo,
                            'revisor': revisor_nome
                        },
                        telefones=[criador['telefone']]
                    )
        
        conn.commit()
        
        return {
            "message": f"Documento {dados.status} com sucesso",
            "cadastro": dict(cadastro_atualizado)
        }


@router.post("/{id}/limpar-documento/{tipo_documento}")
def limpar_documento(
    id: int,
    tipo_documento: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Limpa um documento para permitir reenvio.
    Remove o arquivo e limpa o status de revisão.
    """
    tipos_validos = ['documento_pessoal', 'comprovante_endereco', 'comprovante_bancario', 'comprovante_mei']
    if tipo_documento not in tipos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido. Use: {tipos_validos}")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        # Verificar permissão (admin ou criador)
        is_admin = current_user.get('role') == 'admin'
        if not is_admin and cadastro['criado_por'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Sem permissão")
        
        # Limpar campos do documento
        campo_doc = f"doc_{tipo_documento}"
        campo_status = f"doc_{tipo_documento}_status"
        campo_motivo = f"doc_{tipo_documento}_motivo"
        
        cur.execute(f"""
            UPDATE pre_cadastro_montadores
            SET {campo_doc} = NULL, {campo_status} = NULL, {campo_motivo} = NULL, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (id,))
        
        cadastro_atualizado = cur.fetchone()
        conn.commit()
        
        return {
            "message": "Documento removido com sucesso",
            "cadastro": dict(cadastro_atualizado)
        }


@router.post("/{id}/converter")
def converter_para_montador(
    id: int,
    identificador: str,
    fornecedor_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Converte um pré-cadastro aprovado em um montador real.
    Requer identificador e fornecedor_id que não estão no pré-cadastro.
    """
    # Apenas admin pode converter
    is_admin = current_user.get('role') == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem converter cadastros")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM pre_cadastro_montadores WHERE id = %s", (id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Pré-cadastro não encontrado")
        
        if cadastro['status'] not in ['aprovado', 'em_analise']:
            raise HTTPException(status_code=400, detail="Apenas cadastros aprovados ou em análise podem ser convertidos")
        
        # Verificar se identificador já existe
        cur.execute("SELECT id FROM montadores WHERE identificador = %s", (identificador,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Identificador já existe")
        
        # Criar montador
        cur.execute("""
            INSERT INTO montadores (
                nome, identificador, email, fornecedor_id, telefone, pix,
                percentual_montagem, percentual_assistencia, percentual_desmontagem,
                auxilio_semanal, filial, localidade, ativo,
                envio_automatico, dia_fechamento, dias_envio_mes, prazo_pagamento_dias,
                email_responsavel_nm, tipo_pagamento, terceirizada_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, true,
                %s, %s, %s, %s,
                %s, %s, %s
            ) RETURNING id
        """, (
            cadastro['nome'],
            identificador,
            cadastro['email'] or f"{identificador}@temp.com",
            fornecedor_id,
            cadastro['telefone'],
            cadastro.get('pix') or '',
            cadastro['percentual_montagem'] / 100,  # Converter para decimal
            cadastro['percentual_assistencia'] / 100,
            cadastro['percentual_desmontagem'] / 100,
            cadastro['auxilio_semanal'],
            cadastro['filial'],
            cadastro['cidade'],
            cadastro.get('envio_automatico', False),
            cadastro.get('dia_fechamento', 25),
            cadastro.get('dias_envio_mes', []),
            cadastro.get('prazo_pagamento_dias', 10),
            cadastro.get('email_responsavel_nm'),
            cadastro.get('tipo_pagamento', 'novo_mundo'),
            cadastro.get('terceirizada_id'),
        ))
        
        montador = cur.fetchone()
        montador_id = montador['id']
        
        # Atualizar pré-cadastro
        cur.execute("""
            UPDATE pre_cadastro_montadores
            SET status = 'convertido', montador_convertido_id = %s, updated_at = NOW()
            WHERE id = %s
        """, (montador_id, id))
        
        conn.commit()
        
        return {
            "message": "Montador criado com sucesso!",
            "montador_id": montador_id,
            "pre_cadastro_id": id
        }


# ==================== ENDPOINTS DE REVISORES ====================

@router.get("/revisores/lista")
def listar_revisores(current_user: dict = Depends(get_current_user)):
    """Lista todos os revisores configurados (apenas admin)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver revisores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT r.id, r.user_id, r.ativo, r.created_at,
                   u.nome, u.email, u.telefone
            FROM revisores_pre_cadastro r
            JOIN users u ON u.id = r.user_id
            ORDER BY u.nome
        """)
        return [dict(r) for r in cur.fetchall()]


@router.get("/revisores/disponiveis")
def listar_usuarios_disponiveis(current_user: dict = Depends(get_current_user)):
    """Lista usuários que podem ser adicionados como revisores (apenas admin)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver usuários disponíveis")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT u.id, u.nome, u.email, u.telefone, u.role,
                   CASE WHEN r.id IS NOT NULL THEN true ELSE false END as ja_revisor
            FROM users u
            LEFT JOIN revisores_pre_cadastro r ON r.user_id = u.id
            WHERE u.ativo = true
            ORDER BY u.nome
        """)
        return [dict(u) for u in cur.fetchall()]


@router.post("/revisores/adicionar/{user_id}")
def adicionar_revisor(user_id: int, current_user: dict = Depends(get_current_user)):
    """Adiciona um usuário como revisor (apenas admin)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores podem adicionar revisores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se usuário existe
        cur.execute("SELECT id, nome FROM users WHERE id = %s AND ativo = true", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Inserir ou atualizar
        cur.execute("""
            INSERT INTO revisores_pre_cadastro (user_id, ativo)
            VALUES (%s, true)
            ON CONFLICT (user_id) DO UPDATE SET ativo = true
            RETURNING *
        """, (user_id,))
        
        conn.commit()
        return {"message": f"Usuário {user['nome']} adicionado como revisor"}


@router.delete("/revisores/remover/{user_id}")
def remover_revisor(user_id: int, current_user: dict = Depends(get_current_user)):
    """Remove um usuário como revisor (apenas admin)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover revisores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            UPDATE revisores_pre_cadastro SET ativo = false WHERE user_id = %s
        """, (user_id,))
        
        conn.commit()
        return {"message": "Revisor removido"}


@router.put("/revisores/toggle/{user_id}")
def toggle_revisor(user_id: int, current_user: dict = Depends(get_current_user)):
    """Ativa/desativa um revisor (apenas admin)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar revisores")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            UPDATE revisores_pre_cadastro 
            SET ativo = NOT ativo 
            WHERE user_id = %s
            RETURNING ativo
        """, (user_id,))
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Revisor não encontrado")
        
        conn.commit()
        return {"ativo": result['ativo']}

