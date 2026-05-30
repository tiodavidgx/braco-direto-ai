/**
 * Serviço de Dashboard
 * 
 * Gerencia requisições de estatísticas e dados do dashboard.
 */

import { apiClient } from './api';

export interface DashboardStats {
  prestadores_ativos: number;
  montadores_ativos: number;
  pagamentos_pendentes: number;
  nfs_aguardando: number;
  lotes_mes_atual: number;
  crescimento_mensal: number;
}

export interface Pendencia {
  id: number;
  tipo: 'prestador' | 'montador';
  nome: string;
  acao: string;
  data_vencimento: string;
  status: 'urgent' | 'pending' | 'overdue';
}

export interface PendenciasResponse {
  pendencias: Pendencia[];
}

export interface AtividadeRecente {
  id: number;
  acao: string;
  entidade: string;
  tempo: string;
  tipo: 'success' | 'warning' | 'info';
}

export const dashboardService = {
  /**
   * Busca estatísticas gerais do dashboard
   */
  async getStats(): Promise<DashboardStats> {
    return apiClient.get<DashboardStats>('/dashboard/stats');
  },

  /**
   * Busca pendências do dia
   */
  async getPendencias(): Promise<PendenciasResponse> {
    return apiClient.get<PendenciasResponse>('/dashboard/pendencias');
  },

  /**
   * Busca atividades recentes
   */
  async getAtividadesRecentes(): Promise<AtividadeRecente[]> {
    return apiClient.get<AtividadeRecente[]>('/dashboard/atividades-recentes');
  },
};
