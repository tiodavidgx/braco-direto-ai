import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Mail, FileText, Send, Clock, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function EnvioRelatorios() {
  const [tipoEnvio, setTipoEnvio] = useState<"prestador" | "montador">("prestador");
  const [sending, setSending] = useState(false);

  // Mock data - substituir por dados reais da API
  const prestadoresPendentes = [
    {
      id: 1,
      nome: "Prestadora ABC Ltda",
      email: "contato@abc.com",
      periodo: "01/11/2025 - 07/11/2025",
      valorTotal: 15480.5,
      quantidadeOS: 12,
    },
  ];

  const montadoresPendentes = [
    {
      id: 1,
      nome: "João Silva",
      email: "joao.silva@email.com",
      periodo: "Novembro/2025",
      valorTotal: 3250.0,
      quantidadeMontagens: 8,
    },
  ];

  const handleEnviarRelatorio = async (id: number, tipo: string) => {
    setSending(true);
    try {
      // Chamar API backend para gerar PDF e enviar email
      const response = await fetch(`/api/v1/relatorios/enviar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, tipo }),
      });

      if (response.ok) {
        toast.success("Relatório enviado com sucesso!");
      } else {
        toast.error("Erro ao enviar relatório");
      }
    } catch (error) {
      toast.error("Erro ao processar envio");
    } finally {
      setSending(false);
    }
  };

  const dados = tipoEnvio === "prestador" ? prestadoresPendentes : montadoresPendentes;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Envio de Relatórios</h1>
        <p className="text-muted-foreground">
          Gerar e enviar relatórios de fechamento por email
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Selecionar Tipo de Envio</CardTitle>
            <Select value={tipoEnvio} onValueChange={(v: any) => setTipoEnvio(v)}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="prestador">Prestadores</SelectItem>
                <SelectItem value="montador">Montadores</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dados.length === 0 ? (
              <div className="py-12 text-center">
                <Mail className="mx-auto h-12 w-12 text-muted-foreground" />
                <p className="mt-4 text-muted-foreground">
                  Nenhum relatório pendente para envio
                </p>
              </div>
            ) : (
              dados.map((item) => (
                <Card key={item.id} className="border-l-4 border-l-primary">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="space-y-3 flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-semibold">{item.nome}</h3>
                          <Badge variant="outline">Pendente</Badge>
                        </div>

                        <div className="grid gap-2 text-sm">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Mail className="h-4 w-4" />
                            <span>{item.email}</span>
                          </div>
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-4 w-4" />
                            <span>Período: {item.periodo}</span>
                          </div>
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <FileText className="h-4 w-4" />
                            <span>
                              {tipoEnvio === "prestador"
                                ? `${item.quantidadeOS} OS`
                                : `${(item as any).quantidadeMontagens} montagens`}
                            </span>
                          </div>
                        </div>

                        <div className="pt-2">
                          <p className="text-2xl font-bold text-primary">
                            R$ {item.valorTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                          </p>
                          <p className="text-xs text-muted-foreground">Valor total do período</p>
                        </div>
                      </div>

                      <div className="flex flex-col gap-2">
                        <Button
                          onClick={() => handleEnviarRelatorio(item.id, tipoEnvio)}
                          disabled={sending}
                          className="gap-2"
                        >
                          <Send className="h-4 w-4" />
                          {sending ? "Enviando..." : "Enviar Relatório"}
                        </Button>
                        <Button variant="outline" size="sm" className="gap-2">
                          <FileText className="h-4 w-4" />
                          Visualizar PDF
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-muted/50">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-primary/10 p-3">
              <CheckCircle2 className="h-6 w-6 text-primary" />
            </div>
            <div className="space-y-1">
              <h4 className="font-semibold">Como funciona?</h4>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li>• Sistema gera PDF com relatório de fechamento</li>
                <li>• Email é enviado automaticamente com PDF anexo</li>
                <li>• Link para upload de Nota Fiscal é incluído no email</li>
                <li>• Destinatário recebe notificação instantânea</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
