import { apiClient } from './api';

export interface Template {
  id: number;
  nome: string;
  tipo: string;
  template: string;
  variaveis?: string;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface Automacao {
  id: number;
  evento: string;
  template_id: string;
  template_nome?: string;
  condicoes?: string;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface Notificacao {
  id: number;
  prestador_id?: number;
  montador_id?: number;
  prestador_nome?: string;
  montador_nome?: string;
  tipo: string;
  mensagem: string;
  status: string;
  data_envio: string;
  erro?: string;
  metadata?: any;
}

export const whatsappService = {
  // Conexão e envio
  async getStatus() {
    const status: any = await apiClient.get('/whatsapp/status');
    
    // Se tem QR Code disponível, buscar o QR Code
    if (status.hasQrCode) {
      try {
        const qrData: any = await apiClient.get('/whatsapp/qr');
        if (qrData.qr_code) {
          status.qrCode = qrData.qr_code;
        }
      } catch (e) {
        console.error('Erro ao buscar QR Code:', e);
      }
    }
    
    return status;
  },

  async getQrCode() {
    return apiClient.get('/whatsapp/qr');
  },

  async getInfo() {
    return apiClient.get('/whatsapp/info');
  },

  async startServer() {
    return apiClient.post('/whatsapp/start-server');
  },

  async stopServer() {
    return apiClient.post('/whatsapp/stop-server');
  },

  async sendMessage(number: string, message: string) {
    return apiClient.post('/whatsapp/send', { number, message });
  },

  async sendBulk(numbers: string[], message: string, delay: number) {
    return apiClient.post('/whatsapp/send-bulk', { numbers, message, delay });
  },

  // Templates
  async getTemplates(tipo?: string): Promise<Template[]> {
    const params = tipo ? { tipo } : {};
    return apiClient.get('/whatsapp/templates', params);
  },

  async getTemplate(id: number): Promise<Template> {
    return apiClient.get(`/whatsapp/templates/${id}`);
  },

  async createTemplate(template: Partial<Template>): Promise<Template> {
    return apiClient.post('/whatsapp/templates', template);
  },

  async updateTemplate(id: number, template: Partial<Template>): Promise<Template> {
    return apiClient.put(`/whatsapp/templates/${id}`, template);
  },

  async deleteTemplate(id: number) {
    return apiClient.delete(`/whatsapp/templates/${id}`);
  },

  // Automações
  async getAutomacoes(): Promise<Automacao[]> {
    return apiClient.get('/whatsapp/automacoes');
  },

  async getAutomacao(id: number): Promise<Automacao> {
    return apiClient.get(`/whatsapp/automacoes/${id}`);
  },

  async createAutomacao(automacao: Partial<Automacao>): Promise<Automacao> {
    return apiClient.post('/whatsapp/automacoes', automacao);
  },

  async updateAutomacao(id: number, automacao: Partial<Automacao>): Promise<Automacao> {
    return apiClient.put(`/whatsapp/automacoes/${id}`, automacao);
  },

  async deleteAutomacao(id: number) {
    return apiClient.delete(`/whatsapp/automacoes/${id}`);
  },

  // Histórico
  async getNotificacoes(limit = 100): Promise<Notificacao[]> {
    return apiClient.get('/whatsapp/notificacoes', { limit });
  },

  // Fila
  async processarFila(limite = 50) {
    return apiClient.post('/whatsapp/processar-fila', { limite });
  },
};
