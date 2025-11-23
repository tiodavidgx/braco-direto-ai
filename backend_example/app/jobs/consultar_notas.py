"""
Job para consultar status de uploads de notas fiscais
Baseado no sistema original: sistema_original/job_consultar_notas.py

Este job:
1. Busca lotes/envios com status "aguardando upload"
2. Consulta API externa (DV) para verificar se houve upload
3. Baixa arquivos de notas fiscais quando disponíveis
4. Cria notificações no sistema
5. Cria cards no Trello automaticamente com anexos
6. Dispara WhatsApp (se configurado)
"""

import os
import time
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from app.database import get_db_connection
from app.services.consulta_nf_client import ConsultaNFClient
from app.services.trello_service import TrelloIntegration

# Configurar logger
logger = logging.getLogger('JobConsultaNotas')
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_lotes_upload_pendente() -> List[Dict[str, Any]]:
    """Busca lotes de prestadores aguardando upload de nota fiscal"""
    with get_db_connection() as conn:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Primeiro garantir que a coluna upload_hash existe
        cur.execute("""
            ALTER TABLE lotes_servico 
            ADD COLUMN IF NOT EXISTS upload_hash TEXT
        """)
        conn.commit()
        
        cur.execute("""
            SELECT 
                l.id,
                l.prestador_id,
                l.prestador_nome,
                l.periodo,
                l.valor_total,
                l.link_upload,
                l.upload_hash,
                l.id_controle,
                l.status_api,
                l.status_arquivo,
                l.data_envio
            FROM lotes_servico l
            WHERE l.link_upload IS NOT NULL
            AND (l.upload_hash IS NOT NULL OR l.id_controle IS NOT NULL)
            AND (l.status_arquivo IS NULL OR l.status_arquivo < 2)
            ORDER BY l.data_envio DESC
        """)
        
        return cur.fetchall()


def get_envios_montagem_upload_pendente() -> List[Dict[str, Any]]:
    """Busca envios de montadores aguardando upload de nota fiscal"""
    with get_db_connection() as conn:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Primeiro garantir que a coluna upload_hash existe
        cur.execute("""
            ALTER TABLE envios_montagem 
            ADD COLUMN IF NOT EXISTS upload_hash TEXT
        """)
        conn.commit()
        
        cur.execute("""
            SELECT 
                e.id,
                e.montador_id,
                e.montador_nome,
                e.periodo,
                e.valor_total,
                e.link_upload,
                e.upload_hash,
                e.id_controle,
                e.status_api,
                e.data_envio
            FROM envios_montagem e
            WHERE e.link_upload IS NOT NULL
            AND (e.upload_hash IS NOT NULL OR e.id_controle IS NOT NULL)
            AND (e.status_api IS NULL OR e.status_api < 2)
            ORDER BY e.data_envio DESC
        """)
        
        return cur.fetchall()


def salvar_arquivos_nf(lote_id: int, arquivos: List[Dict], stats: Dict):
    """Salva informações dos arquivos no banco"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Primeiro garantir que as colunas existem
        cur.execute("""
            ALTER TABLE lotes_servico 
            ADD COLUMN IF NOT EXISTS total_arquivos_nf INTEGER,
            ADD COLUMN IF NOT EXISTS tamanho_total_nf BIGINT,
            ADD COLUMN IF NOT EXISTS data_ultima_consulta TIMESTAMP
        """)
        conn.commit()
        
        # Atualizar lote com informações dos arquivos
        cur.execute("""
            UPDATE lotes_servico
            SET 
                total_arquivos_nf = %s,
                tamanho_total_nf = %s,
                data_ultima_consulta = NOW()
            WHERE id = %s
        """, (stats['total_arquivos'], stats['total_tamanho'], lote_id))
        
        conn.commit()


def atualizar_status_arquivo(lote_id: int, status: int):
    """Atualiza status de arquivo do lote"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE lotes_servico
            SET status_arquivo = %s
            WHERE id = %s
        """, (status, lote_id))
        
        conn.commit()


def salvar_nota_fiscal(lote_id: int, caminho_arquivo: str):
    """Salva caminho da nota fiscal, atualiza datas e calcula vencimento"""
    from datetime import datetime, timedelta
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Buscar tempo de vencimento do prestador
        cur.execute("""
            SELECT p.tempo_vencimento_dias 
            FROM lotes_servico ls
            JOIN prestadores p ON ls.prestador_id = p.id
            WHERE ls.id = %s
        """, (lote_id,))
        
        result = cur.fetchone()
        dias_vencimento = result[0] if result and result[0] else 30
        
        # Calcular data de vencimento
        data_vencimento = datetime.now() + timedelta(days=dias_vencimento)
        
        # Atualizar lote com todas as informações
        cur.execute("""
            UPDATE lotes_servico
            SET 
                nota_fiscal_path = %s,
                status_api = 1,
                data_recebimento_nf = NOW(),
                data_vencimento_pagamento = %s
            WHERE id = %s
        """, (caminho_arquivo, data_vencimento, lote_id))
        
        conn.commit()
        
        logger.info(f"   📅 Data vencimento: {data_vencimento.strftime('%d/%m/%Y')} ({dias_vencimento} dias)")


def atualizar_status_api(lote_id: int, status: int):
    """Atualiza status da API"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE lotes_servico
            SET status_api = %s
            WHERE id = %s
        """, (status, lote_id))
        
        conn.commit()


def criar_notificacao(tipo: str, titulo: str, mensagem: str, lote_id: int, icone: str = '📋', prioridade: int = 0):
    """Cria uma notificação no sistema"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO notificacoes 
            (tipo, titulo, mensagem, lote_id, icone, prioridade, data_criacao, lida)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), false)
        """, (tipo, titulo, mensagem, lote_id, icone, prioridade))
        
        conn.commit()


# ========================================
# FUNÇÕES PARA ENVIOS DE MONTAGEM
# ========================================

def salvar_arquivos_nf_montagem(envio_id: int, arquivos: List[Dict], stats: Dict):
    """Salva informações dos arquivos de montagem no banco"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Garantir que as colunas existem
        cur.execute("""
            ALTER TABLE envios_montagem 
            ADD COLUMN IF NOT EXISTS total_arquivos_nf INTEGER,
            ADD COLUMN IF NOT EXISTS tamanho_total_nf BIGINT,
            ADD COLUMN IF NOT EXISTS data_ultima_consulta TIMESTAMP
        """)
        conn.commit()
        
        # Atualizar envio com informações dos arquivos
        cur.execute("""
            UPDATE envios_montagem
            SET 
                total_arquivos_nf = %s,
                tamanho_total_nf = %s,
                data_ultima_consulta = NOW()
            WHERE id = %s
        """, (stats['total_arquivos'], stats['total_tamanho'], envio_id))
        
        conn.commit()


def atualizar_status_arquivo_montagem(envio_id: int, status: int):
    """Atualiza status de arquivo do envio de montagem"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Garantir que a coluna existe
        cur.execute("""
            ALTER TABLE envios_montagem 
            ADD COLUMN IF NOT EXISTS status_arquivo INTEGER DEFAULT 0
        """)
        conn.commit()
        
        cur.execute("""
            UPDATE envios_montagem
            SET status_arquivo = %s
            WHERE id = %s
        """, (status, envio_id))
        
        conn.commit()


def salvar_nota_fiscal_montagem(envio_id: int, caminho_arquivo: str):
    """Salva caminho da nota fiscal de montagem, atualiza datas e calcula vencimento"""
    from datetime import datetime, timedelta
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Buscar tempo de vencimento do montador
        cur.execute("""
            SELECT m.tempo_vencimento_dias 
            FROM envios_montagem em
            JOIN montadores m ON em.montador_id = m.id
            WHERE em.id = %s
        """, (envio_id,))
        
        result = cur.fetchone()
        dias_vencimento = result[0] if result and result[0] else 30
        
        # Calcular data de vencimento
        data_vencimento = datetime.now() + timedelta(days=dias_vencimento)
        
        # Atualizar envio com todas as informações
        cur.execute("""
            UPDATE envios_montagem
            SET 
                nota_fiscal_path = %s,
                status_api = 1,
                data_recebimento_nf = NOW(),
                data_vencimento_pagamento = %s
            WHERE id = %s
        """, (caminho_arquivo, data_vencimento, envio_id))
        
        conn.commit()
        
        logger.info(f"   📅 Data vencimento: {data_vencimento.strftime('%d/%m/%Y')} ({dias_vencimento} dias)")


def atualizar_status_api_montagem(envio_id: int, status: int):
    """Atualiza status da API para envio de montagem"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE envios_montagem
            SET status_api = %s
            WHERE id = %s
        """, (status, envio_id))
        
        conn.commit()


def criar_notificacao_montagem(tipo: str, titulo: str, mensagem: str, envio_montagem_id: int, icone: str = '📋', prioridade: int = 0):
    """Cria uma notificação no sistema para envio de montagem"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Garantir que a coluna existe
        cur.execute("""
            ALTER TABLE notificacoes 
            ADD COLUMN IF NOT EXISTS envio_montagem_id INTEGER REFERENCES envios_montagem(id)
        """)
        conn.commit()
        
        cur.execute("""
            INSERT INTO notificacoes 
            (tipo, titulo, mensagem, envio_montagem_id, icone, prioridade, data_criacao, lida)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), false)
        """, (tipo, titulo, mensagem, envio_montagem_id, icone, prioridade))
        
        conn.commit()


async def enviar_notificacao_websocket(tipo: str, titulo: str, mensagem: str, dados: Dict[str, Any] = None):
    """Envia notificação via WebSocket para todos os clientes conectados"""
    try:
        from app.routes.notifications import notification_manager
        await notification_manager.send_notification(
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            dados=dados or {}
        )
    except Exception as e:
        logger.warning(f"⚠️  Erro ao enviar WebSocket: {e}")


def enviar_notificacao_websocket_sync(tipo: str, titulo: str, mensagem: str, dados: Dict[str, Any] = None):
    """Wrapper síncrono para enviar notificação WebSocket"""
    try:
        # Tentar executar em event loop existente ou criar novo
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se loop já está rodando, agendar tarefa
                asyncio.create_task(enviar_notificacao_websocket(tipo, titulo, mensagem, dados))
            else:
                # Se não está rodando, executar diretamente
                loop.run_until_complete(enviar_notificacao_websocket(tipo, titulo, mensagem, dados))
        except RuntimeError:
            # Criar novo event loop se não houver um
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(enviar_notificacao_websocket(tipo, titulo, mensagem, dados))
            loop.close()
    except Exception as e:
        logger.warning(f"⚠️  Erro ao enviar notificação WebSocket: {e}")


def processar_uploads_pendentes():
    """Processa lotes e envios de montagem aguardando upload de notas fiscais"""
    
    logger.info("="*60)
    logger.info("🔍 JOB DE CONSULTA DE NOTAS FISCAIS")
    logger.info("="*60)
    logger.info(f"⏰ Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    try:
        # Buscar lotes de prestadores
        lotes = get_lotes_upload_pendente()
        logger.info(f"🔧 {len(lotes)} lote(s) de prestadores aguardando nota fiscal")
        
        # Buscar envios de montadores
        envios_montagem = get_envios_montagem_upload_pendente()
        logger.info(f"🔧 {len(envios_montagem)} envio(s) de montadores aguardando nota fiscal")
        
        total_pendentes = len(lotes) + len(envios_montagem)
        
        if total_pendentes == 0:
            logger.info("✅ Nenhum item pendente no momento")
            return {
                'success': True,
                'total_processados': 0,
                'arquivos_encontrados': 0,
                'downloads': 0,
                'erros': 0
            }
        
        # Criar cliente de consulta
        client = ConsultaNFClient()
        
        arquivos_encontrados = 0
        downloads_realizados = 0
        erros = 0
        
        # ========================================
        # PROCESSAR LOTES DE PRESTADORES
        # ========================================
        
        for lote in lotes:
            lote_id = lote['id']
            upload_hash = lote.get('upload_hash')
            id_controle = lote.get('id_controle')
            prestador = lote['prestador_nome']
            periodo = lote['periodo']
            
            logger.info(f"\n{'─'*60}")
            logger.info(f"📦 Lote #{lote_id}")
            logger.info(f"   👤 Prestador: {prestador}")
            logger.info(f"   📅 Período: {periodo}")
            
            # Se não tem upload_hash, tentar usar id_controle como fallback
            if not upload_hash and id_controle:
                upload_hash = str(id_controle)
                logger.info(f"   ⚠️  Usando id_controle como hash (lote antigo)")
            
            if not upload_hash:
                logger.info(f"   ⚠️  Sem hash de upload - pulando")
                continue
            
            # Garantir que upload_hash é string
            upload_hash = str(upload_hash)
            logger.info(f"   🔑 Hash: {upload_hash[:20]}...")
            
            # Consultar status na API
            logger.info(f"   🔍 Consultando arquivos...")
            sucesso, dados, erro = client.consultar_e_processar(upload_hash)
            
            if not sucesso:
                logger.info(f"   ❌ Erro ao consultar: {erro}")
                erros += 1
                continue
            
            nota = dados['nota']
            arquivos = dados['arquivos']
            stats = dados['estatisticas']
            
            logger.info(f"   📊 Status: {nota['status_descricao']}")
            logger.info(f"   📁 Arquivos encontrados: {stats['total_arquivos']}")
            
            if len(arquivos) > 0:
                arquivos_encontrados += 1
                logger.info(f"   📦 Total: {stats['total_tamanho_formatado']}")
                
                # Verificar se já foi processado
                status_arquivo_atual = lote.get('status_arquivo', 0)
                ja_processado = status_arquivo_atual == 2
                
                if ja_processado:
                    logger.info(f"   ℹ️  Arquivos já foram baixados anteriormente")
                    continue
                
                # Verificar se já existe notificação
                with get_db_connection() as conn_check:
                    cur_check = conn_check.cursor()
                    cur_check.execute("SELECT COUNT(*) FROM notificacoes WHERE lote_id = %s", (lote_id,))
                    ja_tem_notificacao = cur_check.fetchone()[0] > 0
                
                if ja_tem_notificacao:
                    logger.info(f"   ℹ️  Notificação já existe para este lote")
                
                # Salvar informações no banco
                salvar_arquivos_nf(lote_id, arquivos, stats)
                logger.info(f"   ✅ Dados salvos no banco")
                
                # Baixar cada arquivo
                pasta_destino = f"uploads/lote_{lote_id}"
                os.makedirs(pasta_destino, exist_ok=True)
                
                for arquivo in arquivos:
                    nome_arquivo = arquivo['nome_original']
                    caminho_local = os.path.join(pasta_destino, nome_arquivo)
                    
                    if os.path.exists(caminho_local):
                        logger.info(f"   ✓ Já existe: {nome_arquivo}")
                        downloads_realizados += 1
                        continue
                    
                    logger.info(f"   ⬇️  Baixando: {nome_arquivo} ({arquivo['tamanho_formatado']})")
                    
                    sucesso_download, mensagem = client.baixar_arquivo(
                        arquivo['link_download'],
                        caminho_local
                    )
                    
                    if sucesso_download:
                        downloads_realizados += 1
                    else:
                        logger.info(f"      ❌ {mensagem}")
                        erros += 1
                
                # Atualizar status
                atualizar_status_arquivo(lote_id, 2)
                logger.info(f"   ✅ Status atualizado: Arquivos baixados")
                
                # Salvar nota fiscal
                primeiro_arquivo = os.path.join(pasta_destino, arquivos[0]['nome_original'])
                salvar_nota_fiscal(lote_id, primeiro_arquivo)
                logger.info(f"   ✅ Nota fiscal salva")
                
                # Criar notificação
                if not ja_tem_notificacao:
                    total_arqs = len(arquivos)
                    titulo = f"📥 Nota Fiscal Recebida - Lote #{lote_id}"
                    mensagem_notif = f"{prestador} enviou {total_arqs} arquivo(s) da nota fiscal ({stats['total_tamanho_formatado']})"
                    
                    criar_notificacao(
                        tipo='nf_recebida',
                        titulo=titulo,
                        mensagem=mensagem_notif,
                        lote_id=lote_id,
                        icone='📥',
                        prioridade=1
                    )
                    logger.info(f"   🔔 Notificação criada no banco")
                    
                    # Enviar notificação WebSocket em tempo real
                    enviar_notificacao_websocket_sync(
                        tipo="success",
                        titulo=titulo,
                        mensagem=mensagem_notif,
                        dados={
                            "lote_id": lote_id,
                            "tipo": "prestador",
                            "prestador": prestador,
                            "periodo": periodo,
                            "valor": lote.get('valor_total', 0),
                            "total_arquivos": total_arqs,
                            "tamanho_total": stats['total_tamanho_formatado'],
                            "nota_fiscal": primeiro_arquivo
                        }
                    )
                    logger.info(f"   📡 Notificação WebSocket enviada")
                    
                    # Enviar notificação WhatsApp
                    try:
                        from app.utils.whatsapp_automation import enviar_notificacao_whatsapp
                        
                        enviar_notificacao_whatsapp(
                            evento='nf_recebida_prestador',
                            destinatario_id=lote.get('prestador_id'),
                            tipo='prestador',
                            variaveis={
                                'nome_prestador': prestador,
                                'periodo': periodo,
                                'valor': str(lote.get('valor_total', 0)),
                                'numero_nf': arquivos[0]['nome_original'],
                                'data_recebimento': datetime.now().strftime('%d/%m/%Y')
                            }
                        )
                        logger.info(f"   📱 Notificação WhatsApp enviada")
                    except Exception as e:
                        logger.warning(f"   ⚠️  Erro ao enviar WhatsApp: {e}")
                
                # Integração Trello - tentar criar card (verificação está no serviço)
                try:
                    trello = TrelloIntegration()
                    if trello.is_configured():
                        logger.info(f"   📋 Criando card no Trello...")
                        
                        nota_fiscal = nota.get('numero_nota')
                        arquivos_baixados = [arq['nome_original'] for arq in arquivos]
                        arquivos_para_anexar = [os.path.join(pasta_destino, arq['nome_original']) for arq in arquivos]
                        valor_lote = lote.get('valor_total', 0)
                        
                        card_result = trello.criar_card_download(
                            lote_id=lote_id,
                            prestador_nome=prestador,
                            montador_nome=None,
                            arquivos_baixados=arquivos_baixados,
                            nota_fiscal=nota_fiscal,
                            arquivos_para_anexar=arquivos_para_anexar,
                            valor_lote=valor_lote
                        )
                        
                        if card_result:
                            logger.info(f"   ✅ Card Trello criado: {card_result['shortUrl']}")
                        else:
                            logger.info(f"   ℹ️  Card já existe ou não foi possível criar")
                    else:
                        logger.info(f"   ℹ️  Integração Trello não configurada")
                except Exception as e:
                    logger.info(f"   ⚠️  Erro ao criar card Trello: {e}")
            
            elif nota['link_valido']:
                logger.info(f"   ⏳ Aguardando upload do prestador")
                logger.info(f"   📅 Link válido por mais {nota['dias_restantes']} dia(s)")
            
            else:
                logger.info(f"   ⏰ Link expirado")
                atualizar_status_api(lote_id, 2)
            
            time.sleep(0.5)
        
        # ========================================
        # PROCESSAR ENVIOS DE MONTADORES
        # ========================================
        
        for envio in envios_montagem:
            envio_id = envio['id']
            upload_hash = envio.get('upload_hash')
            id_controle = envio.get('id_controle')
            montador = envio['montador_nome']
            periodo = envio['periodo']
            
            logger.info(f"\n{'─'*60}")
            logger.info(f"🔧 Envio Montagem #{envio_id}")
            logger.info(f"   👤 Montador: {montador}")
            logger.info(f"   📅 Período: {periodo}")
            
            # Se não tem upload_hash, tentar usar id_controle como fallback
            if not upload_hash and id_controle:
                upload_hash = str(id_controle)
                logger.info(f"   ⚠️  Usando id_controle como hash (envio antigo)")
            
            if not upload_hash:
                logger.info(f"   ⚠️  Sem hash de upload - pulando")
                continue
            
            # Garantir que upload_hash é string
            upload_hash = str(upload_hash)
            logger.info(f"   🔑 Hash: {upload_hash[:20]}...")
            
            # Consultar status na API
            logger.info(f"   🔍 Consultando arquivos...")
            sucesso, dados, erro = client.consultar_e_processar(upload_hash)
            
            if not sucesso:
                logger.info(f"   ❌ Erro ao consultar: {erro}")
                erros += 1
                continue
            
            nota = dados['nota']
            arquivos = dados['arquivos']
            stats = dados['estatisticas']
            
            logger.info(f"   📊 Status: {nota['status_descricao']}")
            logger.info(f"   📁 Arquivos encontrados: {stats['total_arquivos']}")
            
            if len(arquivos) > 0:
                arquivos_encontrados += 1
                logger.info(f"   📦 Total: {stats['total_tamanho_formatado']}")
                
                # Verificar se já foi processado
                status_arquivo_atual = envio.get('status_arquivo', 0)
                ja_processado = status_arquivo_atual == 2
                
                if ja_processado:
                    logger.info(f"   ℹ️  Arquivos já foram baixados anteriormente")
                    continue
                
                # Verificar se já existe notificação
                with get_db_connection() as conn_check:
                    cur_check = conn_check.cursor()
                    cur_check.execute("SELECT COUNT(*) FROM notificacoes WHERE envio_montagem_id = %s", (envio_id,))
                    ja_tem_notificacao = cur_check.fetchone()[0] > 0
                
                if ja_tem_notificacao:
                    logger.info(f"   ℹ️  Notificação já existe para este envio")
                
                # Salvar informações no banco
                salvar_arquivos_nf_montagem(envio_id, arquivos, stats)
                logger.info(f"   ✅ Dados salvos no banco")
                
                # Baixar cada arquivo
                pasta_destino = f"uploads/montagem_{envio_id}"
                os.makedirs(pasta_destino, exist_ok=True)
                
                for arquivo in arquivos:
                    nome_arquivo = arquivo['nome_original']
                    caminho_local = os.path.join(pasta_destino, nome_arquivo)
                    
                    if os.path.exists(caminho_local):
                        logger.info(f"   ✓ Já existe: {nome_arquivo}")
                        downloads_realizados += 1
                        continue
                    
                    logger.info(f"   ⬇️  Baixando: {nome_arquivo} ({arquivo['tamanho_formatado']})")
                    
                    sucesso_download, mensagem = client.baixar_arquivo(
                        arquivo['link_download'],
                        caminho_local
                    )
                    
                    if sucesso_download:
                        downloads_realizados += 1
                    else:
                        logger.info(f"      ❌ {mensagem}")
                        erros += 1
                
                # Atualizar status
                atualizar_status_arquivo_montagem(envio_id, 2)
                logger.info(f"   ✅ Status atualizado: Arquivos baixados")
                
                # Salvar nota fiscal
                primeiro_arquivo = os.path.join(pasta_destino, arquivos[0]['nome_original'])
                salvar_nota_fiscal_montagem(envio_id, primeiro_arquivo)
                logger.info(f"   ✅ Nota fiscal salva")
                
                # Criar notificação
                if not ja_tem_notificacao:
                    total_arqs = len(arquivos)
                    titulo = f"📥 Nota Fiscal Recebida - Montagem #{envio_id}"
                    mensagem_notif = f"{montador} enviou {total_arqs} arquivo(s) da nota fiscal ({stats['total_tamanho_formatado']})"
                    
                    criar_notificacao_montagem(
                        tipo='nf_recebida',
                        titulo=titulo,
                        mensagem=mensagem_notif,
                        envio_montagem_id=envio_id,
                        icone='📥',
                        prioridade=1
                    )
                    logger.info(f"   🔔 Notificação criada no banco")
                    
                    # Enviar notificação WebSocket em tempo real
                    enviar_notificacao_websocket_sync(
                        tipo="success",
                        titulo=titulo,
                        mensagem=mensagem_notif,
                        dados={
                            "envio_montagem_id": envio_id,
                            "tipo": "montador",
                            "montador": montador,
                            "periodo": periodo,
                            "valor": envio.get('valor_total', 0),
                            "total_arquivos": total_arqs,
                            "tamanho_total": stats['total_tamanho_formatado'],
                            "nota_fiscal": primeiro_arquivo
                        }
                    )
                    logger.info(f"   📡 Notificação WebSocket enviada")
                    
                    # Enviar notificação WhatsApp
                    try:
                        from app.utils.whatsapp_automation import enviar_notificacao_whatsapp
                        
                        enviar_notificacao_whatsapp(
                            evento='nf_recebida_montador',
                            destinatario_id=envio.get('montador_id'),
                            tipo='montador',
                            variaveis={
                                'nome_montador': montador,
                                'periodo': periodo,
                                'valor': str(envio.get('valor_total', 0)),
                                'numero_nf': arquivos[0]['nome_original'],
                                'data_recebimento': datetime.now().strftime('%d/%m/%Y')
                            }
                        )
                        logger.info(f"   � Notificação WhatsApp enviada")
                    except Exception as e:
                        logger.warning(f"   ⚠️  Erro ao enviar WhatsApp: {e}")
                
                # Integração Trello - tentar criar card (verificação está no serviço)
                try:
                    trello = TrelloIntegration()
                    if trello.is_configured():
                        logger.info(f"   � Criando card no Trello...")
                        
                        nota_fiscal = nota.get('numero_nota')
                        arquivos_baixados = [arq['nome_original'] for arq in arquivos]
                        arquivos_para_anexar = [os.path.join(pasta_destino, arq['nome_original']) for arq in arquivos]
                        valor_envio = envio.get('valor_total', 0)
                        
                        card_result = trello.criar_card_download(
                            lote_id=None,
                            prestador_nome=None,
                            montador_nome=montador,
                            arquivos_baixados=arquivos_baixados,
                            nota_fiscal=nota_fiscal,
                            arquivos_para_anexar=arquivos_para_anexar,
                            valor_lote=valor_envio,
                            envio_montagem_id=envio_id
                        )
                        
                        if card_result:
                            logger.info(f"   ✅ Card Trello criado: {card_result['shortUrl']}")
                        else:
                            logger.info(f"   ℹ️  Card já existe ou não foi possível criar")
                    else:
                        logger.info(f"   ℹ️  Integração Trello não configurada")
                except Exception as e:
                    logger.info(f"   ⚠️  Erro ao criar card Trello: {e}")
            
            elif nota['link_valido']:
                logger.info(f"   ⏳ Aguardando upload do montador")
                logger.info(f"   📅 Link válido por mais {nota['dias_restantes']} dia(s)")
            
            else:
                logger.info(f"   ⏰ Link expirado")
                atualizar_status_api_montagem(envio_id, 2)
            
            time.sleep(0.5)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ PROCESSAMENTO CONCLUÍDO")
        logger.info(f"   Total processados: {total_pendentes}")
        logger.info(f"   Arquivos encontrados: {arquivos_encontrados}")
        logger.info(f"   Downloads realizados: {downloads_realizados}")
        logger.info(f"   Erros: {erros}")
        logger.info(f"{'='*60}")
        
        return {
            'success': True,
            'total_processados': total_pendentes,
            'arquivos_encontrados': arquivos_encontrados,
            'downloads': downloads_realizados,
            'erros': erros
        }
    
    except Exception as e:
        logger.error(f"❌ Erro crítico no job: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # Permitir execução direta do script
    processar_uploads_pendentes()
