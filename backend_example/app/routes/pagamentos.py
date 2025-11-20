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
from app.utils.whatsapp_automation import enviar_notificacao_whatsapp

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
async def marcar_lote_como_pago(id: int):
    """Marca um lote específico como pago"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            data_hoje = datetime.now().date()
            
            # Buscar informações do lote antes de marcar como pago
            cur.execute("""
                SELECT 
                    ls.prestador_id,
                    ls.periodo,
                    ls.valor_total,
                    p.nome as prestador_nome,
                    p.telefone
                FROM lotes_servico ls
                JOIN prestadores p ON ls.prestador_id = p.id
                WHERE ls.id = %s
            """, (id,))
            
            lote_info = cur.fetchone()
            
            if not lote_info:
                raise HTTPException(status_code=404, detail="Lote não encontrado")
            
            prestador_id, periodo, valor_total, prestador_nome, telefone = lote_info
            
            # Marcar como pago
            cur.execute("""
                UPDATE lotes_servico 
                SET data_pagamento = %s
                WHERE id = %s
            """, (data_hoje, id))
            
            conn.commit()
            
            # Enviar notificação WhatsApp
            try:
                print(f"\n📱 Enviando notificação de pagamento realizado...")
                enviar_notificacao_whatsapp(
                    evento='pagamento_realizado_prestador',
                    destinatario_id=prestador_id,
                    tipo='prestador',
                    variaveis={
                        'nome_prestador': prestador_nome,
                        'periodo': periodo,
                        'valor': str(valor_total),
                        'data_pagamento': data_hoje.strftime('%d/%m/%Y')
                    }
                )
            except Exception as e:
                print(f"⚠️ Erro ao enviar WhatsApp: {str(e)}")
                # Não falha a operação se WhatsApp der erro
            
            # Enviar notificação WebSocket
            try:
                from app.routes.notifications import notification_manager
                await notification_manager.send_notification(
                    tipo="success",
                    titulo=f"💰 Pagamento Realizado - Lote #{id}",
                    mensagem=f"{prestador_nome} - Pagamento de R$ {valor_total:.2f} realizado",
                    dados={
                        "lote_id": id,
                        "tipo": "prestador",
                        "prestador": prestador_nome,
                        "periodo": periodo,
                        "valor": float(valor_total),
                        "data_pagamento": data_hoje.strftime('%d/%m/%Y')
                    }
                )
                print(f"   📡 Notificação WebSocket enviada")
            except Exception as e:
                print(f"⚠️ Erro ao enviar notificação WebSocket: {str(e)}")
            
            return {'message': 'Lote marcado como pago com sucesso'}

@router.post("/montagem/{id}/marcar-pago")
async def marcar_montagem_como_paga(id: int):
    """Marca uma montagem específica como paga"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            data_hoje = datetime.now().date()
            
            # Buscar informações da montagem antes de marcar como pago
            cur.execute("""
                SELECT 
                    em.montador_id,
                    em.periodo,
                    em.valor_total,
                    m.nome as montador_nome,
                    m.telefone
                FROM envios_montagem em
                JOIN montadores m ON em.montador_id = m.id
                WHERE em.id = %s
            """, (id,))
            
            montagem_info = cur.fetchone()
            
            if not montagem_info:
                raise HTTPException(status_code=404, detail="Montagem não encontrada")
            
            montador_id, periodo, valor_total, montador_nome, telefone = montagem_info
            
            # Marcar como pago
            cur.execute("""
                UPDATE envios_montagem 
                SET data_pagamento = %s
                WHERE id = %s
            """, (data_hoje, id))
            
            conn.commit()
            
            # Enviar notificação WhatsApp
            try:
                print(f"\n📱 Enviando notificação de pagamento realizado...")
                enviar_notificacao_whatsapp(
                    evento='pagamento_realizado_montador',
                    destinatario_id=montador_id,
                    tipo='montador',
                    variaveis={
                        'nome_montador': montador_nome,
                        'periodo': periodo,
                        'valor': str(valor_total),
                        'data_pagamento': data_hoje.strftime('%d/%m/%Y')
                    }
                )
            except Exception as e:
                print(f"⚠️ Erro ao enviar WhatsApp: {str(e)}")
                # Não falha a operação se WhatsApp der erro
            
            # Enviar notificação WebSocket
            try:
                from app.routes.notifications import notification_manager
                await notification_manager.send_notification(
                    tipo="success",
                    titulo=f"💰 Pagamento Realizado - Montagem #{id}",
                    mensagem=f"{montador_nome} - Pagamento de R$ {valor_total:.2f} realizado",
                    dados={
                        "montagem_id": id,
                        "tipo": "montador",
                        "montador": montador_nome,
                        "periodo": periodo,
                        "valor": float(valor_total),
                        "data_pagamento": data_hoje.strftime('%d/%m/%Y')
                    }
                )
                print(f"   📡 Notificação WebSocket enviada")
            except Exception as e:
                print(f"⚠️ Erro ao enviar notificação WebSocket: {str(e)}")
            
            return {'message': 'Montagem marcada como paga com sucesso'}
            # Enviar notificação WhatsApp
            try:
                print(f"\n📱 Enviando notificação de pagamento realizado...")
                enviar_notificacao_whatsapp(
                    evento='pagamento_realizado_montador',
                    destinatario_id=montador_id,
                    tipo='montador',
                    variaveis={
                        'nome_montador': montador_nome,
                        'periodo': periodo,
                        'valor': str(valor_total),
                        'data_pagamento': data_hoje.strftime('%d/%m/%Y')
                    }
                )
            except Exception as e:
                print(f"⚠️ Erro ao enviar WhatsApp: {str(e)}")
                # Não falha a operação se WhatsApp der erro
            
            return {'message': 'Montagem marcada como paga com sucesso'}
