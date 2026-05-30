#!/usr/bin/env python3
"""
Executa o job de consulta de notas manualmente
"""

import sys
import os

# Adicionar path do backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.jobs.consultar_notas import processar_uploads_pendentes

if __name__ == "__main__":
    print("="*60)
    print("🔄 EXECUTANDO JOB DE CONSULTA DE NOTAS")
    print("="*60)
    print()
    print("Este job vai:")
    print("  1. Buscar lotes com upload pendente")
    print("  2. Consultar API externa para ver se NF foi enviada")
    print("  3. Baixar arquivos de NF")
    print("  4. Criar cards no Trello")
    print("  5. Enviar notificações")
    print()
    print("-"*60)
    print()
    
    try:
        resultado = processar_uploads_pendentes()
        
        print()
        print("="*60)
        print("✅ JOB CONCLUÍDO")
        print("="*60)
        print()
        print(f"📊 Resultados:")
        print(f"   Total processados: {resultado.get('total_processados', 0)}")
        print(f"   Arquivos encontrados: {resultado.get('arquivos_encontrados', 0)}")
        print(f"   Downloads realizados: {resultado.get('downloads', 0)}")
        print(f"   Cards criados no Trello: {resultado.get('cards_trello', 0)}")
        print()
        
        erros = resultado.get('erros', [])
        if erros:
            print(f"⚠️  Erros ({len(erros)}):")
            for erro in erros:
                print(f"   - {erro}")
        else:
            print("✅ Nenhum erro encontrado")
        print()
        
        detalhes = resultado.get('detalhes', [])
        if detalhes:
            print(f"📋 Detalhes ({len(detalhes)}):")
            for detalhe in detalhes:
                print(f"   • {detalhe}")
        print()
        
    except Exception as e:
        print()
        print("="*60)
        print("❌ ERRO AO EXECUTAR JOB")
        print("="*60)
        print(f"\n{str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
