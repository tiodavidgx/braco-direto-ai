#!/usr/bin/env python3
"""
Script para testar notificações em tempo real
Execute: python test_notifications.py
"""

import asyncio
import sys
import os

# Adicionar path do backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.routes.notifications import notification_manager


async def enviar_teste_nf_recebida():
    """Simula notificação de NF recebida"""
    print("📤 Enviando notificação: NF Recebida...")
    await notification_manager.send_notification(
        tipo="success",
        titulo="📄 Nota Fiscal Recebida",
        mensagem="João Silva enviou a NF do período 11/2025",
        dados={
            "lote_id": 123,
            "tipo": "prestador",
            "nome": "João Silva",
            "periodo": "11/2025",
            "valor": 1500.50,
            "nota_fiscal": "NF_001.pdf"
        }
    )
    print("✅ Notificação enviada!")


async def enviar_teste_trello():
    """Simula notificação de integração Trello"""
    print("📤 Enviando notificação: Trello...")
    await notification_manager.send_notification(
        tipo="info",
        titulo="🔗 Integrado no Trello",
        mensagem="Prestador Maria Santos - Lote #456",
        dados={
            "lote_id": 456,
            "tipo": "prestador",
            "nome": "Maria Santos",
            "card_url": "https://trello.com/c/abc123",
            "valor": 2300.00
        }
    )
    print("✅ Notificação enviada!")


async def enviar_teste_aviso():
    """Simula notificação de aviso"""
    print("📤 Enviando notificação: Aviso...")
    await notification_manager.send_notification(
        tipo="warning",
        titulo="⚠️ Atenção Necessária",
        mensagem="Pagamento vence em 24 horas - R$ 1.200,00",
        dados={
            "lote_id": 789,
            "tipo": "montador",
            "nome": "Carlos Montador",
            "valor": 1200.00
        }
    )
    print("✅ Notificação enviada!")


async def enviar_teste_erro():
    """Simula notificação de erro"""
    print("📤 Enviando notificação: Erro...")
    await notification_manager.send_notification(
        tipo="error",
        titulo="❌ Erro no Processamento",
        mensagem="Falha ao enviar email para Ana Costa",
        dados={
            "lote_id": 321,
            "erro": "SMTP timeout"
        }
    )
    print("✅ Notificação enviada!")


async def teste_multiplas():
    """Envia múltiplas notificações para testar empilhamento"""
    print("📤 Enviando múltiplas notificações...")
    
    await enviar_teste_nf_recebida()
    await asyncio.sleep(0.5)
    
    await enviar_teste_trello()
    await asyncio.sleep(0.5)
    
    await enviar_teste_aviso()
    await asyncio.sleep(0.5)
    
    await enviar_teste_erro()
    
    print("✅ Todas as notificações enviadas!")


async def menu():
    """Menu interativo"""
    while True:
        print("\n" + "="*50)
        print("🔔 TESTE DE NOTIFICAÇÕES EM TEMPO REAL")
        print("="*50)
        print("\nEscolha uma opção:")
        print("1. Notificação: NF Recebida (success)")
        print("2. Notificação: Integração Trello (info)")
        print("3. Notificação: Aviso (warning)")
        print("4. Notificação: Erro (error)")
        print("5. Enviar todas de uma vez")
        print("0. Sair")
        print("\n" + "="*50)
        
        escolha = input("\nDigite o número da opção: ").strip()
        
        if escolha == "1":
            await enviar_teste_nf_recebida()
        elif escolha == "2":
            await enviar_teste_trello()
        elif escolha == "3":
            await enviar_teste_aviso()
        elif escolha == "4":
            await enviar_teste_erro()
        elif escolha == "5":
            await teste_multiplas()
        elif escolha == "0":
            print("\n👋 Até logo!")
            break
        else:
            print("\n❌ Opção inválida!")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   🔔  TESTADOR DE NOTIFICAÇÕES EM TEMPO REAL              ║
║                                                            ║
║   Certifique-se de que:                                   ║
║   1. O backend está rodando (porta 8000)                  ║
║   2. O frontend está aberto no navegador                  ║
║   3. O WebSocket está conectado                           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(menu())
    except KeyboardInterrupt:
        print("\n\n👋 Interrompido pelo usuário. Até logo!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
