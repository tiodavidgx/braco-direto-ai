import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { pagamentosService } from "@/services/pagamentos.service";
import { PagamentoPendente } from "@/types/pagamento";

function obterStatusUrgencia(diasParaVencimento: number): { emoji: string; texto: string; prioridade: number; variant: string } {
  if (diasParaVencimento < 0) {
    const diasAtrasado = Math.abs(diasParaVencimento);
    return { emoji: "🔴", texto: `Vencido há ${diasAtrasado} dia(s)`, prioridade: 1, variant: "destructive" };
  } else if (diasParaVencimento === 0) {
    return { emoji: "⚠️", texto: "Vence HOJE", prioridade: 2, variant: "warning" };
  } else if (diasParaVencimento === 1) {
    return { emoji: "🟡", texto: "Vence amanhã", prioridade: 3, variant: "warning" };
  } else if (diasParaVencimento <= 3) {
    return { emoji: "🟢", texto: `Vence em ${diasParaVencimento} dias`, prioridade: 4, variant: "success" };
  } else if (diasParaVencimento <= 10) {
    return { emoji: "🔵", texto: `Vence em ${diasParaVencimento} dias`, prioridade: 5, variant: "default" };
  } else {
    return { emoji: "⚪", texto: `Vence em ${diasParaVencimento} dias`, prioridade: 6, variant: "default" };
  }
}

export default function PagamentosVencidos() {
  const { toast } = useToast();
  const [pagamentos, setPagamentos] = useState<{ servicos: any[]; montagens: any[] }>({ servicos: [], montagens: [] });
  const [loading, setLoading] = useState(true);
  const [confirmarRollback, setConfirmarRollback] = useState(false);
  const [tipoFiltro, setTipoFiltro] = useState("Todos");
  const [statusFiltro, setStatusFiltro] = useState("Todos");

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
      setConfirmarRollback(false);
      carregarPagamentos();
    } catch (error: any) {
      toast({
        title: "Erro ao desfazer pagamentos",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const marcarComoPago = async (tipo: 'servico' | 'montagem', id: number) => {
    try {
      if (tipo === 'servico') {
        await pagamentosService.marcarLoteComoPago(id);
      } else {
        await pagamentosService.marcarMontagemComoPaga(id);
      }
      toast({
        title: "✅ Pago!",
      });
      carregarPagamentos();
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
  const urgentes = pagamentos.servicos.filter(p => p.dias_para_vencimento <= 1).length + 
                   pagamentos.montagens.filter(p => p.dias_para_vencimento <= 1).length;

  // Preparar dados da tabela
  const dadosTabela: PagamentoPendente[] = [];

  pagamentos.servicos.forEach(lote => {
    const { emoji, texto, prioridade } = obterStatusUrgencia(lote.dias_para_vencimento);
    const fornecedorId = lote.prestador_fornecedor_id || '-';
    dadosTabela.push({
      prioridade,
      status: `${emoji} ${texto}`,
      tipo: '📦 Serviço',
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
    });
  });

  pagamentos.montagens.forEach(envio => {
    const { emoji, texto, prioridade } = obterStatusUrgencia(envio.dias_para_vencimento);
    const detalhes = envio.detalhes || {};
    const periodo = detalhes.periodo_relatorio || envio.periodo || 'N/A';
    const fornecedorId = envio.montador_fornecedor_id || '-';
    dadosTabela.push({
      prioridade,
      status: `${emoji} ${texto}`,
      tipo: '🔧 Montagem',
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
    });
  });

  // Ordenar por prioridade
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

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-foreground">Pagamentos Pendentes</h1>
        <p className="text-muted-foreground">Carregando...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-foreground">Pagamentos Pendentes</h1>

      {/* Ações em Massa */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Ações em Massa</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Button 
            onClick={marcarTodosComNFComoPagos}
            className="w-full"
          >
            ✅ Marcar Todos com NF como Pagos
          </Button>
          
          <Button 
            onClick={() => {
              if (confirmarRollback) {
                desfazerTodosPagamentos();
              } else {
                setConfirmarRollback(true);
                toast({
                  title: "⚠️ Clique novamente para CONFIRMAR o rollback!",
                  variant: "destructive",
                });
              }
            }}
            variant="secondary"
            className="w-full"
          >
            🔄 Desfazer TODOS os Pagamentos
          </Button>
          
          {confirmarRollback && (
            <Button 
              onClick={() => setConfirmarRollback(false)}
              variant="outline"
              className="w-full"
            >
              ❌ Cancelar
            </Button>
          )}
        </div>
      </div>

      <Separator />

      {/* Métricas */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="text-2xl font-bold text-foreground">{vencidos}</div>
            <div className="text-sm text-muted-foreground">🔴 Vencidos</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-2xl font-bold text-foreground">{urgentes}</div>
            <div className="text-sm text-muted-foreground">⚠️ Urgentes</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-2xl font-bold text-foreground">{totalGeral}</div>
            <div className="text-sm text-muted-foreground">📊 Total</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-2xl font-bold text-foreground">{totalServicos}/{totalMontagens}</div>
            <div className="text-sm text-muted-foreground">📦/🔧</div>
          </CardContent>
        </Card>
      </div>

      {totalGeral === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-lg text-success">🎉 Não há pagamentos pendentes!</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Separator />

          {/* Filtros */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-foreground mb-2 block">Tipo:</label>
              <Select value={tipoFiltro} onValueChange={setTipoFiltro}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todos">Todos</SelectItem>
                  <SelectItem value="Serviços">Serviços</SelectItem>
                  <SelectItem value="Montagens">Montagens</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium text-foreground mb-2 block">Status:</label>
              <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todos">Todos</SelectItem>
                  <SelectItem value="Vencidos">Vencidos</SelectItem>
                  <SelectItem value="Urgentes (0-1d)">Urgentes (0-1d)</SelectItem>
                  <SelectItem value="Próximos (2-10d)">Próximos (2-10d)</SelectItem>
                  <SelectItem value="Futuros (>10d)">Futuros (&gt;10d)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {dadosFiltrados.length === 0 ? (
            <Card>
              <CardContent className="p-6">
                <p className="text-center text-muted-foreground">Nenhum pagamento encontrado.</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <p className="text-foreground font-medium">
                Mostrando {dadosFiltrados.length} de {dadosTabela.length} pagamentos
              </p>

              <Separator />

              {/* Lista de Pagamentos */}
              <div className="space-y-4">
                {dadosFiltrados.map((item, idx) => (
                  <div key={`${item._tipo_original}_${item._id}`}>
                    <Card>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 space-y-1">
                            <div className="text-sm">
                              <span className="font-semibold">{item.status}</span> | {item.tipo} | <span className="font-semibold">ID: {item.id}</span> | {item.nome} | <span className="font-semibold">Fornecedor ID:</span> {item.fornecedorId} | {item.periodo}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              💰 {item.valor} | ⏰ Vence: {item.vencimento} | 📄 NF: {item.nf}
                            </div>
                          </div>
                          <Button
                            onClick={() => marcarComoPago(item._tipo_original, item._id)}
                            size="sm"
                          >
                            ✅ Pago
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                    {idx < dadosFiltrados.length - 1 && <Separator className="my-2" />}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
