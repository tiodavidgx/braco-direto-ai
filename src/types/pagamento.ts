export interface PagamentoPendente {
  prioridade: number;
  status: string;
  tipo: string;
  id: number;
  nome: string;
  fornecedorId: string;
  periodo: string;
  valor: string;
  vencimento: string;
  nf: string;
  _tipo_original: 'servico' | 'montagem';
  _id: number;
  _dias: number;
}
