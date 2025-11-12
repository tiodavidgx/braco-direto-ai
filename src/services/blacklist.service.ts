/**
 * Serviço de Blacklist
 * 
 * Gerencia todas as requisições relacionadas a blacklist de O.S. e Boletins.
 * Conecta o frontend ao backend Python (FastAPI).
 */

import { apiClient } from './api';

export interface OSBlacklistItem {
  id: number;
  prestador_id: number;
  prestador_nome: string;
  os_numero: string;
  motivo: string | null;
  data_adicao: string;
}

export interface BoletimBlacklistItem {
  id: number;
  montador_id: number;
  montador_nome: string;
  boletim: string;
  motivo: string | null;
  data_adicao: string;
}

export interface OSBlacklistAdd {
  prestador_id: number;
  os_numero: string;
  motivo?: string;
}

export interface BoletimBlacklistAdd {
  montador_id: number;
  boletim: string;
  motivo?: string;
}

export const blacklistService = {
  // ===== O.S. (PRESTADORES) =====
  
  /**
   * Lista todas as O.S. na blacklist
   */
  async getAllOS(): Promise<OSBlacklistItem[]> {
    return apiClient.get<OSBlacklistItem[]>('/blacklist/os');
  },

  /**
   * Adiciona uma O.S. à blacklist
   */
  async addOS(data: OSBlacklistAdd): Promise<{ success: boolean; message: string; id: number }> {
    return apiClient.post('/blacklist/os', data);
  },

  /**
   * Remove uma O.S. da blacklist
   */
  async removeOS(id: number): Promise<{ success: boolean; message: string }> {
    return apiClient.delete(`/blacklist/os/${id}`);
  },

  /**
   * Verifica se O.S. estão na blacklist
   */
  async checkOS(numbers: string[]): Promise<any> {
    return apiClient.post('/blacklist/os/check', { numbers });
  },

  // ===== BOLETINS (MONTADORES) =====
  
  /**
   * Lista todos os boletins na blacklist
   */
  async getAllBoletins(): Promise<BoletimBlacklistItem[]> {
    return apiClient.get<BoletimBlacklistItem[]>('/blacklist/boletins');
  },

  /**
   * Adiciona um boletim à blacklist
   */
  async addBoletim(data: BoletimBlacklistAdd): Promise<{ success: boolean; message: string; id: number }> {
    return apiClient.post('/blacklist/boletins', data);
  },

  /**
   * Remove um boletim da blacklist
   */
  async removeBoletim(id: number): Promise<{ success: boolean; message: string }> {
    return apiClient.delete(`/blacklist/boletins/${id}`);
  },

  /**
   * Verifica se boletins estão na blacklist
   */
  async checkBoletins(numbers: string[]): Promise<any> {
    return apiClient.post('/blacklist/boletins/check', { numbers });
  },
};
