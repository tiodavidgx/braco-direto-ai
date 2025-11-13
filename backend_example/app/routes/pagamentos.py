"""
Rotas de Pagamentos Pendentes
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import get_db_connection

router = APIRouter(tags=["pagamentos"])

def calcular_dias_para_vencimento(data_vencimento):
    """Calcula dias até vencimento"""
    if not data_vencimento:
        return None
    
    hoje = datetime.now().date()
    if isinstance(data_vencimento, str):
        data_vencimento = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
    elif isinstance(data_vencimento, datetime):
        data_vencimento = data_vencimento.date()
    
    return (data_vencimento - hoje).days

@router.get("/pendentes")
def get_todos_pagamentos_pendentes():
    """Retorna todos os pagamentos pendentes (serviços e montagens)"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Buscar lotes de serviço pendentes
            cur.execute("""
                SELECT 
                    ls.id,
                    ls.prestador_id,
                    p.nome as prestador_nome,
                    p.fornecedor_id as prestador_fornecedor_id,
                    ls.periodo,
                    ls.valor_total,
                    ls.data_vencimento_pagamento,
                    ls.data_recebimento_nf,
                    ls.data_pagamento
                FROM lotes_servico ls
                JOIN prestadores p ON ls.prestador_id = p.id
                WHERE ls.data_pagamento IS NULL
                ORDER BY ls.data_vencimento_pagamento ASC NULLS LAST
            """)
            
            servicos = []
            for row in cur.fetchall():
                dias = calcular_dias_para_vencimento(row[6])
                servicos.append({
                    'id': row[0],
                    'prestador_id': row[1],
                    'prestador_nome': row[2],
                    'prestador_fornecedor_id': row[3],
                    'periodo': row[4],
                    'valor_total': float(row[5]) if row[5] else None,
                    'data_vencimento_pagamento': row[6].isoformat() if row[6] else None,
                    'data_recebimento_nf': row[7].isoformat() if row[7] else None,
                    'data_pagamento': row[8].isoformat() if row[8] else None,
                    'dias_para_vencimento': dias
                })
            
            # Buscar montagens pendentes
            cur.execute("""
                SELECT 
                    em.id,
                    em.montador_id,
                    m.nome as montador_nome,
                    m.fornecedor_id as montador_fornecedor_id,
                    em.periodo,
                    em.valor_total,
                    em.data_vencimento_pagamento,
                    em.data_recebimento_nf,
                    em.data_pagamento,
                    em.detalhes
                FROM envios_montagem em
                JOIN montadores m ON em.montador_id = m.id
                WHERE em.data_pagamento IS NULL
                ORDER BY em.data_vencimento_pagamento ASC NULLS LAST
            """)
            
            montagens = []
            for row in cur.fetchall():
                dias = calcular_dias_para_vencimento(row[6])
                montagens.append({
                    'id': row[0],
                    'montador_id': row[1],
                    'montador_nome': row[2],
                    'montador_fornecedor_id': row[3],
                    'periodo': row[4],
                    'valor_total': float(row[5]) if row[5] else None,
                    'data_vencimento_pagamento': row[6].isoformat() if row[6] else None,
                    'data_recebimento_nf': row[7].isoformat() if row[7] else None,
                    'data_pagamento': row[8].isoformat() if row[8] else None,
                    'detalhes': row[9],
                    'dias_para_vencimento': dias
                })
            
            return {
                'servicos': servicos,
                'montagens': montagens
            }

@router.post("/marcar-todos-nao-pendentes-pagos")
def marcar_todos_nao_pendentes_como_pagos():
    """Marca todos os lotes e montagens com NF recebida como pagos"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            data_hoje = datetime.now().date()
            
            # Marcar lotes com NF como pagos
            cur.execute("""
                UPDATE lotes_servico 
                SET data_pagamento = %s
                WHERE data_recebimento_nf IS NOT NULL 
                AND data_pagamento IS NULL
            """, (data_hoje,))
            lotes_atualizados = cur.rowcount
            
            # Marcar montagens com NF como pagos
            cur.execute("""
                UPDATE envios_montagem 
                SET data_pagamento = %s
                WHERE data_recebimento_nf IS NOT NULL 
                AND data_pagamento IS NULL
            """, (data_hoje,))
            montagens_atualizadas = cur.rowcount
            
            conn.commit()
            
            total = lotes_atualizados + montagens_atualizadas
            return {
                'total': total,
                'lotes': lotes_atualizados,
                'montagens': montagens_atualizadas
            }

@router.post("/desmarcar-todos-pagos")
def desmarcar_todos_como_pagos():
    """Remove a marcação de pagamento de todos os lotes e montagens"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Desmarcar lotes
            cur.execute("""
                UPDATE lotes_servico 
                SET data_pagamento = NULL
                WHERE data_pagamento IS NOT NULL
            """)
            lotes_atualizados = cur.rowcount
            
            # Desmarcar montagens
            cur.execute("""
                UPDATE envios_montagem 
                SET data_pagamento = NULL
                WHERE data_pagamento IS NOT NULL
            """)
            montagens_atualizadas = cur.rowcount
            
            conn.commit()
            
            total = lotes_atualizados + montagens_atualizadas
            return {
                'total': total,
                'lotes': lotes_atualizados,
                'montagens': montagens_atualizadas
            }

@router.post("/lote/{id}/marcar-pago")
def marcar_lote_como_pago(id: int):
    """Marca um lote específico como pago"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            data_hoje = datetime.now().date()
            
            cur.execute("""
                UPDATE lotes_servico 
                SET data_pagamento = %s
                WHERE id = %s
            """, (data_hoje, id))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Lote não encontrado")
            
            conn.commit()
            
            return {'message': 'Lote marcado como pago com sucesso'}

@router.post("/montagem/{id}/marcar-pago")
def marcar_montagem_como_paga(id: int):
    """Marca uma montagem específica como paga"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            data_hoje = datetime.now().date()
            
            cur.execute("""
                UPDATE envios_montagem 
                SET data_pagamento = %s
                WHERE id = %s
            """, (data_hoje, id))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Montagem não encontrada")
            
            conn.commit()
            
            return {'message': 'Montagem marcada como paga com sucesso'}
