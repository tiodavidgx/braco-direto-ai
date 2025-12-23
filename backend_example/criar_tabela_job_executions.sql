-- Criar tabela para persistir histórico de execuções de jobs
-- Execute com: psql -U usuario -d database -f criar_tabela_job_executions.sql

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
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_job_executions_name ON job_executions(job_name);
CREATE INDEX IF NOT EXISTS idx_job_executions_status ON job_executions(status);
CREATE INDEX IF NOT EXISTS idx_job_executions_started ON job_executions(started_at DESC);

-- Comentários
COMMENT ON TABLE job_executions IS 'Histórico de execuções de jobs do sistema';
COMMENT ON COLUMN job_executions.status IS 'running, completed, error, cancelled';
COMMENT ON COLUMN job_executions.result IS 'Resultado da execução em JSON (estatísticas, contadores, etc)';
COMMENT ON COLUMN job_executions.logs IS 'Logs completos da execução';
