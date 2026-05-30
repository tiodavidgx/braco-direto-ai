#!/usr/bin/env python3
"""
Script para corrigir data_recebimento_nf e data_vencimento_pagamento
em lotes que já têm nota fiscal mas faltam essas datas.

Execução: python3 corrigir_datas_nf.py
"""

from app.database import get_db_connection
from datetime import datetime, timedelta

def corrigir_lotes_servico():
    """Corrige lotes de prestadores com NF mas sem datas"""
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Buscar lotes com NF mas sem datas completas
        cur.execute("""
            SELECT ls.id, p.tempo_vencimento_dias, ls.nota_fiscal_path,
                   ls.data_recebimento_nf, ls.data_vencimento_pagamento
            FROM lotes_servico ls
            LEFT JOIN prestadores p ON ls.prestador_id = p.id
            WHERE ls.nota_fiscal_path IS NOT NULL
            AND (ls.data_recebimento_nf IS NULL OR ls.data_vencimento_pagamento IS NULL)
            AND ls.pago = FALSE
            ORDER BY ls.id
        """)
        
        lotes = cur.fetchall()
        
        if not lotes:
            print("✅ Todos os lotes com NF já têm datas corretas!")
            return
        
        print(f"\n🔧 Corrigindo {len(lotes)} lote(s) de prestadores...\n")
        
        for lote_id, dias_venc, nf_path, data_rec, data_venc in lotes:
            dias = dias_venc if dias_venc else 30
            
            # Se não tem data de recebimento, usar NOW()
            # Se não tem data de vencimento, calcular baseado no tempo do prestador
            if not data_venc:
                data_vencimento = datetime.now() + timedelta(days=dias)
            else:
                data_vencimento = data_venc
            
            cur.execute("""
                UPDATE lotes_servico
                SET 
                    data_recebimento_nf = COALESCE(data_recebimento_nf, NOW()),
                    data_vencimento_pagamento = COALESCE(data_vencimento_pagamento, %s)
                WHERE id = %s
            """, (data_vencimento, lote_id))
            
            status = []
            if not data_rec:
                status.append("data_recebimento_nf")
            if not data_venc:
                status.append(f"data_vencimento ({dias} dias)")
            
            print(f"✅ Lote #{lote_id:3d} - Corrigido: {', '.join(status)}")
        
        conn.commit()
        print(f"\n✅ Total de {len(lotes)} lote(s) corrigido(s)!\n")


def corrigir_envios_montagem():
    """Corrige envios de montadores com NF mas sem datas"""
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Buscar envios com NF mas sem datas completas
        cur.execute("""
            SELECT em.id, m.tempo_vencimento_dias, em.nota_fiscal_path,
                   em.data_recebimento_nf, em.data_vencimento_pagamento
            FROM envios_montagem em
            LEFT JOIN montadores m ON em.montador_id = m.id
            WHERE em.nota_fiscal_path IS NOT NULL
            AND (em.data_recebimento_nf IS NULL OR em.data_vencimento_pagamento IS NULL)
            AND em.pago = FALSE
            ORDER BY em.id
        """)
        
        envios = cur.fetchall()
        
        if not envios:
            print("✅ Todos os envios de montagem com NF já têm datas corretas!")
            return
        
        print(f"\n🔧 Corrigindo {len(envios)} envio(s) de montadores...\n")
        
        for envio_id, dias_venc, nf_path, data_rec, data_venc in envios:
            dias = dias_venc if dias_venc else 30
            
            if not data_venc:
                data_vencimento = datetime.now() + timedelta(days=dias)
            else:
                data_vencimento = data_venc
            
            cur.execute("""
                UPDATE envios_montagem
                SET 
                    data_recebimento_nf = COALESCE(data_recebimento_nf, NOW()),
                    data_vencimento_pagamento = COALESCE(data_vencimento_pagamento, %s)
                WHERE id = %s
            """, (data_vencimento, envio_id))
            
            status = []
            if not data_rec:
                status.append("data_recebimento_nf")
            if not data_venc:
                status.append(f"data_vencimento ({dias} dias)")
            
            print(f"✅ Envio #{envio_id:3d} - Corrigido: {', '.join(status)}")
        
        conn.commit()
        print(f"\n✅ Total de {len(envios)} envio(s) corrigido(s)!\n")


if __name__ == "__main__":
    print("="*60)
    print("🔧 CORREÇÃO DE DATAS DE NOTAS FISCAIS")
    print("="*60)
    
    try:
        corrigir_lotes_servico()
        corrigir_envios_montagem()
        
        print("="*60)
        print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
