import { useState } from "react";
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
import { RefreshCw, MessageSquare, Settings, Phone, Send, Users, Wrench, List } from "lucide-react";
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

  const carregarPrestadores = async () => {
    try {
      const data: any = await prestadoresService.getAll();
      const lista = Array.isArray(data) ? data : [];
      setPrestadores(lista.filter((p: any) => p.telefone));
    } catch (error) {
      console.error("Erro ao carregar prestadores:", error);
    }
  };

  const carregarMontadores = async () => {
    try {
      const data: any = await montadoresService.getAll();
      const lista = Array.isArray(data) ? data : [];
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
                    {status?.status === "error" && (
                      <Badge variant="destructive">Offline</Badge>
                    )}
                    {status?.status === "connected" && (
                      <Badge className="bg-green-500">Conectado</Badge>
                    )}
                    {status?.status && status.status !== "error" && status.status !== "connected" && (
                      <Badge variant="secondary">Aguardando</Badge>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Autenticação</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {status?.hasQrCode && (
                      <Badge variant="outline">QR Code Disponível</Badge>
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
                    {status?.status === "connected" ? (
                      <p className="text-sm text-foreground truncate">Conectado</p>
                    ) : (
                      <Badge variant="secondary">N/A</Badge>
                    )}
                  </CardContent>
                </Card>
              </div>

              {status?.status !== "connected" && (
                <Alert>
                  <AlertDescription className="space-y-2">
                    <p className="font-semibold">Como Conectar:</p>
                    <ol className="list-decimal list-inside space-y-1 text-sm">
                      <li>Inicie o serviço WhatsApp: <code className="bg-muted px-1 rounded">npm start</code></li>
                      <li>Acesse: <a href="http://localhost:3000/qr" target="_blank" className="text-primary hover:underline">http://localhost:3000/qr</a></li>
                      <li>Escaneie o QR Code com WhatsApp → Aparelhos conectados</li>
                      <li>Volte aqui e clique em "Atualizar Status"</li>
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
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">URLs do Serviço</h3>
                <div className="grid gap-2">
                  <code className="bg-muted p-2 rounded text-sm">http://localhost:3000/status</code>
                  <code className="bg-muted p-2 rounded text-sm">http://localhost:3000/qr</code>
                  <code className="bg-muted p-2 rounded text-sm">http://localhost:3000/info</code>
                  <code className="bg-muted p-2 rounded text-sm">http://localhost:3000/send</code>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold mb-2">Como Iniciar o Serviço</h3>
                <code className="bg-muted p-3 rounded block text-sm">
                  npm start
                </code>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
