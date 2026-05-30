import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  FileSpreadsheet, 
  Trash2, 
  Download, 
  Upload, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Copy,
  RefreshCw,
  BarChart3
} from "lucide-react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import * as XLSX from "xlsx";

interface MMSRecord {
  certificado: string;
  filial_montadora?: string;
  data_emissao?: string;
  data_entrega?: string;
  data_pre_agendamento?: string;
  turno_agendamento?: string;
  codigo_conjunto?: string;
  codigo_mercadoria?: string;
  qtde_unit_mercadoria?: string;
  descricao_mercadoria?: string;
  valor_mercadoria?: string;
  valor_unitario_mercadoria?: string;
  valor_servico?: string;
  valor_custo?: string;
  vigencia_inicial?: string;
  nome_cliente?: string;
  cpf_cnpj?: string;
  endereco?: string;
  numero_endereco?: string;
  complemento_endereco?: string;
  referencia?: string;
  cidade?: string;
  uf?: string;
  bairro?: string;
  cep?: string;
  ddd?: string;
  telefone_principal?: string;
  ddd_tel_secundario?: string;
  tel_secundario?: string;
  email_segurado?: string;
  tipo_pessoa?: string;
  entrega_realizada?: string;
  id_plano?: string;
}

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

// Ordem das colunas conforme especificado
const COLUMN_ORDER = [
  "certificado",
  "filial_montadora",
  "data_emissao",
  "data_entrega",
  "data_pre_agendamento",
  "turno_agendamento",
  "codigo_conjunto",
  "codigo_mercadoria",
  "qtde_unit_mercadoria",
  "descricao_mercadoria",
  "valor_mercadoria",
  "valor_unitario_mercadoria",
  "valor_servico",
  "valor_custo",
  "vigencia_inicial",
  "nome_cliente",
  "cpf_cnpj",
  "endereco",
  "numero_endereco",
  "complemento_endereco",
  "referencia",
  "cidade",
  "uf",
  "bairro",
  "cep",
  "ddd",
  "telefone_principal",
  "ddd_tel_secundario",
  "tel_secundario",
  "email_segurado",
  "tipo_pessoa",
  "entrega_realizada",
  "id_plano"
];

// Headers para exibição
const COLUMN_HEADERS = [
  "certificado",
  "Filial Montadora",
  "Data emissao mms",
  "Data da entrega mms",
  "date([dataPreAgendamento mms])",
  "Turno agendamento mms",
  "codigoConjunto mms",
  "codigoMercadoria mms",
  "qtdeUnitMercadoria mms",
  "descricaoMercadoria mms",
  "valorMercadoria mms",
  "valorUnitarioMercadoria mms",
  "valorServico mms",
  "valorCusto mms",
  "vigenciaInicial mms",
  "nomeCliente mms",
  "cpfCnpj mms",
  "endereco mms",
  "numeroEndereco mms",
  "complementoEndereco mms",
  "referencia mms",
  "cidade mms",
  "uf mms",
  "bairro mms",
  "cep mms",
  "ddd mms",
  "telefonePrincipal mms",
  "dddTelSecundario mms",
  "TelSecundario mms",
  "emailSegurado mms",
  "tipoPessoa mms",
  "entregaRealizada MMS",
  "idPlano MMS"
];

export default function MMS() {
  const [inputData, setInputData] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [estatisticas, setEstatisticas] = useState<Estatisticas | null>(null);
  const [outputData, setOutputData] = useState("");
  const { toast } = useToast();

  // Parsear os dados colados (tab-separated)
  const parseInputData = (text: string): MMSRecord[] => {
    const lines = text.trim().split('\n');
    const records: MMSRecord[] = [];
    
    // Pular header se existir
    const startIndex = lines[0]?.toLowerCase().includes('certificado') ? 1 : 0;
    
    for (let i = startIndex; i < lines.length; i++) {
      const values = lines[i].split('\t');
      if (values.length > 0 && values[0]?.trim()) {
        const record: MMSRecord = {
          certificado: values[0]?.trim() || '',
          filial_montadora: values[1]?.trim() || '',
          data_emissao: values[2]?.trim() || '',
          data_entrega: values[3]?.trim() || '',
          data_pre_agendamento: values[4]?.trim() || '',
          turno_agendamento: values[5]?.trim() || '',
          codigo_conjunto: values[6]?.trim() || '',
          codigo_mercadoria: values[7]?.trim() || '',
          qtde_unit_mercadoria: values[8]?.trim() || '',
          descricao_mercadoria: values[9]?.trim() || '',
          valor_mercadoria: values[10]?.trim() || '',
          valor_unitario_mercadoria: values[11]?.trim() || '',
          valor_servico: values[12]?.trim() || '',
          valor_custo: values[13]?.trim() || '',
          vigencia_inicial: values[14]?.trim() || '',
          nome_cliente: values[15]?.trim() || '',
          cpf_cnpj: values[16]?.trim() || '',
          endereco: values[17]?.trim() || '',
          numero_endereco: values[18]?.trim() || '',
          complemento_endereco: values[19]?.trim() || '',
          referencia: values[20]?.trim() || '',
          cidade: values[21]?.trim() || '',
          uf: values[22]?.trim() || '',
          bairro: values[23]?.trim() || '',
          cep: values[24]?.trim() || '',
          ddd: values[25]?.trim() || '',
          telefone_principal: values[26]?.trim() || '',
          ddd_tel_secundario: values[27]?.trim() || '',
          tel_secundario: values[28]?.trim() || '',
          email_segurado: values[29]?.trim() || '',
          tipo_pessoa: values[30]?.trim() || '',
          entrega_realizada: values[31]?.trim() || '',
          id_plano: values[32]?.trim() || ''
        };
        records.push(record);
      }
    }
    
    return records;
  };

  // Converter registros de volta para texto tab-separated
  const recordsToText = (records: MMSRecord[], includeHeader: boolean = true): string => {
    let lines: string[] = [];
    
    if (includeHeader) {
      lines.push(COLUMN_HEADERS.join('\t'));
    }
    
    for (const record of records) {
      const values = COLUMN_ORDER.map(col => (record as any)[col] || '');
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
      
      // Atualizar estatísticas
      carregarEstatisticas();
      
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

  // Limpar banco
  const handleLimpar = async () => {
    if (!confirm("Tem certeza que deseja LIMPAR TODOS os certificados do banco?\n\nIsso não pode ser desfeito!")) {
      return;
    }

    setLoading(true);
    try {
      const response: any = await apiClient.delete('/mms/limpar');
      
      toast({
        title: "Dados limpos!",
        description: `${response.registros_removidos} registros removidos`,
      });
      
      setResult(null);
      setOutputData("");
      carregarEstatisticas();
      
    } catch (error: any) {
      toast({
        title: "Erro ao limpar",
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
    const headers = COLUMN_HEADERS;
    const data = result.dados_novos.map(record => 
      COLUMN_ORDER.map(col => (record as any)[col] || '')
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

  // Carregar estatísticas ao montar
  useState(() => {
    carregarEstatisticas();
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
            Remova duplicados dos relatórios MMS baseado no certificado
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={carregarEstatisticas}
            disabled={loading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Atualizar
          </Button>
          <Button 
            variant="destructive" 
            onClick={handleLimpar}
            disabled={loading}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Limpar Banco
          </Button>
        </div>
      </div>

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
                <span className="text-muted-foreground">Total de certificados:</span>
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
              <strong>Processar:</strong> Salva os novos certificados no banco.
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
            <li>Ou clique em "Processar e Salvar" para salvar os novos certificados no banco</li>
            <li>Os dados limpos (sem duplicados) aparecem à direita</li>
            <li>Copie ou baixe o resultado para usar no seu relatório</li>
          </ol>
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <p className="text-sm font-medium">⚠️ Importante:</p>
            <p className="text-sm text-muted-foreground">
              O sistema verifica duplicados pelo campo <strong>certificado</strong>. 
              Uma vez processado, o certificado fica salvo no banco e será considerado duplicado nas próximas vezes.
              Use "Limpar Banco" apenas se quiser reiniciar do zero.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
