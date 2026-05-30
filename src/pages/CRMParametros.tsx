import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  Settings,
  Tag,
  Palette,
  Plus,
  Loader2,
  CheckCircle2,
  Trash2,
  GripHorizontal,
  ChevronRight,
  ArrowLeft,
  ListChecks,
  Monitor,
  Building2,
} from "lucide-react";
import { crmService } from "@/services/crm.service";
import { Link } from "react-router-dom";

const STATUS_CORES = [
  { value: "gray", label: "Cinza", tw: "bg-gray-400" },
  { value: "blue", label: "Azul", tw: "bg-blue-500" },
  { value: "amber", label: "Amarelo", tw: "bg-amber-500" },
  { value: "orange", label: "Laranja", tw: "bg-orange-500" },
  { value: "emerald", label: "Verde", tw: "bg-emerald-500" },
  { value: "red", label: "Vermelho", tw: "bg-red-500" },
  { value: "purple", label: "Roxo", tw: "bg-purple-500" },
  { value: "pink", label: "Rosa", tw: "bg-pink-500" },
];

function corToTw(cor: string) {
  return STATUS_CORES.find((c) => c.value === cor)?.tw || "bg-gray-400";
}

export default function CRMParametros() {
  const [tab, setTab] = useState<"areas" | "status" | "resolucoes" | "plataformas" | "credenciadas">("areas");
  const [areas, setAreas] = useState<{ id: number; nome: string; ativo: boolean; ordem: number }[]>([]);
  const [motivos, setMotivos] = useState<{ id: number; nome: string; ativo: boolean; ordem: number; area_id: number | null }[]>([]);
  const [statusList, setStatusList] = useState<{ id: number; nome: string; cor: string; ativo: boolean; ordem: number; area_id: number | null }[]>([]);
  const [resolucoes, setResolucoes] = useState<{ id: number; nome: string; ativo: boolean; ordem: number }[]>([]);
  const [plataformas, setPlataformas] = useState<{ id: number; nome: string; ativo: boolean; ordem: number }[]>([]);
  const [credenciadas, setCredenciadas] = useState<{ id: number; nome: string; ativo: boolean; ordem: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [novaArea, setNovaArea] = useState("");
  const [expandedAreaId, setExpandedAreaId] = useState<number | null>(null);
  const [motivoInputByArea, setMotivoInputByArea] = useState<Record<number, string>>({});
  const [novoStatus, setNovoStatus] = useState("");
  const [novoStatusCor, setNovoStatusCor] = useState("gray");
  const [novoStatusAreaId, setNovoStatusAreaId] = useState<number | null>(null);
  const [novaResolucao, setNovaResolucao] = useState("");
  const [novaPlataforma, setNovaPlataforma] = useState("");
  const [novaCredenciada, setNovaCredenciada] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [a, m, s, r, p, c] = await Promise.all([crmService.getAreas(), crmService.getMotivos(), crmService.getStatusDetalhe(), crmService.getResolucoes(), crmService.getPlataformas(), crmService.getCredenciadas()]);
      setAreas(a);
      setMotivos(m);
      setStatusList(s);
      setResolucoes(r);
      setPlataformas(p);
      setCredenciadas(c);
    } catch {
      toast.error("Erro ao carregar parâmetros");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAddArea = async () => {
    const nome = novaArea.trim();
    if (!nome) return;
    try {
      await crmService.createArea(nome);
      setNovaArea("");
      await loadData();
      toast.success("Área adicionada");
    } catch {
      toast.error("Erro ao adicionar área");
    }
  };

  const handleAddMotivoInline = async (areaId: number) => {
    const nome = (motivoInputByArea[areaId] || "").trim();
    if (!nome) return;
    try {
      await crmService.createMotivo(nome, areaId);
      setMotivoInputByArea((prev) => ({ ...prev, [areaId]: "" }));
      await loadData();
      toast.success("Motivo adicionado");
    } catch {
      toast.error("Erro ao adicionar motivo");
    }
  };

  const handleAddStatus = async () => {
    const nome = novoStatus.trim();
    if (!nome) return;
    try {
      await crmService.createStatusDetalhe(nome, novoStatusCor, novoStatusAreaId || undefined);
      setNovoStatus("");
      setNovoStatusCor("gray");
      setNovoStatusAreaId(null);
      await loadData();
      toast.success("Status adicionado");
    } catch {
      toast.error("Erro ao adicionar status");
    }
  };

  const handleAddResolucao = async () => {
    const nome = novaResolucao.trim();
    if (!nome) return;
    try {
      await crmService.createResolucao(nome);
      setNovaResolucao("");
      await loadData();
      toast.success("Resolução adicionada");
    } catch {
      toast.error("Erro ao adicionar resolução");
    }
  };

  const handleToggle = async (type: "area" | "motivo" | "status" | "resolucao" | "plataforma" | "credenciada", id: number, ativo: boolean) => {
    try {
      if (type === "area") await crmService.updateArea(id, { ativo });
      else if (type === "motivo") await crmService.updateMotivo(id, { ativo });
      else if (type === "status") await crmService.updateStatusDetalhe(id, { ativo });
      else if (type === "plataforma") await crmService.updatePlataforma(id, { ativo });
      else if (type === "credenciada") await crmService.updateCredenciada(id, { ativo });
      else await crmService.updateResolucao(id, { ativo });
      await loadData();
    } catch {
      toast.error("Erro ao atualizar");
    }
  };

  const handleSaveEdit = async (type: "area" | "motivo" | "status" | "resolucao" | "plataforma" | "credenciada", id: number) => {
    const nome = editingName.trim();
    if (!nome) return;
    try {
      if (type === "area") await crmService.updateArea(id, { nome });
      else if (type === "motivo") await crmService.updateMotivo(id, { nome });
      else if (type === "status") await crmService.updateStatusDetalhe(id, { nome });
      else if (type === "plataforma") await crmService.updatePlataforma(id, { nome });
      else if (type === "credenciada") await crmService.updateCredenciada(id, { nome });
      else await crmService.updateResolucao(id, { nome });
      setEditingId(null);
      setEditingName("");
      await loadData();
      toast.success("Atualizado");
    } catch {
      toast.error("Erro ao atualizar");
    }
  };

  const handleDeleteArea = async (id: number) => {
    if (!confirm("Excluir esta área?")) return;
    try {
      await crmService.deleteArea(id);
      await loadData();
      toast.success("Área excluída");
    } catch {
      toast.error("Erro ao excluir");
    }
  };

  const handleDeleteMotivo = async (id: number) => {
    if (!confirm("Excluir este motivo?")) return;
    try {
      await crmService.deleteMotivo(id);
      await loadData();
      toast.success("Motivo excluído");
    } catch {
      toast.error("Erro ao excluir");
    }
  };

  const handleDeleteResolucao = async (id: number) => {
    if (!confirm("Excluir esta resolução?")) return;
    try {
      await crmService.deleteResolucao(id);
      await loadData();
      toast.success("Resolução excluída");
    } catch {
      toast.error("Erro ao excluir");
    }
  };

  const handleAddPlataforma = async () => {
    const nome = novaPlataforma.trim();
    if (!nome) return;
    try {
      await crmService.createPlataforma(nome);
      setNovaPlataforma("");
      await loadData();
      toast.success("Plataforma adicionada");
    } catch {
      toast.error("Erro ao adicionar plataforma");
    }
  };

  const handleDeletePlataforma = async (id: number) => {
    if (!confirm("Excluir esta plataforma?")) return;
    try {
      await crmService.deletePlataforma(id);
      await loadData();
      toast.success("Plataforma excluída");
    } catch {
      toast.error("Erro ao excluir");
    }
  };

  const handleAddCredenciada = async () => {
    const nome = novaCredenciada.trim();
    if (!nome) return;
    try {
      await crmService.createCredenciada(nome);
      setNovaCredenciada("");
      await loadData();
      toast.success("Credenciada adicionada");
    } catch {
      toast.error("Erro ao adicionar credenciada");
    }
  };

  const handleDeleteCredenciada = async (id: number) => {
    if (!confirm("Excluir esta credenciada?")) return;
    try {
      await crmService.deleteCredenciada(id);
      await loadData();
      toast.success("Credenciada excluída");
    } catch {
      toast.error("Erro ao excluir");
    }
  };

  const handleUpdateCor = async (id: number, cor: string) => {
    try {
      await crmService.updateStatusDetalhe(id, { cor });
      await loadData();
    } catch {
      toast.error("Erro ao atualizar cor");
    }
  };

  const activeCount = tab === "areas"
    ? areas.filter((a) => a.ativo).length
    : tab === "status"
    ? statusList.filter((s) => s.ativo).length
    : tab === "plataformas"
    ? plataformas.filter((p) => p.ativo).length
    : tab === "credenciadas"
    ? credenciadas.filter((c) => c.ativo).length
    : resolucoes.filter((r) => r.ativo).length;
  const totalCount = tab === "areas"
    ? areas.length
    : tab === "status"
    ? statusList.length
    : tab === "plataformas"
    ? plataformas.length
    : tab === "credenciadas"
    ? credenciadas.length
    : resolucoes.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/crm">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Settings className="h-6 w-6 text-primary" />
              Parâmetros do CRM
            </h1>
            <p className="text-sm text-muted-foreground">Configure as áreas, motivos, status e resoluções disponíveis no sistema</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            {activeCount} ativos de {totalCount}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-muted w-fit flex-wrap">
        <button
          onClick={() => { setTab("areas"); setEditingId(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "areas" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Tag className="h-4 w-4" />
          Áreas
          <Badge variant="outline" className="text-[10px] px-1.5 h-5 ml-1">{areas.length}</Badge>
        </button>
        <button
          onClick={() => { setTab("status"); setEditingId(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "status" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Palette className="h-4 w-4" />
          Status Atual
          <Badge variant="outline" className="text-[10px] px-1.5 h-5 ml-1">{statusList.length}</Badge>
        </button>
        <button
          onClick={() => { setTab("resolucoes"); setEditingId(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "resolucoes" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <ListChecks className="h-4 w-4" />
          Tipo de Resolução
          <Badge variant="outline" className="text-[10px] px-1.5 h-5 ml-1">{resolucoes.length}</Badge>
        </button>
        <button
          onClick={() => { setTab("plataformas"); setEditingId(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "plataformas" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Monitor className="h-4 w-4" />
          Plataformas
          <Badge variant="outline" className="text-[10px] px-1.5 h-5 ml-1">{plataformas.length}</Badge>
        </button>
        <button
          onClick={() => { setTab("credenciadas"); setEditingId(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "credenciadas" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="h-4 w-4" />
          Credenciadas
          <Badge variant="outline" className="text-[10px] px-1.5 h-5 ml-1">{credenciadas.length}</Badge>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="max-w-2xl">
          {/* ---- ÁREAS (crm_areas - parent) ---- */}
          {tab === "areas" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Nova área..."
                  value={novaArea}
                  onChange={(e) => setNovaArea(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddArea()}
                  className="h-9 flex-1"
                />
                <Button size="sm" className="h-9 px-4" onClick={handleAddArea} disabled={!novaArea.trim()}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Adicionar
                </Button>
              </div>

              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-muted/40 border-b flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Áreas cadastradas</span>
                  <span className="text-[11px] text-muted-foreground">Clique para expandir motivos · Duplo clique no nome para editar</span>
                </div>
                <ScrollArea className="h-[60vh]">
                  <div className="divide-y">
                    {areas.map((a) => {
                      const isOpen = expandedAreaId === a.id;
                      const motivosDaArea = motivos.filter((m) => m.area_id === a.id);
                      return (
                      <div key={a.id} className={a.ativo ? "bg-card" : "bg-muted/30 opacity-60"}>
                        <div className="flex items-center gap-3 px-4 py-3">
                          <button
                            type="button"
                            onClick={() => setExpandedAreaId(isOpen ? null : a.id)}
                            className="shrink-0 text-muted-foreground hover:text-foreground transition-transform"
                            aria-label={isOpen ? "Recolher" : "Expandir"}
                          >
                            <ChevronRight className={`h-4 w-4 transition-transform ${isOpen ? "rotate-90" : ""}`} />
                          </button>
                          {editingId === a.id ? (
                            <Input
                              className="h-8 text-sm flex-1"
                              value={editingName}
                              onChange={(e) => setEditingName(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleSaveEdit("area", a.id);
                                if (e.key === "Escape") { setEditingId(null); setEditingName(""); }
                              }}
                              autoFocus
                            />
                          ) : (
                            <span
                              className="text-sm flex-1 cursor-pointer hover:text-primary transition-colors"
                              onDoubleClick={() => { setEditingId(a.id); setEditingName(a.nome); }}
                            >
                              {a.nome}
                              <Badge variant="outline" className="text-[10px] px-1.5 h-5 ml-2 font-normal">{motivosDaArea.length} motivos</Badge>
                            </span>
                          )}
                          {editingId === a.id ? (
                            <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => handleSaveEdit("area", a.id)}>
                              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            </Button>
                          ) : (
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={a.ativo}
                                onCheckedChange={(v) => handleToggle("area", a.id, v)}
                              />
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                                onClick={() => handleDeleteArea(a.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          )}
                        </div>
                        {isOpen && (
                          <div className="bg-muted/20 border-t px-4 py-3 space-y-2">
                            <div className="flex items-center gap-2">
                              <Input
                                placeholder="Novo motivo..."
                                value={motivoInputByArea[a.id] || ""}
                                onChange={(e) => setMotivoInputByArea((prev) => ({ ...prev, [a.id]: e.target.value }))}
                                onKeyDown={(e) => e.key === "Enter" && handleAddMotivoInline(a.id)}
                                className="h-8 flex-1 text-sm"
                              />
                              <Button
                                size="sm"
                                className="h-8 px-3"
                                onClick={() => handleAddMotivoInline(a.id)}
                                disabled={!(motivoInputByArea[a.id] || "").trim()}
                              >
                                <Plus className="h-3.5 w-3.5 mr-1" />
                                Adicionar
                              </Button>
                            </div>
                            <div className="space-y-1">
                              {motivosDaArea.map((m) => (
                                <div
                                  key={m.id}
                                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md bg-card border ${
                                    m.ativo ? "" : "opacity-60"
                                  }`}
                                >
                                  {editingId === m.id ? (
                                    <Input
                                      className="h-7 text-sm flex-1"
                                      value={editingName}
                                      onChange={(e) => setEditingName(e.target.value)}
                                      onKeyDown={(e) => {
                                        if (e.key === "Enter") handleSaveEdit("motivo", m.id);
                                        if (e.key === "Escape") { setEditingId(null); setEditingName(""); }
                                      }}
                                      autoFocus
                                    />
                                  ) : (
                                    <span
                                      className="text-sm flex-1 cursor-pointer hover:text-primary transition-colors"
                                      onDoubleClick={() => { setEditingId(m.id); setEditingName(m.nome); }}
                                    >
                                      {m.nome}
                                    </span>
                                  )}
                                  {editingId === m.id ? (
                                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => handleSaveEdit("motivo", m.id)}>
                                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                                    </Button>
                                  ) : (
                                    <>
                                      <Switch
                                        checked={m.ativo}
                                        onCheckedChange={(v) => handleToggle("motivo", m.id, v)}
                                      />
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                                        onClick={() => handleDeleteMotivo(m.id)}
                                      >
                                        <Trash2 className="h-3.5 w-3.5" />
                                      </Button>
                                    </>
                                  )}
                                </div>
                              ))}
                              {motivosDaArea.length === 0 && (
                                <p className="text-xs text-muted-foreground py-2 px-1">Nenhum motivo cadastrado para esta área.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                      );
                    })}
                    {areas.length === 0 && (
                      <p className="text-center text-sm text-muted-foreground py-12">Nenhuma área cadastrada</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}



          {/* ---- STATUS ---- */}
          {tab === "status" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                <Select value={novoStatusAreaId ? String(novoStatusAreaId) : ""} onValueChange={(v) => setNovoStatusAreaId(Number(v))}>
                  <SelectTrigger className="h-9 w-[180px]">
                    <SelectValue placeholder="Motivo (opcional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {motivos.filter((m) => m.ativo).map((m) => (
                      <SelectItem key={m.id} value={String(m.id)}>{m.nome}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Novo status..."
                  value={novoStatus}
                  onChange={(e) => setNovoStatus(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddStatus()}
                  className="h-9 flex-1"
                />
                <Select value={novoStatusCor} onValueChange={setNovoStatusCor}>
                  <SelectTrigger className="h-9 w-[120px] text-sm">
                    <div className="flex items-center gap-2">
                      <div className={`h-3 w-3 rounded-full ${corToTw(novoStatusCor)}`} />
                      <SelectValue />
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_CORES.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        <div className="flex items-center gap-2">
                          <div className={`h-3 w-3 rounded-full ${c.tw}`} />
                          {c.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button size="sm" className="h-9 px-4" onClick={handleAddStatus} disabled={!novoStatus.trim()}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Adicionar
                </Button>
              </div>

              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-muted/40 border-b flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Status cadastrados</span>
                  <span className="text-[11px] text-muted-foreground">Duplo clique para editar · A cor define o indicador visual</span>
                </div>
                <ScrollArea className="h-[60vh]">
                  <div className="divide-y">
                    {statusList.map((s) => {
                      const parentMotivo = motivos.find((m) => m.id === s.area_id);
                      return (
                      <div
                        key={s.id}
                        className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                          s.ativo ? "bg-card" : "bg-muted/30 opacity-60"
                        }`}
                      >
                        <div className={`h-3.5 w-3.5 rounded-full shrink-0 ${corToTw(s.cor)}`} />
                        {editingId === s.id ? (
                          <Input
                            className="h-8 text-sm flex-1"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveEdit("status", s.id);
                              if (e.key === "Escape") { setEditingId(null); setEditingName(""); }
                            }}
                            autoFocus
                          />
                        ) : (
                          <div className="flex-1 cursor-pointer hover:text-primary transition-colors" onDoubleClick={() => { setEditingId(s.id); setEditingName(s.nome); }}>
                            <span className="text-sm">{s.nome}</span>
                            {parentMotivo && <span className="text-xs text-muted-foreground ml-2">({parentMotivo.nome})</span>}
                          </div>
                        )}
                        {editingId === s.id ? (
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => handleSaveEdit("status", s.id)}>
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          </Button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Select value={s.cor} onValueChange={(v) => handleUpdateCor(s.id, v)}>
                              <SelectTrigger className="h-8 w-[110px] text-xs">
                                <div className="flex items-center gap-2">
                                  <div className={`h-2.5 w-2.5 rounded-full ${corToTw(s.cor)}`} />
                                  <SelectValue />
                                </div>
                              </SelectTrigger>
                              <SelectContent>
                                {STATUS_CORES.map((c) => (
                                  <SelectItem key={c.value} value={c.value}>
                                    <div className="flex items-center gap-2">
                                      <div className={`h-3 w-3 rounded-full ${c.tw}`} />
                                      {c.label}
                                    </div>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Switch
                              checked={s.ativo}
                              onCheckedChange={(v) => handleToggle("status", s.id, v)}
                            />
                          </div>
                        )}
                      </div>
                      );
                    })}
                    {statusList.length === 0 && (
                      <p className="text-center text-sm text-muted-foreground py-12">Nenhum status cadastrado</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}

          {/* ---- RESOLUÇÕES ---- */}
          {tab === "resolucoes" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Nova resolução..."
                  value={novaResolucao}
                  onChange={(e) => setNovaResolucao(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddResolucao()}
                  className="h-9 flex-1"
                />
                <Button size="sm" className="h-9 px-4" onClick={handleAddResolucao} disabled={!novaResolucao.trim()}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Adicionar
                </Button>
              </div>

              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-muted/40 border-b flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Tipos de resolução cadastrados</span>
                  <span className="text-[11px] text-muted-foreground">Duplo clique para editar</span>
                </div>
                <ScrollArea className="h-[60vh]">
                  <div className="divide-y">
                    {resolucoes.map((r) => (
                      <div
                        key={r.id}
                        className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                          r.ativo ? "bg-card" : "bg-muted/30 opacity-60"
                        }`}
                      >
                        <GripHorizontal className="h-4 w-4 text-muted-foreground/30 shrink-0" />
                        {editingId === r.id ? (
                          <Input
                            className="h-8 text-sm flex-1"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveEdit("resolucao", r.id);
                              if (e.key === "Escape") { setEditingId(null); setEditingName(""); }
                            }}
                            autoFocus
                          />
                        ) : (
                          <span
                            className="text-sm flex-1 cursor-pointer hover:text-primary transition-colors"
                            onDoubleClick={() => { setEditingId(r.id); setEditingName(r.nome); }}
                          >
                            {r.nome}
                          </span>
                        )}
                        {editingId === r.id ? (
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => handleSaveEdit("resolucao", r.id)}>
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          </Button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={r.ativo}
                              onCheckedChange={(v) => handleToggle("resolucao", r.id, v)}
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeleteResolucao(r.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                    {resolucoes.length === 0 && (
                      <p className="text-center text-sm text-muted-foreground py-12">Nenhuma resolução cadastrada</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}

          {/* ---- PLATAFORMAS ---- */}
          {tab === "plataformas" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Nova plataforma..."
                  value={novaPlataforma}
                  onChange={(e) => setNovaPlataforma(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddPlataforma()}
                  className="h-9 flex-1"
                />
                <Button size="sm" className="h-9 px-4" onClick={handleAddPlataforma} disabled={!novaPlataforma.trim()}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Adicionar
                </Button>
              </div>

              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-muted/40 border-b flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Plataformas cadastradas</span>
                  <span className="text-[11px] text-muted-foreground">Duplo clique para editar</span>
                </div>
                <ScrollArea className="h-[60vh]">
                  <div className="divide-y">
                    {plataformas.map((p) => (
                      <div
                        key={p.id}
                        className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                          p.ativo ? "bg-card" : "bg-muted/30 opacity-60"
                        }`}
                      >
                        <GripHorizontal className="h-4 w-4 text-muted-foreground/30 shrink-0" />
                        {editingId === p.id ? (
                          <Input
                            className="h-8 text-sm flex-1"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveEdit("plataforma", p.id);
                              if (e.key === "Escape") { setEditingId(null); setEditingName(""); }
                            }}
                            autoFocus
                          />
                        ) : (
                          <span
                            className="text-sm flex-1 cursor-pointer hover:text-primary transition-colors"
                            onDoubleClick={() => { setEditingId(p.id); setEditingName(p.nome); }}
                          >
                            {p.nome}
                          </span>
                        )}
                        {editingId === p.id ? (
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => handleSaveEdit("plataforma", p.id)}>
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          </Button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={p.ativo}
                              onCheckedChange={(v) => handleToggle("plataforma", p.id, v)}
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeletePlataforma(p.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                    {plataformas.length === 0 && (
                      <p className="text-center text-sm text-muted-foreground py-12">Nenhuma plataforma cadastrada</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}

          {/* ---- CREDENCIADAS ---- */}
          {tab === "credenciadas" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Nova credenciada..."
                  value={novaCredenciada}
                  onChange={(e) => setNovaCredenciada(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddCredenciada()}
                  className="h-9 flex-1"
                />
                <Button size="sm" className="h-9 px-4" onClick={handleAddCredenciada} disabled={!novaCredenciada.trim()}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Adicionar
                </Button>
              </div>

              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-muted/40 border-b flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Credenciadas cadastradas</span>
                  <span className="text-[11px] text-muted-foreground">Duplo clique para editar</span>
                </div>
                <ScrollArea className="h-[60vh]">
                  <div className="divide-y">
                    {credenciadas.map((c) => (
                      <div
                        key={c.id}
                        className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                          c.ativo ? "bg-card" : "bg-muted/30 opacity-60"
                        }`}
                      >
                        <GripHorizontal className="h-4 w-4 text-muted-foreground/30 shrink-0" />
                        {editingId === c.id ? (
                          <Input
                            className="h-8 text-sm flex-1"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveEdit("credenciada", c.id);
                              if (e.key === "Escape") { setEditingId(null); setEditingName(""); }
                            }}
                            autoFocus
                          />
                        ) : (
                          <span
                            className="text-sm flex-1 cursor-pointer hover:text-primary transition-colors"
                            onDoubleClick={() => { setEditingId(c.id); setEditingName(c.nome); }}
                          >
                            {c.nome}
                          </span>
                        )}
                        {editingId === c.id ? (
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => handleSaveEdit("credenciada", c.id)}>
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          </Button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={c.ativo}
                              onCheckedChange={(v) => handleToggle("credenciada", c.id, v)}
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeleteCredenciada(c.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                    {credenciadas.length === 0 && (
                      <p className="text-center text-sm text-muted-foreground py-12">Nenhuma credenciada cadastrada</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
