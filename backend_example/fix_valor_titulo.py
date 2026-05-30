#!/usr/bin/env python3
"""Fix: Atualizar valor_titulo nos títulos parcelados existentes"""
import sys
sys.path.insert(0, '/var/www/braco-direto-ai/backend_example')

import psycopg2, psycopg2.extras
from app.database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # 1. Parcelas criadas via split (têm titulo_original_id)
        cur.execute("""
            UPDATE titulos_importados t
            SET valor_titulo = sub.total
            FROM (
                SELECT titulo_original_id, SUM(valor) as total
                FROM titulos_importados
                WHERE titulo_original_id IS NOT NULL
                GROUP BY titulo_original_id
            ) sub
            WHERE t.titulo_original_id = sub.titulo_original_id
            AND (t.valor_titulo IS NULL OR t.valor_titulo = 0)
        """)
        print(f"Parcelas split atualizadas: {cur.rowcount}")

        # 2. Parcelas criadas na importação (parcela_numero sem titulo_original_id)
        cur.execute("""
            UPDATE titulos_importados t
            SET valor_titulo = sub.total
            FROM (
                SELECT 
                    REGEXP_REPLACE(numero_titulo, E'\\s*\\(\\d+/\\d+\\)$', '') as base,
                    nome_fornecedor, data_vencimento, SUM(valor) as total
                FROM titulos_importados
                WHERE parcela_numero IS NOT NULL AND titulo_original_id IS NULL
                GROUP BY base, nome_fornecedor, data_vencimento
            ) sub
            WHERE REGEXP_REPLACE(t.numero_titulo, E'\\s*\\(\\d+/\\d+\\)$', '') = sub.base
            AND t.nome_fornecedor = sub.nome_fornecedor
            AND t.data_vencimento = sub.data_vencimento
            AND t.parcela_numero IS NOT NULL
            AND t.titulo_original_id IS NULL
            AND (t.valor_titulo IS NULL OR t.valor_titulo = 0)
        """)
        print(f"Parcelas importação atualizadas: {cur.rowcount}")

print("OK - valor_titulo corrigido")
