import { useState, useEffect, useMemo, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
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
  ChevronLeft, 
  ChevronRight, 
  Calendar,
  Search,
  X,
  Undo2,
  Loader2
} from "lucide-react";
import { format, isToday, isYesterday, parseISO, startOfMonth, endOfMonth, eachDayOfInterval, addMonths, subMonths } from "date-fns";
import { ptBR } from "date-fns/locale";

// Função para determinar a URL da API
const getApiBaseUrl = (): string => {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `${window.location.origin}/api/v1`;
  }
  return 'http://localhost:14001/api/v1';
};

const API_URL = getApiBaseUrl();

interface Titulo {
  id: number;
  numero_titulo?: string;
  nome_fornecedor: string;
  cod_fornecedor?: string;
  cnpj_cpf?: string;
  valor: number;
  data_vencimento: string;
  data_emissao?: string;
  descricao?: string;
  status: string;
  tier: number;
  data_agendamento?: string;
  parcela_numero?: number;
  parcela_total?: number;
  filial?: string;
}

interface DiaComTitulos {
  data: Date;
  dataStr: string;
  titulos: Titulo[];
  total: number;
}

export default function CalendarioPagamentos() {
  const { toast } = useToast();
  const [mesAtual, setMesAtual] = useState(new Date());
  const [titulos, setTitulos] = useState<Titulo[]>([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState("");
  const [horaAtual, setHoraAtual] = useState(new Date());
  const [marcandoNaoPago, setMarcandoNaoPago] = useState<number | null>(null);
  const [confirmNaoPago, setConfirmNaoPago] = useState<Titulo | null>(null);
  const diasScrollRef = useRef<HTMLDivElement>(null);
  const todayColumnRef = useRef<HTMLDivElement>(null);
  const hasScrolledToToday = useRef(false);

  // Atualizar hora a cada minuto para verificar se passou das 14:30
  useEffect(() => {
    const interval = setInterval(() => {
      setHoraAtual(new Date());
    }, 60000); // Atualiza a cada 1 minuto
    return () => clearInterval(interval);
  }, []);

  // Verificar se passou das 14:30
  const isPagamentoEmAndamento = () => {
    const hora = horaAtual.getHours();
    const minutos = horaAtual.getMinutes();
    return hora > 14 || (hora === 14 && minutos >= 30);
  };

  useEffect(() => {
    hasScrolledToToday.current = false;
    carregarTitulos();
  }, [mesAtual]);

  const carregarTitulos = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/gestao-pagamentos/titulos?status=agendado`);
      if (response.ok) {
        const data = await response.json();
        setTitulos(data);
      }
    } catch (error) {
      console.error("Erro ao carregar títulos:", error);
    } finally {
      setLoading(false);
    }
  };

  // Função para marcar título como não pago (volta para pendente)
  const marcarComoNaoPago = async (tituloId: number) => {
    try {
      setMarcandoNaoPago(tituloId);
      const response = await fetch(`${API_URL}/gestao-pagamentos/titulos/${tituloId}/agendar`, {
        method: 'PUT'
      });
      
      if (response.ok) {
        // Remover título da lista
        setTitulos(prev => prev.filter(t => t.id !== tituloId));
        toast({
          title: "Título atualizado",
          description: "O título foi marcado como não pago e voltou para pendentes.",
        });
      } else {
        throw new Error("Erro ao atualizar título");
      }
    } catch (error) {
      console.error("Erro ao marcar como não pago:", error);
      toast({
        title: "Erro",
        description: "Não foi possível marcar o título como não pago.",
        variant: "destructive"
      });
    } finally {
      setMarcandoNaoPago(null);
    }
  };

  // Filtrar títulos pela busca
  const titulosFiltrados = useMemo(() => {
    if (!busca.trim()) return titulos;
    
    const termoBusca = busca.toLowerCase().trim();
    return titulos.filter(t => 
      t.nome_fornecedor?.toLowerCase().includes(termoBusca) ||
      t.cod_fornecedor?.toLowerCase().includes(termoBusca) ||
      t.cnpj_cpf?.includes(termoBusca)
    );
  }, [titulos, busca]);

  const getDiasDoMes = (): DiaComTitulos[] => {
    const dias = eachDayOfInterval({
      start: startOfMonth(mesAtual),
      end: endOfMonth(mesAtual)
    });

    return dias.map(dia => {
      const dataStr = format(dia, "yyyy-MM-dd");
      const titulosDoDia = titulosFiltrados.filter(t => t.data_agendamento === dataStr);
      const total = titulosDoDia.reduce((sum, t) => sum + (t.valor || 0), 0);
      
      return {
        data: dia,
        dataStr,
        titulos: titulosDoDia,
        total
      };
    }).filter(d => d.titulos.length > 0);
  };

  const formatarValor = (valor: number) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL"
    }).format(valor);
  };

  const diasComTitulos = useMemo(() => getDiasDoMes(), [titulosFiltrados, mesAtual]);
  const totalMes = diasComTitulos.reduce((sum, d) => sum + d.total, 0);
  const totalTitulos = diasComTitulos.reduce((sum, d) => sum + d.titulos.length, 0);

  // Auto-scroll para o dia de hoje quando os dados carregam
  useEffect(() => {
    if (diasComTitulos.length > 0 && !hasScrolledToToday.current && !loading) {
      setTimeout(() => {
        const container = diasScrollRef.current;
        const todayEl = todayColumnRef.current;
        if (container && todayEl) {
          container.scrollTo({
            left: todayEl.offsetLeft - container.offsetLeft - 12,
            behavior: 'smooth'
          });
          hasScrolledToToday.current = true;
        } else if (container) {
          // Se hoje não tem títulos, scroll para o próximo dia futuro
          const hoje = new Date();
          const idx = diasComTitulos.findIndex(d => d.data >= hoje);
          if (idx > 0) {
            const cols = container.querySelectorAll('[data-dia-col]');
            const target = cols[idx] as HTMLElement;
            if (target) {
              container.scrollTo({
                left: target.offsetLeft - container.offsetLeft - 12,
                behavior: 'smooth'
              });
            }
          }
          hasScrolledToToday.current = true;
        }
      }, 300);
    }
  }, [diasComTitulos, loading]);

  const getDiaSemana = (data: Date) => {
    const dias = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
    return dias[data.getDay()];
  };

  return (
    <div className="min-h-screen bg-gray-50/50 -m-4 md:-m-8 p-4 md:p-8">
      <div className="max-w-[1920px] mx-auto space-y-5">
        
        {/* Header */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-white rounded-xl border border-gray-200 shadow-sm">
                <Calendar className="h-6 w-6 text-gray-700" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-gray-800">
                  Calendário de Pagamentos
                </h1>
                <p className="text-gray-500 text-sm">
                  Programação financeira mensal
                </p>
              </div>
            </div>
            
            {/* Navegação */}
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="icon"
                onClick={() => setMesAtual(subMonths(mesAtual, 1))}
                className="h-10 w-10 rounded-lg border-gray-200 hover:bg-gray-100"
              >
                <ChevronLeft className="h-5 w-5 text-gray-600" />
              </Button>
              <div className="px-5 py-2 bg-white rounded-lg border border-gray-200 min-w-[180px] text-center">
                <span className="text-base font-medium text-gray-700 capitalize">
                  {format(mesAtual, "MMMM yyyy", { locale: ptBR })}
                </span>
              </div>
              <Button 
                variant="outline" 
                size="icon"
                onClick={() => setMesAtual(addMonths(mesAtual, 1))}
                className="h-10 w-10 rounded-lg border-gray-200 hover:bg-gray-100"
              >
                <ChevronRight className="h-5 w-5 text-gray-600" />
              </Button>
            </div>
          </div>

          {/* Barra de Pesquisa */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
            <div className="relative w-full sm:w-96">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Buscar por fornecedor, código ou CNPJ..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="pl-10 pr-10 h-10 bg-white border-gray-200 rounded-lg focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
              />
              {busca && (
                <button
                  onClick={() => setBusca("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Resumo Inline */}
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Total:</span>
                <span className="font-semibold text-gray-800">{formatarValor(totalMes)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Títulos:</span>
                <span className="font-semibold text-gray-800">{totalTitulos}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Dias:</span>
                <span className="font-semibold text-gray-800">{diasComTitulos.length}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Grid de Colunas por Dia */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center space-y-3">
              <div className="w-10 h-10 border-3 border-gray-300 border-t-gray-600 rounded-full animate-spin mx-auto" />
              <p className="text-gray-500 text-sm">Carregando...</p>
            </div>
          </div>
        ) : diasComTitulos.length === 0 ? (
          <Card className="bg-white border-gray-200">
            <CardContent className="py-16 text-center">
              <Calendar className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-700 mb-1">
                {busca ? "Nenhum resultado encontrado" : "Nenhum pagamento programado"}
              </h3>
              <p className="text-gray-500 text-sm">
                {busca 
                  ? `Não encontramos títulos para "${busca}"`
                  : "Não há títulos agendados para este mês"
                }
              </p>
            </CardContent>
          </Card>
        ) : (
          <div ref={diasScrollRef} className="flex gap-4 overflow-x-auto pb-4 -mx-4 px-4 md:-mx-8 md:px-8">
            {diasComTitulos.map(dia => {
              const ehHoje = isToday(dia.data);
              const ehOntem = isYesterday(dia.data);
              const pagamentoEmAndamento = ehHoje && isPagamentoEmAndamento() && dia.titulos.length > 0;
              
              return (
                <div 
                  key={dia.dataStr}
                  ref={ehHoje ? todayColumnRef : undefined}
                  data-dia-col
                  className="flex-shrink-0 w-[280px] bg-white rounded-xl border border-gray-200 overflow-hidden"
                >
                  {/* Header do Dia */}
                  <div className={`
                    p-4 border-b
                    ${ehHoje 
                      ? "bg-gray-800 text-white border-gray-800" 
                      : "bg-gray-50 text-gray-800 border-gray-200"
                    }
                  `}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold">{getDiaSemana(dia.data)}</span>
                      <div className="flex items-center gap-1.5">
                        {ehHoje && !pagamentoEmAndamento && (
                          <Badge className="bg-white/20 text-white border-0 text-xs">
                            Hoje
                          </Badge>
                        )}
                        {pagamentoEmAndamento && (
                          <Badge className="bg-amber-500 text-white border-0 text-xs animate-pulse">
                            💳 Pagamento em andamento
                          </Badge>
                        )}
                        {ehOntem && (
                          <Badge className="bg-gray-400 text-white border-0 text-xs">
                            Ontem
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className={`text-sm ${ehHoje ? "text-gray-300" : "text-gray-500"}`}>
                      {format(dia.data, "dd 'de' MMMM", { locale: ptBR })}
                    </div>
                    <div className={`flex items-center justify-between mt-3 pt-3 border-t ${ehHoje ? "border-white/20" : "border-gray-200"}`}>
                      <span className={`text-xs ${ehHoje ? "text-gray-300" : "text-gray-500"}`}>
                        {dia.titulos.length} título{dia.titulos.length !== 1 ? 's' : ''}
                      </span>
                      <span className="font-bold">{formatarValor(dia.total)}</span>
                    </div>
                  </div>

                  {/* Lista de Títulos */}
                  <ScrollArea className="h-[420px]">
                    <div className="p-3 space-y-2">
                      {dia.titulos.map((titulo) => (
                        <div 
                          key={titulo.id}
                          className="p-3 rounded-lg bg-gray-50 hover:bg-gray-100 border border-gray-100 hover:border-gray-200 transition-colors group relative"
                        >
                          {/* Botão para marcar como não pago - só aparece no dia seguinte (ontem) */}
                          {ehOntem && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="absolute top-1 right-1 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-600 hover:bg-red-50"
                              onClick={() => setConfirmNaoPago(titulo)}
                              disabled={marcandoNaoPago === titulo.id}
                              title="Marcar como não pago (voltar para pendente)"
                            >
                              {marcandoNaoPago === titulo.id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Undo2 className="h-3.5 w-3.5" />
                              )}
                            </Button>
                          )}
                          
                          <p className="font-medium text-gray-800 text-sm leading-tight mb-2 line-clamp-2" title={titulo.nome_fornecedor}>
                            {titulo.nome_fornecedor}
                          </p>
                          
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {titulo.numero_titulo && (
                                <span className="text-xs text-gray-500 bg-white px-1.5 py-0.5 rounded border border-gray-200">
                                  #{titulo.numero_titulo}
                                </span>
                              )}
                              {titulo.parcela_numero && titulo.parcela_total && titulo.parcela_total > 1 && (
                                <span className="text-xs text-gray-600 bg-gray-200 px-1.5 py-0.5 rounded">
                                  {titulo.parcela_numero}/{titulo.parcela_total}
                                </span>
                              )}
                            </div>
                            <span className="text-sm font-bold text-gray-800">
                              {formatarValor(titulo.valor)}
                            </span>
                          </div>
                          
                          <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
                            <span>Venc: {format(parseISO(titulo.data_vencimento), "dd/MM/yy")}</span>
                            {titulo.filial && <span>Filial {titulo.filial}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dialog de Confirmação - Marcar como Não Pago */}
      <AlertDialog open={!!confirmNaoPago} onOpenChange={(open) => !open && setConfirmNaoPago(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Marcar como não pago?</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmNaoPago && (
                <>
                  Deseja realmente marcar o título de <strong>{confirmNaoPago.nome_fornecedor}</strong> no valor de{" "}
                  <strong>{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(confirmNaoPago.valor)}</strong> como não pago?
                  <br /><br />
                  O título voltará para a lista de pendentes na Gestão de Pagamentos.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => {
                if (confirmNaoPago) {
                  marcarComoNaoPago(confirmNaoPago.id);
                  setConfirmNaoPago(null);
                }
              }}
            >
              Sim, marcar como não pago
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
