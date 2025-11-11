import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Plus, Mail, Phone, Calendar, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { prestadoresService } from "@/services/prestadores.service";
import { Prestador } from "@/types/prestador";

interface BlacklistItem {
  id: number;
  prestador_id: number;
  prestador_nome: string;
  os_numero: string;
  motivo: string;
  data_adicao: string;
}

export default function Prestadores() {
  const [searchTerm, setSearchTerm] = useState("");
  const [blacklistItems, setBlacklistItems] = useState<BlacklistItem[]>([]);
  const [prestadorSelecionado, setPrestadorSelecionado] = useState<number | null>(null);
  const [numerosOS, setNumerosOS] = useState("");
  const [motivo, setMotivo] = useState("");
  const [searchBlacklist, setSearchBlacklist] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [prestadores, setPrestadores] = useState<Prestador[]>([]);
  const [loading, setLoading] = useState(true);
  const [prestadorEditando, setPrestadorEditando] = useState<Prestador | null>(null);
  
  // Form states
  const [formNome, setFormNome] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formEmailsAdicionais, setFormEmailsAdicionais] = useState("");
  const [formFornecedorId, setFormFornecedorId] = useState("");
  const [formRegraEnvio, setFormRegraEnvio] = useState("Nenhuma");
  const [formDiasEnvio, setFormDiasEnvio] = useState("");
  const [formTempoVencimento, setFormTempoVencimento] = useState("10");

  useEffect(() => {
    carregarBlacklist();
    carregarPrestadores();
  }, []);

  const carregarPrestadores = async () => {
    try {
      setLoading(true);
      const response = await prestadoresService.getAll({ limit: 1000 });
      setPrestadores(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar prestadores:", error);
      toast.error("Erro ao carregar prestadores");
    } finally {
      setLoading(false);
    }
  };

  const filteredPrestadores = prestadores.filter((p) =>
    p.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const carregarBlacklist = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/os`);
      const data = await res.json();
      setBlacklistItems(data);
    } catch (error) {
      console.error("Erro ao carregar blacklist:", error);
    }
  };

  const adicionarNaBlacklist = async () => {
    if (!prestadorSelecionado || !numerosOS.trim()) {
      toast.error("Selecione um prestador e insira os números das O.S.");
      return;
    }

    const numerosArray = numerosOS.split(",").map(n => n.trim()).filter(n => n);

    try {
      for (const numero of numerosArray) {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/os`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prestador_id: prestadorSelecionado,
            os_numero: numero,
            motivo: motivo || null,
          }),
        });

        if (!response.ok) {
          const error = await response.json();
          toast.error(`${numero}: ${error.detail || 'Erro ao adicionar'}`);
        } else {
          toast.success(`O.S. ${numero} adicionada à blacklist`);
        }
      }

      setNumerosOS("");
      setMotivo("");
      setPrestadorSelecionado(null);
      carregarBlacklist();
    } catch (error) {
      toast.error("Erro ao adicionar à blacklist");
      console.error(error);
    }
  };

  const removerDaBlacklist = async (id: number, numero: string) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/os/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast.success(`O.S. ${numero} removida da blacklist`);
        carregarBlacklist();
      } else {
        toast.error("Erro ao remover da blacklist");
      }
    } catch (error) {
      toast.error("Erro ao remover da blacklist");
      console.error(error);
    }
  };

  const blacklistFiltrada = blacklistItems.filter(item =>
    item.prestador_nome?.toLowerCase().includes(searchBlacklist.toLowerCase()) ||
    item.os_numero?.toLowerCase().includes(searchBlacklist.toLowerCase()) ||
    item.motivo?.toLowerCase().includes(searchBlacklist.toLowerCase())
  );

  const abrirEdicao = (prestador: Prestador) => {
    setPrestadorEditando(prestador);
    setFormNome(prestador.nome);
    setFormEmail(prestador.email);
    setFormEmailsAdicionais(prestador.emails_adicionais || "");
    setFormFornecedorId(prestador.fornecedor_id);
    setFormRegraEnvio(prestador.regra_envio || "Nenhuma");
    setFormDiasEnvio(prestador.dias_envio || "");
    setFormTempoVencimento(prestador.tempo_vencimento_dias?.toString() || "10");
    setEditDialogOpen(true);
  };

  const limparForm = () => {
    setFormNome("");
    setFormEmail("");
    setFormEmailsAdicionais("");
    setFormFornecedorId("");
    setFormRegraEnvio("Nenhuma");
    setFormDiasEnvio("");
    setFormTempoVencimento("10");
    setPrestadorEditando(null);
  };

  const adicionarPrestador = async () => {
    if (!formNome || !formEmail || !formFornecedorId) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/prestadores`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: formNome,
          email: formEmail,
          fornecedor_id: formFornecedorId,
          regra_envio: formRegraEnvio,
          dias_envio: formDiasEnvio,
          emails_adicionais: formEmailsAdicionais || null,
          tempo_vencimento_dias: parseInt(formTempoVencimento),
        }),
      });

      if (response.ok) {
        toast.success("Prestador adicionado com sucesso!");
        setDialogOpen(false);
        limparForm();
        carregarPrestadores();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao adicionar prestador");
      }
    } catch (error) {
      toast.error("Erro ao adicionar prestador");
      console.error(error);
    }
  };

  const editarPrestador = async () => {
    if (!prestadorEditando || !formNome || !formEmail || !formFornecedorId) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }

    try {
      await prestadoresService.update(prestadorEditando.id, {
        nome: formNome,
        email: formEmail,
        fornecedor_id: formFornecedorId,
        regra_envio: formRegraEnvio,
        dias_envio: formDiasEnvio,
        emails_adicionais: formEmailsAdicionais || null,
        tempo_vencimento_dias: parseInt(formTempoVencimento),
      });

      toast.success("Prestador atualizado com sucesso!");
      setEditDialogOpen(false);
      limparForm();
      carregarPrestadores();
    } catch (error) {
      toast.error("Erro ao atualizar prestador");
      console.error(error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Prestadores</h1>
          <p className="text-muted-foreground">Gerenciar empresas prestadoras de serviços</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) limparForm();
        }}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Novo Prestador
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Adicionar Novo Prestador</DialogTitle>
              <DialogDescription>
                Preencha os dados do prestador de serviços
              </DialogDescription>
            </DialogHeader>
            
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="nome">Nome *</Label>
                <Input
                  id="nome"
                  value={formNome}
                  onChange={(e) => setFormNome(e.target.value)}
                  placeholder="Nome da empresa"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="email">E-mail Principal *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="contato@empresa.com"
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
                  <Label htmlFor="regra">Regra de Envio</Label>
                  <Select value={formRegraEnvio} onValueChange={setFormRegraEnvio}>
                    <SelectTrigger id="regra">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Nenhuma">Nenhuma</SelectItem>
                      <SelectItem value="Semanal">Semanal</SelectItem>
                      <SelectItem value="Mensal (Dia Fixo)">Mensal (Dia Fixo)</SelectItem>
                      <SelectItem value="Quinzenal">Quinzenal</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="vencimento">Prazo Pagamento</Label>
                  <Select value={formTempoVencimento} onValueChange={setFormTempoVencimento}>
                    <SelectTrigger id="vencimento">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3">3 dias úteis</SelectItem>
                      <SelectItem value="10">10 dias úteis</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {formRegraEnvio === "Semanal" && (
                <div className="grid gap-2">
                  <Label htmlFor="dia-semana">Dia da Semana</Label>
                  <Select value={formDiasEnvio} onValueChange={setFormDiasEnvio}>
                    <SelectTrigger id="dia-semana">
                      <SelectValue placeholder="Selecione..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Segunda-feira">Segunda-feira</SelectItem>
                      <SelectItem value="Terça-feira">Terça-feira</SelectItem>
                      <SelectItem value="Quarta-feira">Quarta-feira</SelectItem>
                      <SelectItem value="Quinta-feira">Quinta-feira</SelectItem>
                      <SelectItem value="Sexta-feira">Sexta-feira</SelectItem>
                      <SelectItem value="Sábado">Sábado</SelectItem>
                      <SelectItem value="Domingo">Domingo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {(formRegraEnvio === "Mensal (Dia Fixo)" || formRegraEnvio === "Quinzenal") && (
                <div className="grid gap-2">
                  <Label htmlFor="dias-mes">Dias do Mês</Label>
                  <Input
                    id="dias-mes"
                    value={formDiasEnvio}
                    onChange={(e) => setFormDiasEnvio(e.target.value)}
                    placeholder="Ex: 5 ou 5,20"
                  />
                  <p className="text-xs text-muted-foreground">
                    Para quinzenal, separe dois dias por vírgula
                  </p>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={adicionarPrestador}>
                Adicionar Prestador
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="lista" className="space-y-6">
        <TabsList>
          <TabsTrigger value="lista">Lista de Prestadores</TabsTrigger>
          <TabsTrigger value="blacklist">
            <ShieldAlert className="h-4 w-4 mr-2" />
            Blacklist de O.S.
          </TabsTrigger>
        </TabsList>

        <TabsContent value="lista">
          <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar prestadores..."
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
                <TableHead>Contato</TableHead>
                <TableHead>Fornecedor ID</TableHead>
                <TableHead>Regra de Envio</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPrestadores.map((prestador) => (
                <TableRow key={prestador.id}>
                  <TableCell className="font-medium">{prestador.nome}</TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{prestador.email}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Phone className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{prestador.telefone}</span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{prestador.fornecedor_id}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Calendar className="h-3 w-3 text-muted-foreground" />
                        <span className="font-medium">{prestador.regra_envio || "Nenhuma"}</span>
                      </div>
                      {prestador.dias_envio && <span className="text-xs text-muted-foreground">{prestador.dias_envio}</span>}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={(prestador.ativo ?? true) ? "default" : "secondary"}
                      className={
                        (prestador.ativo ?? true)
                          ? "bg-success text-success-foreground"
                          : ""
                      }
                    >
                      {(prestador.ativo ?? true) ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => abrirEdicao(prestador)}>
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
                <DialogTitle>Editar Prestador</DialogTitle>
                <DialogDescription>
                  Atualize os dados do prestador de serviços
                </DialogDescription>
              </DialogHeader>
              
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="edit-nome">Nome *</Label>
                  <Input
                    id="edit-nome"
                    value={formNome}
                    onChange={(e) => setFormNome(e.target.value)}
                    placeholder="Nome da empresa"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-email">E-mail Principal *</Label>
                  <Input
                    id="edit-email"
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    placeholder="contato@empresa.com"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edit-emails-adicionais">E-mails Adicionais</Label>
                  <Input
                    id="edit-emails-adicionais"
                    value={formEmailsAdicionais}
                    onChange={(e) => setFormEmailsAdicionais(e.target.value)}
                    placeholder="email2@empresa.com, email3@empresa.com"
                  />
                  <p className="text-xs text-muted-foreground">
                    Separe múltiplos emails por vírgula
                  </p>
                </div>

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
                    <Label htmlFor="edit-regra">Regra de Envio</Label>
                    <Select value={formRegraEnvio} onValueChange={setFormRegraEnvio}>
                      <SelectTrigger id="edit-regra">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Nenhuma">Nenhuma</SelectItem>
                        <SelectItem value="Semanal">Semanal</SelectItem>
                        <SelectItem value="Mensal (Dia Fixo)">Mensal (Dia Fixo)</SelectItem>
                        <SelectItem value="Quinzenal">Quinzenal</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="edit-vencimento">Prazo Pagamento</Label>
                    <Select value={formTempoVencimento} onValueChange={setFormTempoVencimento}>
                      <SelectTrigger id="edit-vencimento">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="3">3 dias úteis</SelectItem>
                        <SelectItem value="10">10 dias úteis</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {formRegraEnvio === "Semanal" && (
                  <div className="grid gap-2">
                    <Label htmlFor="edit-dia-semana">Dia da Semana</Label>
                    <Select value={formDiasEnvio} onValueChange={setFormDiasEnvio}>
                      <SelectTrigger id="edit-dia-semana">
                        <SelectValue placeholder="Selecione..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Segunda-feira">Segunda-feira</SelectItem>
                        <SelectItem value="Terça-feira">Terça-feira</SelectItem>
                        <SelectItem value="Quarta-feira">Quarta-feira</SelectItem>
                        <SelectItem value="Quinta-feira">Quinta-feira</SelectItem>
                        <SelectItem value="Sexta-feira">Sexta-feira</SelectItem>
                        <SelectItem value="Sábado">Sábado</SelectItem>
                        <SelectItem value="Domingo">Domingo</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {(formRegraEnvio === "Mensal (Dia Fixo)" || formRegraEnvio === "Quinzenal") && (
                  <div className="grid gap-2">
                    <Label htmlFor="edit-dias-mes">Dias do Mês</Label>
                    <Input
                      id="edit-dias-mes"
                      value={formDiasEnvio}
                      onChange={(e) => setFormDiasEnvio(e.target.value)}
                      placeholder="Ex: 5 ou 5,20"
                    />
                    <p className="text-xs text-muted-foreground">
                      Para quinzenal, separe dois dias por vírgula
                    </p>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={editarPrestador}>
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
                Adicionar O.S. à Blacklist
              </CardTitle>
              <CardDescription>
                Impeça que O.S. específicas sejam enviadas novamente nos relatórios
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Prestador</Label>
                  <Select
                    value={prestadorSelecionado?.toString()}
                    onValueChange={(v) => setPrestadorSelecionado(Number(v))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione..." />
                    </SelectTrigger>
                    <SelectContent>
                      {prestadores.map((p) => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Números das O.S.</Label>
                  <Input
                    placeholder="Ex: OS001, OS002, OS003"
                    value={numerosOS}
                    onChange={(e) => setNumerosOS(e.target.value)}
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
                disabled={!prestadorSelecionado || !numerosOS.trim()}
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
                  <CardTitle>O.S. na Blacklist</CardTitle>
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
                  <p className="text-muted-foreground">Nenhuma O.S. na blacklist</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Prestador</TableHead>
                      <TableHead>Número O.S.</TableHead>
                      <TableHead>Motivo</TableHead>
                      <TableHead>Data de Adição</TableHead>
                      <TableHead className="text-right">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {blacklistFiltrada.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">
                          {item.prestador_nome}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{item.os_numero}</Badge>
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
                            onClick={() => removerDaBlacklist(item.id, item.os_numero)}
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
