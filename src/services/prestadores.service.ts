/**
 * Serviço de Prestadores
 * 
 * Gerencia todas as requisições relacionadas a prestadores.
 * Conecta o frontend ao backend Python (FastAPI).
 */

import { apiClient } from './api';
import { Prestador, PrestadorCreate, PrestadorUpdate } from '@/types/prestador';

export interface PrestadoresResponse {
  data: Prestador[];
  total: number;
  page: number;
  pages: number;
}

export interface PrestadoresFilters {
  search?: string;
  ativo?: boolean;
  page?: number;
  limit?: number;
}

export const prestadoresService = {
  /**
   * Lista todos os prestadores com filtros e paginação
   */
  async getAll(filters?: PrestadoresFilters): Promise<PrestadoresResponse> {
    return apiClient.get<PrestadoresResponse>('/prestadores', filters);
  },

  /**
   * Busca um prestador específico por ID
   */
  async getById(id: number): Promise<Prestador> {
    return apiClient.get<Prestador>(`/prestadores/${id}`);
  },

  /**
   * Cria um novo prestador
   */
  async create(data: PrestadorCreate): Promise<{ id: number; message: string }> {
    return apiClient.post('/prestadores', data);
  },

  /**
   * Atualiza um prestador existente
   */
  async update(id: number, data: PrestadorUpdate): Promise<Prestador> {
    return apiClient.put(`/prestadores/${id}`, data);
  },

  /**
   * Remove um prestador
   */
  async delete(id: number): Promise<void> {
    return apiClient.delete(`/prestadores/${id}`);
  },
};
