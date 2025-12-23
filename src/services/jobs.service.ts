import { apiClient } from './api';

export interface JobStatus {
  consulta_notas: {
    running: boolean;
    last_run: string | null;
    last_result: {
      total_processados: number;
      arquivos_encontrados: number;
      downloads: number;
      erros: number;
    } | null;
    error: string | null;
  };
}

export interface JobResult {
  status: string;
  last_run: string | null;
  result: {
    total_processados: number;
    arquivos_encontrados: number;
    downloads: number;
    erros: number;
  } | null;
  error: string | null;
}

export interface JobConfig {
  id: number;
  nome: string;
  descricao: string;
  ativo: boolean;
  intervalo_minutos: number;
  ultima_execucao: string | null;
  proxima_execucao: string | null;
  total_execucoes: number;
  total_erros: number;
  ultima_mensagem: string | null;
}

export interface SchedulerStatus {
  running: boolean;
  pid: number | null;
}

export const jobsService = {
  // Status dos jobs em execução
  async getStatus(): Promise<JobStatus> {
    const response = await apiClient.get<JobStatus>('/jobs/status');
    return response;
  },

  // Executar job de consulta de notas manualmente
  async executarConsultaNotas() {
    const response = await apiClient.post<any>('/jobs/consulta-notas/executar');
    return response;
  },

  // Obter resultado do último job
  async getResultadoConsultaNotas(): Promise<JobResult> {
    const response = await apiClient.get<JobResult>('/jobs/consulta-notas/resultado');
    return response;
  },

  // Configurações de jobs
  async getJobsConfig(): Promise<JobConfig[]> {
    const response = await apiClient.get<JobConfig[]>('/jobs/config');
    return response;
  },

  async updateJobConfig(jobName: string, data: { ativo: boolean; intervalo_minutos: number }) {
    const response = await apiClient.put<any>(`/jobs/config/${jobName}`, data);
    return response;
  },

  // Scheduler (processo externo)
  async getSchedulerStatus(): Promise<SchedulerStatus> {
    const response = await apiClient.get('/jobs/scheduler/status') as { data: SchedulerStatus };
    return response.data;
  },

  async startScheduler() {
    const response = await apiClient.post('/jobs/scheduler/start') as { data: any };
    return response.data;
  },

  async stopScheduler() {
    const response = await apiClient.post('/jobs/scheduler/stop') as { data: any };
    return response.data;
  },

  async reloadScheduler() {
    const response = await apiClient.post('/jobs/scheduler/reload') as { data: any };
    return response.data;
  },

  async getLogs(): Promise<{ logs: string }> {
    const response = await apiClient.get('/jobs/logs') as { data: { logs: string } };
    return response.data;
  },

  // Trello Montadores
  async executarTrelloMontadores() {
    const response = await apiClient.post<any>('/jobs/trello-montadores/executar');
    return response;
  },

  async getResultadoTrelloMontadores(): Promise<JobResult> {
    const response = await apiClient.get<JobResult>('/jobs/trello-montadores/resultado');
    return response;
  },

  // Histórico de execuções
  async getExecutions(jobName?: string, limit: number = 20): Promise<{ total: number; executions: JobExecution[] }> {
    const params = new URLSearchParams();
    if (jobName) params.append('job_name', jobName);
    params.append('limit', limit.toString());
    const response = await apiClient.get<{ total: number; executions: JobExecution[] }>(`/jobs/executions?${params}`);
    return response;
  },

  async getExecutionStats(jobName: string): Promise<JobExecutionStats> {
    const response = await apiClient.get<JobExecutionStats>(`/jobs/executions/stats/${jobName}`);
    return response;
  },

  async cleanupHistory(dias: number = 30): Promise<{ success: boolean; removidos: number }> {
    const response = await apiClient.delete<{ success: boolean; removidos: number }>(`/jobs/executions/cleanup?dias=${dias}`);
    return response;
  }
};

// Tipos para histórico de execuções
export interface JobExecution {
  id: number;
  job_name: string;
  status: 'running' | 'completed' | 'error' | 'cancelled';
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  result: Record<string, any> | null;
  error: string | null;
}

export interface JobExecutionStats {
  job_name: string;
  total_execucoes: number;
  total_sucesso: number;
  total_erros: number;
  taxa_sucesso: number;
  tempo_medio_segundos: number;
  ultima_execucao: {
    data: string;
    status: string;
    duracao: number;
  } | null;
}