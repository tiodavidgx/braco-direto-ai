"""
Gatilhos de WhatsApp para o kanban Montagem 24h.

Destinatários: todos os users com `acesso_montagem=TRUE`, ativos, com telefone.
Idempotência: tabela `montagem_alertas_enviados (pedido_id, tipo)`.
Log: tabela `montagem_whatsapp_log`.

Todos os envios são silenciosos (nunca levantam exceção) — chamadores devem
envolver em try/except mesmo assim por segurança, seguindo o padrão do CRM.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psycopg2.extras
import requests

from app.database import get_db_connection

logger = logging.getLogger(__name__)

WHATSAPP_URL = os.getenv("WHATSAPP_BASE_URL", "http://localhost:14003")
WA_HEADERS = {"X-Internal-Token": os.getenv("WHATSAPP_INTERNAL_TOKEN", "")}


# ---------------------------------------------------------------------------
# Infra interna
# ---------------------------------------------------------------------------

def _get_template(cur, evento: str) -> Optional[str]:
    cur.execute(
        """
        SELECT t.template
        FROM automacao_whatsapp a
        JOIN templates_whatsapp t ON t.id::text = a.template_id
        WHERE a.evento = %s AND a.ativo = TRUE AND t.ativo = TRUE
        """,
        (evento,),
    )
    r = cur.fetchone()
    if not r:
        return None
    # Suporta tanto RealDictCursor quanto tupla
    return r["template"] if isinstance(r, dict) else r[0]


def _render(template: str, variaveis: Dict) -> str:
    out = template
    for k, v in (variaveis or {}).items():
        out = out.replace("{{" + str(k) + "}}", "" if v is None else str(v))
    return out


def _limpar_telefone(telefone: str) -> str:
    digits = "".join(c for c in (telefone or "") if c.isdigit())
    if not digits:
        return ""
    if not digits.startswith("55"):
        digits = "55" + digits
    return digits


def _send_whatsapp(telefone: str, mensagem: str) -> Tuple[bool, Optional[str]]:
    tel = _limpar_telefone(telefone)
    if not tel:
        return False, "telefone vazio"
    try:
        resp = requests.post(
            f"{WHATSAPP_URL}/send",
            json={"number": tel, "message": mensagem},
            headers=WA_HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            try:
                body = resp.json()
            except Exception:
                body = {}
            if body.get("success"):
                return True, None
            return False, (body.get("error") or resp.text)[:300]
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:  # pragma: no cover
        return False, str(e)[:300]


def _log_envio(
    cur,
    pedido_id: Optional[str],
    user_id: Optional[int],
    tipo: str,
    telefone: Optional[str],
    mensagem: str,
    sucesso: bool,
    erro: Optional[str] = None,
) -> None:
    try:
        cur.execute(
            """
            INSERT INTO montagem_whatsapp_log
                (pedido_id, user_id, tipo, telefone, mensagem, sucesso, erro)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (pedido_id, user_id, tipo, telefone, (mensagem or "")[:4000], sucesso, (erro or None)),
        )
    except Exception as e:  # pragma: no cover
        logger.error(f"[montagem_whatsapp] falha ao logar envio: {e}")


def _destinatarios(cur, excluir_user_id: Optional[int] = None) -> List[Dict]:
    cur.execute(
        """
        SELECT id, nome, telefone
        FROM users
        WHERE acesso_montagem = TRUE
          AND ativo = TRUE
          AND telefone IS NOT NULL
          AND telefone <> ''
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    if excluir_user_id is not None:
        rows = [r for r in rows if r.get("id") != excluir_user_id]
    return rows


def _ja_enviou(cur, pedido_id: str, tipo: str) -> bool:
    cur.execute(
        "SELECT 1 FROM montagem_alertas_enviados WHERE pedido_id = %s AND tipo = %s",
        (pedido_id, tipo),
    )
    return cur.fetchone() is not None


def _marcar_enviado(cur, pedido_id: str, tipo: str) -> None:
    cur.execute(
        """
        INSERT INTO montagem_alertas_enviados (pedido_id, tipo, enviado_em)
        VALUES (%s, %s, NOW())
        ON CONFLICT (pedido_id, tipo) DO UPDATE SET enviado_em = NOW()
        """,
        (pedido_id, tipo),
    )


def _disparar(
    evento: str,
    variaveis: Dict,
    pedido_id: str,
    *,
    excluir_user_id: Optional[int] = None,
    idempotente: bool = False,
) -> int:
    """Dispara o evento para todos os responsáveis. Retorna nº de envios OK."""
    enviados_ok = 0
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            template = _get_template(cur, evento)
            if not template:
                logger.info(f"[montagem_whatsapp] evento '{evento}' sem template/automação ativa — ignorado")
                return 0
            if idempotente and _ja_enviou(cur, pedido_id, evento):
                return 0
            destinatarios = _destinatarios(cur, excluir_user_id=excluir_user_id)
            if not destinatarios:
                logger.info(f"[montagem_whatsapp] nenhum responsável com telefone para '{evento}' (pedido {pedido_id})")
                if idempotente:
                    # marca mesmo sem envio para não varrer toda rodada
                    _marcar_enviado(cur, pedido_id, evento)
                    conn.commit()
                return 0
            mensagem = _render(template, variaveis)
            for d in destinatarios:
                ok, err = _send_whatsapp(d.get("telefone") or "", mensagem)
                _log_envio(
                    cur,
                    pedido_id=pedido_id,
                    user_id=d.get("id"),
                    tipo=evento,
                    telefone=d.get("telefone"),
                    mensagem=mensagem,
                    sucesso=ok,
                    erro=err,
                )
                if ok:
                    enviados_ok += 1
            if idempotente:
                _marcar_enviado(cur, pedido_id, evento)
            conn.commit()
    except Exception as e:  # pragma: no cover
        logger.error(f"[montagem_whatsapp] erro disparando '{evento}' pedido {pedido_id}: {e}")
    return enviados_ok


# ---------------------------------------------------------------------------
# API pública dos gatilhos
# ---------------------------------------------------------------------------

def notificar_novo_ticket(pedido_id: str, variaveis: Dict) -> int:
    return _disparar("montagem_novo_ticket", variaveis, pedido_id, idempotente=True)


def notificar_comentario(
    pedido_id: str,
    comentador_user_id: Optional[int],
    variaveis: Dict,
) -> int:
    return _disparar(
        "montagem_comentario",
        variaveis,
        pedido_id,
        excluir_user_id=comentador_user_id,
        idempotente=False,
    )


def notificar_retomada(pedido_id: str, variaveis: Dict) -> int:
    # Sem idempotência por pedido — pode retomar várias vezes ao longo do tempo.
    return _disparar("montagem_retomada", variaveis, pedido_id, idempotente=False)


def notificar_prazo_4h(pedido_id: str, variaveis: Dict) -> int:
    return _disparar("montagem_prazo_4h", variaveis, pedido_id, idempotente=True)


def notificar_prazo_vencido(pedido_id: str, variaveis: Dict) -> int:
    return _disparar("montagem_prazo_vencido", variaveis, pedido_id, idempotente=True)


# ---------------------------------------------------------------------------
# Lembre-me: lembretes agendados pelo usuário
# ---------------------------------------------------------------------------

def _get_user_telefone(cur, usuario_id: int) -> Optional[str]:
    cur.execute("SELECT telefone FROM users WHERE id = %s", (usuario_id,))
    r = cur.fetchone()
    if not r:
        return None
    return (r["telefone"] if isinstance(r, dict) else r[0]) or None


def _get_user_nome(cur, usuario_id: int) -> Optional[str]:
    cur.execute("SELECT nome FROM users WHERE id = %s", (usuario_id,))
    r = cur.fetchone()
    if not r:
        return None
    return (r["nome"] if isinstance(r, dict) else r[0]) or None


def criar_lembrete(
    pedido_id: str,
    usuario_id: int,
    *,
    horas: Optional[int] = None,
    amanha: bool = False,
) -> Dict:
    """Cria lembrete agendado. Retorna o lembrete criado."""
    agora = datetime.now()

    if amanha:
        agendar_para = (agora + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
    elif horas:
        agendar_para = agora + timedelta(hours=horas)
    else:
        agendar_para = agora + timedelta(hours=1)

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        telefone = _get_user_telefone(cur, usuario_id)
        cur.execute(
            """
            INSERT INTO montagem_lembretes
                (pedido_id, usuario_id, usuario_telefone, agendar_para)
            VALUES (%s, %s, %s, %s)
            RETURNING id, pedido_id, usuario_id, agendar_para, enviado, criado_em
            """,
            (pedido_id, usuario_id, telefone, agendar_para),
        )
        row = dict(cur.fetchone())
        conn.commit()

    row["agendar_para"] = row["agendar_para"].isoformat() if row.get("agendar_para") else None
    row["criado_em"] = row["criado_em"].isoformat() if row.get("criado_em") else None
    return row


def _carregar_dados_pedido(cur, pedido_id: str) -> Optional[Dict]:
    """Carrega dados do pedido para montar variáveis da mensagem."""
    cur.execute(
        """
        SELECT m.id::text AS pedido_id,
               m.identificador_pedido,
               m.filial_venda,
               m.nome_montador,
               m.data_entrega,
               v.nome_cliente
        FROM bot_montagem_mes m
        LEFT JOIN LATERAL (
            SELECT nome_cliente FROM bot_vendas bv
            WHERE bv.identificador_pedido = m.identificador_pedido
            ORDER BY CASE WHEN bv.identificador_nf = m.identificador_nf THEN 0 ELSE 1 END,
                     bv.id DESC
            LIMIT 1
        ) v ON TRUE
        WHERE m.id::text = %s
        LIMIT 1
        """,
        (pedido_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def _inserir_comentario_sistema(cur, pedido_id: str, texto: str, autor_nome: str, autor_id: Optional[int]) -> None:
    """Registra um comentário de sistema no ticket (alimenta o chat)."""
    try:
        cur.execute(
            """
            INSERT INTO montagem_comentarios
                (pedido_id, texto, tipo, autor_id, autor_nome)
            VALUES (%s, %s, 'comentario', %s, %s)
            """,
            (pedido_id, texto, autor_id, autor_nome),
        )
    except Exception as e:  # pragma: no cover
        logger.error(f"[montagem_whatsapp] falha ao inserir comentário de lembrete: {e}")


def processar_lembretes_pendentes() -> int:
    """Dispara lembretes vencidos. Envia WhatsApp e registra comentário no chat."""
    enviados = 0
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                SELECT id, pedido_id, usuario_id, usuario_telefone, agendar_para
                FROM montagem_lembretes
                WHERE enviado = FALSE AND agendar_para <= NOW()
                ORDER BY agendar_para ASC
                LIMIT 50
                """
            )
            lembretes = cur.fetchall()

            if not lembretes:
                return 0

            for lem in lembretes:
                pedido_id = lem["pedido_id"]
                usuario_id = lem["usuario_id"]
                telefone = lem["usuario_telefone"] or _get_user_telefone(cur, usuario_id)
                nome_usuario = _get_user_nome(cur, usuario_id) or "Usuário"

                dados = _carregar_dados_pedido(cur, pedido_id)
                variaveis = {
                    "numero_pedido": (dados or {}).get("identificador_pedido") or pedido_id,
                    "cliente_nome": (dados or {}).get("nome_cliente") or "—",
                    "filial_venda": (dados or {}).get("filial_venda") or "—",
                    "montador_nome": (dados or {}).get("nome_montador") or "—",
                    "prazo_limite_fmt": "",
                }
                data_entrega = (dados or {}).get("data_entrega")
                if data_entrega:
                    try:
                        variaveis["prazo_limite_fmt"] = data_entrega.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        variaveis["prazo_limite_fmt"] = str(data_entrega)

                template = _get_template(cur, "montagem_lembrete")
                if template:
                    mensagem = _render(template, variaveis)
                else:
                    mensagem = (
                        f"🔔 Lembrete – Montagem 24h\n"
                        f"Pedido: {variaveis['numero_pedido']}\n"
                        f"Cliente: {variaveis['cliente_nome']}\n"
                        f"Você pediu para ser lembrado."
                    )

                ok, err = (False, "sem telefone")
                if telefone:
                    ok, err = _send_whatsapp(telefone, mensagem)

                _log_envio(
                    cur,
                    pedido_id=pedido_id,
                    user_id=usuario_id,
                    tipo="lembrete",
                    telefone=telefone,
                    mensagem=mensagem,
                    sucesso=ok,
                    erro=err,
                )

                # Alimenta o chat do ticket
                _inserir_comentario_sistema(
                    cur,
                    pedido_id,
                    f"🔔 Lembrete agendado por {nome_usuario} disparado.",
                    autor_nome=nome_usuario,
                    autor_id=usuario_id,
                )

                cur.execute(
                    "UPDATE montagem_lembretes SET enviado = TRUE WHERE id = %s",
                    (lem["id"],),
                )
                if ok:
                    enviados += 1

            conn.commit()
            logger.info(f"[montagem_whatsapp] lembretes processados: {enviados}/{len(lembretes)}")
    except Exception as e:  # pragma: no cover
        logger.error(f"[montagem_whatsapp] erro processando lembretes: {e}")
    return enviados
