#!/usr/bin/env python3
"""
Simula webhook de NF recebida para lote específico
"""

import requests
import sys

def simular_nf_recebida(lote_id, tipo="lote"):
    """Simula recebimento de NF para um lote"""
    
    url = "http://localhost:8000/api/v1/upload/webhook/nf-recebida"
    
    payload = {
        "lote_id": lote_id,
        "tipo": tipo,  # "lote" ou "montagem"
        "hash": f"hash_{lote_id}",
        "nota_fiscal": f"NF_LOTE_{lote_id}.pdf",
        "data_upload": "2025-11-13T14:30:00"
    }
    
    print(f"\n📤 Simulando recebimento de NF para lote {lote_id}...")
    print(f"   Tipo: {tipo}")
    print(f"   Payload: {payload}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sucesso: {data}")
            print()
            print("🔔 Verifique o frontend - deve aparecer notificação verde!")
        else:
            print(f"❌ Erro: {response.text}")
            
    except Exception as e:
        print(f"❌ Exceção: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        lote_id = int(sys.argv[1])
        tipo = sys.argv[2] if len(sys.argv) > 2 else "lote"
    else:
        lote_id = 177
        tipo = "lote"
    
    print("="*60)
    print("🔔 SIMULADOR DE RECEBIMENTO DE NF")
    print("="*60)
    
    simular_nf_recebida(lote_id, tipo)
    
    print("\n💡 Uso:")
    print(f"   python {sys.argv[0]} <lote_id> [tipo]")
    print(f"   python {sys.argv[0]} 177 lote")
    print(f"   python {sys.argv[0]} 50 montagem")
