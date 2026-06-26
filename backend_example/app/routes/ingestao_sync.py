"""
Sync / Reconciliação de Boletins de Montagem para Envios Automáticos
Recebe a lista completa de boletins ativos e reconcilia com o banco.
Endpoint exclusivo para a tabela boletins_montagem_envios.
"""

import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, model_validator
import psycopg2.extras
from app.database import get_db_connection

router = APIRouter()


# ── Auth ──────────────────────────────────────────────

def verificar_api_key(api_key: str):
    """Valida X-Bot-Key contra bot_config"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM bot_config WHERE api_key = %s AND ativo = TRUE",
            (api_key,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=401, detail="API key inválida ou inativa")


# ── Helpers ───────────────────────────────────────────

def parse_date(value):
    """Converte string/Excel serial para date. Retorna None se inválido."""
    if value is None or value == '' or value == 'None':
        return None
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    s = str(value).strip()
    if not s:
        return None
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y']:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        excel_epoch = datetime(1899, 12, 30)
        return (excel_epoch + timedelta(days=float(s))).date()
    except (ValueError, TypeError):
        pass
    return None


# ── Model ─────────────────────────────────────────────

class BoletimSyncEntry(BaseModel):
    """13 colunas do Excel de montagem — aceita variantes de nomes de campo"""
    nome_do_montador: Optional[str] = None
    identificador_do_montador: str
    identificador_boletim_montagem: str
    filial_saida: Optional[str] = None
    nota_fiscal: Optional[str] = None
    serie_nota_fiscal: Optional[str] = None
    nome_do_cliente: Optional[str] = None
    data_da_previsao_montagem: Optional[str] = None
    data_da_montagem: Optional[str] = None
    produto: Optional[str] = None
    nome_produto: Optional[str] = None
    media_de_valor_venda: Optional[float] = 0.0
    tipo_servico: Optional[str] = "MONTAGEM"

    @model_validator(mode='before')
    @classmethod
    def normalizar_chaves(cls, data: dict) -> dict:
        """Aceita nomes alternativos de campos comuns do outro sistema."""
        if not isinstance(data, dict):
            return data
        # valor_venda → media_de_valor_venda
        if 'valor_venda' in data and 'media_de_valor_venda' not in data:
            data['media_de_valor_venda'] = data['valor_venda']
        # data_montagem → data_da_montagem
        if 'data_montagem' in data and 'data_da_montagem' not in data:
            data['data_da_montagem'] = data['data_montagem']
        # nome_cliente → nome_do_cliente
        if 'nome_cliente' in data and 'nome_do_cliente' not in data:
            data['nome_do_cliente'] = data['nome_cliente']
        # nome_montador → nome_do_montador
        if 'nome_montador' in data and 'nome_do_montador' not in data:
            data['nome_do_montador'] = data['nome_montador']
        # boletim → identificador_boletim_montagem
        if 'boletim' in data and 'identificador_boletim_montagem' not in data:
            data['identificador_boletim_montagem'] = data['boletim']
        # previsao_montagem → data_da_previsao_montagem
        if 'previsao_montagem' in data and 'data_da_previsao_montagem' not in data:
            data['data_da_previsao_montagem'] = data['previsao_montagem']
        return data


# ── Endpoint ──────────────────────────────────────────

@router.post("/montadores/sync")
def sync_boletins_montadores(
    dados: List[BoletimSyncEntry],
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
):
    """
    Recebe a lista COMPLETA de boletins ativos e reconcilia com o banco.
    
    - Insere novos boletins
    - Atualiza boletins existentes (ainda pendentes)
    - Remove pendentes que não estão mais no payload (cancelados)
    - Reassigna boletins que mudaram de montador
    - NUNCA altera boletins já processados ou bloqueados
    """
    verificar_api_key(x_bot_key)

    resultado = {
        "status": "ok",
        "total_recebido": len(dados),
        "inseridos": 0,
        "atualizados": 0,
        "removidos": 0,
        "reassignments": 0,
        "ignorados_processados": 0,
        "ignorados_nao_cadastrados": 0,
        "ignorados_blacklist": 0,
        "erros": 0,
        "detalhes_erros": [],
        "por_montador": [],
    }

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # ── Agrupar payload por identificador do montador ──
        recebidos_por_montador: Dict[str, Dict[str, dict]] = {}
        for item in dados:
            identificador = str(item.identificador_do_montador).strip()
            boletim = str(item.identificador_boletim_montagem).strip()
            if not identificador or not boletim:
                resultado["erros"] += 1
                resultado["detalhes_erros"].append({
                    "erro": "identificador ou boletim vazio",
                    "item": item.dict(),
                })
                continue
            if identificador not in recebidos_por_montador:
                recebidos_por_montador[identificador] = {}
            recebidos_por_montador[identificador][boletim] = item.dict()

        # ── Processar cada montador ──
        for identificador, boletins_recebidos in recebidos_por_montador.items():
            mr = {
                "identificador": identificador,
                "nome": "",
                "inseridos": 0,
                "atualizados": 0,
                "removidos": 0,
                "reassignments": 0,
            }

            try:
                # Buscar montador para percentuais e nome
                cur.execute(
                    """SELECT id, nome, percentual_montagem, percentual_assistencia,
                              percentual_desmontagem
                       FROM montadores WHERE identificador = %s""",
                    (identificador,)
                )
                montador = cur.fetchone()

                # Pular montadores não cadastrados na base
                if not montador:
                    resultado["ignorados_nao_cadastrados"] += len(boletins_recebidos)
                    continue

                pcts = {
                    "montagem": float(montador['percentual_montagem']),
                    "assistencia": float(montador['percentual_assistencia']),
                    "desmontagem": float(montador['percentual_desmontagem']),
                }
                nome_default = montador['nome']
                mr["nome"] = nome_default

                # ── Pré-carregar blacklist e processados (performance) ──
                cur.execute("SELECT boletim FROM boletins_blacklist")
                blacklist = {r['boletim'] for r in cur.fetchall()}

                cur.execute(
                    """SELECT boletim FROM boletins_montagem_envios
                       WHERE identificador_montador = %s AND status = 'processado'""",
                    (identificador,)
                )
                processados = {r['boletim'] for r in cur.fetchall()}

                # ── Remover pendentes que não estão no payload ──
                cur.execute(
                    """SELECT boletim FROM boletins_montagem_envios
                       WHERE identificador_montador = %s AND status = 'pendente'""",
                    (identificador,)
                )
                pendentes_db = {r['boletim'] for r in cur.fetchall()}
                a_remover = pendentes_db - set(boletins_recebidos.keys())

                if a_remover:
                    ph = ','.join(['%s'] * len(a_remover))
                    cur.execute(
                        f"""DELETE FROM boletins_montagem_envios
                             WHERE identificador_montador = %s
                               AND boletim IN ({ph})
                               AND status = 'pendente'""",
                        [identificador] + list(a_remover)
                    )
                    mr["removidos"] = cur.rowcount
                    resultado["removidos"] += mr["removidos"]

                # ── UPSERT cada boletim do payload (bulk) ──
                rows_to_upsert = []  # coleta para bulk insert
                for boletim, item in boletins_recebidos.items():
                    try:
                        # Pular boletins na blacklist
                        if boletim in blacklist:
                            resultado["ignorados_blacklist"] += 1
                            continue

                        # Pular boletins já processados
                        if boletim in processados:
                            resultado["ignorados_processados"] += 1
                            continue

                        # Verificar reassignment (boletim em outro montador)
                        cur.execute(
                            """SELECT identificador_montador, status
                               FROM boletins_montagem_envios
                               WHERE boletim = %s LIMIT 1""",
                            (boletim,)
                        )
                        existente = cur.fetchone()

                        if existente and existente['identificador_montador'] != identificador:
                            if existente['status'] == 'pendente':
                                cur.execute(
                                    """UPDATE boletins_montagem_envios
                                       SET identificador_montador = %s, nome_montador = %s,
                                           updated_at = NOW()
                                       WHERE boletim = %s AND status = 'pendente'""",
                                    (identificador, item.get('nome_do_montador') or nome_default, boletim)
                                )
                                if cur.rowcount > 0:
                                    mr["reassignments"] += 1
                                    resultado["reassignments"] += 1
                                # Reassign feito, agora faz UPSERT normalmente
                            else:
                                resultado["ignorados_processados"] += 1
                                continue

                        # Calcular comissão
                        valor = float(item.get('media_de_valor_venda') or 0)
                        tipo_raw = (item.get('tipo_servico') or 'MONTAGEM').upper()
                        if 'ASSIST' in tipo_raw or 'TECNICA' in tipo_raw:
                            tipo_srv = 'ASSISTENCIA_TECNICA'
                            pct = pcts['assistencia']
                        elif 'DESMONT' in tipo_raw:
                            tipo_srv = 'DESMONTAGEM'
                            pct = pcts['desmontagem']
                        else:
                            tipo_srv = 'MONTAGEM'
                            pct = pcts['montagem']
                        comissao = round(valor * pct, 2)

                        rows_to_upsert.append((
                            identificador, item.get('nome_do_montador') or nome_default, boletim,
                            parse_date(item.get('data_da_montagem')),
                            parse_date(item.get('data_da_previsao_montagem')),
                            valor,
                            item.get('nome_do_cliente') or '',
                            item.get('nome_produto') or '',
                            tipo_srv, comissao,
                            item.get('filial_saida') or '',
                            item.get('nota_fiscal') or '',
                            item.get('serie_nota_fiscal') or '',
                        ))

                    except Exception as e:
                        resultado["erros"] += 1
                        resultado["detalhes_erros"].append({
                            "boletim": boletim,
                            "erro": str(e),
                        })

                # Bulk UPSERT — uma única query para todos os boletins
                if rows_to_upsert:
                    from psycopg2.extras import execute_values
                    execute_values(cur, """
                        INSERT INTO boletins_montagem_envios (
                            identificador_montador, nome_montador, boletim,
                            data_montagem, data_previsao_montagem,
                            valor_venda, nome_cliente, nome_produto,
                            tipo_servico, comissao_calculada,
                            filial_saida, nota_fiscal, serie_nota_fiscal
                        ) VALUES %s
                        ON CONFLICT (identificador_montador, boletim)
                        DO UPDATE SET
                            nome_montador = EXCLUDED.nome_montador,
                            data_montagem = EXCLUDED.data_montagem,
                            data_previsao_montagem = EXCLUDED.data_previsao_montagem,
                            valor_venda = EXCLUDED.valor_venda,
                            nome_cliente = EXCLUDED.nome_cliente,
                            nome_produto = EXCLUDED.nome_produto,
                            tipo_servico = EXCLUDED.tipo_servico,
                            comissao_calculada = EXCLUDED.comissao_calculada,
                            filial_saida = EXCLUDED.filial_saida,
                            nota_fiscal = EXCLUDED.nota_fiscal,
                            serie_nota_fiscal = EXCLUDED.serie_nota_fiscal,
                            updated_at = NOW()
                    """, rows_to_upsert)
                    # Estimar inseridos vs atualizados (bulk não distingue facilmente)
                    novos = len(rows_to_upsert)
                    mr["inseridos"] += novos
                    resultado["inseridos"] += novos

                conn.commit()
                resultado["por_montador"].append(mr)

            except Exception as e:
                conn.rollback()
                resultado["erros"] += 1
                resultado["detalhes_erros"].append({
                    "identificador": identificador,
                    "erro": str(e),
                })

    return resultado


# ── Model para adição manual ─────────────────────────

class BoletimAddEntry(BaseModel):
    identificador_do_montador: str
    nome_do_montador: Optional[str] = None
    identificador_boletim_montagem: str
    data_da_montagem: Optional[str] = None
    media_de_valor_venda: Optional[float] = 0.0
    nome_do_cliente: Optional[str] = None
    nome_produto: Optional[str] = None
    tipo_servico: Optional[str] = "MONTAGEM"
    adicional: Optional[float] = 0.0
    motivo_valor_extra: Optional[str] = None


# ── Endpoint de adição manual (usado pelo painel) ────

@router.post("/montadores/adicionar")
def adicionar_boletim(item: BoletimAddEntry):
    """
    Adiciona um boletim manualmente via painel de Envio Automático.
    Insere diretamente em boletins_montagem_envios.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        identificador = str(item.identificador_do_montador).strip()
        boletim = str(item.identificador_boletim_montagem).strip()

        if not identificador or not boletim:
            raise HTTPException(status_code=400, detail="identificador e boletim são obrigatórios")

        # Buscar percentuais do montador
        cur.execute(
            """SELECT nome, percentual_montagem, percentual_assistencia, percentual_desmontagem
               FROM montadores WHERE identificador = %s""",
            (identificador,)
        )
        montador = cur.fetchone()
        if not montador:
            raise HTTPException(status_code=404, detail="Montador não encontrado")

        pcts = {
            "montagem": float(montador['percentual_montagem']),
            "assistencia": float(montador['percentual_assistencia']),
            "desmontagem": float(montador['percentual_desmontagem']),
        }

        valor = float(item.media_de_valor_venda or 0)
        tipo_raw = (item.tipo_servico or 'MONTAGEM').upper()
        if 'ASSIST' in tipo_raw or 'TECNICA' in tipo_raw:
            tipo_srv = 'ASSISTENCIA_TECNICA'
            pct = pcts['assistencia']
        elif 'DESMONT' in tipo_raw:
            tipo_srv = 'DESMONTAGEM'
            pct = pcts['desmontagem']
        else:
            tipo_srv = 'MONTAGEM'
            pct = pcts['montagem']
        comissao = round(valor * pct, 2)

        cur.execute("""
            INSERT INTO boletins_montagem_envios (
                identificador_montador, nome_montador, boletim,
                data_montagem, valor_venda, nome_cliente, nome_produto,
                tipo_servico, comissao_calculada,
                valor_extra, motivo_valor_extra,
                status, updated_at
            ) VALUES (%s,%s,%s, %s,%s, %s,%s, %s,%s, %s,%s, 'pendente', NOW())
            ON CONFLICT (identificador_montador, boletim)
            DO UPDATE SET
                nome_montador = EXCLUDED.nome_montador,
                data_montagem = EXCLUDED.data_montagem,
                valor_venda = EXCLUDED.valor_venda,
                nome_cliente = EXCLUDED.nome_cliente,
                nome_produto = EXCLUDED.nome_produto,
                tipo_servico = EXCLUDED.tipo_servico,
                comissao_calculada = EXCLUDED.comissao_calculada,
                valor_extra = EXCLUDED.valor_extra,
                motivo_valor_extra = EXCLUDED.motivo_valor_extra,
                updated_at = NOW()
            RETURNING id, boletim
        """, (
            identificador, item.nome_do_montador or montador['nome'], boletim,
            parse_date(item.data_da_montagem) or date.today(),
            valor,
            item.nome_do_cliente or '',
            item.nome_produto or '',
            tipo_srv, comissao,
            float(item.adicional or 0),
            item.motivo_valor_extra or '',
        ))

        result = cur.fetchone()
        conn.commit()

        return {
            "status": "ok",
            "id": result['id'],
            "boletim": result['boletim'],
            "message": "Boletim adicionado com sucesso"
        }
