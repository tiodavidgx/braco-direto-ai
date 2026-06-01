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
  cidade?: string;
  dia_envio_1?: number;
  dia_envio_2?: number;
  envio_automatico?: boolean;
  dia_fechamento?: number;
  dias_envio_mes?: number[];
  prazo_pagamento_dias?: number;
  email_responsavel_nm?: string;
  tipo_pagamento?: string;
  terceirizada_id?: number | null;
  email_template_id?: number | null;
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
  cidade?: string;
  dia_envio_1?: number;
  dia_envio_2?: number;
  envio_automatico?: boolean;
  dia_fechamento?: number;
  dias_envio_mes?: number[];
  prazo_pagamento_dias?: number;
  email_responsavel_nm?: string;
  tipo_pagamento?: string;
  terceirizada_id?: number | null;
  email_template_id?: number | null;
}

export interface MontadorUpdate extends Partial<MontadorCreate> {}
