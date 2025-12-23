"""
Utilitários para gerenciar histórico de execuções de jobs
Persiste logs e resultados no banco de dados
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import json
from app.database import get_db_connection

logger = logging.getLogger('JobExecution')


class JobExecutionManager:
    """
    Gerencia o ciclo de vida de execuções de jobs
    Persiste no banco de dados para histórico
    """
    
    @staticmethod
    def iniciar_execucao(job_name: str) -> int:
        """
        Registra início de uma execução de job
        
        Args:
            job_name: Nome do job (ex: 'consulta_notas', 'trello_montadores')
            
        Returns:
            ID da execução criada
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                # Garantir que a tabela existe
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS job_executions (
                        id SERIAL PRIMARY KEY,
                        job_name VARCHAR(100) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'running',
                        started_at TIMESTAMP DEFAULT NOW(),
                        finished_at TIMESTAMP,
                        duration_seconds INTEGER,
                        result JSONB,
                        error TEXT,
                        logs TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Criar índices se não existirem
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_job_executions_name 
                    ON job_executions(job_name)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_job_executions_started 
                    ON job_executions(started_at DESC)
                """)
                
                # Inserir nova execução
                cur.execute("""
                    INSERT INTO job_executions (job_name, status, started_at)
                    VALUES (%s, 'running', NOW())
                    RETURNING id
                """, (job_name,))
                
                execution_id = cur.fetchone()[0]
                conn.commit()
                
                logger.info(f"Execução #{execution_id} iniciada para job '{job_name}'")
                return execution_id
                
        except Exception as e:
            logger.error(f"Erro ao iniciar execução: {e}")
            return -1
    
    @staticmethod
    def finalizar_execucao(
        execution_id: int,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        logs: Optional[str] = None
    ) -> bool:
        """
        Finaliza uma execução de job
        
        Args:
            execution_id: ID da execução
            status: 'completed', 'error', 'cancelled'
            result: Dicionário com resultado (será salvo como JSON)
            error: Mensagem de erro se houver
            logs: Logs completos da execução
            
        Returns:
            True se atualizado com sucesso
        """
        if execution_id < 0:
            return False
            
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    UPDATE job_executions
                    SET 
                        status = %s,
                        finished_at = NOW(),
                        duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER,
                        result = %s,
                        error = %s,
                        logs = %s
                    WHERE id = %s
                """, (
                    status,
                    json.dumps(result) if result else None,
                    error,
                    logs,
                    execution_id
                ))
                
                conn.commit()
                logger.info(f"Execução #{execution_id} finalizada com status '{status}'")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao finalizar execução: {e}")
            return False
    
    @staticmethod
    def obter_ultimas_execucoes(job_name: Optional[str] = None, limit: int = 10) -> list:
        """
        Obtém as últimas execuções de jobs
        
        Args:
            job_name: Filtrar por nome do job (None = todos)
            limit: Quantidade máxima de registros
            
        Returns:
            Lista de execuções
        """
        try:
            with get_db_connection() as conn:
                import psycopg2.extras
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                if job_name:
                    cur.execute("""
                        SELECT 
                            id,
                            job_name,
                            status,
                            started_at,
                            finished_at,
                            duration_seconds,
                            result,
                            error
                        FROM job_executions
                        WHERE job_name = %s
                        ORDER BY started_at DESC
                        LIMIT %s
                    """, (job_name, limit))
                else:
                    cur.execute("""
                        SELECT 
                            id,
                            job_name,
                            status,
                            started_at,
                            finished_at,
                            duration_seconds,
                            result,
                            error
                        FROM job_executions
                        ORDER BY started_at DESC
                        LIMIT %s
                    """, (limit,))
                
                return list(cur.fetchall())
                
        except Exception as e:
            logger.error(f"Erro ao obter execuções: {e}")
            return []
    
    @staticmethod
    def obter_estatisticas(job_name: str) -> Dict[str, Any]:
        """
        Obtém estatísticas de um job
        
        Args:
            job_name: Nome do job
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                # Total de execuções
                cur.execute("""
                    SELECT COUNT(*) FROM job_executions WHERE job_name = %s
                """, (job_name,))
                total = cur.fetchone()[0]
                
                # Execuções com sucesso
                cur.execute("""
                    SELECT COUNT(*) FROM job_executions 
                    WHERE job_name = %s AND status = 'completed'
                """, (job_name,))
                sucesso = cur.fetchone()[0]
                
                # Execuções com erro
                cur.execute("""
                    SELECT COUNT(*) FROM job_executions 
                    WHERE job_name = %s AND status = 'error'
                """, (job_name,))
                erros = cur.fetchone()[0]
                
                # Tempo médio de execução
                cur.execute("""
                    SELECT AVG(duration_seconds) FROM job_executions 
                    WHERE job_name = %s AND status = 'completed' AND duration_seconds IS NOT NULL
                """, (job_name,))
                tempo_medio = cur.fetchone()[0] or 0
                
                # Última execução
                cur.execute("""
                    SELECT started_at, status, duration_seconds 
                    FROM job_executions 
                    WHERE job_name = %s 
                    ORDER BY started_at DESC 
                    LIMIT 1
                """, (job_name,))
                ultima = cur.fetchone()
                
                return {
                    'job_name': job_name,
                    'total_execucoes': total,
                    'total_sucesso': sucesso,
                    'total_erros': erros,
                    'taxa_sucesso': round((sucesso / total * 100) if total > 0 else 100, 1),
                    'tempo_medio_segundos': round(tempo_medio, 1),
                    'ultima_execucao': {
                        'data': ultima[0].isoformat() if ultima else None,
                        'status': ultima[1] if ultima else None,
                        'duracao': ultima[2] if ultima else None
                    } if ultima else None
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'job_name': job_name,
                'total_execucoes': 0,
                'total_sucesso': 0,
                'total_erros': 0,
                'taxa_sucesso': 100,
                'tempo_medio_segundos': 0,
                'ultima_execucao': None
            }
    
    @staticmethod
    def limpar_historico(dias: int = 30) -> int:
        """
        Remove execuções antigas do histórico
        
        Args:
            dias: Manter apenas execuções dos últimos N dias
            
        Returns:
            Quantidade de registros removidos
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    DELETE FROM job_executions
                    WHERE started_at < NOW() - INTERVAL '%s days'
                    RETURNING id
                """, (dias,))
                
                removidos = cur.rowcount
                conn.commit()
                
                logger.info(f"Removidos {removidos} registros antigos do histórico")
                return removidos
                
        except Exception as e:
            logger.error(f"Erro ao limpar histórico: {e}")
            return 0


# Instância global para uso fácil
job_execution_manager = JobExecutionManager()
