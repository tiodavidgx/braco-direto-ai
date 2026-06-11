import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Fuel,
  Wrench,
  FileText,
  Upload,
  Check,
  Loader2,
  Trash2,
  History,
  Car,
  DollarSign,
  LogOut,
  CheckCircle,
  Clock,
  Pencil,
  X,
  Eye
} from "lucide-react";
import { toast } from "sonner";

const API_BASE = (() => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl !== '') {
    if (envUrl.startsWith('/')) return `${window.location.origin}${envUrl}`;
    return envUrl;
  }
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `${window.location.origin}/api/v1`;
  }
  return 'http://localhost:14001/api/v1';
})();

const MOTORISTA_TOKEN_KEY = "braco_motorista_token";
const MOTORISTA_USER_KEY = "braco_motorista_user";

interface Lancamento {
  id: number;
  tipo: string;
  descricao: string | null;
  valor: number;
  km_atual: number | null;
  observacao: string | null;
  comprovante_url: string | null;
  comprovantes_urls: string[];
  trello_card_id: string | null;
  trello_card_url: string | null;
  pago: boolean;
  pago_em: string | null;
  recebido: boolean;
  recebido_em: string | null;
  created_at: string;
}

const tipoConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  abastecimento: { label: "Abastecimento", icon: <Fuel className="h-4 w-4" />, color: "bg-green-100 text-green-800" },
  manutencao: { label: "Manutenção/Reparo", icon: <Wrench className="h-4 w-4" />, color: "bg-orange-100 text-orange-800" },
  outros: { label: "Outros", icon: <FileText className="h-4 w-4" />, color: "bg-blue-100 text-blue-800" },
};

export default function LancamentosMotorista() {
  // Auth state
  const [token, setToken] = useState<string | null>(localStorage.getItem(MOTORISTA_TOKEN_KEY));
  const [userName, setUserName] = useState<string>((() => {
    try { return JSON.parse(localStorage.getItem(MOTORISTA_USER_KEY) || "{}").nome || ""; } catch { return ""; }
  })());
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // Form state
  const [tipo, setTipo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [valor, setValor] = useState("");
  const [kmAtual, setKmAtual] = useState("");
  const [observacao, setObservacao] = useState("");
  const [comprovantes, setComprovantes] = useState<File[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  // Edit state
  const [editando, setEditando] = useState<Lancamento | null>(null);
  const [editTipo, setEditTipo] = useState("");
  const [editDescricao, setEditDescricao] = useState("");
  const [editValor, setEditValor] = useState("");
  const [editKmAtual, setEditKmAtual] = useState("");
  const [editObservacao, setEditObservacao] = useState("");
  const [editComprovantes, setEditComprovantes] = useState<File[]>([]);
  const [editManterUrls, setEditManterUrls] = useState<string[]>([]);
  const [salvandoEdicao, setSalvandoEdicao] = useState(false);
  const [excluindo, setExcluindo] = useState<number | null>(null);

  // Preview state
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // History state
  const [lancamentos, setLancamentos] = useState<Lancamento[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (token) carregarHistorico();
    else setCarregando(false);
  }, [token]);

  function getAuthHeaders(): Record<string, string> {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      toast.error("Preencha email e senha");
      return;
    }
    setLoginLoading(true);
    try {
      const res = await fetch(`${API_BASE}/sistema/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: loginEmail, password: loginPassword }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Email ou senha incorretos");
      }
      const data = await res.json();
      if (data.user?.role !== "motorista" && data.user?.role !== "admin") {
        throw new Error("Acesso negado. Esta página é exclusiva para motoristas.");
      }
      setToken(data.access_token);
      setUserName(data.user.nome);
      localStorage.setItem(MOTORISTA_TOKEN_KEY, data.access_token);
      localStorage.setItem(MOTORISTA_USER_KEY, JSON.stringify(data.user));
      toast.success(`Bem-vindo, ${data.user.nome}!`);
    } catch (err: any) {
      toast.error(err.message || "Erro ao fazer login");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    setToken(null);
    setUserName("");
    localStorage.removeItem(MOTORISTA_TOKEN_KEY);
    localStorage.removeItem(MOTORISTA_USER_KEY);
    setLancamentos([]);
    setTotal(0);
  }

  async function carregarHistorico() {
    setCarregando(true);
    try {
      const res = await fetch(`${API_BASE}/lancamentos-motorista?limit=100`, {
        headers: getAuthHeaders(),
      });
      if (res.status === 401) { handleLogout(); return; }
      if (!res.ok) throw new Error("Erro ao carregar histórico");
      const data = await res.json();
      setLancamentos(data.lancamentos || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error("Erro ao carregar histórico:", e);
    } finally {
      setCarregando(false);
    }
  }

  function limparForm() {
    setTipo("");
    setDescricao("");
    setValor("");
    setKmAtual("");
    setObservacao("");
    setComprovantes([]);
    // Reset file input
    const fileInput = document.getElementById("comprovante-input") as HTMLInputElement;
    if (fileInput) fileInput.value = "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!tipo) {
      toast.error("Selecione o tipo de despesa");
      return;
    }
    if (!valor || parseFloat(valor) <= 0) {
      toast.error("Informe um valor válido");
      return;
    }
    if (!kmAtual) {
      toast.error("Informe o KM atual");
      return;
    }
    if (!comprovantes.length) {
      toast.error("Anexe o comprovante/foto");
      return;
    }
    if (tipo !== 'abastecimento' && !descricao) {
      toast.error("Informe a descrição da despesa");
      return;
    }

    setEnviando(true);
    try {
      const formData = new FormData();
      formData.append("tipo", tipo);
      formData.append("valor", valor);
      if (descricao) formData.append("descricao", descricao);
      if (kmAtual) formData.append("km_atual", kmAtual);
      if (observacao) formData.append("observacao", observacao);
      comprovantes.forEach((file) => formData.append("comprovantes", file));

      const res = await fetch(`${API_BASE}/lancamentos-motorista`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      });

      if (res.status === 401) { handleLogout(); return; }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Erro ao registrar despesa");
      }

      toast.success("Despesa registrada com sucesso!");
      setEnviado(true);
      limparForm();
      carregarHistorico();

      // Reset success state after 5s
      setTimeout(() => setEnviado(false), 5000);
    } catch (err: any) {
      toast.error(err.message || "Erro ao registrar despesa");
    } finally {
      setEnviando(false);
    }
  }

  function formatarValor(v: number) {
    return `R$ ${v.toFixed(2).replace('.', ',')}`;
  }

  function formatarData(iso: string) {
    const d = new Date(iso);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  function dentroDosPrazoDias(created_at: string, dias: number = 5): boolean {
    const criado = new Date(created_at);
    const agora = new Date();
    const diff = (agora.getTime() - criado.getTime()) / (1000 * 60 * 60 * 24);
    return diff <= dias;
  }

  function abrirEdicao(l: Lancamento) {
    setEditando(l);
    setEditTipo(l.tipo);
    setEditDescricao(l.descricao || "");
    setEditValor(String(l.valor));
    setEditKmAtual(l.km_atual ? String(l.km_atual) : "");
    setEditObservacao(l.observacao || "");
    setEditComprovantes([]);
    const urls = l.comprovantes_urls?.length > 0 ? l.comprovantes_urls : l.comprovante_url ? [l.comprovante_url] : [];
    setEditManterUrls(urls);
  }

  function fecharEdicao() {
    setEditando(null);
    setEditComprovantes([]);
    setEditManterUrls([]);
  }

  async function handleSalvarEdicao(e: React.FormEvent) {
    e.preventDefault();
    if (!editando) return;

    if (!editTipo) { toast.error("Selecione o tipo"); return; }
    if (!editValor || parseFloat(editValor) <= 0) { toast.error("Valor inválido"); return; }
    if (!editKmAtual) { toast.error("Informe o KM"); return; }
    if (editTipo !== 'abastecimento' && !editDescricao) { toast.error("Informe a descrição"); return; }

    setSalvandoEdicao(true);
    try {
      const formData = new FormData();
      formData.append("tipo", editTipo);
      formData.append("valor", editValor);
      formData.append("km_atual", editKmAtual);
      if (editDescricao) formData.append("descricao", editDescricao);
      if (editObservacao) formData.append("observacao", editObservacao);
      formData.append("manter_urls", JSON.stringify(editManterUrls));
      if (editComprovantes.length > 0) {
        editComprovantes.forEach((file) => formData.append("comprovantes", file));
      }

      const res = await fetch(`${API_BASE}/lancamentos-motorista/${editando.id}`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: formData,
      });

      if (res.status === 401) { handleLogout(); return; }
      if (res.status === 403) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Prazo de edição expirado");
        return;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const msg = typeof err.detail === 'string' ? err.detail
          : Array.isArray(err.detail) ? err.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ')
          : "Erro ao editar";
        throw new Error(msg);
      }

      toast.success("Despesa atualizada!");
      fecharEdicao();
      carregarHistorico();
    } catch (err: any) {
      toast.error(err.message || "Erro ao editar despesa");
    } finally {
      setSalvandoEdicao(false);
    }
  }

  async function handleExcluir(id: number) {
    if (!confirm("Tem certeza que deseja excluir esta despesa?")) return;
    setExcluindo(id);
    try {
      const res = await fetch(`${API_BASE}/lancamentos-motorista/${id}`, {
        method: "DELETE",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      });
      if (res.status === 401) { handleLogout(); return; }
      if (res.status === 403) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Prazo de exclusão expirado");
        return;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Erro ao excluir");
      }
      toast.success("Despesa excluída!");
      carregarHistorico();
    } catch (err: any) {
      toast.error(err.message || "Erro ao excluir despesa");
    } finally {
      setExcluindo(null);
    }
  }

  // Sum total value
  const totalValor = lancamentos.reduce((sum, l) => sum + l.valor, 0);

  // Login screen
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <Car className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-xl">Braço Direito</CardTitle>
            <CardDescription>Acesso Motorista - Lançamento de Despesas</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="login-email">Email</Label>
                <Input
                  id="login-email"
                  type="email"
                  placeholder="seu@email.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  disabled={loginLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="login-password">Senha</Label>
                <Input
                  id="login-password"
                  type="password"
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  disabled={loginLoading}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loginLoading}>
                {loginLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Entrando...
                  </>
                ) : (
                  "Entrar"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                <Car className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900">Braço Direito</h1>
                <p className="text-sm text-slate-500">Olá, {userName}</p>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout} title="Sair">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>

      <div className="w-full max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Form Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Nova Despesa
            </CardTitle>
            <CardDescription>
              Registre suas despesas de combustível, manutenção e outros
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Tipo */}
              <div className="space-y-2">
                <Label htmlFor="tipo">Tipo de Despesa *</Label>
                <select
                  id="tipo"
                  value={tipo}
                  onChange={(e) => setTipo(e.target.value)}
                  className="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value="">Selecione o tipo...</option>
                  <option value="abastecimento">⛽ Abastecimento</option>
                  <option value="manutencao">🔧 Manutenção / Reparo</option>
                  <option value="outros">📄 Outros</option>
                </select>
              </div>

              {/* Valor + KM */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="valor">Valor (R$) *</Label>
                  <Input
                    id="valor"
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="0,00"
                    value={valor}
                    onChange={(e) => setValor(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="km">KM Atual *</Label>
                  <Input
                    id="km"
                    type="number"
                    min="0"
                    placeholder="Ex: 45230"
                    value={kmAtual}
                    onChange={(e) => setKmAtual(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Descrição */}
              <div className="space-y-2">
                <Label htmlFor="descricao">
                  Descrição {tipo !== 'abastecimento' ? '*' : ''}
                </Label>
                <Input
                  id="descricao"
                  placeholder={tipo === 'abastecimento' ? 'Ex: Gasolina comum - Posto Shell' : tipo === 'manutencao' ? 'Ex: Troca de óleo + filtro' : 'Descreva a despesa'}
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                />
              </div>

              {/* Observação */}
              <div className="space-y-2">
                <Label htmlFor="obs">Observação</Label>
                <Textarea
                  id="obs"
                  placeholder="Alguma observação adicional..."
                  rows={2}
                  value={observacao}
                  onChange={(e) => setObservacao(e.target.value)}
                />
              </div>

              {/* Comprovante */}
              <div className="space-y-2">
                <Label htmlFor="comprovante-input">Comprovante / Foto *</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="comprovante-input"
                    type="file"
                    accept="image/*,.pdf"
                    multiple
                    onChange={(e) => setComprovantes(Array.from(e.target.files || []))}
                    className="flex-1"
                  />
                </div>
                {comprovantes.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {comprovantes.map((f, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        <Upload className="h-3 w-3 mr-1" />
                        {f.name.length > 20 ? f.name.slice(0, 20) + '...' : f.name}
                      </Badge>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  Selecione uma ou mais fotos do cupom/recibo
                </p>
              </div>

              {/* Submit */}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={enviando}
              >
                {enviando ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Enviando...
                  </>
                ) : enviado ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Enviado com sucesso!
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Registrar Despesa
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Histórico */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Histórico
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              {total > 0 && (
                <Badge variant="outline" className="text-sm">
                  {total} lançamento{total !== 1 ? 's' : ''}
                </Badge>
              )}
              {totalValor > 0 && (
                <Badge className="text-sm bg-primary">
                  Total: {formatarValor(totalValor)}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {carregando ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Carregando...</span>
              </div>
            ) : lancamentos.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Car className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>Nenhuma despesa registrada ainda</p>
              </div>
            ) : (
              <div className="space-y-3">
                {lancamentos.map((l) => {
                  const cfg = tipoConfig[l.tipo] || tipoConfig.outros;
                  return (
                    <div
                      key={l.id}
                      className="p-3 rounded-lg border bg-white hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`flex items-center justify-center h-9 w-9 rounded-full shrink-0 ${cfg.color}`}>
                          {cfg.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium text-sm truncate">
                              {cfg.label}
                            </span>
                            <span className="font-semibold text-sm whitespace-nowrap">
                              {formatarValor(l.valor)}
                            </span>
                          </div>
                          {l.descricao && (
                            <p className="text-sm text-muted-foreground truncate">{l.descricao}</p>
                          )}
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <span>{formatarData(l.created_at)}</span>
                        {l.km_atual && <span>KM: {l.km_atual.toLocaleString('pt-BR')}</span>}
                        <label
                          className={`inline-flex items-center gap-1 text-xs cursor-pointer select-none rounded-full px-2 py-0.5 transition-colors ${
                            l.recebido ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                          }`}
                          onClick={async (e) => {
                            e.preventDefault();
                            try {
                              const res = await fetch(`${API_BASE}/lancamentos-motorista/${l.id}/recebido`, {
                                method: 'PATCH',
                                headers: getAuthHeaders(),
                              });
                              if (res.status === 401) { handleLogout(); return; }
                              if (!res.ok) throw new Error('Erro');
                              const data = await res.json();
                              setLancamentos(prev => prev.map(x => x.id === l.id ? { ...x, recebido: data.lancamento.recebido, recebido_em: data.lancamento.recebido_em } : x));
                              toast.success(data.lancamento.recebido ? 'Marcado como recebido' : 'Desmarcado');
                            } catch {
                              toast.error('Erro ao atualizar');
                            }
                          }}
                        >
                          <span className={`inline-flex items-center justify-center h-3.5 w-3.5 rounded border ${
                            l.recebido ? 'bg-green-600 border-green-600' : 'border-yellow-500 bg-white'
                          }`}>
                            {l.recebido && <Check className="h-2.5 w-2.5 text-white" />}
                          </span>
                          {l.recebido ? 'Recebido' : 'Pendente'}
                        </label>
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                        {(l.comprovantes_urls?.length > 0 ? l.comprovantes_urls : l.comprovante_url ? [l.comprovante_url] : []).map((url: string, i: number) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setPreviewUrl(`${window.location.origin}${url}`)}
                            className="text-blue-600 hover:underline flex items-center gap-0.5 cursor-pointer"
                          >
                            <Eye className="h-3 w-3" /> {l.comprovantes_urls?.length > 1 ? `Foto ${i+1}` : 'Comprovante'}
                          </button>
                        ))}
                      </div>
                      {/* Botões editar/excluir (até 5 dias) */}
                      {dentroDosPrazoDias(l.created_at) && (
                        <div className="mt-2 flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => abrirEdicao(l)}
                          >
                            <Pencil className="h-3 w-3 mr-1" /> Editar
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                            disabled={excluindo === l.id}
                            onClick={() => handleExcluir(l.id)}
                          >
                            {excluindo === l.id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <><Trash2 className="h-3 w-3 mr-1" /> Excluir</>
                            )}
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Modal de Edição */}
        {editando && (
          <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center">
            <div className="bg-white w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-t-xl sm:rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-lg">Editar Despesa #{editando.id}</h3>
                <Button variant="ghost" size="sm" onClick={fecharEdicao}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <form onSubmit={handleSalvarEdicao} className="space-y-4">
                <div className="space-y-2">
                  <Label>Tipo de Despesa *</Label>
                  <select
                    value={editTipo}
                    onChange={(e) => setEditTipo(e.target.value)}
                    className="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  >
                    <option value="">Selecione...</option>
                    <option value="abastecimento">⛽ Abastecimento</option>
                    <option value="manutencao">🔧 Manutenção / Reparo</option>
                    <option value="outros">📄 Outros</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Valor (R$) *</Label>
                    <Input type="number" step="0.01" value={editValor} onChange={(e) => setEditValor(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>KM Atual *</Label>
                    <Input type="number" value={editKmAtual} onChange={(e) => setEditKmAtual(e.target.value)} />
                  </div>
                </div>
                {editTipo !== 'abastecimento' && (
                  <div className="space-y-2">
                    <Label>Descrição *</Label>
                    <Input value={editDescricao} onChange={(e) => setEditDescricao(e.target.value)} />
                  </div>
                )}
                <div className="space-y-2">
                  <Label>Observação</Label>
                  <Textarea value={editObservacao} onChange={(e) => setEditObservacao(e.target.value)} rows={2} />
                </div>
                <div className="space-y-2">
                  <Label>Comprovantes atuais</Label>
                  {editManterUrls.length > 0 ? (
                    <div className="space-y-2">
                      {editManterUrls.map((url, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 rounded border bg-gray-50">
                          <button
                            type="button"
                            className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer"
                            onClick={() => setPreviewUrl(`${window.location.origin}${url}`)}
                          >
                            {url.match(/\.(jpg|jpeg|png|webp|heic)$/i) ? (
                              <img
                                src={`${window.location.origin}${url}`}
                                alt={`Comprovante ${i + 1}`}
                                className="h-12 w-12 object-cover rounded"
                              />
                            ) : (
                              <div className="h-12 w-12 flex items-center justify-center bg-gray-200 rounded text-xs">PDF</div>
                            )}
                            <span className="text-xs text-blue-600 hover:underline truncate flex items-center gap-1">
                              <Eye className="h-3 w-3" /> Foto {i + 1}
                            </span>
                          </button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                            onClick={() => setEditManterUrls(prev => prev.filter((_, idx) => idx !== i))}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">Nenhum comprovante</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>Adicionar novos comprovantes</Label>
                  <Input
                    type="file"
                    accept="image/*,.pdf"
                    multiple
                    onChange={(e) => setEditComprovantes(Array.from(e.target.files || []))}
                  />
                  {editComprovantes.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {editComprovantes.map((f, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          <Upload className="h-3 w-3 mr-1" />
                          {f.name.length > 20 ? f.name.slice(0, 20) + '...' : f.name}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" className="flex-1" onClick={fecharEdicao}>
                    Cancelar
                  </Button>
                  <Button type="submit" className="flex-1" disabled={salvandoEdicao}>
                    {salvandoEdicao ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Salvando...</>
                    ) : (
                      <><Check className="h-4 w-4 mr-2" /> Salvar</>
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal de Visualização */}
        {previewUrl && (
          <div
            className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4"
            onClick={() => setPreviewUrl(null)}
          >
            <div
              className="relative bg-white rounded-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-3 border-b">
                <span className="font-medium text-sm">Visualização</span>
                <div className="flex items-center gap-2">
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Abrir em nova aba
                  </a>
                  <Button variant="ghost" size="sm" onClick={() => setPreviewUrl(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="flex-1 overflow-auto flex items-center justify-center p-2 min-h-[300px]">
                {previewUrl.match(/\.(jpg|jpeg|png|webp|heic)$/i) ? (
                  <img
                    src={previewUrl}
                    alt="Comprovante"
                    className="max-w-full max-h-[75vh] object-contain rounded"
                  />
                ) : (
                  <iframe
                    src={previewUrl}
                    title="Visualizar PDF"
                    className="w-full h-[75vh] rounded"
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
