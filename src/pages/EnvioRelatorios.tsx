import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Mail, Upload, Send, Plus, Trash2, Edit2, MessageSquare, History } from "lucide-react";
import { toast } from "sonner";
import * as XLSX from 'xlsx';

interface ManualEntry {
  os_numero?: string;
  boletim?: string;
  cliente: string;
  localidade?: string;
  modalidade?: string;
  produto?: string;
  data_execucao: string;
  valor: number;
  valor_extra?: number;
  comissao?: number;
}

export default function EnvioRelatorios() {
  const [tipoEnvio, setTipoEnvio] = useState<"prestador" | "montador">("prestador");
  const [aba, setAba] = useState<"manual" | "excel" | "historico">("manual");
  const [manualEntries, setManualEntries] = useState<ManualEntry[]>([]);
  const [excelData, setExcelData] = useState<any[]>([]);
  const [sending, setSending] = useState(false);
  const [enviarWhatsApp, setEnviarWhatsApp] = useState(true);

  // Configurações de email
  const [emailConfig, setEmailConfig] = useState({
    cc: "projetos.qualidade@novomundo.com.br",
    assunto: "Relatório de Fechamento - {{periodo}}",
    corpo: `Segue em anexo o relatório de fechamento do período {{periodo}}.

📎 Link para envio de Nota Fiscal: {{link_upload}}

Atenciosamente,
Novo Mundo`,
  });

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    toast.info("Processando planilha...");

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet);

        // Normalizar nomes das colunas
        const normalizedData = jsonData.map((row: any) => {
          const normalized: any = {};
          Object.keys(row).forEach(key => {
            const normalizedKey = key
              .toLowerCase()
              .replace(/\s+/g, '_')
              .replace(/[^\w]/g, '');
            normalized[normalizedKey] = row[key];
          });
          
          // Verificar status (se já foi enviado antes)
          normalized.status = "Pendente"; // TODO: verificar no backend
          
          return normalized;
        });

        setExcelData(normalizedData);
        toast.success(`${normalizedData.length} linhas carregadas com sucesso!`);
      } catch (error) {
        toast.error("Erro ao processar planilha");
        console.error(error);
      }
    };

    reader.readAsArrayBuffer(file);
  };

  const adicionarEntradaManual = () => {
    const novaEntrada: ManualEntry = {
      os_numero: "",
      cliente: "",
      data_execucao: new Date().toISOString().split('T')[0],
      valor: 0,
    };
    setManualEntries([...manualEntries, novaEntrada]);
  };

  const removerEntrada = (index: number) => {
    const novasEntradas = manualEntries.filter((_, i) => i !== index);
    setManualEntries(novasEntradas);
  };

  const atualizarEntrada = (index: number, campo: string, valor: any) => {
    const novasEntradas = [...manualEntries];
    novasEntradas[index] = {
      ...novasEntradas[index],
      [campo]: valor,
    };
    setManualEntries(novasEntradas);
  };

  const handleEnviarRelatorios = async () => {
    setSending(true);
    try {
      const dadosParaEnviar = aba === "manual" ? manualEntries : excelData.filter(d => d.status === "Pendente");
      
      if (dadosParaEnviar.length === 0) {
        toast.warning("Nenhum item para enviar");
        return;
      }

      // Chamar API para gerar PDFs e enviar emails
      const response = await fetch(`/api/v1/relatorios/enviar-lote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipo: tipoEnvio,
          dados: dadosParaEnviar,
          emailConfig,
          enviarWhatsApp,
        }),
      });

      if (response.ok) {
        toast.success(`${dadosParaEnviar.length} relatório(s) enviado(s) com sucesso!`);
        setManualEntries([]);
        setExcelData([]);
      } else {
        toast.error("Erro ao enviar relatórios");
      }
    } catch (error) {
      toast.error("Erro ao processar envio");
    } finally {
      setSending(false);
    }
  };

  const valorTotal = aba === "manual" 
    ? manualEntries.reduce((sum, e) => sum + (e.valor + (e.valor_extra || 0)), 0)
    : excelData.filter(d => d.status === "Pendente").reduce((sum, e) => sum + e.valor, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Envio de Relatórios</h1>
          <p className="text-muted-foreground">
            Importar planilha ou lançar manualmente para envio de relatórios
          </p>
        </div>
        <Select value={tipoEnvio} onValueChange={(v: any) => setTipoEnvio(v)}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="prestador">🔧 Prestadores</SelectItem>
            <SelectItem value="montador">🔨 Montadores</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Tabs value={aba} onValueChange={(v: any) => setAba(v)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="manual" className="gap-2">
            <Edit2 className="h-4 w-4" />
            Lançamento Manual
          </TabsTrigger>
          <TabsTrigger value="excel" className="gap-2">
            <Upload className="h-4 w-4" />
            Importar Excel
          </TabsTrigger>
          <TabsTrigger value="historico" className="gap-2">
            <History className="h-4 w-4" />
            Histórico
          </TabsTrigger>
        </TabsList>

        {/* LANÇAMENTO MANUAL */}
        <TabsContent value="manual" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Adicionar {tipoEnvio === "prestador" ? "OS" : "Montagens"}</CardTitle>
                <Button onClick={adicionarEntradaManual} variant="outline" className="gap-2">
                  <Plus className="h-4 w-4" />
                  Adicionar Linha
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {manualEntries.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground">
                  <p>Nenhum item adicionado ainda</p>
                  <p className="text-sm">Clique em "Adicionar Linha" para começar</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{tipoEnvio === "prestador" ? "OS" : "Boletim"}</TableHead>
                        <TableHead>Cliente</TableHead>
                        {tipoEnvio === "prestador" && <TableHead>Localidade</TableHead>}
                        {tipoEnvio === "prestador" && <TableHead>Modalidade</TableHead>}
                        {tipoEnvio === "montador" && <TableHead>Produto</TableHead>}
                        <TableHead>Data</TableHead>
                        <TableHead>Valor (R$)</TableHead>
                        {tipoEnvio === "prestador" && <TableHead>Extra (R$)</TableHead>}
                        <TableHead>Total (R$)</TableHead>
                        <TableHead className="w-16"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {manualEntries.map((entry, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Input
                              value={tipoEnvio === "prestador" ? entry.os_numero : entry.boletim}
                              onChange={(e) => atualizarEntrada(index, tipoEnvio === "prestador" ? "os_numero" : "boletim", e.target.value)}
                              placeholder={tipoEnvio === "prestador" ? "OS001" : "BOL001"}
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              value={entry.cliente}
                              onChange={(e) => atualizarEntrada(index, "cliente", e.target.value)}
                              placeholder="Nome do cliente"
                            />
                          </TableCell>
                          {tipoEnvio === "prestador" && (
                            <TableCell>
                              <Input
                                value={entry.localidade}
                                onChange={(e) => atualizarEntrada(index, "localidade", e.target.value)}
                                placeholder="Cidade"
                              />
                            </TableCell>
                          )}
                          {tipoEnvio === "prestador" && (
                            <TableCell>
                              <Input
                                value={entry.modalidade}
                                onChange={(e) => atualizarEntrada(index, "modalidade", e.target.value)}
                                placeholder="Instalação"
                              />
                            </TableCell>
                          )}
                          {tipoEnvio === "montador" && (
                            <TableCell>
                              <Input
                                value={entry.produto}
                                onChange={(e) => atualizarEntrada(index, "produto", e.target.value)}
                                placeholder="Produto"
                              />
                            </TableCell>
                          )}
                          <TableCell>
                            <Input
                              type="date"
                              value={entry.data_execucao}
                              onChange={(e) => atualizarEntrada(index, "data_execucao", e.target.value)}
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              type="number"
                              step="0.01"
                              value={entry.valor}
                              onChange={(e) => atualizarEntrada(index, "valor", parseFloat(e.target.value) || 0)}
                            />
                          </TableCell>
                          {tipoEnvio === "prestador" && (
                            <TableCell>
                              <Input
                                type="number"
                                step="0.01"
                                value={entry.valor_extra || 0}
                                onChange={(e) => atualizarEntrada(index, "valor_extra", parseFloat(e.target.value) || 0)}
                              />
                            </TableCell>
                          )}
                          <TableCell>
                            <span className="font-semibold">
                              {(entry.valor + (entry.valor_extra || 0)).toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removerEntrada(index)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {manualEntries.length > 0 && (
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Valor Total</p>
                    <p className="text-3xl font-bold text-primary">
                      R$ {valorTotal.toFixed(2)}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {manualEntries.length} {tipoEnvio === "prestador" ? "OS" : "montagens"}
                    </p>
                  </div>
                  <Button onClick={() => setManualEntries([])} variant="outline">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Limpar Tudo
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* IMPORTAR EXCEL */}
        <TabsContent value="excel" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Importar Planilha Excel</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-center border-2 border-dashed border-border rounded-lg p-12">
                  <Label htmlFor="file-upload" className="cursor-pointer">
                    <div className="text-center">
                      <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
                      <p className="mt-4 text-sm font-medium">Clique para selecionar arquivo</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Formatos aceitos: .xlsx, .xls
                      </p>
                    </div>
                    <Input
                      id="file-upload"
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleFileUpload}
                      className="sr-only"
                    />
                  </Label>
                </div>

                {excelData.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-4">Pré-visualização</h3>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>OS/Boletim</TableHead>
                            <TableHead>Cliente</TableHead>
                            <TableHead>Valor</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {excelData.map((row, i) => (
                            <TableRow key={i}>
                              <TableCell>{row.os_numero}</TableCell>
                              <TableCell>{row.cliente}</TableCell>
                              <TableCell>R$ {row.valor.toFixed(2)}</TableCell>
                              <TableCell>
                                <Badge variant={row.status === "Pendente" ? "default" : "secondary"}>
                                  {row.status}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* HISTÓRICO */}
        <TabsContent value="historico" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Histórico de Envios</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Mock de histórico */}
              <div className="space-y-4">
                {[
                  {
                    id: 1,
                    nome: "Prestadora ABC",
                    periodo: "01/11 - 07/11",
                    valor: 15480.5,
                    data: "08/11/2025",
                    status: "Aguardando NF",
                  },
                  {
                    id: 2,
                    nome: "João Silva",
                    periodo: "Novembro/2025",
                    valor: 3250.0,
                    data: "05/11/2025",
                    status: "Pago",
                  },
                ].map((item) => (
                  <div key={item.id} className="rounded-lg border border-border p-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="font-semibold">{item.nome}</p>
                        <p className="text-sm text-muted-foreground">Período: {item.periodo}</p>
                        <p className="text-sm text-muted-foreground">Enviado em: {item.data}</p>
                      </div>
                      <div className="text-right space-y-2">
                        <p className="text-lg font-bold">R$ {item.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
                        <Badge variant={item.status === "Pago" ? "default" : "secondary"}>
                          {item.status}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* CONFIGURAÇÕES E ENVIO */}
      {(aba === "manual" && manualEntries.length > 0) || (aba === "excel" && excelData.length > 0) ? (
        <Card>
          <CardHeader>
            <CardTitle>⚙️ Configurações de Envio</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="cc">CC (com vírgula)</Label>
              <Input
                id="cc"
                value={emailConfig.cc}
                onChange={(e) => setEmailConfig({ ...emailConfig, cc: e.target.value })}
                placeholder="email1@empresa.com, email2@empresa.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="assunto">Assunto do Email</Label>
              <Input
                id="assunto"
                value={emailConfig.assunto}
                onChange={(e) => setEmailConfig({ ...emailConfig, assunto: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Variáveis: {`{{periodo}}, {{nome_prestador}}, {{valor_total}}`}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="corpo">Corpo do Email</Label>
              <Textarea
                id="corpo"
                value={emailConfig.corpo}
                onChange={(e) => setEmailConfig({ ...emailConfig, corpo: e.target.value })}
                rows={6}
              />
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="whatsapp"
                checked={enviarWhatsApp}
                onCheckedChange={(checked) => setEnviarWhatsApp(checked as boolean)}
              />
              <Label htmlFor="whatsapp" className="flex items-center gap-2 cursor-pointer">
                <MessageSquare className="h-4 w-4" />
                Enviar notificação por WhatsApp também
              </Label>
            </div>

            <div className="pt-4">
              <Button onClick={handleEnviarRelatorios} disabled={sending} className="w-full gap-2" size="lg">
                {sending ? (
                  <>Enviando...</>
                ) : (
                  <>
                    <Send className="h-5 w-5" />
                    Enviar {manualEntries.length || excelData.filter(d => d.status === "Pendente").length} Relatório(s)
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
