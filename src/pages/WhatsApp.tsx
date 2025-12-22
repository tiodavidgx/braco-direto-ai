import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { RefreshCw, MessageSquare, Settings, Phone, Send, Users, Wrench, List, QrCode, Loader2 } from "lucide-react";
import { whatsappService } from "@/services/whatsapp.service";
import { prestadoresService } from "@/services/prestadores.service";
import { montadoresService } from "@/services/montadores.service";

export default function WhatsApp() {
  const { toast } = useToast();
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [tipoEnvio, setTipoEnvio] = useState("manual");
  const [numero, setNumero] = useState("");
  const [numeros, setNumeros] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [delay, setDelay] = useState(3);
  const [prestadores, setPrestadores] = useState<any[]>([]);
  const [montadores, setMontadores] = useState<any[]>([]);
  const [prestadorSelecionado, setPrestadorSelecionado] = useState("");
  const [montadorSelecionado, setMontadorSelecionado] = useState("");
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-refresh enquanto aguarda QR Code ou durante inicialização
  useEffect(() => {
    // Busca status inicial
    atualizarStatusSilencioso();

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);

  // Configura auto-refresh baseado no status
  useEffect(() => {
    // Limpa intervalo anterior
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
      refreshIntervalRef.current = null;
    }

    // Se está aguardando QR Code ou inicializando, faz refresh a cada 2 segundos
    if (status?.server_running && (status?.hasQrCode || status?.status === 'initializing' || status?.status === 'qr_ready')) {
      refreshIntervalRef.current = setInterval(() => {
        atualizarStatusSilencioso();
      }, 2000);
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [status?.server_running, status?.hasQrCode, status?.status]);

  const atualizarStatusSilencioso = async () => {
    try {
      const data = await whatsappService.getStatus();
      setStatus(data);
    } catch (error) {
      // Silencioso - não mostra erro
    }
  };

  const atualizarStatus = async () => {
    setLoading(true);
    try {
      const data = await whatsappService.getStatus();
      setStatus(data);
    } catch (error) {
      toast({
        title: "Erro",
        description: "Não foi possível conectar ao serviço WhatsApp",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const iniciarServidor = async () => {
    setLoading(true);
    try {
      const response = await whatsappService.startServer();
      toast({
        title: "Sucesso",
        description: response.message || "Servidor WhatsApp iniciado",
      });
      setTimeout(() => atualizarStatus(), 2000);
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao iniciar servidor",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const pararServidor = async () => {
    setLoading(true);
    try {
      const response = await whatsappService.stopServer();
      toast({
        title: "Sucesso",
        description: response.message || "Servidor WhatsApp parado",
      });
      setTimeout(() => atualizarStatus(), 1000);
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao parar servidor",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const processarFila = async () => {
    setLoading(true);
    try {
      const response: any = await whatsappService.processarFila();
      toast({
        title: "Fila Processada",
        description: `${response.enviados || 0} mensagens enviadas de ${response.processados || 0} pendentes`,
      });
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao processar fila",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const carregarPrestadores = async () => {
    try {
      const response: any = await prestadoresService.getAll();
      const lista = response.data || [];
      setPrestadores(lista.filter((p: any) => p.telefone));
    } catch (error) {
      console.error("Erro ao carregar prestadores:", error);
    }
  };

  const carregarMontadores = async () => {
    try {
      const response: any = await montadoresService.getAll();
      const lista = response.data || [];
      setMontadores(lista.filter((m: any) => m.telefone));
    } catch (error) {
      console.error("Erro ao carregar montadores:", error);
    }
  };

  const enviarMensagem = async () => {
    if (!mensagem.trim()) {
      toast({ title: "Erro", description: "Digite uma mensagem", variant: "destructive" });
      return;
    }

    let destinatarios: string[] = [];
    
    if (tipoEnvio === "manual") {
      if (!numero) {
        toast({ title: "Erro", description: "Digite um número", variant: "destructive" });
        return;
      }
      destinatarios = [numero];
    } else if (tipoEnvio === "prestador") {
      const prest = prestadores.find(p => p.id === prestadorSelecionado);
      if (!prest) {
        toast({ title: "Erro", description: "Selecione um prestador", variant: "destructive" });
        return;
      }
      destinatarios = [prest.telefone];
    } else if (tipoEnvio === "montador") {
      const mont = montadores.find(m => m.id === montadorSelecionado);
      if (!mont) {
        toast({ title: "Erro", description: "Selecione um montador", variant: "destructive" });
        return;
      }
      destinatarios = [mont.telefone];
    } else if (tipoEnvio === "lista") {
      destinatarios = numeros.split('\n').filter(n => n.trim());
      if (destinatarios.length === 0) {
        toast({ title: "Erro", description: "Digite ao menos um número", variant: "destructive" });
        return;
      }
    }

    setLoading(true);
    try {
      if (destinatarios.length === 1) {
        await whatsappService.sendMessage(destinatarios[0], mensagem);
        toast({ title: "Sucesso", description: "Mensagem enviada!" });
      } else {
        await whatsappService.sendBulk(destinatarios, mensagem, delay * 1000);
        toast({ title: "Sucesso", description: `${destinatarios.length} mensagens enviadas!` });
      }
      setMensagem("");
      setNumero("");
      setNumeros("");
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao enviar mensagem",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">WhatsApp</h1>
          <p className="text-muted-foreground">Gerencie o envio de mensagens WhatsApp</p>
        </div>
      </div>

      <Tabs defaultValue="status" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="status">
            <Phone className="mr-2 h-4 w-4" />
            Status & Conexão
          </TabsTrigger>
          <TabsTrigger value="enviar" onClick={() => {
            carregarPrestadores();
            carregarMontadores();
          }}>
            <Send className="mr-2 h-4 w-4" />
            Enviar Mensagens
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings className="mr-2 h-4 w-4" />
            Configurações
          </TabsTrigger>
        </TabsList>

        {/* TAB STATUS */}
        <TabsContent value="status" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Status da Conexão</CardTitle>
                <Button onClick={atualizarStatus} disabled={loading} size="sm">
                  <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  Atualizar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Serviço</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {!status && (
                      <Badge variant="outline">Clique em Atualizar</Badge>
                    )}
                    {status?.server_running === false && (
                      <Badge variant="destructive">Offline</Badge>
                    )}
                    {status?.status === "connected" && (
                      <Badge className="bg-green-500">Conectado</Badge>
                    )}
                    {status?.status === "qr_ready" && (
                      <Badge variant="secondary" className="bg-orange-500 text-white">Aguardando QR</Badge>
                    )}
                    {status?.status === "initializing" && (
                      <Badge variant="secondary">Inicializando...</Badge>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Autenticação</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {status?.hasQrCode && (
                      <Badge variant="outline" className="bg-orange-500 text-white">QR Code Pronto</Badge>
                    )}
                    {status?.status === "connected" && (
                      <Badge className="bg-green-500">Autenticado</Badge>
                    )}
                    {!status?.hasQrCode && status?.status !== "connected" && status && (
                      <Badge variant="secondary">-</Badge>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Usuário</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {status?.info?.name ? (
                      <p className="text-sm text-foreground truncate">{status.info.name}</p>
                    ) : (
                      <Badge variant="secondary">N/A</Badge>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Controles do Servidor */}
              <div className="flex gap-2 justify-center flex-wrap">
                {status?.server_running === false ? (
                  <Button onClick={iniciarServidor} disabled={loading} className="bg-green-600 hover:bg-green-700">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Iniciar Servidor WhatsApp
                  </Button>
                ) : (
                  <>
                    <Button onClick={pararServidor} disabled={loading} variant="destructive">
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Parar Servidor
                    </Button>
                    {status?.status === "connected" && (
                      <Button onClick={processarFila} disabled={loading} variant="outline">
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Processar Fila Pendente
                      </Button>
                    )}
                  </>
                )}
              </div>

              {/* QR Code */}
              {status?.server_running && status?.hasQrCode && (
                <div className="flex flex-col items-center space-y-4">
                  <Separator />
                  <div className="flex items-center gap-2">
                    <QrCode className="h-5 w-5 text-green-600" />
                    <h3 className="text-lg font-semibold">Escaneie o QR Code</h3>
                  </div>
                  
                  {status?.qrCode ? (
                    <div className="bg-white p-6 rounded-xl shadow-lg border-2 border-green-500">
                      <img src={status.qrCode} alt="QR Code WhatsApp" className="w-72 h-72" />
                    </div>
                  ) : (
                    <div className="bg-white p-6 rounded-xl shadow-lg border flex items-center justify-center w-72 h-72">
                      <Loader2 className="h-8 w-8 animate-spin text-green-500" />
                    </div>
                  )}
                  
                  <div className="text-sm text-muted-foreground max-w-md text-center space-y-1">
                    <p className="font-medium text-foreground">Como conectar:</p>
                    <p>1. Abra o WhatsApp no celular</p>
                    <p>2. Vá em <strong>Menu → Aparelhos conectados</strong></p>
                    <p>3. Toque em <strong>"Conectar um aparelho"</strong></p>
                    <p>4. Aponte a câmera para este código</p>
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Aguardando leitura do QR Code...</span>
                  </div>
                </div>
              )}

              {/* Estado de inicialização */}
              {status?.server_running && status?.status === 'initializing' && !status?.hasQrCode && (
                <div className="flex flex-col items-center space-y-4 py-8">
                  <Loader2 className="h-12 w-12 animate-spin text-green-500" />
                  <p className="text-muted-foreground">Iniciando WhatsApp...</p>
                  <p className="text-xs text-muted-foreground">O QR Code aparecerá em instantes</p>
                </div>
              )}

              {status?.status === "connected" && (
                <Alert className="bg-green-50 border-green-200">
                  <AlertDescription className="text-green-800">
                    <p className="font-semibold">✅ WhatsApp Conectado!</p>
                    <p>Você já pode enviar mensagens pela aba "Enviar Mensagens"</p>
                    {status?.info && (
                      <p className="mt-2">👤 Conectado como: <strong>{status.info.name}</strong> ({status.info.number})</p>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              {status?.server_running === false && (
                <Alert>
                  <AlertDescription className="space-y-2">
                    <p className="font-semibold">Como Conectar:</p>
                    <ol className="list-decimal list-inside space-y-1 text-sm">
                      <li>Clique no botão "Iniciar Servidor WhatsApp" acima</li>
                      <li>Aguarde o QR Code aparecer nesta página</li>
                      <li>Escaneie o QR Code com WhatsApp → Aparelhos conectados</li>
                      <li>Pronto! O WhatsApp estará conectado</li>
                    </ol>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB ENVIAR */}
        <TabsContent value="enviar" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Enviar Mensagem</CardTitle>
              <CardDescription>
                Escolha os destinatários e envie mensagens WhatsApp
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <Label>Tipo de Envio</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <Button
                    variant={tipoEnvio === "manual" ? "default" : "outline"}
                    onClick={() => setTipoEnvio("manual")}
                    className="w-full"
                  >
                    <Phone className="mr-2 h-4 w-4" />
                    Manual
                  </Button>
                  <Button
                    variant={tipoEnvio === "prestador" ? "default" : "outline"}
                    onClick={() => setTipoEnvio("prestador")}
                    className="w-full"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    Prestador
                  </Button>
                  <Button
                    variant={tipoEnvio === "montador" ? "default" : "outline"}
                    onClick={() => setTipoEnvio("montador")}
                    className="w-full"
                  >
                    <Wrench className="mr-2 h-4 w-4" />
                    Montador
                  </Button>
                  <Button
                    variant={tipoEnvio === "lista" ? "default" : "outline"}
                    onClick={() => setTipoEnvio("lista")}
                    className="w-full"
                  >
                    <List className="mr-2 h-4 w-4" />
                    Lista
                  </Button>
                </div>
              </div>

              <Separator />

              {tipoEnvio === "manual" && (
                <div className="space-y-2">
                  <Label htmlFor="numero">Número do WhatsApp</Label>
                  <Input
                    id="numero"
                    placeholder="5511999999999"
                    value={numero}
                    onChange={(e) => setNumero(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Digite com código do país + DDD + número
                  </p>
                </div>
              )}

              {tipoEnvio === "prestador" && (
                <div className="space-y-2">
                  <Label htmlFor="prestador">Selecione o Prestador</Label>
                  <Select value={prestadorSelecionado} onValueChange={setPrestadorSelecionado}>
                    <SelectTrigger>
                      <SelectValue placeholder="Escolha um prestador" />
                    </SelectTrigger>
                    <SelectContent>
                      {prestadores.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.nome} - {p.telefone}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {tipoEnvio === "montador" && (
                <div className="space-y-2">
                  <Label htmlFor="montador">Selecione o Montador</Label>
                  <Select value={montadorSelecionado} onValueChange={setMontadorSelecionado}>
                    <SelectTrigger>
                      <SelectValue placeholder="Escolha um montador" />
                    </SelectTrigger>
                    <SelectContent>
                      {montadores.map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.nome} - {m.telefone}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {tipoEnvio === "lista" && (
                <div className="space-y-2">
                  <Label htmlFor="numeros">Lista de Números</Label>
                  <Textarea
                    id="numeros"
                    placeholder="5511999999999&#10;5511988888888&#10;5511977777777"
                    value={numeros}
                    onChange={(e) => setNumeros(e.target.value)}
                    rows={6}
                  />
                  <p className="text-xs text-muted-foreground">
                    Um número por linha. Total: {numeros.split('\n').filter(n => n.trim()).length}
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="mensagem">Mensagem</Label>
                <Textarea
                  id="mensagem"
                  placeholder="Digite a mensagem..."
                  value={mensagem}
                  onChange={(e) => setMensagem(e.target.value)}
                  rows={8}
                />
                <p className="text-xs text-muted-foreground">
                  Use *texto* para negrito, _texto_ para itálico
                </p>
              </div>

              {tipoEnvio === "lista" && (
                <div className="space-y-2">
                  <Label htmlFor="delay">Delay entre mensagens (segundos)</Label>
                  <Input
                    id="delay"
                    type="number"
                    min="2"
                    max="10"
                    value={delay}
                    onChange={(e) => setDelay(parseInt(e.target.value))}
                  />
                </div>
              )}

              <Button
                onClick={enviarMensagem}
                disabled={loading || status?.status !== "connected"}
                className="w-full"
                size="lg"
              >
                <Send className="mr-2 h-4 w-4" />
                Enviar Mensagem
              </Button>

              {status?.status !== "connected" && (
                <Alert>
                  <AlertDescription>
                    WhatsApp não está conectado. Conecte primeiro na aba "Status & Conexão"
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB CONFIGURAÇÕES */}
        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Configurações do Serviço</CardTitle>
              <CardDescription>
                O servidor WhatsApp está totalmente integrado ao sistema
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">📡 Status do Servidor</h3>
                <div className="bg-muted p-3 rounded">
                  <p className="text-sm">
                    Servidor: {status?.server_running ? '✅ Rodando' : '❌ Parado'}
                  </p>
                  <p className="text-sm">
                    Conexão WhatsApp: {status?.status === 'connected' ? '✅ Conectado' : '⏳ Desconectado'}
                  </p>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold mb-2">🔧 Gerenciar Servidor</h3>
                <div className="flex gap-2">
                  <Button onClick={iniciarServidor} disabled={loading || status?.server_running} className="bg-green-600 hover:bg-green-700">
                    Iniciar Servidor
                  </Button>
                  <Button onClick={pararServidor} disabled={loading || !status?.server_running} variant="destructive">
                    Parar Servidor
                  </Button>
                  <Button onClick={atualizarStatus} disabled={loading} variant="outline">
                    <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Atualizar Status
                  </Button>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold mb-2">📝 Informações</h3>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    • O servidor WhatsApp roda na porta 3000
                  </p>
                  <p className="text-sm text-muted-foreground">
                    • As credenciais são salvas automaticamente após o primeiro login
                  </p>
                  <p className="text-sm text-muted-foreground">
                    • Você pode parar e iniciar o servidor a qualquer momento
                  </p>
                  <p className="text-sm text-muted-foreground">
                    • O QR Code aparece automaticamente quando necessário
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
