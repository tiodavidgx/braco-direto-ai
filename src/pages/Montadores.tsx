import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

interface BlacklistItem {
  id: number;
  montador_id: number;
  montador_nome: string;
  boletim: string;
  motivo: string;
  data_adicao: string;
}

export default function Montadores() {
  const [searchTerm, setSearchTerm] = useState("");
  const [blacklistItems, setBlacklistItems] = useState<BlacklistItem[]>([]);
  const [montadorSelecionado, setMontadorSelecionado] = useState<number | null>(null);
  const [numerosBoletim, setNumerosBoletim] = useState("");
  const [motivo, setMotivo] = useState("");
  const [searchBlacklist, setSearchBlacklist] = useState("");

  // Mock data
  const montadores = [
    {
      id: 1,
      nome: "João Silva",
      identificador: "MONT001",
      email: "joao.silva@email.com",
      telefone: "(11) 98765-1111",
      percentualComissao: 5.5,
      auxilioSemanal: 150.0,
      ativo: true,
    },
    {
      id: 2,
      nome: "Maria Santos",
      identificador: "MONT002",
      email: "maria.santos@email.com",
      telefone: "(11) 98765-2222",
      percentualComissao: 6.0,
      auxilioSemanal: 150.0,
      ativo: true,
    },
    {
      id: 3,
      nome: "Carlos Oliveira",
      identificador: "MONT003",
      email: "carlos.oliveira@email.com",
      telefone: "(11) 98765-3333",
      percentualComissao: 5.0,
      auxilioSemanal: 100.0,
      ativo: false,
    },
  ];

  const filteredMontadores = montadores.filter((m) =>
    m.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    carregarBlacklist();
  }, []);

  const carregarBlacklist = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/boletins`);
      const data = await res.json();
      setBlacklistItems(data);
    } catch (error) {
      console.error("Erro ao carregar blacklist:", error);
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
        const response = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/boletins`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            montador_id: montadorSelecionado,
            boletim: numero,
            motivo: motivo || null,
          }),
        });

        if (!response.ok) {
          const error = await response.json();
          toast.error(`${numero}: ${error.detail || 'Erro ao adicionar'}`);
        } else {
          toast.success(`Boletim ${numero} adicionado à blacklist`);
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
      const response = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/boletins/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast.success(`Boletim ${numero} removido da blacklist`);
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
    item.montador_nome?.toLowerCase().includes(searchBlacklist.toLowerCase()) ||
    item.boletim?.toLowerCase().includes(searchBlacklist.toLowerCase()) ||
    item.motivo?.toLowerCase().includes(searchBlacklist.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Montadores</h1>
          <p className="text-muted-foreground">Gerenciar profissionais de montagem</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Novo Montador
        </Button>
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
                <TableHead>Comissão</TableHead>
                <TableHead>Auxílio Semanal</TableHead>
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
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Percent className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium">{montador.percentualComissao}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">
                      R$ {montador.auxilioSemanal.toFixed(2)}
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
                    <Button variant="ghost" size="sm">
                      Editar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
