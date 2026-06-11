import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import {
  RefreshCw,
  Eye,
  Check,
  User,
  Building2,
  Phone,
  MapPin,
  FileText,
  Clock,
  CheckCircle2,
  FileImage,
  Download,
  X,
  AlertCircle,
  XCircle,
  CheckCircle,
  History
} from "lucide-react";

interface PreCadastro {
  id: number;
  tipo_pessoa: "PF" | "PJ";
  nome: string;
  cpf_cnpj: string | null;
  email: string | null;
  telefone: string | null;
  filial: string | null;
  cidade: string | null;
  endereco: string | null;
  banco: string | null;
  agencia: string | null;
  conta: string | null;
  tipo_conta: string | null;
  pix: string | null;
  percentual_montagem: number;
  percentual_assistencia: number;
  percentual_desmontagem: number;
  auxilio_semanal: number;
  doc_comprovante_endereco: string | null;
  doc_comprovante_bancario: string | null;
  doc_documento_pessoal: string | null;
  doc_comprovante_mei: string | null;
  // Campos de revisão de documentos
  doc_documento_pessoal_status: string | null;
  doc_documento_pessoal_motivo: string | null;
  doc_comprovante_endereco_status: string | null;
  doc_comprovante_endereco_motivo: string | null;
  doc_comprovante_bancario_status: string | null;
  doc_comprovante_bancario_motivo: string | null;
  doc_comprovante_mei_status: string | null;
  doc_comprovante_mei_motivo: string | null;
  // Campos de conclusão
  id_montador: string | null;
  numero_fornecedor: string | null;
  re: string | null;
  concluido_por: number | null;
  concluido_por_nome: string | null;
  concluido_em: string | null;
  status: string;
  etapa_atual: number;
  observacoes: string | null;
  criado_por_nome: string | null;
  created_at: string;
  updated_at: string;
}

const RevisaoCadastroMontador = () => {
  const [cadastros, setCadastros] = useState<PreCadastro[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCadastro, setSelectedCadastro] = useState<PreCadastro | null>(null);
  const [showCardDialog, setShowCardDialog] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<string | null>(null);
  const [previewDocName, setPreviewDocName] = useState<string>("");
  
  // Estados do formulário de revisão
  const [checkMontador, setCheckMontador] = useState(false);
  const [checkFornecedor, setCheckFornecedor] = useState(false);
  const [checkChamadoTI, setCheckChamadoTI] = useState(false);
  const [idMontador, setIdMontador] = useState("");
  const [numeroFornecedor, setNumeroFornecedor] = useState("");
  const [re, setRe] = useState("");
  const [concluindo, setConcluindo] = useState(false);
  
  // Estados para revisão de documentos
  const [showRecusarDialog, setShowRecusarDialog] = useState(false);
  const [docRecusando, setDocRecusando] = useState<{ tipo: string; nome: string } | null>(null);
  const [motivoRecusa, setMotivoRecusa] = useState("");
  const [processandoRevisao, setProcessandoRevisao] = useState(false);

  const fetchCadastros = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<{ data: PreCadastro[]; total: number }>("/pre-cadastro-montadores");
      setCadastros(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar cadastros:", error);
      toast.error("Erro ao carregar cadastros");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCadastros();
  }, [fetchCadastros]);

  const pendentes = cadastros.filter(c => c.status === "aguardando_docs" || c.status === "em_analise" || c.status === "aprovado");
  const concluidos = cadastros.filter(c => c.status === "convertido");

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const abrirCard = (cadastro: PreCadastro) => {
    setSelectedCadastro(cadastro);
    // Se já foi concluído, preencher os campos
    if (cadastro.status === 'convertido') {
      setCheckMontador(true);
      setCheckFornecedor(true);
      setCheckChamadoTI(true);
      setIdMontador(cadastro.id_montador || "");
      setNumeroFornecedor(cadastro.numero_fornecedor || "");
      setRe(cadastro.re || "");
    } else {
      setCheckMontador(false);
      setCheckFornecedor(false);
      setCheckChamadoTI(false);
      setIdMontador("");
      setNumeroFornecedor("");
      setRe("");
    }
    setShowCardDialog(true);
  };

  const getDocUrl = (docPath: string | null) => {
    if (!docPath) return null;
    // Usar a URL base da janela em produção
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      return `${window.location.origin}${docPath}`;
    }
    return `http://localhost:14001${docPath}`;
  };

  const abrirPreviewDoc = (docPath: string | null, docName: string) => {
    if (!docPath) return;
    const url = getDocUrl(docPath);
    if (url) {
      setPreviewDoc(url);
      setPreviewDocName(docName);
    }
  };

  const getDocumentos = (cadastro: PreCadastro) => {
    const docs: { nome: string; path: string; tipo: string; status: string | null; motivo: string | null }[] = [];
    
    if (cadastro.tipo_pessoa === "PF") {
      if (cadastro.doc_documento_pessoal) {
        docs.push({ 
          nome: "Documento Pessoal", 
          path: cadastro.doc_documento_pessoal,
          tipo: "documento_pessoal",
          status: cadastro.doc_documento_pessoal_status,
          motivo: cadastro.doc_documento_pessoal_motivo
        });
      }
      if (cadastro.doc_comprovante_endereco) {
        docs.push({ 
          nome: "Comprovante de Endereço", 
          path: cadastro.doc_comprovante_endereco,
          tipo: "comprovante_endereco",
          status: cadastro.doc_comprovante_endereco_status,
          motivo: cadastro.doc_comprovante_endereco_motivo
        });
      }
    }
    
    if (cadastro.doc_comprovante_bancario) {
      docs.push({ 
        nome: "Comprovante Bancário", 
        path: cadastro.doc_comprovante_bancario,
        tipo: "comprovante_bancario",
        status: cadastro.doc_comprovante_bancario_status,
        motivo: cadastro.doc_comprovante_bancario_motivo
      });
    }
    
    if (cadastro.tipo_pessoa === "PJ" && cadastro.doc_comprovante_mei) {
      docs.push({ 
        nome: "Comprovante MEI", 
        path: cadastro.doc_comprovante_mei,
        tipo: "comprovante_mei",
        status: cadastro.doc_comprovante_mei_status,
        motivo: cadastro.doc_comprovante_mei_motivo
      });
    }
    
    return docs;
  };

  const aprovarDocumento = async (tipoDocumento: string) => {
    if (!selectedCadastro) return;
    
    setProcessandoRevisao(true);
    try {
      const response = await apiClient.post<{ cadastro: PreCadastro }>(`/pre-cadastro-montadores/${selectedCadastro.id}/revisar-documento`, {
        tipo_documento: tipoDocumento,
        status: "aprovado"
      });
      
      setSelectedCadastro(response.cadastro);
      toast.success("Documento aprovado!");
      fetchCadastros();
    } catch (error: any) {
      console.error("Erro ao aprovar documento:", error);
      toast.error(error.message || "Erro ao aprovar documento");
    } finally {
      setProcessandoRevisao(false);
    }
  };

  const abrirRecusarDialog = (tipoDocumento: string, nomeDocumento: string) => {
    setDocRecusando({ tipo: tipoDocumento, nome: nomeDocumento });
    setMotivoRecusa("");
    setShowRecusarDialog(true);
  };

  const recusarDocumento = async () => {
    if (!selectedCadastro || !docRecusando) return;
    
    if (!motivoRecusa.trim()) {
      toast.error("Informe o motivo da recusa");
      return;
    }
    
    setProcessandoRevisao(true);
    try {
      const response = await apiClient.post<{ cadastro: PreCadastro }>(`/pre-cadastro-montadores/${selectedCadastro.id}/revisar-documento`, {
        tipo_documento: docRecusando.tipo,
        status: "recusado",
        motivo: motivoRecusa.trim()
      });
      
      setSelectedCadastro(response.cadastro);
      setShowRecusarDialog(false);
      setDocRecusando(null);
      setMotivoRecusa("");
      toast.success("Documento recusado. O montador será notificado para reenvio.");
      fetchCadastros();
    } catch (error: any) {
      console.error("Erro ao recusar documento:", error);
      toast.error(error.message || "Erro ao recusar documento");
    } finally {
      setProcessandoRevisao(false);
    }
  };

  const getStatusIcon = (status: string | null) => {
    if (status === "aprovado") return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (status === "recusado") return <XCircle className="h-4 w-4 text-red-500" />;
    return <AlertCircle className="h-4 w-4 text-yellow-500" />;
  };

  const getStatusBadge = (status: string | null) => {
    if (status === "aprovado") return <Badge className="bg-green-100 text-green-700">Aprovado</Badge>;
    if (status === "recusado") return <Badge className="bg-red-100 text-red-700">Recusado</Badge>;
    return <Badge className="bg-yellow-100 text-yellow-700">Pendente</Badge>;
  };

  const handleConcluir = async () => {
    if (!selectedCadastro) return;

    // Validar que todos os documentos foram revisados (aprovados ou recusados)
    const documentos = getDocumentos(selectedCadastro);
    const docsPendentes = documentos.filter(doc => !doc.status || (doc.status !== 'aprovado' && doc.status !== 'recusado'));
    
    if (docsPendentes.length > 0) {
      toast.error(`Revise todos os documentos antes de concluir. Documentos pendentes: ${docsPendentes.map(d => d.nome).join(', ')}`);
      return;
    }

    // Verificar se algum documento foi recusado
    const docsRecusados = documentos.filter(doc => doc.status === 'recusado');
    if (docsRecusados.length > 0) {
      toast.error(`Existem documentos recusados. O montador precisa reenviar: ${docsRecusados.map(d => d.nome).join(', ')}`);
      return;
    }

    // Validações
    if (!checkMontador) {
      toast.error("Marque 'Montador cadastrado'");
      return;
    }
    if (!checkFornecedor) {
      toast.error("Marque 'Fornecedor cadastrado'");
      return;
    }
    if (!checkChamadoTI) {
      toast.error("Marque 'Chamado TI concluído'");
      return;
    }
    if (!idMontador.trim()) {
      toast.error("Informe o ID do Montador");
      return;
    }
    if (!numeroFornecedor.trim()) {
      toast.error("Informe o Número do Fornecedor");
      return;
    }
    if (!re.trim()) {
      toast.error("Informe o RE");
      return;
    }

    setConcluindo(true);
    try {
      // 1. Criar o montador na tabela de montadores (ignorar se já existir)
      try {
        await apiClient.post("/montadores", {
          identificador: idMontador.trim(),
          nome: selectedCadastro.nome,
          fornecedor_id: numeroFornecedor.trim(),
          email: selectedCadastro.email || `montador${idMontador.trim()}@semmail.com`,
          telefone: selectedCadastro.telefone || "",
          filial: selectedCadastro.filial || "",
          cidade: selectedCadastro.cidade || "",
          pix: selectedCadastro.pix || "",
          percentual_montagem: (selectedCadastro.percentual_montagem || 5) / 100,
          percentual_assistencia: (selectedCadastro.percentual_assistencia || 3) / 100,
          percentual_desmontagem: (selectedCadastro.percentual_desmontagem || 2) / 100,
          auxilio_semanal: selectedCadastro.auxilio_semanal || 0,
          ativo: true,
          envio_automatico: true,
          dias_envio_mes: (selectedCadastro as any).dias_envio_mes || [16, 26],
          email_responsavel_nm: (selectedCadastro as any).email_responsavel_nm || "",
          tipo_pagamento: (selectedCadastro as any).tipo_pagamento || "novo_mundo",
          terceirizada_id: (selectedCadastro as any).terceirizada_id || null,
          email_template_id: (selectedCadastro as any).email_template_id || null,
        });
      } catch (err: any) {
        // Se já existe, atualiza com os dados completos do pré-cadastro
        if (err.message?.includes("já existe") || err.message?.includes("already exists")) {
          console.log("Montador já existe, atualizando dados...");
          try {
            await apiClient.put(`/montadores/${idMontador.trim()}`, {
              pix: selectedCadastro.pix || "",
              envio_automatico: true,
              dias_envio_mes: (selectedCadastro as any).dias_envio_mes || [16, 26],
              email_responsavel_nm: (selectedCadastro as any).email_responsavel_nm || "",
              tipo_pagamento: (selectedCadastro as any).tipo_pagamento || "novo_mundo",
              terceirizada_id: (selectedCadastro as any).terceirizada_id || null,
              email_template_id: (selectedCadastro as any).email_template_id || null,
            });
          } catch (updateErr: any) {
            console.log("Atualização do montador existente falhou (não crítico):", updateErr.message);
          }
        } else {
          throw err;
        }
      }

      // 2. Concluir o pré-cadastro com histórico
      await apiClient.post(`/pre-cadastro-montadores/${selectedCadastro.id}/concluir`, {
        id_montador: idMontador.trim(),
        numero_fornecedor: numeroFornecedor.trim(),
        re: re.trim()
      });

      toast.success("Montador criado com sucesso!");
      setShowCardDialog(false);
      fetchCadastros();
    } catch (error: any) {
      console.error("Erro ao concluir:", error);
      toast.error(error.message || "Erro ao criar montador");
    } finally {
      setConcluindo(false);
    }
  };

  const CardMontador = ({ cadastro, isConcluido = false }: { cadastro: PreCadastro; isConcluido?: boolean }) => {
    const docs = getDocumentos(cadastro);
    
    return (
      <Card 
        className={`cursor-pointer hover:shadow-md transition-shadow ${isConcluido ? 'opacity-75' : ''}`}
        onClick={() => abrirCard(cadastro)}
      >
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              {cadastro.tipo_pessoa === "PF" ? (
                <User className="h-4 w-4 text-blue-500" />
              ) : (
                <Building2 className="h-4 w-4 text-green-500" />
              )}
              <span className="font-medium">{cadastro.nome}</span>
            </div>
            <Badge variant="outline" className="text-xs">
              {cadastro.tipo_pessoa}
            </Badge>
          </div>
          
          {cadastro.filial && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground mb-1">
              <MapPin className="h-3 w-3" />
              {cadastro.filial}
            </div>
          )}
          
          {cadastro.telefone && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground mb-1">
              <Phone className="h-3 w-3" />
              {cadastro.telefone}
            </div>
          )}
          
          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2 pt-2 border-t">
            <Clock className="h-3 w-3" />
            {formatDate(cadastro.created_at)}
          </div>
          
          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
            <FileText className="h-3 w-3" />
            {docs.length} documento(s)
          </div>
          
          {isConcluido && (
            <div className="flex items-center gap-1 text-xs text-green-600 mt-2">
              <CheckCircle2 className="h-3 w-3" />
              Concluído
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Revisão de Cadastro de Montador</h1>
          <p className="text-muted-foreground">
            Revise os cadastros pendentes e conclua o processo
          </p>
        </div>
        
        <Button onClick={fetchCadastros} disabled={loading} variant="outline">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {/* Kanban */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Coluna Pendente */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <h2 className="text-lg font-semibold">Pendente</h2>
            <Badge variant="secondary">{pendentes.length}</Badge>
          </div>
          
          <div className="bg-yellow-50 rounded-lg p-4 min-h-[400px] space-y-3">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : pendentes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                <CheckCircle2 className="h-8 w-8 mb-2" />
                <p>Nenhum cadastro pendente</p>
              </div>
            ) : (
              pendentes.map(cadastro => (
                <CardMontador key={cadastro.id} cadastro={cadastro} />
              ))
            )}
          </div>
        </div>

        {/* Coluna Concluído */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <h2 className="text-lg font-semibold">Concluído</h2>
            <Badge variant="secondary">{concluidos.length}</Badge>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4 min-h-[400px] space-y-3">
            {concluidos.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                <FileText className="h-8 w-8 mb-2" />
                <p>Nenhum cadastro concluído</p>
              </div>
            ) : (
              concluidos.map(cadastro => (
                <CardMontador key={cadastro.id} cadastro={cadastro} isConcluido />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Dialog do Card de Revisão */}
      <Dialog open={showCardDialog} onOpenChange={setShowCardDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedCadastro?.tipo_pessoa === 'PF' ? (
                <User className="h-5 w-5 text-blue-500" />
              ) : (
                <Building2 className="h-5 w-5 text-green-500" />
              )}
              {selectedCadastro?.nome}
            </DialogTitle>
          </DialogHeader>

          {selectedCadastro && (
            <div className="space-y-6">
              {/* Informações do Cadastro */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <Label className="text-xs text-muted-foreground">Tipo</Label>
                  <p className="font-medium">{selectedCadastro.tipo_pessoa === 'PF' ? 'Pessoa Física' : 'Pessoa Jurídica'}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Filial</Label>
                  <p className="font-medium">{selectedCadastro.filial || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Telefone</Label>
                  <p className="font-medium">{selectedCadastro.telefone || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Email</Label>
                  <p className="font-medium">{selectedCadastro.email || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">% Montagem</Label>
                  <p className="font-medium">{selectedCadastro.percentual_montagem}%</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Auxílio Semanal</Label>
                  <p className="font-medium">R$ {selectedCadastro.auxilio_semanal?.toFixed(2)}</p>
                </div>
              </div>

              {/* Documentos */}
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Revisão de Documentos
                </h3>
                <div className="space-y-3">
                  {getDocumentos(selectedCadastro).map((doc, index) => (
                    <div 
                      key={index}
                      className={`p-4 border rounded-lg ${
                        doc.status === 'aprovado' ? 'bg-green-50 border-green-200' :
                        doc.status === 'recusado' ? 'bg-red-50 border-red-200' :
                        'bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(doc.status)}
                          <FileImage className="h-4 w-4 text-blue-500" />
                          <span className="font-medium">{doc.nome}</span>
                          {getStatusBadge(doc.status)}
                        </div>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => abrirPreviewDoc(doc.path, doc.nome)}
                            title="Visualizar"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            asChild
                            title="Download"
                          >
                            <a href={getDocUrl(doc.path) || '#'} download target="_blank">
                              <Download className="h-4 w-4" />
                            </a>
                          </Button>
                        </div>
                      </div>
                      
                      {/* Motivo da recusa (se houver) */}
                      {doc.status === 'recusado' && doc.motivo && (
                        <div className="mt-2 p-2 bg-red-100 rounded text-sm text-red-700">
                          <strong>Motivo da recusa:</strong> {doc.motivo}
                        </div>
                      )}
                      
                      {/* Botões de ação (se ainda não revisado ou recusado) */}
                      {doc.status !== 'aprovado' && (
                        <div className="flex gap-2 mt-3 pt-3 border-t">
                          <Button
                            size="sm"
                            variant="outline"
                            className="bg-green-100 hover:bg-green-200 border-green-300 text-green-700"
                            onClick={() => aprovarDocumento(doc.tipo)}
                            disabled={processandoRevisao}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Aprovar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="bg-red-100 hover:bg-red-200 border-red-300 text-red-700"
                            onClick={() => abrirRecusarDialog(doc.tipo, doc.nome)}
                            disabled={processandoRevisao}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Recusar
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                  {getDocumentos(selectedCadastro).length === 0 && (
                    <p className="text-muted-foreground text-sm">
                      Nenhum documento anexado
                    </p>
                  )}
                </div>
              </div>

              {/* Checklist */}
              <div className="space-y-4 p-4 border rounded-lg">
                <h3 className="font-semibold">Checklist de Conclusão</h3>
                
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <Checkbox 
                      id="checkMontador" 
                      checked={checkMontador}
                      onCheckedChange={(checked) => setCheckMontador(checked === true)}
                      disabled={selectedCadastro?.status === 'convertido'}
                    />
                    <Label htmlFor="checkMontador" className="cursor-pointer">
                      Montador cadastrado
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <Checkbox 
                      id="checkFornecedor" 
                      checked={checkFornecedor}
                      onCheckedChange={(checked) => setCheckFornecedor(checked === true)}
                      disabled={selectedCadastro?.status === 'convertido'}
                    />
                    <Label htmlFor="checkFornecedor" className="cursor-pointer">
                      Fornecedor cadastrado
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <Checkbox 
                      id="checkChamadoTI" 
                      checked={checkChamadoTI}
                      onCheckedChange={(checked) => setCheckChamadoTI(checked === true)}
                      disabled={selectedCadastro?.status === 'convertido'}
                    />
                    <Label htmlFor="checkChamadoTI" className="cursor-pointer">
                      Chamado TI concluído
                    </Label>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t">
                  <div>
                    <Label htmlFor="idMontador">ID Montador *</Label>
                    <Input
                      id="idMontador"
                      value={idMontador}
                      onChange={(e) => setIdMontador(e.target.value)}
                      placeholder="Ex: 4001"
                      disabled={selectedCadastro?.status === 'convertido'}
                    />
                  </div>
                  <div>
                    <Label htmlFor="numeroFornecedor">Número do Fornecedor *</Label>
                    <Input
                      id="numeroFornecedor"
                      value={numeroFornecedor}
                      onChange={(e) => setNumeroFornecedor(e.target.value)}
                      placeholder="Ex: FORN001"
                      disabled={selectedCadastro?.status === 'convertido'}
                    />
                  </div>
                  <div>
                    <Label htmlFor="re">RE *</Label>
                    <Input
                      id="re"
                      value={re}
                      onChange={(e) => setRe(e.target.value)}
                      placeholder="Ex: 12345"
                      disabled={selectedCadastro?.status === 'convertido'}
                    />
                  </div>
                </div>
              </div>

              {/* Histórico de Conclusão - apenas se já foi concluído */}
              {selectedCadastro?.status === 'convertido' && selectedCadastro?.concluido_em && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <h3 className="font-semibold mb-3 flex items-center gap-2 text-green-700">
                    <History className="h-4 w-4" />
                    Histórico de Conclusão
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Concluído por:</span>
                      <span className="font-medium">{selectedCadastro.concluido_por_nome || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Data/Hora:</span>
                      <span className="font-medium">{selectedCadastro.concluido_em ? formatDate(selectedCadastro.concluido_em) : '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">ID Montador:</span>
                      <span className="font-medium">{selectedCadastro.id_montador || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Nº Fornecedor:</span>
                      <span className="font-medium">{selectedCadastro.numero_fornecedor || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">RE:</span>
                      <span className="font-medium">{selectedCadastro.re || '-'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Botão Concluir - apenas se ainda não foi concluído */}
              {selectedCadastro?.status !== 'convertido' && (
                <div className="flex justify-end">
                  <Button 
                    onClick={handleConcluir}
                    disabled={concluindo}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {concluindo ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Processando...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Concluir
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog de Preview de Documento */}
      <Dialog open={!!previewDoc} onOpenChange={() => setPreviewDoc(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{previewDocName}</span>
              <Button variant="ghost" size="sm" onClick={() => setPreviewDoc(null)}>
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          
          {previewDoc && (
            <div className="w-full h-[70vh]">
              {previewDoc.toLowerCase().endsWith('.pdf') ? (
                <iframe 
                  src={previewDoc} 
                  className="w-full h-full border rounded"
                  title={previewDocName}
                />
              ) : (
                <img 
                  src={previewDoc} 
                  alt={previewDocName}
                  className="max-w-full max-h-full mx-auto object-contain"
                />
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog de Recusar Documento */}
      <Dialog open={showRecusarDialog} onOpenChange={setShowRecusarDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <XCircle className="h-5 w-5" />
              Recusar Documento
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Você está recusando o documento: <strong>{docRecusando?.nome}</strong>
            </p>
            
            <div>
              <Label htmlFor="motivoRecusa">Motivo da Recusa *</Label>
              <Textarea
                id="motivoRecusa"
                value={motivoRecusa}
                onChange={(e) => setMotivoRecusa(e.target.value)}
                placeholder="Descreva o motivo da recusa para que o montador saiba o que precisa corrigir..."
                rows={4}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Este motivo será exibido para o montador na tela de pré-cadastro.
              </p>
            </div>
            
            <div className="flex justify-end gap-2">
              <Button 
                variant="outline" 
                onClick={() => setShowRecusarDialog(false)}
                disabled={processandoRevisao}
              >
                Cancelar
              </Button>
              <Button 
                variant="destructive"
                onClick={recusarDocumento}
                disabled={processandoRevisao || !motivoRecusa.trim()}
              >
                {processandoRevisao ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Processando...
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 mr-2" />
                    Confirmar Recusa
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RevisaoCadastroMontador;
