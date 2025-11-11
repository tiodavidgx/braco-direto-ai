import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Mail, Upload, Send, Plus, Trash2, FileSpreadsheet, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import * as XLSX from 'xlsx';
import { prestadoresService } from "@/services/prestadores.service";
import { montadoresService } from "@/services/montadores.service";
import { Prestador } from "@/types/prestador";
import { Montador } from "@/types/montador";

// Interfaces baseadas no streamlit original
interface PrestadorEntry {
  nome_prestador: string;
  periodo: string;
  o_s: string;
  cliente: string;
  localidade: string;
  modalidade: string;
  data_execucao: string;
  valor_custo_prestador: number;
  valor_extra: number;
  motivo_extra: string;
  valor_total: number;
}

interface MontadorEntry {
  identificador_do_montador: string;
  nome_do_montador: string;
  identificador_boletim_montagem: string;
  data_da_montagem: string;
  media_de_valor_venda: number;
  nome_do_cliente: string;
  nome_produto: string;
}

export default function EnvioRelatorios() {
  // Estado principal
  const [tipoEnvio, setTipoEnvio] = useState<"prestador" | "montador">("prestador");
  const [manualEntriesPrestador, setManualEntriesPrestador] = useState<PrestadorEntry[]>([]);
  const [manualEntriesMontador, setManualEntriesMontador] = useState<MontadorEntry[]>([]);
  const [excelData, setExcelData] = useState<any[]>([]);
  const [dataParaEnvio, setDataParaEnvio] = useState<any[]>([]);
  const [sending, setSending] = useState(false);
  const [enviarWhatsApp, setEnviarWhatsApp] = useState(true);
  
  // Dados do banco
  const [prestadores, setPrestadores] = useState<Prestador[]>([]);
  const [montadores, setMontadores] = useState<Montador[]>([]);
  const [loading, setLoading] = useState(true);

  // Form Manual - Prestador
  const [formPrestador, setFormPrestador] = useState({
    nome_prestador: "",
    periodo: "",
    o_s: "",
    cliente: "",
    localidade: "",
    modalidade: "",
    data_execucao: "",
    valor: "0",
    valor_extra: "0",
    motivo_extra: "",
  });

  // Form Manual - Montador
  const [formMontador, setFormMontador] = useState({
    nome_montador: "",
    identificador: "",
    boletim: "",
    data_montagem: "",
    valor_venda: "0",
    cliente: "",
    produto: "",
  });

  // Configurações de email
  const [emailConfig, setEmailConfig] = useState({
    cc: "projetos.qualidade@novomundo.com.br",
    assunto: tipoEnvio === "prestador"
      ? "Novo Mundo Resolve | Nota Fiscal | Período: {{periodo}} | Prestador: {{nome_prestador}}"
      : "Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}",
    corpo: tipoEnvio === "prestador"
      ? `Segue a relação de boletins para emissão da nota fiscal de serviços entre **{{periodo}}**.

📎 Para anexar a Nota Fiscal, acesse o link abaixo:
{{link_upload}}

⚠️ Este link é válido por 30 dias.

Obrigado.`
      : `Olá, {{nome_montador}},

Segue em anexo o seu relatório de pagamento de montagens referente ao período de **{{periodo_relatorio}}**.

📎 **Link para upload de documentos:** {{link_upload}}

Qualquer dúvida, estamos à disposição.`,
  });

  // Carregar prestadores e montadores do banco
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [prestadoresData, montadoresData] = await Promise.all([
          prestadoresService.getAll({ limit: 1000 }),
          montadoresService.getAll({ ativo: true, limit: 1000 })
        ]);
        
        setPrestadores(prestadoresData.data || []);
        setMontadores(montadoresData.data || []);
      } catch (error) {
        console.error("Erro ao carregar dados:", error);
        toast.error("Erro ao carregar prestadores e montadores");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // PRESTADOR: Adicionar entrada manual
  const adicionarEntradaPrestador = () => {
    if (!formPrestador.nome_prestador || !formPrestador.periodo || !formPrestador.o_s || !formPrestador.data_execucao) {
      toast.error("Preencha os campos obrigatórios: Prestador, Período, O.S. e Data");
      return;
    }

    const valor = parseFloat(formPrestador.valor) || 0;
    const valorExtra = parseFloat(formPrestador.valor_extra) || 0;

    const novaEntrada: PrestadorEntry = {
      nome_prestador: formPrestador.nome_prestador,
      periodo: formPrestador.periodo,
      o_s: formPrestador.o_s,
      cliente: formPrestador.cliente,
      localidade: formPrestador.localidade,
      modalidade: formPrestador.modalidade,
      data_execucao: formPrestador.data_execucao,
      valor_custo_prestador: valor,
      valor_extra: valorExtra,
      motivo_extra: formPrestador.motivo_extra,
      valor_total: valor + valorExtra,
    };

    setManualEntriesPrestador([...manualEntriesPrestador, novaEntrada]);
    setDataParaEnvio([...manualEntriesPrestador, novaEntrada]);
    
    // Limpar form
    setFormPrestador({
      nome_prestador: formPrestador.nome_prestador, // Manter o prestador selecionado
      periodo: formPrestador.periodo, // Manter o período
      o_s: "",
      cliente: "",
      localidade: "",
      modalidade: "",
      data_execucao: "",
      valor: "0",
      valor_extra: "0",
      motivo_extra: "",
    });

    toast.success("Entrada adicionada à lista");
  };

  // MONTADOR: Adicionar entrada manual
  const adicionarEntradaMontador = () => {
    if (!formMontador.nome_montador || !formMontador.boletim || !formMontador.data_montagem || !formMontador.valor_venda) {
      toast.error("Preencha os campos obrigatórios: Montador, Boletim, Data e Valor");
      return;
    }

    const montadorSelecionado = montadores.find(m => m.nome === formMontador.nome_montador);
    if (!montadorSelecionado) {
      toast.error("Montador não encontrado");
      return;
    }

    const novaEntrada: MontadorEntry = {
      identificador_do_montador: montadorSelecionado.identificador,
      nome_do_montador: formMontador.nome_montador,
      identificador_boletim_montagem: formMontador.boletim,
      data_da_montagem: formMontador.data_montagem,
      media_de_valor_venda: parseFloat(formMontador.valor_venda) || 0,
      nome_do_cliente: formMontador.cliente,
      nome_produto: formMontador.produto,
    };

    setManualEntriesMontador([...manualEntriesMontador, novaEntrada]);
    setDataParaEnvio([...manualEntriesMontador, novaEntrada]);

    // Limpar form (mantendo montador e data)
    setFormMontador({
      nome_montador: formMontador.nome_montador,
      identificador: formMontador.identificador,
      boletim: "",
      data_montagem: formMontador.data_montagem,
      valor_venda: "0",
      cliente: "",
      produto: "",
    });

    toast.success("Entrada adicionada à lista");
  };

  // Upload de Excel
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

        // Normalizar nomes das colunas (remover espaços, acentos, caracteres especiais)
        const normalizedData = jsonData.map((row: any) => {
          const normalized: any = {};
          Object.keys(row).forEach(key => {
            const normalizedKey = key
              .toLowerCase()
              .normalize("NFD")
              .replace(/[\u0300-\u036f]/g, "")
              .replace(/\s+/g, '_')
              .replace(/[^\w]/g, '_');
            normalized[normalizedKey] = row[key];
          });
          return normalized;
        });

        // Validar colunas obrigatórias
        if (tipoEnvio === "prestador") {
          const required = ["nome_prestador", "periodo", "data_execucao", "o_s"];
          const hasAllColumns = required.every(col =>
            normalizedData.length > 0 && normalizedData[0].hasOwnProperty(col)
          );

          if (!hasAllColumns) {
            toast.error(`Excel precisa das colunas: ${required.join(", ")}`);
            return;
          }

          // Converter valores numéricos
          normalizedData.forEach(row => {
            row.valor_custo_prestador = parseFloat(row.valor_custo_prestador || 0);
            row.valor_extra = parseFloat(row.valor_extra || 0);
            row.valor_total = row.valor_custo_prestador + row.valor_extra;
          });
        } else {
          const required = ["identificador_do_montador", "identificador_boletim_montagem", "data_da_montagem", "media_de_valor_venda", "nome_produto"];
          const hasAllColumns = required.every(col =>
            normalizedData.length > 0 && normalizedData[0].hasOwnProperty(col)
          );

          if (!hasAllColumns) {
            toast.error(`Excel precisa das colunas: ${required.join(", ")}`);
            return;
          }

          // Converter valores numéricos
          normalizedData.forEach(row => {
            row.media_de_valor_venda = parseFloat(row.media_de_valor_venda || 0);
          });
        }

        setExcelData(normalizedData);
        setDataParaEnvio(normalizedData);
        toast.success(`${normalizedData.length} linhas carregadas com sucesso!`);
      } catch (error) {
        toast.error("Erro ao processar planilha");
        console.error(error);
      }
    };

    reader.readAsArrayBuffer(file);
  };

  // Enviar relatórios
  const enviarRelatorios = async () => {
    if (dataParaEnvio.length === 0) {
      toast.error("Nenhum dado para enviar");
      return;
    }

    setSending(true);
    toast.info("Enviando relatórios...");

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/relatorios/enviar-lote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipo: tipoEnvio,
          dados: dataParaEnvio,
          emailConfig,
          enviarWhatsApp,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`${result.sucesso} relatórios enviados com sucesso!`);
        
        if (result.warning) {
          toast.warning(result.warning);
        }

        // Limpar dados
        setManualEntriesPrestador([]);
        setManualEntriesMontador([]);
        setExcelData([]);
        setDataParaEnvio([]);
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao enviar relatórios");
      }
    } catch (error) {
      toast.error("Erro ao enviar relatórios");
      console.error(error);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Envio de Relatórios</h1>
          <p className="text-muted-foreground">
            Enviar relatórios de fechamento para prestadores e montadores
          </p>
        </div>

        <Select value={tipoEnvio} onValueChange={(v: "prestador" | "montador") => {
          setTipoEnvio(v);
          setManualEntriesPrestador([]);
          setManualEntriesMontador([]);
          setExcelData([]);
          setDataParaEnvio([]);
        }}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="prestador">🏢 Prestadores</SelectItem>
            <SelectItem value="montador">👷 Montadores</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Tabs defaultValue="manual" className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="manual">Lançamento Manual</TabsTrigger>
          <TabsTrigger value="excel">Importar Excel</TabsTrigger>
        </TabsList>

        <TabsContent value="manual" className="space-y-6">
          {tipoEnvio === "prestador" ? (
            <Card>
              <CardHeader>
                <CardTitle>Adicionar Boletim Manualmente</CardTitle>
                <CardDescription>Preencha os dados do serviço prestado</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Prestador *</Label>
                    <Select
                      value={formPrestador.nome_prestador}
                      onValueChange={(v) => setFormPrestador({ ...formPrestador, nome_prestador: v })}
                      disabled={loading}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={loading ? "Carregando..." : "Selecione..."} />
                      </SelectTrigger>
                      <SelectContent>
                        {prestadores.map((p) => (
                          <SelectItem key={p.id} value={p.nome}>{p.nome}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Período *</Label>
                    <Input
                      placeholder="01/11 - 07/11"
                      value={formPrestador.periodo}
                      onChange={(e) => setFormPrestador({ ...formPrestador, periodo: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>O.S *</Label>
                    <Input
                      placeholder="OS001"
                      value={formPrestador.o_s}
                      onChange={(e) => setFormPrestador({ ...formPrestador, o_s: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Cliente</Label>
                    <Input
                      placeholder="Nome do cliente"
                      value={formPrestador.cliente}
                      onChange={(e) => setFormPrestador({ ...formPrestador, cliente: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Data de Execução *</Label>
                    <Input
                      type="date"
                      value={formPrestador.data_execucao}
                      onChange={(e) => setFormPrestador({ ...formPrestador, data_execucao: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Localidade</Label>
                    <Input
                      placeholder="São Paulo"
                      value={formPrestador.localidade}
                      onChange={(e) => setFormPrestador({ ...formPrestador, localidade: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Modalidade</Label>
                    <Input
                      placeholder="Instalação"
                      value={formPrestador.modalidade}
                      onChange={(e) => setFormPrestador({ ...formPrestador, modalidade: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Valor (R$)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formPrestador.valor}
                      onChange={(e) => setFormPrestador({ ...formPrestador, valor: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Valor Extra (R$)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formPrestador.valor_extra}
                      onChange={(e) => setFormPrestador({ ...formPrestador, valor_extra: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Valor Total</Label>
                    <div className="flex h-10 items-center rounded-md border bg-muted px-3 text-sm font-bold">
                      R$ {(parseFloat(formPrestador.valor) + parseFloat(formPrestador.valor_extra)).toFixed(2)}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Motivo Valor Extra</Label>
                  <Input
                    placeholder="Hora extra, deslocamento..."
                    value={formPrestador.motivo_extra}
                    onChange={(e) => setFormPrestador({ ...formPrestador, motivo_extra: e.target.value })}
                  />
                </div>

                <Button onClick={adicionarEntradaPrestador} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  Adicionar à Lista
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Adicionar Montagem Manualmente</CardTitle>
                <CardDescription>Preencha os dados da montagem realizada</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Montador *</Label>
                    <Select
                      value={formMontador.nome_montador}
                      onValueChange={(v) => {
                        const montador = montadores.find(m => m.nome === v);
                        setFormMontador({
                          ...formMontador,
                          nome_montador: v,
                          identificador: montador?.identificador || ""
                        });
                      }}
                      disabled={loading}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={loading ? "Carregando..." : "Selecione..."} />
                      </SelectTrigger>
                      <SelectContent>
                        {montadores.map((m) => (
                          <SelectItem key={m.id} value={m.nome}>{m.nome}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Data da Montagem *</Label>
                    <Input
                      type="date"
                      value={formMontador.data_montagem}
                      onChange={(e) => setFormMontador({ ...formMontador, data_montagem: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Boletim Montagem *</Label>
                    <Input
                      placeholder="BOL001"
                      value={formMontador.boletim}
                      onChange={(e) => setFormMontador({ ...formMontador, boletim: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Média de Valor Venda (R$) *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formMontador.valor_venda}
                      onChange={(e) => setFormMontador({ ...formMontador, valor_venda: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Cliente</Label>
                    <Input
                      placeholder="Nome do cliente"
                      value={formMontador.cliente}
                      onChange={(e) => setFormMontador({ ...formMontador, cliente: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Nome do Produto *</Label>
                    <Input
                      placeholder="Cama Box, Guarda-Roupa..."
                      value={formMontador.produto}
                      onChange={(e) => setFormMontador({ ...formMontador, produto: e.target.value })}
                    />
                  </div>
                </div>

                <Button onClick={adicionarEntradaMontador} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  Adicionar à Lista
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Preview da lista manual */}
          {((tipoEnvio === "prestador" && manualEntriesPrestador.length > 0) ||
            (tipoEnvio === "montador" && manualEntriesMontador.length > 0)) && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Lista para Envio</CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setManualEntriesPrestador([]);
                      setManualEntriesMontador([]);
                      setDataParaEnvio([]);
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Limpar Lista
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {tipoEnvio === "prestador" ? (
                          <>
                            <TableHead>Prestador</TableHead>
                            <TableHead>Período</TableHead>
                            <TableHead>O.S.</TableHead>
                            <TableHead>Cliente</TableHead>
                            <TableHead>Data</TableHead>
                            <TableHead className="text-right">Valor Total</TableHead>
                          </>
                        ) : (
                          <>
                            <TableHead>Montador</TableHead>
                            <TableHead>Boletim</TableHead>
                            <TableHead>Produto</TableHead>
                            <TableHead>Cliente</TableHead>
                            <TableHead>Data</TableHead>
                            <TableHead className="text-right">Valor</TableHead>
                          </>
                        )}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tipoEnvio === "prestador"
                        ? manualEntriesPrestador.map((entry, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{entry.nome_prestador}</TableCell>
                              <TableCell>{entry.periodo}</TableCell>
                              <TableCell><Badge variant="outline">{entry.o_s}</Badge></TableCell>
                              <TableCell>{entry.cliente || "-"}</TableCell>
                              <TableCell>{entry.data_execucao}</TableCell>
                              <TableCell className="text-right font-medium">
                                R$ {entry.valor_total.toFixed(2)}
                              </TableCell>
                            </TableRow>
                          ))
                        : manualEntriesMontador.map((entry, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{entry.nome_do_montador}</TableCell>
                              <TableCell><Badge variant="outline">{entry.identificador_boletim_montagem}</Badge></TableCell>
                              <TableCell>{entry.nome_produto}</TableCell>
                              <TableCell>{entry.nome_do_cliente || "-"}</TableCell>
                              <TableCell>{entry.data_da_montagem}</TableCell>
                              <TableCell className="text-right font-medium">
                                R$ {entry.media_de_valor_venda.toFixed(2)}
                              </TableCell>
                            </TableRow>
                          ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="excel" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5" />
                Importar Planilha Excel
              </CardTitle>
              <CardDescription>
                {tipoEnvio === "prestador"
                  ? "Colunas obrigatórias: nome_prestador, periodo, data_execucao, o_s"
                  : "Colunas obrigatórias: identificador_do_montador, identificador_boletim_montagem, data_da_montagem, media_de_valor_venda, nome_produto"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted/50 transition-colors">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
                    <p className="mb-2 text-sm text-muted-foreground">
                      <span className="font-semibold">Clique para fazer upload</span> ou arraste e solte
                    </p>
                    <p className="text-xs text-muted-foreground">Arquivos Excel (.xlsx)</p>
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept=".xlsx,.xls"
                    onChange={handleFileUpload}
                  />
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Preview do Excel */}
          {excelData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Preview dos Dados Importados</CardTitle>
                <CardDescription>{excelData.length} linhas carregadas</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border max-h-96 overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {tipoEnvio === "prestador" ? (
                          <>
                            <TableHead>Prestador</TableHead>
                            <TableHead>Período</TableHead>
                            <TableHead>O.S.</TableHead>
                            <TableHead>Cliente</TableHead>
                            <TableHead>Data</TableHead>
                            <TableHead className="text-right">Valor Total</TableHead>
                          </>
                        ) : (
                          <>
                            <TableHead>Montador</TableHead>
                            <TableHead>Boletim</TableHead>
                            <TableHead>Produto</TableHead>
                            <TableHead>Cliente</TableHead>
                            <TableHead>Data</TableHead>
                            <TableHead className="text-right">Valor</TableHead>
                          </>
                        )}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {excelData.map((row, idx) => (
                        <TableRow key={idx}>
                          {tipoEnvio === "prestador" ? (
                            <>
                              <TableCell>{row.nome_prestador}</TableCell>
                              <TableCell>{row.periodo}</TableCell>
                              <TableCell><Badge variant="outline">{row.o_s}</Badge></TableCell>
                              <TableCell>{row.cliente || "-"}</TableCell>
                              <TableCell>{row.data_execucao}</TableCell>
                              <TableCell className="text-right font-medium">
                                R$ {row.valor_total?.toFixed(2) || "0.00"}
                              </TableCell>
                            </>
                          ) : (
                            <>
                              <TableCell>{row.identificador_do_montador}</TableCell>
                              <TableCell><Badge variant="outline">{row.identificador_boletim_montagem}</Badge></TableCell>
                              <TableCell>{row.nome_produto}</TableCell>
                              <TableCell>{row.nome_do_cliente || "-"}</TableCell>
                              <TableCell>{row.data_da_montagem}</TableCell>
                              <TableCell className="text-right font-medium">
                                R$ {row.media_de_valor_venda?.toFixed(2) || "0.00"}
                              </TableCell>
                            </>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Configurações de Envio */}
      {dataParaEnvio.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Configurações de Email
            </CardTitle>
            <CardDescription>
              Configure o assunto e corpo do email. Use variáveis como {`{{periodo}}`}, {`{{nome_prestador}}`}, {`{{valor_total}}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>CC (com cópia)</Label>
              <Input
                placeholder="email1@empresa.com, email2@empresa.com"
                value={emailConfig.cc}
                onChange={(e) => setEmailConfig({ ...emailConfig, cc: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Assunto</Label>
              <Input
                value={emailConfig.assunto}
                onChange={(e) => setEmailConfig({ ...emailConfig, assunto: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Corpo do Email</Label>
              <Textarea
                rows={8}
                value={emailConfig.corpo}
                onChange={(e) => setEmailConfig({ ...emailConfig, corpo: e.target.value })}
              />
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="whatsapp"
                checked={enviarWhatsApp}
                onCheckedChange={(checked) => setEnviarWhatsApp(checked as boolean)}
              />
              <label
                htmlFor="whatsapp"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
              >
                <MessageSquare className="h-4 w-4" />
                Enviar notificação por WhatsApp também
              </label>
            </div>

            <Button
              onClick={enviarRelatorios}
              disabled={sending}
              size="lg"
              className="w-full"
            >
              <Send className="mr-2 h-5 w-5" />
              {sending ? "Enviando..." : `Enviar ${dataParaEnvio.length} Relatório(s)`}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
