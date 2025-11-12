import { apiClient } from './api';

export const pagamentosService = {
  getTodosPagamentosPendentes: async () => {
    return apiClient.get<{ servicos: any[]; montagens: any[] }>('/pagamentos/pendentes');
  },

  marcarTodosNaoPendentesPagos: async () => {
    return apiClient.post<{ total: number; lotes: number; montagens: number }>('/pagamentos/marcar-todos-nao-pendentes-pagos');
  },

  desmarcarTodosPagos: async () => {
    return apiClient.post<{ total: number; lotes: number; montagens: number }>('/pagamentos/desmarcar-todos-pagos');
  },

  marcarLoteComoPago: async (id: number) => {
    return apiClient.post(`/pagamentos/lote/${id}/marcar-pago`);
  },

  marcarMontagemComoPaga: async (id: number) => {
    return apiClient.post(`/pagamentos/montagem/${id}/marcar-pago`);
  },
};
