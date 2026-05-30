import { apiClient } from "./api";
import type {
  CRMTicket,
  CRMTicketCreate,
  CRMTicketStatus,
  CRMStats,
  CRMComentario,
  DadosPedidoVenda,
  DadosPedidoBusca,
} from "@/types/crm";

// ============================================================
// Service
// ============================================================
export const crmService = {
  // Listar tickets com filtros
  async getTickets(params?: {
    status?: CRMTicketStatus;
    analista_id?: number;
    solicitante_id?: number;
    search?: string;
    motivo?: string;
  }): Promise<CRMTicket[]> {
    return apiClient.get<CRMTicket[]>("/crm/tickets", params);
  },

  // Obter ticket por ID
  async getTicket(id: number): Promise<CRMTicket> {
    return apiClient.get<CRMTicket>(`/crm/tickets/${id}`);
  },

  // Criar ticket
  async createTicket(data: CRMTicketCreate): Promise<CRMTicket> {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      if (key === "anexos" && Array.isArray(value)) {
        value.forEach((f: File) => formData.append("anexos", f));
      } else if (value instanceof File) {
        formData.append(key, value);
      } else if (value !== undefined && value !== null) {
        formData.append(key, String(value));
      }
    });
    return apiClient.post<CRMTicket>("/crm/tickets", formData);
  },

  // Mover ticket de status (Kanban drag)
  async updateStatus(id: number, status: CRMTicketStatus): Promise<CRMTicket> {
    return apiClient.put<CRMTicket>(`/crm/tickets/${id}/status`, { status });
  },

  // Adicionar comentário (com anexos opcionais e status obrigatório)
  async addComentario(ticketId: number, texto: string, anexos?: File[], statusDetalhe?: string, dataNovaAnalise?: string): Promise<CRMComentario> {
    const formData = new FormData();
    formData.append("texto", texto);
    if (statusDetalhe) formData.append("status_detalhe", statusDetalhe);
    if (dataNovaAnalise) formData.append("data_nova_analise", dataNovaAnalise);
    anexos?.forEach(f => formData.append("anexos", f));
    return apiClient.post<CRMComentario>(`/crm/tickets/${ticketId}/comentarios`, formData);
  },

  // Finalizar ticket com resolução
  async finalizarTicket(id: number, data: { resolucao: string; descricao_resolucao: string }): Promise<CRMTicket> {
    return apiClient.put<CRMTicket>(`/crm/tickets/${id}/finalizar`, data);
  },

  // Aprovar retorno (criador/admin)
  async aprovarTicket(id: number, comentario: string): Promise<CRMTicket> {
    return apiClient.put<CRMTicket>(`/crm/tickets/${id}/aprovar`, { comentario });
  },

  // Recusar retorno (criador/admin)
  async recusarTicket(id: number, comentario: string): Promise<CRMTicket> {
    return apiClient.put<CRMTicket>(`/crm/tickets/${id}/recusar`, { comentario });
  },

  // Estatísticas
  async getStats(): Promise<CRMStats> {
    return apiClient.get<CRMStats>("/crm/stats");
  },

  // Buscar dados do pedido para preenchimento automático
  async buscarDadosPedido(idPedido: string): Promise<DadosPedidoBusca | null> {
    try {
      return await apiClient.get<DadosPedidoBusca>(`/dados-bot/buscar/${idPedido}`);
    } catch {
      return null;
    }
  },

  // Buscar última atualização das views do bot
  async buscarUltimaAtualizacao(): Promise<Record<string, string | null>> {
    try {
      return await apiClient.get<Record<string, string | null>>('/dados-bot/ultima-atualizacao');
    } catch {
      return {};
    }
  },

  // Reatribuir ticket a outro analista
  async reatribuir(ticketId: number, analistaId: number, analistaNome: string): Promise<CRMTicket> {
    return apiClient.put<CRMTicket>(`/crm/tickets/${ticketId}`, {
      analista_id: analistaId,
      analista_nome: analistaNome,
    });
  },

  // Listar analistas disponíveis (para reatribuição)
  async getAnalistas(): Promise<{ id: number; nome: string }[]> {
    return apiClient.get<{ id: number; nome: string }[]>("/crm/analistas");
  },

  // Excluir ticket
  async deleteTicket(id: number): Promise<void> {
    await apiClient.delete(`/crm/tickets/${id}`);
  },

  // ---- Parâmetros ----
  // Áreas (antigo "Motivos")
  async getAreas(): Promise<{ id: number; nome: string; ativo: boolean; ordem: number }[]> {
    return apiClient.get("/crm/parametros/areas");
  },
  async createArea(nome: string) {
    const fd = new FormData(); fd.append("nome", nome);
    return apiClient.post("/crm/parametros/areas", fd);
  },
  async updateArea(id: number, data: { nome?: string; ativo?: boolean; ordem?: number }) {
    const fd = new FormData();
    if (data.nome !== undefined) fd.append("nome", data.nome);
    if (data.ativo !== undefined) fd.append("ativo", String(data.ativo));
    if (data.ordem !== undefined) fd.append("ordem", String(data.ordem));
    return apiClient.put(`/crm/parametros/areas/${id}`, fd);
  },
  async deleteArea(id: number) {
    return apiClient.delete(`/crm/parametros/areas/${id}`);
  },

  // Motivos
  async getMotivos(): Promise<{ id: number; nome: string; ativo: boolean; ordem: number; area_id: number | null }[]> {
    return apiClient.get("/crm/parametros/motivos");
  },
  async createMotivo(nome: string, area_id: number) {
    const fd = new FormData(); fd.append("nome", nome); fd.append("area_id", String(area_id));
    return apiClient.post("/crm/parametros/motivos", fd);
  },
  async updateMotivo(id: number, data: { nome?: string; ativo?: boolean; ordem?: number; area_id?: number }) {
    const fd = new FormData();
    if (data.nome !== undefined) fd.append("nome", data.nome);
    if (data.ativo !== undefined) fd.append("ativo", String(data.ativo));
    if (data.ordem !== undefined) fd.append("ordem", String(data.ordem));
    if (data.area_id !== undefined) fd.append("area_id", String(data.area_id));
    return apiClient.put(`/crm/parametros/motivos/${id}`, fd);
  },
  async deleteMotivo(id: number) {
    return apiClient.delete(`/crm/parametros/motivos/${id}`);
  },

  async getStatusDetalhe(): Promise<{ id: number; nome: string; cor: string; ativo: boolean; ordem: number; area_id: number | null }[]> {
    return apiClient.get("/crm/parametros/status");
  },
  async createStatusDetalhe(nome: string, cor: string, area_id?: number) {
    const fd = new FormData(); fd.append("nome", nome); fd.append("cor", cor);
    if (area_id !== undefined) fd.append("area_id", String(area_id));
    return apiClient.post("/crm/parametros/status", fd);
  },
  async updateStatusDetalhe(id: number, data: { nome?: string; cor?: string; ativo?: boolean; ordem?: number; area_id?: number }) {
    const fd = new FormData();
    if (data.nome !== undefined) fd.append("nome", data.nome);
    if (data.cor !== undefined) fd.append("cor", data.cor);
    if (data.ativo !== undefined) fd.append("ativo", String(data.ativo));
    if (data.ordem !== undefined) fd.append("ordem", String(data.ordem));
    if (data.area_id !== undefined) fd.append("area_id", String(data.area_id));
    return apiClient.put(`/crm/parametros/status/${id}`, fd);
  },

  // ---- Resoluções ----
  async getResolucoes(): Promise<{ id: number; nome: string; ativo: boolean; ordem: number }[]> {
    return apiClient.get("/crm/parametros/resolucoes");
  },
  async createResolucao(nome: string) {
    const fd = new FormData(); fd.append("nome", nome);
    return apiClient.post("/crm/parametros/resolucoes", fd);
  },
  async updateResolucao(id: number, data: { nome?: string; ativo?: boolean; ordem?: number }) {
    const fd = new FormData();
    if (data.nome !== undefined) fd.append("nome", data.nome);
    if (data.ativo !== undefined) fd.append("ativo", String(data.ativo));
    if (data.ordem !== undefined) fd.append("ordem", String(data.ordem));
    return apiClient.put(`/crm/parametros/resolucoes/${id}`, fd);
  },
  async deleteResolucao(id: number) {
    return apiClient.delete(`/crm/parametros/resolucoes/${id}`);
  },

  // Plataformas
  async getPlataformas(): Promise<{ id: number; nome: string; ativo: boolean; ordem: number }[]> {
    return apiClient.get("/crm/parametros/plataformas");
  },
  async createPlataforma(nome: string) {
    const fd = new FormData(); fd.append("nome", nome);
    return apiClient.post("/crm/parametros/plataformas", fd);
  },
  async updatePlataforma(id: number, data: { nome?: string; ativo?: boolean; ordem?: number }) {
    const fd = new FormData();
    if (data.nome !== undefined) fd.append("nome", data.nome);
    if (data.ativo !== undefined) fd.append("ativo", String(data.ativo));
    if (data.ordem !== undefined) fd.append("ordem", String(data.ordem));
    return apiClient.put(`/crm/parametros/plataformas/${id}`, fd);
  },
  async deletePlataforma(id: number) {
    return apiClient.delete(`/crm/parametros/plataformas/${id}`);
  },

  // Credenciadas
  async getCredenciadas(): Promise<{ id: number; nome: string; ativo: boolean; ordem: number }[]> {
    return apiClient.get("/crm/parametros/credenciadas");
  },
  async createCredenciada(nome: string) {
    const fd = new FormData(); fd.append("nome", nome);
    return apiClient.post("/crm/parametros/credenciadas", fd);
  },
  async updateCredenciada(id: number, data: { nome?: string; ativo?: boolean; ordem?: number }) {
    const fd = new FormData();
    if (data.nome !== undefined) fd.append("nome", data.nome);
    if (data.ativo !== undefined) fd.append("ativo", String(data.ativo));
    if (data.ordem !== undefined) fd.append("ordem", String(data.ordem));
    return apiClient.put(`/crm/parametros/credenciadas/${id}`, fd);
  },
  async deleteCredenciada(id: number) {
    return apiClient.delete(`/crm/parametros/credenciadas/${id}`);
  },

  // Lembretes WhatsApp
  async criarLembrete(ticketId: number, tipo: "1h" | "2h" | "6h" | "amanha") {
    return apiClient.post(`/crm/tickets/${ticketId}/lembrete`, { tipo });
  },
  async getLembretes(ticketId: number): Promise<{ id: number; ticket_id: number; agendar_para: string; enviado: boolean; criado_em: string }[]> {
    return apiClient.get(`/crm/tickets/${ticketId}/lembretes`);
  },
};
