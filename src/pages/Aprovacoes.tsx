import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { Check, X, Clock, Shield } from "lucide-react";

interface Aprovacao {
  id: number;
  montador_id: number;
  montador_nome: string;
  montador_identificador: string;
  usuario_id: number;
  usuario_nome: string;
  campo: string;
  valor_antigo: string | null;
  valor_novo: string;
  status: string;
  created_at: string;
}

export default function Aprovacoes() {
  const [aprovacoes, setAprovacoes] = useState<Aprovacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejeitando, setRejeitando] = useState<number | null>(null);
  const [motivoRejeicao, setMotivoRejeicao] = useState("");

  useEffect(() => {
    carregar();
  }, []);

  const carregar = async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<Aprovacao[]>("/aprovacoes/montadores?status=pendente");
      setAprovacoes(data || []);
    } catch (error) {
      toast.error("Erro ao carregar aprovações");
    } finally {
      setLoading(false);
    }
  };

  const aprovar = async (id: number) => {
    try {
      await apiClient.post(`/aprovacoes/montadores/${id}/aprovar`, {});
      toast.success("Alteração aprovada e aplicada!");
      carregar();
    } catch (error: any) {
      toast.error(error.message || "Erro ao aprovar");
    }
  };

  const rejeitar = async (id: number) => {
    try {
      await apiClient.post(`/aprovacoes/montadores/${id}/rejeitar`, {
        motivo_rejeicao: motivoRejeicao || "Rejeitado pelo administrador",
      });
      toast.success("Alteração rejeitada");
      setRejeitando(null);
      setMotivoRejeicao("");
      carregar();
    } catch (error: any) {
      toast.error(error.message || "Erro ao rejeitar");
    }
  };

  const formatCampo = (campo: string) => {
    const nomes: Record<string, string> = {
      percentual_montagem: "% Montagem",
      percentual_assistencia: "% Assistência",
      percentual_desmontagem: "% Desmontagem",
      auxilio_semanal: "Auxílio Semanal",
      dias_envio_mes: "Dias de Envio",
      dia_fechamento: "Dia Fechamento",
      prazo_pagamento_dias: "Prazo Pagamento",
      envio_automatico: "Envio Automático",
    };
    return nomes[campo] || campo;
  };

  const formatValor = (valor: string | null) => {
    if (valor === null || valor === undefined) return "—";
    if (valor === "true") return "Sim";
    if (valor === "false") return "Não";
    return String(valor);
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
          <h1 className="text-2xl font-bold tracking-tight">Aprovações Pendentes</h1>
          <p className="text-muted-foreground mt-1">
            Edições em campos críticos que precisam da sua revisão
          </p>
        </div>
        <Badge variant="outline" className="text-lg px-3 py-1">
          {aprovacoes.length} pendente{aprovacoes.length !== 1 ? "s" : ""}
        </Badge>
      </div>

      {aprovacoes.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg">Nenhuma aprovação pendente</p>
            <p className="text-sm mt-1">Todas as edições foram revisadas</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Montador</TableHead>
                  <TableHead>Campo</TableHead>
                  <TableHead>De</TableHead>
                  <TableHead>Para</TableHead>
                  <TableHead>Solicitante</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead className="w-32">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {aprovacoes.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="font-medium">{a.montador_nome}</TableCell>
                    <TableCell>{formatCampo(a.campo)}</TableCell>
                    <TableCell className="text-muted-foreground text-xs">{formatValor(a.valor_antigo)}</TableCell>
                    <TableCell className="font-semibold text-xs">{formatValor(a.valor_novo)}</TableCell>
                    <TableCell className="text-xs">{a.usuario_nome}</TableCell>
                    <TableCell className="text-xs">
                      {new Date(a.created_at).toLocaleDateString("pt-BR")}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-green-600"
                          onClick={() => aprovar(a.id)}
                          title="Aprovar"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-600"
                          onClick={() => setRejeitando(a.id)}
                          title="Rejeitar"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Dialog de rejeição */}
      <Dialog open={rejeitando !== null} onOpenChange={() => setRejeitando(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rejeitar Alteração</DialogTitle>
            <DialogDescription>Informe o motivo da rejeição</DialogDescription>
          </DialogHeader>
          <Textarea
            value={motivoRejeicao}
            onChange={(e) => setMotivoRejeicao(e.target.value)}
            placeholder="Motivo da rejeição..."
            rows={3}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejeitando(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={() => rejeitando && rejeitar(rejeitando)}>
              Rejeitar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
