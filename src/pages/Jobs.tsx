import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { jobsService } from '@/services/jobs.service';

export default function Jobs() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  const executarJob = async () => {
    setLoading(true);
    try {
      await jobsService.executarConsultaNotas();
      toast({ title: 'Sucesso', description: 'Job iniciado!' });
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error?.message || 'Erro ao executar job',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">Jobs Automáticos</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Execução Manual - Consulta de Notas Fiscais</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={executarJob} disabled={loading}>
            {loading ? 'Executando...' : 'Executar Job'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}


  const carregarResultado = async () => {
    try {
      const data = await jobsService.getResultadoConsultaNotas();
      setResultado(data);
      setExecutando(data.status === 'running');
    } catch (error) {
      console.error('Erro ao carregar resultado:', error);
    }
  };

  useEffect(() => {
    carregarResultado();
    
    // Atualizar a cada 5 segundos se estiver executando
    const interval = setInterval(() => {
      if (executando) {
        carregarResultado();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [executando]);

  const handleExecutar = async () => {
    setCarregando(true);
    try {
      await jobsService.executarConsultaNotas();
      toast({ title: 'Sucesso', description: 'Job iniciado com sucesso!' });
      setExecutando(true);
      setTimeout(carregarResultado, 2000);
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error?.response?.data?.detail || 'Erro ao iniciar job',
        variant: 'destructive'
      });
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            Verifica uploads pendentes na API externa e cria cards no Trello
          </p>
        </div>
        <Button 
          onClick={handleExecutar} 
          disabled={executando || carregando}
        >
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
              Executado em: {new Date(resultado.last_run).toLocaleString('pt-BR')}
            </p>
          )}

          {resultado.result && (
            <div className="grid grid-cols-4 gap-4 pt-2">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Processados</p>
                <p className="text-2xl font-bold">{resultado.result.total_processados}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Arquivos</p>
                <p className="text-2xl font-bold">{resultado.result.arquivos_encontrados}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Downloads</p>
                <p className="text-2xl font-bold text-green-600">{resultado.result.downloads}</p>
              </div>
              <div className="space-y-1">
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

interface JobConfig {
  id: number;
  nome: string;
  descricao: string;
  ativo: boolean;
  intervalo_minutos: number;
  total_execucoes: number;
  total_erros: number;
  ultima_execucao: string | null;
  proxima_execucao: string | null;
  ultima_mensagem: string | null;
}

interface ServiceStatus {
  running: boolean;
  pid: number | null;
}

export default function Jobs() {
  console.log('🔍 Jobs component mounted');
  const { toast } = useToast();
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>({ running: false, pid: null });
  const [jobs, setJobs] = useState<JobConfig[]>([]);
  const [logs, setLogs] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [jobConfigs, setJobConfigs] = useState<Record<number, { ativo: boolean; intervalo: number }>>({});

  const loadServiceStatus = async () => {
    console.log('📊 Loading service status...');
    try {
      const status = await jobsService.getSchedulerStatus();
      console.log('✅ Status loaded:', status);
      setServiceStatus(status);
    } catch (error) {
      console.error('❌ Erro ao carregar status:', error);
    }
  };

  const loadJobs = async () => {
    try {
      const data: any = await jobsService.getJobs();
      const jobsArray = Array.isArray(data) ? data : [];
      setJobs(jobsArray);
      
      // Inicializar configurações locais
      const configs: Record<number, { ativo: boolean; intervalo: number }> = {};
      jobsArray.forEach((job: JobConfig) => {
        configs[job.id] = {
          ativo: job.ativo,
          intervalo: job.intervalo_minutos
        };
      });
      setJobConfigs(configs);
    } catch (error) {
      console.error('Erro ao carregar jobs:', error);
      setJobs([]);
    }
  };

  const loadLogs = async () => {
    try {
      const data: any = await jobsService.getLogs();
      setLogs(data?.logs || '');
    } catch (error) {
      console.error('Erro ao carregar logs:', error);
    }
  };

  useEffect(() => {
    loadServiceStatus();
    loadJobs();
    loadLogs();
    
    // Atualizar a cada 30 segundos
    const interval = setInterval(() => {
      loadServiceStatus();
      loadJobs();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const handleStartService = async () => {
    setLoading(true);
    try {
      await jobsService.startScheduler();
      toast({ title: 'Sucesso', description: 'Serviço iniciado com sucesso!' });
      setTimeout(() => {
        loadServiceStatus();
        loadJobs();
      }, 2000);
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error.message || 'Erro ao iniciar serviço',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStopService = async () => {
    setLoading(true);
    try {
      await jobsService.stopScheduler();
      toast({ title: 'Sucesso', description: 'Serviço parado com sucesso!' });
      setTimeout(() => {
        loadServiceStatus();
      }, 1000);
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error.message || 'Erro ao parar serviço',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReloadService = async () => {
    setLoading(true);
    try {
      await jobsService.reloadScheduler();
      toast({ title: 'Sucesso', description: 'Configurações recarregadas!' });
      setTimeout(() => {
        loadJobs();
      }, 1000);
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error.message || 'Erro ao recarregar configurações',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveJob = async (job: JobConfig) => {
    const config = jobConfigs[job.id];
    if (!config) return;
    
    if (config.ativo === job.ativo && config.intervalo === job.intervalo_minutos) {
      toast({ description: 'Nenhuma alteração detectada' });
      return;
    }
    
    try {
      await jobsService.updateJob(job.nome, {
        ativo: config.ativo,
        intervalo_minutos: config.intervalo
      });
      toast({ title: 'Sucesso', description: 'Configurações salvas!' });
      
      if (serviceStatus.running) {
        toast({ description: 'Recarregando serviço...' });
        await handleReloadService();
      } else {
        toast({ description: 'Inicie o serviço para aplicar as mudanças' });
      }
      
      loadJobs();
    } catch (error: any) {
      toast({ 
        title: 'Erro', 
        description: error.message || 'Erro ao salvar configurações',
        variant: 'destructive'
      });
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return date.toLocaleString('pt-BR');
  };

  const getTimeSince = (dateStr: string | null) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    return `Há ${hours}h ${minutes}min`;
  };

  const getTimeUntil = (dateStr: string | null) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const now = new Date();
    const diff = date.getTime() - now.getTime();
    if (diff < 0) return 'Em breve...';
    const minutes = Math.floor(diff / 60000);
    return `Em ${minutes} minutos`;
  };

  const calculateSuccessRate = (job: JobConfig) => {
    if (job.total_execucoes === 0) return 0;
    return ((job.total_execucoes - job.total_erros) / job.total_execucoes) * 100;
  };

  console.log('🔍 About to render. Jobs:', jobs.length, 'Loading:', loading);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Jobs Automáticos</h1>
          <p className="text-muted-foreground">Gerencie e monitore tarefas agendadas</p>
        </div>
      </div>

      {/* Execução Manual - Job Consulta Notas */}
      <Card>
        <CardHeader>
          <CardTitle>Execução Manual - Consulta de Notas Fiscais</CardTitle>
          <CardDescription>
            Execute o job de consulta e download de notas fiscais manualmente
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConsultaNotasControl />
        </CardContent>
      </Card>

      {/* Status do Serviço */}
      <Card>
        <CardHeader>
          <CardTitle>Status do Serviço</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {serviceStatus.running ? (
                <Badge className="flex items-center gap-2 bg-green-600 hover:bg-green-700">
                  <Activity className="h-4 w-4" />
                  Serviço Rodando {serviceStatus.pid && `(PID: ${serviceStatus.pid})`}
                </Badge>
              ) : (
                <Badge variant="destructive" className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Serviço Parado
                </Badge>
              )}
            </div>
            
            <div className="flex gap-2">
              {serviceStatus.running ? (
                <>
                  <Button 
                    variant="destructive" 
                    onClick={handleStopService} 
                    disabled={loading}
                  >
                    <Square className="h-4 w-4 mr-2" />
                    Parar Serviço
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={handleReloadService} 
                    disabled={loading}
                  >
                    <RotateCw className="h-4 w-4 mr-2" />
                    Recarregar
                  </Button>
                </>
              ) : (
                <Button 
                  onClick={handleStartService} 
                  disabled={loading}
                >
                  <Play className="h-4 w-4 mr-2" />
                  Iniciar Serviço
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Lista de Jobs */}
      <Accordion type="multiple" className="space-y-4">
        {jobs.map((job) => (
          <AccordionItem key={job.id} value={`job-${job.id}`} className="border rounded-lg">
            <AccordionTrigger className="px-6 hover:no-underline">
              <div className="flex items-center gap-3">
                {job.ativo ? (
                  <Badge variant="default">Ativo</Badge>
                ) : (
                  <Badge variant="secondary">Inativo</Badge>
                )}
                <div className="text-left">
                  <div className="font-semibold">{job.nome.toUpperCase()}</div>
                  <div className="text-sm text-muted-foreground">{job.descricao}</div>
                </div>
              </div>
            </AccordionTrigger>
            
            <AccordionContent className="px-6 pb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {/* Informações */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Activity className="h-5 w-5" />
                      Informações
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <span className="font-medium">{job.ativo ? '✅ Ativo' : '⏸️ Inativo'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Intervalo:</span>
                      <span className="font-medium">{job.intervalo_minutos} minutos</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Execuções:</span>
                      <span className="font-medium">{job.total_execucoes}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Erros:</span>
                      <span className="font-medium text-destructive">{job.total_erros}</span>
                    </div>
                    {job.total_execucoes > 0 && (
                      <div className="pt-2 border-t">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" />
                            Taxa de Sucesso:
                          </span>
                          <span className="text-lg font-bold text-green-600">
                            {calculateSuccessRate(job).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Execuções */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Clock className="h-5 w-5" />
                      Execuções
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <div className="text-muted-foreground mb-1">Última Execução:</div>
                      {job.ultima_execucao ? (
                        <>
                          <div className="font-medium">{formatDate(job.ultima_execucao)}</div>
                          <div className="text-sm text-muted-foreground">{getTimeSince(job.ultima_execucao)}</div>
                        </>
                      ) : (
                        <div className="font-medium">Nunca executado</div>
                      )}
                    </div>
                    
                    <div className="pt-2 border-t">
                      <div className="text-muted-foreground mb-1">Próxima Execução:</div>
                      {job.proxima_execucao && job.ativo ? (
                        <>
                          <div className="font-medium">{formatDate(job.proxima_execucao)}</div>
                          <div className="text-sm text-muted-foreground">{getTimeUntil(job.proxima_execucao)}</div>
                        </>
                      ) : (
                        <div className="font-medium text-muted-foreground">-</div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Última Mensagem */}
              {job.ultima_mensagem && (
                <Card className="mb-6 bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-2">
                      <span className="text-blue-600 dark:text-blue-400">💬</span>
                      <span className="text-blue-800 dark:text-blue-200">{job.ultima_mensagem}</span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Configurações */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Configurações</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id={`ativo-${job.id}`}
                        checked={jobConfigs[job.id]?.ativo ?? job.ativo}
                        onCheckedChange={(checked) => {
                          setJobConfigs(prev => ({
                            ...prev,
                            [job.id]: { ...prev[job.id], ativo: checked }
                          }));
                        }}
                      />
                      <Label htmlFor={`ativo-${job.id}`}>Ativo</Label>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor={`intervalo-${job.id}`}>Intervalo (minutos)</Label>
                      <Input
                        id={`intervalo-${job.id}`}
                        type="number"
                        min={1}
                        max={1440}
                        step={5}
                        value={jobConfigs[job.id]?.intervalo ?? job.intervalo_minutos}
                        onChange={(e) => {
                          setJobConfigs(prev => ({
                            ...prev,
                            [job.id]: { ...prev[job.id], intervalo: parseInt(e.target.value) }
                          }));
                        }}
                      />
                    </div>
                    
                    <Button onClick={() => handleSaveJob(job)} className="w-full">
                      <Save className="h-4 w-4 mr-2" />
                      Salvar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>

      {jobs.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            Nenhum job configurado
          </CardContent>
        </Card>
      )}

      {/* Logs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Logs Recentes</CardTitle>
              <CardDescription>Últimas 50 linhas do scheduler</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadLogs}>
              <RotateCw className="h-4 w-4 mr-2" />
              Atualizar
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {logs ? (
            <Textarea
              value={logs}
              readOnly
              className="font-mono text-xs h-64 resize-none"
            />
          ) : (
            <p className="text-center text-muted-foreground py-8">
              Nenhum log disponível ainda
            </p>
          )}
        </CardContent>
      </Card>

      {/* Instruções */}
      <Card>
        <CardHeader>
          <CardTitle>📖 Como Usar</CardTitle>
        </CardHeader>
        <CardContent className="prose dark:prose-invert max-w-none">
          <h3>Como Funcionam os Jobs Automáticos</h3>
          <ol>
            <li><strong>Iniciar o Serviço:</strong> Clique em "▶️ Iniciar Serviço"</li>
            <li><strong>Configurar Jobs:</strong> Ative/desative jobs e ajuste o intervalo</li>
            <li><strong>Salvar:</strong> Clique em "💾 Salvar" para aplicar</li>
            <li><strong>Monitorar:</strong> Acompanhe execuções e logs</li>
          </ol>

          <h3>Jobs Disponíveis</h3>
          <ul>
            <li><strong>consultar_notas:</strong> Consulta e baixa arquivos de notas fiscais</li>
            <li><strong>enviar_api:</strong> Envia lotes pendentes para a API</li>
          </ul>

          <h3>Dicas</h3>
          <ul>
            <li>Intervalos menores = mais frequente, mas mais processamento</li>
            <li>Recomendado: 60 minutos para consultar_notas</li>
            <li>O serviço roda em background, não precisa manter a aplicação aberta</li>
            <li>Use "🔄 Recarregar" para aplicar mudanças sem parar o serviço</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
