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
        
        # Inserir job padrão se não existir
        cursor.execute("""
            INSERT INTO jobs_config (nome, descricao, ativo, intervalo_minutos)
            VALUES ('consulta_notas', 'Consulta notas fiscais na API e cria cards no Trello', TRUE, 60)
            ON CONFLICT (nome) DO NOTHING
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
    """Função que será executada pelo scheduler"""
    logger.info("🔄 Iniciando job de consulta de notas...")
    
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
    config = carregar_configuracao_job('consulta_notas')
    
    if config and config['ativo']:
        intervalo = config['intervalo_minutos']
        
        scheduler.add_job(
            executar_job_consulta_notas,
            trigger=IntervalTrigger(minutes=intervalo),
            id='consulta_notas',
            name='Consulta Notas Fiscais',
            replace_existing=True,
            max_instances=1  # Evita execuções simultâneas
        )
        
        logger.info(f"✅ Job 'consulta_notas' agendado: intervalo de {intervalo} minutos")
    else:
        logger.info("⏸️  Job 'consulta_notas' está desativado")


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
