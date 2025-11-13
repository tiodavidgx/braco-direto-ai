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
  FileSpreadsheet
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

export default function HistoricoEnvios() {
  const [tipoFiltro, setTipoFiltro] = useState<"todos" | "prestador" | "montador">("todos");
  const [statusFiltro, setStatusFiltro] = useState("todos");
  const [searchTerm, setSearchTerm] = useState("");
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialogId, setOpenDialogId] = useState<number | null>(null);
  const [osItems, setOsItems] = useState<OSItem[]>([]);
  const [loadingOS, setLoadingOS] = useState(false);

  // Carregar histórico da API
  useEffect(() => {
    const loadHistorico = async () => {
      try {
        setLoading(true);
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
        
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

    loadHistorico();
  }, [tipoFiltro, statusFiltro]);

  const filteredData = historico.filter((item) => {
    const nome = item.prestador_nome || item.montador_nome || "";
    const matchSearch = nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        item.id.toString().includes(searchTerm) ||
                        item.periodo.toLowerCase().includes(searchTerm.toLowerCase());
    return matchSearch;
  });

  // Carregar O.S. do lote
  const loadOSItems = async (loteId: number, tipo: string) => {
    try {
      setLoadingOS(true);
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
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
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Histórico de Envios</h1>
          <p className="text-muted-foreground mt-2">
            Consulta e gestão completa de relatórios enviados
          </p>
        </div>
        <Button onClick={exportarCSV} variant="outline" className="gap-2">
          <FileSpreadsheet className="h-4 w-4" />
          Exportar CSV
        </Button>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Total de Envios
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{totalEnvios}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {historico.filter(h => h.tipo === 'prestador').length} prestadores / {historico.filter(h => h.tipo === 'montador').length} montadores
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Package className="h-4 w-4" />
              Total O.S./Itens
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{totalOS}</div>
            <p className="text-xs text-muted-foreground mt-1">Itens processados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Valor Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalValor)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Acumulado</p>
          </CardContent>
        </Card>

        <Card className="border-green-200 dark:border-green-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-green-600 dark:text-green-400 flex items-center gap-2">
              <CalendarDays className="h-4 w-4" />
              Pagos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{totalPagos}</div>
            <p className="text-xs text-muted-foreground mt-1">{totalEnvios - totalPagos} pendentes</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros e Tabela */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4">
            <CardTitle className="text-lg">Filtros e Busca</CardTitle>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="relative md:col-span-2">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nome, ID, período..."
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
              
              <div className="rounded-lg border overflow-hidden">
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
                              <Button variant="ghost" size="sm" className="gap-2">
                                <Eye className="h-4 w-4" />
                                Ver Detalhes
                                <ChevronRight className="h-3 w-3" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
                              <DialogHeader>
                                <DialogTitle className="text-xl flex items-center gap-2">
                                  <FileText className="h-5 w-5" />
                                  Detalhes do Envio #{item.id}
                                </DialogTitle>
                                <DialogDescription>
                                  {nome} - {item.periodo}
                                </DialogDescription>
                              </DialogHeader>
                              
                              <Tabs defaultValue="info" className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                  <TabsTrigger value="info">📋 Informações</TabsTrigger>
                                  <TabsTrigger value="grid">
                                    <Grid3x3 className="h-4 w-4 mr-2" />
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

                                  <div className="grid grid-cols-2 gap-6">
                                    <Card>
                                      <CardHeader className="pb-3">
                                        <CardTitle className="text-sm font-medium text-muted-foreground">Tipo</CardTitle>
                                      </CardHeader>
                                      <CardContent>
                                        <Badge variant={item.tipo === "prestador" ? "default" : "secondary"} className="text-base">
                                          {item.tipo === "prestador" ? "🔧 Prestador" : "🔨 Montador"}
                                        </Badge>
                                      </CardContent>
                                    </Card>
                                    
                                    <Card>
                                      <CardHeader className="pb-3">
                                        <CardTitle className="text-sm font-medium text-muted-foreground">Status</CardTitle>
                                      </CardHeader>
                                      <CardContent>
                                        <Badge variant={getStatusVariant(item.status)} className="text-base">
                                          {item.status}
                                        </Badge>
                                      </CardContent>
                                    </Card>
                                    
                                    <Card>
                                      <CardHeader className="pb-3">
                                        <CardTitle className="text-sm font-medium text-muted-foreground">Valor Total</CardTitle>
                                      </CardHeader>
                                      <CardContent>
                                        <p className="text-2xl font-bold text-primary">
                                          {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.valor_total)}
                                        </p>
                                      </CardContent>
                                    </Card>
                                    
                                    <Card>
                                      <CardHeader className="pb-3">
                                        <CardTitle className="text-sm font-medium text-muted-foreground">Quantidade</CardTitle>
                                      </CardHeader>
                                      <CardContent>
                                        <p className="text-2xl font-bold">
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

                                  <div className="flex gap-3">
                                    <Button variant="outline" className="flex-1 gap-2">
                                      <Download className="h-4 w-4" />
                                      Baixar PDF
                                    </Button>
                                    <Button variant="outline" className="flex-1 gap-2">
                                      <Mail className="h-4 w-4" />
                                      Reenviar Email
                                    </Button>
                                    
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
    </div>
  );
}
