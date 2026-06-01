"""
Scheduler para execução automática de jobs
Usa APScheduler para agendar tarefas em intervalos configuráveis
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .database import get_db_connection

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Instância global do scheduler
scheduler = None


def criar_tabela_jobs_config():
    """Cria tabela de configuração de jobs se não existir"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs_config (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                descricao TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                intervalo_minutos INTEGER DEFAULT 60,
                ultima_execucao TIMESTAMP,
                proxima_execucao TIMESTAMP,
                total_execucoes INTEGER DEFAULT 0,
                total_erros INTEGER DEFAULT 0,
                ultima_mensagem TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inserir/atualizar job de consulta_notas (que inclui criação de cards Trello)
        cursor.execute("""
            INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos)
            VALUES ('consulta_notas', 'Consulta notas fiscais na API, baixa arquivos e cria cards no Trello (prestadores e montadores)', TRUE, 30)
            ON CONFLICT (nome) DO UPDATE SET
                descricao = 'Consulta notas fiscais na API, baixa arquivos e cria cards no Trello (prestadores e montadores)'
        """)
        
        # Desativar job separado de trello_montadores (se existir) - não deve ser usado
        cursor.execute("""
            UPDATE jobs_config SET ativo = FALSE, 
            descricao = 'DESATIVADO - Integração Trello agora faz parte do job consulta_notas'
            WHERE nome = 'trello_montadores'
        """)
        
        # Inserir/atualizar job de envio automático de montadores (só pré-aprovados)
        cursor.execute("""
            INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos)
            VALUES ('auto_envio_montadores', 'Envio automático APENAS de montadores pré-aprovados nos dias configurados', TRUE, 1440)
            ON CONFLICT (nome) DO UPDATE SET
                descricao = 'Envio automático APENAS de montadores pré-aprovados nos dias configurados',
                ativo = TRUE
        """)
        
        conn.commit()
        logger.info("✅ Tabela jobs_config criada/verificada")


def atualizar_estatisticas_job(nome: str, sucesso: bool, mensagem: str = None):
    """Atualiza estatísticas de execução do job"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if sucesso:
            cursor.execute("""
                UPDATE jobs_config
                SET 
                    total_execucoes = total_execucoes + 1,
                    ultima_execucao = %s,
                    ultima_mensagem = %s
                WHERE nome = %s
            """, (datetime.now(), mensagem, nome))
        else:
            cursor.execute("""
                UPDATE jobs_config
                SET 
                    total_execucoes = total_execucoes + 1,
                    total_erros = total_erros + 1,
                    ultima_execucao = %s,
                    ultima_mensagem = %s
                WHERE nome = %s
            """, (datetime.now(), mensagem, nome))
        
        conn.commit()


def executar_job_consulta_notas():
    """
    Executa job de consulta de notas fiscais.
    Este job:
    1. Busca lotes de prestadores e envios de montadores aguardando upload
    2. Consulta a API externa para verificar se há arquivos
    3. Baixa os arquivos quando disponíveis
    4. Cria cards no Trello com os anexos
    5. Envia notificações (WebSocket e WhatsApp)
    """
    logger.info("📋 Iniciando job: Consulta de Notas Fiscais")
    
    try:
        from app.jobs.consultar_notas import processar_uploads_pendentes
        
        resultado = processar_uploads_pendentes()
        
        # Tratar erros - pode ser int ou lista
        erros = resultado.get('erros', 0)
        if isinstance(erros, list):
            total_erros = len(erros)
        else:
            total_erros = erros
        
        mensagem = (
            f"Processados: {resultado.get('total_processados', 0)}, "
            f"Arquivos: {resultado.get('arquivos_encontrados', 0)}, "
            f"Downloads: {resultado.get('downloads', 0)}, "
            f"Erros: {total_erros}"
        )
        
        logger.info(f"✅ Job concluído: {mensagem}")
        atualizar_estatisticas_job('consulta_notas', True, mensagem)
        
        return resultado
        
    except Exception as e:
        mensagem = f"Erro: {str(e)}"
        logger.error(f"❌ Job falhou: {mensagem}")
        atualizar_estatisticas_job('consulta_notas', False, mensagem)
        raise


def carregar_configuracao_job(nome: str):
    """Carrega configuração de um job do banco"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ativo, intervalo_minutos
            FROM jobs_config
            WHERE nome = %s
        """, (nome,))
        
        row = cursor.fetchone()
        if row:
            return {
                'ativo': row[0],
                'intervalo_minutos': row[1]
            }
        return None


def configurar_jobs():
    """Configura todos os jobs no scheduler baseado nas configurações do banco"""
    global scheduler
    
    if scheduler is None:
        logger.error("❌ Scheduler não foi inicializado")
        return
    
    # Remover todos os jobs existentes
    scheduler.remove_all_jobs()
    logger.info("🧹 Jobs anteriores removidos")
    
    # Carregar configuração do job consulta_notas
    # Este job faz TUDO: consulta API, baixa arquivos, cria cards Trello
    config = carregar_configuracao_job('consulta_notas')
    
    if config and config['ativo']:
        intervalo = config['intervalo_minutos']
        
        scheduler.add_job(
            executar_job_consulta_notas,
            trigger=IntervalTrigger(minutes=intervalo),
            id='consulta_notas',
            name='Consulta Notas Fiscais + Trello',
            replace_existing=True,
            max_instances=1  # Evita execuções simultâneas
        )
        
        logger.info(f"✅ Job 'consulta_notas' agendado: intervalo de {intervalo} minutos")
    else:
        logger.info(f"⏸️  Job 'consulta_notas' desativado")

    # Job CRM WhatsApp: lembretes agendados + lembrete diário 13h
    crm_config = carregar_configuracao_job('crm_whatsapp_diario')
    if crm_config and crm_config['ativo']:
        crm_intervalo = crm_config['intervalo_minutos']
        from app.crm_whatsapp import executar_job_crm_whatsapp
        scheduler.add_job(
            executar_job_crm_whatsapp,
            trigger=IntervalTrigger(minutes=crm_intervalo),
            id='crm_whatsapp_diario',
            name='CRM WhatsApp Lembretes',
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"✅ Job 'crm_whatsapp_diario' agendado: intervalo de {crm_intervalo} minutos")
    else:
        logger.info(f"⏸️  Job 'crm_whatsapp_diario' desativado ou não configurado")

    # Job Envio Automático de Montadores (só pré-aprovados)
    auto_envio_config = carregar_configuracao_job('auto_envio_montadores')
    if auto_envio_config and auto_envio_config['ativo']:
        from app.services.auto_envio import processar_envios_pre_aprovados
        scheduler.add_job(
            processar_envios_pre_aprovados,
            trigger=IntervalTrigger(minutes=auto_envio_config['intervalo_minutos']),
            id='auto_envio_montadores',
            name='Envio Automático Montadores (Pré-aprovados)',
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"✅ Job 'auto_envio_montadores' agendado: a cada {auto_envio_config['intervalo_minutos']} min")
    else:
        logger.info(f"⏸️  Job 'auto_envio_montadores' desativado ou não configurado")

    # Job Alertas Montagem 24h: novos tickets, retomada standby, prazo 4h, prazo vencido
    alertas_config = carregar_configuracao_job('alertas_montagem_whatsapp')
    if alertas_config and alertas_config['ativo']:
        alertas_intervalo = alertas_config['intervalo_minutos']

        def _executar_alertas_montagem_wrap():
            try:
                from app.jobs.alertas_montagem import executar_alertas_montagem
                resultado = executar_alertas_montagem()
                mensagem = (
                    f"analisados={resultado.get('itens_analisados', 0)}, "
                    f"novos={resultado.get('novo_ticket', 0)}, "
                    f"retomadas={resultado.get('retomada', 0)}, "
                    f"4h={resultado.get('prazo_4h', 0)}, "
                    f"vencidos={resultado.get('prazo_vencido', 0)}, "
                    f"erros={resultado.get('erros', 0)}"
                )
                atualizar_estatisticas_job('alertas_montagem_whatsapp', True, mensagem)
            except Exception as e:
                logger.error(f"❌ Job 'alertas_montagem_whatsapp' falhou: {e}")
                atualizar_estatisticas_job('alertas_montagem_whatsapp', False, f"Erro: {e}")

        scheduler.add_job(
            _executar_alertas_montagem_wrap,
            trigger=IntervalTrigger(minutes=alertas_intervalo),
            id='alertas_montagem_whatsapp',
            name='Alertas WhatsApp Montagem 24h',
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"✅ Job 'alertas_montagem_whatsapp' agendado: intervalo de {alertas_intervalo} minutos")
    else:
        logger.info(f"⏸️  Job 'alertas_montagem_whatsapp' desativado ou não configurado")

    # Job Lembretes Montagem 24h: dispara WhatsApp e alimenta o chat
    lembretes_config = carregar_configuracao_job('lembretes_montagem_whatsapp')
    if lembretes_config and lembretes_config['ativo']:
        lembretes_intervalo = lembretes_config['intervalo_minutos']

        def _executar_lembretes_montagem_wrap():
            try:
                from app.utils.montagem_whatsapp import processar_lembretes_pendentes
                enviados = processar_lembretes_pendentes()
                atualizar_estatisticas_job(
                    'lembretes_montagem_whatsapp', True, f"enviados={enviados}"
                )
            except Exception as e:
                logger.error(f"❌ Job 'lembretes_montagem_whatsapp' falhou: {e}")
                atualizar_estatisticas_job('lembretes_montagem_whatsapp', False, f"Erro: {e}")

        scheduler.add_job(
            _executar_lembretes_montagem_wrap,
            trigger=IntervalTrigger(minutes=lembretes_intervalo),
            id='lembretes_montagem_whatsapp',
            name='Lembretes WhatsApp Montagem 24h',
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"✅ Job 'lembretes_montagem_whatsapp' agendado: intervalo de {lembretes_intervalo} minutos")
    else:
        logger.info(f"⏸️  Job 'lembretes_montagem_whatsapp' desativado ou não configurado")


def iniciar_scheduler():
    """Inicia o scheduler"""
    global scheduler
    
    try:
        # Criar tabela se não existir
        criar_tabela_jobs_config()
        
        # Criar scheduler
        scheduler = BackgroundScheduler(
            daemon=False,
            timezone='America/Sao_Paulo'
        )
        
        # Configurar jobs
        configurar_jobs()
        
        # Iniciar scheduler
        scheduler.start()
        
        logger.info("🚀 Scheduler iniciado com sucesso")
        logger.info(f"📋 Jobs agendados: {len(scheduler.get_jobs())}")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar scheduler: {e}")
        raise


def parar_scheduler():
    """Para o scheduler graciosamente"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=True)
        logger.info("🛑 Scheduler parado")


def recarregar_scheduler():
    """Recarrega configurações do scheduler"""
    logger.info("🔄 Recarregando configurações...")
    configurar_jobs()
    logger.info("✅ Configurações recarregadas")


def obter_status_scheduler():
    """Retorna status atual do scheduler"""
    global scheduler
    
    if scheduler is None:
        return {
            'running': False,
            'jobs': []
        }
    
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        'running': scheduler.running,
        'jobs': jobs_info
    }
