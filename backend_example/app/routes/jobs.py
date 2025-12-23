"""
Rotas para gerenciar Jobs e tarefas agendadas
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import threading
import logging
from datetime import datetime
from pathlib import Path
import os
import signal
import subprocess
from ..database import get_db_connection
from ..utils.job_execution import job_execution_manager

router = APIRouter()

# Logger para jobs
logger = logging.getLogger('JobsRouter')

# Estado dos jobs em execução (em memória - para status em tempo real)
job_status = {
    'consulta_notas': {
        'running': False,
        'last_run': None,
        'last_result': None,
        'error': None,
        'execution_id': None
    },
    'trello_montadores': {
        'running': False,
        'last_run': None,
        'last_result': None,
        'error': None,
        'execution_id': None
    }
}


class JobUpdate(BaseModel):
    ativo: bool
    intervalo_minutos: int


# ===== ENDPOINTS PARA EXECUÇÃO MANUAL DE JOBS =====

@router.get("/status")
async def get_jobs_status():
    """Retorna status de todos os jobs em execução"""
    # Status do scheduler integrado
    try:
        from app.scheduler import obter_status_scheduler
        scheduler_status = obter_status_scheduler()
    except:
        scheduler_status = {'running': False, 'jobs': []}
    
    return {
        'manual_execution': job_status,
        'scheduler': scheduler_status
    }


@router.post("/consulta-notas/executar")
async def executar_job_consulta_notas():
    """Executa o job de consulta de notas fiscais manualmente"""
    
    if job_status['consulta_notas']['running']:
        raise HTTPException(status_code=409, detail="Job já está em execução")
    
    try:
        # Executar em thread separada
        def run_job():
            from app.jobs.consultar_notas import processar_uploads_pendentes
            import io
            import sys
            
            # Registrar início no banco
            execution_id = job_execution_manager.iniciar_execucao('consulta_notas')
            job_status['consulta_notas']['execution_id'] = execution_id
            job_status['consulta_notas']['running'] = True
            job_status['consulta_notas']['error'] = None
            
            # Capturar logs
            log_buffer = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = log_buffer
            
            try:
                result = processar_uploads_pendentes()
                job_status['consulta_notas']['last_result'] = result
                job_status['consulta_notas']['last_run'] = datetime.now().isoformat()
                
                # Salvar no banco
                sys.stdout = old_stdout
                logs = log_buffer.getvalue()
                
                job_execution_manager.finalizar_execucao(
                    execution_id=execution_id,
                    status='completed' if result.get('success') else 'error',
                    result=result,
                    logs=logs
                )
                
            except Exception as e:
                sys.stdout = old_stdout
                logs = log_buffer.getvalue()
                error_msg = str(e)
                
                job_status['consulta_notas']['error'] = error_msg
                job_execution_manager.finalizar_execucao(
                    execution_id=execution_id,
                    status='error',
                    error=error_msg,
                    logs=logs
                )
                logger.error(f"Erro no job consulta_notas: {e}")
            finally:
                job_status['consulta_notas']['running'] = False
        
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "message": "Job iniciado com sucesso",
            "status": "running"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar job: {str(e)}")


@router.get("/consulta-notas/resultado")
async def get_resultado_consulta_notas():
    """Retorna o resultado do último job executado"""
    
    status = job_status['consulta_notas']
    
    if not status['last_run'] and not status['running']:
        return {
            "status": "never_run",
            "message": "Job nunca foi executado"
        }
    
    return {
        "status": "running" if status['running'] else "completed",
        "last_run": status['last_run'],
        "result": status['last_result'],
        "error": status['error'],
        "execution_id": status.get('execution_id')
    }


# ===== ENDPOINTS PARA HISTÓRICO DE EXECUÇÕES =====

@router.get("/executions")
async def get_job_executions(job_name: Optional[str] = None, limit: int = 20):
    """
    Retorna histórico de execuções de jobs
    
    Args:
        job_name: Filtrar por nome do job (opcional)
        limit: Quantidade máxima de registros (padrão: 20)
    """
    executions = job_execution_manager.obter_ultimas_execucoes(job_name, limit)
    return {
        "total": len(executions),
        "executions": executions
    }


@router.get("/executions/stats/{job_name}")
async def get_job_stats(job_name: str):
    """Retorna estatísticas de um job específico"""
    stats = job_execution_manager.obter_estatisticas(job_name)
    return stats


@router.delete("/executions/cleanup")
async def cleanup_job_history(dias: int = 30):
    """
    Remove execuções antigas do histórico
    
    Args:
        dias: Manter apenas execuções dos últimos N dias (padrão: 30)
    """
    removidos = job_execution_manager.limpar_historico(dias)
    return {
        "success": True,
        "removidos": removidos,
        "message": f"Removidos {removidos} registros com mais de {dias} dias"
    }


# ===== ENDPOINTS PARA SCHEDULER (processo externo) =====

@router.get("/scheduler/status")
def get_scheduler_status():
    """Verifica status do serviço scheduler"""
    pid_file = Path('scheduler.pid')
    
    if not pid_file.exists():
        return {"running": False, "pid": None}
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Verificar se processo existe
        try:
            os.kill(pid, 0)
            return {"running": True, "pid": pid}
        except OSError:
            # Processo não existe, remover arquivo PID
            try:
                pid_file.unlink()
            except:
                pass
            return {"running": False, "pid": None}
    except Exception as e:
        return {"running": False, "pid": None, "error": str(e)}


@router.post("/scheduler/start")
def start_scheduler():
    """Inicia o serviço scheduler"""
    pid_file = Path('scheduler.pid')
    
    # Verificar se já está rodando
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                raise HTTPException(status_code=400, detail="Serviço já está rodando")
            except OSError:
                pid_file.unlink()
        except:
            pass
    
    try:
        # Caminho para o script scheduler
        scheduler_path = Path(__file__).parent.parent.parent / 'run_scheduler.py'
        
        if not scheduler_path.exists():
            raise HTTPException(status_code=404, detail="Script scheduler não encontrado")
        
        # Iniciar processo em background
        processo = subprocess.Popen(
            ['python', str(scheduler_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        return {
            "message": "Serviço iniciado",
            "pid": processo.pid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
def stop_scheduler():
    """Para o serviço scheduler"""
    pid_file = Path('scheduler.pid')
    
    if not pid_file.exists():
        raise HTTPException(status_code=400, detail="Serviço não está rodando")
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Tentar parar graciosamente
        try:
            os.kill(pid, signal.SIGTERM)
            
            # Aguardar um pouco
            import time
            time.sleep(2)
            
            # Verificar se parou
            try:
                os.kill(pid, 0)
                # Ainda rodando, forçar
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            except OSError:
                pass  # Já parou
        except OSError:
            pass  # Processo não existe
        
        # Remover arquivo PID
        if pid_file.exists():
            pid_file.unlink()
        
        return {"message": "Serviço parado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/reload")
def reload_scheduler():
    """Recarrega configurações do scheduler"""
    pid_file = Path('scheduler.pid')
    
    if not pid_file.exists():
        raise HTTPException(status_code=400, detail="Serviço não está rodando")
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Enviar sinal SIGHUP para recarregar
        os.kill(pid, signal.SIGHUP)
        
        return {"message": "Configurações recarregadas"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== ENDPOINTS PARA CONFIGURAÇÃO DE JOBS =====

@router.get("/config")
def get_jobs_config():
    """Lista configurações de todos os jobs"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Criar tabela se não existir
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
        
        cursor.execute("""
            SELECT 
                id,
                nome,
                descricao,
                ativo,
                intervalo_minutos,
                ultima_execucao,
                proxima_execucao,
                total_execucoes,
                total_erros,
                ultima_mensagem
            FROM jobs_config
            ORDER BY nome
        """)
        
        jobs = []
        for row in cursor.fetchall():
            jobs.append({
                "id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "ativo": row[3],
                "intervalo_minutos": row[4],
                "ultima_execucao": row[5].isoformat() if row[5] else None,
                "proxima_execucao": row[6].isoformat() if row[6] else None,
                "total_execucoes": row[7],
                "total_erros": row[8],
                "ultima_mensagem": row[9]
            })
        
        return jobs


@router.put("/config/{job_name}")
def update_job_config(job_name: str, update: JobUpdate):
    """Atualiza configuração de um job"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE jobs_config
            SET ativo = %s, intervalo_minutos = %s
            WHERE nome = %s
        """, (update.ativo, update.intervalo_minutos, job_name))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        conn.commit()
    
    # Recarregar scheduler para aplicar mudanças
    try:
        from app.scheduler import recarregar_scheduler
        recarregar_scheduler()
    except Exception as e:
        print(f"Erro ao recarregar scheduler: {e}")
    
    return {"message": "Configuração atualizada"}


@router.get("/logs")
def get_scheduler_logs():
    """Retorna logs recentes do scheduler"""
    log_file = Path('scheduler.log')
    
    if not log_file.exists():
        return {"logs": ""}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Últimas 50 linhas
            recent_lines = lines[-50:]
            return {"logs": "".join(recent_lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== JOB TRELLO MONTADORES =====

@router.post("/trello-montadores/executar")
async def executar_job_trello_montadores():
    """Executa o job de criar cards Trello para montadores"""
    
    if job_status['trello_montadores']['running']:
        raise HTTPException(status_code=409, detail="Job já está em execução")
    
    try:
        # Executar em thread separada
        def run_job():
            import subprocess
            from pathlib import Path
            
            job_status['trello_montadores']['running'] = True
            job_status['trello_montadores']['error'] = None
            
            try:
                script_path = Path(__file__).parent.parent.parent.parent / "sistema_original" / "criar_cards_trello_montadores.py"
                
                result = subprocess.run(
                    ["python3", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutos
                )
                
                job_status['trello_montadores']['last_result'] = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode,
                    'success': result.returncode == 0
                }
                job_status['trello_montadores']['last_run'] = datetime.now().isoformat()
            except Exception as e:
                job_status['trello_montadores']['error'] = str(e)
            finally:
                job_status['trello_montadores']['running'] = False
        
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "message": "Job iniciado com sucesso",
            "status": "running"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar job: {str(e)}")


@router.get("/trello-montadores/resultado")
async def get_resultado_trello_montadores():
    """Retorna o resultado do último job executado"""
    
    status = job_status['trello_montadores']
    
    if not status['last_run'] and not status['running']:
        return {
            "status": "never_run",
            "message": "Job nunca foi executado"
        }
    
    return {
        "status": "running" if status['running'] else "completed",
        "last_run": status['last_run'],
        "result": status['last_result'],
        "error": status['error']
    }

