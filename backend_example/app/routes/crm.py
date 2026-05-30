"""
Rotas do CRM - Gerenciamento de Tickets
Endpoints para CRUD de tickets, comentários, e gestão do Kanban
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List
import psycopg2.extras
import os
import uuid
import shutil
from datetime import datetime
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user
from app.crm_whatsapp import notificar_ticket_novo, notificar_interacao_terceiro, criar_lembrete

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "crm")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _ticket_row_to_dict(row: dict, cur, include_children: bool = False) -> dict:
    """Convert a ticket row to full dict with comentários and optionally children"""
    ticket = dict(row)
    ticket["prazo"] = str(ticket["prazo"]) if ticket["prazo"] else None
    ticket["data_nova_analise"] = str(ticket["data_nova_analise"]) if ticket.get("data_nova_analise") else None
    ticket["created_at"] = ticket["created_at"].isoformat() if ticket["created_at"] else None
    ticket["updated_at"] = ticket["updated_at"].isoformat() if ticket["updated_at"] else None

    # Buscar comentários
    cur.execute("""
        SELECT c.id, c.ticket_id, c.usuario_id, c.usuario_nome, c.texto, c.status_detalhe, c.data_nova_analise, c.created_at
        FROM crm_comentarios c
        WHERE c.ticket_id = %s
        ORDER BY c.created_at ASC
    """, (ticket["id"],))
    comentarios = []
    for c in cur.fetchall():
        com = dict(c)
        com["data_nova_analise"] = str(com["data_nova_analise"]) if com.get("data_nova_analise") else None
        com["created_at"] = com["created_at"].isoformat() if com["created_at"] else None
        cur.execute("""
            SELECT nome, url, tipo FROM crm_comentario_anexos WHERE comentario_id = %s
        """, (com["id"],))
        com["anexos"] = [dict(a) for a in cur.fetchall()]
        comentarios.append(com)

    ticket["comentarios"] = comentarios

    # Compute necessita_analise: ticket aberto precisa de interação diária
    if ticket["status"] not in ("resolvido",):
        today = datetime.now().date()
        data_nova = ticket.get("data_nova_analise")
        # Se tem data_nova_analise no futuro, está "adormecido"
        if data_nova and (data_nova if isinstance(data_nova, type(today)) else datetime.strptime(str(data_nova), "%Y-%m-%d").date()) > today:
            ticket["necessita_analise"] = False
        else:
            # Verifica se teve interação hoje
            cur.execute("""
                SELECT 1 FROM crm_comentarios
                WHERE ticket_id = %s AND created_at::date = CURRENT_DATE
                LIMIT 1
            """, (ticket["id"],))
            ticket["necessita_analise"] = cur.fetchone() is None
    else:
        ticket["necessita_analise"] = False

    # Count children
    cur.execute("SELECT COUNT(*) as cnt FROM crm_tickets WHERE parent_id = %s", (ticket["id"],))
    ticket["children_count"] = cur.fetchone()["cnt"]

    # Include full children list if requested
    if include_children:
        cur.execute("""
            SELECT * FROM crm_tickets WHERE parent_id = %s ORDER BY created_at ASC
        """, (ticket["id"],))
        ticket["children"] = [_ticket_row_to_dict(child, cur) for child in cur.fetchall()]
    else:
        ticket["children"] = []

    return ticket


@router.get("/tickets")
def list_tickets(
    status: Optional[str] = None,
    analista_id: Optional[int] = None,
    solicitante_id: Optional[int] = None,
    search: Optional[str] = None,
    area: Optional[str] = None,
    motivo: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Lista todos os tickets do CRM com filtros opcionais"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        conditions = []
        params = []

        if status:
            conditions.append("t.status = %s")
            params.append(status)
        if analista_id:
            conditions.append("t.analista_id = %s")
            params.append(analista_id)
        if solicitante_id:
            conditions.append("t.solicitante_id = %s")
            params.append(solicitante_id)
        if area:
            conditions.append("t.area = %s")
            params.append(area)
        if motivo:
            conditions.append("t.motivo = %s")
            params.append(motivo)
        if search:
            conditions.append("(t.id_pedido ILIKE %s OR t.nome_cliente ILIKE %s OR t.area ILIKE %s OR t.motivo ILIKE %s)")
            s = f"%{search}%"
            params.extend([s, s, s, s])

        # Always exclude child tickets from main listing
        conditions.append("t.parent_id IS NULL")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        cur.execute(f"""
            SELECT t.* FROM crm_tickets t {where}
            ORDER BY t.created_at DESC
        """, params)

        tickets = []
        for row in cur.fetchall():
            tickets.append(_ticket_row_to_dict(row, cur))

        return tickets


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, current_user: dict = Depends(get_current_user)):
    """Obtém um ticket por ID"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM crm_tickets WHERE id = %s", (ticket_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")
        return _ticket_row_to_dict(row, cur, include_children=True)


@router.post("/tickets")
def create_ticket(
    id_pedido: str = Form(...),
    nome_cliente: str = Form(...),
    telefone: str = Form(...),
    email: Optional[str] = Form(""),
    area: str = Form(...),
    motivo: str = Form(...),
    descricao: str = Form(...),
    prazo: str = Form(...),
    glpi: str = Form(...),
    id_processo: str = Form(...),
    plataforma: str = Form(...),
    credenciada: str = Form(...),
    tipo_operacao_venda: Optional[str] = Form(None),
    situacao_timeline: Optional[str] = Form(None),
    produto: Optional[str] = Form(""),
    nome_produto: Optional[str] = Form(""),
    anexos: List[UploadFile] = File([]),
    current_user: dict = Depends(get_current_user),
):
    """Cria um novo ticket CRM. Detecta automaticamente se deve ser filho de ticket existente."""
    if not (motivo or "").strip():
        raise HTTPException(422, "Área é obrigatória")
    anexo_url = ""
    anexo_nome = None

    anexo_urls = []
    anexo_nomes = []
    for arq in anexos:
        if arq and arq.filename:
            ext = os.path.splitext(arq.filename)[1]
            safe_name = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(arq.file, f)
            anexo_urls.append(f"/uploads/crm/{safe_name}")
            anexo_nomes.append(arq.filename)
    anexo_url = "|".join(anexo_urls) if anexo_urls else ""
    anexo_nome = "|".join(anexo_nomes) if anexo_nomes else ""

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Auto-detect parent: find open ticket with same id_pedido + produto
        parent_id = None
        if id_pedido and produto:
            cur.execute("""
                SELECT id FROM crm_tickets
                WHERE id_pedido = %s AND produto = %s
                  AND status != 'resolvido' AND parent_id IS NULL
                ORDER BY created_at ASC
                LIMIT 1
            """, (id_pedido, produto))
            existing = cur.fetchone()
            if existing:
                parent_id = existing["id"]

        # Auto-assign: se sub-ticket, herda analista do pai; senão, analista com menos tickets
        analista_id = None
        analista_nome = None
        if parent_id:
            cur.execute("SELECT analista_id, analista_nome FROM crm_tickets WHERE id = %s", (parent_id,))
            parent = cur.fetchone()
            if parent and parent["analista_id"]:
                analista_id = parent["analista_id"]
                analista_nome = parent["analista_nome"]
        if not analista_id:
            cur.execute("""
                SELECT u.id, u.nome,
                       COALESCE((SELECT COUNT(*) FROM crm_tickets t 
                                 WHERE t.analista_id = u.id AND t.status != 'resolvido'), 0) as ticket_count
                FROM users u
                WHERE u.crm_analista = TRUE AND u.ativo = TRUE
                ORDER BY ticket_count ASC, u.id ASC
                LIMIT 1
            """)
            analista = cur.fetchone()
            if analista:
                analista_id = analista["id"]
                analista_nome = analista["nome"]

        cur.execute("""
            INSERT INTO crm_tickets 
                (id_pedido, nome_cliente, telefone, email, anexo_url, anexo_nome,
                 area, motivo, descricao, glpi, id_processo, plataforma, credenciada, prazo,
                 status, solicitante_id, solicitante_nome, analista_id, analista_nome,
                 tipo_operacao_venda, situacao_timeline, status_detalhe,
                 produto, nome_produto, parent_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'novo', %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s)
            RETURNING *
        """, (
            id_pedido, nome_cliente, telefone, email, anexo_url, anexo_nome,
            area, motivo or "", descricao, glpi or "", id_processo or "", plataforma or "",
            credenciada or "", prazo,
            current_user["id"], current_user["nome"],
            analista_id, analista_nome,
            tipo_operacao_venda, situacao_timeline, area,
            produto or "", nome_produto or "", parent_id,
        ))
        ticket = cur.fetchone()
        conn.commit()

        # WhatsApp: notificar analista atribuído
        if analista_id:
            try:
                notificar_ticket_novo(
                    ticket_id=ticket["id"], analista_id=analista_id,
                    analista_nome=analista_nome or "",
                    id_pedido=id_pedido, nome_cliente=nome_cliente,
                    area=area, motivo=motivo or ""
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erro WhatsApp ticket novo: {e}")

        return _ticket_row_to_dict(ticket, cur)


@router.put("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Move ticket de status (Kanban drag). Auto-atribui analista se necessário."""
    new_status = data.get("status")
    if new_status not in ("novo", "em_andamento", "retorno", "resolvido"):
        raise HTTPException(status_code=400, detail="Status inválido")

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT * FROM crm_tickets WHERE id = %s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        # Auto-assign if moving to em_andamento and no analyst
        analista_id = ticket["analista_id"]
        analista_nome = ticket["analista_nome"]
        if new_status == "em_andamento" and not analista_id:
            cur.execute("""
                SELECT u.id, u.nome,
                       COALESCE((SELECT COUNT(*) FROM crm_tickets t 
                                 WHERE t.analista_id = u.id AND t.status != 'resolvido'), 0) as tc
                FROM users u
                WHERE u.crm_analista = TRUE AND u.ativo = TRUE
                ORDER BY tc ASC, u.id ASC LIMIT 1
            """)
            a = cur.fetchone()
            if a:
                analista_id = a["id"]
                analista_nome = a["nome"]

        cur.execute("""
            UPDATE crm_tickets 
            SET status = %s, analista_id = %s, analista_nome = %s, updated_at = NOW()
            WHERE id = %s RETURNING *
        """, (new_status, analista_id, analista_nome, ticket_id))
        updated = cur.fetchone()
        conn.commit()

        return _ticket_row_to_dict(updated, cur)


@router.post("/tickets/{ticket_id}/comentarios")
async def add_comentario(
    ticket_id: int,
    texto: str = Form(""),
    status_detalhe: Optional[str] = Form(None),
    data_nova_analise: Optional[str] = Form(None),
    anexos: List[UploadFile] = File([]),
    current_user: dict = Depends(get_current_user),
):
    """Adiciona uma interação ao ticket, com anexos opcionais e status obrigatório"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT id FROM crm_tickets WHERE id = %s", (ticket_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        # Update status_detalhe on ticket if provided
        if status_detalhe:
            cur.execute(
                "UPDATE crm_tickets SET status_detalhe = %s, data_nova_analise = %s, updated_at = NOW() WHERE id = %s",
                (status_detalhe, data_nova_analise if data_nova_analise else None, ticket_id)
            )

        # Insert comment
        cur.execute("""
            INSERT INTO crm_comentarios (ticket_id, usuario_id, usuario_nome, texto, status_detalhe, data_nova_analise)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (ticket_id, current_user["id"], current_user["nome"], texto, status_detalhe,
              data_nova_analise if data_nova_analise else None))
        comentario = dict(cur.fetchone())
        comentario["data_nova_analise"] = str(comentario["data_nova_analise"]) if comentario.get("data_nova_analise") else None
        comentario["created_at"] = comentario["created_at"].isoformat() if comentario["created_at"] else None

        # Save attachments
        anexos_info = []
        for file in anexos:
            if file.filename:
                ext = os.path.splitext(file.filename)[1]
                safe_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(UPLOAD_DIR, safe_name)
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)
                url = f"/uploads/crm/{safe_name}"
                cur.execute("""
                    INSERT INTO crm_comentario_anexos (comentario_id, nome, url, tipo)
                    VALUES (%s, %s, %s, %s)
                """, (comentario["id"], file.filename, url, file.content_type or ""))
                anexos_info.append({"nome": file.filename, "url": url, "tipo": file.content_type or ""})

        comentario["anexos"] = anexos_info
        conn.commit()

        # WhatsApp: notificar analista se quem comentou não é o próprio analista
        try:
            cur.execute("SELECT analista_id FROM crm_tickets WHERE id = %s", (ticket_id,))
            tk = cur.fetchone()
            if tk and tk["analista_id"] and tk["analista_id"] != current_user["id"]:
                notificar_interacao_terceiro(
                    ticket_id=ticket_id,
                    analista_id=tk["analista_id"],
                    comentador_nome=current_user["nome"],
                    texto=texto or "(anexo)"
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro WhatsApp interação: {e}")

        return comentario


@router.put("/tickets/{ticket_id}/finalizar")
def finalizar_ticket(
    ticket_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Finaliza um ticket com resolução"""
    resolucao = data.get("resolucao")
    descricao_resolucao = data.get("descricao_resolucao")

    if not resolucao:
        raise HTTPException(status_code=400, detail="Tipo de resolução é obrigatório")
    if not descricao_resolucao:
        raise HTTPException(status_code=400, detail="Descrição da resolução é obrigatória")

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if parent ticket has open children
        cur.execute("""
            SELECT COUNT(*) as open_children
            FROM crm_tickets
            WHERE parent_id = %s AND status != 'resolvido'
        """, (ticket_id,))
        open_children = cur.fetchone()["open_children"]
        if open_children > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível finalizar: existem {open_children} ticket(s) filho(s) em aberto"
            )

        cur.execute("SELECT parent_id FROM crm_tickets WHERE id = %s", (ticket_id,))
        check_ticket = cur.fetchone()
        if not check_ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")
        is_child = check_ticket["parent_id"] is not None

        if is_child:
            # Ticket filho: resolve direto, sem aprovação
            cur.execute("""
                UPDATE crm_tickets 
                SET status = 'resolvido', status_detalhe = %s,
                    resolucao = %s, descricao_resolucao = %s, updated_at = NOW()
                WHERE id = %s RETURNING *
            """, (resolucao, resolucao, descricao_resolucao, ticket_id))
            ticket = cur.fetchone()

            finalizacao_texto = f"🔒 Ticket finalizado\nResolução: {resolucao}\n{descricao_resolucao}"
            cur.execute(
                """INSERT INTO crm_comentarios (ticket_id, usuario_id, usuario_nome, texto, status_detalhe)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (ticket_id, current_user["id"], current_user["nome"], finalizacao_texto, resolucao)
            )
        else:
            # Ticket pai: vai para retorno/aprovação
            cur.execute("""
                UPDATE crm_tickets 
                SET status = 'retorno', status_detalhe = 'Aguardando Aprovação',
                    resolucao = %s, descricao_resolucao = %s, updated_at = NOW()
                WHERE id = %s RETURNING *
            """, (resolucao, descricao_resolucao, ticket_id))
            ticket = cur.fetchone()

            finalizacao_texto = f"🔒 Ticket finalizado\nResolução: {resolucao}\n{descricao_resolucao}"
            cur.execute(
                """INSERT INTO crm_comentarios (ticket_id, usuario_id, usuario_nome, texto, status_detalhe)
                   VALUES (%s, %s, %s, %s, 'Aguardando Aprovação') RETURNING id""",
                (ticket_id, current_user["id"], current_user["nome"], finalizacao_texto)
            )

        conn.commit()

        return _ticket_row_to_dict(ticket, cur)


@router.put("/tickets/{ticket_id}/aprovar")
def aprovar_ticket(
    ticket_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Criador ou admin aprova o retorno do ticket — move para resolvido"""
    comentario = data.get("comentario", "").strip()

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM crm_tickets WHERE id = %s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        # Only creator or admin can approve
        is_admin = current_user.get("role") == "admin"
        is_creator = current_user["id"] == ticket["solicitante_id"]
        if not is_admin and not is_creator:
            raise HTTPException(status_code=403, detail="Apenas o criador ou admin pode aprovar")

        if ticket["status"] != "retorno":
            raise HTTPException(status_code=400, detail="Ticket não está em retorno")

        # Add approval comment
        if comentario:
            cur.execute(
                """INSERT INTO crm_comentarios (ticket_id, usuario_id, usuario_nome, texto, status_detalhe)
                   VALUES (%s, %s, %s, %s, 'Aprovado') RETURNING id""",
                (ticket_id, current_user["id"], current_user["nome"], comentario),
            )
        else:
            cur.execute(
                """INSERT INTO crm_comentarios (ticket_id, usuario_id, usuario_nome, texto, status_detalhe)
                   VALUES (%s, %s, %s, %s, 'Aprovado') RETURNING id""",
                (ticket_id, current_user["id"], current_user["nome"], "Retorno aprovado"),
            )

        cur.execute("""
            UPDATE crm_tickets 
            SET status = 'resolvido', status_detalhe = COALESCE(resolucao, 'Resolvido'), updated_at = NOW()
            WHERE id = %s RETURNING *
        """, (ticket_id,))
        updated = cur.fetchone()
        conn.commit()
        return _ticket_row_to_dict(updated, cur)


@router.put("/tickets/{ticket_id}/recusar")
def recusar_ticket(
    ticket_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Criador ou admin recusa o retorno — volta para em_andamento com mesmo analista"""
    comentario = data.get("comentario", "").strip()

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM crm_tickets WHERE id = %s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        is_admin = current_user.get("role") == "admin"
        is_creator = current_user["id"] == ticket["solicitante_id"]
        if not is_admin and not is_creator:
            raise HTTPException(status_code=403, detail="Apenas o criador ou admin pode recusar")

        if ticket["status"] != "retorno":
            raise HTTPException(status_code=400, detail="Ticket não está em retorno")

        if not comentario:
            raise HTTPException(status_code=400, detail="Informe o motivo da recusa")

        # Add rejection comment
        cur.execute(
            """INSERT INTO crm_comentarios (ticket_id, usuario_id, usuario_nome, texto, status_detalhe)
               VALUES (%s, %s, %s, %s, 'Recusado') RETURNING id""",
            (ticket_id, current_user["id"], current_user["nome"], comentario),
        )

        cur.execute("""
            UPDATE crm_tickets 
            SET status = 'em_andamento', status_detalhe = 'Em Andamento',
                resolucao = NULL, descricao_resolucao = NULL, updated_at = NOW()
            WHERE id = %s RETURNING *
        """, (ticket_id,))
        updated = cur.fetchone()
        conn.commit()
        return _ticket_row_to_dict(updated, cur)


@router.get("/stats")
def get_stats(current_user: dict = Depends(get_current_user)):
    """Retorna estatísticas do CRM"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'novo') as novos,
                COUNT(*) FILTER (WHERE status = 'em_andamento') as em_andamento,
                COUNT(*) FILTER (WHERE status = 'retorno') as retorno,
                COUNT(*) FILTER (WHERE status = 'resolvido') as resolvidos,
                COUNT(*) FILTER (WHERE status NOT IN ('resolvido','retorno') AND prazo < CURRENT_DATE) as atrasados,
                COUNT(*) FILTER (
                    WHERE status NOT IN ('resolvido')
                    AND (data_nova_analise IS NULL OR data_nova_analise <= CURRENT_DATE)
                    AND NOT EXISTS (
                        SELECT 1 FROM crm_comentarios c 
                        WHERE c.ticket_id = crm_tickets.id AND c.created_at::date = CURRENT_DATE
                    )
                ) as necessita_analise
            FROM crm_tickets
        """)
        return dict(cur.fetchone())


@router.get("/analistas")
def get_analistas(current_user: dict = Depends(get_current_user)):
    """Retorna lista de analistas CRM disponíveis"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, nome FROM users 
            WHERE crm_analista = TRUE AND ativo = TRUE
            ORDER BY nome
        """)
        return [dict(r) for r in cur.fetchall()]


@router.put("/tickets/{ticket_id}")
def update_ticket(
    ticket_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza campos do ticket (ex: reatribuir analista)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        updates = []
        params = []

        if "analista_id" in data:
            updates.append("analista_id = %s")
            params.append(data["analista_id"])
        if "analista_nome" in data:
            updates.append("analista_nome = %s")
            params.append(data["analista_nome"])
        if "data_nova_analise" in data:
            updates.append("data_nova_analise = %s")
            params.append(data["data_nova_analise"] if data["data_nova_analise"] else None)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        updates.append("updated_at = NOW()")
        params.append(ticket_id)

        cur.execute(f"""
            UPDATE crm_tickets SET {', '.join(updates)} WHERE id = %s RETURNING *
        """, params)
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")
        conn.commit()

        return _ticket_row_to_dict(ticket, cur)


@router.delete("/tickets/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Exclui um ticket e todos os seus dados (comentários, anexos, filhos)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT id, parent_id FROM crm_tickets WHERE id = %s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        # Delete children first (CASCADE handles comments/attachments)
        cur.execute("DELETE FROM crm_tickets WHERE parent_id = %s", (ticket_id,))
        # Delete the ticket itself
        cur.execute("DELETE FROM crm_tickets WHERE id = %s", (ticket_id,))
        conn.commit()

        return {"ok": True}


# ============================================================
# Parâmetros — Áreas (antigo "Motivos")
# ============================================================

@router.get("/parametros/areas")
def list_areas(current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nome, ativo, ordem FROM crm_areas ORDER BY ordem, nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/parametros/areas")
def create_area(nome: str = Form(...), current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 as next FROM crm_areas")
        next_ord = cur.fetchone()["next"]
        cur.execute(
            "INSERT INTO crm_areas (nome, ordem) VALUES (%s, %s) RETURNING id, nome, ativo, ordem",
            (nome.strip(), next_ord),
        )
        row = dict(cur.fetchone())
        conn.commit()
        return row


@router.put("/parametros/areas/{area_id}")
def update_area(
    area_id: int,
    nome: Optional[str] = Form(None),
    ativo: Optional[bool] = Form(None),
    ordem: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sets, vals = [], []
        if nome is not None:
            sets.append("nome = %s"); vals.append(nome.strip())
        if ativo is not None:
            sets.append("ativo = %s"); vals.append(ativo)
        if ordem is not None:
            sets.append("ordem = %s"); vals.append(ordem)
        if not sets:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(area_id)
        cur.execute(
            f"UPDATE crm_areas SET {', '.join(sets)} WHERE id = %s RETURNING id, nome, ativo, ordem",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Área não encontrada")
        conn.commit()
        return dict(row)


@router.delete("/parametros/areas/{area_id}")
def delete_area(area_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM crm_areas WHERE id = %s", (area_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Área não encontrada")
        conn.commit()
        return {"ok": True}


# ============================================================
# Parâmetros — Motivos
# ============================================================

@router.get("/parametros/motivos")
def list_motivos(area_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if area_id:
            cur.execute("SELECT id, nome, ativo, ordem, area_id FROM crm_motivos WHERE area_id = %s ORDER BY ordem, nome", (area_id,))
        else:
            cur.execute("SELECT id, nome, ativo, ordem, area_id FROM crm_motivos ORDER BY ordem, nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/parametros/motivos")
def create_motivo(nome: str = Form(...), area_id: int = Form(...), current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 as next FROM crm_motivos")
        next_ord = cur.fetchone()["next"]
        cur.execute(
            "INSERT INTO crm_motivos (nome, ordem, area_id) VALUES (%s, %s, %s) RETURNING id, nome, ativo, ordem, area_id",
            (nome.strip(), next_ord, area_id),
        )
        row = dict(cur.fetchone())
        conn.commit()
        return row


@router.put("/parametros/motivos/{motivo_id}")
def update_motivo(
    motivo_id: int,
    nome: Optional[str] = Form(None),
    ativo: Optional[bool] = Form(None),
    ordem: Optional[int] = Form(None),
    area_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sets, vals = [], []
        if nome is not None:
            sets.append("nome = %s"); vals.append(nome.strip())
        if ativo is not None:
            sets.append("ativo = %s"); vals.append(ativo)
        if ordem is not None:
            sets.append("ordem = %s"); vals.append(ordem)
        if area_id is not None:
            sets.append("area_id = %s"); vals.append(area_id)
        if not sets:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(motivo_id)
        cur.execute(
            f"UPDATE crm_motivos SET {', '.join(sets)} WHERE id = %s RETURNING id, nome, ativo, ordem, area_id",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Motivo não encontrado")
        conn.commit()
        return dict(row)


@router.delete("/parametros/motivos/{motivo_id}")
def delete_motivo(motivo_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM crm_motivos WHERE id = %s", (motivo_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Motivo não encontrado")
        conn.commit()
        return {"ok": True}


# ============================================================
# Parâmetros — Status Detalhe
# ============================================================

@router.get("/parametros/status")
def list_status_detalhe(area_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if area_id:
            cur.execute("SELECT id, nome, cor, ativo, ordem, area_id FROM crm_status_detalhe WHERE area_id = %s ORDER BY ordem, nome", (area_id,))
        else:
            cur.execute("SELECT id, nome, cor, ativo, ordem, area_id FROM crm_status_detalhe ORDER BY ordem, nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/parametros/status")
def create_status_detalhe(
    nome: str = Form(...),
    cor: str = Form("gray"),
    area_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 as next FROM crm_status_detalhe")
        next_ord = cur.fetchone()["next"]
        cur.execute(
            "INSERT INTO crm_status_detalhe (nome, cor, ordem, area_id) VALUES (%s, %s, %s, %s) RETURNING id, nome, cor, ativo, ordem, area_id",
            (nome.strip(), cor.strip(), next_ord, area_id),
        )
        row = dict(cur.fetchone())
        conn.commit()
        return row


@router.put("/parametros/status/{status_id}")
def update_status_detalhe(
    status_id: int,
    nome: Optional[str] = Form(None),
    cor: Optional[str] = Form(None),
    ativo: Optional[bool] = Form(None),
    ordem: Optional[int] = Form(None),
    area_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sets, vals = [], []
        if nome is not None:
            sets.append("nome = %s"); vals.append(nome.strip())
        if cor is not None:
            sets.append("cor = %s"); vals.append(cor.strip())
        if ativo is not None:
            sets.append("ativo = %s"); vals.append(ativo)
        if ordem is not None:
            sets.append("ordem = %s"); vals.append(ordem)
        if area_id is not None:
            sets.append("area_id = %s"); vals.append(area_id)
        if not sets:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(status_id)
        cur.execute(
            f"UPDATE crm_status_detalhe SET {', '.join(sets)} WHERE id = %s RETURNING id, nome, cor, ativo, ordem, area_id",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Status não encontrado")
        conn.commit()
        return dict(row)


# ============================================================
# Parâmetros — Resoluções
# ============================================================

@router.get("/parametros/resolucoes")
def list_resolucoes(current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nome, ativo, ordem FROM crm_resolucoes ORDER BY ordem, nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/parametros/resolucoes")
def create_resolucao(nome: str = Form(...), current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 as next FROM crm_resolucoes")
        next_ord = cur.fetchone()["next"]
        cur.execute(
            "INSERT INTO crm_resolucoes (nome, ordem) VALUES (%s, %s) RETURNING id, nome, ativo, ordem",
            (nome.strip(), next_ord),
        )
        row = dict(cur.fetchone())
        conn.commit()
        return row


@router.put("/parametros/resolucoes/{resolucao_id}")
def update_resolucao(
    resolucao_id: int,
    nome: Optional[str] = Form(None),
    ativo: Optional[bool] = Form(None),
    ordem: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sets, vals = [], []
        if nome is not None:
            sets.append("nome = %s"); vals.append(nome.strip())
        if ativo is not None:
            sets.append("ativo = %s"); vals.append(ativo)
        if ordem is not None:
            sets.append("ordem = %s"); vals.append(ordem)
        if not sets:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(resolucao_id)
        cur.execute(
            f"UPDATE crm_resolucoes SET {', '.join(sets)} WHERE id = %s RETURNING id, nome, ativo, ordem",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Resolução não encontrada")
        conn.commit()
        return dict(row)


@router.delete("/parametros/resolucoes/{resolucao_id}")
def delete_resolucao(resolucao_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM crm_resolucoes WHERE id = %s", (resolucao_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Resolução não encontrada")
        conn.commit()
        return {"ok": True}


# ==================== PLATAFORMAS ====================

@router.get("/parametros/plataformas")
def list_plataformas(current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nome, ativo, ordem FROM crm_plataformas ORDER BY ordem, nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/parametros/plataformas")
def create_plataforma(nome: str = Form(...), current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 as next FROM crm_plataformas")
        next_ord = cur.fetchone()["next"]
        cur.execute(
            "INSERT INTO crm_plataformas (nome, ordem) VALUES (%s, %s) RETURNING id, nome, ativo, ordem",
            (nome.strip(), next_ord),
        )
        row = dict(cur.fetchone())
        conn.commit()
        return row


@router.put("/parametros/plataformas/{plat_id}")
def update_plataforma(
    plat_id: int,
    nome: Optional[str] = Form(None),
    ativo: Optional[bool] = Form(None),
    ordem: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sets, vals = [], []
        if nome is not None:
            sets.append("nome = %s"); vals.append(nome.strip())
        if ativo is not None:
            sets.append("ativo = %s"); vals.append(ativo)
        if ordem is not None:
            sets.append("ordem = %s"); vals.append(ordem)
        if not sets:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(plat_id)
        cur.execute(
            f"UPDATE crm_plataformas SET {', '.join(sets)} WHERE id = %s RETURNING id, nome, ativo, ordem",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Plataforma não encontrada")
        conn.commit()
        return dict(row)


@router.delete("/parametros/plataformas/{plat_id}")
def delete_plataforma(plat_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM crm_plataformas WHERE id = %s", (plat_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Plataforma não encontrada")
        conn.commit()
        return {"ok": True}


# ==================== CREDENCIADAS ====================

@router.get("/parametros/credenciadas")
def list_credenciadas(current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nome, ativo, ordem FROM crm_credenciadas ORDER BY ordem, nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/parametros/credenciadas")
def create_credenciada(nome: str = Form(...), current_user: dict = Depends(get_current_user)):
    nome_limpo = (nome or "").strip()
    if not nome_limpo:
        raise HTTPException(400, "Nome é obrigatório")
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 as next FROM crm_credenciadas")
        next_ord = cur.fetchone()["next"]
        try:
            cur.execute(
                "INSERT INTO crm_credenciadas (nome, ordem) VALUES (%s, %s) RETURNING id, nome, ativo, ordem",
                (nome_limpo, next_ord),
            )
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(409, "Credenciada já existe")
        row = dict(cur.fetchone())
        conn.commit()
        return row


@router.put("/parametros/credenciadas/{cred_id}")
def update_credenciada(
    cred_id: int,
    nome: Optional[str] = Form(None),
    ativo: Optional[bool] = Form(None),
    ordem: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sets, vals = [], []
        if nome is not None:
            sets.append("nome = %s"); vals.append(nome.strip())
        if ativo is not None:
            sets.append("ativo = %s"); vals.append(ativo)
        if ordem is not None:
            sets.append("ordem = %s"); vals.append(ordem)
        if not sets:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(cred_id)
        cur.execute(
            f"UPDATE crm_credenciadas SET {', '.join(sets)} WHERE id = %s RETURNING id, nome, ativo, ordem",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Credenciada não encontrada")
        conn.commit()
        return dict(row)


@router.delete("/parametros/credenciadas/{cred_id}")
def delete_credenciada(cred_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM crm_credenciadas WHERE id = %s", (cred_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Credenciada não encontrada")
        conn.commit()
        return {"ok": True}


# ============================================================
# Lembre-me
# ============================================================

@router.post("/tickets/{ticket_id}/lembrete")
def add_lembrete(
    ticket_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Cria lembrete WhatsApp agendado para o usuário.
    data.tipo: '1h', '2h', '6h', 'amanha'
    """
    tipo = data.get("tipo", "1h")

    kwargs = {}
    if tipo == "1h":
        kwargs["horas"] = 1
    elif tipo == "2h":
        kwargs["horas"] = 2
    elif tipo == "6h":
        kwargs["horas"] = 6
    elif tipo == "amanha":
        kwargs["amanha"] = True
    else:
        raise HTTPException(400, "Tipo inválido. Use: 1h, 2h, 6h, amanha")

    lembrete = criar_lembrete(ticket_id=ticket_id, usuario_id=current_user["id"], **kwargs)
    return lembrete


@router.get("/tickets/{ticket_id}/lembretes")
def list_lembretes(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Lista lembretes pendentes do usuário para este ticket"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, ticket_id, agendar_para, enviado, criado_em
            FROM crm_lembretes
            WHERE ticket_id = %s AND usuario_id = %s AND enviado = FALSE
            ORDER BY agendar_para ASC
        """, (ticket_id, current_user["id"]))
        rows = cur.fetchall()
        for r in rows:
            r["agendar_para"] = r["agendar_para"].isoformat() if r["agendar_para"] else None
            r["criado_em"] = r["criado_em"].isoformat() if r["criado_em"] else None
        return rows
