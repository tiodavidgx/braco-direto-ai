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
    const response = await apiClient.get('/jobs/status') as { data: JobStatus };
    return response.data;
  },

  // Executar job de consulta de notas manualmente
  async executarConsultaNotas() {
    const response = await apiClient.post('/jobs/consulta-notas/executar') as { data: any };
    return response.data;
  },

  // Obter resultado do último job
  async getResultadoConsultaNotas(): Promise<JobResult> {
    const response = await apiClient.get('/jobs/consulta-notas/resultado') as { data: JobResult };
    return response.data;
  },

  // Configurações de jobs
  async getJobs(): Promise<JobConfig[]> {
    const response = await apiClient.get('/jobs/config') as { data: JobConfig[] };
    return response.data;
  },

  async updateJob(jobName: string, data: { ativo: boolean; intervalo_minutos: number }) {
    const response = await apiClient.put(`/jobs/config/${jobName}`, data) as { data: any };
    return response.data;
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
};
