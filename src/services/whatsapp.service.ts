import { apiClient } from './api';

export const whatsappService = {
  async getStatus() {
    return apiClient.get('/whatsapp/status');
  },

  async getInfo() {
    return apiClient.get('/whatsapp/info');
  },

  async sendMessage(number: string, message: string) {
    return apiClient.post('/whatsapp/send', { number, message });
  },

  async sendBulk(numbers: string[], message: string, delay: number) {
    return apiClient.post('/whatsapp/send-bulk', { numbers, message, delay });
  },
};
