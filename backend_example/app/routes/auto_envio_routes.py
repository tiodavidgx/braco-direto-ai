"""
Rotas de Envio Automático
Endpoints para o painel de envio automático e execução manual
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, List, Tuple
from datetime import date, datetime, timedelta
import psycopg2.extras
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user

router = APIRouter()


def gerar_ciclos(dias_envio: List[int], hoje: date) -> List[Tuple[date, date, bool]]:
    """
    Gera todos os períodos entre dias de envio consecutivos.
    Retorna lista de (data_inicio, data_fim, is_atual).
    
    Ex: dias_envio=[16, 26], hoje=01/06 → ciclos:
      [27/04→16/05, False], [17/05→26/05, False], [27/05→16/06, True]
    """
    if not dias_envio:
        dias_envio = [25]
    
    dias = sorted(dias_envio)
    ciclos = []
    
    # Começar ~3 meses atrás
    cursor = date(hoje.year, hoje.month, 1) - timedelta(days=90)
    
    # Ajustar cursor para depois do último dia de envio do mês anterior
    # Encontrar o primeiro ciclo que comece antes ou durante o período de interesse
    
    while cursor <= hoje + timedelta(days=45):
        # Encontrar próximo dia de envio a partir do cursor
        proximo = None
        for d in dias:
            try:
                candidate = date(cursor.year, cursor.month, min(d, 28))
                if candidate >= cursor:
                    if proximo is None or candidate < proximo:
                        proximo = candidate
            except ValueError:
                pass
        
        if proximo is None:
            # Avançar para dia 1 do próximo mês
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
            continue
        
        is_atual = cursor <= hoje <= proximo
        ciclos.append((cursor, proximo, is_atual))
        cursor = proximo + timedelta(days=1)
    
    return ciclos


@router.get("/montadores/resumo")
def resumo_envio_automatico(
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna cards por ciclo de envio para cada montador.
    Um card = um período entre dias de envio consecutivos.
    """
    hoje = date.today()
    dia_hoje = hoje.day
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                m.id, m.nome, m.identificador,
                m.dias_envio_mes, m.prazo_pagamento_dias,
                m.email_responsavel_nm, m.percentual_montagem,
                m.percentual_assistencia, m.percentual_desmontagem,
                m.tipo_pagamento, m.terceirizada_id,
                m.pre_aprovado_em,
                t.nome as terceirizada_nome
            FROM montadores m
            LEFT JOIN terceirizadas t ON t.id = m.terceirizada_id
            WHERE m.envio_automatico = TRUE AND m.ativo = TRUE
            ORDER BY m.nome
        """)
        
        montadores = cur.fetchall()
        resultado = []
        
        for m in montadores:
            dias_envio = m.get('dias_envio_mes') or []
            ciclos = gerar_ciclos(dias_envio, hoje)
            
            for data_inicio, data_fim, is_atual in ciclos:
                # Contar boletins pendentes neste ciclo
                cur.execute("""
                    SELECT 
                        COUNT(*) as qtd_pendentes,
                        COALESCE(SUM(valor_venda), 0) as total_venda,
                        COALESCE(SUM(comissao_calculada), 0) as total_comissao
                    FROM boletins_montagem_envios
                    WHERE identificador_montador = %s
                      AND status = 'pendente'
                      AND data_montagem >= %s
                      AND data_montagem <= %s
                """, (m['identificador'], data_inicio, data_fim))
                
                stats = cur.fetchone()
                qtd = stats['qtd_pendentes'] or 0
                
                # Só mostra ciclos com boletins pendentes
                if qtd == 0:
                    continue
                
                # Badge: Aprovado vs Aguardando aprovação
                pre_aprovado = m.get('pre_aprovado_em')
                if pre_aprovado:
                    badge = "aprovado"
                    badge_label = "Aprovado"
                else:
                    badge = "aguardando"
                    badge_label = "Aguardando aprovação"
                
                resultado.append({
                    "id": m['id'],
                    "nome": m['nome'],
                    "identificador": m['identificador'],
                    "dias_envio": dias_envio,
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
    data_inicio_param: Optional[str] = None,
    data_fim_param: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Retorna boletins detalhados de um montador. Aceita período opcional."""
    hoje = date.today()
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM montadores WHERE id = %s", (montador_id,))
        montador = cur.fetchone()
        if not montador:
            raise HTTPException(status_code=404, detail="Montador não encontrado")
        
        # Período: parâmetros ou tudo pendente até hoje
        if data_inicio_param:
            data_inicio = date.fromisoformat(data_inicio_param)
        else:
            data_inicio = date(2020, 1, 1)
        
        if data_fim_param:
            data_fim = date.fromisoformat(data_fim_param)
        else:
            data_fim = hoje
        
        cur.execute("""
            SELECT * FROM boletins_montagem_envios
            WHERE identificador_montador = %s
              AND data_montagem >= %s
              AND data_montagem <= %s
              AND status = 'pendente'
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
            "DELETE FROM boletins_montagem_envios WHERE id = %s AND status = 'pendente'",
            (boletim_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Boletim não encontrado ou já processado")
        conn.commit()
        return {"message": "Boletim removido com sucesso"}


@router.post("/montadores/{montador_id}/forcar-envio")
def forcar_envio_montador(
    montador_id: int,
    ate_data: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Força o envio para um montador. Se ate_data informado, mescla ciclos vencidos."""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    from app.services.auto_envio import processar_envios_automaticos_montadores
    
    ate = None
    if ate_data:
        try:
            ate = date.fromisoformat(ate_data)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    else:
        # Sempre força com ate_data=hoje para ignorar a restrição de dia de envio
        ate = date.today()
    
    # Executa síncrono para garantir que o envio aconteça
    resultado = processar_envios_automaticos_montadores(dry_run=False, montador_id=montador_id, ate_data=ate)
    
    return {
        "message": "Envio concluído",
        "montador_id": montador_id,
        "resultado": resultado,
    }


@router.post("/montadores/{montador_id}/pre-aprovar")
def pre_aprovar_envio(
    montador_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Marca o ciclo atual como pré-aprovado. No dia do envio, dispara automático."""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE montadores SET pre_aprovado_em = NOW() WHERE id = %s",
            (montador_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Montador não encontrado")
        conn.commit()
        return {"message": "Pré-aprovado! O envio será automático no dia configurado."}


@router.delete("/montadores/{montador_id}/pre-aprovar")
def cancelar_pre_aprovacao(
    montador_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Cancela a pré-aprovação do ciclo atual."""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Apenas administradores")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE montadores SET pre_aprovado_em = NULL WHERE id = %s",
            (montador_id,)
        )
        conn.commit()
        return {"message": "Pré-aprovação cancelada."}


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
            FROM boletins_montagem_envios ib
            WHERE ib.status = 'processado'
            GROUP BY ib.lote_envio_id, ib.identificador_montador, ib.nome_montador
            ORDER BY MAX(ib.updated_at) DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        return cur.fetchall()
