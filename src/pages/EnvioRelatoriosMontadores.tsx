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
import { montadoresService } from "@/services/montadores.service";
import { emailConfigService } from "@/services/email-config.service";
import { Montador } from "@/types/montador";
import { apiClient } from "@/services/api";

interface MontadorEntry {
  identificador_do_montador: string;
  nome_do_montador: string;
  identificador_boletim_montagem: string;
  data_da_montagem: string;
  media_de_valor_venda: number;
  nome_do_cliente: string;
  nome_produto: string;
  comissao: number;
  adicional?: number;
  motivo_valor_extra?: string;
  tipo_servico: "MONTAGEM" | "ASSISTENCIA_TECNICA" | "DESMONTAGEM";
}

export default function EnvioRelatoriosMontadores() {
  // Estado principal
  const [manualEntries, setManualEntries] = useState<MontadorEntry[]>([]);
  const [excelData, setExcelData] = useState<any[]>([]);
  const [dataParaEnvio, setDataParaEnvio] = useState<any[]>([]);
  const [sending, setSending] = useState(false);
  const [enviarWhatsApp, setEnviarWhatsApp] = useState(true);
  
  // Status preview
  const [statusPreview, setStatusPreview] = useState<any[]>([]);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  
  // Dados do banco
  const [montadores, setMontadores] = useState<Montador[]>([]);
  const [loading, setLoading] = useState(true);

  // Form Manual
  const [formMontador, setFormMontador] = useState({
    nome_montador: "",
    identificador: "",
    boletim: "",
    data_montagem: "",
    valor_venda: "0",
    cliente: "",
    produto: "",
    valor_extra: "0",
    motivo_valor_extra: "",
    tipo_servico: "MONTAGEM" as "MONTAGEM" | "ASSISTENCIA_TECNICA" | "DESMONTAGEM",
  });

  // Configurações de email
  const [emailConfig, setEmailConfig] = useState({
    cc: "projetos.qualidade@novomundo.com.br",
    assunto: "Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}",
    corpo: `Olá, {{nome_montador}},

Segue em anexo o seu relatório de pagamento de montagens referente ao período de **{{periodo_relatorio}}**.

📎 **Link para upload de documentos:** {{link_upload}}

Qualquer dúvida, estamos à disposição.`,
  });

  // Carregar montadores do banco
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const montadoresData = await montadoresService.getAll({ limit: 1000 });
        setMontadores(montadoresData.data || []);
      } catch (error) {
        console.error("Erro ao carregar montadores:", error);
        toast.error("Erro ao carregar montadores");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Carregar configuração de email salva
  useEffect(() => {
    const loadEmailConfig = async () => {
      try {
        const config = await emailConfigService.getConfig("montador");
        setEmailConfig({
          cc: config.cc || "projetos.qualidade@novomundo.com.br",
          assunto: config.assunto,
          corpo: config.corpo
        });
      } catch (error) {
        console.error("Erro ao carregar configuração de email:", error);
        // Manter config padrão se der erro
      }
    };

    loadEmailConfig();
  }, []);

  // Verificar status quando dados mudarem
  useEffect(() => {
    const verificarStatus = async () => {
      if (dataParaEnvio.length === 0) {
        setStatusPreview([]);
        return;
      }

      setLoadingPreview(true);
      try {
        // Coletar boletins
        const boletins: string[] = dataParaEnvio
          .map(item => item.identificador_boletim_montagem)
          .filter(Boolean);

        if (boletins.length === 0) {
          setStatusPreview([]);
          return;
        }

        // Verificar blacklist
        let blacklisted: string[] = [];
        try {
          blacklisted = await apiClient.post<string[]>("/blacklist/boletins/check", { numbers: boletins });
        } catch (e) {
          console.error("Erro ao verificar blacklist:", e);
        }

        // Verificar boletins já enviados
        let alreadySent: string[] = [];
        try {
          alreadySent = await apiClient.post<string[]>("/relatorios/verificar-boletins-enviados", { boletins });
        } catch (e) {
          console.error("Erro ao verificar boletins enviados:", e);
        }

        // Criar preview de status
        const preview = boletins.map(boletim => {
          if (blacklisted.includes(boletim)) {
            return { number: boletim, status: "Na blacklist", color: "red" };
          }
          if (alreadySent.includes(boletim)) {
            return { number: boletim, status: "Já enviado", color: "orange" };
          }
          return { number: boletim, status: "Pendente", color: "green" };
        });

        setStatusPreview(preview);
      } catch (error) {
        console.error("Erro ao verificar status:", error);
      } finally {
        setLoadingPreview(false);
      }
    };

    verificarStatus();
  }, [dataParaEnvio]);

  // Auto preencher com dados de teste
  const autoPreencherMontador = () => {
    const hoje = new Date().toISOString().split('T')[0];
    const boletimNumber = Math.floor(Math.random() * 9000) + 1000; // Gera número entre 1000-9999
    
    // Procurar montador "david"
    const montadorDavid = montadores.find(m => m.nome.toLowerCase().includes("david"));
    
    setFormMontador({
      nome_montador: montadorDavid ? montadorDavid.nome : (montadores.length > 0 ? montadores[0].nome : ""),
      identificador: montadorDavid ? montadorDavid.identificador : (montadores.length > 0 ? montadores[0].identificador : ""),
      boletim: `H${boletimNumber}`,
      data_montagem: hoje,
      valor_venda: "150.00",
      cliente: "Cliente Teste",
      produto: "Produto Teste",
      valor_extra: "0",
      motivo_valor_extra: "",
      tipo_servico: "MONTAGEM",
    });
    
    toast.success("Formulário preenchido automaticamente!");
  };

  // Adicionar entrada manual
  const adicionarManual = () => {
    if (!formMontador.nome_montador || !formMontador.identificador || !formMontador.boletim) {
      toast.error("Preencha os campos obrigatórios: Montador, Identificador e Boletim");
      return;
    }

    const montador = montadores.find(m => m.nome === formMontador.nome_montador);
    if (!montador) {
      toast.error("Montador não encontrado no banco de dados");
      return;
    }

    const valorVenda = parseFloat(formMontador.valor_venda) || 0;
    const valorExtra = parseFloat(formMontador.valor_extra) || 0;
    
    // Selecionar percentual correto baseado no tipo de serviço
    let percentual = 0.05; // default
    if (formMontador.tipo_servico === "MONTAGEM") {
      percentual = montador.percentual_montagem || 0.05;
    } else if (formMontador.tipo_servico === "ASSISTENCIA_TECNICA") {
      percentual = montador.percentual_assistencia || 0.05;
    } else if (formMontador.tipo_servico === "DESMONTAGEM") {
      percentual = montador.percentual_desmontagem || 0.05;
    }
    
    const comissao = valorVenda * percentual;

    console.log("🔍 DEBUG - Criando entry:", {
      tipo_servico: formMontador.tipo_servico,
      percentual: percentual,
      adicional: valorExtra,
      motivo_valor_extra: formMontador.motivo_valor_extra,
      formMontador: formMontador
    });

    const entry: MontadorEntry = {
      identificador_do_montador: formMontador.identificador,
      nome_do_montador: formMontador.nome_montador,
      identificador_boletim_montagem: formMontador.boletim,
      data_da_montagem: formMontador.data_montagem,
      media_de_valor_venda: valorVenda,
      nome_do_cliente: formMontador.cliente || "-",
      nome_produto: formMontador.produto || "-",
      comissao: comissao,
      adicional: valorExtra,
      motivo_valor_extra: formMontador.motivo_valor_extra || undefined,
      tipo_servico: formMontador.tipo_servico,
    };

    console.log("🔍 DEBUG - Entry criado:", entry);

    setManualEntries([...manualEntries, entry]);
    setDataParaEnvio([...manualEntries, entry]);
    
    // Limpar form
    setFormMontador({
      nome_montador: "",
      identificador: "",
      boletim: "",
      data_montagem: "",
      valor_venda: "0",
      cliente: "",
      produto: "",
      valor_extra: "0",
      motivo_valor_extra: "",
      tipo_servico: "MONTAGEM",
    });

    toast.success("Boletim adicionado à lista!");
  };

  // Upload Excel
  const handleExcelUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const bstr = evt.target?.result;
        const wb = XLSX.read(bstr, { type: 'binary' });
        const wsname = wb.SheetNames[0];
        const ws = wb.Sheets[wsname];
        const data = XLSX.utils.sheet_to_json(ws);

        // Normalizar colunas
        const normalizedData = data.map((row: any) => {
          const normalized: any = {};
          Object.keys(row).forEach(key => {
            const normalizedKey = key.trim().toLowerCase().replace(/\s+/g, '_');
            normalized[normalizedKey] = row[key];
          });
          return normalized;
        });

        // Validar colunas obrigatórias
        const requiredColumns = [
          'identificador_do_montador',
          'identificador_boletim_montagem',
          'data_da_montagem',
          'media_de_valor_venda',
          'nome_produto',
          'tipo_servico'
        ];

        const firstRow = normalizedData[0] || {};
        const missingColumns = requiredColumns.filter(col => !(col in firstRow));

        if (missingColumns.length > 0) {
          toast.error(`Colunas obrigatórias faltando: ${missingColumns.join(', ')}`);
          return;
        }

        // Enriquecer dados com informações do montador
        const enrichedData = normalizedData.map((row: any) => {
          const montador = montadores.find(m => m.identificador === row.identificador_do_montador);
          const valorVenda = parseFloat(row.media_de_valor_venda) || 0;
          const valorExtra = parseFloat(row.adicional || row.valor_extra || 0);
          
          // Determinar tipo de serviço (obrigatório)
          let tipoServico: "MONTAGEM" | "ASSISTENCIA_TECNICA" | "DESMONTAGEM" = "MONTAGEM";
          const tipoRaw = (row.tipo_servico || row.tipo || "").toUpperCase();
          if (tipoRaw.includes("ASSIST") || tipoRaw.includes("TECNICA")) {
            tipoServico = "ASSISTENCIA_TECNICA";
          } else if (tipoRaw.includes("DESMONT")) {
            tipoServico = "DESMONTAGEM";
          } else if (tipoRaw.includes("MONTAGEM") || tipoRaw === "MONTAGEM") {
            tipoServico = "MONTAGEM";
          }
          
          // Calcular comissão baseada no tipo de serviço
          let percentual = 0.05;
          if (montador) {
            if (tipoServico === "MONTAGEM") {
              percentual = montador.percentual_montagem || 0.05;
            } else if (tipoServico === "ASSISTENCIA_TECNICA") {
              percentual = montador.percentual_assistencia || 0.05;
            } else if (tipoServico === "DESMONTAGEM") {
              percentual = montador.percentual_desmontagem || 0.05;
            }
          }
          
          return {
            ...row,
            nome_do_montador: montador?.nome || row.nome_do_montador || "Desconhecido",
            identificador_boletim_montagem: String(row.identificador_boletim_montagem || ''),
            data_da_montagem: row.data_da_montagem,
            media_de_valor_venda: valorVenda,
            nome_do_cliente: row.nome_do_cliente || "-",
            nome_produto: row.nome_produto || "-",
            comissao: valorVenda * percentual,
            adicional: valorExtra,
            motivo_valor_extra: row.motivo_valor_extra || row.motivo || undefined,
            tipo_servico: tipoServico,
          };
        });

        setExcelData(enrichedData);
        setDataParaEnvio(enrichedData);
        toast.success(`✅ ${enrichedData.length} registros carregados do Excel`);
      } catch (error) {
        console.error("Erro ao ler Excel:", error);
        toast.error("Erro ao processar arquivo Excel");
      }
    };
    reader.readAsBinaryString(file);
  };

  // Salvar configuração de email
  const salvarConfiguracao = async () => {
    if (!emailConfig.assunto || !emailConfig.corpo) {
      toast.error("Assunto e corpo são obrigatórios");
      return;
    }

    setSavingConfig(true);
    try {
      await emailConfigService.saveConfig("montador", emailConfig);
      toast.success("✅ Configuração salva! Será usada no próximo envio.");
    } catch (error) {
      console.error("Erro ao salvar configuração:", error);
      toast.error("Erro ao salvar configuração");
    } finally {
      setSavingConfig(false);
    }
  };

  // Enviar relatórios
  const enviarRelatorios = async () => {
    if (dataParaEnvio.length === 0) {
      toast.error("Nenhum dado para enviar");
      return;
    }

    // Verificar se há boletins pendentes
    const pendentes = statusPreview.filter(s => s.status === "Pendente");
    if (pendentes.length === 0) {
      toast.error("Nenhum boletim novo para enviar. Todos já foram enviados ou estão na blacklist.");
      return;
    }

    setSending(true);
    try {
      console.log("📤 DEBUG - Enviando dados:", dataParaEnvio);
      console.log("📤 DEBUG - Primeiro item:", dataParaEnvio[0]);

      const result = await apiClient.post<any>("/relatorios/enviar-lote", {
        tipo: "montador",
        dados: dataParaEnvio,
        emailConfig: emailConfig,
        enviarWhatsApp: enviarWhatsApp,
      });

      if (result.sucesso > 0) {
        toast.success(`✅ ${result.sucesso} envio(s) realizado(s) com sucesso!`);
      }
      if (result.erros > 0) {
        toast.error(`❌ ${result.erros} erro(s) no envio`);
      }
      if (result.ignorados > 0) {
        toast.warning(`⚠️ ${result.ignorados} boletim(s) ignorado(s) (já enviados ou na blacklist)`);
      }

      // Limpar dados
      setDataParaEnvio([]);
      setExcelData([]);
      setManualEntries([]);
      setStatusPreview([]);
    } catch (error: any) {
      console.error("Erro ao enviar:", error);
      toast.error(error.message || "Erro ao enviar relatórios");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Envio de Relatórios - Montadores</h1>
        <p className="text-muted-foreground mt-2">
          Envie relatórios de pagamento para montadores com validação de blacklist e duplicatas
        </p>
      </div>

      <Tabs defaultValue="manual" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="manual">
            <Plus className="h-4 w-4 mr-2" />
            Lançamento Manual
          </TabsTrigger>
          <TabsTrigger value="excel">
            <FileSpreadsheet className="h-4 w-4 mr-2" />
            Importar Excel
          </TabsTrigger>
        </TabsList>

        {/* Lançamento Manual */}
        <TabsContent value="manual" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Adicionar Montagem Manualmente</CardTitle>
              <CardDescription>Preencha os dados do boletim de montagem</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-end mb-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={autoPreencherMontador}
                  disabled={loading || montadores.length === 0}
                >
                  ⚡ Auto Preencher
                </Button>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Montador *</Label>
                  <Select
                    value={formMontador.nome_montador}
                    onValueChange={(value) => {
                      const montador = montadores.find(m => m.nome === value);
                      setFormMontador({
                        ...formMontador,
                        nome_montador: value,
                        identificador: montador?.identificador || "",
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione o montador" />
                    </SelectTrigger>
                    <SelectContent>
                      {montadores.map((m) => (
                        <SelectItem key={m.id} value={m.nome}>
                          {m.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Identificador *</Label>
                  <Input
                    value={formMontador.identificador}
                    onChange={(e) => setFormMontador({ ...formMontador, identificador: e.target.value })}
                    placeholder="MONT001"
                    disabled
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Boletim Montagem *</Label>
                  <Input
                    value={formMontador.boletim}
                    onChange={(e) => setFormMontador({ ...formMontador, boletim: e.target.value })}
                    placeholder="12345"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Tipo de Serviço *</Label>
                  <Select
                    value={formMontador.tipo_servico}
                    onValueChange={(value: "MONTAGEM" | "ASSISTENCIA_TECNICA" | "DESMONTAGEM") =>
                      setFormMontador({ ...formMontador, tipo_servico: value })
                    }
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

                <div className="space-y-2">
                  <Label>Data da Montagem</Label>
                  <Input
                    type="date"
                    value={formMontador.data_montagem}
                    onChange={(e) => setFormMontador({ ...formMontador, data_montagem: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Valor Venda (R$)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formMontador.valor_venda}
                    onChange={(e) => setFormMontador({ ...formMontador, valor_venda: e.target.value })}
                    placeholder="0.00"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Valor Extra (R$)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formMontador.valor_extra}
                    onChange={(e) => setFormMontador({ ...formMontador, valor_extra: e.target.value })}
                    placeholder="0.00"
                  />
                  <p className="text-xs text-muted-foreground">
                    Valor fixo (não afetado pela comissão)
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>Cliente</Label>
                  <Input
                    value={formMontador.cliente}
                    onChange={(e) => setFormMontador({ ...formMontador, cliente: e.target.value })}
                    placeholder="Nome do cliente"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Motivo Valor Extra</Label>
                  <Input
                    value={formMontador.motivo_valor_extra}
                    onChange={(e) => setFormMontador({ ...formMontador, motivo_valor_extra: e.target.value })}
                    placeholder="Ex: Deslocamento, hora extra, etc"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Nome do Produto</Label>
                  <Input
                    value={formMontador.produto}
                    onChange={(e) => setFormMontador({ ...formMontador, produto: e.target.value })}
                    placeholder="Produto"
                  />
                </div>
              </div>

              <Button onClick={adicionarManual} className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Adicionar à Lista
              </Button>
            </CardContent>
          </Card>

          {/* Lista Manual */}
          {manualEntries.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Lista para Envio ({manualEntries.length} boletins)</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Montador</TableHead>
                      <TableHead>Boletim</TableHead>
                      <TableHead>Valor Venda</TableHead>
                      <TableHead>Comissão</TableHead>
                      <TableHead>Valor Extra</TableHead>
                      <TableHead>Motivo Extra</TableHead>
                      <TableHead>Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {manualEntries.map((entry, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{entry.nome_do_montador}</TableCell>
                        <TableCell>{entry.identificador_boletim_montagem}</TableCell>
                        <TableCell>R$ {entry.media_de_valor_venda.toFixed(2)}</TableCell>
                        <TableCell>R$ {entry.comissao.toFixed(2)}</TableCell>
                        <TableCell>R$ {(entry.adicional || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-sm text-gray-600">{entry.motivo_valor_extra || "-"}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const newEntries = manualEntries.filter((_, i) => i !== idx);
                              setManualEntries(newEntries);
                              setDataParaEnvio(newEntries);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Importar Excel */}
        <TabsContent value="excel" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Importar Relatório via Excel</CardTitle>
              <CardDescription>
                Faça upload do arquivo Excel com os dados de montagem
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Arquivo Excel</Label>
                <Input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleExcelUpload}
                />
                <p className="text-xs text-muted-foreground">
                  <strong>Colunas obrigatórias:</strong> identificador_do_montador, identificador_boletim_montagem,
                  data_da_montagem, media_de_valor_venda, nome_produto, tipo_servico
                </p>
                <p className="text-xs text-muted-foreground">
                  <strong>Colunas opcionais:</strong> adicional (ou valor_extra) - valor fixo não afetado pela comissão; 
                  motivo_valor_extra (ou motivo) - justificativa do valor extra
                </p>
                <p className="text-xs text-muted-foreground">
                  <strong>Valores para tipo_servico:</strong> MONTAGEM, ASSISTENCIA_TECNICA (ou ASSIST), DESMONTAGEM (ou DESMONT)
                </p>
              </div>

              {excelData.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">
                    ✅ {excelData.length} registros carregados
                  </p>
                  <div className="max-h-[300px] overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Montador</TableHead>
                          <TableHead>Boletim</TableHead>
                          <TableHead>Data</TableHead>
                          <TableHead>Valor</TableHead>
                          <TableHead>Produto</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {excelData.slice(0, 10).map((row, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{row.nome_do_montador}</TableCell>
                            <TableCell>{row.identificador_boletim_montagem}</TableCell>
                            <TableCell>{row.data_da_montagem}</TableCell>
                            <TableCell>R$ {row.media_de_valor_venda?.toFixed(2)}</TableCell>
                            <TableCell>{row.nome_produto}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    {excelData.length > 10 && (
                      <p className="text-sm text-muted-foreground mt-2 text-center">
                        ... e mais {excelData.length - 10} registros
                      </p>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Preview de Status */}
      {statusPreview.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>📊 Status dos Boletins</CardTitle>
            <CardDescription>Verificação de blacklist e envios anteriores</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 mb-4">
              <Badge variant="default" className="bg-green-500">
                {statusPreview.filter(s => s.status === "Pendente").length} Pendentes
              </Badge>
              <Badge variant="default" className="bg-orange-500">
                {statusPreview.filter(s => s.status === "Já enviado").length} Já Enviados
              </Badge>
              <Badge variant="default" className="bg-red-500">
                {statusPreview.filter(s => s.status === "Na blacklist").length} Na Blacklist
              </Badge>
            </div>

            <div className="max-h-[200px] overflow-auto">
              <div className="grid grid-cols-3 gap-2">
                {statusPreview.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <span className="font-mono">{item.number}</span>
                    <Badge
                      variant={
                        item.status === "Pendente"
                          ? "default"
                          : item.status === "Já enviado"
                          ? "secondary"
                          : "destructive"
                      }
                    >
                      {item.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Configurações de Email */}
      <Card>
        <CardHeader>
          <CardTitle>⚙️ Configurações de E-mail</CardTitle>
          <CardDescription>
            Personalize o assunto e corpo do email. Use variáveis: {"{"}
            {"{nome_montador}}"}, {"{"}
            {"{periodo_relatorio}}"}, {"{"}
            {"{link_upload}}"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>CC (Cópia)</Label>
            <Input
              value={emailConfig.cc}
              onChange={(e) => setEmailConfig({ ...emailConfig, cc: e.target.value })}
              placeholder="email1@empresa.com, email2@empresa.com"
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
            <Label>Corpo do E-mail</Label>
            <Textarea
              value={emailConfig.corpo}
              onChange={(e) => setEmailConfig({ ...emailConfig, corpo: e.target.value })}
              rows={6}
            />
          </div>

          <Button 
            onClick={salvarConfiguracao} 
            disabled={savingConfig}
            variant="outline"
            className="w-full"
          >
            💾 Salvar Configuração
          </Button>
          <p className="text-xs text-muted-foreground text-center">
            A configuração salva será carregada automaticamente na próxima vez
          </p>

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
        </CardContent>
      </Card>

      {/* Botão de Envio */}
      {dataParaEnvio.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <Button
              onClick={enviarRelatorios}
              disabled={sending || statusPreview.filter(s => s.status === "Pendente").length === 0}
              className="w-full"
              size="lg"
            >
              {sending ? (
                <>Enviando...</>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Enviar {statusPreview.filter(s => s.status === "Pendente").length} Relatório(s)
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
