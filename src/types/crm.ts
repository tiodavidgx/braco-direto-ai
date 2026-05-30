// Status do ticket no Kanban
export type CRMTicketStatus = "novo" | "em_andamento" | "retorno" | "resolvido";

// Lista fixa de áreas (fallback)
export const CRM_AREAS = [
  "Atraso na entrega",
  "Produto danificado",
  "Produto errado",
  "Falta de peças",
  "Montagem incorreta",
  "Cancelamento",
  "Reembolso",
  "Troca",
  "Reclamação de qualidade",
  "Problema com NF",
  "Divergência de valor",
  "Outro",
] as const;

export type CRMArea = (typeof CRM_AREAS)[number];

export const CRM_STATUS_DETALHE = [
  "Novo",
  "Em Análise",
  "Aguardando Cliente",
  "Aguardando Fornecedor",
  "Aguardando Transportadora",
  "Em Andamento",
  "Pendente Montagem",
  "Pendente Troca",
  "Pendente Peças",
  "Resolvido",
] as const;

export const CRM_RESOLUCOES = [
  "Produto substituído",
  "Reembolso efetuado",
  "Entrega realizada",
  "Montagem concluída",
  "Peças enviadas",
  "Cancelamento processado",
  "Acordo com cliente",
  "Sem procedência",
  "Outro",
] as const;

// Ticket principal do CRM
export interface CRMTicket {
  id: number;
  id_pedido: string; // chave principal do sistema
  // Dados do cliente
  nome_cliente: string;
  telefone: string;
  email: string;
  anexo_url: string;
  anexo_nome?: string;
  // Dados do caso
  area: string;
  motivo: string;
  descricao: string;
  glpi?: string;
  id_processo?: string;
  plataforma?: string;
  credenciada?: string;
  prazo: string; // ISO date
  // Controle
  status: CRMTicketStatus;
  solicitante_id: number;
  solicitante_nome: string;
  analista_id: number | null;
  analista_nome: string | null;
  tipo_operacao_venda?: string;
  situacao_timeline?: string;
  status_detalhe?: string;
  resolucao?: string;
  descricao_resolucao?: string;
  comentarios: CRMComentario[];
  // Produto
  produto?: string;
  nome_produto?: string;
  // Análise diária
  necessita_analise?: boolean;
  data_nova_analise?: string | null;
  // Parent-child
  parent_id?: number | null;
  children_count?: number;
  children?: CRMTicket[];
  created_at: string;
  updated_at: string;
}

// Comentário / timeline do ticket
export interface CRMComentario {
  id: number;
  ticket_id: number;
  usuario_id: number;
  usuario_nome: string;
  texto: string;
  status_detalhe?: string;
  data_nova_analise?: string | null;
  anexos?: { nome: string; url: string; tipo: string }[];
  created_at: string;
}

// Payload para criar um novo ticket
export interface CRMTicketCreate {
  id_pedido: string;
  nome_cliente: string;
  telefone: string;
  email?: string;
  anexos?: File[];
  area: string;
  motivo?: string;
  descricao: string;
  glpi?: string;
  id_processo?: string;
  plataforma?: string;
  credenciada?: string;
  prazo: string;
  produto?: string;
  nome_produto?: string;
  tipo_operacao_venda?: string;
  situacao_timeline?: string;
}

// Stats do CRM
export interface CRMStats {
  total: number;
  novos: number;
  em_andamento: number;
  retorno: number;
  resolvidos: number;
  atrasados: number;
  necessita_analise: number;
}

// Dados do pedido vindos do bot
export interface ProdutoVenda {
  produto: string;
  nome_produto: string;
  identificador_nf: string;
  numero_nf: string;
  situacao_nota: string;
  serie_nf?: string;
}

export interface ClientePedido {
  identificador_pedido: string;
  nome_cliente: string;
  telefone_cliente?: string;
  cpf_cnpj_cliente?: string;
  cidade_nf?: string;
  uf_nf?: string;
  data_emissao?: string;
  data_previsao_entrega?: string;
  situacao_timeline?: string;
  data_entrega_efetiva?: string;
  tipo_operacao_venda?: string;
  filial_venda?: string;
  filial_saida?: string;
  deseja_entrega?: string;
}

export interface DadosPedidoBusca {
  id_pedido: string;
  cliente: ClientePedido | null;
  produtos: ProdutoVenda[];
  nmresolve: DadosNMResolve[];
  montagem: DadosMontagem[];
}

export interface DadosPedidoVenda {
  id_pedido: string;
  nome_cliente: string;
  telefone?: string;
  email?: string;
  data_venda?: string;
  valor?: number;
  plataforma?: string;
  status_venda?: string;
}

export interface DadosMontagem {
  nota_fiscal?: string;
  modalidade_servico?: string;
  data_previsao_montagem?: string;
  data_montagem?: string;
  situacao_boletim?: string;
  nome_montador?: string;
  identificador_montador?: string;
  identificador_nf?: string;
  produto?: string;
  identificador_boletim_montagem?: string;
}

export interface DadosNMResolve {
  boletim?: string;
  modalidade?: string;
  situacao_boletim?: string;
  situacao_servico?: string;
  id_prestador?: string;
  prestador?: string;
  data_finalizacao?: string;
  nome_produto?: string;
  identificador_nf?: string;
  produto?: string;
}
