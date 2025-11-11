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
import { Search, Plus, Mail, Phone, Calendar, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

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

  // Mock data - será substituído por dados reais da API
  const prestadores = [
    {
      id: 1,
      nome: "Prestadora ABC Ltda",
      email: "contato@abc.com",
      fornecedorId: "FOR123",
      telefone: "(11) 98765-4321",
      regraEnvio: "Semanal",
      diasEnvio: "Segunda-feira",
      tempoVencimento: 10,
      status: "ativo",
    },
    {
      id: 2,
      nome: "Serviços XYZ",
      email: "admin@xyz.com.br",
      fornecedorId: "FOR456",
      telefone: "(11) 91234-5678",
      regraEnvio: "Quinzenal",
      diasEnvio: "1, 15",
      tempoVencimento: 15,
      status: "ativo",
    },
    {
      id: 3,
      nome: "Prestadora 123",
      email: "contato@123.com",
      fornecedorId: "FOR789",
      telefone: "(11) 99999-8888",
      regraEnvio: "Mensal (Dia Fixo)",
      diasEnvio: "5",
      tempoVencimento: 10,
      status: "pendente",
    },
  ];

  const filteredPrestadores = prestadores.filter((p) =>
    p.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    carregarBlacklist();
  }, []);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Prestadores</h1>
          <p className="text-muted-foreground">Gerenciar empresas prestadoras de serviços</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Novo Prestador
        </Button>
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
                    <Badge variant="outline">{prestador.fornecedorId}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Calendar className="h-3 w-3 text-muted-foreground" />
                        <span className="font-medium">{prestador.regraEnvio}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{prestador.diasEnvio}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={prestador.status === "ativo" ? "default" : "secondary"}
                      className={
                        prestador.status === "ativo"
                          ? "bg-success text-success-foreground"
                          : ""
                      }
                    >
                      {prestador.status}
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
