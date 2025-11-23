#!/usr/bin/env python3
"""
Teste para verificar criação de card Trello para Montadores
"""

import sys
import os

# Adicionar o diretório app ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.trello_service import TrelloIntegration

def test_criar_card_montador():
    """Testa criação de card para montador"""
    
    print("=" * 60)
    print("TESTE: Criação de Card Trello para Montador")
    print("=" * 60)
    
    # Inicializar Trello
    trello = TrelloIntegration()
    
    if not trello.is_configured():
        print("❌ Trello não está configurado!")
        return False
    
    print("✅ Trello configurado")
    
    # Dados de teste
    montador_nome = "TESTE MONTADOR"
    arquivos_baixados = ["teste_arquivo.pdf"]
    nota_fiscal = "123456"
    valor_lote = 100.50
    envio_montagem_id = 999999  # ID de teste
    
    print(f"\n📋 Criando card de teste...")
    print(f"   Montador: {montador_nome}")
    print(f"   Envio ID: {envio_montagem_id}")
    print(f"   Arquivos: {arquivos_baixados}")
    print(f"   Valor: R$ {valor_lote}")
    
    try:
        resultado = trello.criar_card_download(
            lote_id=None,  # Para montador, lote_id é None
            prestador_nome=None,  # Para montador, prestador é None
            montador_nome=montador_nome,
            arquivos_baixados=arquivos_baixados,
            nota_fiscal=nota_fiscal,
            arquivos_para_anexar=None,  # Sem anexos no teste
            valor_lote=valor_lote,
            envio_montagem_id=envio_montagem_id
        )
        
        if resultado:
            print(f"\n✅ SUCESSO!")
            print(f"   Card URL: {resultado.get('shortUrl', 'N/A')}")
            print(f"   Card ID: {resultado.get('id', 'N/A')}")
            
            # Verificar se foi salvo no banco
            from app.database import get_db_connection
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT card_id, short_url, tipo, envio_montagem_id 
                    FROM trello_cards 
                    WHERE envio_montagem_id = %s
                """, (envio_montagem_id,))
                card_db = cur.fetchone()
                
                if card_db:
                    print(f"\n✅ Card salvo no banco:")
                    print(f"   Card ID: {card_db[0]}")
                    print(f"   URL: {card_db[1]}")
                    print(f"   Tipo: {card_db[2]}")
                    print(f"   Envio Montagem ID: {card_db[3]}")
                else:
                    print(f"\n⚠️  Card NÃO foi salvo no banco")
            
            return True
        else:
            print(f"\n❌ FALHA: Não foi possível criar o card")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = test_criar_card_montador()
    sys.exit(0 if sucesso else 1)
