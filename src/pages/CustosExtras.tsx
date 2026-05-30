import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { 
  Plus, 
  Trash2, 
  Edit, 
  Loader2, 
  DollarSign,
  CheckCircle,
  Clock,
  Search,
  AlertCircle
} from "lucide-react";

interface CustoExtra {
  id: number;
  montador_id: number | null;
  identificador_montador: string;
  identificador_boletim: string;
  valor: number;
  motivo: string;
  observacao: string | null;
  status: string;
  cadastrado_por: number | null;
  cadastrado_por_nome: string | null;
  montador_nome: string | null;
  processado_em: string | null;
  created_at: string;
}

export default function CustosExtras() {
  const { user, isAdmin } = useAuth();
  const [custos, setCustos] = useState<CustoExtra[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedCusto, setSelectedCusto] = useState<CustoExtra | null>(null);
  const [filtroStatus, setFiltroStatus] = useState<string>("todos");
  const [submitting, setSubmitting] = useState(false);

  // Função para verificar se o usuário pode editar/excluir um custo
  const podeEditarCusto = (custo: CustoExtra) => {
    if (isAdmin) return true;
    return custo.cadastrado_por === user?.id;
  };
  
  const [formData, setFormData] = useState({
    identificador_montador: "",
    identificador_boletim: "",
    valor: "",
    motivo: "",
    observacao: "",
    gerar_boletim: false
  });

  useEffect(() => {
    carregarCustos();
  }, [filtroStatus]);

  const carregarCustos = async () => {
    setLoading(true);
    try {
      const params = filtroStatus !== "todos" ? `?status=${filtroStatus}` : "";
      const response = await apiClient.get<{ data: CustoExtra[]; total: number }>(
        `/custos-extras${params}`
      );
      setCustos(response.data);
    } catch (error) {
      console.error("Erro ao carregar custos:", error);
      toast.error("Erro ao carregar custos extras");
    } finally {
      setLoading(false);
    }
  };

  const criarCusto = async () => {
    // Se não está gerando boletim, precisa ter um identificador informado
    if (!formData.identificador_montador || !formData.valor || !formData.motivo) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }
    
    // Se não está gerando boletim automático, precisa informar o boletim
    if (!formData.gerar_boletim && !formData.identificador_boletim) {
      toast.error("Informe o identificador do boletim ou marque 'Gerar Boletim de Ajuste'");
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiClient.post<CustoExtra>("/custos-extras", {
        identificador_montador: formData.identificador_montador,
        identificador_boletim: formData.gerar_boletim ? "" : formData.identificador_boletim,
        valor: parseFloat(formData.valor),
        motivo: formData.motivo,
        observacao: formData.observacao || null,
        gerar_boletim: formData.gerar_boletim
      });
      
      const mensagem = formData.gerar_boletim 
        ? `Custo extra cadastrado para ${response.montador_nome} com boletim ${response.identificador_boletim}!`
        : `Custo extra cadastrado para ${response.montador_nome}!`;
      toast.success(mensagem);
      
      setDialogOpen(false);
      limparForm();
      carregarCustos();
    } catch (error: any) {
      toast.error(error.message || "Erro ao criar custo extra");
    } finally {
      setSubmitting(false);
    }
  };

  const atualizarCusto = async () => {
    if (!selectedCusto) return;

    setSubmitting(true);
    try {
      await apiClient.put(`/custos-extras/${selectedCusto.id}`, {
        identificador_montador: formData.identificador_montador,
        identificador_boletim: formData.identificador_boletim,
        valor: parseFloat(formData.valor),
        motivo: formData.motivo,
        observacao: formData.observacao || null
      });
      
      toast.success("Custo extra atualizado!");
      setEditDialogOpen(false);
      limparForm();
      carregarCustos();
    } catch (error: any) {
      toast.error(error.message || "Erro ao atualizar custo extra");
    } finally {
      setSubmitting(false);
    }
  };

  const excluirCusto = async (custo: CustoExtra) => {
    if (!confirm(`Deseja excluir o custo extra de R$ ${custo.valor.toFixed(2)}?`)) {
      return;
    }

    try {
      await apiClient.delete(`/custos-extras/${custo.id}`);
      toast.success("Custo extra excluído!");
      carregarCustos();
    } catch (error: any) {
      toast.error(error.message || "Erro ao excluir custo extra");
    }
  };

  const abrirEdicao = (custo: CustoExtra) => {
    setSelectedCusto(custo);
    setFormData({
      identificador_montador: custo.identificador_montador,
      identificador_boletim: custo.identificador_boletim,
      valor: custo.valor.toString(),
      motivo: custo.motivo,
      observacao: custo.observacao || "",
      gerar_boletim: false
    });
    setEditDialogOpen(true);
  };

  const limparForm = () => {
    setFormData({
      identificador_montador: "",
      identificador_boletim: "",
      valor: "",
      motivo: "",
      observacao: "",
      gerar_boletim: false
    });
    setSelectedCusto(null);
  };

  const formatarMoeda = (valor: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const totalPendente = custos
    .filter(c => c.status === 'pendente')
    .reduce((acc, c) => acc + c.valor, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Custos Extras</h1>
          <p className="text-muted-foreground">
            Cadastre custos extras para serem vinculados aos envios de montadores
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Novo Custo Extra
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Cadastrar Custo Extra</DialogTitle>
              <DialogDescription>
                Informe os dados do custo extra a ser vinculado ao boletim de montagem
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="identificador_montador">
                    Identificador do Montador *
                  </Label>
                  <Input
                    id="identificador_montador"
                    placeholder="Ex: 3992"
                    value={formData.identificador_montador}
                    onChange={(e) => setFormData({ ...formData, identificador_montador: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">
                    Código do montador no sistema
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 mb-2">
                    <input
                      type="checkbox"
                      id="gerar_boletim"
                      checked={formData.gerar_boletim}
                      onChange={(e) => setFormData({ ...formData, gerar_boletim: e.target.checked, identificador_boletim: "" })}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <Label htmlFor="gerar_boletim" className="text-sm font-medium cursor-pointer">
                      Gerar Boletim de Ajuste
                    </Label>
                  </div>
                  {!formData.gerar_boletim ? (
                    <>
                      <Label htmlFor="identificador_boletim">
                        Identificador do Boletim *
                      </Label>
                      <Input
                        id="identificador_boletim"
                        placeholder="Ex: BM-2026-001"
                        value={formData.identificador_boletim}
                        onChange={(e) => setFormData({ ...formData, identificador_boletim: e.target.value })}
                      />
                      <p className="text-xs text-muted-foreground">
                        Número do boletim de montagem
                      </p>
                    </>
                  ) : (
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                      <p className="text-sm text-blue-700">
                        <strong>Boletim de Ajuste:</strong> Será gerado automaticamente no formato A-AAAA-XXXX
                      </p>
                      <p className="text-xs text-blue-600 mt-1">
                        Usado para custos sem boletim real associado
                      </p>
                    </div>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="valor">Valor do Custo Extra *</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    R$
                  </span>
                  <Input
                    id="valor"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0,00"
                    className="pl-10"
                    value={formData.valor}
                    onChange={(e) => setFormData({ ...formData, valor: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="motivo">Motivo / Descrição *</Label>
                <Textarea
                  id="motivo"
                  placeholder="Descreva o motivo do custo extra..."
                  rows={3}
                  value={formData.motivo}
                  onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="observacao">Observação</Label>
                <Textarea
                  id="observacao"
                  placeholder="Observação adicional (opcional)..."
                  rows={2}
                  value={formData.observacao}
                  onChange={(e) => setFormData({ ...formData, observacao: e.target.value })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setDialogOpen(false); limparForm(); }}>
                Cancelar
              </Button>
              <Button onClick={criarCusto} disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Salvando...
                  </>
                ) : (
                  "Cadastrar"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Cards de resumo */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Pendente</CardTitle>
            <DollarSign className="h-4 w-4 text-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">{formatarMoeda(totalPendente)}</div>
            <p className="text-xs text-muted-foreground">
              {custos.filter(c => c.status === 'pendente').length} custo(s) aguardando processamento
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pendentes</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{custos.filter(c => c.status === 'pendente').length}</div>
            <p className="text-xs text-muted-foreground">Aguardando vinculação</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Processados</CardTitle>
            <CheckCircle className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">{custos.filter(c => c.status === 'processado').length}</div>
            <p className="text-xs text-muted-foreground">Já vinculados aos envios</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros e tabela */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Lista de Custos Extras</CardTitle>
              <CardDescription>
                Custos cadastrados pela equipe para vinculação aos envios
              </CardDescription>
            </div>
            <Select value={filtroStatus} onValueChange={setFiltroStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filtrar por status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                <SelectItem value="pendente">Pendentes</SelectItem>
                <SelectItem value="processado">Processados</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : custos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Nenhum custo extra cadastrado</p>
              <Button 
                variant="link" 
                className="mt-2"
                onClick={() => setDialogOpen(true)}
              >
                Cadastrar primeiro custo
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Montador</TableHead>
                  <TableHead>Boletim</TableHead>
                  <TableHead>Valor</TableHead>
                  <TableHead>Motivo</TableHead>
                  <TableHead>Observação</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Cadastrado por</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {custos.map((custo) => (
                  <TableRow key={custo.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">
                          {custo.montador_nome || `ID: ${custo.identificador_montador}`}
                        </p>
                        {custo.montador_nome && (
                          <p className="text-xs text-muted-foreground">
                            {custo.identificador_montador}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {custo.identificador_boletim}
                    </TableCell>
                    <TableCell className="font-semibold text-primary">
                      {formatarMoeda(custo.valor)}
                    </TableCell>
                    <TableCell className="max-w-[150px] truncate" title={custo.motivo}>
                      {custo.motivo}
                    </TableCell>
                    <TableCell className="max-w-[150px] truncate text-muted-foreground" title={custo.observacao || ''}>
                      {custo.observacao || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={custo.status === 'pendente' ? 'outline' : 'default'}>
                        {custo.status === 'pendente' ? (
                          <>
                            <Clock className="mr-1 h-3 w-3" />
                            Pendente
                          </>
                        ) : (
                          <>
                            <CheckCircle className="mr-1 h-3 w-3" />
                            Processado
                          </>
                        )}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {custo.cadastrado_por_nome || '-'}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(custo.created_at).toLocaleDateString('pt-BR')}
                    </TableCell>
                    <TableCell className="text-right">
                      {custo.status === 'pendente' && podeEditarCusto(custo) && (
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Editar"
                            onClick={() => abrirEdicao(custo)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Excluir"
                            onClick={() => excluirCusto(custo)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dialog de Edição */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Editar Custo Extra</DialogTitle>
            <DialogDescription>
              Atualize os dados do custo extra
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_identificador_montador">
                  Identificador do Montador *
                </Label>
                <Input
                  id="edit_identificador_montador"
                  value={formData.identificador_montador}
                  onChange={(e) => setFormData({ ...formData, identificador_montador: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_identificador_boletim">
                  Identificador do Boletim *
                </Label>
                <Input
                  id="edit_identificador_boletim"
                  value={formData.identificador_boletim}
                  onChange={(e) => setFormData({ ...formData, identificador_boletim: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_valor">Valor do Custo Extra *</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  R$
                </span>
                <Input
                  id="edit_valor"
                  type="number"
                  step="0.01"
                  min="0"
                  className="pl-10"
                  value={formData.valor}
                  onChange={(e) => setFormData({ ...formData, valor: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_motivo">Motivo / Descrição *</Label>
              <Textarea
                id="edit_motivo"
                rows={3}
                value={formData.motivo}
                onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_observacao">Observação</Label>
              <Textarea
                id="edit_observacao"
                placeholder="Observação adicional (opcional)..."
                rows={2}
                value={formData.observacao}
                onChange={(e) => setFormData({ ...formData, observacao: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setEditDialogOpen(false); limparForm(); }}>
              Cancelar
            </Button>
            <Button onClick={atualizarCusto} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Salvando...
                </>
              ) : (
                "Salvar Alterações"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
