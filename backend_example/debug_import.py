#!/usr/bin/env python3
"""Debug: why 0 titles imported from CSV"""
import psycopg2
import re
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'braco_db'),
    user=os.getenv('DB_USER', 'braco'),
    password=os.getenv('DB_PASS'),
    host=os.getenv('DB_HOST', 'localhost')
)
cur = conn.cursor()

# CSV titles to check
titles = [
    ('29968', '1633987', '2026-03-12', 'GILMAR ALVES FERREIRA'),
    ('151317', '87', '2026-03-02', 'DAYANE DA CONCEICAO DA CRUZ'),
    ('32934', '3737', '2026-02-13', 'LEONEL SOARES DE QUEIROZ'),
]

print("=== CHECKING EACH CSV TITLE ===\n")

for cod, tit, dt, forn in titles:
    forn_prefix = forn[:20].upper()
    print(f"--- Title: {tit}, Cod: {cod}, Fornecedor: {forn[:30]}, Venc: {dt} ---")
    
    # 1. Check duplicate (same logic as import)
    cur.execute("""
        SELECT id, numero_titulo, UPPER(LEFT(nome_fornecedor,20)), data_vencimento 
        FROM titulos_importados 
        WHERE (
            TRIM(numero_titulo) = %s 
            OR TRIM(numero_titulo) LIKE %s
            OR TRIM(numero_titulo) LIKE %s
        )
        AND UPPER(LEFT(nome_fornecedor, 20)) = %s
        AND data_vencimento = %s
    """, (tit, f"{tit}-P%", f"{tit} (%", forn_prefix, dt))
    dups = cur.fetchall()
    print(f"  Duplicate check: {len(dups)} found")
    for d in dups:
        print(f"    -> id={d[0]}, titulo={d[1]}, forn_prefix={d[2]}, venc={d[3]}")
    
    # 2. Check blacklist
    cod_upper = (cod or '').strip().upper()
    tit_base = re.sub(r'[-\s]*P\d+$', '', tit)
    tit_base = re.sub(r'\s*\(\d+/\d+\)$', '', tit_base)
    chave = f"{cod_upper}|{tit_base.upper()}"
    
    cur.execute("SELECT id, chave_fornecedor_titulo FROM titulos_excluidos WHERE chave_fornecedor_titulo = %s", (chave,))
    bl = cur.fetchall()
    print(f"  Blacklist check (chave={chave}): {len(bl)} found")
    for b in bl:
        print(f"    -> id={b[0]}, chave={b[1]}")
    
    # 3. Date check
    from datetime import date
    data_minima = date(2026, 1, 16)
    data_venc = date(int(dt[:4]), int(dt[5:7]), int(dt[8:10]))
    if data_venc <= data_minima:
        print(f"  DATE FILTER: BLOCKED (venc {data_venc} <= {data_minima})")
    else:
        print(f"  Date filter: OK (venc {data_venc} > {data_minima})")
    
    # Verdict
    if dups:
        print(f"  >>> BLOCKED BY: DUPLICATE")
    elif bl:
        print(f"  >>> BLOCKED BY: BLACKLIST")
    elif data_venc <= data_minima:
        print(f"  >>> BLOCKED BY: DATE FILTER")
    else:
        print(f"  >>> SHOULD BE IMPORTED (no block found)")
    print()

# Also show all blacklist entries for reference
print("\n=== ALL BLACKLIST ENTRIES ===")
cur.execute("SELECT id, cod_fornecedor, numero_titulo, chave_fornecedor_titulo FROM titulos_excluidos")
for r in cur.fetchall():
    print(f"  id={r[0]}, cod={r[1]}, titulo={r[2]}, chave={r[3]}")

conn.close()
