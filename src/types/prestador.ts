/**
 * Types para Prestadores
 * 
 * Define os tipos TypeScript para os dados de prestadores.
 * Estes tipos devem corresponder aos modelos do backend Python.
 */

export interface Prestador {
  id: number;
  nome: string;
  email: string;
  fornecedor_id?: string;
  telefone?: string;
  regra_envio?: string;
  dias_envio?: string;
  tempo_vencimento_dias: number;
  emails_adicionais?: string;
  filial?: string;
  localidade?: string;
  ativo?: boolean;
  created_at: string;
  updated_at: string;
}

export interface PrestadorCreate {
  nome: string;
  email: string;
  fornecedor_id?: string;
  telefone?: string;
  regra_envio?: string;
  dias_envio?: string;
  tempo_vencimento_dias?: number;
  emails_adicionais?: string;
  filial?: string;
  localidade?: string;
}

export interface PrestadorUpdate extends Partial<PrestadorCreate> {}
