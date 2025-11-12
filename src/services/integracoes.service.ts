import { apiClient } from './api';

export const integracoesService = {
  async getTrelloConfig() {
    return apiClient.get('/integracoes/trello/config');
  },

  async saveTrelloConfig(data: any) {
    return apiClient.post('/integracoes/trello/config', data);
  },

  async testTrelloConnection() {
    return apiClient.get('/integracoes/trello/test');
  },

  async listBoards() {
    return apiClient.get('/integracoes/trello/boards');
  },

  async listLists(boardId: string) {
    return apiClient.get(`/integracoes/trello/boards/${boardId}/lists`);
  },
};
