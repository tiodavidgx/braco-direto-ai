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
  }, []);

  const carregarTemplates = async () => {
    try {
      const data = await automacaoService.getTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Erro ao carregar templates:", error);
    }
  };

  const carregarTriggers = async () => {
    try {
      const data = await automacaoService.getTriggers();
      setTriggers(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Erro ao carregar triggers:", error);
    }
  };

  const carregarHistorico = async () => {
    try {
      const data = await automacaoService.getHistorico();
      setHistorico(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Erro ao carregar histórico:", error);
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

  const toggleTrigger = async (triggerId: number, novoStatus: boolean) => {
    try {
      await automacaoService.updateTrigger(String(triggerId), { ativo: novoStatus });
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
      
      if (triggerExistente) {
        await automacaoService.updateTrigger(triggerExistente.id, {
          template_id: templateId,
        });
        toast({ title: "Sucesso", description: "Gatilho atualizado!" });
      } else {
        await automacaoService.saveTrigger({
          evento,
          template_id: templateId,
          ativo: true,
        });
        toast({ title: "Sucesso", description: "Gatilho criado!" });
      }
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
      "{{lote_id}}",
      "{{card_url}}",
      "{{data_integracao}}",
    ],
    montador: [
      "{{nome_montador}}",
      "{{periodo_relatorio}}",
      "{{valor_total}}",
      "{{quantidade_os}}",
      "{{numero_nf}}",
      "{{data_recebimento}}",
      "{{envio_id}}",
      "{{card_url}}",
      "{{data_integracao}}",
    ],
    envio_relatorio: [
      "{{nome_prestador}}",
      "{{nome_montador}}",
      "{{periodo}}",
      "{{valor}}",
      "{{link}}",
    ],
    nf_recebida: [
      "{{nome_prestador}}",
      "{{nome_montador}}",
      "{{numero_nf}}",
      "{{data_recebimento}}",
      "{{valor}}",
      "{{periodo}}",
    ],
    trello_integracao: [
      "{{nome_prestador}}",
      "{{nome_montador}}",
      "{{lote_id}}",
      "{{envio_id}}",
      "{{valor}}",
      "{{card_url}}",
      "{{data_integracao}}",
    ],
  };

  const templatesPrestador = templates.filter(t => t.tipo === "prestador");
  const templatesMontador = templates.filter(t => t.tipo === "montador");
  const templatesEnvioRelatorio = templates.filter(t => t.tipo === "envio_relatorio");
  const templatesNFRecebida = templates.filter(t => t.tipo === "nf_recebida");
  const templatesTrello = templates.filter(t => t.tipo === "trello_integracao");

  // Agrupar templates por tipo para exibição
  const tiposTemplates = [
    { key: 'prestador', label: 'Prestadores', templates: templatesPrestador },
    { key: 'montador', label: 'Montadores', templates: templatesMontador },
    { key: 'envio_relatorio', label: 'Envio de Relatório', templates: templatesEnvioRelatorio },
    { key: 'nf_recebida', label: 'NF Recebida', templates: templatesNFRecebida },
    { key: 'trello_integracao', label: 'Integração Trello', templates: templatesTrello },
  ];

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
                            <SelectItem value="envio_relatorio">Envio de Relatório</SelectItem>
                            <SelectItem value="nf_recebida">NF Recebida</SelectItem>
                            <SelectItem value="trello_integracao">Integração Trello</SelectItem>
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
                        {(variaveis[tipoTemplate as keyof typeof variaveis] || variaveis.prestador).map((v) => (
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
                  {tiposTemplates.map(({ key, label, templates: tipoTemplates }) => 
                    tipoTemplates.length > 0 && (
                      <div key={key} className="space-y-3">
                        <h3 className="font-semibold">{label}</h3>
                        {tipoTemplates.map((t) => (
                          <Card key={t.id}>
                            <CardHeader className="pb-3">
                              <div className="flex items-center justify-between">
                                <div>
                                  <CardTitle className="text-base">{t.nome}</CardTitle>
                                  <Badge variant="outline" className="mt-1">{t.tipo}</Badge>
                                </div>
                                <div className="flex gap-2">
                                  <Button size="sm" variant="outline" onClick={() => abrirEdicao(t)}>
                                    <Edit className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>
                            </CardHeader>
                            <CardContent>
                              <code className="text-xs bg-muted p-2 rounded block overflow-x-auto whitespace-pre-wrap">
                                {t.template.substring(0, 200)}
                                {t.template.length > 200 && "..."}
                              </code>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )
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
                <Card key={trigger.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base">
                          {trigger.evento === 'envio_email_prestador' && '📧 Relatório Enviado - Prestador'}
                          {trigger.evento === 'nf_recebida_prestador' && '📎 NF Recebida - Prestador'}
                          {trigger.evento === 'envio_email_montador' && '📧 Relatório Enviado - Montador'}
                          {trigger.evento === 'nf_recebida_montador' && '📎 NF Recebida - Montador'}
                          {trigger.evento === 'trello_card_criado_prestador' && '🔗 Trello Integrado - Prestador'}
                          {trigger.evento === 'trello_card_criado_montador' && '🔗 Trello Integrado - Montador'}
                          {trigger.evento === 'pagamento_realizado_prestador' && '💰 Pagamento Realizado - Prestador'}
                          {trigger.evento === 'pagamento_realizado_montador' && '💰 Pagamento Realizado - Montador'}
                          {!['envio_email_prestador', 'nf_recebida_prestador', 'envio_email_montador', 'nf_recebida_montador', 'trello_card_criado_prestador', 'trello_card_criado_montador', 'pagamento_realizado_prestador', 'pagamento_realizado_montador'].includes(trigger.evento) && `🔔 ${trigger.evento}`}
                        </CardTitle>
                        <CardDescription className="text-sm">
                          {trigger.evento === 'envio_email_prestador' && 'Quando o relatório de fechamento é enviado ao prestador'}
                          {trigger.evento === 'nf_recebida_prestador' && 'Quando o prestador anexa a nota fiscal'}
                          {trigger.evento === 'envio_email_montador' && 'Quando o relatório de pagamento é enviado ao montador'}
                          {trigger.evento === 'nf_recebida_montador' && 'Quando o montador anexa a nota fiscal'}
                          {trigger.evento === 'trello_card_criado_prestador' && 'Quando o card do Trello é criado para o prestador'}
                          {trigger.evento === 'trello_card_criado_montador' && 'Quando o card do Trello é criado para o montador'}
                          {trigger.evento === 'pagamento_realizado_prestador' && 'Quando o pagamento é confirmado para o prestador'}
                          {trigger.evento === 'pagamento_realizado_montador' && 'Quando o pagamento é confirmado para o montador'}
                        </CardDescription>
                      </div>
                      <Switch 
                        checked={trigger.ativo}
                        onCheckedChange={(checked) => toggleTrigger(trigger.id, checked)}
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
                  <CardTitle>Histórico de Envios</CardTitle>
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
        </TabsContent>
      </Tabs>
    </div>
  );
}
