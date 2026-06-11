"""
CRM WhatsApp Automations
Envia notificações WhatsApp para analistas do CRM

Automações:
1. Ticket novo atribuído → Zap para analista
2. Interação de terceiro → Zap para analista responsável
3. Daily 13h → Zap para cada ticket sem interação do dia
4. Lembre-me → Zap agendado pelo analista
"""

import logging
import requests
from datetime import datetime, timedelta
from app.database import get_db_connection
from app.utils.whatsapp_http import WA_HEADERS
import psycopg2.extras

logger = logging.getLogger(__name__)

WHATSAPP_URL = "http://localhost:14003/send"
DOMAIN = "https://suportedg.site"


def _get_template(evento: str) -> str | None:
    """Busca template ativo do DB para um evento CRM. Retorna None se não encontrar."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT t.template
                FROM automacao_whatsapp a
                JOIN templates_whatsapp t ON t.id::text = a.template_id
                WHERE a.evento = %s AND a.ativo = TRUE AND t.ativo = TRUE
            """, (evento,))
            row = cur.fetchone()
            return row["template"] if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar template para {evento}: {e}")
        return None


def _render_template(template: str, variaveis: dict) -> str:
    """Substitui {{variavel}} no template pelos valores fornecidos."""
    msg = template
    for key, val in variaveis.items():
        msg = msg.replace("{{" + key + "}}", str(val) if val else "")
    return msg


def _send_whatsapp(telefone: str, mensagem: str) -> tuple[bool, str | None]:
    """Envia mensagem WhatsApp via serviço local.
    Retorna (sucesso, erro_str_ou_None)."""
    if not telefone:
        logger.warning("Telefone vazio, não enviando WhatsApp")
        return False, "telefone vazio"

    # Limpar telefone: só dígitos
    num = "".join(c for c in telefone if c.isdigit())
    if not num:
        return False, "telefone sem dígitos"
    # Adicionar código do país se necessário
    if len(num) == 11 or len(num) == 10:
        num = "55" + num

    try:
        resp = requests.post(WHATSAPP_URL, json={"number": num, "message": mensagem}, timeout=15, headers=WA_HEADERS)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        try:
            data = resp.json()
        except Exception as e:
            return False, f"json inválido: {e}"
        if data.get("success"):
            return True, None
        return False, str(data.get("error") or data)[:300]
    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp para {num}: {e}")
        return False, str(e)[:300]


def _log_envio(tipo: str, ticket_id: int, destinatario_id: int, telefone: str, mensagem: str, sucesso: bool, erro: str = None):
    """Registra envio no log"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO crm_whatsapp_log (tipo, ticket_id, destinatario_id, telefone, mensagem, sucesso, erro)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (tipo, ticket_id, destinatario_id, telefone, mensagem, sucesso, erro))
            conn.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar log WhatsApp: {e}")


def _get_user_telefone(user_id: int) -> str | None:
    """Busca telefone de um user pelo id"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT telefone FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return row["telefone"] if row else None
    except:
        return None


def _get_ticket_vars(ticket_id: int) -> dict:
    """Busca dados completos do ticket para usar como variáveis de template."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM crm_tickets WHERE id = %s", (ticket_id,))
            t = cur.fetchone()
            if not t:
                return {}
            return {
                "ticket_id": str(t["id"]),
                "id_pedido": t.get("id_pedido") or "",
                "nome_cliente": t.get("nome_cliente") or "",
                "telefone_cliente": t.get("telefone") or "",
                "email_cliente": t.get("email") or "",
                "area": t.get("area") or "",
                "motivo": t.get("motivo") or "",
                "status": t.get("status") or "",
                "status_detalhe": t.get("status_detalhe") or "",
                "prazo": str(t["prazo"]) if t.get("prazo") else "",
                "produto": t.get("produto") or "",
                "nome_produto": t.get("nome_produto") or "",
                "analista_nome": t.get("analista_nome") or "",
                "solicitante_nome": t.get("solicitante_nome") or "",
                "descricao": t.get("descricao") or "",
                "link": f"{DOMAIN}/crm",
            }
    except Exception as e:
        logger.error(f"Erro ao buscar dados do ticket {ticket_id}: {e}")
        return {"ticket_id": str(ticket_id), "link": f"{DOMAIN}/crm"}


# ============================================================
# 1. Ticket novo atribuído
# ============================================================

def notificar_ticket_novo(ticket_id: int, analista_id: int, analista_nome: str,
                          id_pedido: str, nome_cliente: str, area: str, motivo: str = ""):
    """Envia WhatsApp para o analista quando um ticket é atribuído a ele."""
    telefone = _get_user_telefone(analista_id)
    if not telefone:
        logger.warning(f"Analista {analista_id} ({analista_nome}) sem telefone cadastrado")
        return

    # Tentar usar template do banco
    tpl = _get_template("crm_ticket_novo")
    if tpl:
        vars = _get_ticket_vars(ticket_id)
        vars.update({"analista_nome": analista_nome})
        msg = _render_template(tpl, vars)
    else:
        motivo_txt = f"\n📋 Motivo: {area}" if area else ""
        area_txt = f"\n📁 Área: {motivo}" if motivo else ""
        msg = (
            f"🎫 *Novo Ticket CRM #{ticket_id}*\n\n"
            f"👤 Cliente: {nome_cliente}\n"
            f"🔢 Pedido: {id_pedido or 'Sem pedido'}"
            f"{motivo_txt}{area_txt}\n\n"
            f"O ticket foi atribuído a você.\n"
            f"Acesse: {DOMAIN}/crm"
        )

    ok, err = _send_whatsapp(telefone, msg)
    _log_envio("ticket_novo", ticket_id, analista_id, telefone, msg, ok, err)


# ============================================================
# 2. Interação de terceiro
# ============================================================

def notificar_interacao_terceiro(ticket_id: int, analista_id: int, comentador_nome: str, texto: str):
    """Envia WhatsApp para analista quando outro usuário comenta no ticket dele."""
    telefone = _get_user_telefone(analista_id)
    if not telefone:
        return

    preview = (texto[:120] + "...") if len(texto) > 120 else texto

    tpl = _get_template("crm_interacao_terceiro")
    if tpl:
        vars = _get_ticket_vars(ticket_id)
        vars.update({
            "comentador_nome": comentador_nome,
            "texto_comentario": preview,
        })
        msg = _render_template(tpl, vars)
    else:
        msg = (
            f"💬 *Nova interação no Ticket #{ticket_id}*\n\n"
            f"👤 {comentador_nome} comentou:\n"
            f"_{preview}_\n\n"
            f"Acesse: {DOMAIN}/crm"
        )

    ok, err = _send_whatsapp(telefone, msg)
    _log_envio("interacao_terceiro", ticket_id, analista_id, telefone, msg, ok, err)


# ============================================================
# 3. Diário 13h – tickets sem interação
# ============================================================

def executar_lembrete_diario():
    """
    Verifica todos os tickets abertos que NÃO tiveram interação hoje.
    Ignora tickets com data_nova_analise no futuro (estão "adormecidos").
    Envia um WhatsApp para cada analista com seus tickets pendentes.
    """
    logger.info("🕐 Executando lembrete diário CRM 13h")
    enviados = 0

    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Tickets abertos sem interação hoje, que não estão adormecidos
            cur.execute("""
                SELECT t.id, t.id_pedido, t.nome_cliente, t.area, t.analista_id, t.analista_nome,
                       u.telefone
                FROM crm_tickets t
                JOIN users u ON u.id = t.analista_id
                WHERE t.status NOT IN ('resolvido')
                  AND t.analista_id IS NOT NULL
                  AND (t.data_nova_analise IS NULL OR t.data_nova_analise <= CURRENT_DATE)
                  AND NOT EXISTS (
                      SELECT 1 FROM crm_comentarios c
                      WHERE c.ticket_id = t.id AND c.created_at::date = CURRENT_DATE
                  )
                ORDER BY t.analista_id, t.id
            """)
            rows = cur.fetchall()

            if not rows:
                logger.info("Nenhum ticket pendente para lembrete diário")
                return 0

            # Agrupar por analista
            por_analista: dict[int, list] = {}
            for r in rows:
                aid = r["analista_id"]
                if aid not in por_analista:
                    por_analista[aid] = {"nome": r["analista_nome"], "telefone": r["telefone"], "tickets": []}
                por_analista[aid]["tickets"].append(r)

            for analista_id, info in por_analista.items():
                if not info["telefone"]:
                    continue

                linhas = []
                for t in info["tickets"]:
                    linhas.append(f"  • #{t['id']} – {t['nome_cliente']} ({t['area'] or 'Sem motivo'})")

                tpl = _get_template("crm_analise_diaria")
                if tpl:
                    msg = _render_template(tpl, {
                        "analista_nome": info["nome"],
                        "qtd_tickets": str(len(info["tickets"])),
                        "lista_tickets": "\n".join(linhas),
                        "link": f"{DOMAIN}/crm",
                    })
                else:
                    msg = (
                        f"⏰ *Lembrete CRM – Tickets para analisar hoje*\n\n"
                        f"Olá {info['nome']}, você tem *{len(info['tickets'])}* ticket(s) sem interação hoje:\n\n"
                        + "\n".join(linhas) + "\n\n"
                        f"Acesse: {DOMAIN}/crm"
                    )

                ok, err = _send_whatsapp(info["telefone"], msg)
                for t in info["tickets"]:
                    _log_envio("analise_diaria", t["id"], analista_id, info["telefone"], msg, ok, err)
                if ok:
                    enviados += 1

        logger.info(f"Lembrete diário: {enviados} analistas notificados de {len(por_analista)} total")
        return enviados

    except Exception as e:
        logger.error(f"Erro no lembrete diário: {e}")
        return 0


# ============================================================
# 4. Lembre-me – lembretes agendados
# ============================================================

def criar_lembrete(ticket_id: int, usuario_id: int, minutos: int = None, horas: int = None, amanha: bool = False):
    """Cria um lembrete agendado para o usuário. Retorna o lembrete criado."""
    agora = datetime.now()

    if amanha:
        # Amanhã às 9h
        amanha_dt = (agora + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        agendar_para = amanha_dt
    elif horas:
        agendar_para = agora + timedelta(hours=horas)
    elif minutos:
        agendar_para = agora + timedelta(minutes=minutos)
    else:
        agendar_para = agora + timedelta(hours=1)

    telefone = _get_user_telefone(usuario_id)

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO crm_lembretes (ticket_id, usuario_id, usuario_telefone, agendar_para)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (ticket_id, usuario_id, telefone, agendar_para))
        lembrete = dict(cur.fetchone())
        conn.commit()

    lembrete["agendar_para"] = lembrete["agendar_para"].isoformat() if lembrete["agendar_para"] else None
    lembrete["criado_em"] = lembrete["criado_em"].isoformat() if lembrete["criado_em"] else None
    return lembrete


def processar_lembretes_pendentes():
    """Processa lembretes que já passaram da hora. Chamado pelo scheduler a cada 5 min."""
    enviados = 0
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT l.*, t.id_pedido, t.nome_cliente, t.area
                FROM crm_lembretes l
                JOIN crm_tickets t ON t.id = l.ticket_id
                WHERE l.enviado = FALSE AND l.agendar_para <= NOW()
                ORDER BY l.agendar_para ASC
                LIMIT 50
            """)
            lembretes = cur.fetchall()

            for lem in lembretes:
                telefone = lem["usuario_telefone"]
                if not telefone:
                    telefone = _get_user_telefone(lem["usuario_id"])

                tpl = _get_template("crm_lembrete")
                if tpl:
                    vars = _get_ticket_vars(lem["ticket_id"])
                    msg = _render_template(tpl, vars)
                else:
                    msg = (
                        f"🔔 *Lembrete CRM – Ticket #{lem['ticket_id']}*\n\n"
                        f"👤 Cliente: {lem['nome_cliente']}\n"
                        f"🔢 Pedido: {lem['id_pedido'] or 'N/A'}\n"
                        f"📋 Motivo: {lem['area'] or 'N/A'}\n\n"
                        f"Você pediu para ser lembrado sobre este ticket.\n"
                        f"Acesse: {DOMAIN}/crm"
                    )

                ok, err = _send_whatsapp(telefone, msg)
                _log_envio("lembrete", lem["ticket_id"], lem["usuario_id"], telefone, msg, ok, err)

                cur.execute("UPDATE crm_lembretes SET enviado = TRUE WHERE id = %s", (lem["id"],))
                if ok:
                    enviados += 1

            conn.commit()

        if lembretes:
            logger.info(f"Lembretes processados: {enviados}/{len(lembretes)} enviados")
        return enviados

    except Exception as e:
        logger.error(f"Erro ao processar lembretes: {e}")
        return 0


# ============================================================
# Job combinado para o scheduler
# ============================================================

def executar_job_crm_whatsapp():
    """
    Job que roda a cada 5 minutos:
    - Processa lembretes agendados que já venceram
    - Se for 13h (entre 13:00 e 13:04), executa lembrete diário
    """
    agora = datetime.now()

    # Sempre processar lembretes pendentes
    processar_lembretes_pendentes()

    # Lembrete diário: executar se hora = 13 e minuto < 5 (janela de 5 min)
    if agora.hour == 13 and agora.minute < 5:
        executar_lembrete_diario()
