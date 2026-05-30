import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { FileText, Zap, History, Plus, Edit, Trash2, TestTube } from "lucide-react";
import { automacaoService } from "@/services/automacao.service";

export default function Automacao() {
  const { toast } = useToast();
  const [templates, setTemplates] = useState<any[]>([]);
  const [triggers, setTriggers] = useState<any[]>([]);
  const [historico, setHistorico] = useState<any[]>([]);
  const [crmHistorico, setCrmHistorico] = useState<any[]>([]);
  const [modoEdicao, setModoEdicao] = useState<"lista" | "novo" | "editar">("lista");
  const [templateEditando, setTemplateEditando] = useState<any>(null);
  const [nomeTemplate, setNomeTemplate] = useState("");
  const [tipoTemplate, setTipoTemplate] = useState("prestador");
  const [textoTemplate, setTextoTemplate] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    carregarTemplates();
    carregarTriggers();
    carregarHistorico();
    carregarCrmHistorico();
  }, []);

  const carregarTemplates = async () => {
    try {
      console.log("[Automacao] Carregando templates...");
      const data = await automacaoService.getTemplates();
      console.log("[Automacao] Templates recebidos:", data);
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("[Automacao] Erro ao carregar templates:", error);
    }
  };

  const carregarTriggers = async () => {
    try {
      console.log("[Automacao] Carregando triggers...");
      const data = await automacaoService.getTriggers();
      console.log("[Automacao] Triggers recebidos:", data);
      setTriggers(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("[Automacao] Erro ao carregar triggers:", error);
    }
  };

  const carregarHistorico = async () => {
    try {
      console.log("[Automacao] Carregando histórico...");
      const data = await automacaoService.getHistorico();
      console.log("[Automacao] Histórico recebido:", data);
      setHistorico(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("[Automacao] Erro ao carregar histórico:", error);
    }
  };

  const carregarCrmHistorico = async () => {
    try {
      const data = await automacaoService.getCrmHistorico();
      setCrmHistorico(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("[Automacao] Erro ao carregar histórico CRM:", error);
    }
  };

  const salvarTemplate = async () => {
    if (!nomeTemplate || !textoTemplate) {
      toast({ title: "Erro", description: "Preencha todos os campos", variant: "destructive" });
      return;
    }

    setLoading(true);
    try {
      if (modoEdicao === "novo") {
        await automacaoService.createTemplate({
          nome: nomeTemplate,
          tipo: tipoTemplate,
          template: textoTemplate,
          ativo: true,
        });
        toast({ title: "Sucesso", description: "Template criado!" });
      } else {
        await automacaoService.updateTemplate(templateEditando.id, {
          template: textoTemplate,
        });
        toast({ title: "Sucesso", description: "Template atualizado!" });
      }
      limparForm();
      carregarTemplates();
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao salvar template",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const deletarTemplate = async (id: string) => {
    try {
      await automacaoService.deleteTemplate(id);
      toast({ title: "Sucesso", description: "Template deletado!" });
      carregarTemplates();
    } catch (error: any) {
      toast({ title: "Erro", description: "Erro ao deletar", variant: "destructive" });
    }
  };

  const limparForm = () => {
    setModoEdicao("lista");
    setTemplateEditando(null);
    setNomeTemplate("");
    setTextoTemplate("");
  };

  const toggleTrigger = async (evento: string, novoStatus: boolean) => {
    try {
      // Usar o evento como identificador
      const triggerExistente = triggers.find(t => t.evento === evento);
      await automacaoService.saveTrigger({
        evento,
        template_id: triggerExistente?.template_id || "",
        ativo: novoStatus,
      }, triggerExistente?.id);
      toast({ 
        title: "Sucesso", 
        description: `Gatilho ${novoStatus ? 'ativado' : 'desativado'}!` 
      });
      carregarTriggers();
    } catch (error: any) {
      toast({
        title: "Erro",
        description: "Erro ao atualizar gatilho",
        variant: "destructive",
      });
    }
  };

  const salvarTrigger = async (evento: string, templateId: string) => {
    try {
      // Buscar se já existe trigger para este evento
      const triggerExistente = triggers.find(t => t.evento === evento);
      
      await automacaoService.saveTrigger({
        evento,
        template_id: templateId,
        ativo: triggerExistente?.ativo ?? true,
      }, triggerExistente?.id);
      toast({ title: "Sucesso", description: "Gatilho atualizado!" });
      carregarTriggers();
    } catch (error: any) {
      toast({
        title: "Erro",
        description: "Erro ao salvar gatilho",
        variant: "destructive",
      });
    }
  };

  const abrirEdicao = (template: any) => {
    setModoEdicao("editar");
    setTemplateEditando(template);
    setNomeTemplate(template.nome);
    setTipoTemplate(template.tipo);
    setTextoTemplate(template.template);
  };

  const variaveis = {
    prestador: [
      "{{nome_prestador}}",
      "{{periodo}}",
      "{{valor}}",
      "{{link}}",
      "{{numero_nf}}",
      "{{data_recebimento}}",
    ],
    montador: [
      "{{nome_montador}}",
      "{{periodo_relatorio}}",
      "{{valor_total}}",
      "{{quantidade_os}}",
      "{{numero_nf}}",
      "{{data_recebimento}}",
    ],
    pre_cadastro: [
      "{{nome_montador}}",
      "{{criado_por}}",
      "{{tipo_documento}}",
      "{{motivo}}",
      "{{id_montador}}",
      "{{numero_fornecedor}}",
      "{{re}}",
    ],
    crm: [
      "{{ticket_id}}",
      "{{id_pedido}}",
      "{{nome_cliente}}",
      "{{telefone_cliente}}",
      "{{email_cliente}}",
      "{{area}}",
      "{{motivo}}",
      "{{status}}",
      "{{status_detalhe}}",
      "{{prazo}}",
      "{{produto}}",
      "{{nome_produto}}",
      "{{analista_nome}}",
      "{{solicitante_nome}}",
      "{{descricao}}",
      "{{comentador_nome}}",
      "{{texto_comentario}}",
      "{{qtd_tickets}}",
      "{{lista_tickets}}",
      "{{link}}",
    ],
  };

  const templatesPrestador = templates.filter(t => t.tipo === "prestador");
  const templatesMontador = templates.filter(t => t.tipo === "montador");
  const templatesPreCadastro = templates.filter(t => t.tipo === "pre_cadastro");
  const templatesCrm = templates.filter(t => t.tipo === "crm");

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Automação WhatsApp</h1>
          <p className="text-muted-foreground">Gerencie templates e gatilhos automáticos</p>
        </div>
      </div>

      <Tabs defaultValue="templates" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="templates">
            <FileText className="mr-2 h-4 w-4" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="triggers">
            <Zap className="mr-2 h-4 w-4" />
            Gatilhos
          </TabsTrigger>
          <TabsTrigger value="historico">
            <History className="mr-2 h-4 w-4" />
            Histórico
          </TabsTrigger>
        </TabsList>

        {/* TAB TEMPLATES */}
        <TabsContent value="templates" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Templates de Mensagens</CardTitle>
                <CardDescription>Crie e gerencie templates reutilizáveis</CardDescription>
              </div>
              <Button onClick={() => setModoEdicao("novo")}>
                <Plus className="mr-2 h-4 w-4" />
                Novo Template
              </Button>
            </CardHeader>
            <CardContent className="space-y-6">
              {modoEdicao === "novo" || modoEdicao === "editar" ? (
                <div className="space-y-4">
                  <h3 className="font-semibold text-lg">
                    {modoEdicao === "novo" ? "Criar" : "Editar"} Template
                  </h3>
                  
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="nome">Nome/ID do Template</Label>
                        <Input
                          id="nome"
                          value={nomeTemplate}
                          onChange={(e) => setNomeTemplate(e.target.value)}
                          placeholder="ex: prestador_personalizado_1"
                          disabled={modoEdicao === "editar"}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="tipo">Tipo</Label>
                        <Select value={tipoTemplate} onValueChange={setTipoTemplate} disabled={modoEdicao === "editar"}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="prestador">Prestador</SelectItem>
                            <SelectItem value="montador">Montador</SelectItem>
                            <SelectItem value="pre_cadastro">Pré-Cadastro</SelectItem>
                            <SelectItem value="crm">CRM</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="template">Mensagem</Label>
                        <Textarea
                          id="template"
                          value={textoTemplate}
                          onChange={(e) => setTextoTemplate(e.target.value)}
                          placeholder="Digite a mensagem..."
                          rows={12}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Variáveis Disponíveis</Label>
                      <div className="bg-muted p-4 rounded-lg space-y-2">
                        {variaveis[tipoTemplate as keyof typeof variaveis].map((v) => (
                          <code key={v} className="block bg-background p-2 rounded text-sm">
                            {v}
                          </code>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button onClick={salvarTemplate} disabled={loading}>
                      Salvar Template
                    </Button>
                    <Button variant="outline" onClick={limparForm}>
                      Cancelar
                    </Button>
                    {modoEdicao === "editar" && (
                      <Button
                        variant="destructive"
                        onClick={() => {
                          if (confirm("Tem certeza que deseja deletar?")) {
                            deletarTemplate(templateEditando.id);
                            limparForm();
                          }
                        }}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Deletar
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {templatesPrestador.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="font-semibold">Prestadores</h3>
                      {templatesPrestador.map((t) => (
                        <Card key={t.id}>
                          <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">{t.nome}</CardTitle>
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => abrirEdicao(t)}>
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <code className="text-xs bg-muted p-2 rounded block overflow-x-auto">
                              {t.template.substring(0, 200)}
                              {t.template.length > 200 && "..."}
                            </code>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}

                  {templatesMontador.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="font-semibold">Montadores</h3>
                      {templatesMontador.map((t) => (
                        <Card key={t.id}>
                          <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">{t.nome}</CardTitle>
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => abrirEdicao(t)}>
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <code className="text-xs bg-muted p-2 rounded block overflow-x-auto">
                              {t.template.substring(0, 200)}
                              {t.template.length > 200 && "..."}
                            </code>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}

                  {templatesPreCadastro.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="font-semibold">Pré-Cadastro</h3>
                      {templatesPreCadastro.map((t) => (
                        <Card key={t.id}>
                          <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">{t.nome}</CardTitle>
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => abrirEdicao(t)}>
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <code className="text-xs bg-muted p-2 rounded block overflow-x-auto">
                              {t.template.substring(0, 200)}
                              {t.template.length > 200 && "..."}
                            </code>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}

                  {templatesCrm.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="font-semibold">CRM</h3>
                      {templatesCrm.map((t) => (
                        <Card key={t.id}>
                          <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">{t.nome}</CardTitle>
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => abrirEdicao(t)}>
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <code className="text-xs bg-muted p-2 rounded block overflow-x-auto">
                              {t.template.substring(0, 200)}
                              {t.template.length > 200 && "..."}
                            </code>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}

                  {templates.length === 0 && (
                    <p className="text-center text-muted-foreground py-8">
                      Nenhum template criado ainda. Clique em "Novo Template" para criar.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB TRIGGERS */}
        <TabsContent value="triggers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Gatilhos Automáticos</CardTitle>
              <CardDescription>Configure quando as mensagens devem ser enviadas</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {triggers.map((trigger) => (
                <Card key={trigger.id || trigger.evento}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base">
                          {trigger.evento === 'envio_email_prestador' && '📧 Email Enviado - Prestador'}
                          {trigger.evento === 'nf_recebida_prestador' && '📎 NF Recebida - Prestador'}
                          {trigger.evento === 'envio_email_montador' && '📧 Email Enviado - Montador'}
                          {trigger.evento === 'nf_recebida_montador' && '📎 NF Recebida - Montador'}
                          {trigger.evento === 'pre_cadastro_enviado_revisao' && '📋 Pré-Cadastro Enviado para Revisão'}
                          {trigger.evento === 'pre_cadastro_documento_recusado' && '⚠️ Documento Recusado'}
                          {trigger.evento === 'pre_cadastro_concluido' && '✅ Cadastro Concluído'}
                          {trigger.evento === 'crm_ticket_novo' && '🎫 CRM - Ticket Novo Atribuído'}
                          {trigger.evento === 'crm_interacao_terceiro' && '💬 CRM - Interação de Terceiro'}
                          {trigger.evento === 'crm_analise_diaria' && '⏰ CRM - Lembrete Diário (13h)'}
                          {trigger.evento === 'crm_lembrete' && '🔔 CRM - Lembre-me Agendado'}
                        </CardTitle>
                        <CardDescription className="text-sm">
                          {trigger.evento === 'envio_email_prestador' && 'Quando um email é enviado ao prestador'}
                          {trigger.evento === 'nf_recebida_prestador' && 'Quando o prestador anexa a nota fiscal'}
                          {trigger.evento === 'envio_email_montador' && 'Quando um email é enviado ao montador'}
                          {trigger.evento === 'nf_recebida_montador' && 'Quando o montador anexa a nota fiscal'}
                          {trigger.evento === 'pre_cadastro_enviado_revisao' && 'Quando um pré-cadastro é enviado para revisão (notifica revisores)'}
                          {trigger.evento === 'pre_cadastro_documento_recusado' && 'Quando um documento é recusado na revisão (notifica quem criou)'}
                          {trigger.evento === 'pre_cadastro_concluido' && 'Quando o cadastro do montador é concluído (notifica envolvidos)'}
                          {trigger.evento === 'crm_ticket_novo' && 'Quando um ticket é criado e atribuído a um analista'}
                          {trigger.evento === 'crm_interacao_terceiro' && 'Quando alguém comenta no ticket de outro analista'}
                          {trigger.evento === 'crm_analise_diaria' && 'Todo dia às 13h, notifica analistas com tickets sem interação'}
                          {trigger.evento === 'crm_lembrete' && 'Quando o analista agenda um lembrete (1h, 2h, 6h, amanhã)'}
                        </CardDescription>
                      </div>
                      <Switch 
                        checked={trigger.ativo}
                        onCheckedChange={(checked) => toggleTrigger(trigger.evento, checked)}
                      />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <Label>Template</Label>
                      <Select
                        value={trigger.template_id}
                        onValueChange={(value) => salvarTrigger(trigger.evento, value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione um template">
                            {trigger.template_nome || "Selecione um template"}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {templates
                            .filter(t => t.ativo)
                            .map((t) => (
                              <SelectItem key={t.id} value={String(t.id)}>
                                {t.nome}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      {trigger.template_nome && (
                        <Badge variant="outline" className="mt-2">
                          Usando: {trigger.template_nome}
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              {triggers.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  Nenhum gatilho configurado ainda
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB HISTÓRICO */}
        <TabsContent value="historico" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Histórico de Envios - Prestadores/Montadores</CardTitle>
                  <CardDescription>Mensagens enviadas automaticamente</CardDescription>
                </div>
                <Button variant="outline" onClick={carregarHistorico}>
                  Atualizar
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {historico.length > 0 ? (
                <div className="space-y-3">
                  {historico.map((h) => (
                    <Card key={h.id}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle className="text-sm">
                              {h.prestador_nome || h.montador_nome}
                            </CardTitle>
                            <CardDescription className="text-xs">
                              {new Date(h.data_envio).toLocaleString('pt-BR')}
                            </CardDescription>
                          </div>
                          <Badge 
                            variant={h.status === 'enviado' ? 'default' : h.status === 'pendente' ? 'secondary' : 'destructive'}
                          >
                            {h.status === 'enviado' && '✅ Enviado'}
                            {h.status === 'pendente' && '⏳ Pendente'}
                            {h.status === 'erro' && '❌ Erro'}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <code className="text-xs bg-muted p-2 rounded block overflow-x-auto whitespace-pre-wrap">
                          {h.mensagem}
                        </code>
                        {h.erro && (
                          <p className="text-xs text-destructive mt-2">
                            Erro: {h.erro}
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  Nenhum envio automático registrado ainda
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Histórico de Envios - CRM</CardTitle>
                  <CardDescription>Notificações WhatsApp enviadas pelo CRM</CardDescription>
                </div>
                <Button variant="outline" onClick={carregarCrmHistorico}>
                  Atualizar
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {crmHistorico.length > 0 ? (
                <div className="space-y-3">
                  {crmHistorico.map((h) => (
                    <Card key={h.id}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle className="text-sm">
                              {h.destinatario_nome || 'Desconhecido'} — Ticket #{h.ticket_id}
                            </CardTitle>
                            <CardDescription className="text-xs">
                              {new Date(h.criado_em).toLocaleString('pt-BR')} • {h.telefone}
                            </CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">
                              {h.tipo === 'ticket_novo' && '🎫 Novo'}
                              {h.tipo === 'interacao_terceiro' && '💬 Interação'}
                              {h.tipo === 'analise_diaria' && '⏰ Diário'}
                              {h.tipo === 'lembrete' && '🔔 Lembrete'}
                            </Badge>
                            <Badge variant={h.sucesso ? 'default' : 'destructive'}>
                              {h.sucesso ? '✅ Enviado' : '❌ Erro'}
                            </Badge>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <code className="text-xs bg-muted p-2 rounded block overflow-x-auto whitespace-pre-wrap">
                          {h.mensagem?.substring(0, 300)}
                          {h.mensagem?.length > 300 && "..."}
                        </code>
                        {h.erro && (
                          <p className="text-xs text-destructive mt-2">
                            Erro: {h.erro}
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  Nenhum envio CRM registrado ainda
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
