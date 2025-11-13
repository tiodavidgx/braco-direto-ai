import { apiClient } from './api';

export interface EmailConfig {
  assunto: string;
  corpo: string;
  cc?: string;
  atualizado_em?: string;
}

export const emailConfigService = {
  /**
   * Busca a configuração de email salva para prestador ou montador
   */
  async getConfig(tipo: 'prestador' | 'montador'): Promise<EmailConfig> {
    return apiClient.get<EmailConfig>(`/relatorios/email-config/${tipo}`);
  },

  /**
   * Salva a configuração de email
   */
  async saveConfig(tipo: 'prestador' | 'montador', config: EmailConfig): Promise<{ success: boolean; message: string }> {
    return apiClient.post<{ success: boolean; message: string }>(`/relatorios/email-config/${tipo}`, config);
  },
};
