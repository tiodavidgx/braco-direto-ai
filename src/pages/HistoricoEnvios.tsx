import { useState } from "react";
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
import { Search, FileText, Download, Eye, Mail, MessageSquare } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export default function HistoricoEnvios() {
  const [tipoFiltro, setTipoFiltro] = useState<"todos" | "prestador" | "montador">("todos");
  const [statusFiltro, setStatusFiltro] = useState("todos");
  const [searchTerm, setSearchTerm] = useState("");

  // Mock data - substituir por dados reais da API
  const historico = [
    {
      id: 1,
      tipo: "prestador",
      loteId: 101,
      nome: "Prestadora ABC Ltda",
      periodo: "01/11/2025 - 07/11/2025",
      valorTotal: 15480.5,
      quantidadeOS: 12,
      dataEnvio: "2025-11-08T10:30:00",
      status: "Aguardando NF",
      emailEnviado: true,
      whatsappEnviado: true,
      linkUpload: "https://api.link.dev.br/upload/abc123",
    },
    {
      id: 2,
      tipo: "montador",
      loteId: 201,
      nome: "João Silva",
      periodo: "Novembro/2025",
      valorTotal: 3250.0,
      quantidadeOS: 8,
      dataEnvio: "2025-11-05T14:20:00",
      status: "Pago",
      emailEnviado: true,
      whatsappEnviado: false,
      linkUpload: null,
    },
    {
      id: 3,
      tipo: "prestador",
      loteId: 102,
      nome: "Serviços XYZ",
      periodo: "15/10/2025 - 31/10/2025",
      valorTotal: 8500.0,
      quantidadeOS: 7,
      dataEnvio: "2025-11-01T09:15:00",
      status: "N.F. RECEBIDA",
      emailEnviado: true,
      whatsappEnviado: true,
      linkUpload: "https://api.link.dev.br/upload/xyz456",
    },
  ];

  const filteredData = historico.filter((item) => {
    const matchTipo = tipoFiltro === "todos" || item.tipo === tipoFiltro;
    const matchStatus = statusFiltro === "todos" || item.status === statusFiltro;
    const matchSearch = item.nome.toLowerCase().includes(searchTerm.toLowerCase());
    return matchTipo && matchStatus && matchSearch;
  });

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
            {filteredData.length === 0 ? (
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
                    <TableHead>Canais</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredData.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Badge variant="outline">#{item.loteId}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={item.tipo === "prestador" ? "default" : "secondary"}>
                          {item.tipo === "prestador" ? "🔧 Prestador" : "🔨 Montador"}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{item.nome}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {item.periodo}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">{item.quantidadeOS}</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold">
                          R$ {item.valorTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {new Date(item.dataEnvio).toLocaleDateString("pt-BR")}
                        <br />
                        <span className="text-xs text-muted-foreground">
                          {new Date(item.dataEnvio).toLocaleTimeString("pt-BR", {
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
                        <div className="flex gap-2">
                          {item.emailEnviado && (
                            <div className="flex items-center gap-1">
                              <Mail className="h-4 w-4 text-success" />
                              <span className="text-xs text-muted-foreground">Email</span>
                            </div>
                          )}
                          {item.whatsappEnviado && (
                            <div className="flex items-center gap-1">
                              <MessageSquare className="h-4 w-4 text-success" />
                              <span className="text-xs text-muted-foreground">WhatsApp</span>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle>Detalhes do Envio #{item.loteId}</DialogTitle>
                              <DialogDescription>
                                {item.nome} - {item.periodo}
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
                                    R$ {item.valorTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-muted-foreground">Quantidade</p>
                                  <p className="text-base font-semibold">
                                    {item.quantidadeOS} {item.tipo === "prestador" ? "OS" : "montagens"}
                                  </p>
                                </div>
                              </div>

                              {item.linkUpload && (
                                <div className="rounded-lg border border-border bg-muted/50 p-4">
                                  <p className="text-sm font-medium mb-2">🔗 Link de Upload</p>
                                  <code className="block text-xs bg-background p-2 rounded break-all">
                                    {item.linkUpload}
                                  </code>
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
                              </div>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
