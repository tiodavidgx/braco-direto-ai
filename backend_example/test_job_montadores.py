#!/usr/bin/env python3
"""
Script para testar se o job está encontrando envios de montadores pendentes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'sistema_original'))

import database as db

print("🔍 VERIFICANDO ENVIOS DE MONTADORES PENDENTES")
print("=" * 60)

# Buscar envios pendentes
envios = db.get_envios_montagem_upload_pendente()

print(f"\n📊 Total de envios pendentes: {len(envios)}")

if len(envios) == 0:
    print("\n⚠️  Nenhum envio pendente encontrado!")
    print("\nVerificando todos os envios de montadores:")
    
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id,
            montador_nome,
            periodo,
            upload_hash IS NOT NULL as tem_hash,
            upload_hash,
            status_arquivo,
            validade_link,
            link_upload
        FROM envios_montagem
        ORDER BY id DESC
        LIMIT 10
    """)
    
    todos_envios = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n📋 Últimos 10 envios de montadores:")
    print("-" * 60)
    for envio in todos_envios:
        print(f"""
ID: {envio[0]}
Montador: {envio[1]}
Período: {envio[2]}
Tem Hash: {envio[3]}
Hash: {envio[4][:20] if envio[4] else 'N/A'}...
Status Arquivo: {envio[5]}
Validade: {envio[6]}
Link: {envio[7][:50] if envio[7] else 'N/A'}...
        """)
else:
    print("\n✅ Envios pendentes encontrados:\n")
    for envio in envios:
        print(f"""
{'─' * 60}
ID: {envio['id']}
Montador: {envio.get('montador_nome', 'N/A')}
Período: {envio.get('periodo', 'N/A')}
Hash: {envio.get('upload_hash', 'N/A')[:20]}...
Status Arquivo: {envio.get('status_arquivo', 'N/A')}
Validade: {envio.get('validade_link', 'N/A')}
        """)

print("\n" + "=" * 60)
