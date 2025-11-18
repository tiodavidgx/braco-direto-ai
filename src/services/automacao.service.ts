import { apiClient } from './api';

export const automacaoService = {
  // Templates (agora usando endpoints do WhatsApp)
  async getTemplates() {
    return apiClient.get('/whatsapp/templates');
  },

  async createTemplate(data: any) {
    return apiClient.post('/whatsapp/templates', data);
  },

  async updateTemplate(id: string, data: any) {
    return apiClient.put(`/whatsapp/templates/${id}`, data);
  },

  async deleteTemplate(id: string) {
    return apiClient.delete(`/whatsapp/templates/${id}`);
  },

  // Automações/Triggers (agora usando endpoints do WhatsApp)
  async getTriggers() {
    return apiClient.get('/whatsapp/automacoes');
  },

  async saveTrigger(data: any) {
    return apiClient.post('/whatsapp/automacoes', data);
  },

  async updateTrigger(id: string, data: any) {
    return apiClient.put(`/whatsapp/automacoes/${id}`, data);
  },

  async deleteTrigger(id: string) {
    return apiClient.delete(`/whatsapp/automacoes/${id}`);
  },

  // Histórico
  async getHistorico(limit = 100) {
    return apiClient.get('/whatsapp/notificacoes', { limit });
  },
};
