/**
 * Gerador de dados mockados para demonstração da tela de
 * Acompanhamento de Montagem — sem backend real.
 *
 * Cobre todos os cenários visuais:
 *  - Pendente dentro do prazo, próximo do corte e fora do prazo
 *  - Em andamento
 *  - Finalizado (local + confirmado pelo ERP)
 *  - Entrega em fim de semana
 *  - Recém-entregue
 */

import type {
  MontagemItem,
  MontagemListResponse,
  MontagemSLA,
} from "@/types/montagem";

const FILIAIS = [
  "São Paulo - Centro",
  "Campinas",
  "Ribeirão Preto",
  "Sorocaba",
  "São José dos Campos",
];

const CLIENTES = [
  "Ana Paula Ribeiro",
  "Carlos Eduardo Silva",
  "Fernanda Moraes",
  "João Pedro Almeida",
  "Larissa Souza",
  "Marcelo Henrique",
  "Patrícia Lima",
  "Rodrigo Vasconcelos",
  "Tatiane Oliveira",
  "Bruno Martins",
  "Juliana Castro",
  "Rafael Nogueira",
];

const MONTADORES = [
  "Equipe Alfa",
  "Equipe Bravo",
  "Equipe Charlie",
  "Equipe Delta",
  null,
];

const MONTADOR_IDS = ["M001", "M002", "M003", "M004", null];

const PRODUTOS = [
  "Guarda-roupa 6 portas + cômoda 4 gavetas",
  "Cama box queen + cabeceira estofada",
  "Sala modulada 3,20m com painel TV",
  "Cozinha modulada 12 peças",
  "Escrivaninha + estante 4 prateleiras",
  "Dormitório casal completo",
  "Home office compacto",
  "Mesa de jantar 6 lugares + buffet",
];

const PRODUTO_CODIGOS = ["71883", "82104", "65327", "90011", "45201", "33789", "52046", "61178"];

const SITUACOES_BOLETIM = ["Aberto", "Em Andamento", "Fechado", "Pendente", "Cancelado"];
const SITUACOES_TIMELINE = ["Aguardando", "Em Rota", "Entregue", "Finalizado", "Reagendado"];

const FILIAIS_SAIDA = ["01", "02", "03", "04", "05"];

function pick<T>(arr: T[], i: number): T {
  return arr[i % arr.length];
}

function addHours(d: Date, h: number): Date {
  return new Date(d.getTime() + h * 3600_000);
}

function addMinutes(d: Date, m: number): Date {
  return new Date(d.getTime() + m * 60_000);
}

function atHour(d: Date, h: number, min = 0): Date {
  const x = new Date(d);
  x.setHours(h, min, 0, 0);
  return x;
}

function proximoDiaUtil(d: Date): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + 1);
  while (x.getDay() === 0 || x.getDay() === 6) x.setDate(x.getDate() + 1);
  return x;
}

function calcSla(dataEntrega: Date, agora: Date): MontagemSLA {
  const dow = dataEntrega.getDay();
  const fds = dow === 0 || dow === 6;

  let etapa: "manha" | "tarde" = "manha";
  let prazo: Date;

  if (fds) {
    let base = new Date(dataEntrega);
    while (base.getDay() === 0 || base.getDay() === 6) {
      base.setDate(base.getDate() + 1);
    }
    etapa = "manha";
    prazo = atHour(base, 18, 0);
  } else if (dataEntrega.getHours() < 13) {
    etapa = "manha";
    prazo = atHour(dataEntrega, 18, 0);
  } else {
    etapa = "tarde";
    prazo = atHour(proximoDiaUtil(dataEntrega), 13, 0);
  }

  const minutosRest = Math.floor((prazo.getTime() - agora.getTime()) / 60000);

  let status: MontagemSLA["status_sla"];
  const minDesdeEntrega =
    (agora.getTime() - dataEntrega.getTime()) / 60000;
  const agoraEhFds = agora.getDay() === 0 || agora.getDay() === 6;

  if (minutosRest < 0) status = "fora_do_prazo";
  else if (minDesdeEntrega <= 30) status = "recem_entregue";
  else if (fds && agoraEhFds) status = "fds";
  else if (minutosRest <= 120) status = "proximo_corte";
  else status = "no_prazo";

  const badge = badgeText(status, etapa, prazo, agora);
  return {
    etapa,
    prazo_limite: prazo.toISOString(),
    status_sla: status,
    minutos_restantes: minutosRest,
    badge_texto: badge,
    entregue_fds: fds,
  };
}

function badgeText(
  status: MontagemSLA["status_sla"],
  etapa: "manha" | "tarde",
  prazo: Date,
  agora: Date
): string {
  if (status === "fora_do_prazo") return "Fora do prazo";
  if (status === "recem_entregue") return "Recém-entregue";
  if (status === "fds") return "Entregue FDS — montar segunda à tarde";

  const dias = Math.floor(
    (atHour(prazo, 0).getTime() - atHour(agora, 0).getTime()) / 86_400_000
  );
  const nomes = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];
  const ref =
    dias === 0 ? "hoje" : dias === 1 ? "amanhã" : nomes[prazo.getDay() === 0 ? 6 : prazo.getDay() - 1];

  if (etapa === "manha") return `Montar ${ref} à tarde`;
  if (ref === "hoje") return "Montar hoje até 13h";
  if (ref === "amanhã") return "Montar até amanhã 13h";
  return `Montar ${ref} até 13h`;
}

interface MockConfig {
  coluna: MontagemItem["coluna"];
  dataEntrega: Date;
  status_erp?: string;
  data_montagem?: Date | null;
  travado_pelo_erp?: boolean;
  marcacaoLocal?: {
    iniciado_em?: Date;
    concluido_em?: Date;
    observacao?: string;
    motivo_atraso?: string;
  };
  conclusao_pendente_erp?: boolean;
  adiamento?: {
    motivo: "cliente_outra_data" | "telefone_invalido";
    nova_data?: Date;
    retorno_em?: Date;
    confirmou_vitrine?: boolean;
  };
}

function monta(i: number, cfg: MockConfig, agora: Date): MontagemItem {
  const sla =
    cfg.coluna === "finalizado" || cfg.coluna === "standby"
      ? null
      : calcSla(cfg.dataEntrega, agora);

  return {
    pedido_id: `MOCK-${String(i).padStart(4, "0")}`,
    numero_pedido: `V${100000 + i}`,
    cliente_nome: pick(CLIENTES, i),
    filial_venda: pick(FILIAIS, i),
    filial_saida: pick(FILIAIS_SAIDA, i),
    nota_fiscal: String(100000 + i * 37),
    serie_nota_fiscal: String((i % 9) + 1).padStart(2, "0"),
    data_entrega: cfg.dataEntrega.toISOString(),
    status_erp:
      cfg.status_erp ?? (cfg.coluna === "finalizado" ? "montado" : "pendente"),
    data_montagem: cfg.data_montagem ? cfg.data_montagem.toISOString() : null,
    montador_nome: pick(MONTADORES, i),
    identificador_montador: pick(MONTADOR_IDS, i),
    produto: pick(PRODUTO_CODIGOS, i),
    nome_produto: pick(PRODUTOS, i),
    produtos_resumo: pick(PRODUTOS, i),
    situacao_boletim:
      cfg.coluna === "finalizado"
        ? "Fechado"
        : cfg.coluna === "standby"
        ? "Pendente"
        : cfg.coluna === "em_andamento"
        ? "Em Andamento"
        : pick(SITUACOES_BOLETIM, i),
    situacao_timeline:
      cfg.coluna === "finalizado"
        ? "Finalizado"
        : cfg.coluna === "standby"
        ? "Reagendado"
        : pick(SITUACOES_TIMELINE, i),
    valor_pedido: 1500 + ((i * 317) % 7000),
    observacoes_erp: null,
    atualizado_em: agora.toISOString(),
    coluna: cfg.coluna,
    sla,
    travado_pelo_erp: cfg.travado_pelo_erp ?? false,
    marcacao_local: cfg.marcacaoLocal
      ? {
          iniciado_em: cfg.marcacaoLocal.iniciado_em?.toISOString() ?? null,
          iniciado_por_user_id: 1,
          concluido_em: cfg.marcacaoLocal.concluido_em?.toISOString() ?? null,
          concluido_por_user_id: cfg.marcacaoLocal.concluido_em ? 1 : null,
          observacao: cfg.marcacaoLocal.observacao ?? null,
          motivo_atraso: cfg.marcacaoLocal.motivo_atraso ?? null,
        }
      : null,
    conclusao_pendente_erp: cfg.conclusao_pendente_erp ?? false,
    adiamento: cfg.adiamento
      ? {
          motivo: cfg.adiamento.motivo,
          motivo_descricao: null,
          nova_data: cfg.adiamento.nova_data?.toISOString() ?? null,
          retorno_em: cfg.adiamento.retorno_em?.toISOString() ?? null,
          confirmou_vitrine: cfg.adiamento.confirmou_vitrine ?? false,
          criado_em: agora.toISOString(),
          criado_por_user_id: 1,
          criado_por_nome: "Operador",
        }
      : null,
  };
}

export function gerarMontagemMock(
  agora: Date = new Date()
): MontagemListResponse {
  const hojeManha = atHour(agora, 9, 0);
  const hojeTardeCedo = atHour(agora, 13, 30);
  const ontem = addHours(agora, -24);
  const antesDeOntem = addHours(agora, -48);
  const ontemTarde = atHour(ontem, 15, 0);
  const ontemManha = atHour(ontem, 9, 30);
  const antesDeOntemTarde = atHour(antesDeOntem, 16, 0);

  // Entrega FDS (último sábado)
  const ultimoSabado = new Date(agora);
  const diff = (ultimoSabado.getDay() + 1) % 7; // dias desde sábado
  ultimoSabado.setDate(ultimoSabado.getDate() - (diff === 0 ? 7 : diff));
  ultimoSabado.setHours(10, 0, 0, 0);

  // Recém entregue (10 min atrás)
  const recem = addMinutes(agora, -10);

  const itens: MontagemItem[] = [
    // -------- Pendentes --------
    monta(1, { coluna: "pendente", dataEntrega: hojeManha }, agora),
    monta(2, { coluna: "pendente", dataEntrega: hojeManha }, agora),
    // Próximo do corte: entregou manhã, já é ~16:30
    monta(
      3,
      {
        coluna: "pendente",
        dataEntrega: addHours(atHour(agora, 16, 15), -7),
      },
      agora
    ),
    // Fora do prazo: entrega ontem de tarde, prazo hoje 13h, agora depois
    monta(
      4,
      {
        coluna: "pendente",
        dataEntrega: ontemTarde,
      },
      agora
    ),
    monta(
      5,
      {
        coluna: "pendente",
        dataEntrega: antesDeOntemTarde,
      },
      agora
    ),
    // Recém entregue
    monta(6, { coluna: "pendente", dataEntrega: recem }, agora),
    // Entregue em FDS
    monta(7, { coluna: "pendente", dataEntrega: ultimoSabado }, agora),

    // -------- Em andamento --------
    monta(
      8,
      {
        coluna: "em_andamento",
        dataEntrega: hojeManha,
        status_erp: "em_andamento",
        marcacaoLocal: { iniciado_em: addMinutes(agora, -45) },
      },
      agora
    ),
    monta(
      9,
      {
        coluna: "em_andamento",
        dataEntrega: ontemTarde,
        status_erp: "pendente",
        marcacaoLocal: { iniciado_em: addMinutes(agora, -120) },
      },
      agora
    ),
    // Em andamento + fora do prazo
    monta(
      10,
      {
        coluna: "em_andamento",
        dataEntrega: antesDeOntemTarde,
        status_erp: "em_andamento",
        marcacaoLocal: {
          iniciado_em: addHours(agora, -3),
        },
      },
      agora
    ),

    // -------- Finalizados --------
    // confirmado pelo ERP
    monta(
      11,
      {
        coluna: "finalizado",
        dataEntrega: ontemManha,
        status_erp: "montado",
        data_montagem: addHours(ontem, 8),
        travado_pelo_erp: true,
      },
      agora
    ),
    monta(
      12,
      {
        coluna: "finalizado",
        dataEntrega: antesDeOntemTarde,
        status_erp: "montado",
        data_montagem: addHours(ontem, -2),
        travado_pelo_erp: true,
      },
      agora
    ),
    // finalizado local, aguardando ERP
    monta(
      13,
      {
        coluna: "finalizado",
        dataEntrega: ontemManha,
        status_erp: "pendente",
        marcacaoLocal: {
          concluido_em: addMinutes(agora, -30),
          observacao: "Cliente conferiu a montagem.",
        },
        conclusao_pendente_erp: true,
      },
      agora
    ),
    // finalizado com motivo de atraso
    monta(
      14,
      {
        coluna: "finalizado",
        dataEntrega: antesDeOntemTarde,
        status_erp: "montado",
        data_montagem: addHours(agora, -5),
        travado_pelo_erp: true,
        marcacaoLocal: {
          concluido_em: addHours(agora, -5),
          motivo_atraso: "Cliente não estava no local na primeira tentativa.",
        },
      },
      agora
    ),

    // -------- Stand by --------
    // Cliente pediu outra data
    monta(
      15,
      {
        coluna: "standby",
        dataEntrega: ontemTarde,
        adiamento: {
          motivo: "cliente_outra_data",
          nova_data: addHours(atHour(agora, 14, 0), 48),
        },
      },
      agora
    ),
    // Telefone inválido — retorna em 7 dias
    monta(
      16,
      {
        coluna: "standby",
        dataEntrega: antesDeOntemTarde,
        adiamento: {
          motivo: "telefone_invalido",
          retorno_em: addHours(agora, 24 * 7),
          confirmou_vitrine: true,
        },
      },
      agora
    ),
    // Telefone inválido — retorno próximo (em 1 dia)
    monta(
      17,
      {
        coluna: "standby",
        dataEntrega: addHours(agora, -24 * 6),
        adiamento: {
          motivo: "telefone_invalido",
          retorno_em: addHours(agora, 24),
          confirmou_vitrine: true,
        },
      },
      agora
    ),
  ];

  const filiais_disponiveis = Array.from(
    new Set(itens.map((i) => i.filial_venda!).filter(Boolean))
  ).sort();

  const resumo = {
    total: itens.length,
    pendente: itens.filter((i) => i.coluna === "pendente").length,
    em_andamento: itens.filter((i) => i.coluna === "em_andamento").length,
    finalizado: itens.filter((i) => i.coluna === "finalizado").length,
    standby: itens.filter((i) => i.coluna === "standby").length,
    fora_do_prazo: itens.filter((i) => i.sla?.status_sla === "fora_do_prazo")
      .length,
    proximo_corte: itens.filter((i) => i.sla?.status_sla === "proximo_corte")
      .length,
  };

  return {
    view_indisponivel: false,
    itens,
    resumo,
    filiais_disponiveis,
  };
}
