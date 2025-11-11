/**
 * Serviço de Montadores
 * 
 * Gerencia todas as requisições relacionadas a montadores.
 * Conecta o frontend ao backend Python (FastAPI).
 */

import { apiClient } from './api';
import { Montador, MontadorCreate, MontadorUpdate } from '@/types/montador';

export interface MontadoresResponse {
  data: Montador[];
  total: number;
  page: number;
  pages: number;
}

export interface MontadoresFilters {
  search?: string;
  ativo?: boolean;
  page?: number;
  limit?: number;
}

export const montadoresService = {
  /**
   * Lista todos os montadores com filtros e paginação
   */
  async getAll(filters?: MontadoresFilters): Promise<MontadoresResponse> {
    return apiClient.get<MontadoresResponse>('/montadores', filters);
  },

  /**
   * Busca um montador específico por ID
   */
  async getById(id: number): Promise<Montador> {
    return apiClient.get<Montador>(`/montadores/${id}`);
  },

  /**
   * Cria um novo montador
   */
  async create(data: MontadorCreate): Promise<{ id: number; message: string }> {
    return apiClient.post('/montadores', data);
  },

  /**
   * Atualiza um montador existente
   */
  async update(id: number, data: MontadorUpdate): Promise<Montador> {
    return apiClient.put(`/montadores/${id}`, data);
  },

  /**
   * Remove um montador
   */
  async delete(id: number): Promise<void> {
    return apiClient.delete(`/montadores/${id}`);
  },
};
