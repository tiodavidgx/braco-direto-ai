import { apiClient } from './api';

export const jobsService = {
  async getStatus() {
    return apiClient.get('/jobs/status');
  },

  async startService() {
    return apiClient.post('/jobs/start');
  },

  async stopService() {
    return apiClient.post('/jobs/stop');
  },

  async reloadService() {
    return apiClient.post('/jobs/reload');
  },

  async getJobs() {
    return apiClient.get('/jobs/config');
  },

  async updateJob(jobName: string, data: { ativo: boolean; intervalo_minutos: number }) {
    return apiClient.put(`/jobs/config/${jobName}`, data);
  },

  async getLogs() {
    return apiClient.get('/jobs/logs');
  },
};
