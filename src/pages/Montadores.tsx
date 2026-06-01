import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Plus, Mail, Phone, Percent, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { montadoresService } from "@/services/montadores.service";
import { blacklistService, BoletimBlacklistItem } from "@/services/blacklist.service";
import { apiClient } from "@/services/api";
import { Montador } from "@/types/montador";
import { useAuth } from "@/contexts/AuthContext";

export default function Montadores() {
  const { isAdmin } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [blacklistItems, setBlacklistItems] = useState<BoletimBlacklistItem[]>([]);
  const [montadorSelecionado, setMontadorSelecionado] = useState<number | null>(null);
  const [numerosBoletim, setNumerosBoletim] = useState("");
  const [motivo, setMotivo] = useState("");
  const [searchBlacklist, setSearchBlacklist] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [montadores, setMontadores] = useState<Montador[]>([]);
  const [loading, setLoading] = useState(true);
  const [montadorEditando, setMontadorEditando] = useState<Montador | null>(null);
  
  // Form states
  const [formNome, setFormNome] = useState("");
  const [formIdentificador, setFormIdentificador] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formEmailsAdicionais, setFormEmailsAdicionais] = useState("");
  const [formFornecedorId, setFormFornecedorId] = useState("");
  const [formPercentualMontagem, setFormPercentualMontagem] = useState("5.0");
  const [formPercentualAssistencia, setFormPercentualAssistencia] = useState("5.0");
  const [formPercentualDesmontagem, setFormPercentualDesmontagem] = useState("5.0");
  const [formAuxilioSemanal, setFormAuxilioSemanal] = useState("100.00");
  const [formRegraEnvio, setFormRegraEnvio] = useState("Nenhuma");
  const [formDiasEnvio, setFormDiasEnvio] = useState("");
  const [formTempoVencimento, setFormTempoVencimento] = useState("10");
  const [formFilial, setFormFilial] = useState("");
  const [formCidade, setFormCidade] = useState("");
  const [formTelefone, setFormTelefone] = useState("");
  const [formPix, setFormPix] = useState("");
  const [formAtivo, setFormAtivo] = useState(true);
  const [formDiaEnvio1, setFormDiaEnvio1] = useState("");
  const [formDiaEnvio2, setFormDiaEnvio2] = useState("");
  // Novos campos - Envio Automático
  const [formEnvioAutomatico, setFormEnvioAutomatico] = useState(true);
  const [formDiaFechamento, setFormDiaFechamento] = useState("25");
  const [formDiasEnvioMes, setFormDiasEnvioMes] = useState<number[]>([16, 26]);
  const [formPrazoPagamento, setFormPrazoPagamento] = useState("10");
  const [formEmailResponsavelNM, setFormEmailResponsavelNM] = useState("");
  // Novos campos - Terceirizada
  const [formTipoPagamento, setFormTipoPagamento] = useState("novo_mundo");
  const [formTerceirizadaId, setFormTerceirizadaId] = useState<number | null>(null);
  const [terceirizadasLista, setTerceirizadasLista] = useState<any[]>([]);
  // Template de email
  const [emailTemplates, setEmailTemplates] = useState<any[]>([]);
  const [formEmailTemplateId, setFormEmailTemplateId] = useState<number | null>(null);

  useEffect(() => {
    carregarBlacklist();
    carregarMontadores();
    carregarTerceirizadas();
    carregarEmailTemplates();
  }, []);

  const carregarTerceirizadas = async () => {
    try {
      const data = await apiClient.get<any[]>("/terceirizadas?ativo=true");
      setTerceirizadasLista(data || []);
    } catch (error) {
      console.error("Erro ao carregar terceirizadas:", error);
    }
  };

  const carregarEmailTemplates = async () => {
    try {
      const res = await apiClient.get<{ data: any[] }>("/email-templates?tipo=montador&ativo=true");
      setEmailTemplates(res.data || []);
    } catch (error) {
      console.error("Erro ao carregar templates de email:", error);
    }
  };

  const carregarMontadores = async () => {
    try {
      setLoading(true);
      const response = await montadoresService.getAll({ limit: 1000 });
      setMontadores(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar montadores:", error);
      toast.error("Erro ao carregar montadores");
    } finally {
      setLoading(false);
    }
  };

  const filteredMontadores = montadores.filter((m) =>
    m.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const carregarBlacklist = async () => {
    try {
      const data = await blacklistService.getAllBoletins();
      setBlacklistItems(data);
    } catch (error) {
      console.error("Erro ao carregar blacklist:", error);
      toast.error("Erro ao carregar blacklist");
    }
  };

  const adicionarNaBlacklist = async () => {
    if (!montadorSelecionado || !numerosBoletim.trim()) {
      toast.error("Selecione um montador e insira os números dos boletins");
      return;
    }

    const numerosArray = numerosBoletim.split(",").map(n => n.trim()).filter(n => n);

    try {
      for (const numero of numerosArray) {
        try {
          await blacklistService.addBoletim({
            montador_id: montadorSelecionado,
            boletim: numero,
            motivo: motivo || undefined,
          });
          toast.success(`Boletim ${numero} adicionado à blacklist`);
        } catch (error: any) {
          toast.error(`${numero}: ${error.message || 'Erro ao adicionar'}`);
        }
      }

      setNumerosBoletim("");
      setMotivo("");
      setMontadorSelecionado(null);
      carregarBlacklist();
    } catch (error) {
      toast.error("Erro ao adicionar à blacklist");
      console.error(error);
    }
  };

  const removerDaBlacklist = async (id: number, numero: string) => {
    try {
      await blacklistService.removeBoletim(id);
      toast.success(`Boletim ${numero} removido da blacklist`);
      carregarBlacklist();
    } catch (error: any) {
      toast.error(error.message || "Erro ao remover da blacklist");
      console.error(error);
    }
  };

  const blacklistFiltrada = blacklistItems.filter(item =>
    item.montador_nome?.toLowerCase().includes(searchBlacklist.toLowerCase()) ||
    item.boletim?.toLowerCase().includes(searchBlacklist.toLowerCase()) ||
    item.motivo?.toLowerCase().includes(searchBlacklist.toLowerCase())
  );

  const adicionarMontador = async () => {
    if (!formNome || !formIdentificador || !formEmail || !formFornecedorId) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }
    if (!formPix || !formPix.trim()) {
      toast.error("PIX é obrigatório");
      return;
    }
    if (!formEmailResponsavelNM || !formEmailResponsavelNM.trim()) {
      toast.error("E-mail do Responsável Novo Mundo é obrigatório");
      return;
    }

    try {
      await montadoresService.create({
        nome: formNome,
        identificador: formIdentificador,
        email: formEmail,
        fornecedor_id: formFornecedorId,
        percentual_montagem: parseFloat(formPercentualMontagem) / 100,
        percentual_assistencia: parseFloat(formPercentualAssistencia) / 100,
        percentual_desmontagem: parseFloat(formPercentualDesmontagem) / 100,
        auxilio_semanal: parseFloat(formAuxilioSemanal),
        regra_envio: formRegraEnvio,
        dias_envio: formDiasEnvio,
        emails_adicionais: formEmailsAdicionais || null,
        tempo_vencimento_dias: parseInt(formTempoVencimento),
        filial: formFilial || null,
        cidade: formCidade || null,
        pix: formPix,
        dia_envio_1: formDiaEnvio1 ? parseInt(formDiaEnvio1) : null,
        dia_envio_2: formDiaEnvio2 ? parseInt(formDiaEnvio2) : null,
        envio_automatico: formEnvioAutomatico,
        dia_fechamento: parseInt(formDiaFechamento) || 25,
        dias_envio_mes: formDiasEnvioMes,
        prazo_pagamento_dias: parseInt(formPrazoPagamento) || 10,
        email_responsavel_nm: formEmailResponsavelNM || null,
        tipo_pagamento: formTipoPagamento,
        terceirizada_id: formTerceirizadaId,
        email_template_id: formEmailTemplateId,
      });

      toast.success("Montador adicionado com sucesso!");
      setDialogOpen(false);
      // Limpar form
      setFormNome("");
      setFormIdentificador("");
      setFormEmail("");
      setFormEmailsAdicionais("");
      setFormFornecedorId("");
      setFormPercentualMontagem("5.0");
      setFormPercentualAssistencia("5.0");
      setFormPercentualDesmontagem("5.0");
      setFormAuxilioSemanal("100.00");
      setFormRegraEnvio("Nenhuma");
      setFormDiasEnvio("");
      setFormTempoVencimento("10");
      setFormFilial("");
      setFormCidade("");
      setFormDiaEnvio1("");
      setFormDiaEnvio2("");
      setFormEnvioAutomatico(true);
      setFormDiaFechamento("25");
      setFormDiasEnvioMes([16, 26]);
      setFormPrazoPagamento("10");
      setFormEmailResponsavelNM("");
      setFormTipoPagamento("novo_mundo");
      setFormTerceirizadaId(null);
      setFormEmailTemplateId(null);
      // Recarregar lista
      carregarMontadores();
    } catch (error: any) {
      toast.error(error.message || "Erro ao adicionar montador");
      console.error(error);
    }
  };

  const abrirEdicao = (montador: Montador) => {
    setMontadorEditando(montador);
    setFormNome(montador.nome);
    setFormIdentificador(montador.identificador);
    setFormEmail(montador.email);
    setFormEmailsAdicionais(montador.emails_adicionais || "");
    setFormFornecedorId(montador.fornecedor_id);
    setFormPercentualMontagem(((montador.percentual_montagem || 0.05) * 100).toString());
    setFormPercentualAssistencia(((montador.percentual_assistencia || 0.05) * 100).toString());
    setFormPercentualDesmontagem(((montador.percentual_desmontagem || 0.05) * 100).toString());
    setFormAuxilioSemanal((montador.auxilio_semanal ?? 100).toString());
    setFormRegraEnvio(montador.regra_envio || "Nenhuma");
    setFormDiasEnvio(montador.dias_envio || "");
    setFormTempoVencimento(montador.tempo_vencimento_dias?.toString() || "10");
    setFormFilial(montador.filial || "");
    setFormCidade(montador.cidade || "");
    setFormTelefone(montador.telefone || "");
    setFormPix(montador.pix || "");
    setFormAtivo(montador.ativo ?? true);
    setFormDiaEnvio1(montador.dia_envio_1?.toString() || "");
    setFormDiaEnvio2(montador.dia_envio_2?.toString() || "");
    setFormEnvioAutomatico(true);
    setFormDiaFechamento((montador.dia_fechamento ?? 25).toString());
    setFormDiasEnvioMes(montador.dias_envio_mes?.length ? montador.dias_envio_mes : [16, 26]);
    setFormPrazoPagamento((montador.prazo_pagamento_dias ?? 10).toString());
    setFormEmailResponsavelNM(montador.email_responsavel_nm || "");
    setFormTipoPagamento(montador.tipo_pagamento || "novo_mundo");
    setFormTerceirizadaId(montador.terceirizada_id || null);
    setFormEmailTemplateId((montador as any).email_template_id || null);
    setEditDialogOpen(true);
  };

  const limparForm = () => {
    setFormNome("");
    setFormIdentificador("");
    setFormEmail("");
    setFormEmailsAdicionais("");
    setFormFornecedorId("");
    setFormPercentualMontagem("5.0");
    setFormPercentualAssistencia("5.0");
    setFormPercentualDesmontagem("5.0");
    setFormAuxilioSemanal("100.00");
    setFormRegraEnvio("Nenhuma");
    setFormDiasEnvio("");
    setFormTempoVencimento("10");
    setFormFilial("");
    setFormCidade("");
    setFormTelefone("");
    setFormPix("");
    setFormAtivo(true);
    setFormDiaEnvio1("");
    setFormDiaEnvio2("");
    setFormEmailTemplateId(null);
    setMontadorEditando(null);
  };

  const editarMontador = async () => {
    if (!montadorEditando || !formNome || !formIdentificador || !formEmail || !formFornecedorId) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }

    try {
      await montadoresService.update(montadorEditando.id, {
        nome: formNome,
        identificador: formIdentificador,
        email: formEmail,
        fornecedor_id: formFornecedorId,
        emails_adicionais: formEmailsAdicionais || null,
        percentual_montagem: parseFloat(formPercentualMontagem) / 100,
        percentual_assistencia: parseFloat(formPercentualAssistencia) / 100,
        percentual_desmontagem: parseFloat(formPercentualDesmontagem) / 100,
        auxilio_semanal: parseFloat(formAuxilioSemanal),
        regra_envio: formRegraEnvio,
        dias_envio: formDiasEnvio,
        tempo_vencimento_dias: parseInt(formTempoVencimento),
        filial: formFilial || null,
        cidade: formCidade || null,
        telefone: formTelefone || null,
        pix: formPix || null,
        ativo: formAtivo,
        dia_envio_1: formDiaEnvio1 ? parseInt(formDiaEnvio1) : null,
        dia_envio_2: formDiaEnvio2 ? parseInt(formDiaEnvio2) : null,
        envio_automatico: formEnvioAutomatico,
        dia_fechamento: parseInt(formDiaFechamento) || 25,
        dias_envio_mes: formDiasEnvioMes,
        prazo_pagamento_dias: parseInt(formPrazoPagamento) || 10,
        email_responsavel_nm: formEmailResponsavelNM || null,
        tipo_pagamento: formTipoPagamento,
        terceirizada_id: formTerceirizadaId,
        email_template_id: formEmailTemplateId,
      });

      toast.success("Montador atualizado com sucesso!");
      setEditDialogOpen(false);
      limparForm();
      carregarMontadores();
    } catch (error) {
      toast.error("Erro ao atualizar montador");
      console.error(error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Montadores</h1>
          <p className="text-muted-foreground">Gerenciar profissionais de montagem</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) limparForm();
        }}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Novo Montador
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Adicionar Novo Montador</DialogTitle>
              <DialogDescription>
                Preencha os dados do profissional de montagem
              </DialogDescription>
            </DialogHeader>
            
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="nome">Nome Completo *</Label>
                <Input
                  id="nome"
                  value={formNome}
                  onChange={(e) => setFormNome(e.target.value)}
                  placeholder="João da Silva"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="identificador">Identificador do Montador *</Label>
                <Input
                  id="identificador"
                  value={formIdentificador}
                  onChange={(e) => setFormIdentificador(e.target.value)}
                  placeholder="MONT001"
                />
                <p className="text-xs text-muted-foreground">
                  ID único do montador no sistema
                </p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="fornecedor">Número do Fornecedor *</Label>
                <Input
                  id="fornecedor"
                  value={formFornecedorId}
                  onChange={(e) => setFormFornecedorId(e.target.value)}
                  placeholder="FOR123"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="filial">Filial Montadora</Label>
                  <Input
                    id="filial"
                    value={formFilial}
                    onChange={(e) => setFormFilial(e.target.value)}
                    placeholder="Nome da filial"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="cidade">Cidade</Label>
                  <Input
                    id="cidade"
                    value={formCidade}
                    onChange={(e) => setFormCidade(e.target.value)}
                    placeholder="São Paulo"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="email">E-mail Principal *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="montador@email.com"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="pix">Chave PIX *</Label>
                <Input
                  id="pix"
                  value={formPix}
                  onChange={(e) => setFormPix(e.target.value)}
                  placeholder="CPF, e-mail, telefone ou chave aleatória (obrigatório)"
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="emails-adicionais">E-mails Adicionais</Label>
                <Input
                  id="emails-adicionais"
                  value={formEmailsAdicionais}
                  onChange={(e) => setFormEmailsAdicionais(e.target.value)}
                  placeholder="email2@empresa.com, email3@empresa.com"
                />
                <p className="text-xs text-muted-foreground">
                  Separe múltiplos emails por vírgula
                </p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="email-responsavel-nm">E-mail Responsável Novo Mundo <span className="text-red-500">*</span></Label>
                <Input
                  id="email-responsavel-nm"
                  type="email"
                  value={formEmailResponsavelNM}
                  onChange={(e) => setFormEmailResponsavelNM(e.target.value)}
                  placeholder="responsavel@novomundo.com.br"
                />
                <p className="text-xs text-muted-foreground">
                  Receberá cópia dos relatórios enviados
                </p>
              </div>

              <div className="grid gap-2">
                <Label>Pagamento por</Label>
                <Select value={formTipoPagamento} onValueChange={setFormTipoPagamento}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="novo_mundo">Novo Mundo</SelectItem>
                    <SelectItem value="terceirizada">Terceirizada</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formTipoPagamento === "terceirizada" && (
                <div className="grid gap-2">
                  <Label>Terceirizada</Label>
                  <Select
                    value={formTerceirizadaId?.toString() || ""}
                    onValueChange={(v) => setFormTerceirizadaId(v ? parseInt(v) : null)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione..." />
                    </SelectTrigger>
                    <SelectContent>
                      {terceirizadasLista.map((t: any) => (
                        <SelectItem key={t.id} value={t.id.toString()}>{t.nome}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="grid grid-cols-3 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="comissao-montagem">% Montagem</Label>
                  <Input
                    id="comissao-montagem"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formPercentualMontagem}
                    onChange={(e) => setFormPercentualMontagem(e.target.value)}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="comissao-assistencia">% Assistência</Label>
                  <Input
                    id="comissao-assistencia"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formPercentualAssistencia}
                    onChange={(e) => setFormPercentualAssistencia(e.target.value)}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="comissao-desmontagem">% Desmontagem</Label>
                  <Input
                    id="comissao-desmontagem"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formPercentualDesmontagem}
                    onChange={(e) => setFormPercentualDesmontagem(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="auxilio">Auxílio Semanal (R$)</Label>
                <Input
                    id="auxilio"
                    type="number"
                    step="10"
                    min="0"
                    value={formAuxilioSemanal}
                    onChange={(e) => setFormAuxilioSemanal(e.target.value)}
                  />
              </div>

              {/* Envio Automático — sempre ativo */}
              <div className="border rounded-md p-3 space-y-3">
                <Label className="font-medium">Envio Automático</Label>
                <div className="grid gap-1">
                    <Label className="text-xs">Dias de Envio (selecione um ou mais)</Label>
                    <div className="grid grid-cols-7 gap-1">
                      {Array.from({length: 28}, (_, i) => i + 1).map(d => (
                        <button
                          key={d}
                          type="button"
                          onClick={() => {
                            if (!isAdmin) { toast.error("Solicite para um administrador a alteração da data de envio"); return; }
                            setFormDiasEnvioMes(prev =>
                              prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d].sort((a,b) => a-b)
                            );
                          }}
                          className={`h-7 text-xs rounded border transition-colors ${
                            formDiasEnvioMes.includes(d)
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-background hover:bg-muted border-input"
                          }`}
                        >
                          {d}
                        </button>
                      ))}
                    </div>
                    {formDiasEnvioMes.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Selecionados: {formDiasEnvioMes.join(", ")}
                      </p>
                    )}
                
                {/* Template de Email */}
                <div>
                  <Label className="text-xs">Template de Email</Label>
                  <Select 
                    value={formEmailTemplateId?.toString() || "__default__"} 
                    onValueChange={(v) => setFormEmailTemplateId(v === "__default__" ? null : parseInt(v))}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Template padrão" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__default__">Padrão Montador</SelectItem>
                      {emailTemplates.map((t: any) => (
                        <SelectItem key={t.id} value={t.id.toString()}>
                          {t.nome} {t.is_default ? "(padrão)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              </div>

            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={adicionarMontador}>
                Adicionar Montador
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="lista" className="space-y-6">
        <TabsList>
          <TabsTrigger value="lista">Lista de Montadores</TabsTrigger>
          <TabsTrigger value="blacklist">
            <ShieldAlert className="h-4 w-4 mr-2" />
            Blacklist de Boletins
          </TabsTrigger>
        </TabsList>

        <TabsContent value="lista">
          <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar montadores..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Identificador</TableHead>
                <TableHead>Contato</TableHead>
                <TableHead>% Mont</TableHead>
                <TableHead>% Assist</TableHead>
                <TableHead>% Desm</TableHead>
                <TableHead>Auxílio</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMontadores.map((montador) => (
                <TableRow key={montador.id}>
                  <TableCell className="font-medium">{montador.nome}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{montador.identificador}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{montador.email}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Phone className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{montador.telefone}</span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="font-medium">{((montador.percentual_montagem || 0) * 100).toFixed(1)}%</span>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="font-medium">{((montador.percentual_assistencia || 0) * 100).toFixed(1)}%</span>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="font-medium">{((montador.percentual_desmontagem || 0) * 100).toFixed(1)}%</span>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">
                      R$ {montador.auxilio_semanal.toFixed(2)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={montador.ativo ? "default" : "secondary"}
                      className={
                        montador.ativo ? "bg-success text-success-foreground" : ""
                      }
                    >
                      {montador.ativo ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => abrirEdicao(montador)}>
                      Editar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Dialog de Edição */}
          <Dialog open={editDialogOpen} onOpenChange={(open) => {
            setEditDialogOpen(open);
            if (!open) limparForm();
          }}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Editar Montador</DialogTitle>
                <DialogDescription>
                  Atualize os dados do montador
                </DialogDescription>
              </DialogHeader>
              
              <div className="grid gap-4 py-4">
                {/* Switch Ativo/Inativo */}
                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="space-y-0.5">
                    <Label htmlFor="edit-ativo">Status do Montador</Label>
                    <p className="text-xs text-muted-foreground">
                      {formAtivo ? "Montador ativo no sistema" : "Montador desativado"}
                    </p>
                  </div>
                  <Switch
                    id="edit-ativo"
                    checked={formAtivo}
                    onCheckedChange={setFormAtivo}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-nome">Nome *</Label>
                  <Input
                    id="edit-nome"
                    value={formNome}
                    onChange={(e) => setFormNome(e.target.value)}
                    placeholder="Nome do montador"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-identificador">Identificador *</Label>
                  <Input
                    id="edit-identificador"
                    value={formIdentificador}
                    onChange={(e) => setFormIdentificador(e.target.value)}
                    placeholder="ID único do montador"
                  />
                  <p className="text-xs text-muted-foreground">
                    Atenção: alterar o identificador pode afetar relatórios já enviados
                  </p>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-telefone">Telefone</Label>
                  <Input
                    id="edit-telefone"
                    type="tel"
                    value={formTelefone}
                    onChange={(e) => setFormTelefone(e.target.value)}
                    placeholder="(11) 99999-9999"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-pix">Chave PIX *</Label>
                  <Input
                    id="edit-pix"
                    value={formPix}
                    onChange={(e) => setFormPix(e.target.value)}
                    placeholder="CPF, e-mail, telefone ou chave aleatória (obrigatório)"
                    required
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-email">E-mail Principal *</Label>
                  <Input
                    id="edit-email"
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    placeholder="contato@montador.com"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-emails-adicionais">E-mails Adicionais</Label>
                  <Input
                    id="edit-emails-adicionais"
                    value={formEmailsAdicionais}
                    onChange={(e) => setFormEmailsAdicionais(e.target.value)}
                    placeholder="email2@montador.com, email3@montador.com"
                  />
                  <p className="text-xs text-muted-foreground">
                    Separe múltiplos emails por vírgula
                  </p>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-email-responsavel-nm">E-mail Responsável Novo Mundo <span className="text-red-500">*</span></Label>
                  <Input
                    id="edit-email-responsavel-nm"
                    type="email"
                    value={formEmailResponsavelNM}
                    onChange={(e) => setFormEmailResponsavelNM(e.target.value)}
                    placeholder="responsavel@novomundo.com.br"
                  />
                </div>

                <div className="grid gap-2">
                  <Label>Pagamento por</Label>
                  <Select value={formTipoPagamento} onValueChange={setFormTipoPagamento}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="novo_mundo">Novo Mundo</SelectItem>
                      <SelectItem value="terceirizada">Terceirizada</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {formTipoPagamento === "terceirizada" && (
                  <div className="grid gap-2">
                    <Label>Terceirizada</Label>
                    <Select
                      value={formTerceirizadaId?.toString() || ""}
                      onValueChange={(v) => setFormTerceirizadaId(v ? parseInt(v) : null)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione..." />
                      </SelectTrigger>
                      <SelectContent>
                        {terceirizadasLista.map((t: any) => (
                          <SelectItem key={t.id} value={t.id.toString()}>{t.nome}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="grid gap-2">
                  <Label htmlFor="edit-fornecedor">Número do Fornecedor *</Label>
                  <Input
                    id="edit-fornecedor"
                    value={formFornecedorId}
                    onChange={(e) => setFormFornecedorId(e.target.value)}
                    placeholder="FOR123"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="edit-filial">Filial Montadora</Label>
                    <Input
                      id="edit-filial"
                      value={formFilial}
                      onChange={(e) => setFormFilial(e.target.value)}
                      placeholder="Nome da filial"
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="edit-cidade">Cidade</Label>
                    <Input
                      id="edit-cidade"
                      value={formCidade}
                      onChange={(e) => setFormCidade(e.target.value)}
                      placeholder="São Paulo"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="edit-montagem">% Montagem</Label>
                    <Input
                      id="edit-montagem"
                      type="number"
                      step="0.1"
                      value={formPercentualMontagem}
                      onChange={(e) => setFormPercentualMontagem(e.target.value)}
                      placeholder="5"
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="edit-assistencia">% Assistência</Label>
                    <Input
                      id="edit-assistencia"
                      type="number"
                      step="0.1"
                      value={formPercentualAssistencia}
                      onChange={(e) => setFormPercentualAssistencia(e.target.value)}
                      placeholder="5"
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="edit-desmontagem">% Desmontagem</Label>
                    <Input
                      id="edit-desmontagem"
                      type="number"
                      step="0.1"
                      value={formPercentualDesmontagem}
                      onChange={(e) => setFormPercentualDesmontagem(e.target.value)}
                      placeholder="5"
                    />
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-auxilio">Auxílio Semanal (R$)</Label>
                  <Input
                    id="edit-auxilio"
                    type="number"
                    step="0.01"
                    value={formAuxilioSemanal}
                    onChange={(e) => setFormAuxilioSemanal(e.target.value)}
                    placeholder="100"
                  />
                </div>

                {/* Envio Automático — sempre ativo */}
                <div className="border rounded-md p-3 space-y-3">
                  <Label className="font-medium">Envio Automático</Label>
                  <div className="grid gap-1">
                    <Label className="text-xs">Dias de Envio</Label>
                    <div className="grid grid-cols-7 gap-1">
                      {Array.from({length: 28}, (_, i) => i + 1).map(d => (
                        <button key={d} type="button" onClick={() => {
                          if (!isAdmin) { toast.error("Solicite para um administrador a alteração da data de envio"); return; }
                          setFormDiasEnvioMes(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d].sort((a,b) => a-b))
                        }}
                          className={`h-7 text-xs rounded border ${formDiasEnvioMes.includes(d) ? "bg-primary text-primary-foreground border-primary" : "bg-background hover:bg-muted border-input"}`}
                        >{d}</button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Template de Email */}
                  <div>
                    <Label className="text-xs">Template de Email</Label>
                    <Select 
                      value={formEmailTemplateId?.toString() || "__default__"} 
                      onValueChange={(v) => setFormEmailTemplateId(v === "__default__" ? null : parseInt(v))}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Template padrão" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__default__">Padrão Montador</SelectItem>
                        {emailTemplates.map((t: any) => (
                          <SelectItem key={t.id} value={t.id.toString()}>
                            {t.nome} {t.is_default ? "(padrão)" : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={editarMontador}>
                  Salvar Alterações
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="blacklist" className="space-y-6">
          {/* Card de Adicionar */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Adicionar Boletim à Blacklist
              </CardTitle>
              <CardDescription>
                Impeça que boletins específicos sejam enviados novamente nos relatórios
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Montador</Label>
                  <Select
                    value={montadorSelecionado?.toString()}
                    onValueChange={(v) => setMontadorSelecionado(Number(v))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione..." />
                    </SelectTrigger>
                    <SelectContent>
                      {montadores.map((m) => (
                        <SelectItem key={m.id} value={m.id.toString()}>
                          {m.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Números dos Boletins</Label>
                  <Input
                    placeholder="Ex: BOL001, BOL002, BOL003"
                    value={numerosBoletim}
                    onChange={(e) => setNumerosBoletim(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Separe múltiplos números por vírgula
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>Motivo (opcional)</Label>
                  <Input
                    placeholder="Ex: Duplicado, Cancelado..."
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                  />
                </div>
              </div>

              <Button
                onClick={adicionarNaBlacklist}
                className="mt-4"
                disabled={!montadorSelecionado || !numerosBoletim.trim()}
              >
                <Plus className="mr-2 h-4 w-4" />
                Adicionar à Blacklist
              </Button>
            </CardContent>
          </Card>

          {/* Card da Lista */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Boletins na Blacklist</CardTitle>
                  <CardDescription>
                    {blacklistFiltrada.length} {blacklistFiltrada.length === 1 ? "item" : "itens"} na blacklist
                  </CardDescription>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Buscar..."
                    value={searchBlacklist}
                    onChange={(e) => setSearchBlacklist(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {blacklistFiltrada.length === 0 ? (
                <div className="text-center py-12">
                  <ShieldAlert className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">Nenhum boletim na blacklist</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Montador</TableHead>
                      <TableHead>Número Boletim</TableHead>
                      <TableHead>Motivo</TableHead>
                      <TableHead>Data de Adição</TableHead>
                      <TableHead className="text-right">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {blacklistFiltrada.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">
                          {item.montador_nome}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{item.boletim}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {item.motivo || "-"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(item.data_adicao).toLocaleDateString("pt-BR")}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removerDaBlacklist(item.id, item.boletim)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
