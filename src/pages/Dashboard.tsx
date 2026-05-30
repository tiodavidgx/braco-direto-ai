import { useEffect, useState } from "react";
import { StatCard } from "@/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  Wrench,
  DollarSign,
  FileText,
  Clock,
  AlertCircle,
  TrendingUp,
  CheckCircle2,
  Send,
} from "lucide-react";
import { apiClient } from "@/services/api";

interface PendenciaEnvio {
  montador_id: number;
  nome: string;
  identificador: string;
  email: string;
  filial: string | null;
  cidade: string | null;
  periodo: number;
  dia_previsto: number;
  dias_atraso: number;
  status: string;
  descricao: string;
}

interface PendenciasResponse {
  total: number;
  data_verificacao: string;
  pendencias: PendenciaEnvio[];
}

export default function Dashboard() {
  const [pendenciasEnvio, setPendenciasEnvio] = useState<PendenciasResponse | null>(null);
  const [loadingPendencias, setLoadingPendencias] = useState(true);

  useEffect(() => {
    carregarPendenciasEnvio();
  }, []);

  const carregarPendenciasEnvio = async () => {
    try {
      const response = await apiClient.get<PendenciasResponse>("/dashboard/pendencias-envio");
      setPendenciasEnvio(response);
    } catch (error) {
      console.error("Erro ao carregar pendências:", error);
    } finally {
      setLoadingPendencias(false);
    }
  };

  const ignorarPendencia = async (montadorId: number, periodo: number) => {
    try {
      await apiClient.post(`/dashboard/pendencias-envio/ignorar?montador_id=${montadorId}&periodo=${periodo}`);
      // Recarregar pendências após ignorar
      carregarPendenciasEnvio();
    } catch (error) {
      console.error("Erro ao ignorar pendência:", error);
    }
  };

  // Mock data - será substituído por dados reais da API
  const stats = [
    {
      title: "Prestadores Ativos",
      value: "24",
      icon: Users,
      trend: { value: "+3 este mês", isPositive: true },
      variant: "default" as const,
    },
    {
      title: "Montadores Ativos",
      value: "18",
      icon: Wrench,
      trend: { value: "+2 este mês", isPositive: true },
      variant: "success" as const,
    },
    {
      title: "Pagamentos Pendentes",
      value: "R$ 45.280",
      icon: DollarSign,
      trend: { value: "5 vencendo hoje", isPositive: false },
      variant: "warning" as const,
    },
    {
      title: "NFs Aguardando",
      value: "12",
      icon: FileText,
      variant: "default" as const,
    },
  ];

  const pendingItems = [
    {
      id: 1,
      type: "prestador",
      name: "Prestadora ABC Ltda",
      action: "Envio de relatório semanal",
      dueDate: "Hoje",
      status: "urgent",
    },
    {
      id: 2,
      type: "montador",
      name: "João Silva",
      action: "Fechamento quinzenal",
      dueDate: "Hoje",
      status: "urgent",
    },
    {
      id: 3,
      type: "prestador",
      name: "Serviços XYZ",
      action: "Upload de Nota Fiscal",
      dueDate: "Há 2 dias",
      status: "overdue",
    },
  ];

  const recentActivities = [
    {
      id: 1,
      action: "Nota Fiscal recebida",
      entity: "Prestadora ABC Ltda",
      time: "Há 15 minutos",
      icon: CheckCircle2,
      variant: "success",
    },
    {
      id: 2,
      action: "Lote de serviço criado",
      entity: "Serviços XYZ",
      time: "Há 1 hora",
      icon: FileText,
      variant: "default",
    },
    {
      id: 3,
      action: "Pagamento marcado como vencido",
      entity: "Montador Carlos Santos",
      time: "Há 2 horas",
      icon: AlertCircle,
      variant: "warning",
    },
  ];

  return (
    <div className="space-y-6 md:space-y-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm md:text-base text-muted-foreground">Visão geral do sistema de gestão</p>
      </div>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </div>

      {/* Card de Pendências de Envio de Montadores */}
      {pendenciasEnvio && pendenciasEnvio.total > 0 && (
        <Card className="border-warning/50 bg-warning/5">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
            <div className="flex items-center gap-2">
              <Send className="h-5 w-5 text-warning" />
              <CardTitle className="text-lg md:text-xl font-semibold text-warning">
                Envios de Montadores Atrasados
              </CardTitle>
            </div>
            <Badge variant="destructive" className="text-sm w-fit">
              {pendenciasEnvio.total} pendente{pendenciasEnvio.total > 1 ? "s" : ""}
            </Badge>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Verificação em: {new Date(pendenciasEnvio.data_verificacao).toLocaleDateString('pt-BR')}
            </p>
            <div className="space-y-3">
              {pendenciasEnvio.pendencias.map((pendencia) => (
                <div
                  key={`${pendencia.montador_id}-${pendencia.periodo}`}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-warning/30 bg-background p-3"
                >
                  <div className="space-y-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{pendencia.nome}</p>
                    <p className="text-sm text-muted-foreground">
                      {pendencia.descricao}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 sm:gap-3 flex-wrap sm:flex-nowrap">
                    <Badge 
                      variant={pendencia.status === "overdue" ? "destructive" : "outline"}
                      className={pendencia.status !== "overdue" ? "border-warning text-warning" : ""}
                    >
                      {pendencia.dias_atraso} dia{pendencia.dias_atraso > 1 ? "s" : ""} de atraso
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-muted-foreground hover:text-foreground"
                      onClick={() => ignorarPendencia(pendencia.montador_id, pendencia.periodo)}
                    >
                      Ignorar
                    </Button>
                    <AlertCircle className={`h-4 w-4 ${pendencia.status === "overdue" ? "text-destructive" : "text-warning"}`} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <CardTitle className="text-lg md:text-xl font-semibold">Pendências de Hoje</CardTitle>
            <Badge variant="destructive" className="text-sm w-fit">
              {pendingItems.filter((i) => i.status === "urgent").length} urgentes
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {pendingItems.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-border bg-muted/50 p-3 sm:p-4"
                >
                  <div className="space-y-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{item.name}</p>
                    <p className="text-sm text-muted-foreground">{item.action}</p>
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <span
                        className={`text-xs ${
                          item.status === "overdue"
                            ? "text-destructive font-medium"
                            : item.status === "urgent"
                            ? "text-warning font-medium"
                            : "text-muted-foreground"
                        }`}
                      >
                        {item.dueDate}
                      </span>
                    </div>
                  </div>
                  <Button size="sm" variant="outline" className="w-full sm:w-auto">
                    Processar
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg md:text-xl font-semibold">Atividades Recentes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivities.map((activity) => {
                const Icon = activity.icon;
                return (
                  <div key={activity.id} className="flex items-start gap-4">
                    <div
                      className={`rounded-lg p-2 ${
                        activity.variant === "success"
                          ? "bg-success/10 text-success"
                          : activity.variant === "warning"
                          ? "bg-warning/10 text-warning"
                          : "bg-primary/10 text-primary"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-medium text-foreground">{activity.action}</p>
                      <p className="text-sm text-muted-foreground">{activity.entity}</p>
                      <p className="text-xs text-muted-foreground">{activity.time}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg md:text-xl font-semibold">Estatísticas do Mês</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">Lotes Processados</p>
                <p className="text-2xl font-bold text-foreground">38</p>
              </div>
              <div className="flex items-center gap-2 text-success">
                <TrendingUp className="h-4 w-4" />
                <span className="text-sm font-medium">+12% vs mês anterior</span>
              </div>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full w-[76%] bg-primary"></div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
