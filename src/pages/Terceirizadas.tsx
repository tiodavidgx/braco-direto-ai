import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { Plus, Pencil, Trash2, Building2, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface Terceirizada {
  id: number;
  nome: string;
  telefone: string | null;
  email: string | null;
  cnpj: string | null;
  percentual_montagem: number;
  percentual_assistencia: number;
  percentual_desmontagem: number;
  ativo: boolean;
  observacoes: string | null;
}

export default function Terceirizadas() {
  const navigate = useNavigate();
  const [terceirizadas, setTerceirizadas] = useState<Terceirizada[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editando, setEditando] = useState<Terceirizada | null>(null);

  const [form, setForm] = useState({
    nome: "",
    telefone: "",
    email: "",
    cnpj: "",
    percentual_montagem: "5.00",
    percentual_assistencia: "5.00",
    percentual_desmontagem: "5.00",
    ativo: true,
    observacoes: "",
  });

  useEffect(() => {
    carregar();
  }, []);

  const carregar = async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<Terceirizada[]>("/terceirizadas");
      setTerceirizadas(data || []);
    } catch (error) {
      toast.error("Erro ao carregar terceirizadas");
    } finally {
      setLoading(false);
    }
  };

  const abrirNovo = () => {
    setEditando(null);
    setForm({
      nome: "", telefone: "", email: "", cnpj: "",
      percentual_montagem: "5.00", percentual_assistencia: "5.00",
      percentual_desmontagem: "5.00", ativo: true, observacoes: "",
    });
    setDialogOpen(true);
  };

  const abrirEdicao = (t: Terceirizada) => {
    setEditando(t);
    setForm({
      nome: t.nome,
      telefone: t.telefone || "",
      email: t.email || "",
      cnpj: t.cnpj || "",
      percentual_montagem: t.percentual_montagem?.toString() || "5.00",
      percentual_assistencia: t.percentual_assistencia?.toString() || "5.00",
      percentual_desmontagem: t.percentual_desmontagem?.toString() || "5.00",
      ativo: t.ativo,
      observacoes: t.observacoes || "",
    });
    setDialogOpen(true);
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast.error("Nome é obrigatório");
      return;
    }

    const payload = {
      nome: form.nome,
      telefone: form.telefone || null,
      email: form.email || null,
      cnpj: form.cnpj || null,
      percentual_montagem: parseFloat(form.percentual_montagem) || 5,
      percentual_assistencia: parseFloat(form.percentual_assistencia) || 5,
      percentual_desmontagem: parseFloat(form.percentual_desmontagem) || 5,
      ativo: form.ativo,
      observacoes: form.observacoes || null,
    };

    try {
      if (editando) {
        await apiClient.put(`/terceirizadas/${editando.id}`, payload);
        toast.success("Terceirizada atualizada!");
      } else {
        await apiClient.post("/terceirizadas", payload);
        toast.success("Terceirizada criada!");
      }
      setDialogOpen(false);
      carregar();
    } catch (error: any) {
      toast.error(error.message || "Erro ao salvar");
    }
  };

  const excluir = async (id: number) => {
    if (!confirm("Tem certeza? Se houver montadores vinculados, a terceirizada será apenas desativada.")) return;
    try {
      await apiClient.delete(`/terceirizadas/${id}`);
      toast.success("Terceirizada removida/desativada");
      carregar();
    } catch (error: any) {
      toast.error(error.message || "Erro ao excluir");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Terceirizadas</h1>
          <p className="text-muted-foreground mt-1">Empresas que intermediam montadores</p>
        </div>
        <Button onClick={abrirNovo} className="gap-2">
          <Plus className="h-4 w-4" /> Nova Terceirizada
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>CNPJ</TableHead>
                <TableHead>Telefone</TableHead>
                <TableHead className="text-right">% Montagem</TableHead>
                <TableHead className="text-right">% Assistência</TableHead>
                <TableHead className="text-right">% Desmontagem</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-28">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {terceirizadas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    Nenhuma terceirizada cadastrada
                  </TableCell>
                </TableRow>
              ) : (
                terceirizadas.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-medium">{t.nome}</TableCell>
                    <TableCell className="text-xs font-mono">{t.cnpj || "-"}</TableCell>
                    <TableCell className="text-xs">{t.telefone || "-"}</TableCell>
                    <TableCell className="text-right">{t.percentual_montagem}%</TableCell>
                    <TableCell className="text-right">{t.percentual_assistencia}%</TableCell>
                    <TableCell className="text-right">{t.percentual_desmontagem}%</TableCell>
                    <TableCell>
                      <Badge variant={t.ativo ? "default" : "secondary"}>
                        {t.ativo ? "Ativa" : "Inativa"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => abrirEdicao(t)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => navigate(`/terceirizadas/${t.id}/pagamentos`)}>
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => excluir(t.id)}>
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Dialog Criar/Editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editando ? "Editar" : "Nova"} Terceirizada</DialogTitle>
            <DialogDescription>
              {editando ? "Altere os dados da terceirizada" : "Cadastre uma nova empresa terceirizada"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div>
              <Label>Nome *</Label>
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>CNPJ</Label>
                <Input value={form.cnpj} onChange={(e) => setForm({ ...form, cnpj: e.target.value })} />
              </div>
              <div>
                <Label>Telefone</Label>
                <Input value={form.telefone} onChange={(e) => setForm({ ...form, telefone: e.target.value })} />
              </div>
            </div>
            <div>
              <Label>Email</Label>
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>

            <div className="border-t pt-3">
              <Label className="font-medium">Comissões (%)</Label>
              <div className="grid grid-cols-3 gap-2 mt-1">
                <div>
                  <Label className="text-xs">% Montagem</Label>
                  <Input
                    type="number" step="0.01"
                    value={form.percentual_montagem}
                    onChange={(e) => setForm({ ...form, percentual_montagem: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="text-xs">% Assistência</Label>
                  <Input
                    type="number" step="0.01"
                    value={form.percentual_assistencia}
                    onChange={(e) => setForm({ ...form, percentual_assistencia: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="text-xs">% Desmontagem</Label>
                  <Input
                    type="number" step="0.01"
                    value={form.percentual_desmontagem}
                    onChange={(e) => setForm({ ...form, percentual_desmontagem: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch checked={form.ativo} onCheckedChange={(c) => setForm({ ...form, ativo: c })} />
              <Label>Ativo</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={salvar}>{editando ? "Salvar" : "Criar"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
