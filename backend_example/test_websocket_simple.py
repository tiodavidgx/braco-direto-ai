#!/usr/bin/env python3
"""
Teste simples de WebSocket - envia notificação HTTP
"""

import requests
import json

# URL do backend
BASE_URL = "http://localhost:14001"

def test_webhook_nf():
    """Testa webhook de NF recebida (deve enviar notificação)"""
    print("\n📤 Testando webhook de NF recebida...")
    
    url = f"{BASE_URL}/api/v1/upload/webhook/nf-recebida"
    
    payload = {
        "lote_id": 123,
        "tipo": "lote",
        "hash": "abc123",
        "nota_fiscal": "NF_TESTE_001.pdf",
        "data_upload": "2025-11-13T10:30:00"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Webhook enviado! Se o frontend estiver aberto, você deve ver a notificação.")
        else:
            print(f"❌ Erro: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")


def check_health():
    """Verifica se API está online"""
    print("\n🏥 Verificando saúde da API...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API está online!")
            return True
        else:
            print(f"❌ API retornou status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        print("💡 Certifique-se de que o backend está rodando (uvicorn)")
        return False


if __name__ == "__main__":
    print("="*60)
    print("🔔 TESTE SIMPLES DE NOTIFICAÇÕES")
    print("="*60)
    
    if check_health():
        print("\n💡 ANTES DE TESTAR:")
        print("   1. Abra o frontend no navegador (http://localhost:14002)")
        print("   2. Abra o Console do navegador (F12)")
        print("   3. Verifique se aparece: 'Conectado ao servidor de notificações'")
        print("\nPressione ENTER para enviar notificação de teste...")
        input()
        
        test_webhook_nf()
        
        print("\n✨ Se tudo estiver certo, você verá uma notificação verde no canto superior direito!")
    else:
        print("\n❌ Não foi possível conectar ao backend.")
        print("   Execute: uvicorn app.main:app --reload")
