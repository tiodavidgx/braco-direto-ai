"""
Dispara notificações quando um upload de NF é recebido
WebSocket, WhatsApp e Trello
"""

import logging
import threading
from datetime import datetime
from app.database import get_db_connection

logger = logging.getLogger('UploadNotifications')


def disparar_notificacoes_upload(upload_id: int):
    """
    Dispara notificações em background quando upload é recebido
    - Notificação WebSocket em tempo real
    - WhatsApp para o prestador/montador
    - Criação de card no Trello
    """
    thread = threading.Thread(
        target=_processar_notificacoes,
        args=(upload_id,),
        daemon=True
    )
    thread.start()


def _processar_notificacoes(upload_id: int):
    """Processa todas as notificações para um upload"""
    try:
        with get_db_connection() as conn:
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Buscar dados do upload
            cur.execute("""
                SELECT 
                    u.id,
                    u.tipo,
                    u.lote_id,
                    u.envio_montagem_id,
                    u.hash
                FROM uploads_nf u
                WHERE u.id = %s
            """, (upload_id,))
            
            upload = cur.fetchone()
            if not upload:
                logger.error(f"Upload {upload_id} não encontrado")
                return
            
            # Buscar arquivos
            cur.execute("""
                SELECT nome_original, tamanho_bytes
                FROM uploads_nf_arquivos
                WHERE upload_id = %s
            """, (upload_id,))
            arquivos = cur.fetchall()
            
            total_arquivos = len(arquivos)
            tamanho_total = sum(a['tamanho_bytes'] for a in arquivos)
            
            # Buscar dados da entidade
            if upload['tipo'] == 'prestador':
                cur.execute("""
                    SELECT 
                        l.prestador_id,
                        l.prestador_nome,
                        l.periodo,
                        l.valor_total,
                        p.email,
                        p.telefone
                    FROM lotes_servico l
                    LEFT JOIN prestadores p ON l.prestador_id = p.id
                    WHERE l.id = %s
                """, (upload['lote_id'],))
                dados = cur.fetchone()
                entity_id = upload['lote_id']
                entity_type = 'prestador'
                nome = dados['prestador_nome']
                destinatario_id = dados['prestador_id']
            else:
                cur.execute("""
                    SELECT 
                        e.montador_id,
                        e.montador_nome,
                        e.periodo,
                        e.valor_total,
                        m.email,
                        m.telefone
                    FROM envios_montagem e
                    LEFT JOIN montadores m ON e.montador_id = m.id
                    WHERE e.id = %s
                """, (upload['envio_montagem_id'],))
                dados = cur.fetchone()
                entity_id = upload['envio_montagem_id']
                entity_type = 'montador'
                nome = dados['montador_nome']
                destinatario_id = dados['montador_id']
            
            if not dados:
                logger.error(f"Dados não encontrados para upload {upload_id}")
                return
            
            # 1. Criar notificação no banco
            _criar_notificacao_banco(
                cur, conn, entity_type, entity_id, nome, 
                total_arquivos, tamanho_total
            )
            
            # 2. Enviar WebSocket
            _enviar_websocket(
                entity_type, entity_id, nome, 
                dados['periodo'], dados['valor_total'],
                total_arquivos, tamanho_total
            )
            
            # 3. Enviar WhatsApp
            _enviar_whatsapp(
                entity_type, destinatario_id, nome,
                dados['periodo'], dados['valor_total'],
                arquivos[0]['nome_original'] if arquivos else None,
                entity_id
            )
            
            # 4. Criar card no Trello
            _criar_card_trello(
                entity_type, entity_id, nome,
                dados['valor_total'], arquivos
            )
            
            logger.info(f"Notificações enviadas para upload {upload_id}")
            
    except Exception as e:
        logger.error(f"Erro ao processar notificações: {e}")
        import traceback
        traceback.print_exc()


def _criar_notificacao_banco(cur, conn, entity_type, entity_id, nome, total_arquivos, tamanho_total):
    """Cria notificação no banco de dados"""
    try:
        tamanho_fmt = _formatar_tamanho(tamanho_total)
        titulo = f"📥 Nota Fiscal Recebida"
        mensagem = f"{nome} enviou {total_arquivos} arquivo(s) ({tamanho_fmt})"
        
        if entity_type == 'prestador':
            cur.execute("""
                INSERT INTO notificacoes 
                (tipo, titulo, mensagem, lote_id, icone, prioridade, data_criacao, lida)
                VALUES ('nf_recebida', %s, %s, %s, '📥', 1, NOW(), false)
            """, (titulo, mensagem, entity_id))
        else:
            cur.execute("""
                INSERT INTO notificacoes 
                (tipo, titulo, mensagem, envio_montagem_id, icone, prioridade, data_criacao, lida)
                VALUES ('nf_recebida', %s, %s, %s, '📥', 1, NOW(), false)
            """, (titulo, mensagem, entity_id))
        
        conn.commit()
        logger.info(f"Notificação criada no banco para {entity_type} #{entity_id}")
        
    except Exception as e:
        logger.warning(f"Erro ao criar notificação no banco: {e}")


def _enviar_websocket(entity_type, entity_id, nome, periodo, valor, total_arquivos, tamanho_total):
    """Envia notificação via WebSocket"""
    try:
        import asyncio
        from app.routes.notifications import notification_manager
        
        tamanho_fmt = _formatar_tamanho(tamanho_total)
        titulo = f"📥 NF Recebida - {'Lote' if entity_type == 'prestador' else 'Montagem'} #{entity_id}"
        mensagem = f"{nome} enviou {total_arquivos} arquivo(s) ({tamanho_fmt})"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            notification_manager.send_notification(
                tipo="success",
                titulo=titulo,
                mensagem=mensagem,
                dados={
                    "tipo": entity_type,
                    "entity_id": entity_id,
                    "nome": nome,
                    "periodo": periodo,
                    "valor": float(valor) if valor else 0,
                    "total_arquivos": total_arquivos,
                    "tamanho_total": tamanho_fmt
                }
            )
        )
        loop.close()
        logger.info(f"WebSocket enviado para {entity_type} #{entity_id}")
        
    except Exception as e:
        logger.warning(f"Erro ao enviar WebSocket: {e}")


def _enviar_whatsapp(entity_type, destinatario_id, nome, periodo, valor, nome_arquivo, entity_id):
    """Envia notificação via WhatsApp"""
    try:
        from app.utils.whatsapp_automation import enviar_notificacao_whatsapp
        
        evento = f'nf_recebida_{entity_type}'
        
        if entity_type == 'prestador':
            variaveis = {
                'nome_prestador': nome,
                'lote_id': str(entity_id),
                'periodo': periodo,
                'valor': str(valor or 0),
                'numero_nf': nome_arquivo or 'N/A',
                'data_recebimento': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
        else:
            variaveis = {
                'nome_montador': nome,
                'envio_id': str(entity_id),
                'periodo': periodo,
                'valor': str(valor or 0),
                'numero_nf': nome_arquivo or 'N/A',
                'data_recebimento': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
        
        enviar_notificacao_whatsapp(
            evento=evento,
            destinatario_id=destinatario_id,
            tipo=entity_type,
            variaveis=variaveis
        )
        logger.info(f"WhatsApp enviado para {entity_type} #{destinatario_id}")
        
    except Exception as e:
        logger.warning(f"Erro ao enviar WhatsApp: {e}")


def _criar_card_trello(entity_type, entity_id, nome, valor, arquivos):
    """Cria card no Trello com os arquivos anexados"""
    try:
        from app.services.trello_service import TrelloIntegration
        
        trello = TrelloIntegration()
        if not trello.is_configured():
            logger.info("Trello não configurado - pulando criação de card")
            return
        
        arquivos_nomes = [a['nome_original'] for a in arquivos]
        
        # Montar caminhos dos arquivos para anexar
        if entity_type == 'prestador':
            pasta = f"uploads/notas_fiscais/lote_{entity_id}"
        else:
            pasta = f"uploads/notas_fiscais/montagem_{entity_id}"
        
        import os
        arquivos_paths = []
        for arq in arquivos:
            # Nome salvo está na tabela, mas aqui só temos nome_original
            # Vamos tentar encontrar pelo nome original
            caminho = os.path.join(pasta, arq['nome_original'])
            if os.path.exists(caminho):
                arquivos_paths.append(caminho)
        
        if entity_type == 'prestador':
            card = trello.criar_card_download(
                lote_id=entity_id,
                prestador_nome=nome,
                arquivos_baixados=arquivos_nomes,
                arquivos_para_anexar=arquivos_paths,
                valor_lote=float(valor) if valor else 0
            )
        else:
            card = trello.criar_card_download(
                envio_montagem_id=entity_id,
                montador_nome=nome,
                arquivos_baixados=arquivos_nomes,
                arquivos_para_anexar=arquivos_paths,
                valor_lote=float(valor) if valor else 0
            )
        
        if card:
            logger.info(f"Card Trello criado: {card.get('shortUrl')}")
        
    except Exception as e:
        logger.warning(f"Erro ao criar card Trello: {e}")


def _formatar_tamanho(bytes: int) -> str:
    """Formata tamanho em bytes"""
    for unidade in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unidade}"
        bytes /= 1024
    return f"{bytes:.1f} TB"
