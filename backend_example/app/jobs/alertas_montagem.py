"""
Job recorrente de alertas WhatsApp para o kanban Montagem 24h.

Detecta e dispara:
- montagem_novo_ticket       — primeiro avistamento de um pedido (idempotente).
- montagem_retomada          — transição de standby -> pendente/em_andamento.
- montagem_prazo_4h          — SLA com <=4h e >0 restante, pendente/em_andamento.
- montagem_prazo_vencido     — SLA com <=0 restante, pendente/em_andamento.

Comentários são tratados síncrono na rota de comentários, não aqui.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

import psycopg2.extras

from app.database import get_db_connection
from app.routes.montagem import (  # type: ignore
    _derivar_coluna,
    _query_adiamentos,
    _query_marcacoes,
    _query_view,
    _tabela_existe,
)
from app.utils import montagem_whatsapp as mw
from app.utils.sla_montagem import calcular_sla

logger = logging.getLogger(__name__)


def _fmt_dt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y %H:%M")
    return str(v)


def _montar_variaveis(row: Dict, prazo_limite: Optional[datetime]) -> Dict:
    minutos = None
    if prazo_limite is not None:
        try:
            agora = datetime.now(prazo_limite.tzinfo) if prazo_limite.tzinfo else datetime.now()
            minutos = int((prazo_limite - agora).total_seconds() // 60)
        except Exception:
            minutos = None

    horas_restantes = ""
    if minutos is not None:
        h = minutos // 60
        horas_restantes = str(h) if h >= 0 else "0"

    return {
        "numero_pedido": row.get("identificador_pedido") or str(row.get("pedido_id") or ""),
        "cliente_nome": row.get("cliente_nome") or "—",
        "filial_venda": row.get("filial_venda") or "—",
        "montador_nome": row.get("nome_montador") or "—",
        "data_entrega_fmt": _fmt_dt(row.get("data_entrega")),
        "prazo_limite_fmt": _fmt_dt(prazo_limite),
        "horas_restantes": horas_restantes,
    }


def _carregar_ultimo_status(cur) -> Dict[str, str]:
    cur.execute("SELECT pedido_id, coluna FROM montagem_ultimo_status")
    return {r["pedido_id"]: r["coluna"] for r in cur.fetchall()}


def _filiais_config(cur) -> Optional[list]:
    """Filiais marcadas na config global do kanban.
    Retorna None se config não existe (= não restringir)."""
    try:
        cur.execute("SELECT filiais FROM montagem_config WHERE id = 1")
        row = cur.fetchone()
        if not row:
            return None
        filiais = row["filiais"] or []
        if not isinstance(filiais, list):
            return None
        return [str(f).strip() for f in filiais if str(f).strip()]
    except Exception:
        return None


def _corte_alertas(cur) -> Optional[datetime]:
    """Timestamp de corte: só alerta pedidos cujo importado_em >= corte.
    Configurável em montagem_config.alertas_corte_em (default = atualizado_em)."""
    try:
        cur.execute(
            """
            SELECT COALESCE(alertas_corte_em, atualizado_em) AS corte
            FROM montagem_config WHERE id = 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        return row.get("corte")
    except Exception:
        return None


def _salvar_ultimo_status(cur, pedido_id: str, coluna: str) -> None:
    cur.execute(
        """
        INSERT INTO montagem_ultimo_status (pedido_id, coluna, atualizado_em)
        VALUES (%s, %s, NOW())
        ON CONFLICT (pedido_id) DO UPDATE
           SET coluna = EXCLUDED.coluna, atualizado_em = NOW()
        """,
        (pedido_id, coluna),
    )


def executar_alertas_montagem() -> Dict:
    """Executa uma passada completa de detecção. Retorna sumário."""
    summary = {
        "itens_analisados": 0,
        "novo_ticket": 0,
        "retomada": 0,
        "prazo_4h": 0,
        "prazo_vencido": 0,
        "erros": 0,
    }

    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if not _tabela_existe(cur):
                logger.info("[alertas_montagem] tabela bot_montagem_mes ainda não existe — ignorando")
                return summary

            rows = _query_view(cur, filiais=None, data_de=None, data_ate=None)
            pedido_ids = [str(r.get("pedido_id")) for r in rows if r.get("pedido_id") is not None]
            marcacoes = _query_marcacoes(cur, pedido_ids)
            adiamentos = _query_adiamentos(cur, pedido_ids)
            ultimos = _carregar_ultimo_status(cur)

            filiais_cfg = _filiais_config(cur)
            filtrar_por_filial = bool(filiais_cfg)
            corte = _corte_alertas(cur)

            summary["itens_analisados"] = len(rows)

            # Coletamos as ações primeiro para evitar locks longos no loop
            acoes = []
            for row in rows:
                try:
                    pedido_id = str(row.get("pedido_id"))
                    marcacao = marcacoes.get(pedido_id)
                    adiamento = adiamentos.get(pedido_id)

                    # Corte temporal: só alerta pedidos importados DEPOIS do corte.
                    # Pedidos pré-existentes não geram mensagem.
                    importado_em = row.get("importado_em")
                    depois_do_corte = True
                    if corte is not None and importado_em is not None:
                        try:
                            imp = importado_em
                            if hasattr(imp, "tzinfo") and imp.tzinfo is None and hasattr(corte, "tzinfo") and corte.tzinfo is not None:
                                # compara "naive" vs "aware": normaliza ambos como naive
                                imp_cmp = imp
                                corte_cmp = corte.replace(tzinfo=None)
                            elif hasattr(imp, "tzinfo") and imp.tzinfo is not None and hasattr(corte, "tzinfo") and corte.tzinfo is None:
                                imp_cmp = imp.replace(tzinfo=None)
                                corte_cmp = corte
                            else:
                                imp_cmp = imp
                                corte_cmp = corte
                            depois_do_corte = imp_cmp >= corte_cmp
                        except Exception:
                            depois_do_corte = True

                    # Filtro por filial: só alerta para filiais marcadas na config global.
                    filial_row = (row.get("filial_venda") or "").strip()
                    if filtrar_por_filial and filial_row not in filiais_cfg:
                        coluna = _derivar_coluna(row, marcacao)
                        if adiamento and not row.get("data_montagem"):
                            coluna = "standby"
                        _salvar_ultimo_status(cur, pedido_id, coluna)
                        continue

                    if not depois_do_corte:
                        coluna = _derivar_coluna(row, marcacao)
                        if adiamento and not row.get("data_montagem"):
                            coluna = "standby"
                        _salvar_ultimo_status(cur, pedido_id, coluna)
                        continue

                    coluna = _derivar_coluna(row, marcacao)
                    if adiamento and not row.get("data_montagem"):
                        coluna = "standby"

                    prazo = None
                    minutos = None
                    data_entrega = row.get("data_entrega")
                    if data_entrega and coluna != "finalizado":
                        try:
                            sla = calcular_sla(data_entrega)
                            prazo = sla.prazo_limite
                            minutos = sla.minutos_restantes
                        except Exception:
                            prazo = None
                            minutos = None

                    variaveis = _montar_variaveis(row, prazo)

                    # Novo ticket: qualquer pedido não finalizado que nunca recebeu alerta
                    if coluna != "finalizado":
                        acoes.append(("novo_ticket", pedido_id, variaveis))

                    # Transição standby -> outra coluna (exceto finalizado para evitar ruído)
                    anterior = ultimos.get(pedido_id)
                    if anterior == "standby" and coluna in ("pendente", "em_andamento"):
                        acoes.append(("retomada", pedido_id, variaveis))

                    # SLA
                    if coluna in ("pendente", "em_andamento") and minutos is not None:
                        if minutos <= 0:
                            acoes.append(("prazo_vencido", pedido_id, variaveis))
                        elif minutos <= 240:
                            acoes.append(("prazo_4h", pedido_id, variaveis))

                    _salvar_ultimo_status(cur, pedido_id, coluna)
                except Exception as e:
                    summary["erros"] += 1
                    logger.error(f"[alertas_montagem] erro avaliando pedido {row.get('pedido_id')}: {e}")

            conn.commit()

        # Dispara (cada dispatch abre sua própria conexão)
        for kind, pedido_id, variaveis in acoes:
            try:
                if kind == "novo_ticket":
                    n = mw.notificar_novo_ticket(pedido_id, variaveis)
                    if n > 0:
                        summary["novo_ticket"] += 1
                elif kind == "retomada":
                    n = mw.notificar_retomada(pedido_id, variaveis)
                    if n > 0:
                        summary["retomada"] += 1
                elif kind == "prazo_4h":
                    n = mw.notificar_prazo_4h(pedido_id, variaveis)
                    if n > 0:
                        summary["prazo_4h"] += 1
                elif kind == "prazo_vencido":
                    n = mw.notificar_prazo_vencido(pedido_id, variaveis)
                    if n > 0:
                        summary["prazo_vencido"] += 1
            except Exception as e:
                summary["erros"] += 1
                logger.error(f"[alertas_montagem] erro disparando {kind} pedido {pedido_id}: {e}")

    except Exception as e:
        logger.error(f"[alertas_montagem] erro geral: {e}")
        summary["erros"] += 1

    return summary
