import { apiClient } from './api';

export const automacaoService = {
  async getTemplates() {
    return apiClient.get('/automacao/templates');
  },

  async createTemplate(data: any) {
    return apiClient.post('/automacao/templates', data);
  },

  async updateTemplate(id: string, data: any) {
    return apiClient.put(`/automacao/templates/${id}`, data);
  },

  async deleteTemplate(id: string) {
    return apiClient.delete(`/automacao/templates/${id}`);
  },

  async getTriggers() {
    return apiClient.get('/automacao/triggers');
  },

  async saveTrigger(data: any) {
    return apiClient.post('/automacao/triggers', data);
  },
};
