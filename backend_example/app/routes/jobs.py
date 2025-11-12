"""
Rotas para gerenciar Jobs e tarefas agendadas
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import threading
from datetime import datetime
from pathlib import Path
import os
import signal
import subprocess
from ..database import get_db_connection

router = APIRouter()

# Estado dos jobs em execução (em memória)
job_status = {
    'consulta_notas': {
        'running': False,
        'last_run': None,
        'last_result': None,
        'error': None
    }
}


class JobUpdate(BaseModel):
    ativo: bool
    intervalo_minutos: int


# ===== ENDPOINTS PARA EXECUÇÃO MANUAL DE JOBS =====

@router.get("/status")
async def get_jobs_status():
    """Retorna status de todos os jobs em execução"""
    return job_status


@router.post("/consulta-notas/executar")
async def executar_job_consulta_notas():
    """Executa o job de consulta de notas fiscais manualmente"""
    
    if job_status['consulta_notas']['running']:
        raise HTTPException(status_code=409, detail="Job já está em execução")
    
    try:
        # Executar em thread separada
        def run_job():
            from app.jobs.consultar_notas import processar_uploads_pendentes
            
            job_status['consulta_notas']['running'] = True
            job_status['consulta_notas']['error'] = None
            
            try:
                result = processar_uploads_pendentes()
                job_status['consulta_notas']['last_result'] = result
                job_status['consulta_notas']['last_run'] = datetime.now().isoformat()
            except Exception as e:
                job_status['consulta_notas']['error'] = str(e)
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
        "error": status['error']
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
            log_text = ''.join(recent_lines)
        
        return {"logs": log_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
