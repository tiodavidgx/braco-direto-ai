import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Fuel,
  Wrench,
  FileText,
  Car,
  DollarSign,
  ExternalLink,
  Loader2,
  Image,
  RefreshCw,
  User,
  CheckCircle,
  Circle,
  Trash2,
} from "lucide-react";
import { apiClient } from "@/services/api";
import { toast } from "sonner";

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
  motorista_nome: string | null;
  motorista_telefone: string | null;
  user_id: number | null;
  pago: boolean;
  pago_em: string | null;
  recebido: boolean;
  recebido_em: string | null;
  created_at: string;
}

interface ResumoMotorista {
  nome: string;
  qtd: number;
  total_valor: number;
}

const tipoConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  abastecimento: { label: "Abastecimento", icon: <Fuel className="h-4 w-4" />, color: "bg-green-100 text-green-800" },
  manutencao: { label: "Manutenção", icon: <Wrench className="h-4 w-4" />, color: "bg-orange-100 text-orange-800" },
  outros: { label: "Outros", icon: <FileText className="h-4 w-4" />, color: "bg-blue-100 text-blue-800" },
};

function formatarValor(v: number) {
  return `R$ ${v.toFixed(2).replace('.', ',')}`;
}

function formatarData(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function DespesasMotoristas() {
  const [lancamentos, setLancamentos] = useState<Lancamento[]>([]);
  const [total, setTotal] = useState(0);
  const [resumo, setResumo] = useState<ResumoMotorista[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [comprovanteUrls, setComprovanteUrls] = useState<string[]>([]);
  const [toggling, setToggling] = useState<number | null>(null);
  const [excluindo, setExcluindo] = useState<number | null>(null);
  const [confirmExcluir, setConfirmExcluir] = useState<number | null>(null);

  useEffect(() => {
    carregarDados();
  }, []);

  async function carregarDados() {
    setCarregando(true);
    try {
      const data = await apiClient.get<{
        lancamentos: Lancamento[];
        total: number;
        resumo_motoristas: ResumoMotorista[];
      }>("/lancamentos-motorista/admin", { limit: 500 });
      setLancamentos(data.lancamentos || []);
      setTotal(data.total || 0);
      setResumo(data.resumo_motoristas || []);
    } catch (e: any) {
      toast.error(e.message || "Erro ao carregar despesas");
    } finally {
      setCarregando(false);
    }
  }

  const totalValor = lancamentos.reduce((sum, l) => sum + l.valor, 0);

  async function handleExcluir(id: number) {
    setExcluindo(id);
    try {
      const res = await fetch(
        `${baseUrl}/api/v1/lancamentos-motorista/${id}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('braco_direto_token')}`,
          },
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro ao excluir');
      }
      setLancamentos((prev) => prev.filter((l) => l.id !== id));
      setTotal((prev) => prev - 1);
      toast.success('Despesa excluída com sucesso');
    } catch (e: any) {
      toast.error(e.message || 'Erro ao excluir despesa');
    } finally {
      setExcluindo(null);
      setConfirmExcluir(null);
    }
  }

  async function togglePago(id: number) {
    setToggling(id);
    try {
      const res = await fetch(
        `${baseUrl}/api/v1/lancamentos-motorista/${id}/pago`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('braco_direto_token')}`,
          },
        }
      );
      if (!res.ok) throw new Error('Erro ao atualizar');
      const data = await res.json();
      setLancamentos((prev) =>
        prev.map((l) =>
          l.id === id ? { ...l, pago: data.lancamento.pago, pago_em: data.lancamento.pago_em } : l
        )
      );
      toast.success(data.message);
    } catch (e: any) {
      toast.error(e.message || 'Erro ao atualizar status');
    } finally {
      setToggling(null);
    }
  }

  const baseUrl = (() => {
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      return window.location.origin;
    }
    return 'http://localhost:14001';
  })();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Car className="h-8 w-8" />
            Despesas dos Motoristas
          </h1>
          <p className="text-muted-foreground">
            Visualize todos os lançamentos e comprovantes dos motoristas
          </p>
        </div>
        <Button onClick={carregarDados} variant="outline" disabled={carregando}>
          <RefreshCw className={`h-4 w-4 mr-2 ${carregando ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {/* Resumo por motorista */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Geral</CardDescription>
            <CardTitle className="text-2xl">{formatarValor(totalValor)}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">{total} lançamento{total !== 1 ? 's' : ''}</p>
          </CardContent>
        </Card>
        {resumo.map((r) => (
          <Card key={r.nome}>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {r.nome}
              </CardDescription>
              <CardTitle className="text-2xl">{formatarValor(r.total_valor)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{r.qtd} lançamento{r.qtd !== 1 ? 's' : ''}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabela */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Todos os Lançamentos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {carregando ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Carregando...</span>
            </div>
          ) : lancamentos.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Car className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>Nenhuma despesa registrada</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">ID</TableHead>
                    <TableHead>Motorista</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Descrição</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead className="text-right">KM</TableHead>
                    <TableHead>Comprovantes</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Trello</TableHead>
                    <TableHead className="w-[60px]">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lancamentos.map((l) => {
                    const cfg = tipoConfig[l.tipo] || tipoConfig.outros;
                    return (
                      <TableRow key={l.id}>
                        <TableCell className="font-mono text-xs">#{l.id}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="font-medium text-sm">{l.motorista_nome || "—"}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={cfg.color}>
                            <span className="flex items-center gap-1">
                              {cfg.icon} {cfg.label}
                            </span>
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm">
                          {l.descricao || "—"}
                          {l.observacao && (
                            <span className="block text-xs text-muted-foreground truncate">
                              Obs: {l.observacao}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatarValor(l.valor)}
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          {l.km_atual ? l.km_atual.toLocaleString('pt-BR') : "—"}
                        </TableCell>
                        <TableCell>
                          {(l.comprovantes_urls?.length > 0) ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2"
                              onClick={() => setComprovanteUrls(l.comprovantes_urls.map((u: string) => `${baseUrl}${u}`))}
                            >
                              <Image className="h-4 w-4 mr-1" />
                              {l.comprovantes_urls.length > 1 ? `Ver (${l.comprovantes_urls.length})` : 'Ver'}
                            </Button>
                          ) : l.comprovante_url ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2"
                              onClick={() => setComprovanteUrls([`${baseUrl}${l.comprovante_url}`])}
                            >
                              <Image className="h-4 w-4 mr-1" />
                              Ver
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm whitespace-nowrap">
                          {formatarData(l.created_at)}
                        </TableCell>
                        <TableCell>
                          {l.recebido ? (
                            <Badge variant="secondary" className="bg-green-100 text-green-800 text-xs">
                              <CheckCircle className="h-3 w-3 mr-0.5" /> Recebido
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                              <Circle className="h-3 w-3 mr-0.5" /> Pendente
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {l.trello_card_url ? (
                            <a
                              href={l.trello_card_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-800"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2 text-red-500 hover:text-red-700 hover:bg-red-50"
                            disabled={excluindo === l.id}
                            onClick={() => setConfirmExcluir(l.id)}
                          >
                            {excluindo === l.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog confirmar exclusão */}
      <Dialog open={confirmExcluir !== null} onOpenChange={() => setConfirmExcluir(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Confirmar Exclusão</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Tem certeza que deseja excluir a despesa <strong>#{confirmExcluir}</strong>? Esta ação não pode ser desfeita.
          </p>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={() => setConfirmExcluir(null)}>Cancelar</Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={excluindo !== null}
              onClick={() => confirmExcluir && handleExcluir(confirmExcluir)}
            >
              {excluindo ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Trash2 className="h-4 w-4 mr-1" />}
              Excluir
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog para comprovantes */}
      <Dialog open={comprovanteUrls.length > 0} onOpenChange={() => setComprovanteUrls([])}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Comprovante{comprovanteUrls.length > 1 ? 's' : ''}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            {comprovanteUrls.map((url, i) => (
              <div key={i}>
                {comprovanteUrls.length > 1 && (
                  <p className="text-sm font-medium text-muted-foreground mb-1">Arquivo {i + 1}</p>
                )}
                {url.toLowerCase().endsWith('.pdf') ? (
                  <iframe src={url} className="w-full h-[500px] border rounded" />
                ) : (
                  <img
                    src={url}
                    alt={`Comprovante ${i + 1}`}
                    className="w-full max-h-[500px] object-contain rounded border"
                  />
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
