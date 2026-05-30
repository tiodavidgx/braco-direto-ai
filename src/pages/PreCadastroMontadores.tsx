import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Plus, 
  User, 
  Building2, 
  FileText, 
  DollarSign, 
  CheckCircle2, 
  ChevronRight, 
  ChevronLeft,
  Upload,
  Trash2,
  Edit,
  Eye,
  Clock,
  AlertCircle,
  Search,
  UserPlus,
  XCircle,
  RefreshCw,
  AlertTriangle
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";

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
  // Campos de responsável
  responsavel_id: number | null;
  responsavel_nome: string | null;
  status: string;
  etapa_atual: number;
  observacoes: string | null;
  criado_por_nome: string | null;
  created_at: string;
  updated_at: string;
}

interface Revisor {
  id: number;
  user_id: number;
  ativo: boolean;
  nome: string;
  email: string;
  telefone: string | null;
}

interface Estatisticas {
  rascunhos: number;
  aguardando_docs: number;
  em_analise: number;
  aprovados: number;
  convertidos: number;
  rejeitados: number;
  total: number;
}

const ETAPAS = [
  { num: 1, titulo: "Tipo de Pessoa", icone: User },
  { num: 2, titulo: "Dados Pessoais", icone: FileText },
  { num: 3, titulo: "Documentos", icone: Upload },
  { num: 4, titulo: "Valores", icone: DollarSign },
  { num: 5, titulo: "Revisão", icone: CheckCircle2 },
];

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  rascunho: { label: "Rascunho", color: "bg-gray-500", icon: Clock },
  aguardando_docs: { label: "Aguardando Revisão", color: "bg-yellow-500", icon: AlertCircle },
  em_analise: { label: "Em Análise", color: "bg-blue-500", icon: Eye },
  aprovado: { label: "Aprovado", color: "bg-green-500", icon: CheckCircle2 },
  convertido: { label: "Concluído", color: "bg-purple-500", icon: UserPlus },
  rejeitado: { label: "Rejeitado", color: "bg-red-500", icon: AlertCircle },
};

// Função para limpar telefone (remove tudo que não é número)
const limparTelefone = (telefone: string): string => {
  return telefone.replace(/\D/g, '');
};

// Função para formatar telefone para exibição
const formatarTelefone = (telefone: string): string => {
  const numeros = limparTelefone(telefone);
  
  if (numeros.length <= 2) return numeros;
  if (numeros.length <= 7) return `(${numeros.slice(0, 2)}) ${numeros.slice(2)}`;
  if (numeros.length <= 11) return `(${numeros.slice(0, 2)}) ${numeros.slice(2, 7)}-${numeros.slice(7)}`;
  // Se tem código do país (55)
  if (numeros.length > 11) {
    const semPais = numeros.slice(-11);
    return `(${semPais.slice(0, 2)}) ${semPais.slice(2, 7)}-${semPais.slice(7)}`;
  }
  return telefone;
};

// Função para validar telefone
const validarTelefone = (telefone: string): { valido: boolean; mensagem?: string } => {
  const numeros = limparTelefone(telefone);
  
  if (numeros.length === 0) {
    return { valido: false, mensagem: "Telefone é obrigatório" };
  }
  
  // Aceita 10 dígitos (fixo) ou 11 dígitos (celular)
  if (numeros.length < 10 || numeros.length > 13) {
    return { valido: false, mensagem: "Telefone deve ter entre 10 e 11 dígitos (DDD + número)" };
  }
  
  // Verifica se DDD é válido (11-99)
  const ddd = parseInt(numeros.slice(-11, -9) || numeros.slice(0, 2));
  if (ddd < 11 || ddd > 99) {
    return { valido: false, mensagem: "DDD inválido" };
  }
  
  return { valido: true };
};

export default function PreCadastroMontadores() {
  const { isAdmin } = useAuth();
  const [cadastros, setCadastros] = useState<PreCadastro[]>([]);
  const [estatisticas, setEstatisticas] = useState<Estatisticas | null>(null);
  const [loading, setLoading] = useState(true);
  const [filtroStatus, setFiltroStatus] = useState<string>("todos");
  const [searchTerm, setSearchTerm] = useState("");
  const [tabAtiva, setTabAtiva] = useState<"cadastros" | "revisores">("cadastros");
  
  // Revisores state
  const [revisores, setRevisores] = useState<Revisor[]>([]);
  const [usuariosDisponiveis, setUsuariosDisponiveis] = useState<any[]>([]);
  const [loadingRevisores, setLoadingRevisores] = useState(false);
  
  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editando, setEditando] = useState<PreCadastro | null>(null);
  const [etapaAtual, setEtapaAtual] = useState(1);
  const [salvando, setSalvando] = useState(false);
  
  // Dialog converter
  const [converterDialogOpen, setConverterDialogOpen] = useState(false);
  const [cadastroParaConverter, setCadastroParaConverter] = useState<PreCadastro | null>(null);
  const [identificador, setIdentificador] = useState("");
  const [fornecedorId, setFornecedorId] = useState("");
  
  // Form state
  const [form, setForm] = useState({
    tipo_pessoa: "PF" as "PF" | "PJ",
    nome: "",
    cpf_cnpj: "",
    email: "",
    telefone: "",
    filial: "",
    cidade: "",
    endereco: "",
    banco: "",
    agencia: "",
    conta: "",
    tipo_conta: "",
    pix: "",
    percentual_montagem: "5.0",
    percentual_assistencia: "3.0",
    percentual_desmontagem: "2.0",
    auxilio_semanal: "0.00",
    observacoes: "",
    // Novos campos
    envio_automatico: false,
    dia_fechamento: "25",
    dias_envio_mes: [] as number[],
    prazo_pagamento_dias: "10",
    email_responsavel_nm: "",
    tipo_pagamento: "novo_mundo" as string,
    terceirizada_id: null as number | null,
  });

  useEffect(() => {
    carregarDados();
  }, [filtroStatus]);

  useEffect(() => {
    if (tabAtiva === "revisores" && isAdmin) {
      carregarRevisores();
    }
  }, [tabAtiva, isAdmin]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const [cadastrosRes, statsRes] = await Promise.all([
        apiClient.get<{ data: PreCadastro[] }>(`/pre-cadastro-montadores${filtroStatus !== "todos" ? `?status=${filtroStatus}` : ""}`),
        apiClient.get<Estatisticas>("/pre-cadastro-montadores/estatisticas")
      ]);
      setCadastros(cadastrosRes.data);
      setEstatisticas(statsRes);
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar pré-cadastros");
    } finally {
      setLoading(false);
    }
  };

  const carregarRevisores = async () => {
    if (!isAdmin) return;
    setLoadingRevisores(true);
    try {
      const [revisoresRes, usuariosRes] = await Promise.all([
        apiClient.get<Revisor[]>("/pre-cadastro-montadores/revisores/lista"),
        apiClient.get<any[]>("/pre-cadastro-montadores/revisores/disponiveis")
      ]);
      setRevisores(revisoresRes);
      setUsuariosDisponiveis(usuariosRes);
    } catch (error) {
      console.error("Erro ao carregar revisores:", error);
    } finally {
      setLoadingRevisores(false);
    }
  };

  const toggleRevisor = async (userId: number) => {
    try {
      await apiClient.put(`/pre-cadastro-montadores/revisores/toggle/${userId}`);
      toast.success("Revisor atualizado!");
      carregarRevisores();
    } catch (error) {
      toast.error("Erro ao atualizar revisor");
    }
  };

  const adicionarRevisor = async (userId: number) => {
    try {
      await apiClient.post(`/pre-cadastro-montadores/revisores/adicionar/${userId}`);
      toast.success("Revisor adicionado!");
      carregarRevisores();
    } catch (error) {
      toast.error("Erro ao adicionar revisor");
    }
  };

  const abrirNovoCadastro = () => {
    setEditando(null);
    setEtapaAtual(1);
    setForm({
      tipo_pessoa: "PF",
      nome: "",
      cpf_cnpj: "",
      email: "",
      telefone: "",
      filial: "",
      cidade: "",
      endereco: "",
      banco: "",
      agencia: "",
      conta: "",
      tipo_conta: "",
      pix: "",
      percentual_montagem: "5.0",
      percentual_assistencia: "3.0",
      percentual_desmontagem: "2.0",
      auxilio_semanal: "0.00",
      observacoes: "",
      envio_automatico: false,
      dia_fechamento: "25",
      dias_envio_mes: [],
      prazo_pagamento_dias: "10",
      email_responsavel_nm: "",
      tipo_pagamento: "novo_mundo",
      terceirizada_id: null,
    });
    setDialogOpen(true);
  };

  const abrirEdicao = (cadastro: PreCadastro) => {
    setEditando(cadastro);
    setEtapaAtual(cadastro.etapa_atual || 1);
    setForm({
      tipo_pessoa: cadastro.tipo_pessoa,
      nome: cadastro.nome || "",
      cpf_cnpj: cadastro.cpf_cnpj || "",
      email: cadastro.email || "",
      telefone: cadastro.telefone || "",
      filial: cadastro.filial || "",
      cidade: cadastro.cidade || "",
      endereco: cadastro.endereco || "",
      banco: cadastro.banco || "",
      agencia: cadastro.agencia || "",
      conta: cadastro.conta || "",
      tipo_conta: cadastro.tipo_conta || "",
      pix: cadastro.pix || "",
      percentual_montagem: cadastro.percentual_montagem?.toString() || "5.0",
      percentual_assistencia: cadastro.percentual_assistencia?.toString() || "5.0",
      percentual_desmontagem: cadastro.percentual_desmontagem?.toString() || "5.0",
      auxilio_semanal: cadastro.auxilio_semanal?.toString() || "100.00",
      observacoes: cadastro.observacoes || "",
      envio_automatico: (cadastro as any).envio_automatico ?? false,
      dia_fechamento: ((cadastro as any).dia_fechamento ?? 25).toString(),
      dias_envio_mes: (cadastro as any).dias_envio_mes || [],
      prazo_pagamento_dias: ((cadastro as any).prazo_pagamento_dias ?? 10).toString(),
      email_responsavel_nm: (cadastro as any).email_responsavel_nm || "",
      tipo_pagamento: (cadastro as any).tipo_pagamento || "novo_mundo",
      terceirizada_id: (cadastro as any).terceirizada_id || null,
    });
    setDialogOpen(true);
  };

  const salvarCadastro = async (avancar = false) => {
    // Só exige nome a partir da etapa 2
    if (etapaAtual >= 2 && !form.nome) {
      toast.error("Nome é obrigatório");
      return;
    }

    // Validar campos obrigatórios na etapa 2 (Dados Pessoais)
    if (etapaAtual === 2 && avancar) {
      const telefoneValidacao = validarTelefone(form.telefone);
      if (!telefoneValidacao.valido) {
        toast.error(telefoneValidacao.mensagem || "Telefone inválido");
        return;
      }
      if (!form.email) {
        toast.error("Email é obrigatório");
        return;
      }
      if (!form.filial) {
        toast.error("Filial é obrigatória");
        return;
      }
      if (!form.cidade) {
        toast.error("Cidade é obrigatória");
        return;
      }
      if (!form.email_responsavel_nm || !form.email_responsavel_nm.trim()) {
        toast.error("E-mail do Responsável Novo Mundo é obrigatório");
        return;
      }
    }

    setSalvando(true);
    try {
      // Se está na etapa 1 e vai avançar, só precisa do tipo_pessoa
      const dados = {
        ...form,
        nome: form.nome || "Rascunho - " + new Date().toLocaleString("pt-BR"),
        percentual_montagem: parseFloat(form.percentual_montagem) || 5.0,
        percentual_assistencia: parseFloat(form.percentual_assistencia) || 3.0,
        percentual_desmontagem: parseFloat(form.percentual_desmontagem) || 2.0,
        auxilio_semanal: parseFloat(form.auxilio_semanal) || 0,
        etapa_atual: avancar ? Math.min(etapaAtual + 1, 5) : etapaAtual,
      };

      if (editando) {
        await apiClient.put(`/pre-cadastro-montadores/${editando.id}`, dados);
        toast.success("Cadastro atualizado!");
      } else {
        const res = await apiClient.post<PreCadastro>("/pre-cadastro-montadores", dados);
        setEditando(res);
        toast.success("Cadastro criado!");
      }

      if (avancar && etapaAtual < 5) {
        setEtapaAtual(etapaAtual + 1);
      }

      carregarDados();
    } catch (error: any) {
      toast.error(error.message || "Erro ao salvar");
    } finally {
      setSalvando(false);
    }
  };

  const finalizarCadastro = async () => {
    if (!form.nome) {
      toast.error("Nome é obrigatório");
      return;
    }

    // Validar campos obrigatórios
    const telefoneValidacao = validarTelefone(form.telefone);
    if (!telefoneValidacao.valido) {
      toast.error(telefoneValidacao.mensagem || "Telefone inválido");
      return;
    }
    if (!form.email) {
      toast.error("Email é obrigatório");
      return;
    }
    if (!form.filial) {
      toast.error("Filial é obrigatória");
      return;
    }
    if (!form.cidade) {
      toast.error("Cidade é obrigatória");
      return;
    }

    // Validar documentos obrigatórios
    if (!editando) {
      toast.error("Salve o cadastro primeiro antes de finalizar");
      return;
    }

    // PF: Documento Pessoal, Comprovante Endereço, Comprovante Bancário
    // PJ: Comprovante Bancário, Comprovante MEI
    if (form.tipo_pessoa === "PF") {
      if (!editando.doc_documento_pessoal) {
        toast.error("Documento Pessoal é obrigatório");
        return;
      }
      if (!editando.doc_comprovante_endereco) {
        toast.error("Comprovante de Endereço é obrigatório");
        return;
      }
      if (!editando.doc_comprovante_bancario) {
        toast.error("Comprovante Bancário é obrigatório");
        return;
      }
    } else {
      // PJ - apenas Comprovante Bancário e MEI
      if (!editando.doc_comprovante_bancario) {
        toast.error("Comprovante Bancário é obrigatório");
        return;
      }
      if (!editando.doc_comprovante_mei) {
        toast.error("Comprovante MEI é obrigatório");
        return;
      }
    }

    setSalvando(true);
    try {
      const dados = {
        ...form,
        nome: form.nome,
        percentual_montagem: parseFloat(form.percentual_montagem) || 5.0,
        percentual_assistencia: parseFloat(form.percentual_assistencia) || 3.0,
        percentual_desmontagem: parseFloat(form.percentual_desmontagem) || 2.0,
        auxilio_semanal: parseFloat(form.auxilio_semanal) || 0,
        etapa_atual: 5,
        // Muda o status para aguardando_docs para aparecer no Kanban de revisão
        status: "aguardando_docs",
      };

      if (editando) {
        await apiClient.put(`/pre-cadastro-montadores/${editando.id}`, dados);
      } else {
        await apiClient.post<PreCadastro>("/pre-cadastro-montadores", dados);
      }

      toast.success("Cadastro finalizado e enviado para revisão!");
      setDialogOpen(false);
      carregarDados();
    } catch (error: any) {
      toast.error(error.message || "Erro ao finalizar");
    } finally {
      setSalvando(false);
    }
  };

  const uploadDocumento = async (tipo: string, file: File) => {
    if (!editando) {
      toast.error("Salve o cadastro primeiro antes de enviar documentos");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    // Construir URL corretamente para produção e desenvolvimento
    const getUploadUrl = () => {
      if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        return `${window.location.origin}/api/v1/pre-cadastro-montadores/${editando.id}/upload/${tipo}`;
      }
      return `http://localhost:8000/api/v1/pre-cadastro-montadores/${editando.id}/upload/${tipo}`;
    };

    try {
      const response = await fetch(
        getUploadUrl(),
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("braco_direto_token")}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Erro no upload");
      }

      const data = await response.json();
      setEditando(data.cadastro);
      toast.success("Documento enviado com sucesso!");
      carregarDados();
    } catch (error) {
      toast.error("Erro ao enviar documento");
    }
  };

  const excluirCadastro = async (id: number) => {
    if (!confirm("Tem certeza que deseja excluir este pré-cadastro?")) return;

    try {
      await apiClient.delete(`/pre-cadastro-montadores/${id}`);
      toast.success("Pré-cadastro excluído");
      carregarDados();
    } catch (error: any) {
      toast.error(error.message || "Erro ao excluir");
    }
  };

  const abrirConverter = (cadastro: PreCadastro) => {
    setCadastroParaConverter(cadastro);
    setIdentificador("");
    setFornecedorId("");
    setConverterDialogOpen(true);
  };

  const converterParaMontador = async () => {
    if (!cadastroParaConverter || !identificador || !fornecedorId) {
      toast.error("Preencha o identificador e fornecedor ID");
      return;
    }

    try {
      await apiClient.post(
        `/pre-cadastro-montadores/${cadastroParaConverter.id}/converter?identificador=${encodeURIComponent(identificador)}&fornecedor_id=${encodeURIComponent(fornecedorId)}`,
        {}
      );
      toast.success("Montador criado com sucesso!");
      setConverterDialogOpen(false);
      carregarDados();
    } catch (error: any) {
      toast.error(error.message || "Erro ao converter");
    }
  };

  const filteredCadastros = cadastros.filter(c =>
    c.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.cpf_cnpj?.includes(searchTerm)
  );

  const renderEtapa = () => {
    switch (etapaAtual) {
      case 1:
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h3 className="text-xl font-semibold mb-2">Qual o tipo de pessoa?</h3>
              <p className="text-muted-foreground">O montador irá atuar como pessoa física ou jurídica?</p>
            </div>
            
            <RadioGroup
              value={form.tipo_pessoa}
              onValueChange={(value) => setForm({ ...form, tipo_pessoa: value as "PF" | "PJ" })}
              className="grid grid-cols-2 gap-4"
            >
              <div>
                <RadioGroupItem value="PF" id="pf" className="peer sr-only" />
                <Label
                  htmlFor="pf"
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-muted bg-popover p-6 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <User className="h-12 w-12 mb-3 text-blue-500" />
                  <span className="text-lg font-semibold">Pessoa Física</span>
                  <span className="text-sm text-muted-foreground">CPF</span>
                </Label>
              </div>
              <div>
                <RadioGroupItem value="PJ" id="pj" className="peer sr-only" />
                <Label
                  htmlFor="pj"
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-muted bg-popover p-6 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Building2 className="h-12 w-12 mb-3 text-green-500" />
                  <span className="text-lg font-semibold">Pessoa Jurídica</span>
                  <span className="text-sm text-muted-foreground">CNPJ / MEI</span>
                </Label>
              </div>
            </RadioGroup>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold mb-4">
              Dados {form.tipo_pessoa === "PF" ? "Pessoais" : "da Empresa"}
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Nome e Sobrenome *</Label>
                <Input
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  placeholder="Nome e sobrenome do montador"
                />
              </div>
              
              <div>
                <Label>Telefone <span className="text-red-500">*</span></Label>
                <Input
                  value={formatarTelefone(form.telefone)}
                  onChange={(e) => {
                    // Limpa e guarda apenas números
                    const apenasNumeros = limparTelefone(e.target.value);
                    // Limita a 11 dígitos (DDD + celular)
                    const telefoneFormatado = apenasNumeros.slice(0, 11);
                    setForm({ ...form, telefone: telefoneFormatado });
                  }}
                  placeholder="(62) 99999-9999"
                  maxLength={15}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Digite apenas números. Ex: 62991234567
                </p>
              </div>
              
              <div className="col-span-2">
                <Label>Email <span className="text-red-500">*</span></Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="email@exemplo.com"
                />
              </div>
              
              <div>
                <Label>Filial <span className="text-red-500">*</span></Label>
                <Input
                  value={form.filial}
                  onChange={(e) => setForm({ ...form, filial: e.target.value })}
                  placeholder="Ex: Goiânia, Brasília"
                />
              </div>
              
              <div>
                <Label>Cidade <span className="text-red-500">*</span></Label>
                <Input
                  value={form.cidade}
                  onChange={(e) => setForm({ ...form, cidade: e.target.value })}
                  placeholder="Cidade de atuação"
                />
              </div>

              <div className="col-span-2">
                <Label>Chave PIX <span className="text-red-500">*</span></Label>
                <Input
                  value={form.pix || ""}
                  onChange={(e) => setForm({ ...form, pix: e.target.value })}
                  placeholder="CPF, e-mail, telefone ou chave aleatória (obrigatório)"
                  required
                />
              </div>

              <div className="col-span-2">
                <Label>E-mail Responsável Novo Mundo <span className="text-red-500">*</span></Label>
                <Input
                  type="email"
                  value={form.email_responsavel_nm || ""}
                  onChange={(e) => setForm({ ...form, email_responsavel_nm: e.target.value })}
                  placeholder="responsavel@novomundo.com.br"
                  required
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Receberá cópia dos relatórios enviados ao montador
                </p>
              </div>
            </div>
          </div>
        );

      case 3:
        // Verificar se há documentos recusados
        const hasDocsRecusados = editando && (
          editando.doc_documento_pessoal_status === 'recusado' ||
          editando.doc_comprovante_endereco_status === 'recusado' ||
          editando.doc_comprovante_bancario_status === 'recusado' ||
          editando.doc_comprovante_mei_status === 'recusado'
        );
        
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold mb-4">Documentos</h3>
            <p className="text-muted-foreground text-sm mb-4">
              Faça upload dos documentos necessários. Formatos aceitos: PDF, JPG, PNG
            </p>
            
            {!editando && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                <p className="text-yellow-800 text-sm">
                  ⚠️ Salve o cadastro primeiro para poder enviar documentos
                </p>
              </div>
            )}
            
            {/* Alerta geral de documentos recusados */}
            {hasDocsRecusados && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
                  <div>
                    <p className="text-red-800 font-medium">Atenção: Documentos Recusados</p>
                    <p className="text-red-700 text-sm">
                      Um ou mais documentos foram recusados na revisão. Por favor, verifique os motivos abaixo e reenvie os documentos corrigidos.
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            <div className="space-y-4">
              {/* Documento Pessoal - apenas para PF */}
              {form.tipo_pessoa === "PF" && (
                <div className={`border rounded-lg p-4 ${
                  editando?.doc_documento_pessoal_status === 'recusado' ? 'border-red-300 bg-red-50' : 
                  editando?.doc_documento_pessoal_status === 'aprovado' ? 'border-green-300 bg-green-50' : ''
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium flex items-center gap-2">
                        Documento Pessoal com Foto <span className="text-red-500">*</span>
                        {editando?.doc_documento_pessoal_status === 'aprovado' && (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                        {editando?.doc_documento_pessoal_status === 'recusado' && (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </h4>
                      <p className="text-sm text-muted-foreground">RG, CNH ou outro documento com foto</p>
                    </div>
                    {editando?.doc_documento_pessoal && editando?.doc_documento_pessoal_status !== 'recusado' ? (
                      <Badge variant="default" className={editando?.doc_documento_pessoal_status === 'aprovado' ? 'bg-green-500' : 'bg-blue-500'}>
                        <CheckCircle2 className="h-3 w-3 mr-1" /> 
                        {editando?.doc_documento_pessoal_status === 'aprovado' ? 'Aprovado' : 'Enviado'}
                      </Badge>
                    ) : (
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          className="hidden"
                          accept=".pdf,.jpg,.jpeg,.png"
                          onChange={(e) => e.target.files?.[0] && uploadDocumento("documento_pessoal", e.target.files[0])}
                          disabled={!editando}
                        />
                        <Button variant={editando?.doc_documento_pessoal_status === 'recusado' ? 'default' : 'outline'} size="sm" disabled={!editando} asChild className={editando?.doc_documento_pessoal_status === 'recusado' ? 'bg-red-500 hover:bg-red-600' : ''}>
                          <span><Upload className="h-4 w-4 mr-1" /> {editando?.doc_documento_pessoal_status === 'recusado' ? 'Reenviar' : 'Upload'}</span>
                        </Button>
                      </label>
                    )}
                  </div>
                  {/* Motivo da recusa */}
                  {editando?.doc_documento_pessoal_status === 'recusado' && editando?.doc_documento_pessoal_motivo && (
                    <div className="mt-3 p-3 bg-red-100 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">
                        <strong>Motivo da recusa:</strong> {editando.doc_documento_pessoal_motivo}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Comprovante de Endereço - apenas para PF */}
              {form.tipo_pessoa === "PF" && (
                <div className={`border rounded-lg p-4 ${
                  editando?.doc_comprovante_endereco_status === 'recusado' ? 'border-red-300 bg-red-50' : 
                  editando?.doc_comprovante_endereco_status === 'aprovado' ? 'border-green-300 bg-green-50' : ''
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium flex items-center gap-2">
                        Comprovante de Endereço <span className="text-red-500">*</span>
                        {editando?.doc_comprovante_endereco_status === 'aprovado' && (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                        {editando?.doc_comprovante_endereco_status === 'recusado' && (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </h4>
                      <p className="text-sm text-muted-foreground">Conta de luz, água ou telefone recente</p>
                    </div>
                    {editando?.doc_comprovante_endereco && editando?.doc_comprovante_endereco_status !== 'recusado' ? (
                      <Badge variant="default" className={editando?.doc_comprovante_endereco_status === 'aprovado' ? 'bg-green-500' : 'bg-blue-500'}>
                        <CheckCircle2 className="h-3 w-3 mr-1" /> 
                        {editando?.doc_comprovante_endereco_status === 'aprovado' ? 'Aprovado' : 'Enviado'}
                      </Badge>
                    ) : (
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          className="hidden"
                          accept=".pdf,.jpg,.jpeg,.png"
                          onChange={(e) => e.target.files?.[0] && uploadDocumento("comprovante_endereco", e.target.files[0])}
                          disabled={!editando}
                        />
                        <Button variant={editando?.doc_comprovante_endereco_status === 'recusado' ? 'default' : 'outline'} size="sm" disabled={!editando} asChild className={editando?.doc_comprovante_endereco_status === 'recusado' ? 'bg-red-500 hover:bg-red-600' : ''}>
                          <span><Upload className="h-4 w-4 mr-1" /> {editando?.doc_comprovante_endereco_status === 'recusado' ? 'Reenviar' : 'Upload'}</span>
                        </Button>
                      </label>
                    )}
                  </div>
                  {/* Motivo da recusa */}
                  {editando?.doc_comprovante_endereco_status === 'recusado' && editando?.doc_comprovante_endereco_motivo && (
                    <div className="mt-3 p-3 bg-red-100 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">
                        <strong>Motivo da recusa:</strong> {editando.doc_comprovante_endereco_motivo}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Comprovante Bancário */}
              <div className={`border rounded-lg p-4 ${
                editando?.doc_comprovante_bancario_status === 'recusado' ? 'border-red-300 bg-red-50' : 
                editando?.doc_comprovante_bancario_status === 'aprovado' ? 'border-green-300 bg-green-50' : ''
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium flex items-center gap-2">
                      Comprovante de Conta Bancária <span className="text-red-500">*</span>
                      {editando?.doc_comprovante_bancario_status === 'aprovado' && (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      )}
                      {editando?.doc_comprovante_bancario_status === 'recusado' && (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                    </h4>
                    <p className="text-sm text-muted-foreground">Extrato ou cartão do banco</p>
                  </div>
                  {editando?.doc_comprovante_bancario && editando?.doc_comprovante_bancario_status !== 'recusado' ? (
                    <Badge variant="default" className={editando?.doc_comprovante_bancario_status === 'aprovado' ? 'bg-green-500' : 'bg-blue-500'}>
                      <CheckCircle2 className="h-3 w-3 mr-1" /> 
                      {editando?.doc_comprovante_bancario_status === 'aprovado' ? 'Aprovado' : 'Enviado'}
                    </Badge>
                  ) : (
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => e.target.files?.[0] && uploadDocumento("comprovante_bancario", e.target.files[0])}
                        disabled={!editando}
                      />
                      <Button variant={editando?.doc_comprovante_bancario_status === 'recusado' ? 'default' : 'outline'} size="sm" disabled={!editando} asChild className={editando?.doc_comprovante_bancario_status === 'recusado' ? 'bg-red-500 hover:bg-red-600' : ''}>
                        <span><Upload className="h-4 w-4 mr-1" /> {editando?.doc_comprovante_bancario_status === 'recusado' ? 'Reenviar' : 'Upload'}</span>
                      </Button>
                    </label>
                  )}
                </div>
                {/* Motivo da recusa */}
                {editando?.doc_comprovante_bancario_status === 'recusado' && editando?.doc_comprovante_bancario_motivo && (
                  <div className="mt-3 p-3 bg-red-100 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-700">
                      <strong>Motivo da recusa:</strong> {editando.doc_comprovante_bancario_motivo}
                    </p>
                  </div>
                )}
              </div>

              {/* Comprovante MEI - apenas para PJ */}
              {form.tipo_pessoa === "PJ" && (
                <div className={`border rounded-lg p-4 ${
                  editando?.doc_comprovante_mei_status === 'recusado' ? 'border-red-300 bg-red-50' : 
                  editando?.doc_comprovante_mei_status === 'aprovado' ? 'border-green-300 bg-green-50' : ''
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium flex items-center gap-2">
                        Comprovante MEI / CNPJ <span className="text-red-500">*</span>
                        {editando?.doc_comprovante_mei_status === 'aprovado' && (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                        {editando?.doc_comprovante_mei_status === 'recusado' && (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </h4>
                      <p className="text-sm text-muted-foreground">Certificado MEI ou Cartão CNPJ</p>
                    </div>
                    {editando?.doc_comprovante_mei && editando?.doc_comprovante_mei_status !== 'recusado' ? (
                      <Badge variant="default" className={editando?.doc_comprovante_mei_status === 'aprovado' ? 'bg-green-500' : 'bg-blue-500'}>
                        <CheckCircle2 className="h-3 w-3 mr-1" /> 
                        {editando?.doc_comprovante_mei_status === 'aprovado' ? 'Aprovado' : 'Enviado'}
                      </Badge>
                    ) : (
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          className="hidden"
                          accept=".pdf,.jpg,.jpeg,.png"
                          onChange={(e) => e.target.files?.[0] && uploadDocumento("comprovante_mei", e.target.files[0])}
                          disabled={!editando}
                        />
                        <Button variant={editando?.doc_comprovante_mei_status === 'recusado' ? 'default' : 'outline'} size="sm" disabled={!editando} asChild className={editando?.doc_comprovante_mei_status === 'recusado' ? 'bg-red-500 hover:bg-red-600' : ''}>
                          <span><Upload className="h-4 w-4 mr-1" /> {editando?.doc_comprovante_mei_status === 'recusado' ? 'Reenviar' : 'Upload'}</span>
                        </Button>
                      </label>
                    )}
                  </div>
                  {/* Motivo da recusa */}
                  {editando?.doc_comprovante_mei_status === 'recusado' && editando?.doc_comprovante_mei_motivo && (
                    <div className="mt-3 p-3 bg-red-100 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">
                        <strong>Motivo da recusa:</strong> {editando.doc_comprovante_mei_motivo}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold mb-4">Valores e Comissões</h3>
            <p className="text-muted-foreground text-sm mb-4">
              Configure os percentuais de comissão negociados com o montador
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>% Comissão Montagem</Label>
                <div className="relative">
                  <Input
                    type="number"
                    step="0.5"
                    value={form.percentual_montagem}
                    onChange={(e) => setForm({ ...form, percentual_montagem: e.target.value })}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">%</span>
                </div>
              </div>
              
              <div>
                <Label>% Comissão Assistência</Label>
                <div className="relative">
                  <Input
                    type="number"
                    step="0.5"
                    value={form.percentual_assistencia}
                    onChange={(e) => setForm({ ...form, percentual_assistencia: e.target.value })}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">%</span>
                </div>
              </div>
              
              <div>
                <Label>% Comissão Desmontagem</Label>
                <div className="relative">
                  <Input
                    type="number"
                    step="0.5"
                    value={form.percentual_desmontagem}
                    onChange={(e) => setForm({ ...form, percentual_desmontagem: e.target.value })}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">%</span>
                </div>
              </div>
              
              <div>
                <Label>Auxílio Semanal (R$)</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">R$</span>
                  <Input
                    type="number"
                    step="10"
                    className="pl-10"
                    value={form.auxilio_semanal}
                    onChange={(e) => setForm({ ...form, auxilio_semanal: e.target.value })}
                  />
                </div>
              </div>
            </div>
            
            <div className="mt-4">
              <Label>Observações</Label>
              <Textarea
                value={form.observacoes}
                onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
                placeholder="Anotações sobre a negociação, acordos especiais, etc."
                rows={3}
              />
            </div>

            {/* Envio Automático */}
            <div className="border rounded-md p-3 space-y-3 mt-4">
              <div className="flex items-center justify-between">
                <Label className="font-medium">Envio Automático</Label>
                <Switch
                  checked={form.envio_automatico}
                  onCheckedChange={(c) => setForm({ ...form, envio_automatico: c })}
                />
              </div>
              {form.envio_automatico && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">Dia de Fechamento</Label>
                      <Select value={form.dia_fechamento} onValueChange={(v) => setForm({ ...form, dia_fechamento: v })}>
                        <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Array.from({length: 28}, (_, i) => i + 1).map(d => (
                            <SelectItem key={d} value={d.toString()}>Dia {d}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">Prazo Pagamento (dias)</Label>
                      <Input type="number" className="h-8 text-xs" value={form.prazo_pagamento_dias}
                        onChange={(e) => setForm({ ...form, prazo_pagamento_dias: e.target.value })} />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Dias de Envio</Label>
                    <div className="grid grid-cols-7 gap-1">
                      {Array.from({length: 28}, (_, i) => i + 1).map(d => (
                        <button key={d} type="button" onClick={() => setForm({ ...form, dias_envio_mes: form.dias_envio_mes.includes(d) ? form.dias_envio_mes.filter(x => x !== d) : [...form.dias_envio_mes, d].sort((a,b) => a-b) })}
                          className={`h-7 text-xs rounded border ${form.dias_envio_mes.includes(d) ? "bg-primary text-primary-foreground border-primary" : "bg-background hover:bg-muted border-input"}`}
                        >{d}</button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold mb-4">Revisão Final</h3>
            
            <div className="bg-muted/50 rounded-lg p-4 space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tipo:</span>
                <span className="font-medium">{form.tipo_pessoa === "PF" ? "Pessoa Física" : "Pessoa Jurídica"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nome:</span>
                <span className="font-medium">{form.nome || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Email:</span>
                <span className="font-medium">{form.email || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Telefone:</span>
                <span className="font-medium">{form.telefone ? formatarTelefone(form.telefone) : "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Filial:</span>
                <span className="font-medium">{form.filial || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Chave PIX:</span>
                <span className="font-medium">{form.pix || "-"}</span>
              </div>
              
              <div className="border-t pt-3 mt-3">
                <h4 className="font-medium mb-2">Comissões</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">Montagem:</span>
                  <span>{form.percentual_montagem}%</span>
                  <span className="text-muted-foreground">Assistência:</span>
                  <span>{form.percentual_assistencia}%</span>
                  <span className="text-muted-foreground">Desmontagem:</span>
                  <span>{form.percentual_desmontagem}%</span>
                  <span className="text-muted-foreground">Auxílio Semanal:</span>
                  <span>R$ {form.auxilio_semanal}</span>
                </div>
              </div>
              
              <div className="border-t pt-3 mt-3">
                <h4 className="font-medium mb-2">Documentos</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex items-center gap-2">
                    {editando?.doc_documento_pessoal ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-yellow-500" />
                    )}
                    <span>Documento Pessoal</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {editando?.doc_comprovante_endereco ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-yellow-500" />
                    )}
                    <span>Comprovante de Endereço</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {editando?.doc_comprovante_bancario ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-yellow-500" />
                    )}
                    <span>Comprovante Bancário</span>
                  </div>
                  {form.tipo_pessoa === "PJ" && (
                    <div className="flex items-center gap-2">
                      {editando?.doc_comprovante_mei ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-yellow-500" />
                      )}
                      <span>Comprovante MEI</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pré-Cadastro de Montadores</h1>
          <p className="text-muted-foreground">Onboarding de novos montadores</p>
        </div>
        <Button onClick={abrirNovoCadastro}>
          <Plus className="h-4 w-4 mr-2" />
          Novo Cadastro
        </Button>
      </div>

      {/* Estatísticas */}
      {estatisticas && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus("rascunho")}>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-gray-600">{estatisticas.rascunhos}</div>
              <div className="text-sm text-muted-foreground">Rascunhos</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus("aguardando_docs")}>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-yellow-600">{estatisticas.aguardando_docs}</div>
              <div className="text-sm text-muted-foreground">Aguardando Revisão</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus("em_analise")}>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-blue-600">{estatisticas.em_analise}</div>
              <div className="text-sm text-muted-foreground">Em Análise</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus("aprovado")}>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-green-600">{estatisticas.aprovados}</div>
              <div className="text-sm text-muted-foreground">Aprovados</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus("convertido")}>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-purple-600">{estatisticas.convertidos}</div>
              <div className="text-sm text-muted-foreground">Concluídos</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus("todos")}>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{estatisticas.total}</div>
              <div className="text-sm text-muted-foreground">Total</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs para Admin */}
      {isAdmin && (
        <div className="flex gap-2 border-b pb-2">
          <Button
            variant={tabAtiva === "cadastros" ? "default" : "outline"}
            onClick={() => setTabAtiva("cadastros")}
          >
            <FileText className="h-4 w-4 mr-2" />
            Pré-Cadastros
          </Button>
          <Button
            variant={tabAtiva === "revisores" ? "default" : "outline"}
            onClick={() => setTabAtiva("revisores")}
          >
            <User className="h-4 w-4 mr-2" />
            Configurar Revisores
          </Button>
        </div>
      )}

      {/* Tab de Revisores (apenas admin) */}
      {isAdmin && tabAtiva === "revisores" && (
        <Card>
          <CardHeader>
            <CardTitle>Revisores de Pré-Cadastro</CardTitle>
            <CardDescription>
              Defina quais usuários podem receber cards para revisão. 
              Os cards são distribuídos aleatoriamente entre os revisores ativos.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingRevisores ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <div className="space-y-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Usuário</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Telefone</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usuariosDisponiveis.map((usuario) => {
                      const revisor = revisores.find(r => r.user_id === usuario.id);
                      const isAtivo = revisor?.ativo ?? false;
                      
                      return (
                        <TableRow key={usuario.id}>
                          <TableCell className="font-medium">
                            {usuario.nome}
                            {usuario.role === "admin" && (
                              <Badge variant="outline" className="ml-2">Admin</Badge>
                            )}
                          </TableCell>
                          <TableCell>{usuario.email}</TableCell>
                          <TableCell>
                            {usuario.telefone || (
                              <span className="text-yellow-600 flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                Sem telefone
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            {revisor ? (
                              <Badge className={isAtivo ? "bg-green-500" : "bg-gray-400"}>
                                {isAtivo ? "Ativo" : "Inativo"}
                              </Badge>
                            ) : (
                              <Badge variant="outline">Não configurado</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            {revisor ? (
                              <Button
                                variant={isAtivo ? "destructive" : "default"}
                                size="sm"
                                onClick={() => toggleRevisor(usuario.id)}
                              >
                                {isAtivo ? "Desativar" : "Ativar"}
                              </Button>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => adicionarRevisor(usuario.id)}
                              >
                                <Plus className="h-4 w-4 mr-1" />
                                Adicionar
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>Como funciona:</strong> Quando um pré-cadastro é enviado para revisão, 
                    o sistema sorteia aleatoriamente um dos revisores ativos para ser o responsável. 
                    Esse revisor receberá uma notificação por WhatsApp (se tiver telefone cadastrado).
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Filtros e Lista - só mostra se não estiver na tab de revisores */}
      {(tabAtiva === "cadastros" || !isAdmin) && (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Lista de Pré-Cadastros</CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nome ou CPF/CNPJ"
                  className="pl-9 w-64"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <Select value={filtroStatus} onValueChange={setFiltroStatus}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos</SelectItem>
                  <SelectItem value="rascunho">Rascunhos</SelectItem>
                  <SelectItem value="aguardando_docs">Aguardando Revisão</SelectItem>
                  <SelectItem value="em_analise">Em Análise</SelectItem>
                  <SelectItem value="aprovado">Aprovados</SelectItem>
                  <SelectItem value="convertido">Concluídos</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Carregando...</div>
          ) : filteredCadastros.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Nenhum pré-cadastro encontrado
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>CPF/CNPJ</TableHead>
                  <TableHead>Filial</TableHead>
                  <TableHead>Etapa</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Responsável</TableHead>
                  <TableHead>Atualizado</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCadastros.map((cadastro) => {
                  const statusConfig = STATUS_CONFIG[cadastro.status] || STATUS_CONFIG.rascunho;
                  const StatusIcon = statusConfig.icon;
                  
                  return (
                    <TableRow key={cadastro.id}>
                      <TableCell className="font-medium">{cadastro.nome}</TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {cadastro.tipo_pessoa === "PF" ? "Pessoa Física" : "Pessoa Jurídica"}
                        </Badge>
                      </TableCell>
                      <TableCell>{cadastro.cpf_cnpj || "-"}</TableCell>
                      <TableCell>{cadastro.filial || "-"}</TableCell>
                      <TableCell>
                        <span className="text-sm">{cadastro.etapa_atual}/5</span>
                      </TableCell>
                      <TableCell>
                        <Badge className={`${statusConfig.color} text-white`}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {statusConfig.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {cadastro.responsavel_nome ? (
                          <div className="flex items-center gap-1">
                            <User className="h-3 w-3 text-blue-500" />
                            <span className="text-sm font-medium">{cadastro.responsavel_nome}</span>
                          </div>
                        ) : (
                          <span className="text-sm text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(cadastro.updated_at).toLocaleDateString("pt-BR")}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {cadastro.status !== "concluido" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => abrirEdicao(cadastro)}
                              title="Editar"
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          )}
                          
                          {isAdmin && (cadastro.status === "aprovado" || cadastro.status === "em_analise") && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => abrirConverter(cadastro)}
                              title="Converter em Montador"
                              className="text-green-600 hover:text-green-700"
                            >
                              <UserPlus className="h-4 w-4" />
                            </Button>
                          )}
                          
                          {cadastro.status !== "convertido" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => excluirCadastro(cadastro.id)}
                              title="Excluir"
                              className="text-red-600 hover:text-red-700"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      )}

      {/* Dialog de Cadastro/Edição */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editando ? `Editando: ${editando.nome}` : "Novo Pré-Cadastro de Montador"}
            </DialogTitle>
            <DialogDescription>
              Preencha as informações do montador. Você pode salvar e continuar depois.
            </DialogDescription>
          </DialogHeader>

          {/* Progress Steps */}
          <div className="flex items-center justify-between mb-6 px-2">
            {ETAPAS.map((etapa, index) => {
              const EtapaIcon = etapa.icone;
              const isActive = etapaAtual === etapa.num;
              const isCompleted = etapaAtual > etapa.num;
              
              return (
                <div key={etapa.num} className="flex items-center">
                  <div
                    className={`flex flex-col items-center cursor-pointer ${
                      isActive ? "text-primary" : isCompleted ? "text-green-500" : "text-muted-foreground"
                    }`}
                    onClick={() => setEtapaAtual(etapa.num)}
                  >
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                        isActive
                          ? "border-primary bg-primary/10"
                          : isCompleted
                          ? "border-green-500 bg-green-500/10"
                          : "border-muted"
                      }`}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="h-5 w-5" />
                      ) : (
                        <EtapaIcon className="h-5 w-5" />
                      )}
                    </div>
                    <span className="text-xs mt-1 hidden sm:block">{etapa.titulo}</span>
                  </div>
                  {index < ETAPAS.length - 1 && (
                    <div
                      className={`w-8 h-0.5 mx-1 ${
                        etapaAtual > etapa.num ? "bg-green-500" : "bg-muted"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Conteúdo da Etapa */}
          <div className="min-h-[300px]">
            {renderEtapa()}
          </div>

          <DialogFooter className="flex items-center justify-between sm:justify-between">
            <div className="flex gap-2">
              {etapaAtual > 1 && (
                <Button variant="outline" onClick={() => setEtapaAtual(etapaAtual - 1)}>
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Anterior
                </Button>
              )}
            </div>
            
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => salvarCadastro(false)} disabled={salvando}>
                Salvar Rascunho
              </Button>
              
              {etapaAtual < 5 ? (
                <Button onClick={() => salvarCadastro(true)} disabled={salvando}>
                  Salvar e Avançar
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              ) : (
                <Button onClick={finalizarCadastro} disabled={salvando}>
                  Enviar para Revisão
                  <CheckCircle2 className="h-4 w-4 ml-1" />
                </Button>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog de Conversão */}
      <Dialog open={converterDialogOpen} onOpenChange={setConverterDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Converter em Montador</DialogTitle>
            <DialogDescription>
              Preencha o identificador e fornecedor ID para criar o montador no sistema.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <Label>Nome do Montador</Label>
              <Input value={cadastroParaConverter?.nome || ""} disabled />
            </div>
            
            <div>
              <Label>Identificador *</Label>
              <Input
                value={identificador}
                onChange={(e) => setIdentificador(e.target.value)}
                placeholder="Ex: 4001"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Código único do montador no sistema
              </p>
            </div>
            
            <div>
              <Label>Fornecedor ID *</Label>
              <Input
                value={fornecedorId}
                onChange={(e) => setFornecedorId(e.target.value)}
                placeholder="Ex: MONT001"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Código do fornecedor para integração
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setConverterDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={converterParaMontador}>
              <UserPlus className="h-4 w-4 mr-2" />
              Criar Montador
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
