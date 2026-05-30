/**
 * Tipos do domínio "Acompanhamento de Montagem".
 */

export type MontagemColuna =
  | "pendente"
  | "em_andamento"
  | "finalizado"
  | "standby";

export type MontagemStatusSLA =
  | "fora_do_prazo"
  | "proximo_corte"
  | "no_prazo"
  | "recem_entregue"
  | "fds";

export type MontagemEtapa = "manha" | "tarde";

export interface MontagemSLA {
  etapa: MontagemEtapa;
  prazo_limite: string; // ISO
  status_sla: MontagemStatusSLA;
  minutos_restantes: number;
  badge_texto: string;
  entregue_fds: boolean;
}

export interface MontagemConclusaoSLA {
  prazo_limite: string;
  data_montagem: string | null;
  dentro_do_prazo: boolean | null;
  diferenca_minutos: number | null;
  etapa: MontagemEtapa;
}

export interface MontagemMarcacaoLocal {
  iniciado_em: string | null;
  iniciado_por_user_id: number | null;
  concluido_em: string | null;
  concluido_por_user_id: number | null;
  observacao: string | null;
  motivo_atraso: string | null;
}

export type MontagemComentarioTipo =
  | "comentario"
  | "adiamento_cliente_outra_data"
  | "adiamento_telefone_invalido"
  | "retomada";

export interface MontagemComentarioAnexo {
  nome: string;
  url: string;
  tipo: string;
}

export interface MontagemComentario {
  id: string;
  texto: string;
  autor_nome: string;
  autor_id: number | null;
  criado_em: string; // ISO
  tipo?: MontagemComentarioTipo;
  nova_data?: string | null;
  anexos?: MontagemComentarioAnexo[];
}

export type MontagemAdiamentoMotivo =
  | "cliente_outra_data"
  | "telefone_invalido";

export interface MontagemAdiamento {
  motivo: MontagemAdiamentoMotivo;
  motivo_descricao: string | null;
  nova_data: string | null; // ISO — para motivo cliente_outra_data
  retorno_em: string | null; // ISO — data em que volta para a fila
  confirmou_vitrine: boolean; // para motivo telefone_invalido
  criado_em: string;
  criado_por_user_id: number | null;
  criado_por_nome: string | null;
}

export interface MontagemItem {
  pedido_id: string;
  numero_pedido: string;
  cliente_nome: string | null;
  filial_venda: string | null;
  filial_saida: string | null;
  nota_fiscal: string | null;
  serie_nota_fiscal: string | null;
  data_entrega: string | null;
  data_previsao_montagem?: string | null;
  status_erp: string | null;
  data_montagem: string | null;
  montador_nome: string | null;
  identificador_montador: string | null;
  produto: string | null;
  nome_produto: string | null;
  produtos_resumo: string | null;
  situacao_boletim: string | null;
  situacao_timeline: string | null;
  valor_pedido: number | null;
  observacoes_erp: string | null;
  atualizado_em: string | null;

  coluna: MontagemColuna;
  sla: MontagemSLA | null;
  conclusao_sla?: MontagemConclusaoSLA | null;

  travado_pelo_erp: boolean;
  marcacao_local: MontagemMarcacaoLocal | null;
  conclusao_pendente_erp: boolean;

  adiamento?: MontagemAdiamento | null;
  comentarios?: MontagemComentario[];
}

export interface MontagemResumo {
  total: number;
  pendente: number;
  em_andamento: number;
  finalizado: number;
  fora_do_prazo: number;
  proximo_corte: number;
  standby?: number;
}

export interface MontagemListResponse {
  view_indisponivel: boolean;
  itens: MontagemItem[];
  resumo: MontagemResumo;
  filiais_disponiveis: string[];
}
