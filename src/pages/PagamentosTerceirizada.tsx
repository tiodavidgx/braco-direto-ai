import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { DollarSign, Building2, TrendingUp, TrendingDown } from "lucide-react";

interface PagamentosResponse {
  terceirizada: {
    id: number;
    nome: string;
    percentual_montagem: number;
  };
  periodo: string;
  montadores: {
    montador_id: number;
    montador_nome: string;
    qtd_boletins: number;
    total_venda: number;
    comissao_montador: number;
    comissao_terceirizada: number;
  }[];
  resumo: {
    total_venda: number;
    nm_paga_terceirizada: number;
    terc_paga_montadores: number;
    margem_terceirizada: number;
  };
}

interface TerceirizadaOption {
  id: number;
  nome: string;
}

export default function PagamentosTerceirizada() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PagamentosResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [terceirizadas, setTerceirizadas] = useState<TerceirizadaOption[]>([]);
  const [selectedId, setSelectedId] = useState(id || "");

  const now = new Date();
  const [mes, setMes] = useState(now.getMonth() + 1);
  const [ano, setAno] = useState(now.getFullYear());

  useEffect(() => {
    carregarTerceirizadas();
  }, []);

  useEffect(() => {
    if (selectedId) {
      carregarPagamentos();
    }
  }, [selectedId, mes, ano]);

  const carregarTerceirizadas = async () => {
    try {
      const data = await apiClient.get<TerceirizadaOption[]>("/terceirizadas?ativo=true");
      setTerceirizadas(data || []);
    } catch (error) {
      toast.error("Erro ao carregar terceirizadas");
    }
  };

  const carregarPagamentos = async () => {
    setLoading(true);
    try {
      const result = await apiClient.get<PagamentosResponse>(
        `/terceirizadas/${selectedId}/pagamentos?mes=${mes}&ano=${ano}`
      );
      setData(result);
    } catch (error) {
      toast.error("Erro ao carregar pagamentos");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Pagamentos - Terceirizada</h1>
        <p className="text-muted-foreground mt-1">
          Visão dos valores a receber da Novo Mundo e a pagar aos montadores
        </p>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="py-3">
          <div className="flex gap-4 items-end">
            <div className="w-64">
              <Label>Terceirizada</Label>
              <Select value={selectedId} onValueChange={setSelectedId}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione..." />
                </SelectTrigger>
                <SelectContent>
                  {terceirizadas.map((t) => (
                    <SelectItem key={t.id} value={t.id.toString()}>{t.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-24">
              <Label>Mês</Label>
              <Select value={mes.toString()} onValueChange={(v) => setMes(parseInt(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <SelectItem key={m} value={m.toString()}>
                      {String(m).padStart(2, "0")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-24">
              <Label>Ano</Label>
              <Select value={ano.toString()} onValueChange={(v) => setAno(parseInt(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[2024, 2025, 2026, 2027].map((a) => (
                    <SelectItem key={a} value={a.toString()}>{a}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {!selectedId ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Selecione uma terceirizada para ver os pagamentos
          </CardContent>
        </Card>
      ) : data ? (
        <>
          {/* Cards de resumo */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  NM → {data.terceirizada.nome}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(data.resumo.nm_paga_terceirizada)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Valor que a Novo Mundo paga para a terceirizada
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingDown className="h-4 w-4 text-red-500" />
                  {data.terceirizada.nome} → Montadores
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-red-600">
                  {formatCurrency(data.resumo.terc_paga_montadores)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Valor que a terceirizada paga aos montadores
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-blue-500" />
                  Margem Líquida
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className={`text-2xl font-bold ${data.resumo.margem_terceirizada >= 0 ? "text-blue-600" : "text-red-600"}`}>
                  {formatCurrency(data.resumo.margem_terceirizada)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {data.resumo.margem_terceirizada >= 0 ? "Lucro" : "Prejuízo"} da terceirizada
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tabela de montadores */}
          <Card>
            <CardHeader>
              <CardTitle>Montadores Vinculados</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Montador</TableHead>
                    <TableHead className="text-center">Qtd Boletins</TableHead>
                    <TableHead className="text-right">Venda Total</TableHead>
                    <TableHead className="text-right">Comissão Montador</TableHead>
                    <TableHead className="text-right">Comissão Terc.</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.montadores.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        Nenhum montador com boletins neste período
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.montadores.map((m, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{m.montador_nome}</TableCell>
                        <TableCell className="text-center">{m.qtd_boletins}</TableCell>
                        <TableCell className="text-right">{formatCurrency(m.total_venda)}</TableCell>
                        <TableCell className="text-right text-red-600">{formatCurrency(m.comissao_montador)}</TableCell>
                        <TableCell className="text-right text-green-600">{formatCurrency(m.comissao_terceirizada)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
