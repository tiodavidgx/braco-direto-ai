import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import {
  Zap, Calendar, DollarSign, Package, Send, Trash2, Eye, Search, RefreshCw,
  TrendingUp, Clock, CheckCircle2, Users, ArrowRight, Plus, ArrowLeft,
  ChevronDown, ChevronRight, AlertCircle,
} from "lucide-react";

// --- Tipos ---
interface MontadorResumo {
  id: number; nome: string; identificador: string;
  dias_envio: number[];
  qtd_pendentes: number; total_venda: number; total_comissao: number;
  periodo_inicio: string; periodo_fim: string;
  badge: string; badge_label: string;
  tipo_pagamento: string; terceirizada_nome: string | null;
  email_responsavel_nm: string | null;
}
interface BoletimDetalhe {
  id: number; boletim: string; data_montagem: string;
  nome_cliente: string; nome_produto: string; tipo_servico: string;
  valor_venda: number; valor_extra: number; comissao_calculada: number;
  status: string; motivo_valor_extra?: string; is_ajuste?: boolean;
}
interface DetalhesMontador {
  montador: any; periodo: { inicio: string; fim: string };
  boletins: BoletimDetalhe[]; total_venda: number; total_comissao: number;
}
type FiltroStatus = "todos" | "pronto" | "aguardando";

// --- Constantes ---
const fmt = (v: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);
const fd = (d: string) => { if (!d) return "-"; try { return new Date(d + "T00:00:00").toLocaleDateString("pt-BR"); } catch { return d; } };

// ============================================================
// PÁGINA DE DETALHE (tela cheia)
// ============================================================
function DetalheMontadorPage({ montadorId, periodoInicio, periodoFim, onBack }: { montadorId: number; periodoInicio?: string; periodoFim?: string; onBack: () => void }) {
  const [data, setData] = useState<DetalhesMontador | null>(null);
  const [loading, setLoading] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [enviarWhatsApp, setEnviarWhatsApp] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [novo, setNovo] = useState({ boletim: "", data: "", cliente: "", produto: "", tipo: "MONTAGEM", venda: "", extra: "", motivo: "" });
  const [adicionando, setAdicionando] = useState(false);

  const carregar = async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (periodoInicio) params.set('data_inicio_param', periodoInicio);
    if (periodoFim) params.set('data_fim_param', periodoFim);
    const qs = params.toString();
    try { setData(await apiClient.get<DetalhesMontador>(`/auto-envio/montadores/${montadorId}/boletins${qs ? '?' + qs : ''}`)); }
    catch { toast.error("Erro ao carregar"); }
    finally { setLoading(false); }
  };
  useEffect(() => { carregar(); }, [montadorId]);

  const forcarEnvio = async () => {
    setEnviando(true);
    try {
      if (isFuturo) {
        // Ciclo futuro → pré-aprovar (dispara automático no dia)
        await apiClient.post(`/auto-envio/montadores/${montadorId}/pre-aprovar`, {});
        toast.success("Pré-aprovado! O envio será automático no dia do vencimento.");
      } else {
        // Hoje ou vencido → enviar agora
        const body: any = {};
        if (cicloVencido && periodoFim) body.ate_data = periodoFim;
        await apiClient.post(`/auto-envio/montadores/${montadorId}/forcar-envio`, body);
        toast.success("Envio confirmado! Os relatórios foram disparados.");
      }
      onBack();
    }
    catch (e: any) { toast.error(e.message || "Erro"); }
    finally { setEnviando(false); }
  };

  const remover = async (id: number) => {
    try { await apiClient.delete(`/auto-envio/montadores/boletins/${id}`); toast.success("Removido"); carregar(); }
    catch (e: any) { toast.error(e.message || "Erro"); }
  };

  const adicionar = async () => {
    if (!novo.boletim.trim()) { toast.error("Boletim obrigatório"); return; }
    if (!novo.venda || parseFloat(novo.venda) <= 0) { toast.error("Valor venda obrigatório"); return; }
    setAdicionando(true);
    try {
      await apiClient.post("/ingestao/montadores", [{
        identificador_do_montador: data?.montador.identificador,
        nome_do_montador: data?.montador.nome,
        identificador_boletim_montagem: novo.boletim.trim(),
        data_da_montagem: novo.data || new Date().toISOString().split("T")[0],
        media_de_valor_venda: parseFloat(novo.venda),
        nome_do_cliente: novo.cliente, nome_produto: novo.produto,
        tipo_servico: novo.tipo,
        adicional: parseFloat(novo.extra) || 0, motivo_valor_extra: novo.motivo,
      }]);
      toast.success("Adicionado!");
      setNovo({ boletim: "", data: "", cliente: "", produto: "", tipo: "MONTAGEM", venda: "", extra: "", motivo: "" });
      setShowAddForm(false);
      carregar();
    } catch (e: any) { toast.error(e.message || "Erro"); }
    finally { setAdicionando(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" /></div>;
  if (!data) return <div className="text-center py-12 text-muted-foreground">Erro ao carregar dados</div>;

  const p = data.boletins.filter(b => b.status === "pendente").length;
  const hoje = new Date().getDate();
  const dias = data?.montador?.dias_envio_mes || [];
  const cicloVencido = periodoFim && new Date(periodoFim + "T00:00:00") < new Date();
  const podeEnviar = true; // Sempre pode confirmar
  const isFuturo = !cicloVencido && !dias.includes(hoje);
  const bq = data.boletins.filter(b => b.status === "bloqueado").length;
  const dp = data.boletins.filter(b => b.status === "duplicado").length;
  const ok = data.boletins.filter(b => b.status === "processado").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-1"><ArrowLeft className="h-4 w-4" /> Voltar</Button>
        <div>
          <h1 className="text-2xl font-bold">{data.montador.nome}</h1>
          <p className="text-sm text-muted-foreground">{fd(data.periodo.inicio)} → {fd(data.periodo.fim)} · {data.boletins.length} boletins · Vendas: {fmt(data.total_venda)} · Comissão: {fmt(data.total_comissao)}</p>
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" size="sm" onClick={carregar}><RefreshCw className="h-4 w-4" /></Button>
          <Button size="sm" onClick={forcarEnvio} disabled={enviando || p === 0} className="gap-2">
            <Send className="h-4 w-4" />
            {enviando ? "Enviando..." : 
             isFuturo ? `Confirmar Envio (${p}) — automático no dia` : 
             `Confirmar Envio (${p})`}
          </Button>
        </div>
      </div>

      {/* Mini stats */}
      <div className="grid grid-cols-4 gap-3">
        {[{ l: "Pendentes", v: p, c: "text-green-600" },{ l: "Bloqueados", v: bq, c: "text-red-600" },{ l: "Já enviados", v: dp, c: "text-orange-600" },{ l: "Processados", v: ok, c: "text-blue-600" }].map(s => (
          <Card key={s.l}><CardContent className="p-4 text-center"><p className={`text-2xl font-bold ${s.c}`}>{s.v}</p><p className="text-xs text-muted-foreground">{s.l}</p></CardContent></Card>
        ))}
      </div>

      {/* Adicionar Boletim */}
      <Card>
        <CardContent className="p-3">
          <Button variant="ghost" size="sm" className="gap-1 text-xs mb-2" onClick={() => setShowAddForm(!showAddForm)}>
            <Plus className="h-3 w-3" />{showAddForm ? "Cancelar" : "Adicionar Boletim"}
          </Button>
          {showAddForm && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div><Label className="text-xs">Boletim *</Label><Input className="h-7 text-xs" value={novo.boletim} onChange={e => setNovo({...novo, boletim: e.target.value})} /></div>
              <div><Label className="text-xs">Data</Label><Input className="h-7 text-xs" type="date" value={novo.data} onChange={e => setNovo({...novo, data: e.target.value})} /></div>
              <div><Label className="text-xs">Valor Venda *</Label><Input className="h-7 text-xs" type="number" step="0.01" value={novo.venda} onChange={e => setNovo({...novo, venda: e.target.value})} /></div>
              <div><Label className="text-xs">Tipo</Label><select className="flex h-7 w-full rounded-md border bg-background px-2 text-xs" value={novo.tipo} onChange={e => setNovo({...novo, tipo: e.target.value})}><option value="MONTAGEM">Montagem</option><option value="ASSISTENCIA_TECNICA">Assistência</option><option value="DESMONTAGEM">Desmontagem</option></select></div>
              <div><Label className="text-xs">Cliente</Label><Input className="h-7 text-xs" value={novo.cliente} onChange={e => setNovo({...novo, cliente: e.target.value})} /></div>
              <div><Label className="text-xs">Produto</Label><Input className="h-7 text-xs" value={novo.produto} onChange={e => setNovo({...novo, produto: e.target.value})} /></div>
              <div><Label className="text-xs">Custo Extra (R$)</Label><Input className="h-7 text-xs" type="number" step="0.01" value={novo.extra} onChange={e => setNovo({...novo, extra: e.target.value})} /></div>
              <div><Label className="text-xs">Motivo Extra</Label><Input className="h-7 text-xs" value={novo.motivo} onChange={e => setNovo({...novo, motivo: e.target.value})} /></div>
              <div className="col-span-full flex justify-end"><Button size="sm" className="text-xs h-7" onClick={adicionar} disabled={adicionando}>{adicionando ? "..." : "Adicionar"}</Button></div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabela */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="w-20">Boletim</TableHead><TableHead className="w-24">Data</TableHead>
                <TableHead>Cliente</TableHead><TableHead>Produto</TableHead><TableHead className="w-20">Tipo</TableHead>
                <TableHead className="text-right w-28">Venda</TableHead><TableHead className="text-right w-20">Extra</TableHead><TableHead className="w-28">Motivo</TableHead>
                <TableHead className="text-right w-28">Comissão</TableHead><TableHead className="w-28">Status</TableHead><TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.boletins.length === 0 ? (
                <TableRow><TableCell colSpan={11} className="text-center py-8 text-muted-foreground">Nenhum boletim</TableCell></TableRow>
              ) : data.boletins.map(b => (
                <TableRow key={b.id} className={b.status === "bloqueado" ? "opacity-50" : ""}>
                  <TableCell className="font-mono text-xs">{b.boletim}</TableCell>
                  <TableCell className="text-xs">{fd(b.data_montagem)}</TableCell>
                  <TableCell className="text-xs">{b.nome_cliente || "-"}</TableCell>
                  <TableCell className="text-xs">{b.nome_produto || "-"}</TableCell>
                  <TableCell className="text-xs"><Badge variant="outline" className="text-xs font-normal">{b.tipo_servico === "MONTAGEM" ? "Mont." : b.tipo_servico === "ASSISTENCIA_TECNICA" ? "Assist." : "Desm."}</Badge></TableCell>
                  <TableCell className="text-right text-xs">{fmt(b.valor_venda)}</TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {b.valor_extra ? <span title={b.motivo_valor_extra || ""}>{fmt(b.valor_extra)}{b.is_ajuste ? " ⚡" : ""}</span> : "-"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate" title={b.motivo_valor_extra || ""}>
                    {b.motivo_valor_extra || "-"}
                  </TableCell>
                  <TableCell className="text-right text-xs font-medium">{fmt(b.comissao_calculada)}</TableCell>
                  <TableCell>
                    {b.status === "pendente" && <Badge className="bg-green-500 text-xs">Pendente</Badge>}
                    {b.status === "bloqueado" && <Badge variant="destructive" className="text-xs">Blacklist</Badge>}
                    {b.status === "duplicado" && <Badge variant="outline" className="text-orange-500 border-orange-500 text-xs">Já enviado</Badge>}
                    {b.status === "processado" && <Badge variant="secondary" className="text-xs">OK</Badge>}
                  </TableCell>
                  <TableCell>
                    {b.status === "pendente" && <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => remover(b.id)}><Trash2 className="h-3 w-3 text-red-400 hover:text-red-600" /></Button>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Checkbox checked={enviarWhatsApp} onCheckedChange={c => setEnviarWhatsApp(c as boolean)} id="wpp" />
          <Label htmlFor="wpp" className="text-xs cursor-pointer">Notificar WhatsApp</Label>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// PÁGINA PRINCIPAL (lista de cards)
// ============================================================
export default function EnvioAutomaticoMontadores() {
  const [montadores, setMontadores] = useState<MontadorResumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filtroStatus, setFiltroStatus] = useState<FiltroStatus>("todos");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedPeriodoInicio, setSelectedPeriodoInicio] = useState<string | undefined>();
  const [selectedPeriodoFim, setSelectedPeriodoFim] = useState<string | undefined>();
  const [openMontadores, setOpenMontadores] = useState<Set<string>>(new Set());

  useEffect(() => { carregar(); }, []);

  const carregar = async () => {
    setLoading(true);
    try { setMontadores(await apiClient.get<MontadorResumo[]>("/auto-envio/montadores/resumo") || []); }
    catch { toast.error("Erro ao carregar"); }
    finally { setLoading(false); }
  };

  const filtered = useMemo(() => {
    let list = montadores.filter(m => m.qtd_pendentes > 0);
    if (search) list = list.filter(m => m.nome.toLowerCase().includes(search.toLowerCase()));
    if (filtroStatus !== "todos") list = list.filter(m => m.badge === filtroStatus);
    return list;
  }, [montadores, search, filtroStatus]);

  const stats = useMemo(() => ({
    total: montadores.length,
    prontos: montadores.filter(m => m.badge === "pronto").length,
    totalPendentes: montadores.reduce((s, m) => s + m.qtd_pendentes, 0),
    totalVenda: montadores.reduce((s, m) => s + m.total_venda, 0),
    totalComissao: montadores.reduce((s, m) => s + m.total_comissao, 0),
  }), [montadores]);

  const filtros: { value: FiltroStatus; label: string; count: number }[] = [
    { value: "todos", label: "Todos", count: stats.total },
    { value: "pronto", label: "Prontos", count: stats.prontos },
    { value: "aguardando", label: "Aguardando", count: montadores.filter(m => m.badge === "aguardando").length },
  ];

  // Tela de detalhe
  if (selectedId) {
    return <DetalheMontadorPage montadorId={selectedId} periodoInicio={selectedPeriodoInicio} periodoFim={selectedPeriodoFim} onBack={() => { setSelectedId(null); setSelectedPeriodoInicio(undefined); setSelectedPeriodoFim(undefined); carregar(); }} />;
  }

  // Loading
  if (loading) {
    return <div className="flex flex-col items-center justify-center h-96 gap-4"><div className="animate-spin h-10 w-10 border-4 border-primary border-t-transparent rounded-full" /><p className="text-muted-foreground text-sm">Carregando...</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-2xl font-bold flex items-center gap-2"><Zap className="h-6 w-6 text-amber-500" /> Envio Automático</h1><p className="text-muted-foreground mt-1">Relatórios enviados automaticamente nos dias configurados</p></div>
        <Button variant="outline" size="sm" onClick={carregar} className="gap-2"><RefreshCw className="h-4 w-4" /> Atualizar</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[{ icon: Users, l: "Montadores", v: stats.total, c: "blue" },{ icon: Package, l: "Boletins pendentes", v: stats.totalPendentes, c: "green" },{ icon: DollarSign, l: "Em vendas", v: fmt(stats.totalVenda), c: "amber", cur: true },{ icon: TrendingUp, l: "Em comissões", v: fmt(stats.totalComissao), c: "purple", cur: true }].map(s => (
          <Card key={s.l} className={`bg-${s.c}-50/50 border-${s.c}-200`}>
            <CardContent className="p-4 flex items-center gap-3"><div className={`p-2 bg-${s.c}-100 rounded-lg`}><s.icon className={`h-5 w-5 text-${s.c}-600`} /></div><div><p className={`text-xl font-bold ${s.cur ? "text-sm" : ""}`}>{s.v}</p><p className="text-xs text-muted-foreground">{s.l}</p></div></CardContent>
          </Card>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" /><Input placeholder="Buscar montador..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" /></div>
        <div className="flex gap-1 flex-wrap">{filtros.map(f => <Button key={f.value} variant={filtroStatus === f.value ? "default" : "outline"} size="sm" onClick={() => setFiltroStatus(f.value)} className="text-xs h-8">{f.label} ({f.count})</Button>)}</div>
      </div>

      {/* Accordion por Montador */}
      {filtered.length === 0 ? (
        <Card><CardContent className="py-16 text-center"><Zap className="h-16 w-16 mx-auto mb-4 text-muted-foreground/30" /><p className="text-lg font-medium text-muted-foreground">{montadores.length === 0 ? "Nenhum montador com envio automático" : "Nenhum resultado"}</p></CardContent></Card>
      ) : (
        <div className="space-y-3">
          {(() => {
            // Agrupar por montador (nome + id)
            const grupos = new Map<string, MontadorResumo[]>();
            for (const m of filtered) {
              const key = `${m.nome}__${m.id}`;
              if (!grupos.has(key)) grupos.set(key, []);
              grupos.get(key)!.push(m);
            }
            // Ordenar ciclos dentro de cada grupo: mais antigo primeiro
            for (const [key, ciclos] of grupos) {
              ciclos.sort((a, b) => a.periodo_inicio.localeCompare(b.periodo_inicio));
            }
            return Array.from(grupos.entries()).map(([key, ciclos]) => {
              const nome = ciclos[0].nome;
              const isOpen = openMontadores.has(key);
              const totalPendentes = ciclos.reduce((s, c) => s + c.qtd_pendentes, 0);
              const totalVenda = ciclos.reduce((s, c) => s + c.total_venda, 0);
              const totalComissao = ciclos.reduce((s, c) => s + c.total_comissao, 0);
              const hasPronto = ciclos.some(c => c.badge === "pronto");

              return (
                <Card key={key} className={hasPronto ? "border-l-4 border-l-green-500" : ""}>
                  {/* Header do Montador */}
                  <div
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30"
                    onClick={() => {
                      const next = new Set(openMontadores);
                      if (next.has(key)) next.delete(key); else next.add(key);
                      setOpenMontadores(next);
                    }}
                  >
                    <div className="flex items-center gap-3">
                      {isOpen ? <ChevronDown className="h-5 w-5 text-muted-foreground" /> : <ChevronRight className="h-5 w-5 text-muted-foreground" />}
                      <div>
                        <h3 className="font-semibold text-lg">{nome}</h3>
                        <p className="text-xs text-muted-foreground">
                          {ciclos.length} ciclo(s) · {totalPendentes} boletins pendentes · Vendas {fmt(totalVenda)} · Comissão {fmt(totalComissao)}
                          {ciclos[0].tipo_pagamento === "terceirizada" && ciclos[0].terceirizada_nome && (
                            <span className="ml-2 text-blue-600">Via: {ciclos[0].terceirizada_nome}</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {hasPronto && <Badge className="bg-green-500 text-xs">Pronto</Badge>}
                      <Badge variant="outline" className="text-xs">{ciclos[0].dias_envio?.join(", ")}</Badge>
                    </div>
                  </div>

                  {/* Ciclos (expandido) */}
                  {isOpen && (
                    <div className="border-t px-4 py-3 space-y-2 bg-muted/20">
                      {(() => {
                        const fechados = ciclos.filter(c => c.badge === "fechado");
                        const ativos = ciclos.filter(c => c.badge !== "fechado");
                        
                        // Card mesclado de ciclos fechados
                        const mesclado = fechados.length > 0 ? {
                          qtd: fechados.reduce((s, c) => s + c.qtd_pendentes, 0),
                          venda: fechados.reduce((s, c) => s + c.total_venda, 0),
                          comissao: fechados.reduce((s, c) => s + c.total_comissao, 0),
                          ate: fechados[fechados.length - 1]?.periodo_fim,
                          ciclos: fechados.length,
                        } : null;

                        return (
                          <>
                            {/* Card mesclado */}
                            {mesclado && (
                              <div className="flex items-center justify-between p-3 rounded border-l-4 border-l-red-400 bg-red-50/40 cursor-pointer hover:shadow-sm transition-shadow"
                                onClick={() => { setSelectedId(ciclos[0].id); setSelectedPeriodoInicio("2020-01-01"); setSelectedPeriodoFim(mesclado.ate); }}>
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                  <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="text-sm font-medium">{mesclado.ciclos} ciclos vencidos (até {fd(mesclado.ate)})</span>
                                      <Badge variant="destructive" className="text-xs">Não enviado</Badge>
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-4 shrink-0 ml-4">
                                  <div className="text-right">
                                    <p className="text-sm font-semibold">{mesclado.qtd} bol.</p>
                                    <p className="text-xs text-muted-foreground">{fmt(mesclado.venda)}</p>
                                  </div>
                                  <Button variant="destructive" size="sm" className="h-7 text-xs gap-1" onClick={e => { e.stopPropagation(); setSelectedId(ciclos[0].id); setSelectedPeriodoInicio("2020-01-01"); setSelectedPeriodoFim(mesclado.ate); }}>
                                    <Send className="h-3 w-3" /> Enviar Tudo
                                  </Button>
                                </div>
                              </div>
                            )}
                            
                            {/* Cards individuais (aguardando/pronto) */}
                            {ativos.map((c, idx) => {
                              const isPronto = c.badge === "pronto";
                              const isAguardando = c.badge === "aguardando";
                              const bc = isPronto ? "border-l-green-500 bg-green-50/40" : "border-l-amber-500 bg-amber-50/40";
                              const Icon = isPronto ? CheckCircle2 : Clock;
                              const ic = isPronto ? "text-green-500" : "text-amber-500";
                              return (
                                <div key={idx}
                                  className={`flex items-center justify-between p-3 rounded border-l-4 ${bc} cursor-pointer hover:shadow-sm transition-shadow`}
                                  onClick={() => { setSelectedId(c.id); setSelectedPeriodoInicio(c.periodo_inicio); setSelectedPeriodoFim(c.periodo_fim); }}>
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <Icon className={`h-5 w-5 shrink-0 ${ic}`} />
                                    <div className="min-w-0">
                                      <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium">{fd(c.periodo_inicio)} → {fd(c.periodo_fim)}</span>
                                        <Badge variant={isPronto ? "default" : "outline"} className="text-xs">{c.badge_label}</Badge>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-4 shrink-0 ml-4">
                                    <div className="text-right">
                                      <p className="text-sm font-semibold">{c.qtd_pendentes} bol.</p>
                                      <p className="text-xs text-muted-foreground">{fmt(c.total_venda)}</p>
                                    </div>
                                    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={e => { e.stopPropagation(); setSelectedId(c.id); setSelectedPeriodoInicio(c.periodo_inicio); setSelectedPeriodoFim(c.periodo_fim); }}>
                                      <Eye className="h-3 w-3" /> Abrir
                                    </Button>
                                  </div>
                                </div>
                              );
                            })}
                          </>
                        );
                      })()}
                    </div>
                  )}
                </Card>
              );
            });
          })()}
        </div>
      )}
    </div>
  );
}
