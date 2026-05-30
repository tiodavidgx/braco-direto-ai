"""
Rotas de Envio Automático
Endpoints para o painel de envio automático e execução manual
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, List, Tuple
from datetime import date, datetime
import psycopg2.extras
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user

router = APIRouter()


def calcular_periodo_ciclo(dias_envio: List[int], hoje: date) -> Tuple[date, date]:
    """
    Calcula o período do ciclo: envia tudo pendente até hoje.
    Não importa a data do boletim — se está pendente, vai.
    A data de corte é sempre HOJE.
    
    Ex: dias_envio=[16, 26], hoje=16/05 → ciclo: 01/01/2020 a 16/05
        (envia tudo pendente até dia 16)
    Ex: dias_envio=[16, 26], hoje=26/05 → ciclo: 01/01/2020 a 26/05
        (envia tudo pendente até dia 26)
    """
    # Data de início: bem antiga para pegar tudo pendente
    data_inicio = date(2020, 1, 1)
    # Data fim: hoje (data de corte)
    data_fim = hoje
    
    return data_inicio, data_fim


@router.get("/montadores/resumo")
def resumo_envio_automatico(
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna resumo de todos os montadores com envio automático ativo.
    Usado pelo painel /envio-automatico-montadores (cards).
    """
    hoje = date.today()
    dia_hoje = hoje.day
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                m.id, m.nome, m.identificador,
                m.dias_envio_mes, m.dia_fechamento, m.prazo_pagamento_dias,
                m.email_responsavel_nm, m.percentual_montagem,
                m.percentual_assistencia, m.percentual_desmontagem,
                m.tipo_pagamento, m.terceirizada_id,
                t.nome as terceirizada_nome
            FROM montadores m
            LEFT JOIN terceirizadas t ON t.id = m.terceirizada_id
            WHERE m.envio_automatico = TRUE AND m.ativo = TRUE
            ORDER BY m.nome
        """)
        
        montadores = cur.fetchall()
        resultado = []
        
        for m in montadores:
            # Calcular próximo dia de envio
            dias_envio = m.get('dias_envio_mes') or []
            proximos_dias = [d for d in dias_envio if d >= dia_hoje]
            if not proximos_dias and dias_envio:
                proximos_dias = dias_envio  # Mostrar dias do próximo mês
            
            # Calcular período do ciclo atual
            data_inicio, data_fim = calcular_periodo_ciclo(dias_envio, hoje)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as qtd_pendentes,
                    COALESCE(SUM(valor_venda), 0) as total_venda,
                    COALESCE(SUM(comissao_calculada), 0) as total_comissao
                FROM ingestao_boletins_montador
                WHERE identificador_montador = %s
                  AND status = 'pendente'
                  AND data_montagem >= %s
                  AND data_montagem <= %s
            """, (m['identificador'], data_inicio, data_fim))
            
            stats = cur.fetchone()
            
            # Determinar badge
            qtd = stats['qtd_pendentes'] or 0
            if qtd == 0:
                badge = "sem_boletins"
                badge_label = "Sem boletins"
            elif dia_hoje in dias_envio:
                badge = "pronto"
                badge_label = "Pronto para envio"
            else:
                badge = "aguardando"
                badge_label = f"Aguardando dia {proximos_dias[0] if proximos_dias else '?'}"
            
            resultado.append({
                "id": m['id'],
                "nome": m['nome'],
                "identificador": m['identificador'],
                "dias_envio": dias_envio,
                "proximos_dias": proximos_dias[:3],
                "prazo_pagamento_dias": m.get('prazo_pagamento_dias', 10),
                "email_responsavel_nm": m.get('email_responsavel_nm'),
                "tipo_pagamento": m.get('tipo_pagamento', 'novo_mundo'),
                "terceirizada_id": m.get('terceirizada_id'),
                "terceirizada_nome": m.get('terceirizada_nome'),
                "qtd_pendentes": qtd,
                "total_venda": float(stats['total_venda'] or 0),
                "total_comissao": float(stats['total_comissao'] or 0),
                "periodo_inicio": data_inicio.isoformat(),
                "periodo_fim": data_fim.isoformat(),
                "badge": badge,
                "badge_label": badge_label,
            })
        
        return resultado


@router.get("/montadores/{montador_id}/boletins")
def boletins_montador(
    montador_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Retorna boletins pendentes detalhados de um montador específico"""
    hoje = date.today()
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar montador
        cur.execute(
            "SELECT * FROM montadores WHERE id = %s",
            (montador_id,)
        )
        montador = cur.fetchone()
        if not montador:
            raise HTTPException(status_code=404, detail="Montador não encontrado")
        
        dias_envio = montador.get('dias_envio_mes') or []
        data_inicio, data_fim = calcular_periodo_ciclo(dias_envio, hoje)
        
        cur.execute("""
            SELECT * FROM ingestao_boletins_montador
            WHERE identificador_montador = %s
              AND data_montagem >= %s
              AND data_montagem <= %s
            ORDER BY data_montagem DESC, boletim
        """, (montador['identificador'], data_inicio, data_fim))
        
        boletins = cur.fetchall()
        
        # Buscar custos extras vinculados a este montador
        cur.execute("""
            SELECT id, identificador_boletim, valor, motivo, status, created_at
            FROM custos_extras
            WHERE identificador_montador = %s AND status = 'pendente'
        """, (montador['identificador'],))
        custos_extras = cur.fetchall()
        
        # Converter boletins para dict e enriquecer com custos extras
        boletins_list = []
        for b in boletins:
            bd = dict(b)
            bd['valor_extra'] = float(bd.get('valor_extra', 0) or 0)
            boletins_list.append(bd)
        
        # Adicionar custos extras como entradas separadas (A-*)
        for ce in custos_extras:
            # Verificar se já existe entrada para este boletim de ajuste
            existe = any(b.get('boletim') == ce['identificador_boletim'] for b in boletins_list)
            if not existe:
                boletins_list.append({
                    "id": -ce['id'],  # Negativo para distinguir
                    "identificador_montador": montador['identificador'],
                    "boletim": ce['identificador_boletim'],
                    "data_montagem": ce['created_at'].strftime('%Y-%m-%d') if ce['created_at'] else hoje.isoformat(),
                    "nome_cliente": "-",
                    "nome_produto": ce['motivo'] or "Ajuste",
                    "tipo_servico": "MONTAGEM",
                    "valor_venda": 0,
                    "valor_extra": float(ce['valor']),
                    "comissao_calculada": 0,
                    "motivo_valor_extra": ce['motivo'],
                    "status": "pendente",
                    "lote_envio_id": None,
                    "is_ajuste": True,
                })
            else:
                # Se já existe, somar o valor ao adicional do boletim
                for b in boletins_list:
                    if b.get('boletim') == ce['identificador_boletim']:
                        b['valor_extra'] = float(b.get('valor_extra', 0) or 0) + float(ce['valor'])
                        if ce['motivo']:
                            motivo_atual = b.get('motivo_valor_extra', '') or ''
                            b['motivo_valor_extra'] = f"{motivo_atual}; {ce['motivo']}".strip('; ')
        
        return {
            "montador": dict(montador),
            "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
            "boletins": boletins_list,
            "total_venda": sum(float(b['valor_venda'] or 0) for b in boletins_list),
            "total_comissao": sum(float(b['comissao_calculada'] or 0) for b in boletins_list),
        }


@router.delete("/montadores/boletins/{boletim_id}")
def remover_boletim(
    boletim_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Remove um boletim da fila de envio"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM ingestao_boletins_montador WHERE id = %s AND status = 'pendente'",
            (boletim_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Boletim não encontrado ou já processado")
        conn.commit()
        return {"message": "Boletim removido com sucesso"}


@router.post("/montadores/{montador_id}/forcar-envio")
def forcar_envio_montador(
    montador_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Força o envio imediato para um montador específico"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    from app.services.auto_envio import processar_envios_automaticos_montadores
    
    # Executar em background
    background_tasks.add_task(processar_envios_automaticos_montadores, dry_run=False)
    
    return {
        "message": "Envio iniciado em background",
        "montador_id": montador_id,
    }


@router.get("/montadores/historico")
def historico_envios_automaticos(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Histórico de envios automáticos realizados"""
    offset = (page - 1) * limit
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                ib.lote_envio_id,
                ib.identificador_montador,
                ib.nome_montador,
                COUNT(*) as qtd_boletins,
                SUM(ib.valor_venda) as total_venda,
                SUM(ib.comissao_calculada) as total_comissao,
                MAX(ib.updated_at) as data_envio
            FROM ingestao_boletins_montador ib
            WHERE ib.status = 'processado'
            GROUP BY ib.lote_envio_id, ib.identificador_montador, ib.nome_montador
            ORDER BY MAX(ib.updated_at) DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        return cur.fetchall()
