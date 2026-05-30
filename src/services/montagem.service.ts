import { apiClient } from "./api";
import type {
  MontagemItem,
  MontagemListResponse,
  MontagemColuna,
} from "@/types/montagem";

export interface ListarMontagensParams {
  filial?: string[];
  coluna?: MontagemColuna;
  data_de?: string;
  data_ate?: string;
}

function buildQuery(params?: ListarMontagensParams): string {
  if (!params) return "";
  const usp = new URLSearchParams();
  if (params.filial && params.filial.length) {
    params.filial.forEach((f) => usp.append("filial", f));
  }
  if (params.coluna) usp.set("coluna", params.coluna);
  if (params.data_de) usp.set("data_de", params.data_de);
  if (params.data_ate) usp.set("data_ate", params.data_ate);
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export const montagemService = {
  listar(params?: ListarMontagensParams): Promise<MontagemListResponse> {
    return apiClient.get<MontagemListResponse>(`/montagem${buildQuery(params)}`);
  },

  listarFiliais(): Promise<{ filiais: string[] }> {
    return apiClient.get<{ filiais: string[] }>(`/montagem/filiais`);
  },

  obterConfig(): Promise<{ filiais: string[] }> {
    return apiClient.get<{ filiais: string[] }>(`/montagem/config`);
  },

  salvarConfig(filiais: string[]): Promise<{ filiais: string[] }> {
    return apiClient.put<{ filiais: string[] }>(`/montagem/config`, { filiais });
  },

  iniciar(pedidoId: string, observacao?: string): Promise<MontagemItem> {
    return apiClient.post<MontagemItem>(
      `/montagem/${encodeURIComponent(pedidoId)}/iniciar`,
      { observacao: observacao ?? null }
    );
  },

  desfazerIniciar(pedidoId: string): Promise<{ ok: boolean }> {
    return apiClient.delete<{ ok: boolean }>(
      `/montagem/${encodeURIComponent(pedidoId)}/iniciar`
    );
  },

  concluir(
    pedidoId: string,
    observacao?: string,
    motivoAtraso?: string
  ): Promise<MontagemItem> {
    return apiClient.post<MontagemItem>(
      `/montagem/${encodeURIComponent(pedidoId)}/concluir`,
      {
        observacao: observacao ?? null,
        motivo_atraso: motivoAtraso ?? null,
      }
    );
  },

  desfazerConcluir(pedidoId: string): Promise<{ ok: boolean }> {
    return apiClient.delete<{ ok: boolean }>(
      `/montagem/${encodeURIComponent(pedidoId)}/concluir`
    );
  },

  adicionarComentario(
    pedidoId: string,
    texto: string,
    anexos?: File[]
  ): Promise<MontagemItem> {
    const fd = new FormData();
    fd.append("texto", texto ?? "");
    (anexos ?? []).forEach((f) => fd.append("anexos", f));
    return apiClient.post<MontagemItem>(
      `/montagem/${encodeURIComponent(pedidoId)}/comentarios`,
      fd
    );
  },

  adiar(
    pedidoId: string,
    payload: {
      motivo: "cliente_outra_data" | "telefone_invalido";
      nova_data?: string | null;
      confirmou_vitrine?: boolean;
      observacao?: string | null;
    }
  ): Promise<MontagemItem> {
    return apiClient.post<MontagemItem>(
      `/montagem/${encodeURIComponent(pedidoId)}/adiar`,
      payload
    );
  },

  retomar(pedidoId: string, texto?: string): Promise<MontagemItem> {
    return apiClient.post<MontagemItem>(
      `/montagem/${encodeURIComponent(pedidoId)}/retomar`,
      texto ? { texto } : {}
    );
  },

  criarLembrete(
    pedidoId: string,
    tipo: "1h" | "2h" | "6h" | "amanha"
  ): Promise<{ id: number; agendar_para: string; enviado: boolean }> {
    return apiClient.post(
      `/montagem/${encodeURIComponent(pedidoId)}/lembrete`,
      { tipo }
    );
  },

  getLembretes(
    pedidoId: string
  ): Promise<{ id: number; pedido_id: string; agendar_para: string; enviado: boolean; criado_em: string }[]> {
    return apiClient.get(
      `/montagem/${encodeURIComponent(pedidoId)}/lembretes`
    );
  },
};
