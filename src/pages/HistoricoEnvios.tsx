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
import { Search, FileText, Download, Eye, Mail, MessageSquare, Loader2, Trash2 } from "lucide-react";
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
import { toast } from "sonner";

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
    const matchSearch = nome.toLowerCase().includes(searchTerm.toLowerCase());
    return matchSearch;
  });

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Histórico de Envios</h1>
        <p className="text-muted-foreground">
          Consultar todos os relatórios enviados por prestador e montador
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <CardTitle>Filtros</CardTitle>
            <div className="flex flex-wrap gap-3">
              <Select value={tipoFiltro} onValueChange={(v: any) => setTipoFiltro(v)}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos</SelectItem>
                  <SelectItem value="prestador">Prestadores</SelectItem>
                  <SelectItem value="montador">Montadores</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos os Status</SelectItem>
                  <SelectItem value="Em Aberto">Em Aberto</SelectItem>
                  <SelectItem value="Aguardando NF">Aguardando NF</SelectItem>
                  <SelectItem value="N.F. RECEBIDA">N.F. RECEBIDA</SelectItem>
                  <SelectItem value="Pago">Pago</SelectItem>
                </SelectContent>
              </Select>

              <div className="relative flex-1 min-w-64">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nome..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {loading ? (
              <div className="py-12 text-center">
                <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-primary" />
                <p className="text-muted-foreground">Carregando histórico...</p>
              </div>
            ) : filteredData.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <FileText className="mx-auto h-12 w-12 mb-4" />
                <p>Nenhum envio encontrado com os filtros selecionados</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Lote</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Nome</TableHead>
                    <TableHead>Período</TableHead>
                    <TableHead>Qtd</TableHead>
                    <TableHead>Valor Total</TableHead>
                    <TableHead>Data Envio</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Upload</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredData.map((item) => {
                    const nome = item.prestador_nome || item.montador_nome || "N/A";
                    
                    return (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Badge variant="outline">#{item.id}</Badge>
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
                      <TableCell>
                        <span className="text-sm">{item.quantidade_os}</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold">
                          R$ {item.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                        </span>
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
                          item.status === "Pago" ? "bg-success text-success-foreground" : ""
                        }>
                          {item.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          {item.link_upload ? (
                            <>
                              {item.status_api === 1 ? (
                                <Badge className="bg-green-50 text-green-700 border-green-300">
                                  ✅ N.F. Recebida
                                </Badge>
                              ) : (
                                <Badge className="bg-blue-50 text-blue-700 border-blue-300">
                                  📤 Link enviado
                                </Badge>
                              )}
                            </>
                          ) : (
                            <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
                              ⏳ Aguardando
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Dialog open={openDialogId === item.id} onOpenChange={(open) => setOpenDialogId(open ? item.id : null)}>
                          <DialogTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle>Detalhes do Envio #{item.id}</DialogTitle>
                              <DialogDescription>
                                {nome} - {item.periodo}
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <p className="text-sm font-medium text-muted-foreground">Tipo</p>
                                  <p className="text-base font-semibold capitalize">{item.tipo}</p>
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-muted-foreground">Status</p>
                                  <Badge variant={getStatusVariant(item.status)}>
                                    {item.status}
                                  </Badge>
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-muted-foreground">Valor Total</p>
                                  <p className="text-lg font-bold text-primary">
                                    R$ {item.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-muted-foreground">Quantidade</p>
                                  <p className="text-base font-semibold">
                                    {item.quantidade_os} {item.tipo === "prestador" ? "OS" : "montagens"}
                                  </p>
                                </div>
                              </div>

                              {item.link_upload && (
                                <div className="rounded-lg border border-border bg-muted/50 p-4">
                                  <p className="text-sm font-medium mb-2">🔗 Link de Upload</p>
                                  <code className="block text-xs bg-background p-2 rounded break-all">
                                    {item.link_upload}
                                  </code>
                                  {item.validade_link && (
                                    <p className="text-xs text-muted-foreground mt-2">
                                      Válido até: {new Date(item.validade_link).toLocaleDateString("pt-BR")}
                                    </p>
                                  )}
                                </div>
                              )}

                              {item.nota_fiscal_path && (
                                <div className="rounded-lg border border-success bg-green-50 p-4">
                                  <p className="text-sm font-medium text-green-700">✅ Nota Fiscal Recebida</p>
                                  <p className="text-xs text-muted-foreground mt-1">{item.nota_fiscal_path}</p>
                                </div>
                              )}

                              <div className="flex gap-2">
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
                            </div>
                          </DialogContent>
                        </Dialog>
                      </TableCell>
                    </TableRow>
                  )})}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
