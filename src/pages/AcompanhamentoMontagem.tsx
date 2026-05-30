import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ClipboardList,
  Hammer,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Loader2,
  Info,
  Search,
  Clock,
  FlaskConical,
  Filter,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { KanbanColunaMontagem } from "@/components/montagem/KanbanColunaMontagem";
import { CardPedidoMontagem } from "@/components/montagem/CardPedidoMontagem";
import { FiltroFiliais } from "@/components/montagem/FiltroFiliais";
import { DialogConcluirMontagem } from "@/components/montagem/DialogConcluirMontagem";
import { DialogDetalheMontagem } from "@/components/montagem/DialogDetalheMontagem";
import { DialogAdiarMontagem } from "@/components/montagem/DialogAdiarMontagem";
import { montagemService } from "@/services/montagem.service";
import { gerarMontagemMock } from "@/lib/mockMontagem";
import type {
  MontagemAdiamentoMotivo,
  MontagemColuna,
  MontagemComentario,
  MontagemItem,
  MontagemListResponse,
} from "@/types/montagem";
import { minutosAte } from "@/lib/slaMontagem";
import { useAuth } from "@/contexts/AuthContext";

const STORAGE_FILIAIS_CONHECIDAS = "montagem.filiais.conhecidas";
const STORAGE_MOCK = "montagem.mock";
const REFRESH_MS = 60_000;

type AbaFinal = "ativos" | "standby" | "finalizados";

export default function AcompanhamentoMontagem() {
  const qc = useQueryClient();
  const { user } = useAuth();

  // Seleção de filiais compartilhada (persistida no backend).
  // Enquanto a config não carrega, usa [] (board vazio até resolver).
  const { data: configData } = useQuery({
    queryKey: ["montagem-config"],
    queryFn: () => montagemService.obterConfig(),
    staleTime: 30_000,
  });
  const filiais = configData?.filiais ?? [];

  const salvarConfigMutation = useMutation({
    mutationFn: (novas: string[]) => montagemService.salvarConfig(novas),
    onMutate: async (novas) => {
      await qc.cancelQueries({ queryKey: ["montagem-config"] });
      const previous = qc.getQueryData<{ filiais: string[] }>(["montagem-config"]);
      qc.setQueryData(["montagem-config"], { filiais: novas });
      return { previous };
    },
    onError: (_err, _novas, ctx) => {
      if (ctx?.previous) qc.setQueryData(["montagem-config"], ctx.previous);
      toast.error("Falha ao salvar seleção de filiais.");
    },
    onSuccess: (resp) => {
      qc.setQueryData(["montagem-config"], resp);
      qc.invalidateQueries({ queryKey: ["montagem"] });
    },
  });
  const setFiliais = (novas: string[]) => salvarConfigMutation.mutate(novas);

  const [filiaisConhecidas, setFiliaisConhecidas] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_FILIAIS_CONHECIDAS);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const [busca, setBusca] = useState("");
  const [aba, setAba] = useState<AbaFinal>("ativos");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [mockMode, setMockMode] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_MOCK) === "1";
    } catch {
      return false;
    }
  });

  const [dialogItem, setDialogItem] = useState<MontagemItem | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Detalhe + comentários
  const [detalheId, setDetalheId] = useState<string | null>(null);
  const [detalheOpen, setDetalheOpen] = useState(false);

  // Adiar
  const [adiarItem, setAdiarItem] = useState<MontagemItem | null>(null);
  const [adiarOpen, setAdiarOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_MOCK, mockMode ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [mockMode]);

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ["montagem", filiais, mockMode],
    queryFn: async (): Promise<MontagemListResponse> => {
      if (mockMode) {
        return gerarMontagemMock();
      }
      // Nenhuma filial selecionada = board vazio. O usuário precisa
      // marcar ao menos uma filial para carregar cards.
      if (!filiais.length) {
        return {
          view_indisponivel: false,
          itens: [],
          resumo: {
            total: 0,
            pendente: 0,
            em_andamento: 0,
            finalizado: 0,
            standby: 0,
            fora_do_prazo: 0,
            proximo_corte: 0,
          },
          filiais_disponiveis: [],
        } as MontagemListResponse;
      }
      return montagemService.listar({ filial: filiais });
    },
    refetchInterval: REFRESH_MS,
    refetchOnWindowFocus: true,
  });

  const itens = useMemo(() => {
    const base = data?.itens ?? [];
    if (!mockMode || !filiais.length) return base;
    return base.filter((i) => i.filial_venda && filiais.includes(i.filial_venda));
  }, [data, mockMode, filiais]);

  const resumo = useMemo(() => {
    if (!mockMode) {
      return (
        data?.resumo ?? {
          total: 0,
          pendente: 0,
          em_andamento: 0,
          finalizado: 0,
          fora_do_prazo: 0,
          proximo_corte: 0,
        }
      );
    }
    return {
      total: itens.length,
      pendente: itens.filter((i) => i.coluna === "pendente").length,
      em_andamento: itens.filter((i) => i.coluna === "em_andamento").length,
      finalizado: itens.filter((i) => i.coluna === "finalizado").length,
      standby: itens.filter((i) => i.coluna === "standby").length,
      fora_do_prazo: itens.filter((i) => i.sla?.status_sla === "fora_do_prazo").length,
      proximo_corte: itens.filter((i) => i.sla?.status_sla === "proximo_corte").length,
    };
  }, [data, itens, mockMode]);
  const viewIndisponivel = data?.view_indisponivel ?? false;
  const filiaisDisponiveis = data?.filiais_disponiveis ?? [];

  // Query separada, leve, só para listar filiais disponíveis no banco.
  // Roda independente da seleção para popular o filtro mesmo quando o
  // usuário ainda não escolheu nenhuma filial (board vazio).
  const { data: filiaisApiData } = useQuery({
    queryKey: ["montagem-filiais", mockMode],
    queryFn: async () => {
      if (mockMode) return { filiais: [] as string[] };
      return montagemService.listarFiliais();
    },
    refetchInterval: REFRESH_MS,
    refetchOnWindowFocus: true,
  });
  const filiaisDoBanco = filiaisApiData?.filiais ?? [];

  // Acumula filiais que já apareceram na API — a lista fica persistida mesmo
  // que uma filial não retorne dados agora, assim o usuário pode deixá-la
  // pré-marcada e futuros cards dela serão pegos automaticamente.
  useEffect(() => {
    const extras = [...filiaisDisponiveis, ...filiaisDoBanco];
    if (!extras.length) return;
    setFiliaisConhecidas((prev) => {
      const merged = Array.from(new Set([...prev, ...extras]));
      if (merged.length === prev.length) return prev;
      try {
        localStorage.setItem(STORAGE_FILIAIS_CONHECIDAS, JSON.stringify(merged));
      } catch {
        /* ignore */
      }
      return merged;
    });
  }, [filiaisDisponiveis, filiaisDoBanco]);

  const filiaisParaFiltro = useMemo(
    () =>
      Array.from(
        new Set([
          ...filiaisConhecidas,
          ...filiaisDoBanco,
          ...filiaisDisponiveis,
          ...filiais,
        ])
      ),
    [filiaisConhecidas, filiaisDoBanco, filiaisDisponiveis, filiais]
  );

  // Auto-ativa modo demonstração se a view ainda não existir
  useEffect(() => {
    if (viewIndisponivel && !mockMode) {
      setMockMode(true);
      toast.info("View de montagem ainda não disponível. Exibindo dados de demonstração.");
    }
  }, [viewIndisponivel, mockMode]);

  // Busca textual leve
  const itensFiltrados = useMemo(() => {
    if (!busca.trim()) return itens;
    const q = busca.trim().toLowerCase();
    return itens.filter((i) =>
      [
        i.numero_pedido,
        i.cliente_nome,
        i.filial_venda,
        i.montador_nome,
        i.produtos_resumo,
      ]
        .filter(Boolean)
        .some((c) => String(c).toLowerCase().includes(q))
    );
  }, [itens, busca]);

  // Ordenar sempre pelo menor prazo primeiro (mais atrasados antes — prazo ASC).
  // Itens sem SLA vão para o fim.
  const ordenar = useCallback((arr: MontagemItem[]) => {
    return [...arr].sort((a, b) => {
      const pa = a.sla ? new Date(a.sla.prazo_limite).getTime() : Infinity;
      const pb = b.sla ? new Date(b.sla.prazo_limite).getTime() : Infinity;
      return pa - pb;
    });
  }, []);

  const porColuna = useMemo(() => {
    const base: Record<MontagemColuna, MontagemItem[]> = {
      pendente: [],
      em_andamento: [],
      finalizado: [],
      standby: [],
    };
    for (const i of itensFiltrados) base[i.coluna].push(i);
    base.pendente = ordenar(base.pendente);
    base.em_andamento = ordenar(base.em_andamento);
    base.finalizado = base.finalizado.sort((a, b) => {
      const ka = a.marcacao_local?.concluido_em ?? a.data_montagem ?? "";
      const kb = b.marcacao_local?.concluido_em ?? b.data_montagem ?? "";
      return kb.localeCompare(ka);
    });
    // Stand by: ordenar pelo retorno mais próximo (nova_data ou retorno_em)
    base.standby = [...base.standby].sort((a, b) => {
      const ka =
        a.adiamento?.nova_data ??
        a.adiamento?.retorno_em ??
        a.adiamento?.criado_em ??
        "";
      const kb =
        b.adiamento?.nova_data ??
        b.adiamento?.retorno_em ??
        b.adiamento?.criado_em ??
        "";
      return ka.localeCompare(kb);
    });
    return base;
  }, [itensFiltrados, ordenar]);

  const foraPrazoPorColuna = useMemo(() => {
    return {
      pendente: porColuna.pendente.filter(
        (i) => i.sla && minutosAte(i.sla.prazo_limite) < 0
      ).length,
      em_andamento: porColuna.em_andamento.filter(
        (i) => i.sla && minutosAte(i.sla.prazo_limite) < 0
      ).length,
    };
  }, [porColuna]);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["montagem"] });

  // Atualiza o cache local quando estamos em modo demonstração.
  const mutarMockItem = (
    pedidoId: string,
    fn: (item: MontagemItem) => MontagemItem
  ) => {
    qc.setQueriesData<MontagemListResponse>(
      { queryKey: ["montagem"] },
      (prev) => {
        if (!prev) return prev;
        const itens = prev.itens.map((it) =>
          it.pedido_id === pedidoId ? fn(it) : it
        );
        const resumo = {
          total: itens.length,
          pendente: itens.filter((i) => i.coluna === "pendente").length,
          em_andamento: itens.filter((i) => i.coluna === "em_andamento").length,
          finalizado: itens.filter((i) => i.coluna === "finalizado").length,
          standby: itens.filter((i) => i.coluna === "standby").length,
          fora_do_prazo: itens.filter(
            (i) => i.sla?.status_sla === "fora_do_prazo"
          ).length,
          proximo_corte: itens.filter(
            (i) => i.sla?.status_sla === "proximo_corte"
          ).length,
        };
        return { ...prev, itens, resumo };
      }
    );
  };

  const handleAbrirDetalhe = (item: MontagemItem) => {
    setDetalheId(item.pedido_id);
    setDetalheOpen(true);
  };

  const handleAdicionarComentario = async (
    pedidoId: string,
    texto: string,
    anexos?: File[]
  ) => {
    if (mockMode) {
      const novo: MontagemComentario = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        texto: texto || "(anexo)",
        autor_nome: user?.nome ?? "Você",
        autor_id: user?.id ?? null,
        criado_em: new Date().toISOString(),
        anexos: (anexos ?? []).map((f) => ({
          nome: f.name,
          url: URL.createObjectURL(f),
          tipo: f.type,
        })),
      };
      mutarMockItem(pedidoId, (it) => ({
        ...it,
        comentarios: [...(it.comentarios ?? []), novo],
      }));
      toast.success("Comentário adicionado.");
      return;
    }
    try {
      await montagemService.adicionarComentario(pedidoId, texto, anexos);
      toast.success("Comentário adicionado.");
      qc.invalidateQueries({ queryKey: ["montagem"] });
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Falha ao salvar comentário."
      );
    }
  };

  const handleAbrirAdiar = (item: MontagemItem) => {
    setAdiarItem(item);
    setAdiarOpen(true);
  };

  const handleConfirmarAdiar = async (payload: {
    motivo: MontagemAdiamentoMotivo;
    nova_data?: string;
    confirmou_vitrine?: boolean;
    observacao?: string;
  }) => {
    if (!adiarItem) return;
    const agora = new Date();
    const retornoEm =
      payload.motivo === "telefone_invalido"
        ? new Date(agora.getTime() + 7 * 24 * 3600_000).toISOString()
        : payload.nova_data ?? null;

    if (mockMode) {
      mutarMockItem(adiarItem.pedido_id, (it) => ({
        ...it,
        coluna: "standby",
        marcacao_local: it.marcacao_local
          ? {
              ...it.marcacao_local,
              iniciado_em: null,
              iniciado_por_user_id: null,
            }
          : null,
        adiamento: {
          motivo: payload.motivo,
          motivo_descricao:
            payload.motivo === "cliente_outra_data"
              ? "Cliente deseja montagem em outro momento"
              : "Telefone do cliente incorreto ou não atende",
          nova_data: payload.nova_data ?? null,
          retorno_em: retornoEm,
          confirmou_vitrine: payload.confirmou_vitrine ?? false,
          criado_em: agora.toISOString(),
          criado_por_user_id: user?.id ?? null,
          criado_por_nome: user?.nome ?? null,
        },
        comentarios: payload.observacao
          ? [
              ...(it.comentarios ?? []),
              {
                id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                texto: `[Adiamento] ${payload.observacao}`,
                autor_nome: user?.nome ?? "Operador",
                autor_id: user?.id ?? null,
                criado_em: agora.toISOString(),
              },
            ]
          : it.comentarios,
      }));
      toast.success(
        `Pedido #${adiarItem.numero_pedido} movido para Stand by.`
      );
      return;
    }
    // Backend real
    try {
      await montagemService.adiar(adiarItem.pedido_id, {
        motivo: payload.motivo,
        nova_data: payload.nova_data ?? null,
        confirmou_vitrine: payload.confirmou_vitrine ?? false,
        observacao: payload.observacao ?? null,
      });
      toast.success(
        `Pedido #${adiarItem.numero_pedido} movido para Stand by.`
      );
      qc.invalidateQueries({ queryKey: ["montagem"] });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Falha ao adiar montagem.");
    }
  };

  const handleRetomar = async (item: MontagemItem) => {
    if (mockMode) {
      mutarMockItem(item.pedido_id, (it) => ({
        ...it,
        coluna: "pendente",
        adiamento: null,
      }));
      toast.success(
        `Pedido #${item.numero_pedido} retomado para a fila de montagem.`
      );
      return;
    }
    try {
      await montagemService.retomar(item.pedido_id);
      toast.success(`Pedido #${item.numero_pedido} retomado.`);
      qc.invalidateQueries({ queryKey: ["montagem"] });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Falha ao retomar.");
    }
  };

  const handleIniciar = async (item: MontagemItem) => {
    if (mockMode) {
      mutarMockItem(item.pedido_id, (it) => ({
        ...it,
        coluna: "em_andamento",
        marcacao_local: {
          ...(it.marcacao_local ?? {
            iniciado_por_user_id: null,
            concluido_em: null,
            concluido_por_user_id: null,
            observacao: null,
            motivo_atraso: null,
          }),
          iniciado_em: new Date().toISOString(),
          iniciado_por_user_id: 1,
        },
      }));
      toast.success(`Montagem do pedido #${item.numero_pedido} iniciada.`);
      return;
    }
    try {
      setBusyId(item.pedido_id);
      await montagemService.iniciar(item.pedido_id);
      toast.success(`Montagem do pedido #${item.numero_pedido} iniciada.`);
      invalidate();
    } catch (e: any) {
      toast.error(e?.message ?? "Erro ao iniciar montagem.");
    } finally {
      setBusyId(null);
    }
  };

  const handleAbrirConcluir = (item: MontagemItem) => {
    setDialogItem(item);
    setDialogOpen(true);
  };

  const handleConcluirConfirm = async (obs?: string, motivo?: string) => {
    if (!dialogItem) return;
    if (mockMode) {
      mutarMockItem(dialogItem.pedido_id, (it) => ({
        ...it,
        coluna: "finalizado",
        conclusao_pendente_erp: true,
        marcacao_local: {
          ...(it.marcacao_local ?? {
            iniciado_em: null,
            iniciado_por_user_id: null,
          }),
          concluido_em: new Date().toISOString(),
          concluido_por_user_id: 1,
          observacao: obs ?? null,
          motivo_atraso: motivo ?? null,
        },
      }));
      toast.success(
        `Pedido #${dialogItem.numero_pedido} marcado como concluído.`
      );
      return;
    }
    try {
      setBusyId(dialogItem.pedido_id);
      await montagemService.concluir(dialogItem.pedido_id, obs, motivo);
      toast.success(
        `Pedido #${dialogItem.numero_pedido} marcado como concluído.`
      );
      invalidate();
    } catch (e: any) {
      toast.error(e?.message ?? "Erro ao concluir montagem.");
      throw e;
    } finally {
      setBusyId(null);
    }
  };

  const handleDesfazer = async (item: MontagemItem) => {
    if (mockMode) {
      mutarMockItem(item.pedido_id, (it) => {
        if (it.coluna === "finalizado") {
          return {
            ...it,
            coluna: it.marcacao_local?.iniciado_em ? "em_andamento" : "pendente",
            conclusao_pendente_erp: false,
            marcacao_local: it.marcacao_local
              ? {
                  ...it.marcacao_local,
                  concluido_em: null,
                  concluido_por_user_id: null,
                  observacao: null,
                  motivo_atraso: null,
                }
              : null,
          };
        }
        return {
          ...it,
          coluna: "pendente",
          marcacao_local: it.marcacao_local
            ? {
                ...it.marcacao_local,
                iniciado_em: null,
                iniciado_por_user_id: null,
              }
            : null,
        };
      });
      toast.success(
        item.coluna === "finalizado" ? "Conclusão desfeita." : "Início desfeito."
      );
      return;
    }
    try {
      setBusyId(item.pedido_id);
      if (item.coluna === "finalizado") {
        await montagemService.desfazerConcluir(item.pedido_id);
        toast.success("Conclusão desfeita.");
      } else {
        await montagemService.desfazerIniciar(item.pedido_id);
        toast.success("Início desfeito.");
      }
      invalidate();
    } catch (e: any) {
      toast.error(e?.message ?? "Erro ao desfazer.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <Hammer className="h-6 w-6 text-primary" />
            Montagem 24h
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            SLA de montagem em 24h após a entrega. Entregas pela manhã devem
            ser montadas até às 18h; entregas à tarde, até 13h do próximo dia útil.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-1.5">
            <FlaskConical className="h-4 w-4 text-amber-600" />
            <Label
              htmlFor="mock-switch"
              className="cursor-pointer text-xs font-medium"
            >
              Modo demonstração
            </Label>
            <Switch
              id="mock-switch"
              checked={mockMode}
              onCheckedChange={setMockMode}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-1.5 h-4 w-4" />
            )}
            Atualizar
          </Button>
        </div>
      </div>

      {/* Indicadores */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <IndicadorCard
          titulo="Pendentes"
          valor={resumo.pendente}
          icone={<ClipboardList className="h-4 w-4" />}
          tom="slate"
        />
        <IndicadorCard
          titulo="Em andamento"
          valor={resumo.em_andamento}
          icone={<Hammer className="h-4 w-4" />}
          tom="amber"
        />
        <IndicadorCard
          titulo="Finalizados"
          valor={resumo.finalizado}
          icone={<CheckCircle2 className="h-4 w-4" />}
          tom="emerald"
        />
        <IndicadorCard
          titulo="Fora do prazo"
          valor={resumo.fora_do_prazo}
          icone={<AlertTriangle className="h-4 w-4" />}
          tom="red"
          destaque={resumo.fora_do_prazo > 0}
        />
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center">
            <FiltroFiliais
              filiais={filiaisParaFiltro}
              selecionadas={filiais}
              onChange={setFiliais}
              confirmarAdicionar
              onAdicionarConhecida={(nova) => {
                setFiliaisConhecidas((prev) => {
                  if (prev.includes(nova)) return prev;
                  const merged = [...prev, nova];
                  try {
                    localStorage.setItem(
                      STORAGE_FILIAIS_CONHECIDAS,
                      JSON.stringify(merged)
                    );
                  } catch {
                    /* ignore */
                  }
                  return merged;
                });
              }}
            />
            <div className="relative max-w-md flex-1">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por pedido, cliente, montador..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            Atualiza a cada 60s
          </div>
        </CardContent>
      </Card>

      {/* Modo demonstração ativo */}
      {mockMode && (
        <Alert className="border-amber-300 bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <FlaskConical className="h-4 w-4" />
          <AlertTitle>Modo demonstração</AlertTitle>
          <AlertDescription>
            Exibindo dados fictícios apenas para visualização da interface.
            As ações (iniciar, concluir, desfazer) funcionam localmente e não
            afetam o banco. Desligue o switch para usar dados reais.
          </AlertDescription>
        </Alert>
      )}

      {/* Nenhuma filial selecionada */}
      {!mockMode && filiais.length === 0 && (
        <Alert>
          <Filter className="h-4 w-4" />
          <AlertTitle>Selecione ao menos uma filial</AlertTitle>
          <AlertDescription>
            Marque as filiais que você quer acompanhar no filtro acima. Somente
            cards das filiais selecionadas (inclusive os finalizados) serão
            carregados.
          </AlertDescription>
        </Alert>
      )}

      {/* View indisponível (view ainda não criada no banco) */}
      {viewIndisponivel && !mockMode && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>View de montagem ainda não disponível</AlertTitle>
          <AlertDescription>
            A view <code>vw_acompanhamento_montagem</code> não foi encontrada
            no banco. Assim que o desenvolvedor responsável a criar, os dados
            aparecerão automaticamente aqui.
          </AlertDescription>
        </Alert>
      )}

      {/* Erro */}
      {error && !viewIndisponivel && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Erro ao carregar montagens</AlertTitle>
          <AlertDescription>
            {(error as Error).message ?? "Tente novamente em instantes."}
          </AlertDescription>
        </Alert>
      )}

      {/* Abas Ativos / Stand by / Finalizados */}
      <Tabs value={aba} onValueChange={(v) => setAba(v as AbaFinal)}>
        <TabsList>
          <TabsTrigger value="ativos">
            Ativos
            <span className="ml-2 rounded bg-muted px-1.5 text-xs text-muted-foreground">
              {resumo.pendente + resumo.em_andamento}
            </span>
          </TabsTrigger>
          <TabsTrigger value="standby">
            Stand by
            <span className="ml-2 rounded bg-muted px-1.5 text-xs text-muted-foreground">
              {resumo.standby ?? 0}
            </span>
          </TabsTrigger>
          <TabsTrigger value="finalizados">
            Finalizados
            <span className="ml-2 rounded bg-muted px-1.5 text-xs text-muted-foreground">
              {resumo.finalizado}
            </span>
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Kanban */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Carregando montagens...
        </div>
      ) : aba === "ativos" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <KanbanColunaMontagem
            titulo="Pendente"
            descricao="Entregue, aguardando início da montagem"
            contador={porColuna.pendente.length}
            destaque={foraPrazoPorColuna.pendente}
            accent="slate"
            vazioLabel="Nenhum pedido pendente"
          >
            {porColuna.pendente.map((item) => (
              <CardPedidoMontagem
                key={item.pedido_id}
                item={item}
                onAbrir={handleAbrirDetalhe}
                onIniciar={handleIniciar}
                onConcluir={handleAbrirConcluir}
                onAdiar={handleAbrirAdiar}
                busy={busyId === item.pedido_id}
              />
            ))}
          </KanbanColunaMontagem>

          <KanbanColunaMontagem
            titulo="Em andamento"
            descricao="Montagem iniciada"
            contador={porColuna.em_andamento.length}
            destaque={foraPrazoPorColuna.em_andamento}
            accent="amber"
            vazioLabel="Nenhuma montagem em andamento"
          >
            {porColuna.em_andamento.map((item) => (
              <CardPedidoMontagem
                key={item.pedido_id}
                item={item}
                onAbrir={handleAbrirDetalhe}
                onConcluir={handleAbrirConcluir}
                onDesfazer={handleDesfazer}
                onAdiar={handleAbrirAdiar}
                busy={busyId === item.pedido_id}
              />
            ))}
          </KanbanColunaMontagem>
        </div>
      ) : aba === "standby" ? (
        <KanbanColunaMontagem
          titulo="Stand by"
          descricao="Montagens adiadas aguardando retorno"
          contador={porColuna.standby.length}
          accent="slate"
          vazioLabel="Nenhuma montagem em stand by"
        >
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {porColuna.standby.map((item) => (
              <CardPedidoMontagem
                key={item.pedido_id}
                item={item}
                onAbrir={handleAbrirDetalhe}
                onRetomar={handleRetomar}
                busy={busyId === item.pedido_id}
              />
            ))}
          </div>
        </KanbanColunaMontagem>
      ) : (
        <KanbanColunaMontagem
          titulo="Finalizado"
          descricao="Montagens concluídas"
          contador={porColuna.finalizado.length}
          accent="emerald"
          vazioLabel="Nenhuma montagem finalizada"
        >
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {porColuna.finalizado.map((item) => (
              <CardPedidoMontagem
                key={item.pedido_id}
                item={item}
                onAbrir={handleAbrirDetalhe}
                onDesfazer={handleDesfazer}
                busy={busyId === item.pedido_id}
              />
            ))}
          </div>
        </KanbanColunaMontagem>
      )}

      <DialogConcluirMontagem
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        item={dialogItem}
        onConfirm={handleConcluirConfirm}
      />

      <DialogAdiarMontagem
        open={adiarOpen}
        onOpenChange={setAdiarOpen}
        item={adiarItem}
        onConfirm={handleConfirmarAdiar}
      />

      <DialogDetalheMontagem
        open={detalheOpen}
        onOpenChange={setDetalheOpen}
        item={
          detalheId ? itens.find((i) => i.pedido_id === detalheId) ?? null : null
        }
        onIniciar={async (it) => {
          await handleIniciar(it);
        }}
        onConcluir={(it) => {
          setDetalheOpen(false);
          handleAbrirConcluir(it);
        }}
        onDesfazer={async (it) => {
          await handleDesfazer(it);
        }}
        onAdicionarComentario={handleAdicionarComentario}
        onAdiar={(it) => {
          setDetalheOpen(false);
          handleAbrirAdiar(it);
        }}
        onRetomar={async (it) => {
          await handleRetomar(it);
        }}
        busy={busyId === detalheId}
      />
    </div>
  );
}

interface IndicadorCardProps {
  titulo: string;
  valor: number;
  icone: React.ReactNode;
  tom: "slate" | "amber" | "emerald" | "red";
  destaque?: boolean;
}

function IndicadorCard({ titulo, valor, icone, tom, destaque }: IndicadorCardProps) {
  const map = {
    slate: "text-slate-700 dark:text-slate-200",
    amber: "text-amber-700 dark:text-amber-300",
    emerald: "text-emerald-700 dark:text-emerald-300",
    red: "text-red-700 dark:text-red-300",
  } as const;
  return (
    <Card
      className={
        destaque
          ? "border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20"
          : ""
      }
    >
      <CardHeader className="pb-2">
        <CardDescription className={`flex items-center gap-1.5 ${map[tom]}`}>
          {icone}
          {titulo}
        </CardDescription>
      </CardHeader>
      <CardContent className="pb-4">
        <CardTitle className={`text-3xl font-semibold ${map[tom]}`}>
          {valor}
        </CardTitle>
      </CardContent>
    </Card>
  );
}
