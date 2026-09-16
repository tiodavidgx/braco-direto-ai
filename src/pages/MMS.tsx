import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  FileSpreadsheet,
  Download,
  Upload,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Copy,
  RefreshCw,
  BarChart3,
  History
} from "lucide-react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import * as XLSX from "xlsx";

interface ProcessResult {
  total_recebidos: number;
  total_novos: number;
  total_duplicados: number;
  dados_novos: MMSRecord[];
}

interface Estatisticas {
  total_certificados: number;
  primeiro_registro: string | null;
  ultimo_registro: string | null;
}

interface ImportLog {
  id: number;
  criado_em: string;
  total_recebidos: number;
  total_novos: number;
  total_duplicados: number;
  usuario_nome: string | null;
}

// Layout do relatório MMS: campo interno + nome da coluna na planilha (na ordem da planilha)
const COLUMNS = [
  { field: "numero_pedido", header: "Número do Pedido" },
  { field: "filial", header: "Filial" },
  { field: "canal_venda", header: "Canal de Venda" },
  { field: "origem_os", header: "Origem OS" },
  { field: "id_contrato", header: "ID do Contrato" },
  { field: "id_criticidade", header: "ID da Criticidade" },
  { field: "cep", header: "CEP" },
  { field: "logradouro", header: "Logradouro" },
  { field: "numero", header: "Número" },
  { field: "bairro", header: "Bairro" },
  { field: "cidade", header: "Cidade" },
  { field: "uf", header: "UF" },
  { field: "complemento", header: "Complemento" },
  { field: "referencia_endereco", header: "Referência do Endereço" },
  { field: "telefone", header: "Telefone" },
  { field: "celular", header: "Celular" },
  { field: "email", header: "E-mail" },
  { field: "nome_cliente", header: "Nome do Cliente Final" },
  { field: "cpf_cnpj", header: "CPF/CNPJ do Cliente" },
  { field: "valor_total_pedido", header: "Valor Total do Pedido" },
  { field: "data_recebimento", header: "Data de Recebimento" },
  { field: "id_servico", header: "ID do Serviço" },
  { field: "valor_servico", header: "Valor do Serviço" },
  { field: "data_agendamento", header: "Data de Agendamento" },
  { field: "turno_agendamento", header: "Turno de Agendamento" },
  { field: "data_previsao_entrega", header: "Data de Previsão de Entrega" },
  { field: "confirma_entrega", header: "Confirma Entrega" },
  { field: "sku_produto", header: "SKU do Produto" },
  { field: "descricao_produto", header: "Descrição do Produto" },
  { field: "valor_unitario_produto", header: "Valor Unitário do Produto" },
  { field: "quantidade_produto", header: "Quantidade do Produto" },
  { field: "quantidade_volumes", header: "Quantidade de Volumes" },
] as const;

type MMSField = typeof COLUMNS[number]["field"];
type MMSRecord = Record<MMSField, string>;

// Coluna que define duplicidade
const KEY_FIELD: MMSField = "numero_pedido";
const KEY_HEADER = "Número do Pedido";

// Normaliza nome de coluna: sem acento, minúsculo, espaços simples
const normalizeHeader = (header: string) =>
  header.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();

const HEADER_TO_FIELD: Record<string, MMSField> = Object.fromEntries(
  COLUMNS.map(c => [normalizeHeader(c.header), c.field])
);

export default function MMS() {
  const [inputData, setInputData] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [estatisticas, setEstatisticas] = useState<Estatisticas | null>(null);
  const [outputData, setOutputData] = useState("");
  const [logs, setLogs] = useState<ImportLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const { toast } = useToast();

  // Parsear os dados colados (tab-separated)
  const parseInputData = (text: string): MMSRecord[] => {
    const lines = text.trim().split(/\r?\n/);
    const records: MMSRecord[] = [];

    // Posição de cada campo: pelo nome no cabeçalho, ou pela ordem padrão se não houver cabeçalho
    const colIndex: Partial<Record<MMSField, number>> = {};
    const headerCells = (lines[0] ?? '').split('\t').map(normalizeHeader);
    const hasHeader = headerCells.some(cell => cell in HEADER_TO_FIELD);

    if (hasHeader) {
      headerCells.forEach((cell, i) => {
        const field = HEADER_TO_FIELD[cell];
        if (field && colIndex[field] === undefined) colIndex[field] = i;
      });
      if (colIndex[KEY_FIELD] === undefined) {
        throw new Error(`Coluna "${KEY_HEADER}" não encontrada no cabeçalho`);
      }
    } else {
      COLUMNS.forEach((c, pos) => { colIndex[c.field] = pos; });
    }

    for (let i = hasHeader ? 1 : 0; i < lines.length; i++) {
      const values = lines[i].split('\t');
      const get = (field: MMSField) => {
        const idx = colIndex[field];
        return idx === undefined ? '' : values[idx]?.trim() || '';
      };

      if (!get(KEY_FIELD)) continue;

      records.push(
        Object.fromEntries(COLUMNS.map(c => [c.field, get(c.field)])) as MMSRecord
      );
    }

    return records;
  };

  // Converter registros de volta para texto tab-separated
  const recordsToText = (records: MMSRecord[], includeHeader: boolean = true): string => {
    let lines: string[] = [];
    
    if (includeHeader) {
      lines.push(COLUMNS.map(c => c.header).join('\t'));
    }
    
    for (const record of records) {
      const values = COLUMNS.map(c => record[c.field] || '');
      lines.push(values.join('\t'));
    }
    
    return lines.join('\n');
  };

  // Processar dados (verificar e salvar)
  const handleProcessar = async () => {
    if (!inputData.trim()) {
      toast({
        title: "Erro",
        description: "Cole os dados primeiro",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      const records = parseInputData(inputData);
      
      if (records.length === 0) {
        toast({
          title: "Erro",
          description: "Nenhum dado válido encontrado",
          variant: "destructive"
        });
        return;
      }

      const response: ProcessResult = await apiClient.post('/mms/processar', { dados: records });
      setResult(response);
      
      // Gerar output apenas com dados novos
      if (response.dados_novos.length > 0) {
        setOutputData(recordsToText(response.dados_novos));
      } else {
        setOutputData("");
      }
      
      toast({
        title: "Processamento concluído!",
        description: `${response.total_novos} novos, ${response.total_duplicados} duplicados`,
      });
      
      // Atualizar estatísticas e logs
      carregarEstatisticas();
      carregarLogs();

    } catch (error: any) {
      toast({
        title: "Erro ao processar",
        description: error.message || "Erro desconhecido",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  // Apenas verificar (sem salvar)
  const handleVerificar = async () => {
    if (!inputData.trim()) {
      toast({
        title: "Erro",
        description: "Cole os dados primeiro",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      const records = parseInputData(inputData);
      
      if (records.length === 0) {
        toast({
          title: "Erro",
          description: "Nenhum dado válido encontrado",
          variant: "destructive"
        });
        return;
      }

      const response: any = await apiClient.post('/mms/verificar', { dados: records });
      setResult({
        total_recebidos: response.total_recebidos,
        total_novos: response.total_novos,
        total_duplicados: response.total_duplicados,
        dados_novos: response.dados_novos
      });
      
      // Gerar output apenas com dados novos
      if (response.dados_novos.length > 0) {
        setOutputData(recordsToText(response.dados_novos));
      } else {
        setOutputData("");
      }
      
      toast({
        title: "Verificação concluída!",
        description: `${response.total_novos} novos, ${response.total_duplicados} duplicados (dados NÃO salvos)`,
      });
      
    } catch (error: any) {
      toast({
        title: "Erro ao verificar",
        description: error.message || "Erro desconhecido",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  // Carregar estatísticas
  const carregarEstatisticas = async () => {
    try {
      const response: Estatisticas = await apiClient.get('/mms/estatisticas');
      setEstatisticas(response);
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
    }
  };

  // Carregar logs de importação
  const carregarLogs = async () => {
    setLoadingLogs(true);
    try {
      const response: ImportLog[] = await apiClient.get('/mms/importacoes');
      setLogs(response);
    } catch (error) {
      console.error('Erro ao carregar logs:', error);
    } finally {
      setLoadingLogs(false);
    }
  };

  // Copiar output
  const handleCopiarOutput = () => {
    if (outputData) {
      navigator.clipboard.writeText(outputData);
      toast({
        title: "Copiado!",
        description: "Dados copiados para a área de transferência",
      });
    }
  };

  // Baixar como CSV
  const handleDownloadCSV = () => {
    if (!outputData) return;
    
    const blob = new Blob([outputData], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `mms_limpo_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Baixar como XLSX (Excel)
  const handleDownloadXLSX = () => {
    if (!result || result.dados_novos.length === 0) {
      toast({
        title: "Erro",
        description: "Nenhum dado para exportar",
        variant: "destructive"
      });
      return;
    }

    // Preparar dados com cabeçalhos originais
    const headers = COLUMNS.map(c => c.header);
    const data = result.dados_novos.map(record => 
      COLUMNS.map(c => record[c.field] || '')
    );

    // Criar worksheet
    const ws = XLSX.utils.aoa_to_sheet([headers, ...data]);
    
    // Ajustar largura das colunas
    const colWidths = headers.map((h, i) => {
      const maxLen = Math.max(
        h.length,
        ...data.map(row => String(row[i] || '').length)
      );
      return { wch: Math.min(maxLen + 2, 50) };
    });
    ws['!cols'] = colWidths;

    // Criar workbook
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Dados Limpos');

    // Baixar arquivo
    XLSX.writeFile(wb, `mms_limpo_${new Date().toISOString().split('T')[0]}.xlsx`);

    toast({
      title: "Download iniciado",
      description: `Exportando ${result.dados_novos.length} registros para Excel`,
    });
  };

  // Carregar estatísticas e logs ao montar
  useState(() => {
    carregarEstatisticas();
    carregarLogs();
  });

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <FileSpreadsheet className="h-8 w-8" />
            MMS - Limpeza de Dados
          </h1>
          <p className="text-muted-foreground mt-1">
            Remova duplicados dos relatórios MMS baseado no Número do Pedido
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => { carregarEstatisticas(); carregarLogs(); }}
            disabled={loading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Atualizar
          </Button>
        </div>
      </div>

      <Tabs defaultValue="limpeza" className="space-y-6">
        <TabsList>
          <TabsTrigger value="limpeza" className="flex items-center gap-2">
            <FileSpreadsheet className="h-4 w-4" />
            Limpeza de Dados
          </TabsTrigger>
          <TabsTrigger value="logs" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Logs de Importação
          </TabsTrigger>
        </TabsList>

        <TabsContent value="limpeza" className="space-y-6 mt-6">

      {/* Estatísticas */}
      {estatisticas && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Estatísticas do Banco
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-6">
              <div>
                <span className="text-muted-foreground">Total de pedidos:</span>
                <Badge variant="secondary" className="ml-2 text-lg">
                  {estatisticas.total_certificados.toLocaleString()}
                </Badge>
              </div>
              {estatisticas.primeiro_registro && (
                <div>
                  <span className="text-muted-foreground">Primeiro registro:</span>
                  <span className="ml-2">{new Date(estatisticas.primeiro_registro).toLocaleString()}</span>
                </div>
              )}
              {estatisticas.ultimo_registro && (
                <div>
                  <span className="text-muted-foreground">Último registro:</span>
                  <span className="ml-2">{new Date(estatisticas.ultimo_registro).toLocaleString()}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Dados de Entrada
            </CardTitle>
            <CardDescription>
              Cole aqui os dados do relatório MMS (copiados do Excel/planilha)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="Cole os dados aqui (com ou sem cabeçalho)...

Os dados devem estar separados por TAB (como quando copia do Excel)"
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              className="min-h-[300px] font-mono text-xs"
            />
            
            <div className="flex gap-2">
              <Button 
                onClick={handleVerificar} 
                disabled={loading || !inputData.trim()}
                variant="outline"
                className="flex-1"
              >
                <AlertTriangle className="h-4 w-4 mr-2" />
                Apenas Verificar
              </Button>
              <Button 
                onClick={handleProcessar} 
                disabled={loading || !inputData.trim()}
                className="flex-1"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Processar e Salvar
              </Button>
            </div>
            
            <p className="text-xs text-muted-foreground">
              <strong>Verificar:</strong> Mostra duplicados sem salvar no banco.
              <br />
              <strong>Processar:</strong> Salva os novos pedidos no banco.
            </p>
          </CardContent>
        </Card>

        {/* Output */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Resultado (Dados Limpos)
            </CardTitle>
            <CardDescription>
              Somente os registros NÃO duplicados aparecem aqui
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {result && (
              <Alert className={result.total_novos > 0 ? "border-green-500" : "border-yellow-500"}>
                <AlertTitle className="flex items-center gap-2">
                  {result.total_novos > 0 ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-yellow-500" />
                  )}
                  Resultado do Processamento
                </AlertTitle>
                <AlertDescription>
                  <div className="flex gap-4 mt-2">
                    <Badge variant="outline">
                      Total: {result.total_recebidos}
                    </Badge>
                    <Badge variant="default" className="bg-green-500">
                      Novos: {result.total_novos}
                    </Badge>
                    <Badge variant="destructive">
                      Duplicados: {result.total_duplicados}
                    </Badge>
                  </div>
                </AlertDescription>
              </Alert>
            )}
            
            <Textarea
              placeholder="Os dados limpos aparecerão aqui após o processamento..."
              value={outputData}
              readOnly
              className="min-h-[250px] font-mono text-xs"
            />
            
            <div className="flex gap-2">
              <Button 
                onClick={handleCopiarOutput} 
                disabled={!outputData}
                variant="outline"
                className="flex-1"
              >
                <Copy className="h-4 w-4 mr-2" />
                Copiar
              </Button>
              <Button 
                onClick={handleDownloadCSV} 
                disabled={!outputData}
                variant="outline"
                className="flex-1"
              >
                <Download className="h-4 w-4 mr-2" />
                CSV
              </Button>
              <Button 
                onClick={handleDownloadXLSX} 
                disabled={!result || result.dados_novos.length === 0}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Excel (XLSX)
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Instruções */}
      <Card>
        <CardHeader>
          <CardTitle>Como usar</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Copie os dados do seu relatório MMS (do Excel ou planilha)</li>
            <li>Cole na área "Dados de Entrada" à esquerda</li>
            <li>Clique em "Apenas Verificar" para ver quantos são duplicados <strong>sem salvar</strong></li>
            <li>Ou clique em "Processar e Salvar" para salvar os novos pedidos no banco</li>
            <li>Os dados limpos (sem duplicados) aparecem à direita</li>
            <li>Copie ou baixe o resultado para usar no seu relatório</li>
          </ol>
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <p className="text-sm font-medium">⚠️ Importante:</p>
            <p className="text-sm text-muted-foreground">
              O sistema verifica duplicados pela coluna <strong>Número do Pedido</strong>.
              Fica uma linha por pedido: se o mesmo pedido vier em várias linhas (um produto por linha), só a primeira é mantida.
              Uma vez processado, o pedido fica salvo no banco e será considerado duplicado nas próximas vezes.
            </p>
          </div>
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Logs de Importação
              </CardTitle>
              <CardDescription>
                Histórico das importações realizadas (ação "Processar e Salvar"): data/hora, quantidade de novos pedidos e quem realizou.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {logs.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  {loadingLogs ? "Carregando..." : "Nenhuma importação registrada ainda."}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Data / Hora</TableHead>
                        <TableHead className="text-right">Recebidos</TableHead>
                        <TableHead className="text-right">Novos</TableHead>
                        <TableHead className="text-right">Duplicados</TableHead>
                        <TableHead>Usuário</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {logs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell className="whitespace-nowrap">
                            {new Date(log.criado_em).toLocaleString('pt-BR')}
                          </TableCell>
                          <TableCell className="text-right">{log.total_recebidos}</TableCell>
                          <TableCell className="text-right">
                            <Badge className="bg-green-500">{log.total_novos}</Badge>
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {log.total_duplicados}
                          </TableCell>
                          <TableCell>{log.usuario_nome || '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
