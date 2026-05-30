"""
Rotas de Acompanhamento de Montagem.

Fonte canônica: tabela `bot_montagem_mes` (view materializada importada via
bot externo — ver /api/dados-bot). Marcações manuais ficam em
`montagem_marcacoes` e complementam/antecipam o status antes do próximo sync.
"""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Literal

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.database import get_db_connection
from app.routes._auth_deps import get_current_user
from app.utils.sla_montagem import calcular_sla, sla_to_dict


router = APIRouter()

# Diretório de uploads para anexos de comentários de montagem.
# Servido via nginx em /uploads/montagem_comentarios/.
UPLOAD_DIR_MONTAGEM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "uploads",
    "montagem_comentarios",
)
os.makedirs(UPLOAD_DIR_MONTAGEM, exist_ok=True)

# Tabela canônica (ex-view `vw_acompanhamento_montagem`).
TABLE_NAME = "bot_montagem_mes"

# Corte fixo: Montagem 24h só considera registros a partir desta data
# de entrega (Data da Entrega >= DATA_CORTE). Acordado em 22/04/2026.
DATA_CORTE = "2026-04-20"

# Situações (boletim/timeline) que indicam pedido concluído.
STATUS_BOLETIM_FINAL = {"fechado", "finalizado", "cancelado", "concluído", "concluido"}
STATUS_TIMELINE_FINAL = {"entregue", "montado", "retirado", "concluído", "concluido"}
STATUS_BOLETIM_EM_ANDAMENTO = {"em andamento", "em execução", "em execucao"}

Coluna = Literal["pendente", "em_andamento", "finalizado"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConcluirMontagemRequest(BaseModel):
    observacao: Optional[str] = Field(None, max_length=2000)
    motivo_atraso: Optional[str] = Field(None, max_length=2000)


class IniciarMontagemRequest(BaseModel):
    observacao: Optional[str] = Field(None, max_length=2000)


class ComentarioRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=2000)


MOTIVOS_ADIAMENTO = {"cliente_outra_data", "telefone_invalido"}


class AdiarRequest(BaseModel):
    motivo: str = Field(..., description="cliente_outra_data | telefone_invalido")
    nova_data: Optional[str] = Field(None, description="ISO datetime — para cliente_outra_data")
    confirmou_vitrine: Optional[bool] = False
    observacao: Optional[str] = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tabela_existe(cur) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        LIMIT 1
        """,
        (TABLE_NAME,),
    )
    return cur.fetchone() is not None


def _norm(v: Optional[str]) -> str:
    return (v or "").strip().lower()


def _derivar_coluna(row: dict, marcacao: Optional[dict]) -> Coluna:
    boletim = _norm(row.get("situacao_boletim"))
    timeline = _norm(row.get("situacao_timeline"))

    # Finalizado automaticamente APENAS quando o ERP informou data_montagem.
    # Status de boletim/timeline sem data_montagem não conta como finalizado.
    if row.get("data_montagem"):
        return "finalizado"
    if marcacao and marcacao.get("concluido_em"):
        return "finalizado"
    if boletim in STATUS_BOLETIM_EM_ANDAMENTO:
        return "em_andamento"
    if marcacao and marcacao.get("iniciado_em"):
        return "em_andamento"
    # Montador atribuído no ERP já indica que está em andamento.
    if (row.get("nome_montador") or "").strip() or (row.get("identificador_montador") or "").strip():
        return "em_andamento"
    return "pendente"


def _fmt(dt) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    if isinstance(dt, date):
        # Serializa date "pura" como ISO local sem TZ para evitar que o
        # frontend (new Date) interprete como UTC e mostre o dia anterior.
        return f"{dt.isoformat()}T00:00:00"
    return str(dt)


def _monta_item(
    row: dict,
    marcacao: Optional[dict],
    comentarios: Optional[List[dict]] = None,
    adiamento: Optional[dict] = None,
) -> dict:
    coluna = _derivar_coluna(row, marcacao)

    # Adiamento ativo sobrescreve a coluna (vira standby), exceto quando
    # o ERP já confirmou data_montagem.
    if adiamento and not row.get("data_montagem"):
        coluna = "standby"

    data_entrega = row.get("data_entrega")
    data_montagem = row.get("data_montagem")
    sla = None
    if data_entrega and coluna != "finalizado":
        try:
            sla = sla_to_dict(calcular_sla(data_entrega))
        except Exception:  # pragma: no cover — robustez p/ dados sujos
            sla = None

    # Avaliação de prazo para itens finalizados: compara data_montagem
    # (quando o ERP informar) com o prazo_limite calculado a partir da
    # data_entrega. Se data_montagem <= prazo_limite => dentro do prazo.
    conclusao_sla = None
    if coluna == "finalizado" and data_entrega:
        try:
            base = calcular_sla(data_entrega)
            prazo = base.prazo_limite
            dm_cmp: Optional[datetime] = None
            apenas_data = False
            if isinstance(data_montagem, datetime):
                dm_cmp = data_montagem
                if dm_cmp.tzinfo is None:
                    dm_cmp = dm_cmp.replace(tzinfo=prazo.tzinfo)
            elif isinstance(data_montagem, date):
                # Coluna DATE (sem hora). Compara por dia: dentro do prazo
                # se data_montagem <= prazo_limite.date().
                dm_cmp = datetime.combine(data_montagem, time(0, 0), tzinfo=prazo.tzinfo)
                apenas_data = True
            if dm_cmp is not None:
                if apenas_data:
                    dentro = data_montagem <= prazo.date()  # type: ignore[arg-type]
                    delta_min = int((dm_cmp - prazo).total_seconds() // 60)
                else:
                    delta_min = int((dm_cmp - prazo).total_seconds() // 60)
                    dentro = delta_min <= 0
                conclusao_sla = {
                    "prazo_limite": prazo.isoformat(),
                    "data_montagem": _fmt(data_montagem),
                    "dentro_do_prazo": dentro,
                    "diferenca_minutos": delta_min,
                    "etapa": base.etapa,
                    "apenas_data": apenas_data,
                }
            else:
                conclusao_sla = {
                    "prazo_limite": prazo.isoformat(),
                    "data_montagem": None,
                    "dentro_do_prazo": None,
                    "diferenca_minutos": None,
                    "etapa": base.etapa,
                    "apenas_data": False,
                }
        except Exception:
            conclusao_sla = None

    concluido_local = bool(marcacao and marcacao.get("concluido_em"))
    boletim = _norm(row.get("situacao_boletim"))
    travado_pelo_erp = boletim in STATUS_BOLETIM_FINAL or bool(row.get("data_montagem"))

    return {
        "pedido_id": str(row.get("pedido_id")),
        "numero_pedido": row.get("identificador_pedido") or str(row.get("pedido_id")),
        "cliente_nome": row.get("cliente_nome"),
        "filial_venda": row.get("filial_venda"),
        "filial_saida": row.get("filial_saida"),
        "nota_fiscal": row.get("nota_fiscal"),
        "serie_nota_fiscal": row.get("serie_nota_fiscal"),
        "data_entrega": _fmt(data_entrega),
        "data_previsao_montagem": _fmt(row.get("data_previsao_montagem")),
        "status_erp": row.get("situacao_boletim"),
        "data_montagem": _fmt(row.get("data_montagem")),
        "montador_nome": row.get("nome_montador"),
        "identificador_montador": row.get("identificador_montador"),
        "produto": row.get("produto"),
        "nome_produto": row.get("nome_produto"),
        "produtos_resumo": row.get("nome_produto"),
        "situacao_boletim": row.get("situacao_boletim"),
        "situacao_timeline": row.get("situacao_timeline"),
        "valor_pedido": None,
        "observacoes_erp": row.get("observacao_montagem"),
        "atualizado_em": _fmt(row.get("importado_em")),
        # estado consolidado
        "coluna": coluna,
        "sla": sla,
        "conclusao_sla": conclusao_sla,
        # marcações locais
        "travado_pelo_erp": travado_pelo_erp,
        "marcacao_local": {
            "iniciado_em": _fmt((marcacao or {}).get("iniciado_em")),
            "iniciado_por_user_id": (marcacao or {}).get("iniciado_por_user_id"),
            "concluido_em": _fmt((marcacao or {}).get("concluido_em")),
            "concluido_por_user_id": (marcacao or {}).get("concluido_por_user_id"),
            "observacao": (marcacao or {}).get("observacao"),
            "motivo_atraso": (marcacao or {}).get("motivo_atraso"),
        } if marcacao else None,
        # flag útil: usuário marcou local, ERP ainda não confirmou
        "conclusao_pendente_erp": concluido_local and not travado_pelo_erp,
        # novas listas/objetos
        "comentarios": comentarios or [],
        "adiamento": adiamento,
    }


# SELECT base: bot_montagem_mes LEFT JOIN bot_vendas (cliente_nome)
_SELECT_BASE = f"""
    SELECT
        m.id::text                         AS pedido_id,
        m.identificador_pedido,
        m.identificador_nf,
        m.identificador_boletim_montagem,
        m.filial_saida,
        m.filial_venda,
        m.nota_fiscal,
        m.serie_nota_fiscal,
        m.data_entrega,
        m.data_previsao_montagem,
        m.data_montagem,
        m.situacao_boletim,
        m.situacao_timeline,
        m.identificador_montador,
        m.nome_montador,
        m.produto,
        m.nome_produto,
        m.observacao_montagem,
        m.importado_em,
        v.nome_cliente                     AS cliente_nome
    FROM {TABLE_NAME} m
    LEFT JOIN LATERAL (
        SELECT nome_cliente
        FROM bot_vendas bv
        WHERE bv.identificador_pedido = m.identificador_pedido
        ORDER BY CASE WHEN bv.identificador_nf = m.identificador_nf THEN 0 ELSE 1 END,
                 bv.id DESC
        LIMIT 1
    ) v ON TRUE
"""


def _query_view(
    cur,
    *,
    filiais: Optional[List[str]],
    data_de: Optional[str],
    data_ate: Optional[str],
) -> List[dict]:
    wheres: List[str] = []
    params: List = []

    # Corte fixo: Montagem 24h só a partir de DATA_CORTE (pela data de entrega).
    # data_de do request só estreita além do corte, nunca o afrouxa.
    corte_efetivo = data_de if (data_de and data_de > DATA_CORTE) else DATA_CORTE
    wheres.append("m.data_entrega >= %s")
    params.append(corte_efetivo)

    if filiais:
        wheres.append("m.filial_venda = ANY(%s)")
        params.append(filiais)
    if data_ate:
        wheres.append("m.data_entrega <= %s")
        params.append(data_ate)

    # Cancelados nunca aparecem no kanban
    wheres.append("COALESCE(LOWER(m.situacao_boletim), '') <> 'cancelado'")

    where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""
    sql = f"""
        {_SELECT_BASE}
        {where_sql}
        ORDER BY m.data_entrega ASC NULLS LAST, m.id ASC
    """
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _query_marcacoes(cur, pedido_ids: List[str]) -> dict:
    if not pedido_ids:
        return {}
    cur.execute(
        """
        SELECT pedido_id, iniciado_em, iniciado_por_user_id,
               concluido_em, concluido_por_user_id, observacao, motivo_atraso
        FROM montagem_marcacoes
        WHERE pedido_id = ANY(%s)
        """,
        (pedido_ids,),
    )
    return {dict(r)["pedido_id"]: dict(r) for r in cur.fetchall()}


def _query_comentarios(cur, pedido_ids: List[str]) -> dict:
    """Retorna dict {pedido_id: [comentario, ...]} ordenado por data."""
    if not pedido_ids:
        return {}
    cur.execute(
        """
        SELECT id, pedido_id, texto, tipo, nova_data,
               autor_id, autor_nome, criado_em
        FROM montagem_comentarios
        WHERE pedido_id = ANY(%s)
        ORDER BY criado_em ASC
        """,
        (pedido_ids,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    ids = [r["id"] for r in rows]
    anexos_map: dict = {}
    if ids:
        cur.execute(
            """
            SELECT comentario_id, nome, url, tipo
            FROM montagem_comentario_anexos
            WHERE comentario_id = ANY(%s)
            ORDER BY id ASC
            """,
            (ids,),
        )
        for a in cur.fetchall():
            ad = dict(a)
            anexos_map.setdefault(ad["comentario_id"], []).append({
                "nome": ad.get("nome"),
                "url": ad.get("url"),
                "tipo": ad.get("tipo") or "",
            })
    agg: dict = {}
    for row in rows:
        pid = row["pedido_id"]
        agg.setdefault(pid, []).append({
            "id": str(row["id"]),
            "texto": row["texto"],
            "tipo": row.get("tipo") or "comentario",
            "nova_data": _fmt(row.get("nova_data")),
            "autor_id": row.get("autor_id"),
            "autor_nome": row.get("autor_nome") or "—",
            "criado_em": _fmt(row.get("criado_em")),
            "anexos": anexos_map.get(row["id"], []),
        })
    return agg


def _query_adiamentos(cur, pedido_ids: List[str]) -> dict:
    """Retorna dict {pedido_id: adiamento_ativo} — apenas ativos."""
    if not pedido_ids:
        return {}
    cur.execute(
        """
        SELECT pedido_id, motivo, motivo_descricao, nova_data, retorno_em,
               confirmou_vitrine, criado_em, criado_por_user_id, criado_por_nome
        FROM montagem_adiamentos
        WHERE pedido_id = ANY(%s) AND ativo
        """,
        (pedido_ids,),
    )
    out: dict = {}
    for r in cur.fetchall():
        row = dict(r)
        out[row["pedido_id"]] = {
            "motivo": row.get("motivo"),
            "motivo_descricao": row.get("motivo_descricao"),
            "nova_data": _fmt(row.get("nova_data")),
            "retorno_em": _fmt(row.get("retorno_em")),
            "confirmou_vitrine": bool(row.get("confirmou_vitrine")),
            "criado_em": _fmt(row.get("criado_em")),
            "criado_por_user_id": row.get("criado_por_user_id"),
            "criado_por_nome": row.get("criado_por_nome"),
        }
    return out


def _buscar_view_um(cur, pedido_id: str) -> Optional[dict]:
    cur.execute(
        f"{_SELECT_BASE} WHERE m.id::text = %s LIMIT 1",
        (pedido_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _buscar_marcacao(cur, pedido_id: str) -> Optional[dict]:
    cur.execute(
        """
        SELECT pedido_id, iniciado_em, iniciado_por_user_id,
               concluido_em, concluido_por_user_id, observacao, motivo_atraso
        FROM montagem_marcacoes WHERE pedido_id = %s
        """,
        (pedido_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Endpoints de leitura
# ---------------------------------------------------------------------------

@router.get("")
def listar_montagens(
    filial: Optional[List[str]] = Query(None, description="Uma ou mais filiais"),
    coluna: Optional[Coluna] = Query(None, description="Filtra por coluna do kanban"),
    data_de: Optional[str] = Query(None, description="ISO date/datetime mínimo de entrega"),
    data_ate: Optional[str] = Query(None, description="ISO date/datetime máximo de entrega"),
    current_user: dict = Depends(get_current_user),
):
    """
    Lista os pedidos do kanban de acompanhamento de montagem.
    Responde 200 com `view_indisponivel=true` caso a view ainda não exista
    no banco — permite o frontend mostrar um estado vazio amigável.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            return {
                "view_indisponivel": True,
                "itens": [],
                "resumo": _resumo_vazio(),
                "filiais_disponiveis": [],
            }

        rows = _query_view(
            cur,
            filiais=filial,
            data_de=data_de,
            data_ate=data_ate,
        )
        pedidos_ids = [str(r.get("pedido_id")) for r in rows if r.get("pedido_id") is not None]
        marcacoes = _query_marcacoes(cur, pedidos_ids)
        comentarios_map = _query_comentarios(cur, pedidos_ids)
        adiamentos_map = _query_adiamentos(cur, pedidos_ids)

    itens = [
        _monta_item(
            r,
            marcacoes.get(str(r.get("pedido_id"))),
            comentarios_map.get(str(r.get("pedido_id"))),
            adiamentos_map.get(str(r.get("pedido_id"))),
        )
        for r in rows
    ]
    if coluna:
        itens = [i for i in itens if i["coluna"] == coluna]

    filiais_disponiveis = sorted({i["filial_venda"] for i in itens if i.get("filial_venda")})
    resumo = _resumo_de(itens)

    return {
        "view_indisponivel": False,
        "itens": itens,
        "resumo": resumo,
        "filiais_disponiveis": filiais_disponiveis,
    }


@router.get("/filiais")
def listar_filiais_montagem(
    current_user: dict = Depends(get_current_user),
):
    """Lista filiais de venda presentes em bot_montagem_mes (após DATA_CORTE).
    Usado apenas para popular o filtro — leve."""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            return {"filiais": []}
        cur.execute(
            f"""
            SELECT DISTINCT filial_venda
            FROM {TABLE_NAME}
            WHERE data_entrega >= %s
              AND filial_venda IS NOT NULL
              AND filial_venda <> ''
            ORDER BY filial_venda
            """,
            (DATA_CORTE,),
        )
        filiais = [r["filial_venda"] for r in cur.fetchall()]
    return {"filiais": filiais}


class MontagemConfigRequest(BaseModel):
    filiais: List[str] = Field(default_factory=list)


@router.get("/config")
def get_montagem_config(
    current_user: dict = Depends(get_current_user),
):
    """Configuração global compartilhada do kanban (filiais selecionadas)."""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT filiais FROM montagem_config WHERE id = 1")
        row = cur.fetchone()
        if not row:
            return {"filiais": []}
        filiais = row["filiais"] or []
        # JSONB já vem como list em psycopg2
        if not isinstance(filiais, list):
            filiais = []
        return {"filiais": filiais}


@router.put("/config")
def set_montagem_config(
    body: MontagemConfigRequest,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza a configuração global do kanban.
    Só admins ou usuários com acesso_montagem podem alterar."""
    if not (
        current_user.get("role") == "admin"
        or current_user.get("acesso_montagem")
    ):
        raise HTTPException(403, "Sem permissão para alterar configuração do kanban.")

    # normaliza: remove vazios/duplicados preservando ordem
    filiais_limpas: List[str] = []
    vistos = set()
    for f in body.filiais or []:
        v = (f or "").strip()
        if v and v not in vistos:
            vistos.add(v)
            filiais_limpas.append(v)

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO montagem_config (id, filiais, atualizado_em, atualizado_por)
            VALUES (1, %s::jsonb, NOW(), %s)
            ON CONFLICT (id) DO UPDATE
               SET filiais = EXCLUDED.filiais,
                   atualizado_em = NOW(),
                   atualizado_por = EXCLUDED.atualizado_por
            RETURNING filiais
            """,
            (psycopg2.extras.Json(filiais_limpas), current_user.get("id")),
        )
        row = cur.fetchone()
    return {"filiais": row["filiais"] if row else filiais_limpas}


@router.get("/resumo")
def resumo_montagens(
    filial: Optional[List[str]] = Query(None),
    data_de: Optional[str] = Query(None),
    data_ate: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            return {"view_indisponivel": True, **_resumo_vazio()}

        rows = _query_view(cur, filiais=filial, data_de=data_de, data_ate=data_ate)
        pedidos_ids = [str(r.get("pedido_id")) for r in rows if r.get("pedido_id") is not None]
        marcacoes = _query_marcacoes(cur, pedidos_ids)
        adiamentos_map = _query_adiamentos(cur, pedidos_ids)

    itens = [
        _monta_item(
            r,
            marcacoes.get(str(r.get("pedido_id"))),
            None,
            adiamentos_map.get(str(r.get("pedido_id"))),
        )
        for r in rows
    ]
    return {"view_indisponivel": False, **_resumo_de(itens)}


def _resumo_vazio() -> dict:
    return {
        "total": 0,
        "pendente": 0,
        "em_andamento": 0,
        "finalizado": 0,
        "standby": 0,
        "fora_do_prazo": 0,
        "proximo_corte": 0,
    }


def _resumo_de(itens: List[dict]) -> dict:
    r = _resumo_vazio()
    r["total"] = len(itens)
    for i in itens:
        col = i["coluna"]
        if col in r:
            r[col] += 1
        sla = i.get("sla") or {}
        status = sla.get("status_sla")
        if status == "fora_do_prazo":
            r["fora_do_prazo"] += 1
        elif status == "proximo_corte":
            r["proximo_corte"] += 1
    return r


# ---------------------------------------------------------------------------
# Marcações manuais
# ---------------------------------------------------------------------------

def _upsert_marcacao(cur, pedido_id: str, fields: dict) -> dict:
    cols = list(fields.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols])
    cur.execute(
        f"""
        INSERT INTO montagem_marcacoes (pedido_id, {', '.join(cols)})
        VALUES (%s, {placeholders})
        ON CONFLICT (pedido_id) DO UPDATE SET {updates}
        RETURNING pedido_id, iniciado_em, iniciado_por_user_id,
                  concluido_em, concluido_por_user_id, observacao, motivo_atraso
        """,
        (pedido_id, *[fields[c] for c in cols]),
    )
    return dict(cur.fetchone())


@router.post("/{pedido_id}/iniciar")
def iniciar_montagem(
    pedido_id: str,
    body: IniciarMontagemRequest,
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            raise HTTPException(503, "Tabela de montagem ainda não disponível.")

        row = _buscar_view_um(cur, pedido_id)
        if not row:
            raise HTTPException(404, "Pedido não encontrado na montagem do mês.")

        boletim = _norm(row.get("situacao_boletim"))
        if boletim in STATUS_BOLETIM_FINAL:
            raise HTTPException(409, "Pedido já consta como concluído no ERP.")

        marcacao = _upsert_marcacao(
            cur,
            pedido_id,
            {
                "iniciado_em": datetime.utcnow(),
                "iniciado_por_user_id": current_user.get("id"),
                "observacao": body.observacao,
            },
        )

    return _monta_item(row, marcacao)


@router.delete("/{pedido_id}/iniciar")
def desfazer_iniciar(
    pedido_id: str,
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            UPDATE montagem_marcacoes
               SET iniciado_em = NULL,
                   iniciado_por_user_id = NULL
             WHERE pedido_id = %s
             RETURNING pedido_id
            """,
            (pedido_id,),
        )
        found = cur.fetchone()

    if not found:
        raise HTTPException(404, "Nenhuma marcação local para este pedido.")
    return {"ok": True}


@router.post("/{pedido_id}/concluir")
def concluir_montagem(
    pedido_id: str,
    body: ConcluirMontagemRequest,
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            raise HTTPException(503, "Tabela de montagem ainda não disponível.")

        row = _buscar_view_um(cur, pedido_id)
        if not row:
            raise HTTPException(404, "Pedido não encontrado na montagem do mês.")

        boletim = _norm(row.get("situacao_boletim"))
        if boletim in {"fechado", "finalizado"}:
            raise HTTPException(409, "Pedido já consta como concluído no ERP.")
        if boletim == "cancelado":
            raise HTTPException(409, "Pedido cancelado no ERP não pode ser concluído.")

        marcacao = _upsert_marcacao(
            cur,
            pedido_id,
            {
                "concluido_em": datetime.utcnow(),
                "concluido_por_user_id": current_user.get("id"),
                "observacao": body.observacao,
                "motivo_atraso": body.motivo_atraso,
            },
        )

    return _monta_item(row, marcacao)


@router.delete("/{pedido_id}/concluir")
def desfazer_concluir(
    pedido_id: str,
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            UPDATE montagem_marcacoes
               SET concluido_em = NULL,
                   concluido_por_user_id = NULL,
                   motivo_atraso = NULL
             WHERE pedido_id = %s
             RETURNING pedido_id
            """,
            (pedido_id,),
        )
        found = cur.fetchone()

    if not found:
        raise HTTPException(404, "Nenhuma marcação local para este pedido.")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Comentários e Adiamento
# ---------------------------------------------------------------------------

def _autor_nome(user: dict) -> Optional[str]:
    return user.get("nome") or user.get("name") or user.get("username")


def _inserir_comentario(
    cur,
    pedido_id: str,
    texto: str,
    user: dict,
    tipo: str = "comentario",
    nova_data=None,
    anexos: Optional[List[UploadFile]] = None,
) -> dict:
    cur.execute(
        """
        INSERT INTO montagem_comentarios
            (pedido_id, texto, tipo, nova_data, autor_id, autor_nome)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, texto, tipo, nova_data, autor_id, autor_nome, criado_em
        """,
        (
            pedido_id,
            texto,
            tipo,
            nova_data,
            user.get("id"),
            _autor_nome(user),
        ),
    )
    r = dict(cur.fetchone())
    comentario_id = r["id"]

    anexos_info: List[dict] = []
    if anexos:
        for file in anexos:
            if not file or not file.filename:
                continue
            ext = os.path.splitext(file.filename)[1]
            safe_name = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR_MONTAGEM, safe_name)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            url = f"/uploads/montagem_comentarios/{safe_name}"
            tipo_mime = file.content_type or ""
            cur.execute(
                """
                INSERT INTO montagem_comentario_anexos
                    (comentario_id, nome, url, tipo)
                VALUES (%s, %s, %s, %s)
                """,
                (comentario_id, file.filename, url, tipo_mime),
            )
            anexos_info.append({"nome": file.filename, "url": url, "tipo": tipo_mime})

    return {
        "id": str(comentario_id),
        "texto": r["texto"],
        "tipo": r.get("tipo") or "comentario",
        "nova_data": _fmt(r.get("nova_data")),
        "autor_id": r.get("autor_id"),
        "autor_nome": r.get("autor_nome") or "—",
        "criado_em": _fmt(r.get("criado_em")),
        "anexos": anexos_info,
    }


def _montar_retorno_item(cur, pedido_id: str) -> dict:
    row = _buscar_view_um(cur, pedido_id)
    if not row:
        raise HTTPException(404, "Pedido não encontrado.")
    marcacao = _buscar_marcacao(cur, pedido_id)
    comentarios = _query_comentarios(cur, [pedido_id]).get(pedido_id, [])
    adiamento = _query_adiamentos(cur, [pedido_id]).get(pedido_id)
    return _monta_item(row, marcacao, comentarios, adiamento)


@router.get("/{pedido_id}/comentarios")
def listar_comentarios(
    pedido_id: str,
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return {"comentarios": _query_comentarios(cur, [pedido_id]).get(pedido_id, [])}


@router.post("/{pedido_id}/comentarios")
async def adicionar_comentario(
    pedido_id: str,
    texto: str = Form(""),
    anexos: List[UploadFile] = File([]),
    current_user: dict = Depends(get_current_user),
):
    texto_limpo = (texto or "").strip()
    anexos_validos = [a for a in (anexos or []) if a and a.filename]
    if not texto_limpo and not anexos_validos:
        raise HTTPException(400, "Informe um texto ou ao menos um anexo.")
    if len(texto_limpo) > 2000:
        raise HTTPException(400, "Texto muito longo (máx 2000 caracteres).")

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            raise HTTPException(503, "Tabela de montagem ainda não disponível.")
        row = _buscar_view_um(cur, pedido_id)
        if not row:
            raise HTTPException(404, "Pedido não encontrado.")
        _inserir_comentario(
            cur,
            pedido_id,
            texto_limpo or "(anexo)",
            current_user,
            anexos=anexos_validos,
        )
        retorno = _montar_retorno_item(cur, pedido_id)

    # Notifica WhatsApp os demais responsáveis (exceto o próprio autor).
    try:
        from app.utils.montagem_whatsapp import notificar_comentario

        texto_wa = texto_limpo if texto_limpo else "📎 Anexo"
        if anexos_validos and texto_limpo:
            texto_wa = f"{texto_limpo}\n📎 {len(anexos_validos)} anexo(s)"
        variaveis = {
            "numero_pedido": row.get("identificador_pedido") or str(row.get("pedido_id") or ""),
            "cliente_nome": row.get("cliente_nome") or "—",
            "filial_venda": row.get("filial_venda") or "—",
            "comentador_nome": _autor_nome(current_user) or "—",
            "texto": (texto_wa or "")[:500],
        }
        notificar_comentario(
            pedido_id=pedido_id,
            comentador_user_id=current_user.get("id"),
            variaveis=variaveis,
        )
    except Exception as e:
        import logging as _lg
        _lg.getLogger(__name__).error(f"Erro WhatsApp comentário montagem: {e}")

    return retorno


@router.post("/{pedido_id}/lembrete")
def criar_lembrete_pedido(
    pedido_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Cria lembrete WhatsApp agendado para o usuário autenticado.
    data.tipo: '1h' | '2h' | '6h' | 'amanha'
    """
    tipo = (data or {}).get("tipo", "1h")
    kwargs: dict = {}
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

    # Valida pedido
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _buscar_view_um(cur, pedido_id):
            raise HTTPException(404, "Pedido não encontrado.")

    from app.utils.montagem_whatsapp import criar_lembrete as _criar_lembrete

    return _criar_lembrete(pedido_id=pedido_id, usuario_id=current_user["id"], **kwargs)


@router.get("/{pedido_id}/lembretes")
def listar_lembretes_pedido(
    pedido_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Lista lembretes pendentes do usuário para este pedido."""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT id, pedido_id, agendar_para, enviado, criado_em
            FROM montagem_lembretes
            WHERE pedido_id = %s AND usuario_id = %s AND enviado = FALSE
            ORDER BY agendar_para ASC
            """,
            (pedido_id, current_user["id"]),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["agendar_para"] = r["agendar_para"].isoformat() if r.get("agendar_para") else None
            r["criado_em"] = r["criado_em"].isoformat() if r.get("criado_em") else None
        return rows


@router.post("/{pedido_id}/adiar")
def adiar_montagem(
    pedido_id: str,
    body: AdiarRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.motivo not in MOTIVOS_ADIAMENTO:
        raise HTTPException(400, f"Motivo inválido. Use: {sorted(MOTIVOS_ADIAMENTO)}")

    # Parse nova_data se informada
    nova_data_dt: Optional[datetime] = None
    if body.nova_data:
        try:
            nova_data_dt = datetime.fromisoformat(body.nova_data.replace("Z", "+00:00"))
            # descarta tz para TIMESTAMP sem tz
            if nova_data_dt.tzinfo is not None:
                nova_data_dt = nova_data_dt.replace(tzinfo=None)
        except ValueError:
            raise HTTPException(400, "nova_data deve ser ISO 8601.")

    if body.motivo == "cliente_outra_data" and nova_data_dt is None:
        raise HTTPException(400, "Informe nova_data para o motivo cliente_outra_data.")

    # Retorno automático
    retorno_em: Optional[datetime]
    motivo_descricao: str
    if body.motivo == "telefone_invalido":
        retorno_em = datetime.utcnow() + timedelta(days=7)
        motivo_descricao = "Telefone do cliente incorreto ou não atende"
    else:
        retorno_em = nova_data_dt
        motivo_descricao = "Cliente deseja montagem em outro momento"

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if not _tabela_existe(cur):
            raise HTTPException(503, "Tabela de montagem ainda não disponível.")
        row = _buscar_view_um(cur, pedido_id)
        if not row:
            raise HTTPException(404, "Pedido não encontrado.")

        # Desativa adiamento anterior (se houver)
        cur.execute(
            "UPDATE montagem_adiamentos SET ativo = FALSE WHERE pedido_id = %s AND ativo",
            (pedido_id,),
        )
        # Cria novo
        cur.execute(
            """
            INSERT INTO montagem_adiamentos
                (pedido_id, motivo, motivo_descricao, nova_data, retorno_em,
                 confirmou_vitrine, observacao,
                 criado_por_user_id, criado_por_nome)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                pedido_id,
                body.motivo,
                motivo_descricao,
                nova_data_dt,
                retorno_em,
                bool(body.confirmou_vitrine),
                body.observacao,
                current_user.get("id"),
                _autor_nome(current_user),
            ),
        )

        # Registra comentário do adiamento
        partes: List[str] = [f"[Adiamento] {motivo_descricao}"]
        if body.motivo == "cliente_outra_data" and nova_data_dt:
            partes.append(
                f"Remarcado para {nova_data_dt.strftime('%d/%m %H:%M')}"
            )
        if body.motivo == "telefone_invalido":
            partes.append("Retorna automaticamente em 7 dias.")
        if body.observacao:
            partes.append(body.observacao.strip())
        texto = " — ".join(partes)
        tipo = (
            "adiamento_cliente_outra_data"
            if body.motivo == "cliente_outra_data"
            else "adiamento_telefone_invalido"
        )
        _inserir_comentario(cur, pedido_id, texto, current_user, tipo=tipo, nova_data=nova_data_dt)

        return _montar_retorno_item(cur, pedido_id)


@router.post("/{pedido_id}/retomar")
def retomar_montagem(
    pedido_id: str,
    body: Optional[ComentarioRequest] = None,
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "UPDATE montagem_adiamentos SET ativo = FALSE WHERE pedido_id = %s AND ativo RETURNING id",
            (pedido_id,),
        )
        desativou = cur.fetchone()
        if not desativou:
            raise HTTPException(404, "Nenhum adiamento ativo para este pedido.")
        texto = (body.texto.strip() if body and body.texto else None) or "[Retomada] Pedido retornou para a fila de montagem."
        _inserir_comentario(cur, pedido_id, texto, current_user, tipo="retomada")
        return _montar_retorno_item(cur, pedido_id)
