import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Search, 
  FileText, 
  Download, 
  Eye, 
  Mail, 
  Loader2, 
  Trash2,
  CalendarDays,
  DollarSign,
  Package,
  Grid3x3,
  ChevronRight,
  FileSpreadsheet,
  Pencil,
  Plus,
  Minus,
  Send,
  RefreshCw
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

interface OSItem {
  id: number;
  os_numero?: string;
  boletim?: string;
  detalhes?: any;
  data_montagem?: string;
  cliente?: string;
  nome_produto?: string;
  valor_venda?: number;
  comissao_calculada?: number;
  comissao_editada?: number;
  adicional?: number;
  motivo_valor_extra?: string;
  servico?: string;
  valor_total?: number;
  endereco?: string;
  prestador_nome?: string;
  montador_nome?: string;
}

interface HistoricoItem {
  id: number;
  tipo: string;
  prestador_nome?: string;
  montador_nome?: string;
  periodo: string;
  valor_total: number;
  quantidade_os: number;
  data_envio: string;
  status: string;
  link_upload?: string;
  validade_link?: string;
  status_api?: number;
  nota_fiscal_path?: string;
}

interface EditItem {
  idx?: number;
  boletim?: string;
  identificador_boletim_montagem?: string;
  data_montagem?: string;
  data_da_montagem?: string;
  cliente?: string;
  nome_do_cliente?: string;
  nome_produto?: string;
  valor_venda?: number;
  media_de_valor_venda?: number;
  comissao_calculada?: number;
  comissao_editada?: number;
  adicional?: number;
  motivo_valor_extra?: string;
  tipo_servico?: string;
  selecionado: boolean;
}

export default function HistoricoEnvios() {
  const [tipoFiltro, setTipoFiltro] = useState<"todos" | "prestador" | "montador">("todos");
  const [statusFiltro, setStatusFiltro] = useState("todos");
  const [searchTerm, setSearchTerm] = useState("");
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialogId, setOpenDialogId] = useState<number | null>(null);
  const [osItems, setOsItems] = useState<OSItem[]>([]);
  const [loadingOS, setLoadingOS] = useState(false);
  
  // Estados para busca de OS/Boletim
  const [buscaOS, setBuscaOS] = useState("");
  const [buscandoOS, setBuscandoOS] = useState(false);
  const [resultadosBusca, setResultadosBusca] = useState<any[]>([]);
  const [mostrarResultados, setMostrarResultados] = useState(false);

  // Estados para modal de edição
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editandoEnvio, setEditandoEnvio] = useState<HistoricoItem | null>(null);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [itemsAtuais, setItemsAtuais] = useState<EditItem[]>([]);
  const [boletinsDisponiveis, setBoletinsDisponiveis] = useState<EditItem[]>([]);
  const [showAddItems, setShowAddItems] = useState(false);
  
  // Estado para formulário de novo item
  const [novoItem, setNovoItem] = useState({
    boletim: '',
    data_montagem: '',
    cliente: '',
    nome_produto: '',
    valor_venda: '',
    adicional: '',
    motivo_adicional: '',
    tipo_servico: 'MONTAGEM'
  });
  
  // Percentuais do montador para cálculo de comissão
  const [percentuais, setPercentuais] = useState({
    montagem: 0.05,
    assistencia: 0.05,
    desmontagem: 0.05
  });

  // Carregar histórico da API
  const carregarHistorico = async () => {
    try {
      setLoading(true);
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
      
      // Montar query params
      const params = new URLSearchParams();
      if (tipoFiltro !== "todos") {
        params.append("tipo", tipoFiltro);
      }
      if (statusFiltro !== "todos") {
        params.append("status", statusFiltro);
      }
      
      const url = `${API_BASE_URL}/relatorios/historico${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);

      if (response.ok) {
        const data = await response.json();
        setHistorico(data);
      } else {
        toast.error("Erro ao carregar histórico");
      }
    } catch (error) {
      console.error("Erro ao carregar histórico:", error);
      toast.error("Erro ao carregar histórico");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarHistorico();
  }, [tipoFiltro, statusFiltro]);

  const filteredData = historico.filter((item) => {
    const nome = item.prestador_nome || item.montador_nome || "";
    const matchSearch = nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        item.id.toString().includes(searchTerm) ||
                        item.periodo.toLowerCase().includes(searchTerm.toLowerCase());
    return matchSearch;
  });

  // Buscar O.S. ou Boletim específico
  const buscarOSouBoletim = async () => {
    if (!buscaOS.trim() || buscaOS.trim().length < 2) {
      toast.error("Digite pelo menos 2 caracteres para buscar");
      return;
    }
    
    try {
      setBuscandoOS(true);
      setMostrarResultados(true);
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
      const response = await fetch(`${API_BASE_URL}/relatorios/historico/buscar?q=${encodeURIComponent(buscaOS.trim())}`);
      
      if (response.ok) {
        const data = await response.json();
        setResultadosBusca(data);
        if (data.length === 0) {
          toast.info("Nenhum resultado encontrado");
        } else {
          toast.success(`${data.length} lote(s) encontrado(s)`);
        }
      } else {
        toast.error("Erro na busca");
      }
    } catch (error) {
      console.error("Erro ao buscar:", error);
      toast.error("Erro ao buscar OS/Boletim");
    } finally {
      setBuscandoOS(false);
    }
  };

  // Carregar O.S. do lote
  const loadOSItems = async (loteId: number, tipo: string) => {
    try {
      setLoadingOS(true);
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
      const response = await fetch(`${API_BASE_URL}/relatorios/historico/${loteId}/os?tipo=${tipo}`);
      
      if (response.ok) {
        const data = await response.json();
        setOsItems(data);
      } else {
        toast.error("Erro ao carregar itens");
      }
    } catch (error) {
      console.error("Erro ao carregar itens:", error);
      toast.error("Erro ao carregar itens");
    } finally {
      setLoadingOS(false);
    }
  };

  // Abrir dialog e carregar O.S.
  const handleOpenDialog = (item: HistoricoItem) => {
    setOpenDialogId(item.id);
    setOsItems([]);
    loadOSItems(item.id, item.tipo);
  };

  const handleDelete = async (id: number, tipo: string) => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
      const endpoint = tipo === "prestador" 
        ? `${API_BASE_URL}/relatorios/historico-envios/prestador/${id}`
        : `${API_BASE_URL}/relatorios/historico-envios/montador/${id}`;
      
      const response = await fetch(endpoint, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success(`${tipo === "prestador" ? "Lote" : "Envio"} excluído com sucesso!`);
        // Fechar o dialog
        setOpenDialogId(null);
        // Recarregar histórico
        setHistorico(prevHistorico => prevHistorico.filter(item => item.id !== id));
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao excluir");
      }
    } catch (error) {
      console.error("Erro ao excluir:", error);
      toast.error("Erro ao excluir registro");
    }
  };

  // Abrir modal de edição
  const handleOpenEdit = async (item: HistoricoItem) => {
    setEditandoEnvio(item);
    setEditDialogOpen(true);
    setLoadingEdit(true);
    setShowAddItems(false);
    
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
      const response = await fetch(
        `${API_BASE_URL}/relatorios/envio/${item.id}/editar-detalhes?tipo=${item.tipo}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setItemsAtuais(data.items_atuais || []);
        setBoletinsDisponiveis(data.boletins_disponiveis || []);
        
        // Carregar percentuais do montador
        if (data.percentuais) {
          setPercentuais({
            montagem: data.percentuais.montagem || 0.05,
            assistencia: data.percentuais.assistencia || 0.05,
            desmontagem: data.percentuais.desmontagem || 0.05
          });
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao carregar dados para edição");
        setEditDialogOpen(false);
      }
    } catch (error) {
      console.error("Erro ao carregar dados para edição:", error);
      toast.error("Erro ao carregar dados para edição");
      setEditDialogOpen(false);
    } finally {
      setLoadingEdit(false);
    }
  };

  // Toggle seleção de item atual
  const toggleItemAtual = (idx: number) => {
    setItemsAtuais(items => 
      items.map((item, i) => 
        i === idx ? { ...item, selecionado: !item.selecionado } : item
      )
    );
  };

  // Toggle seleção de item disponível para adicionar
  const toggleItemDisponivel = (idx: number) => {
    setBoletinsDisponiveis(items => 
      items.map((item, i) => 
        i === idx ? { ...item, selecionado: !item.selecionado } : item
      )
    );
  };

  // Adicionar itens selecionados da lista de disponíveis
  const adicionarItensSelecionados = () => {
    const itensParaAdicionar = boletinsDisponiveis.filter(item => item.selecionado);
    if (itensParaAdicionar.length === 0) {
      toast.warning("Selecione pelo menos um item para adicionar");
      return;
    }
    
    // Mover para lista de atuais
    setItemsAtuais(prev => [
      ...prev,
      ...itensParaAdicionar.map((item, idx) => ({
        ...item,
        idx: prev.length + idx,
        selecionado: true
      }))
    ]);
    
    // Remover da lista de disponíveis
    setBoletinsDisponiveis(prev => prev.filter(item => !item.selecionado));
    setShowAddItems(false);
    toast.success(`${itensParaAdicionar.length} item(s) adicionado(s)`);
  };

  // Adicionar novo item manualmente
  const adicionarNovoItemManual = () => {
    if (!novoItem.boletim.trim()) {
      toast.error("Preencha o número do boletim");
      return;
    }
    if (!novoItem.valor_venda || parseFloat(novoItem.valor_venda) <= 0) {
      toast.error("Preencha o valor de venda");
      return;
    }
    
    // Criar novo item
    const valorVenda = parseFloat(novoItem.valor_venda) || 0;
    const adicionalValor = parseFloat(novoItem.adicional) || 0;
    
    // Calcular comissão baseada no tipo de serviço e percentual
    let percentual = percentuais.montagem;
    if (novoItem.tipo_servico === 'ASSISTENCIA_TECNICA') {
      percentual = percentuais.assistencia;
    } else if (novoItem.tipo_servico === 'DESMONTAGEM') {
      percentual = percentuais.desmontagem;
    }
    const comissaoCalculada = valorVenda * percentual;
    
    const novoItemFormatado: EditItem = {
      idx: itemsAtuais.length,
      boletim: novoItem.boletim.trim(),
      data_montagem: novoItem.data_montagem || new Date().toLocaleDateString('pt-BR'),
      cliente: novoItem.cliente || '-',
      nome_produto: novoItem.nome_produto || '-',
      valor_venda: valorVenda,
      comissao_calculada: comissaoCalculada,
      adicional: adicionalValor,
      motivo_valor_extra: novoItem.motivo_adicional || '',
      tipo_servico: novoItem.tipo_servico,
      selecionado: true
    };
    
    // Adicionar à lista
    setItemsAtuais(prev => [...prev, novoItemFormatado]);
    
    // Limpar formulário
    setNovoItem({
      boletim: '',
      data_montagem: '',
      cliente: '',
      nome_produto: '',
      valor_venda: '',
      adicional: '',
      motivo_adicional: '',
      tipo_servico: 'MONTAGEM'
    });
    
    toast.success(`Boletim ${novoItem.boletim} adicionado!`);
  };

  // Salvar edição e reenviar
  const handleSalvarEReenviar = async () => {
    const itensSelecionados = itemsAtuais.filter(item => item.selecionado);
    
    if (itensSelecionados.length === 0) {
      toast.error("Selecione pelo menos um item para manter no envio");
      return;
    }
    
    if (!editandoEnvio) return;
    
    setSavingEdit(true);
    
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
      const response = await fetch(
        `${API_BASE_URL}/relatorios/envio/${editandoEnvio.id}/editar-reenviar`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tipo: editandoEnvio.tipo,
            items_selecionados: itensSelecionados
          })
        }
      );
      
      if (response.ok) {
        const result = await response.json();
        toast.success(result.message || "Envio atualizado e reenviado com sucesso!");
        
        // Lote original foi deletado e novo criado - recarregar histórico completo
        setEditDialogOpen(false);
        setEditandoEnvio(null);
        setOpenDialogId(null);
        
        // Recarregar dados do servidor
        carregarHistorico();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao salvar e reenviar");
      }
    } catch (error) {
      console.error("Erro ao salvar e reenviar:", error);
      toast.error("Erro ao salvar e reenviar");
    } finally {
      setSavingEdit(false);
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "Pago":
        return "default";
      case "Aguardando NF":
        return "secondary";
      case "N.F. RECEBIDA":
        return "outline";
      default:
        return "secondary";
    }
  };

  // Métricas
  const totalEnvios = historico.length;
  const totalValor = historico.reduce((acc, item) => acc + item.valor_total, 0);
  const totalOS = historico.reduce((acc, item) => acc + item.quantidade_os, 0);
  const totalPagos = historico.filter(item => item.status === "Pago").length;

  // Exportar para CSV
  const exportarCSV = () => {
    const headers = ['Lote', 'Tipo', 'Nome', 'Período', 'Qtd', 'Valor', 'Data Envio', 'Status'];
    const rows = filteredData.map(item => [
      item.id,
      item.tipo,
      item.prestador_nome || item.montador_nome || 'N/A',
      item.periodo,
      item.quantidade_os,
      item.valor_total.toFixed(2),
      new Date(item.data_envio).toLocaleString('pt-BR'),
      item.status
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `historico_envios_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.success(`${filteredData.length} registros exportados!`);
  };

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Histórico de Envios</h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1 md:mt-2">
            Consulta e gestão completa de relatórios enviados
          </p>
        </div>
        <Button onClick={exportarCSV} variant="outline" className="gap-2 w-full sm:w-auto">
          <FileSpreadsheet className="h-4 w-4" />
          Exportar CSV
        </Button>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <Card>
          <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
            <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FileText className="h-4 w-4 hidden sm:block" />
              Total de Envios
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 md:p-6 pt-0">
            <div className="text-xl md:text-2xl font-bold text-foreground">{totalEnvios}</div>
            <p className="text-xs text-muted-foreground mt-1 hidden sm:block">
              {historico.filter(h => h.tipo === 'prestador').length} prestadores / {historico.filter(h => h.tipo === 'montador').length} montadores
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
            <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Package className="h-4 w-4 hidden sm:block" />
              Total O.S.
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 md:p-6 pt-0">
            <div className="text-xl md:text-2xl font-bold text-foreground">{totalOS}</div>
            <p className="text-xs text-muted-foreground mt-1 hidden sm:block">Itens processados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
            <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground flex items-center gap-2">
              <DollarSign className="h-4 w-4 hidden sm:block" />
              Valor Total
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 md:p-6 pt-0">
            <div className="text-lg md:text-2xl font-bold text-foreground">
              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalValor)}
            </div>
            <p className="text-xs text-muted-foreground mt-1 hidden sm:block">Acumulado</p>
          </CardContent>
        </Card>

        <Card className="border-green-200 dark:border-green-900">
          <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
            <CardTitle className="text-xs md:text-sm font-medium text-green-600 dark:text-green-400 flex items-center gap-2">
              <CalendarDays className="h-4 w-4 hidden sm:block" />
              Pagos
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 md:p-6 pt-0">
            <div className="text-xl md:text-2xl font-bold text-green-600 dark:text-green-400">{totalPagos}</div>
            <p className="text-xs text-muted-foreground mt-1 hidden sm:block">{totalEnvios - totalPagos} pendentes</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros e Tabela */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4">
            <CardTitle className="text-base md:text-lg">Filtros e Busca</CardTitle>
            
            {/* Busca por OS/Boletim */}
            <div className="flex flex-col sm:flex-row gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-blue-500" />
                <Input
                  placeholder="🔍 Buscar O.S. ou Boletim para encontrar o lote..."
                  value={buscaOS}
                  onChange={(e) => {
                    setBuscaOS(e.target.value);
                    if (e.target.value === "") {
                      setMostrarResultados(false);
                      setResultadosBusca([]);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      buscarOSouBoletim();
                    }
                  }}
                  className="pl-9 bg-white dark:bg-background"
                />
              </div>
              <Button 
                onClick={buscarOSouBoletim} 
                disabled={buscandoOS || buscaOS.trim().length < 2}
                className="gap-2"
              >
                {buscandoOS ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Buscar
              </Button>
            </div>
            
            {/* Resultados da busca de OS/Boletim */}
            {mostrarResultados && (
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-muted px-4 py-2 flex items-center justify-between">
                  <span className="text-sm font-medium">
                    Resultados para "{buscaOS}" ({resultadosBusca.length})
                  </span>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => {
                      setMostrarResultados(false);
                      setBuscaOS("");
                      setResultadosBusca([]);
                    }}
                  >
                    ✕ Fechar
                  </Button>
                </div>
                {resultadosBusca.length === 0 && !buscandoOS ? (
                  <div className="p-4 text-center text-muted-foreground">
                    Nenhum lote encontrado com essa O.S. ou Boletim
                  </div>
                ) : (
                  <div className="divide-y">
                    {resultadosBusca.map((r, idx) => (
                      <div 
                        key={idx} 
                        className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-muted/50"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant={r.tipo === "prestador" ? "default" : "secondary"}>
                              {r.tipo === "prestador" ? "🔧 Prestador" : "🔨 Montador"}
                            </Badge>
                            <span className="font-semibold">Lote #{r.lote_id}</span>
                            <span className="text-muted-foreground">•</span>
                            <span>{r.nome}</span>
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            <span className="text-blue-600 dark:text-blue-400 font-medium">
                              {r.tipo_item}: {r.item_encontrado}
                            </span>
                            <span className="mx-2">•</span>
                            <span>Período: {r.periodo}</span>
                            <span className="mx-2">•</span>
                            <span>R$ {r.valor_total?.toFixed(2)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={r.status === "Pago" ? "default" : "outline"}>
                            {r.status}
                          </Badge>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => {
                              // Encontrar o item no histórico e abrir detalhes
                              const itemHistorico = historico.find(
                                h => h.id === r.lote_id && h.tipo === r.tipo
                              );
                              if (itemHistorico) {
                                handleOpenDialog(itemHistorico);
                              } else {
                                toast.info("Carregando lote...");
                                // Se não está no histórico atual, rolar para mostrar o lote
                              }
                            }}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Ver Lote
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <div className="relative sm:col-span-2">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Filtrar por nome, ID, período..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>

              <Select value={tipoFiltro} onValueChange={(v: any) => setTipoFiltro(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">📊 Todos os Tipos</SelectItem>
                  <SelectItem value="prestador">🔧 Prestadores</SelectItem>
                  <SelectItem value="montador">🔨 Montadores</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">⚪ Todos os Status</SelectItem>
                  <SelectItem value="Em Aberto">⏳ Em Aberto</SelectItem>
                  <SelectItem value="Aguardando NF">📄 Aguardando NF</SelectItem>
                  <SelectItem value="N.F. RECEBIDA">✅ N.F. RECEBIDA</SelectItem>
                  <SelectItem value="Pago">💰 Pago</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-16 text-center">
              <Loader2 className="h-10 w-10 mx-auto mb-4 animate-spin text-primary" />
              <p className="text-muted-foreground">Carregando histórico...</p>
            </div>
          ) : filteredData.length === 0 ? (
            <div className="py-16 text-center">
              <FileText className="mx-auto h-16 w-16 mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">Nenhum envio encontrado</h3>
              <p className="text-muted-foreground">Tente ajustar os filtros ou fazer uma nova busca</p>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Mostrando <span className="font-semibold">{filteredData.length}</span> de <span className="font-semibold">{historico.length}</span> registros
                </p>
              </div>
              
              {/* Mobile View - Cards */}
              <div className="space-y-3 md:hidden">
                {filteredData.map((item) => {
                  const nome = item.prestador_nome || item.montador_nome || "N/A";
                  return (
                    <Card key={item.id} className="overflow-hidden">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="font-mono text-xs">#{item.id}</Badge>
                            <Badge variant={item.tipo === "prestador" ? "default" : "secondary"} className="text-xs">
                              {item.tipo === "prestador" ? "🔧" : "🔨"}
                            </Badge>
                          </div>
                          <Badge variant={getStatusVariant(item.status)} className={`text-xs ${
                            item.status === "Pago" ? "bg-green-100 text-green-700 border-green-300" : ""
                          }`}>
                            {item.status}
                          </Badge>
                        </div>
                        
                        <div className="mb-3">
                          <p className="font-semibold text-foreground truncate">{nome}</p>
                          <p className="text-sm text-muted-foreground">{item.periodo}</p>
                        </div>
                        
                        <div className="grid grid-cols-3 gap-2 text-center mb-3">
                          <div className="bg-muted/50 rounded p-2">
                            <p className="text-xs text-muted-foreground">Qtd</p>
                            <p className="font-semibold">{item.quantidade_os}</p>
                          </div>
                          <div className="bg-muted/50 rounded p-2">
                            <p className="text-xs text-muted-foreground">Valor</p>
                            <p className="font-semibold text-sm">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.valor_total)}</p>
                          </div>
                          <div className="bg-muted/50 rounded p-2">
                            <p className="text-xs text-muted-foreground">Data</p>
                            <p className="font-semibold text-sm">{new Date(item.data_envio).toLocaleDateString("pt-BR")}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center justify-between pt-2 border-t">
                          {item.link_upload ? (
                            item.status_api === 1 ? (
                              <Badge className="bg-green-100 text-green-700 text-xs">✅ N.F. OK</Badge>
                            ) : (
                              <Badge className="bg-blue-100 text-blue-700 text-xs">📤 Enviado</Badge>
                            )
                          ) : (
                            <Badge variant="outline" className="bg-yellow-100 text-yellow-700 text-xs">⏳ Pendente</Badge>
                          )}
                          
                          <Dialog open={openDialogId === item.id} onOpenChange={(open) => {
                            if (open) {
                              handleOpenDialog(item);
                            } else {
                              setOpenDialogId(null);
                              setOsItems([]);
                            }
                          }}>
                            <DialogTrigger asChild>
                              <Button variant="ghost" size="sm" className="gap-1">
                                <Eye className="h-4 w-4" />
                                Ver Detalhes
                                <ChevronRight className="h-3 w-3" />
                              </Button>
                            </DialogTrigger>
                          </Dialog>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              {/* Desktop View - Table */}
              <div className="rounded-lg border overflow-hidden hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="font-semibold">Lote</TableHead>
                      <TableHead className="font-semibold">Tipo</TableHead>
                      <TableHead className="font-semibold">Nome</TableHead>
                      <TableHead className="font-semibold">Período</TableHead>
                      <TableHead className="font-semibold text-center">Qtd</TableHead>
                      <TableHead className="font-semibold text-right">Valor Total</TableHead>
                      <TableHead className="font-semibold">Data Envio</TableHead>
                      <TableHead className="font-semibold">Status</TableHead>
                      <TableHead className="font-semibold">Upload</TableHead>
                      <TableHead className="font-semibold text-right">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredData.map((item) => {
                      const nome = item.prestador_nome || item.montador_nome || "N/A";
                      
                      return (
                      <TableRow key={item.id} className="hover:bg-muted/50 transition-colors">
                        <TableCell>
                          <Badge variant="outline" className="font-mono">#{item.id}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={item.tipo === "prestador" ? "default" : "secondary"}>
                            {item.tipo === "prestador" ? "🔧 Prestador" : "🔨 Montador"}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium">{nome}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {item.periodo}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="outline" className="font-semibold">{item.quantidade_os}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-semibold">
                          {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.valor_total)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {new Date(item.data_envio).toLocaleDateString("pt-BR")}
                          <br />
                          <span className="text-xs text-muted-foreground">
                            {new Date(item.data_envio).toLocaleTimeString("pt-BR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(item.status)} className={
                            item.status === "Pago" ? "bg-green-100 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-400" : ""
                          }>
                            {item.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            {item.link_upload ? (
                              <>
                                {item.status_api === 1 ? (
                                  <Badge className="bg-green-100 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-400">
                                    ✅ N.F. OK
                                  </Badge>
                                ) : (
                                  <Badge className="bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-950 dark:text-blue-400">
                                    📤 Enviado
                                  </Badge>
                                )}
                              </>
                            ) : (
                              <Badge variant="outline" className="bg-yellow-100 text-yellow-700 border-yellow-300 dark:bg-yellow-950 dark:text-yellow-400">
                                ⏳ Pendente
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Dialog open={openDialogId === item.id} onOpenChange={(open) => {
                            if (open) {
                              handleOpenDialog(item);
                            } else {
                              setOpenDialogId(null);
                              setOsItems([]);
                            }
                          }}>
                            <DialogTrigger asChild>
                              <Button variant="ghost" size="sm" className="gap-1 md:gap-2 px-2 md:px-3">
                                <Eye className="h-4 w-4" />
                                <span className="hidden sm:inline">Ver Detalhes</span>
                                <ChevronRight className="h-3 w-3" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="w-[95vw] max-w-5xl max-h-[90vh] overflow-y-auto p-4 md:p-6">
                              <DialogHeader>
                                <DialogTitle className="text-lg md:text-xl flex items-center gap-2">
                                  <FileText className="h-5 w-5" />
                                  Detalhes do Envio #{item.id}
                                </DialogTitle>
                                <DialogDescription>
                                  {nome} - {item.periodo}
                                </DialogDescription>
                              </DialogHeader>
                              
                              <Tabs defaultValue="info" className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                  <TabsTrigger value="info" className="text-xs sm:text-sm">📋 Informações</TabsTrigger>
                                  <TabsTrigger value="grid" className="text-xs sm:text-sm">
                                    <Grid3x3 className="h-4 w-4 mr-1 md:mr-2" />
                                    {item.tipo === 'prestador' ? 'O.S.' : 'Boletins'} ({item.quantidade_os})
                                  </TabsTrigger>
                                </TabsList>
                                
                                <TabsContent value="info" className="space-y-4 mt-4">
                                  {/* Timeline */}
                                  <Card>
                                    <CardHeader className="pb-3">
                                      <CardTitle className="text-sm font-medium text-muted-foreground">
                                        Timeline do Envio
                                      </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                      <div className="space-y-4">
                                        {/* Criação do Lote */}
                                        <div className="flex gap-4">
                                          <div className="flex flex-col items-center">
                                            <div className="w-3 h-3 rounded-full bg-primary"></div>
                                            <div className="w-0.5 h-full bg-border mt-2"></div>
                                          </div>
                                          <div className="flex-1 pb-4">
                                            <div className="flex items-center gap-2 mb-1">
                                              <span className="font-semibold">Lote Criado</span>
                                              <Badge variant="outline" className="text-xs">
                                                {new Date(item.data_envio).toLocaleDateString('pt-BR')}
                                              </Badge>
                                            </div>
                                            <p className="text-sm text-muted-foreground">
                                              {item.tipo === 'prestador' ? 'Relatório de prestador' : 'Relatório de montador'} gerado com {item.quantidade_os} {item.tipo === 'prestador' ? 'O.S.' : 'itens'}
                                            </p>
                                          </div>
                                        </div>

                                        {/* Email Enviado */}
                                        <div className="flex gap-4">
                                          <div className="flex flex-col items-center">
                                            <div className={`w-3 h-3 rounded-full ${item.link_upload ? 'bg-blue-500' : 'bg-muted'}`}></div>
                                            <div className="w-0.5 h-full bg-border mt-2"></div>
                                          </div>
                                          <div className="flex-1 pb-4">
                                            <div className="flex items-center gap-2 mb-1">
                                              <span className={`font-semibold ${!item.link_upload && 'text-muted-foreground'}`}>
                                                Email Enviado
                                              </span>
                                              {item.link_upload && (
                                                <Badge className="text-xs bg-blue-500">
                                                  {new Date(item.data_envio).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                                                </Badge>
                                              )}
                                            </div>
                                            <p className="text-sm text-muted-foreground">
                                              {item.link_upload ? (
                                                <>Relatório enviado com link para upload de NF</>
                                              ) : (
                                                <>Aguardando envio de email</>
                                              )}
                                            </p>
                                          </div>
                                        </div>

                                        {/* NF Recebida */}
                                        <div className="flex gap-4">
                                          <div className="flex flex-col items-center">
                                            <div className={`w-3 h-3 rounded-full ${item.nota_fiscal_path || item.status_api === 1 ? 'bg-green-500' : 'bg-muted'}`}></div>
                                            <div className="w-0.5 h-full bg-border mt-2"></div>
                                          </div>
                                          <div className="flex-1 pb-4">
                                            <div className="flex items-center gap-2 mb-1">
                                              <span className={`font-semibold ${!(item.nota_fiscal_path || item.status_api === 1) && 'text-muted-foreground'}`}>
                                                Nota Fiscal Recebida
                                              </span>
                                              {(item.nota_fiscal_path || item.status_api === 1) && (
                                                <Badge className="text-xs bg-green-500">
                                                  ✓ Confirmado
                                                </Badge>
                                              )}
                                            </div>
                                            <p className="text-sm text-muted-foreground">
                                              {item.nota_fiscal_path ? (
                                                <>NF armazenada: {item.nota_fiscal_path.split('/').pop()}</>
                                              ) : item.status_api === 1 ? (
                                                <>NF recebida via upload</>
                                              ) : (
                                                <>Aguardando recebimento da NF</>
                                              )}
                                            </p>
                                          </div>
                                        </div>

                                        {/* Pagamento */}
                                        <div className="flex gap-4">
                                          <div className="flex flex-col items-center">
                                            <div className={`w-3 h-3 rounded-full ${item.status === 'Pago' ? 'bg-green-600' : 'bg-muted'}`}></div>
                                          </div>
                                          <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                              <span className={`font-semibold ${item.status !== 'Pago' && 'text-muted-foreground'}`}>
                                                Pagamento Realizado
                                              </span>
                                              {item.status === 'Pago' && (
                                                <Badge className="text-xs bg-green-600">
                                                  ✓ Concluído
                                                </Badge>
                                              )}
                                            </div>
                                            <p className="text-sm text-muted-foreground">
                                              {item.status === 'Pago' ? (
                                                <>Pagamento confirmado - {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.valor_total)}</>
                                              ) : (
                                                <>Aguardando pagamento - Status: {item.status}</>
                                              )}
                                            </p>
                                          </div>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>

                                  <div className="grid grid-cols-2 gap-3 md:gap-6">
                                    <Card>
                                      <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
                                        <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground">Tipo</CardTitle>
                                      </CardHeader>
                                      <CardContent className="p-3 md:p-6 pt-0">
                                        <Badge variant={item.tipo === "prestador" ? "default" : "secondary"} className="text-sm md:text-base">
                                          {item.tipo === "prestador" ? "🔧 Prestador" : "🔨 Montador"}
                                        </Badge>
                                      </CardContent>
                                    </Card>
                                    
                                    <Card>
                                      <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
                                        <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground">Status</CardTitle>
                                      </CardHeader>
                                      <CardContent className="p-3 md:p-6 pt-0">
                                        <Badge variant={getStatusVariant(item.status)} className="text-sm md:text-base">
                                          {item.status}
                                        </Badge>
                                      </CardContent>
                                    </Card>
                                    
                                    <Card>
                                      <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
                                        <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground">Valor Total</CardTitle>
                                      </CardHeader>
                                      <CardContent className="p-3 md:p-6 pt-0">
                                        <p className="text-lg md:text-2xl font-bold text-primary">
                                          {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.valor_total)}
                                        </p>
                                      </CardContent>
                                    </Card>
                                    
                                    <Card>
                                      <CardHeader className="pb-2 md:pb-3 p-3 md:p-6">
                                        <CardTitle className="text-xs md:text-sm font-medium text-muted-foreground">Quantidade</CardTitle>
                                      </CardHeader>
                                      <CardContent className="p-3 md:p-6 pt-0">
                                        <p className="text-lg md:text-2xl font-bold">
                                          {item.quantidade_os} {item.tipo === "prestador" ? "O.S." : "itens"}
                                        </p>
                                      </CardContent>
                                    </Card>
                                  </div>

                                  {item.link_upload && (
                                    <Card className="border-blue-200 dark:border-blue-900">
                                      <CardHeader className="pb-3">
                                        <CardTitle className="text-sm font-medium text-blue-600 dark:text-blue-400">
                                          🔗 Link de Upload
                                        </CardTitle>
                                      </CardHeader>
                                      <CardContent>
                                        <code className="block text-xs bg-muted p-3 rounded break-all font-mono">
                                          {item.link_upload}
                                        </code>
                                        {item.validade_link && (
                                          <p className="text-xs text-muted-foreground mt-2">
                                            ⏰ Válido até: {new Date(item.validade_link).toLocaleDateString("pt-BR")} às{" "}
                                            {new Date(item.validade_link).toLocaleTimeString("pt-BR")}
                                          </p>
                                        )}
                                      </CardContent>
                                    </Card>
                                  )}

                                  {item.nota_fiscal_path && (
                                    <Card className="border-green-200 dark:border-green-900">
                                      <CardHeader className="pb-3">
                                        <CardTitle className="text-sm font-medium text-green-600 dark:text-green-400">
                                          ✅ Nota Fiscal Recebida
                                        </CardTitle>
                                      </CardHeader>
                                      <CardContent>
                                        <p className="text-sm font-mono">{item.nota_fiscal_path}</p>
                                      </CardContent>
                                    </Card>
                                  )}

                                  <Separator />

                                  <div className="flex flex-col sm:flex-row gap-3">
                                    <Button 
                                      variant="outline" 
                                      className="flex-1 gap-2"
                                      onClick={() => {
                                        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:14001/api/v1';
                                        window.open(`${API_BASE_URL}/relatorios/download-relatorio/${item.tipo}/${item.id}`, '_blank');
                                      }}
                                    >
                                      <Download className="h-4 w-4" />
                                      <span className="hidden sm:inline">Baixar</span> PDF
                                    </Button>
                                    
                                    {item.tipo === "montador" && (
                                      <Button 
                                        variant="outline" 
                                        className="flex-1 gap-2 border-blue-300 text-blue-600 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-400 dark:hover:bg-blue-950"
                                        onClick={() => handleOpenEdit(item)}
                                      >
                                        <Pencil className="h-4 w-4" />
                                        <span className="hidden sm:inline">Editar e</span> Reenviar
                                      </Button>
                                    )}
                                    
                                    <AlertDialog>
                                      <AlertDialogTrigger asChild>
                                        <Button variant="destructive" className="flex-1 gap-2">
                                          <Trash2 className="h-4 w-4" />
                                          Excluir
                                        </Button>
                                      </AlertDialogTrigger>
                                      <AlertDialogContent>
                                        <AlertDialogHeader>
                                          <AlertDialogTitle>Confirmar Exclusão</AlertDialogTitle>
                                          <AlertDialogDescription>
                                            Tem certeza que deseja excluir este {item.tipo === "prestador" ? "lote" : "envio"}? 
                                            {item.tipo === "prestador" && " Todas as O.S. relacionadas também serão excluídas."}
                                            {" "}Esta ação não pode ser desfeita.
                                          </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                          <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                          <AlertDialogAction
                                            onClick={() => handleDelete(item.id, item.tipo)}
                                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                          >
                                            Excluir
                                          </AlertDialogAction>
                                        </AlertDialogFooter>
                                      </AlertDialogContent>
                                    </AlertDialog>
                                  </div>
                                </TabsContent>
                                
                                <TabsContent value="grid" className="mt-4">
                                  {loadingOS ? (
                                    <div className="py-12 text-center">
                                      <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-primary" />
                                      <p className="text-muted-foreground">Carregando {item.tipo === 'prestador' ? 'O.S.' : 'boletins'}...</p>
                                    </div>
                                  ) : osItems.length === 0 ? (
                                    <div className="py-12 text-center">
                                      <Package className="mx-auto h-12 w-12 mb-4 text-muted-foreground" />
                                      <p className="text-muted-foreground">Nenhum item encontrado</p>
                                    </div>
                                  ) : (
                                    <Card>
                                      <CardContent className="p-0">
                                        <div className="rounded-lg border overflow-x-auto">
                                          <Table>
                                            <TableHeader>
                                              <TableRow className="bg-muted/50">
                                                <TableHead className="font-semibold w-16">#</TableHead>
                                                {item.tipo === 'prestador' ? (
                                                  <>
                                                    <TableHead className="font-semibold min-w-[100px]">O.S. Número</TableHead>
                                                    <TableHead className="font-semibold min-w-[200px]">Cliente</TableHead>
                                                    <TableHead className="font-semibold min-w-[200px]">Serviço</TableHead>
                                                    <TableHead className="font-semibold text-right min-w-[120px]">Valor</TableHead>
                                                  </>
                                                ) : (
                                                  <>
                                                    <TableHead className="font-semibold min-w-[120px]">Boletim</TableHead>
                                                    <TableHead className="font-semibold min-w-[130px]">Data Montagem</TableHead>
                                                    <TableHead className="font-semibold min-w-[200px]">Cliente</TableHead>
                                                    <TableHead className="font-semibold min-w-[180px]">Produto</TableHead>
                                                    <TableHead className="font-semibold text-right min-w-[120px]">Valor Venda</TableHead>
                                                    <TableHead className="font-semibold text-right min-w-[120px]">Comissão</TableHead>
                                                    <TableHead className="font-semibold text-right min-w-[110px]">Valor Extra</TableHead>
                                                    <TableHead className="font-semibold min-w-[150px]">Motivo Extra</TableHead>
                                                  </>
                                                )}
                                              </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                              {osItems.map((os, idx) => {
                                                // Para prestadores, os campos já vêm extraídos da API
                                                const cliente = os.cliente || '-';
                                                const servico = os.servico || '-';
                                                const valorRaw = os.valor_total || 0;
                                                const valor = parseFloat(String(valorRaw)) || 0;
                                                
                                                // Para montadores - buscar direto no objeto os primeiro, depois em detalhes
                                                const valorVendaRaw = os.valor_venda || 0;
                                                const valorVenda = parseFloat(String(valorVendaRaw)) || 0;
                                                
                                                const comissaoRaw = os.comissao_editada || 
                                                                   os.comissao_calculada || 
                                                                   0;
                                                const comissao = parseFloat(String(comissaoRaw)) || 0;
                                                
                                                return (
                                                  <TableRow key={os.id} className="hover:bg-muted/50">
                                                    <TableCell className="font-mono text-sm text-muted-foreground">
                                                      {idx + 1}
                                                    </TableCell>
                                                    {item.tipo === 'prestador' ? (
                                                      <>
                                                        <TableCell className="font-semibold">
                                                          {os.os_numero || '-'}
                                                        </TableCell>
                                                        <TableCell className="text-sm">
                                                          {cliente}
                                                        </TableCell>
                                                        <TableCell className="text-sm">
                                                          {servico}
                                                        </TableCell>
                                                        <TableCell className="text-right font-semibold tabular-nums">
                                                          {valor > 0 ? 
                                                            new Intl.NumberFormat('pt-BR', { 
                                                              style: 'currency', 
                                                              currency: 'BRL',
                                                              minimumFractionDigits: 2 
                                                            }).format(valor) 
                                                            : 'R$ 0,00'}
                                                        </TableCell>
                                                      </>
                                                    ) : (
                                                      <>
                                                        <TableCell className="font-semibold">
                                                          {os.boletim || '-'}
                                                        </TableCell>
                                                        <TableCell className="text-sm">
                                                          {os.data_montagem || '-'}
                                                        </TableCell>
                                                        <TableCell className="text-sm">
                                                          {os.cliente || '-'}
                                                        </TableCell>
                                                        <TableCell className="text-sm">
                                                          {os.nome_produto || '-'}
                                                        </TableCell>
                                                        <TableCell className="text-right font-semibold tabular-nums">
                                                          {valorVenda > 0 ? 
                                                            new Intl.NumberFormat('pt-BR', { 
                                                              style: 'currency', 
                                                              currency: 'BRL',
                                                              minimumFractionDigits: 2 
                                                            }).format(valorVenda) 
                                                            : 'R$ 0,00'}
                                                        </TableCell>
                                                        <TableCell className="text-right font-semibold tabular-nums">
                                                          {comissao > 0 ? 
                                                            new Intl.NumberFormat('pt-BR', { 
                                                              style: 'currency', 
                                                              currency: 'BRL',
                                                              minimumFractionDigits: 2 
                                                            }).format(comissao) 
                                                            : 'R$ 0,00'}
                                                        </TableCell>
                                                        <TableCell className="text-right font-semibold tabular-nums">
                                                          {(os.adicional || 0) > 0 ? 
                                                            new Intl.NumberFormat('pt-BR', { 
                                                              style: 'currency', 
                                                              currency: 'BRL',
                                                              minimumFractionDigits: 2 
                                                            }).format(os.adicional || 0) 
                                                            : 'R$ 0,00'}
                                                        </TableCell>
                                                        <TableCell className="text-sm text-muted-foreground">
                                                          {os.motivo_valor_extra || '-'}
                                                        </TableCell>
                                                      </>
                                                    )}
                                                  </TableRow>
                                                );
                                              })}
                                            </TableBody>
                                          </Table>
                                        </div>
                                        
                                        {/* Resumo abaixo da tabela */}
                                        <div className="p-4 bg-muted/30 border-t">
                                          <div className="flex items-center justify-between text-sm">
                                            <span className="text-muted-foreground">
                                              Total de {item.tipo === 'prestador' ? 'O.S.' : 'boletins'}: 
                                              <span className="font-semibold ml-1">{osItems.length}</span>
                                            </span>
                                            {item.tipo === 'prestador' ? (
                                              <span className="font-semibold text-lg">
                                                Total: {new Intl.NumberFormat('pt-BR', { 
                                                  style: 'currency', 
                                                  currency: 'BRL' 
                                                }).format(
                                                  osItems.reduce((acc, os) => {
                                                    const valorRaw = os.valor_total || 0;
                                                    return acc + (parseFloat(String(valorRaw)) || 0);
                                                  }, 0)
                                                )}
                                              </span>
                                            ) : (
                                              <div className="flex gap-6">
                                                <span className="text-muted-foreground">
                                                  Valor Venda: 
                                                  <span className="font-semibold ml-1">
                                                    {new Intl.NumberFormat('pt-BR', { 
                                                      style: 'currency', 
                                                      currency: 'BRL' 
                                                    }).format(
                                                      osItems.reduce((acc, os) => {
                                                        const valorVendaRaw = os.valor_venda || 0;
                                                        return acc + (parseFloat(String(valorVendaRaw)) || 0);
                                                      }, 0)
                                                    )}
                                                  </span>
                                                </span>
                                                <span className="font-semibold text-lg">
                                                  Total Comissão: {new Intl.NumberFormat('pt-BR', { 
                                                    style: 'currency', 
                                                    currency: 'BRL' 
                                                  }).format(
                                                    osItems.reduce((acc, os) => {
                                                      const comissaoRaw = os.comissao_editada || os.comissao_calculada || 0;
                                                      return acc + (parseFloat(String(comissaoRaw)) || 0);
                                                    }, 0)
                                                  )}
                                                </span>
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </CardContent>
                                    </Card>
                                  )}
                                </TabsContent>
                              </Tabs>
                            </DialogContent>
                          </Dialog>
                        </TableCell>
                      </TableRow>
                    )})}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Modal de Edição e Reenvio */}
      <Dialog open={editDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setEditDialogOpen(false);
          setEditandoEnvio(null);
          setItemsAtuais([]);
          setBoletinsDisponiveis([]);
          setShowAddItems(false);
        }
      }}>
        <DialogContent className="w-[95vw] max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Pencil className="h-5 w-5" />
              Editar Envio #{editandoEnvio?.id}
            </DialogTitle>
            <DialogDescription>
              {editandoEnvio?.montador_nome || editandoEnvio?.prestador_nome} - {editandoEnvio?.periodo}
            </DialogDescription>
          </DialogHeader>

          {loadingEdit ? (
            <div className="py-12 text-center">
              <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-primary" />
              <p className="text-muted-foreground">Carregando dados para edição...</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Items Atuais */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">
                      Items no Envio ({itemsAtuais.filter(i => i.selecionado).length} de {itemsAtuais.length} selecionados)
                    </CardTitle>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddItems(!showAddItems)}
                      className="gap-2"
                    >
                      <Plus className="h-4 w-4" />
                      Adicionar Items
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[300px] overflow-y-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="w-10"></TableHead>
                          <TableHead>Boletim</TableHead>
                          <TableHead>Data</TableHead>
                          <TableHead>Cliente</TableHead>
                          <TableHead>Produto</TableHead>
                          <TableHead className="text-right">Valor</TableHead>
                          <TableHead className="text-right">Comissão</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {itemsAtuais.map((item, idx) => (
                          <TableRow 
                            key={idx} 
                            className={`cursor-pointer transition-colors ${!item.selecionado ? 'opacity-50 bg-red-50 dark:bg-red-950/20' : 'hover:bg-muted/50'}`}
                            onClick={() => toggleItemAtual(idx)}
                          >
                            <TableCell>
                              <Checkbox 
                                checked={item.selecionado}
                                onCheckedChange={() => toggleItemAtual(idx)}
                              />
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {item.boletim || item.identificador_boletim_montagem || '-'}
                            </TableCell>
                            <TableCell className="text-sm">
                              {item.data_montagem || item.data_da_montagem || '-'}
                            </TableCell>
                            <TableCell className="text-sm">
                              {item.cliente || item.nome_do_cliente || '-'}
                            </TableCell>
                            <TableCell className="text-sm">
                              {item.nome_produto || '-'}
                            </TableCell>
                            <TableCell className="text-right text-sm">
                              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
                                item.valor_venda || item.media_de_valor_venda || 0
                              )}
                            </TableCell>
                            <TableCell className="text-right font-semibold">
                              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
                                item.comissao_editada || item.comissao_calculada || 0
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Totais */}
                  <div className="mt-4 pt-4 border-t flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      {itemsAtuais.filter(i => !i.selecionado).length > 0 && (
                        <span className="text-red-500">
                          {itemsAtuais.filter(i => !i.selecionado).length} item(s) será(ão) removido(s)
                        </span>
                      )}
                    </span>
                    <span className="font-semibold">
                      Novo Total: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
                        itemsAtuais
                          .filter(i => i.selecionado)
                          .reduce((acc, item) => acc + (item.comissao_editada || item.comissao_calculada || 0) + (item.adicional || 0), 0)
                      )}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Painel de Adicionar Items */}
              {showAddItems && (
                <Card className="border-blue-200 dark:border-blue-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm text-blue-600 dark:text-blue-400">
                      Adicionar Novo Boletim
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Boletim *</label>
                        <Input
                          placeholder="Ex: H1234"
                          value={novoItem.boletim}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, boletim: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Data Montagem</label>
                        <Input
                          type="date"
                          value={novoItem.data_montagem}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, data_montagem: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Cliente</label>
                        <Input
                          placeholder="Nome do cliente"
                          value={novoItem.cliente}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, cliente: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Produto</label>
                        <Input
                          placeholder="Nome do produto"
                          value={novoItem.nome_produto}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, nome_produto: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Valor Venda *</label>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="0,00"
                          value={novoItem.valor_venda}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, valor_venda: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Tipo Serviço</label>
                        <Select
                          value={novoItem.tipo_servico}
                          onValueChange={(value) => setNovoItem(prev => ({ ...prev, tipo_servico: value }))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="MONTAGEM">Montagem</SelectItem>
                            <SelectItem value="ASSISTENCIA_TECNICA">Assistência Técnica</SelectItem>
                            <SelectItem value="DESMONTAGEM">Desmontagem</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Custo Extra</label>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="0,00"
                          value={novoItem.adicional}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, adicional: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Motivo Custo Extra</label>
                        <Input
                          placeholder="Ex: Deslocamento, peça extra..."
                          value={novoItem.motivo_adicional}
                          onChange={(e) => setNovoItem(prev => ({ ...prev, motivo_adicional: e.target.value }))}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowAddItems(false)}
                      >
                        Cancelar
                      </Button>
                      <Button
                        size="sm"
                        onClick={adicionarNovoItemManual}
                        className="gap-2"
                      >
                        <Plus className="h-4 w-4" />
                        Adicionar ao Envio
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Separator />

              {/* Botões de Ação */}
              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setEditDialogOpen(false)}
                  disabled={savingEdit}
                >
                  Cancelar
                </Button>
                <Button
                  onClick={handleSalvarEReenviar}
                  disabled={savingEdit || itemsAtuais.filter(i => i.selecionado).length === 0}
                  className="gap-2"
                >
                  {savingEdit ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Salvando...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      Salvar e Reenviar
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
