import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Activity, Play, CheckCircle, XCircle, Clock, Settings } from 'lucide-react';
import { jobsService } from '@/services/jobs.service';
import { useToast } from '@/hooks/use-toast';

// Componente para execução manual do job
function ConsultaNotasControl() {
  const { toast } = useToast();
  const [executando, setExecutando] = useState(false);
  const [resultado, setResultado] = useState<any>(null);

  const carregarResultado = async () => {
    try {
      const data = await jobsService.getResultadoConsultaNotas();
      setResultado(data);
      setExecutando(data.status === 'running');
    } catch (error) {
      console.error('Erro:', error);
    }
  };

  useEffect(() => {
    carregarResultado();
    const interval = setInterval(() => {
      if (executando) carregarResultado();
    }, 5000);
    return () => clearInterval(interval);
  }, [executando]);

  const handleExecutar = async () => {
    try {
      await jobsService.executarConsultaNotas();
      toast({ title: 'Sucesso', description: 'Job iniciado!' });
      setExecutando(true);
      setTimeout(carregarResultado, 2000);
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error?.response?.data?.detail || 'Erro ao iniciar',
        variant: 'destructive'
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Verifica uploads pendentes e cria cards no Trello
        </p>
        <Button onClick={handleExecutar} disabled={executando}>
          <Play className="h-4 w-4 mr-2" />
          {executando ? 'Executando...' : 'Executar Agora'}
        </Button>
      </div>

      {resultado && resultado.status !== 'never_run' && (
        <div className="border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">Último Resultado</h4>
            {resultado.status === 'running' ? (
              <Badge className="bg-blue-600">
                <Activity className="h-3 w-3 mr-1 animate-pulse" />
                Executando
              </Badge>
            ) : resultado.error ? (
              <Badge variant="destructive">
                <XCircle className="h-3 w-3 mr-1" />
                Erro
              </Badge>
            ) : (
              <Badge className="bg-green-600">
                <CheckCircle className="h-3 w-3 mr-1" />
                Concluído
              </Badge>
            )}
          </div>

          {resultado.last_run && (
            <p className="text-sm text-muted-foreground">
              Executado: {new Date(resultado.last_run).toLocaleString('pt-BR')}
            </p>
          )}

          {resultado.result && (
            <div className="grid grid-cols-4 gap-4 pt-2">
              <div>
                <p className="text-xs text-muted-foreground">Processados</p>
                <p className="text-2xl font-bold">{resultado.result.total_processados}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Arquivos</p>
                <p className="text-2xl font-bold">{resultado.result.arquivos_encontrados}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Downloads</p>
                <p className="text-2xl font-bold text-green-600">{resultado.result.downloads}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Erros</p>
                <p className="text-2xl font-bold text-red-600">{resultado.result.erros}</p>
              </div>
            </div>
          )}

          {resultado.error && (
            <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
              <strong>Erro:</strong> {resultado.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Componente para configuração automática
function JobConfigControl() {
  const { toast } = useToast();
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null);

  const carregarConfig = async () => {
    try {
      const data = await jobsService.getJobsConfig();
      console.log('Jobs carregados:', data);
      
      if (data && data.length > 0) {
        // Buscar especificamente o job consulta_notas
        const job = data.find((j: any) => j.nome === 'consulta_notas');
        if (job) {
          setConfig(job);
        } else {
          setConfig(data[0]); // Fallback para primeiro job
        }
      }
      
      // Carregar status do scheduler
      const status = await jobsService.getStatus();
      setSchedulerStatus(status);
      
    } catch (error) {
      console.error('Erro ao carregar config:', error);
      toast({
        title: 'Erro',
        description: 'Não foi possível carregar as configurações',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarConfig();
    // Atualizar a cada 30 segundos
    const interval = setInterval(carregarConfig, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSalvar = async () => {
    if (!config) return;
    
    try {
      await jobsService.updateJobConfig(config.nome, {
        ativo: config.ativo,
        intervalo_minutos: config.intervalo_minutos
      });
      
      toast({ 
        title: 'Sucesso', 
        description: 'Configuração atualizada! O scheduler foi recarregado.' 
      });
      
      // Recarregar após salvar
      setTimeout(carregarConfig, 1000);
      
    } catch (error: any) {
      console.error('Erro ao salvar:', error);
      toast({ 
        title: 'Erro', 
        description: error?.response?.data?.detail || 'Erro ao salvar',
        variant: 'destructive'
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Activity className="h-4 w-4 animate-spin" />
        Carregando configurações...
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          ⚠️ Nenhuma configuração encontrada. Verifique se o backend está rodando.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status do Scheduler */}
      <div className="bg-slate-50 border rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="text-sm font-semibold">Status do Scheduler</h4>
            <p className="text-xs text-muted-foreground">
              {schedulerStatus?.scheduler?.running 
                ? '✅ Scheduler está rodando' 
                : '⚠️ Scheduler não está ativo'}
            </p>
          </div>
          {schedulerStatus?.scheduler?.jobs && schedulerStatus.scheduler.jobs.length > 0 && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Próxima Execução</p>
              <p className="text-sm font-semibold">
                {schedulerStatus.scheduler.jobs[0]?.next_run 
                  ? new Date(schedulerStatus.scheduler.jobs[0].next_run).toLocaleString('pt-BR')
                  : 'Não agendado'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Controle de Ativação */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor="ativo">Execução Automática</Label>
            <Switch
              id="ativo"
              checked={config.ativo}
              onCheckedChange={(checked) => setConfig({ ...config, ativo: checked })}
            />
            {config.ativo ? (
              <Badge className="bg-green-600">Ativo</Badge>
            ) : (
              <Badge variant="secondary">Inativo</Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {config.ativo 
              ? 'O job será executado automaticamente no intervalo configurado'
              : 'Ative para começar a execução automática'}
          </p>
        </div>
      </div>

      {/* Configuração de Intervalo */}
      <div className="space-y-2">
        <Label htmlFor="intervalo">Intervalo de Execução (minutos)</Label>
        <div className="flex items-center gap-4">
          <Input
            id="intervalo"
            type="number"
            min="1"
            max="1440"
            value={config.intervalo_minutos}
            onChange={(e) => setConfig({ ...config, intervalo_minutos: parseInt(e.target.value) || 1 })}
            className="w-32"
          />
          <span className="text-sm text-muted-foreground">
            {config.intervalo_minutos < 60 
              ? `${config.intervalo_minutos} minuto${config.intervalo_minutos > 1 ? 's' : ''}`
              : config.intervalo_minutos === 60
              ? '1 hora'
              : `${Math.floor(config.intervalo_minutos / 60)}h ${config.intervalo_minutos % 60}min`}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Recomendado: 60 minutos (1 hora) ou mais
        </p>
      </div>

      {/* Estatísticas */}
      <div className="border-t pt-4 space-y-4">
        <h4 className="text-sm font-semibold">Estatísticas e Histórico</h4>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-3">
            <p className="text-xs text-blue-600 font-medium">Total Execuções</p>
            <p className="text-2xl font-bold text-blue-700">{config.total_execucoes || 0}</p>
          </div>
          <div className="bg-red-50 rounded-lg p-3">
            <p className="text-xs text-red-600 font-medium">Erros</p>
            <p className="text-2xl font-bold text-red-700">{config.total_erros || 0}</p>
          </div>
          <div className="bg-green-50 rounded-lg p-3">
            <p className="text-xs text-green-600 font-medium">Taxa Sucesso</p>
            <p className="text-2xl font-bold text-green-700">
              {config.total_execucoes > 0 
                ? Math.round((1 - (config.total_erros || 0) / config.total_execucoes) * 100)
                : 100}%
            </p>
          </div>
        </div>

        {config.ultima_execucao && (
          <div className="space-y-2 bg-slate-50 rounded-lg p-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground font-medium">Última Execução</p>
                <p className="text-sm font-semibold">{new Date(config.ultima_execucao).toLocaleString('pt-BR')}</p>
              </div>
              {config.proxima_execucao && (
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Próxima Execução</p>
                  <p className="text-sm font-semibold">{new Date(config.proxima_execucao).toLocaleString('pt-BR')}</p>
                </div>
              )}
            </div>
            {config.ultima_mensagem && (
              <div className="pt-2 border-t">
                <p className="text-xs text-muted-foreground font-medium">Última Mensagem</p>
                <p className="text-sm">{config.ultima_mensagem}</p>
              </div>
            )}
          </div>
        )}

        {!config.ultima_execucao && (
          <div className="text-sm text-muted-foreground bg-slate-50 rounded-lg p-3 text-center">
            Nenhuma execução automática realizada ainda
          </div>
        )}
      </div>

      {/* Botão Salvar */}
      <Button onClick={handleSalvar} className="w-full" size="lg">
        <Settings className="h-4 w-4 mr-2" />
        Salvar Configuração
      </Button>
    </div>
  );
}

// Componente para Trello Montadores
function TrelloMontadoresControl() {
  const { toast } = useToast();
  const [executando, setExecutando] = useState(false);
  const [resultado, setResultado] = useState<any>(null);

  const carregarResultado = async () => {
    try {
      const data = await jobsService.getResultadoTrelloMontadores();
      setResultado(data);
      setExecutando(data.status === 'running');
    } catch (error) {
      console.error('Erro:', error);
    }
  };

  useEffect(() => {
    carregarResultado();
    const interval = setInterval(() => {
      if (executando) carregarResultado();
    }, 3000);
    return () => clearInterval(interval);
  }, [executando]);

  const handleExecutar = async () => {
    try {
      await jobsService.executarTrelloMontadores();
      toast({ title: 'Sucesso', description: 'Job de Trello iniciado!' });
      setExecutando(true);
      setTimeout(carregarResultado, 2000);
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error?.response?.data?.detail || 'Erro ao iniciar',
        variant: 'destructive'
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <Button 
          onClick={handleExecutar} 
          disabled={executando}
          className="w-full"
        >
          {executando ? (
            <>
              <Activity className="mr-2 h-4 w-4 animate-spin" />
              Processando Montadores...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              Processar Montadores
            </>
          )}
        </Button>
      </div>

      {resultado && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            {resultado.status === 'running' && (
              <Badge variant="default" className="gap-1">
                <Activity className="h-3 w-3 animate-spin" />
                Em execução
              </Badge>
            )}
            {resultado.status === 'completed' && resultado.result?.success && (
              <Badge variant="default" className="gap-1 bg-green-600">
                <CheckCircle className="h-3 w-3" />
                Concluído
              </Badge>
            )}
            {resultado.status === 'completed' && !resultado.result?.success && (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="h-3 w-3" />
                Erro
              </Badge>
            )}
          </div>

          {resultado.last_run && (
            <p className="text-sm text-muted-foreground">
              Última execução: {new Date(resultado.last_run).toLocaleString('pt-BR')}
            </p>
          )}

          {resultado.result?.stdout && (
            <div className="bg-muted p-3 rounded-md">
              <p className="text-xs font-mono whitespace-pre-wrap max-h-64 overflow-y-auto">
                {resultado.result.stdout}
              </p>
            </div>
          )}

          {resultado.error && (
            <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
              <strong>Erro:</strong> {resultado.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Jobs() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Jobs Automáticos</h1>
        <p className="text-muted-foreground">Gerencie e monitore tarefas agendadas</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            <div>
              <CardTitle>Agendamento Automático</CardTitle>
              <CardDescription>
                Configure a execução automática do job de consulta de notas
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <JobConfigControl />
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Execução Manual</CardTitle>
          <CardDescription>
            Execute o job imediatamente para testes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConsultaNotasControl />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-orange-600" />
            <div>
              <CardTitle>Cards Trello - Montadores</CardTitle>
              <CardDescription>
                Processa montadores e cria cards no Trello com anexos
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <TrelloMontadoresControl />
        </CardContent>
      </Card>
    </div>
  );
}
