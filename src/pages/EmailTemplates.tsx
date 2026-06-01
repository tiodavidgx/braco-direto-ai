import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Mail, Plus, Trash2, Edit, Star, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/services/api";

interface EmailTemplate {
  id: number;
  tipo: string;
  nome: string;
  descricao: string | null;
  assunto: string;
  corpo: string;
  cc: string | null;
  variaveis: string[];
  ativo: boolean;
  is_default: boolean;
  atualizado_em: string | null;
}

const VARIAVEIS_POR_TIPO: Record<string, { nome: string; descricao: string }[]> = {
  montador: [
    { nome: "{{periodo_relatorio}}", descricao: "Período do relatório" },
    { nome: "{{nome_montador}}", descricao: "Nome do montador" },
    { nome: "{{link_upload}}", descricao: "Link para upload de documentos" },
  ],
};

export default function EmailTemplates() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editando, setEditando] = useState<EmailTemplate | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<EmailTemplate | null>(null);

  const [form, setForm] = useState({
    tipo: "montador" as string,
    nome: "",
    descricao: "",
    assunto: "",
    corpo: "",
    cc: "",
    is_default: false,
  });

  useEffect(() => {
    carregarTemplates();
  }, []);

  const carregarTemplates = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<{ data: EmailTemplate[] }>("/email-templates?tipo=montador");
      setTemplates(res.data || []);
    } catch (e) {
      toast.error("Erro ao carregar templates");
    } finally {
      setLoading(false);
    }
  };

  const abrirNovo = () => {
    setEditando(null);
    setForm({
      tipo: "montador",
      nome: "Padrão Montador",
      descricao: "",
      assunto: "Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}",
      corpo: "Olá, {{nome_montador}},\n\nSegue em anexo o seu relatório de pagamento de montagens referente ao período de **{{periodo_relatorio}}**.\n\n📎 **Link para upload de documentos:** {{link_upload}}\n\nQualquer dúvida, estamos à disposição.",
      cc: "",
      is_default: false,
    });
    setDialogOpen(true);
  };

  const abrirEdicao = (t: EmailTemplate) => {
    setEditando(t);
    setForm({
      tipo: t.tipo,
      nome: t.nome,
      descricao: t.descricao || "",
      assunto: t.assunto,
      corpo: t.corpo,
      cc: t.cc || "",
      is_default: t.is_default,
    });
    setDialogOpen(true);
  };

  const salvar = async () => {
    if (!form.nome || !form.assunto || !form.corpo) {
      toast.error("Nome, assunto e corpo são obrigatórios");
      return;
    }
    setSalvando(true);
    try {
      if (editando) {
        await apiClient.put(`/email-templates/${editando.id}`, form);
        toast.success("Template atualizado!");
      } else {
        await apiClient.post("/email-templates", form);
        toast.success("Template criado!");
      }
      carregarTemplates();
      setDialogOpen(false);
    } catch (e: any) {
      toast.error(e.message || "Erro ao salvar");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id: number) => {
    if (!confirm("Tem certeza que deseja excluir este template?")) return;
    try {
      await apiClient.delete(`/email-templates/${id}`);
      toast.success("Template excluído!");
      carregarTemplates();
    } catch (e: any) {
      toast.error(e.message || "Erro ao excluir");
    }
  };

  const toggleAtivo = async (t: EmailTemplate) => {
    try {
      await apiClient.put(`/email-templates/${t.id}`, { ativo: !t.ativo });
      carregarTemplates();
    } catch (e: any) {
      toast.error(e.message || "Erro ao atualizar");
    }
  };

  const tornarDefault = async (t: EmailTemplate) => {
    try {
      await apiClient.put(`/email-templates/${t.id}`, { is_default: true });
      toast.success(`"${t.nome}" agora é o template padrão!`);
      carregarTemplates();
    } catch (e: any) {
      toast.error(e.message || "Erro ao atualizar");
    }
  };

  const inserirVariavel = (variavel: string, campo: "assunto" | "corpo") => {
    setForm({ ...form, [campo]: form[campo] + " " + variavel });
  };

  const variaveisDisponiveis = VARIAVEIS_POR_TIPO[form.tipo] || VARIAVEIS_POR_TIPO.montador;

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Templates de Email</h1>
          <p className="text-sm md:text-base text-muted-foreground">
            Gerencie os modelos de email para envio de relatórios
          </p>
        </div>
        <Button onClick={abrirNovo} className="gap-2">
          <Plus className="h-4 w-4" /> Novo Template
        </Button>
      </div>

      {loading ? (
        <Card><CardContent className="p-8 text-center text-muted-foreground">Carregando...</CardContent></Card>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <Mail className="h-12 w-12 mx-auto mb-3 opacity-30" />
            Nenhum template cadastrado. Clique em "Novo Template" para começar.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {(() => {
            const tipo = "montador";
            const doTipo = templates.filter((t) => t.tipo === tipo);
            return (
              <Card key={tipo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    Montadores
                    <Badge variant="outline">{doTipo.length}</Badge>
                  </CardTitle>
                  <CardDescription>
                    Templates para envio de relatórios de montadores
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {doTipo.length === 0 ? (
                    <p className="text-center text-muted-foreground py-4">Nenhum template cadastrado</p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Nome</TableHead>
                          <TableHead>Assunto</TableHead>
                          <TableHead>Padrão</TableHead>
                          <TableHead>Ativo</TableHead>
                          <TableHead className="w-[120px]">Ações</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {doTipo.map((t) => (
                          <TableRow key={t.id}>
                            <TableCell className="font-medium">
                              <div>{t.nome}</div>
                              {t.descricao && (
                                <div className="text-xs text-muted-foreground">{t.descricao}</div>
                              )}
                            </TableCell>
                            <TableCell className="max-w-[300px] truncate">{t.assunto}</TableCell>
                            <TableCell>
                              {t.is_default ? (
                                <Badge className="gap-1"><Star className="h-3 w-3" /> Padrão</Badge>
                              ) : (
                                <Button variant="ghost" size="sm" onClick={() => tornarDefault(t)} title="Tornar padrão">
                                  <Star className="h-3 w-3 text-muted-foreground" />
                                </Button>
                              )}
                            </TableCell>
                            <TableCell>
                              <Switch checked={t.ativo} onCheckedChange={() => toggleAtivo(t)} />
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button variant="ghost" size="icon" onClick={() => { setPreviewTemplate(t); setPreviewOpen(true); }} title="Visualizar">
                                  <Eye className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" onClick={() => abrirEdicao(t)} title="Editar">
                                  <Edit className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" onClick={() => excluir(t.id)} title="Excluir">
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            );
          })()}
        </div>
      )}

      {/* Dialog Criar/Editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editando ? "Editar Template" : "Novo Template de Email"}</DialogTitle>
            <DialogDescription>
              Configure o assunto, corpo e variáveis do template.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label>Nome *</Label>
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Ex: Template Formal" />
            </div>

            <div>
              <Label>Descrição</Label>
              <Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Breve descrição do template" />
            </div>

            <div>
              <Label>Assunto *</Label>
              <Input value={form.assunto} onChange={(e) => setForm({ ...form, assunto: e.target.value })} placeholder="Assunto do email" />
            </div>

            <div>
              <Label>Corpo *</Label>
              <Textarea
                value={form.corpo}
                onChange={(e) => setForm({ ...form, corpo: e.target.value })}
                placeholder="Corpo do email (HTML suportado)"
                rows={8}
              />
            </div>

            <div>
              <Label>CC (cópia)</Label>
              <Input value={form.cc} onChange={(e) => setForm({ ...form, cc: e.target.value })} placeholder="emails separados por vírgula" />
            </div>

            {/* Variáveis disponíveis */}
            <div className="bg-muted/50 rounded-md p-3">
              <Label className="text-xs mb-2 block">Variáveis disponíveis — clique para inserir:</Label>
              <div className="flex flex-wrap gap-2">
                {variaveisDisponiveis.map((v) => (
                  <Badge
                    key={v.nome}
                    variant="outline"
                    className="cursor-pointer hover:bg-primary hover:text-primary-foreground"
                    onClick={() => inserirVariavel(v.nome, "corpo")}
                    title={v.descricao}
                  >
                    {v.nome}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch checked={form.is_default} onCheckedChange={(c) => setForm({ ...form, is_default: c })} />
              <Label>Template padrão</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={salvar} disabled={salvando}>
              {salvando ? "Salvando..." : editando ? "Atualizar" : "Criar Template"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog Preview */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Preview: {previewTemplate?.nome}</DialogTitle>
            <DialogDescription>
              Visualize como o email será renderizado (variáveis serão substituídas no envio real)
            </DialogDescription>
          </DialogHeader>
          {previewTemplate && (
            <div className="space-y-4">
              <div>
                <Label className="text-xs text-muted-foreground">Assunto:</Label>
                <p className="font-medium">{previewTemplate.assunto}</p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Corpo:</Label>
                <div className="bg-white border rounded-md p-4 prose prose-sm max-w-none" 
                     dangerouslySetInnerHTML={{ __html: previewTemplate.corpo.replace(/\n/g, "<br>") }} />
              </div>
              {previewTemplate.cc && (
                <div>
                  <Label className="text-xs text-muted-foreground">CC:</Label>
                  <p>{previewTemplate.cc}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
