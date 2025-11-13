import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { pagamentosService } from "@/services/pagamentos.service";
import { PagamentoPendente } from "@/types/pagamento";
import { CheckCircle2, AlertCircle, Clock, Download, Search, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

type SortField = 'status' | 'tipo' | 'nome' | 'valor' | 'vencimento';
type SortDirection = 'asc' | 'desc';

function obterStatusUrgencia(diasParaVencimento: number): { 
  emoji: string; 
  texto: string; 
  prioridade: number; 
  variant: "default" | "destructive" | "outline" | "secondary";
  corFundo: string;
} {
  if (diasParaVencimento < 0) {
    const diasAtrasado = Math.abs(diasParaVencimento);
    return { 
      emoji: "🔴", 
      texto: `Vencido há ${diasAtrasado}d`, 
      prioridade: 1, 
      variant: "destructive",
      corFundo: "bg-red-50 dark:bg-red-950"
    };
  } else if (diasParaVencimento === 0) {
    return { 
      emoji: "⚠️", 
      texto: "Vence HOJE", 
      prioridade: 2, 
      variant: "destructive",
      corFundo: "bg-orange-50 dark:bg-orange-950"
    };
  } else if (diasParaVencimento === 1) {
    return { 
      emoji: "🟡", 
      texto: "Vence amanhã", 
      prioridade: 3, 
      variant: "secondary",
      corFundo: "bg-yellow-50 dark:bg-yellow-950"
    };
  } else if (diasParaVencimento <= 3) {
    return { 
      emoji: "🟢", 
      texto: `${diasParaVencimento}d`, 
      prioridade: 4, 
      variant: "outline",
      corFundo: ""
    };
  } else if (diasParaVencimento <= 10) {
    return { 
      emoji: "🔵", 
      texto: `${diasParaVencimento}d`, 
      prioridade: 5, 
      variant: "outline",
      corFundo: ""
    };
  } else {
    return { 
      emoji: "⚪", 
      texto: `${diasParaVencimento}d`, 
      prioridade: 6, 
      variant: "outline",
      corFundo: ""
    };
  }
}

export default function PagamentosVencidos() {
  const { toast } = useToast();
  const [pagamentos, setPagamentos] = useState<{ servicos: any[]; montagens: any[] }>({ servicos: [], montagens: [] });
  const [loading, setLoading] = useState(true);
  const [confirmarRollback, setConfirmarRollback] = useState(false);
  const [tipoFiltro, setTipoFiltro] = useState("Todos");
  const [statusFiltro, setStatusFiltro] = useState("Todos");
  const [buscaTexto, setBuscaTexto] = useState("");
  const [sortField, setSortField] = useState<SortField>('status');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'marcarTodos' | 'desfazerTodos' | null>(null);

  const carregarPagamentos = async () => {
    try {
      setLoading(true);
      const dados = await pagamentosService.getTodosPagamentosPendentes();
      setPagamentos(dados);
    } catch (error: any) {
      toast({
        title: "Erro ao carregar pagamentos",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarPagamentos();
  }, []);

  const marcarTodosComNFComoPagos = async () => {
    try {
      const resultado = await pagamentosService.marcarTodosNaoPendentesPagos();
      toast({
        title: "✅ Pagamentos marcados!",
        description: `${resultado.total} pagamentos marcados! (${resultado.lotes} lotes + ${resultado.montagens} montagens)`,
      });
      setShowConfirmDialog(false);
      setConfirmAction(null);
      carregarPagamentos();
    } catch (error: any) {
      toast({
        title: "Erro ao marcar pagamentos",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const desfazerTodosPagamentos = async () => {
    try {
      const resultado = await pagamentosService.desmarcarTodosPagos();
      toast({
        title: "🔄 Pagamentos desfeitos!",
        description: `${resultado.total} pagamentos desfeitos! (${resultado.lotes} lotes + ${resultado.montagens} montagens)`,
        variant: "destructive",
      });
      setShowConfirmDialog(false);
      setConfirmAction(null);
      carregarPagamentos();
    } catch (error: any) {
      toast({
        title: "Erro ao desfazer pagamentos",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleConfirmAction = () => {
    if (confirmAction === 'marcarTodos') {
      marcarTodosComNFComoPagos();
    } else if (confirmAction === 'desfazerTodos') {
      desfazerTodosPagamentos();
    }
  };

  const marcarComoPago = async (tipo: 'servico' | 'montagem', id: number) => {
    try {
      if (tipo === 'servico') {
        await pagamentosService.marcarLoteComoPago(id);
      } else {
        await pagamentosService.marcarMontagemComoPaga(id);
      }
      
      // Remover apenas o item marcado da lista sem recarregar
      setPagamentos(prev => ({
        servicos: tipo === 'servico' ? prev.servicos.filter(s => s.id !== id) : prev.servicos,
        montagens: tipo === 'montagem' ? prev.montagens.filter(m => m.id !== id) : prev.montagens,
      }));
      
      toast({
        title: "✅ Pago!",
      });
    } catch (error: any) {
      toast({
        title: "Erro ao marcar como pago",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const totalServicos = pagamentos.servicos.length;
  const totalMontagens = pagamentos.montagens.length;
  const totalGeral = totalServicos + totalMontagens;
  const vencidos = pagamentos.servicos.filter(p => p.dias_para_vencimento < 0).length + 
                   pagamentos.montagens.filter(p => p.dias_para_vencimento < 0).length;
  const urgentes = pagamentos.servicos.filter(p => p.dias_para_vencimento <= 1 && p.dias_para_vencimento >= 0).length + 
                   pagamentos.montagens.filter(p => p.dias_para_vencimento <= 1 && p.dias_para_vencimento >= 0).length;
  const comNF = pagamentos.servicos.filter(p => p.data_recebimento_nf).length +
                pagamentos.montagens.filter(p => p.data_recebimento_nf).length;
  const semNF = totalGeral - comNF;

  const valorTotal = pagamentos.servicos.reduce((acc, p) => acc + (p.valor_total || 0), 0) +
                     pagamentos.montagens.reduce((acc, p) => acc + (p.valor_total || 0), 0);

  // Preparar dados da tabela
  const dadosTabela: PagamentoPendente[] = [];

  pagamentos.servicos.forEach(lote => {
    const { emoji, texto, prioridade, corFundo } = obterStatusUrgencia(lote.dias_para_vencimento);
    const fornecedorId = lote.prestador_fornecedor_id || '-';
    dadosTabela.push({
      prioridade,
      status: `${emoji} ${texto}`,
      tipo: 'Serviço',
      id: lote.id,
      nome: lote.prestador_nome,
      fornecedorId,
      periodo: lote.periodo || 'N/A',
      valor: lote.valor_total ? `R$ ${lote.valor_total.toFixed(2)}` : '-',
      vencimento: lote.data_vencimento_pagamento ? new Date(lote.data_vencimento_pagamento).toLocaleDateString('pt-BR') : '-',
      nf: lote.data_recebimento_nf ? new Date(lote.data_recebimento_nf).toLocaleDateString('pt-BR') : '❌',
      _tipo_original: 'servico',
      _id: lote.id,
      _dias: lote.dias_para_vencimento,
      _corFundo: corFundo,
      _valorNumerico: lote.valor_total || 0,
      _dataVencimento: lote.data_vencimento_pagamento || '',
    });
  });

  pagamentos.montagens.forEach(envio => {
    const { emoji, texto, prioridade, corFundo } = obterStatusUrgencia(envio.dias_para_vencimento);
    const detalhes = envio.detalhes || {};
    const periodo = detalhes.periodo_relatorio || envio.periodo || 'N/A';
    const fornecedorId = envio.montador_fornecedor_id || '-';
    dadosTabela.push({
      prioridade,
      status: `${emoji} ${texto}`,
      tipo: 'Montagem',
      id: envio.id,
      nome: envio.montador_nome,
      fornecedorId,
      periodo,
      valor: envio.valor_total ? `R$ ${envio.valor_total.toFixed(2)}` : '-',
      vencimento: envio.data_vencimento_pagamento ? new Date(envio.data_vencimento_pagamento).toLocaleDateString('pt-BR') : '-',
      nf: envio.data_recebimento_nf ? new Date(envio.data_recebimento_nf).toLocaleDateString('pt-BR') : '❌',
      _tipo_original: 'montagem',
      _id: envio.id,
      _dias: envio.dias_para_vencimento,
      _corFundo: corFundo,
      _valorNumerico: envio.valor_total || 0,
      _dataVencimento: envio.data_vencimento_pagamento || '',
    });
  });

  // Ordenar por prioridade (padrão)
  dadosTabela.sort((a, b) => a.prioridade - b.prioridade);

  // Aplicar filtros
  let dadosFiltrados = dadosTabela;

  if (tipoFiltro === "Serviços") {
    dadosFiltrados = dadosFiltrados.filter(d => d._tipo_original === 'servico');
  } else if (tipoFiltro === "Montagens") {
    dadosFiltrados = dadosFiltrados.filter(d => d._tipo_original === 'montagem');
  }

  if (statusFiltro === "Vencidos") {
    dadosFiltrados = dadosFiltrados.filter(d => d._dias < 0);
  } else if (statusFiltro === "Urgentes (0-1d)") {
    dadosFiltrados = dadosFiltrados.filter(d => d._dias >= 0 && d._dias <= 1);
  } else if (statusFiltro === "Próximos (2-10d)") {
    dadosFiltrados = dadosFiltrados.filter(d => d._dias >= 2 && d._dias <= 10);
  } else if (statusFiltro === "Futuros (>10d)") {
    dadosFiltrados = dadosFiltrados.filter(d => d._dias > 10);
  }

  // Aplicar busca por texto
  if (buscaTexto) {
    const buscaLower = buscaTexto.toLowerCase();
    dadosFiltrados = dadosFiltrados.filter(d => 
      d.nome.toLowerCase().includes(buscaLower) ||
      d.id.toString().includes(buscaLower) ||
      d.fornecedorId.toLowerCase().includes(buscaLower) ||
      d.periodo.toLowerCase().includes(buscaLower)
    );
  }

  // Aplicar ordenação
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  dadosFiltrados.sort((a, b) => {
    let comparison = 0;
    
    switch (sortField) {
      case 'status':
        comparison = a.prioridade - b.prioridade;
        break;
      case 'tipo':
        comparison = a.tipo.localeCompare(b.tipo);
        break;
      case 'nome':
        comparison = a.nome.localeCompare(b.nome);
        break;
      case 'valor':
        comparison = (a._valorNumerico || 0) - (b._valorNumerico || 0);
        break;
      case 'vencimento':
        comparison = (a._dataVencimento || '').localeCompare(b._dataVencimento || '');
        break;
    }
    
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  // Função para exportar CSV
  const exportarCSV = () => {
    const headers = ['Status', 'Tipo', 'ID', 'Nome', 'Fornecedor ID', 'Período', 'Valor', 'Vencimento', 'NF'];
    const rows = dadosFiltrados.map(d => [
      d.status,
      d.tipo,
      d.id,
      d.nome,
      d.fornecedorId,
      d.periodo,
      d.valor,
      d.vencimento,
      d.nf
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `pagamentos_pendentes_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast({
      title: "📥 Exportado!",
      description: `${dadosFiltrados.length} pagamentos exportados para CSV`,
    });
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="ml-2 h-4 w-4" />;
    return sortDirection === 'asc' ? 
      <ArrowUp className="ml-2 h-4 w-4" /> : 
      <ArrowDown className="ml-2 h-4 w-4" />;
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Pagamentos Pendentes</h1>
          <p className="text-muted-foreground mt-2">Gestão de pagamentos a fornecedores</p>
        </div>
        <Card>
          <CardContent className="p-12 text-center">
            <div className="animate-pulse text-muted-foreground">Carregando dados...</div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Pagamentos Pendentes</h1>
          <p className="text-muted-foreground mt-2">Gestão e controle de pagamentos a fornecedores</p>
        </div>
        <Button onClick={exportarCSV} variant="outline" className="gap-2">
          <Download className="h-4 w-4" />
          Exportar CSV
        </Button>
      </div>

      {/* Métricas em Destaque */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Pendente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{totalGeral}</div>
            <p className="text-xs text-muted-foreground mt-1">{totalServicos} serv / {totalMontagens} mont</p>
          </CardContent>
        </Card>
        
        <Card className="border-red-200 dark:border-red-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-red-600 dark:text-red-400 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Vencidos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">{vencidos}</div>
            <p className="text-xs text-muted-foreground mt-1">Requerem atenção</p>
          </CardContent>
        </Card>
        
        <Card className="border-orange-200 dark:border-orange-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-600 dark:text-orange-400 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Urgentes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{urgentes}</div>
            <p className="text-xs text-muted-foreground mt-1">0-1 dia</p>
          </CardContent>
        </Card>

        <Card className="border-green-200 dark:border-green-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-green-600 dark:text-green-400 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Com NF
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{comNF}</div>
            <p className="text-xs text-muted-foreground mt-1">{semNF} sem NF</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Valor Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorTotal)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">A pagar</p>
          </CardContent>
        </Card>
      </div>

      {/* Ações em Massa */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Ações em Massa</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button 
            onClick={() => {
              setConfirmAction('marcarTodos');
              setShowConfirmDialog(true);
            }}
            className="gap-2"
            variant="default"
          >
            <CheckCircle2 className="h-4 w-4" />
            Marcar Todos com NF como Pagos
          </Button>
          
          <Button 
            onClick={() => {
              setConfirmAction('desfazerTodos');
              setShowConfirmDialog(true);
            }}
            variant="destructive"
            className="gap-2"
          >
            <AlertCircle className="h-4 w-4" />
            Desfazer TODOS os Pagamentos
          </Button>
        </CardContent>
      </Card>

      {totalGeral === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h3 className="text-xl font-semibold text-foreground mb-2">Nenhum pagamento pendente!</h3>
            <p className="text-muted-foreground">Todos os pagamentos estão em dia.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Filtros e Busca */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Filtros e Busca</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por nome, ID, fornecedor..."
                    value={buscaTexto}
                    onChange={(e) => setBuscaTexto(e.target.value)}
                    className="pl-9"
                  />
                </div>
                
                <Select value={tipoFiltro} onValueChange={setTipoFiltro}>
                  <SelectTrigger>
                    <SelectValue placeholder="Tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Todos">📊 Todos os tipos</SelectItem>
                    <SelectItem value="Serviços">📦 Serviços</SelectItem>
                    <SelectItem value="Montagens">🔧 Montagens</SelectItem>
                  </SelectContent>
                </Select>
                
                <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                  <SelectTrigger>
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Todos">⚪ Todos os status</SelectItem>
                    <SelectItem value="Vencidos">🔴 Vencidos</SelectItem>
                    <SelectItem value="Urgentes (0-1d)">⚠️ Urgentes (0-1d)</SelectItem>
                    <SelectItem value="Próximos (2-10d)">🟡 Próximos (2-10d)</SelectItem>
                    <SelectItem value="Futuros (>10d)">🔵 Futuros (&gt;10d)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {dadosFiltrados.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <p className="text-muted-foreground">Nenhum pagamento encontrado com os filtros aplicados.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">
                    Pagamentos ({dadosFiltrados.length} {dadosFiltrados.length !== dadosTabela.length && `de ${dadosTabela.length}`})
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="cursor-pointer" onClick={() => handleSort('status')}>
                          <div className="flex items-center">
                            Status
                            <SortIcon field="status" />
                          </div>
                        </TableHead>
                        <TableHead className="cursor-pointer" onClick={() => handleSort('tipo')}>
                          <div className="flex items-center">
                            Tipo
                            <SortIcon field="tipo" />
                          </div>
                        </TableHead>
                        <TableHead>ID</TableHead>
                        <TableHead className="cursor-pointer" onClick={() => handleSort('nome')}>
                          <div className="flex items-center">
                            Nome
                            <SortIcon field="nome" />
                          </div>
                        </TableHead>
                        <TableHead>Fornecedor</TableHead>
                        <TableHead>Período</TableHead>
                        <TableHead className="cursor-pointer text-right" onClick={() => handleSort('valor')}>
                          <div className="flex items-center justify-end">
                            Valor
                            <SortIcon field="valor" />
                          </div>
                        </TableHead>
                        <TableHead className="cursor-pointer" onClick={() => handleSort('vencimento')}>
                          <div className="flex items-center">
                            Vencimento
                            <SortIcon field="vencimento" />
                          </div>
                        </TableHead>
                        <TableHead className="text-center">NF</TableHead>
                        <TableHead className="text-right">Ação</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dadosFiltrados.map((item) => (
                        <TableRow key={`${item._tipo_original}_${item._id}`} className={item._corFundo}>
                          <TableCell>
                            <Badge variant={
                              item._dias < 0 ? "destructive" :
                              item._dias <= 1 ? "secondary" :
                              "outline"
                            }>
                              {item.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {item.tipo === 'Serviço' ? '📦' : '🔧'} {item.tipo}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{item.id}</TableCell>
                          <TableCell className="font-medium">{item.nome}</TableCell>
                          <TableCell className="text-muted-foreground">{item.fornecedorId}</TableCell>
                          <TableCell className="text-sm">{item.periodo}</TableCell>
                          <TableCell className="text-right font-medium">{item.valor}</TableCell>
                          <TableCell>{item.vencimento}</TableCell>
                          <TableCell className="text-center">
                            {item.nf === '❌' ? (
                              <Badge variant="destructive">Sem NF</Badge>
                            ) : (
                              <span className="text-sm text-muted-foreground">{item.nf}</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              onClick={() => marcarComoPago(item._tipo_original, item._id)}
                              size="sm"
                              variant="default"
                              className="gap-1"
                            >
                              <CheckCircle2 className="h-3 w-3" />
                              Pago
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Dialog de Confirmação */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction === 'marcarTodos' ? '✅ Confirmar Pagamentos' : '🔄 Confirmar Rollback'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction === 'marcarTodos' ? (
                <>
                  Você está prestes a marcar <strong>todos os pagamentos com NF recebida</strong> como pagos.
                  Esta ação irá atualizar {comNF} registros.
                </>
              ) : (
                <>
                  <span className="text-red-600 dark:text-red-400 font-semibold">ATENÇÃO!</span> Você está prestes a <strong>desfazer TODOS os pagamentos</strong> marcados hoje.
                  Esta é uma ação crítica e irá reverter múltiplos registros.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowConfirmDialog(false);
              setConfirmAction(null);
            }}>
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmAction} className={confirmAction === 'desfazerTodos' ? 'bg-red-600 hover:bg-red-700' : ''}>
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
