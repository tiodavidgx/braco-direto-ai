/**
 * Types para Montadores
 * 
 * Define os tipos TypeScript para os dados de montadores.
 */

export interface Montador {
  id: number;
  nome: string;
  identificador: string;
  email: string;
  telefone?: string;
  percentual_montagem: number;
  percentual_assistencia: number;
  percentual_desmontagem: number;
  auxilio_semanal: number;
  ativo: boolean;
  fornecedor_id?: string;
  regra_envio?: string;
  dias_envio?: string;
  emails_adicionais?: string;
  tempo_vencimento_dias: number;
  filial?: string;
  localidade?: string;
  created_at: string;
  updated_at: string;
}

export interface MontadorCreate {
  nome: string;
  identificador: string;
  email: string;
  telefone?: string;
  percentual_montagem: number;
  percentual_assistencia: number;
  percentual_desmontagem: number;
  auxilio_semanal: number;
  ativo?: boolean;
  fornecedor_id?: string;
  regra_envio?: string;
  dias_envio?: string;
  emails_adicionais?: string;
  tempo_vencimento_dias?: number;
  filial?: string;
  localidade?: string;
}

export interface MontadorUpdate extends Partial<MontadorCreate> {}
