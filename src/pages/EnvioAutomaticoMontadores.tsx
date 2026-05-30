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
} from "lucide-react";

// --- Tipos ---
interface MontadorResumo {
  id: number; nome: string; identificador: string;
  dias_envio: number[]; proximos_dias: number[];
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
function DetalheMontadorPage({ montadorId, onBack }: { montadorId: number; onBack: () => void }) {
  const [data, setData] = useState<DetalhesMontador | null>(null);
  const [loading, setLoading] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [enviarWhatsApp, setEnviarWhatsApp] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [novo, setNovo] = useState({ boletim: "", data: "", cliente: "", produto: "", tipo: "MONTAGEM", venda: "", extra: "", motivo: "" });
  const [adicionando, setAdicionando] = useState(false);

  const carregar = async () => {
    setLoading(true);
    try { setData(await apiClient.get<DetalhesMontador>(`/auto-envio/montadores/${montadorId}/boletins`)); }
    catch { toast.error("Erro ao carregar"); }
    finally { setLoading(false); }
  };
  useEffect(() => { carregar(); }, [montadorId]);

  const forcarEnvio = async () => {
    setEnviando(true);
    try { await apiClient.post(`/auto-envio/montadores/${montadorId}/forcar-envio`, {}); toast.success("Envio confirmado! Os relatórios foram disparados."); onBack(); }
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
            {enviando ? "Enviando..." : `Confirmar Envio (${p})`}
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
    return <DetalheMontadorPage montadorId={selectedId} onBack={() => { setSelectedId(null); carregar(); }} />;
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

      {/* Grid */}
      {filtered.length === 0 ? (
        <Card><CardContent className="py-16 text-center"><Zap className="h-16 w-16 mx-auto mb-4 text-muted-foreground/30" /><p className="text-lg font-medium text-muted-foreground">{montadores.length === 0 ? "Nenhum montador com envio automático" : "Nenhum resultado"}</p></CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(m => {
            const isPronto = m.badge === "pronto", isAguardando = m.badge === "aguardando";
            const bc = isPronto ? "border-l-green-500" : isAguardando ? "border-l-amber-500" : "border-l-gray-300";
            const Icon = isPronto ? CheckCircle2 : isAguardando ? Clock : Package;
            const ic = isPronto ? "text-green-500" : isAguardando ? "text-amber-500" : "text-gray-400";
            return (
              <Card key={m.id} className={`cursor-pointer hover:shadow-lg transition-all border-l-4 ${bc} hover:-translate-y-0.5`} onClick={() => setSelectedId(m.id)}>
                <CardHeader className="pb-2"><div className="flex items-center justify-between"><CardTitle className="text-base truncate">{m.nome}</CardTitle><Badge variant={isPronto ? "default" : isAguardando ? "outline" : "secondary"} className="text-xs">{m.badge_label}</Badge></div></CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-2 text-sm"><Calendar className="h-4 w-4 text-muted-foreground shrink-0" /><span className="text-muted-foreground">Dias: {m.dias_envio?.length ? m.dias_envio.join(", ") : "—"}</span></div>
                  <div className="flex items-center gap-2"><Icon className={`h-5 w-5 ${ic}`} /><span className="text-lg font-semibold">{m.qtd_pendentes}</span><span className="text-sm text-muted-foreground">pendentes</span></div>
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t"><div><p className="text-xs text-muted-foreground">Vendas</p><p className="text-sm font-semibold">{fmt(m.total_venda)}</p></div><div><p className="text-xs text-muted-foreground">Comissão</p><p className="text-sm font-semibold text-green-700">{fmt(m.total_comissao)}</p></div></div>
                  {m.tipo_pagamento === "terceirizada" && m.terceirizada_nome && <div className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded"><ArrowRight className="h-3 w-3" /> Via: {m.terceirizada_nome}</div>}
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1"><span>{fd(m.periodo_inicio)} → {fd(m.periodo_fim)}</span><Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={e => { e.stopPropagation(); setSelectedId(m.id); }}><Eye className="h-3 w-3" /> Abrir</Button></div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
