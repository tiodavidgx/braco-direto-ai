import { apiClient } from './api';

export interface TrelloConfig {
  api_key: string;
  token: string;
  board_id: string;
  lista_id: string;
  ativo: boolean;
}

export interface TrelloBoard {
  id: string;
  name: string;
}

export interface TrelloLista {
  id: string;
  name: string;
}

export const integracoesService = {
  // Configuração do Trello
  async getTrelloConfig(): Promise<TrelloConfig> {
    const response = await apiClient.get('/integracoes/trello/config') as { data: TrelloConfig };
    return response.data;
  },

  async saveTrelloConfig(config: TrelloConfig) {
    const response = await apiClient.post('/integracoes/trello/config', config) as { data: any };
    return response.data;
  },

  // Testar conexão
  async testTrelloConnection(api_key: string, token: string) {
    const response = await apiClient.post('/integracoes/trello/test', { api_key, token }) as { data: any };
    return response.data;
  },

  // Listar boards do usuário
  async getTrelloBoards(api_key: string, token: string): Promise<TrelloBoard[]> {
    const response = await apiClient.get('/integracoes/trello/boards', {
      params: { api_key, token }
    }) as { data: TrelloBoard[] };
    return response.data;
  },

  // Listar listas de um board
  async getTrelloListas(board_id: string, api_key: string, token: string): Promise<TrelloLista[]> {
    const response = await apiClient.get(`/integracoes/trello/listas/${board_id}`, {
      params: { api_key, token }
    }) as { data: TrelloLista[] };
    return response.data;
  },
};
