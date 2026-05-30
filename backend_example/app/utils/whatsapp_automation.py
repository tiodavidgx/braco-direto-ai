"""
Utilitário para processar automações WhatsApp
"""
import os
import requests
import re
from typing import Dict, Any, Optional
from app.database import get_db_connection
from app.utils.whatsapp_http import WA_HEADERS
import psycopg2.extras

WHATSAPP_BASE_URL = os.getenv("WHATSAPP_BASE_URL", "http://localhost:3000")


def processar_template(template: str, variaveis: Dict[str, Any]) -> str:
    """
    Substitui variáveis no template
    
    Args:
        template: Template com placeholders {{variavel}}
        variaveis: Dicionário com valores das variáveis
    
    Returns:
        Template processado com valores substituídos
    """
    resultado = template
    for chave, valor in variaveis.items():
        placeholder = f"{{{{{chave}}}}}"
        resultado = resultado.replace(placeholder, str(valor))
    
    return resultado


def enviar_notificacao_whatsapp(
    evento: str,
    destinatario_id: int,
    tipo: str,  # 'prestador' ou 'montador'
    variaveis: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Processa e envia notificação WhatsApp baseada em automação
    
    Args:
        evento: Nome do evento (ex: 'envio_email_prestador')
        destinatario_id: ID do prestador ou montador
        tipo: 'prestador' ou 'montador'
        variaveis: Variáveis para substituir no template
    
    Returns:
        Resultado do envio ou None se não houver automação ativa
    """
    print(f"\n🤖 [WhatsApp Automation] Iniciando processamento...")
    print(f"   Evento: {evento}")
    print(f"   Destinatário ID: {destinatario_id}")
    print(f"   Tipo: {tipo}")
    print(f"   Variáveis: {variaveis}")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar automação ativa para este evento
        cur.execute("""
            SELECT a.*, t.template, t.nome as template_nome
            FROM automacao_whatsapp a
            JOIN templates_whatsapp t ON a.template_id = t.id::text
            WHERE a.evento = %s AND a.ativo = TRUE AND t.ativo = TRUE
            LIMIT 1
        """, (evento,))
        
        automacao = cur.fetchone()
        
        if not automacao:
            print(f"   ⚠️ Nenhuma automação ativa encontrada para evento: {evento}")
            return {
                'success': False,
                'message': f'Nenhuma automação ativa para evento: {evento}'
            }
        
        print(f"   ✅ Automação encontrada: {automacao['template_nome']}")
        
        # Buscar informações do destinatário
        telefone = None
        nome = None
        
        if tipo == 'prestador':
            cur.execute("SELECT nome, telefone FROM prestadores WHERE id = %s", (destinatario_id,))
        else:
            cur.execute("SELECT nome, telefone FROM montadores WHERE id = %s", (destinatario_id,))
        
        destinatario = cur.fetchone()
        
        if not destinatario:
            print(f"❌ Destinatário não encontrado: {tipo} #{destinatario_id}")
            return None
        
        telefone = destinatario.get('telefone')
        nome = destinatario.get('nome')
        
        if not telefone:
            print(f"⚠️ {tipo.capitalize()} {nome} não tem telefone cadastrado")
            return None
        
        # Adicionar nome às variáveis
        if tipo == 'prestador':
            variaveis['nome_prestador'] = nome
        else:
            variaveis['nome_montador'] = nome
        
        # Processar template
        mensagem = processar_template(automacao['template'], variaveis)
        
        print(f"\n📤 Enviando WhatsApp:")
        print(f"   Destinatário: {nome} ({telefone})")
        print(f"   Evento: {evento}")
        print(f"   Template: {automacao['template_nome']}")
        
        # Verificar se servidor WhatsApp está rodando
        try:
            status_response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2, headers=WA_HEADERS)
            status_data = status_response.json()
            
            print(f"   📡 Status WhatsApp: {status_data.get('status', 'unknown')}")
            
            if status_data.get('status') != 'connected':
                print(f"   ⚠️ WhatsApp não está conectado (status: {status_data.get('status')}). Enfileirando...")
                
                # Adicionar à fila para processamento posterior
                cur.execute("""
                    INSERT INTO notificacoes_whatsapp 
                    (prestador_id, montador_id, tipo, mensagem, status, metadata)
                    VALUES (%s, %s, %s, %s, 'pendente', %s)
                """, (
                    destinatario_id if tipo == 'prestador' else None,
                    destinatario_id if tipo == 'montador' else None,
                    evento,
                    mensagem,
                    psycopg2.extras.Json({
                        'telefone': telefone,
                        'nome': nome,
                        'template': automacao['template_nome']
                    })
                ))
                conn.commit()
                
                return {
                    'success': True,
                    'message': 'WhatsApp não conectado. Mensagem enfileirada.',
                    'queued': True
                }
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Servidor WhatsApp não está acessível: {e}")
            
            # Adicionar à fila
            cur.execute("""
                INSERT INTO notificacoes_whatsapp 
                (prestador_id, montador_id, tipo, mensagem, status, metadata)
                VALUES (%s, %s, %s, %s, 'pendente', %s)
            """, (
                destinatario_id if tipo == 'prestador' else None,
                destinatario_id if tipo == 'montador' else None,
                evento,
                mensagem,
                psycopg2.extras.Json({
                    'telefone': telefone,
                    'nome': nome,
                    'template': automacao['template_nome']
                })
            ))
            conn.commit()
            
            return {
                'success': True,
                'message': f'Servidor WhatsApp offline ({str(e)}). Mensagem enfileirada.',
                'queued': True
            }
        
        # Enviar mensagem
        print(f"   📤 Tentando enviar via API...")
        try:
            response = requests.post(
                f"{WHATSAPP_BASE_URL}/send",
                json={
                    'number': telefone,
                    'message': mensagem
                },
                timeout=30, headers=WA_HEADERS)
            
            print(f"   📡 Response status: {response.status_code}")
            resultado = response.json()
            print(f"   📡 Response body: {resultado}")
            
            if resultado.get('success'):
                print(f"   ✅ Mensagem enviada com sucesso!")
                
                # Registrar envio
                cur.execute("""
                    INSERT INTO notificacoes_whatsapp 
                    (prestador_id, montador_id, tipo, mensagem, status, metadata)
                    VALUES (%s, %s, %s, %s, 'enviado', %s)
                """, (
                    destinatario_id if tipo == 'prestador' else None,
                    destinatario_id if tipo == 'montador' else None,
                    evento,
                    mensagem,
                    psycopg2.extras.Json({
                        'telefone': telefone,
                        'nome': nome,
                        'template': automacao['template_nome']
                    })
                ))
                conn.commit()
                
                return resultado
            else:
                print(f"   ❌ Erro ao enviar: {resultado.get('error')}")
                
                # Registrar erro
                cur.execute("""
                    INSERT INTO notificacoes_whatsapp 
                    (prestador_id, montador_id, tipo, mensagem, status, erro, metadata)
                    VALUES (%s, %s, %s, %s, 'erro', %s, %s)
                """, (
                    destinatario_id if tipo == 'prestador' else None,
                    destinatario_id if tipo == 'montador' else None,
                    evento,
                    mensagem,
                    resultado.get('error'),
                    psycopg2.extras.Json({
                        'telefone': telefone,
                        'nome': nome,
                        'template': automacao['template_nome']
                    })
                ))
                conn.commit()
                
                return resultado
                
        except Exception as e:
            print(f"   ❌ Exceção ao enviar: {e}")
            
            # Registrar erro
            cur.execute("""
                INSERT INTO notificacoes_whatsapp 
                (prestador_id, montador_id, tipo, mensagem, status, erro, metadata)
                VALUES (%s, %s, %s, %s, 'erro', %s, %s)
            """, (
                destinatario_id if tipo == 'prestador' else None,
                destinatario_id if tipo == 'montador' else None,
                evento,
                mensagem,
                str(e),
                psycopg2.extras.Json({
                    'telefone': telefone,
                    'nome': nome,
                    'template': automacao['template_nome']
                })
            ))
            conn.commit()
            
            return {
                'success': False,
                'error': str(e)
            }


def processar_fila_whatsapp(limite: int = 50) -> Dict[str, Any]:
    """
    Processa mensagens pendentes na fila de WhatsApp
    
    Args:
        limite: Número máximo de mensagens a processar
    
    Returns:
        Estatísticas do processamento
    """
    # Verificar se WhatsApp está conectado
    try:
        status_response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2, headers=WA_HEADERS)
        status = status_response.json()
        
        if status.get('status') != 'connected':
            return {
                'success': False,
                'message': 'WhatsApp não está conectado'
            }
    except:
        return {
            'success': False,
            'message': 'Servidor WhatsApp não está rodando'
        }
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar mensagens pendentes
        cur.execute("""
            SELECT * FROM notificacoes_whatsapp 
            WHERE status = 'pendente'
            ORDER BY data_envio
            LIMIT %s
        """, (limite,))
        
        pendentes = cur.fetchall()
        
        if not pendentes:
            return {
                'success': True,
                'message': 'Nenhuma mensagem pendente',
                'processadas': 0
            }
        
        enviadas = 0
        erros = 0
        
        print(f"\n📤 Processando {len(pendentes)} mensagens pendentes...")
        
        for notificacao in pendentes:
            try:
                metadata = notificacao.get('metadata', {})
                telefone = metadata.get('telefone')
                
                if not telefone:
                    continue
                
                # Enviar mensagem
                response = requests.post(
                    f"{WHATSAPP_BASE_URL}/send",
                    json={
                        'number': telefone,
                        'message': notificacao['mensagem']
                    },
                    timeout=30, headers=WA_HEADERS)
                
                resultado = response.json()
                
                if resultado.get('success'):
                    cur.execute("""
                        UPDATE notificacoes_whatsapp 
                        SET status = 'enviado'
                        WHERE id = %s
                    """, (notificacao['id'],))
                    enviadas += 1
                    print(f"   ✅ Enviado para {metadata.get('nome')}")
                else:
                    cur.execute("""
                        UPDATE notificacoes_whatsapp 
                        SET status = 'erro', erro = %s
                        WHERE id = %s
                    """, (resultado.get('error'), notificacao['id']))
                    erros += 1
                    print(f"   ❌ Erro ao enviar para {metadata.get('nome')}")
                
                # Delay entre mensagens
                import time
                time.sleep(2)
                
            except Exception as e:
                cur.execute("""
                    UPDATE notificacoes_whatsapp 
                    SET status = 'erro', erro = %s
                    WHERE id = %s
                """, (str(e), notificacao['id']))
                erros += 1
                print(f"   ❌ Exceção: {e}")
        
        conn.commit()
        
        return {
            'success': True,
            'message': f'Processamento concluído',
            'total': len(pendentes),
            'enviadas': enviadas,
            'erros': erros
        }
