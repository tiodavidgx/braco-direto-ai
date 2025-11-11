import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Trash2, Plus, ShieldAlert, Search } from "lucide-react";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface BlacklistItem {
  id: number;
  prestador_id?: number;
  montador_id?: number;
  prestador_nome?: string;
  montador_nome?: string;
  os_numero?: string;
  boletim?: string;
  motivo: string;
  data_adicao: string;
}

interface Entidade {
  id: number;
  nome: string;
}

export default function Blacklist() {
  const [tipoAtivo, setTipoAtivo] = useState<"prestadores" | "montadores">("prestadores");
  const [blacklistItems, setBlacklistItems] = useState<BlacklistItem[]>([]);
  const [prestadores, setPrestadores] = useState<Entidade[]>([]);
  const [montadores, setMontadores] = useState<Entidade[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  // Form states
  const [entidadeSelecionada, setEntidadeSelecionada] = useState<number | null>(null);
  const [numeros, setNumeros] = useState("");
  const [motivo, setMotivo] = useState("");

  useEffect(() => {
    carregarDados();
  }, [tipoAtivo]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      // Buscar entidades (prestadores ou montadores)
      if (tipoAtivo === "prestadores") {
        const resPrestadores = await fetch(`${import.meta.env.VITE_API_URL}/prestadores`);
        const dataPrestadores = await resPrestadores.json();
        setPrestadores(dataPrestadores);

        // Buscar blacklist de OS
        const resBlacklist = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/os`);
        const dataBlacklist = await resBlacklist.json();
        setBlacklistItems(dataBlacklist);
      } else {
        const resMontadores = await fetch(`${import.meta.env.VITE_API_URL}/montadores`);
        const dataMontadores = await resMontadores.json();
        setMontadores(dataMontadores);

        // Buscar blacklist de boletins
        const resBlacklist = await fetch(`${import.meta.env.VITE_API_URL}/blacklist/boletins`);
        const dataBlacklist = await resBlacklist.json();
        setBlacklistItems(dataBlacklist);
      }
    } catch (error) {
      toast.error("Erro ao carregar dados");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const adicionarNaBlacklist = async () => {
    if (!entidadeSelecionada || !numeros.trim()) {
      toast.error("Selecione uma entidade e insira os números");
      return;
    }

    const numerosArray = numeros.split(",").map(n => n.trim()).filter(n => n);

    try {
      for (const numero of numerosArray) {
        const endpoint = tipoAtivo === "prestadores" 
          ? `${import.meta.env.VITE_API_URL}/blacklist/os`
          : `${import.meta.env.VITE_API_URL}/blacklist/boletins`;

        const body = tipoAtivo === "prestadores"
          ? { prestador_id: entidadeSelecionada, os_numero: numero, motivo }
          : { montador_id: entidadeSelecionada, boletim: numero, motivo };

        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          const error = await response.json();
          toast.error(`${numero}: ${error.message || 'Erro ao adicionar'}`);
        } else {
          toast.success(`${numero} adicionado à blacklist`);
        }
      }

      // Limpar form e recarregar
      setNumeros("");
      setMotivo("");
      setEntidadeSelecionada(null);
      carregarDados();
    } catch (error) {
      toast.error("Erro ao adicionar à blacklist");
      console.error(error);
    }
  };

  const removerDaBlacklist = async (id: number, numero: string) => {
    try {
      const endpoint = tipoAtivo === "prestadores"
        ? `${import.meta.env.VITE_API_URL}/blacklist/os/${id}`
        : `${import.meta.env.VITE_API_URL}/blacklist/boletins/${id}`;

      const response = await fetch(endpoint, { method: "DELETE" });

      if (response.ok) {
        toast.success(`${numero} removido da blacklist`);
        carregarDados();
      } else {
        toast.error("Erro ao remover da blacklist");
      }
    } catch (error) {
      toast.error("Erro ao remover da blacklist");
      console.error(error);
    }
  };

  const itemsFiltrados = blacklistItems.filter(item => {
    const searchLower = searchTerm.toLowerCase();
    if (tipoAtivo === "prestadores") {
      return (
        item.prestador_nome?.toLowerCase().includes(searchLower) ||
        item.os_numero?.toLowerCase().includes(searchLower) ||
        item.motivo?.toLowerCase().includes(searchLower)
      );
    } else {
      return (
        item.montador_nome?.toLowerCase().includes(searchLower) ||
        item.boletim?.toLowerCase().includes(searchLower) ||
        item.motivo?.toLowerCase().includes(searchLower)
      );
    }
  });

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <ShieldAlert className="h-8 w-8 text-destructive" />
          <div>
            <h1 className="text-3xl font-bold text-foreground">Blacklist de Relatórios</h1>
            <p className="text-muted-foreground">
              Gerencie O.S. e Boletins que não devem ser enviados novamente
            </p>
          </div>
        </div>

        <Tabs value={tipoAtivo} onValueChange={(v) => setTipoAtivo(v as "prestadores" | "montadores")}>
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="prestadores">Prestadores (O.S.)</TabsTrigger>
            <TabsTrigger value="montadores">Montadores (Boletins)</TabsTrigger>
          </TabsList>

          <TabsContent value={tipoAtivo} className="space-y-6">
            {/* Card de Adicionar */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Plus className="h-5 w-5" />
                  Adicionar à Blacklist
                </CardTitle>
                <CardDescription>
                  Impeça que {tipoAtivo === "prestadores" ? "O.S." : "boletins"} específicos sejam enviados novamente
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label>
                      {tipoAtivo === "prestadores" ? "Prestador" : "Montador"}
                    </Label>
                    <Select
                      value={entidadeSelecionada?.toString()}
                      onValueChange={(v) => setEntidadeSelecionada(Number(v))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(tipoAtivo === "prestadores" ? prestadores : montadores).map((e) => (
                          <SelectItem key={e.id} value={e.id.toString()}>
                            {e.nome}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>
                      Números {tipoAtivo === "prestadores" ? "das O.S." : "dos Boletins"}
                    </Label>
                    <Input
                      placeholder="Ex: OS001, OS002, OS003"
                      value={numeros}
                      onChange={(e) => setNumeros(e.target.value)}
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
                  disabled={!entidadeSelecionada || !numeros.trim()}
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
                    <CardTitle>
                      {tipoAtivo === "prestadores" ? "O.S." : "Boletins"} na Blacklist
                    </CardTitle>
                    <CardDescription>
                      {itemsFiltrados.length} {itemsFiltrados.length === 1 ? "item" : "itens"} na blacklist
                    </CardDescription>
                  </div>
                  <div className="relative w-64">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      placeholder="Buscar..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <p className="text-center text-muted-foreground py-8">Carregando...</p>
                ) : itemsFiltrados.length === 0 ? (
                  <div className="text-center py-12">
                    <ShieldAlert className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      Nenhum item na blacklist
                    </p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>
                          {tipoAtivo === "prestadores" ? "Prestador" : "Montador"}
                        </TableHead>
                        <TableHead>
                          {tipoAtivo === "prestadores" ? "Número O.S." : "Número Boletim"}
                        </TableHead>
                        <TableHead>Motivo</TableHead>
                        <TableHead>Data de Adição</TableHead>
                        <TableHead className="text-right">Ações</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {itemsFiltrados.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-medium">
                            {tipoAtivo === "prestadores" 
                              ? item.prestador_nome 
                              : item.montador_nome}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {tipoAtivo === "prestadores" ? item.os_numero : item.boletim}
                            </Badge>
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
                              onClick={() =>
                                removerDaBlacklist(
                                  item.id,
                                  (tipoAtivo === "prestadores" ? item.os_numero : item.boletim) || ""
                                )
                              }
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
    </div>
  );
}
