import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Settings, TestTube, ExternalLink, Shield, Save, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast as sonnerToast } from "sonner";
import { integracoesService, TrelloConfig, TrelloBoard, TrelloLista } from "@/services/integracoes.service";
import { apiClient } from "@/services/api";

export default function Integracoes() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<TrelloConfig>({
    api_key: "",
    token: "",
    board_id: "",
    lista_id: "",
    ativo: false,
  });
  const [boards, setBoards] = useState<TrelloBoard[]>([]);
  const [listas, setListas] = useState<TrelloLista[]>([]);
  const [testando, setTestando] = useState(false);

  // reCAPTCHA state
  const [recaptchaConfig, setRecaptchaConfig] = useState({
    recaptcha_enabled: false,
    recaptcha_site_key: "",
    recaptcha_secret_key: "",
    recaptcha_score_minimo: 0.5,
  });
  const [recaptchaLoading, setRecaptchaLoading] = useState(false);
  const [showSecretKey, setShowSecretKey] = useState(false);

  useEffect(() => {
    carregarConfig();
    carregarRecaptchaConfig();
  }, []);

  const carregarRecaptchaConfig = async () => {
    try {
      const data = await apiClient.get<typeof recaptchaConfig>("/integracoes/recaptcha/config");
      setRecaptchaConfig(data);
    } catch (error) {
      console.error("Erro ao carregar config reCAPTCHA:", error);
    }
  };

  const salvarRecaptchaConfig = async () => {
    setRecaptchaLoading(true);
    try {
      await apiClient.post("/integracoes/recaptcha/config", recaptchaConfig);
      sonnerToast.success("Configuração reCAPTCHA salva com sucesso!");
    } catch (error: any) {
      sonnerToast.error(error.message || "Erro ao salvar configuração reCAPTCHA");
    } finally {
      setRecaptchaLoading(false);
    }
  };

  const carregarConfig = async () => {
    try {
      const data = await integracoesService.getTrelloConfig();
      setConfig(data);
      
      // Se já tem credenciais, carregar boards
      if (data.api_key && data.token) {
        carregarBoards(data.api_key, data.token);
      }
      
      // Se já tem board selecionado, carregar listas
      if (data.board_id && data.api_key && data.token) {
        carregarListas(data.board_id, data.api_key, data.token);
      }
    } catch (error) {
      console.error("Erro ao carregar config:", error);
    }
  };

  const carregarBoards = async (apiKey: string, token: string) => {
    try {
      const data = await integracoesService.getTrelloBoards(apiKey, token);
      setBoards(data);
    } catch (error: any) {
      console.error("Erro ao carregar boards:", error);
    }
  };

  const carregarListas = async (boardId: string, apiKey: string, token: string) => {
    try {
      const data = await integracoesService.getTrelloListas(boardId, apiKey, token);
      setListas(data);
    } catch (error: any) {
      console.error("Erro ao carregar listas:", error);
    }
  };

  const testarConexao = async () => {
    if (!config.api_key || !config.token) {
      toast({
        title: "Erro",
        description: "Preencha API Key e Token primeiro",
        variant: "destructive",
      });
      return;
    }

    setTestando(true);
    try {
      const result = await integracoesService.testTrelloConnection(config.api_key, config.token);
      
      if (result.success) {
        toast({ title: "Sucesso", description: "Conexão OK! Carregando boards..." });
        await carregarBoards(config.api_key, config.token);
      } else {
        toast({
          title: "Erro",
          description: "Falha na conexão. Verifique as credenciais.",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao testar conexão",
        variant: "destructive",
      });
    } finally {
      setTestando(false);
    }
  };

  const salvarConfig = async () => {
    if (!config.api_key || !config.token) {
      toast({
        title: "Erro",
        description: "Preencha API Key e Token",
        variant: "destructive",
      });
      return;
    }

    if (!config.board_id || !config.lista_id) {
      toast({
        title: "Erro",
        description: "Selecione um Board e uma Lista",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      await integracoesService.saveTrelloConfig(config);
      toast({ title: "Sucesso", description: "Configuração salva!" });
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message || "Erro ao salvar configuração",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBoardChange = (boardId: string) => {
    setConfig({ ...config, board_id: boardId, lista_id: "" });
    setListas([]);
    if (config.api_key && config.token) {
      carregarListas(boardId, config.api_key, config.token);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Integrações</h1>
          <p className="text-muted-foreground">Configure integrações com serviços externos</p>
        </div>
      </div>

      <Tabs defaultValue="trello" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="trello">
            <Settings className="mr-2 h-4 w-4" />
            Trello
          </TabsTrigger>
          <TabsTrigger value="seguranca">
            <Shield className="mr-2 h-4 w-4" />
            Segurança
          </TabsTrigger>
          <TabsTrigger value="futuras">
            Futuras Integrações
          </TabsTrigger>
        </TabsList>

        {/* TAB TRELLO */}
        <TabsContent value="trello" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Integração com Trello</CardTitle>
              <CardDescription>
                Configure a criação automática de cards no Trello
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Alert>
                <AlertDescription className="space-y-2">
                  <p className="font-semibold">Como configurar:</p>
                  <ol className="list-decimal list-inside space-y-1 text-sm">
                    <li>
                      Obter API Key:{" "}
                      <a
                        href="https://trello.com/power-ups/admin"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        https://trello.com/power-ups/admin
                        <ExternalLink className="inline ml-1 h-3 w-3" />
                      </a>
                    </li>
                    <li>Clique em "New" para criar uma Power-Up e copie a API Key</li>
                    <li>Clique em "Token" para gerar um token de autorização</li>
                    <li>Use o botão "Testar Conexão" para listar seus boards e listas</li>
                  </ol>
                </AlertDescription>
              </Alert>

              <div className="space-y-4">
                <h3 className="font-semibold">Credenciais</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="apiKey">API Key</Label>
                    <Input
                      id="apiKey"
                      type="password"
                      value={config.api_key}
                      onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                      placeholder="Sua chave de API do Trello"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="token">Token</Label>
                    <Input
                      id="token"
                      type="password"
                      value={config.token}
                      onChange={(e) => setConfig({ ...config, token: e.target.value })}
                      placeholder="Seu token de autorização"
                    />
                  </div>
                </div>

                <Button 
                  variant="outline" 
                  onClick={testarConexao} 
                  disabled={testando || !config.api_key || !config.token}
                >
                  <TestTube className="mr-2 h-4 w-4" />
                  {testando ? "Testando..." : "Testar Conexão"}
                </Button>
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="font-semibold">Destino dos Cards</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="board">Board</Label>
                    <Select
                      value={config.board_id}
                      onValueChange={handleBoardChange}
                      disabled={boards.length === 0}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione um board" />
                      </SelectTrigger>
                      <SelectContent>
                        {boards.map((board) => (
                          <SelectItem key={board.id} value={board.id}>
                            {board.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="lista">Lista</Label>
                    <Select
                      value={config.lista_id}
                      onValueChange={(value) => setConfig({ ...config, lista_id: value })}
                      disabled={listas.length === 0}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione uma lista" />
                      </SelectTrigger>
                      <SelectContent>
                        {listas.map((lista) => (
                          <SelectItem key={lista.id} value={lista.id}>
                            {lista.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="ativo">Ativar integração com Trello</Label>
                  <p className="text-sm text-muted-foreground">
                    Cards serão criados automaticamente ao baixar arquivos
                  </p>
                </div>
                <Switch
                  id="ativo"
                  checked={config.ativo}
                  onCheckedChange={(checked) => setConfig({ ...config, ativo: checked })}
                />
              </div>

              <Separator />

              <Button onClick={salvarConfig} disabled={loading}>
                Salvar Configuração
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB SEGURANÇA - reCAPTCHA */}
        <TabsContent value="seguranca" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                <div>
                  <CardTitle>Google reCAPTCHA v3</CardTitle>
                  <CardDescription>
                    Proteção contra bots no login e cadastro. Obtenha as chaves em{" "}
                    <a
                      href="https://www.google.com/recaptcha/admin"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      google.com/recaptcha/admin
                      <ExternalLink className="inline ml-1 h-3 w-3" />
                    </a>
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label className="text-base">Habilitar reCAPTCHA</Label>
                  <p className="text-sm text-muted-foreground">
                    Ativa verificação invisível no login e cadastro
                  </p>
                </div>
                <Switch
                  checked={recaptchaConfig.recaptcha_enabled}
                  onCheckedChange={(checked) =>
                    setRecaptchaConfig({ ...recaptchaConfig, recaptcha_enabled: checked })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label>Site Key (chave pública)</Label>
                <Input
                  value={recaptchaConfig.recaptcha_site_key}
                  onChange={(e) =>
                    setRecaptchaConfig({ ...recaptchaConfig, recaptcha_site_key: e.target.value })
                  }
                  placeholder="6Lc..."
                />
              </div>

              <div className="space-y-2">
                <Label>Secret Key (chave secreta)</Label>
                <div className="relative">
                  <Input
                    type={showSecretKey ? "text" : "password"}
                    value={recaptchaConfig.recaptcha_secret_key}
                    onChange={(e) =>
                      setRecaptchaConfig({ ...recaptchaConfig, recaptcha_secret_key: e.target.value })
                    }
                    placeholder="6Lc..."
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowSecretKey(!showSecretKey)}
                  >
                    {showSecretKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Score mínimo (0.0 a 1.0)</Label>
                <p className="text-sm text-muted-foreground">
                  Quanto maior, mais rigoroso. 0.5 é o recomendado. Abaixo desse score a requisição é bloqueada.
                </p>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={recaptchaConfig.recaptcha_score_minimo}
                  onChange={(e) =>
                    setRecaptchaConfig({ ...recaptchaConfig, recaptcha_score_minimo: parseFloat(e.target.value) || 0.5 })
                  }
                />
              </div>

              <Separator />

              <Button onClick={salvarRecaptchaConfig} disabled={recaptchaLoading} className="w-full">
                {recaptchaLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Salvando...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Salvar Configuração
                  </>
                )}
              </Button>

              <Alert>
                <AlertDescription>
                  <p>Implementado em: <strong>Login</strong> e <strong>Cadastro</strong></p>
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB FUTURAS */}
        <TabsContent value="futuras" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Futuras Integrações</CardTitle>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertDescription>
                  💡 Em breve: Slack, Microsoft Teams, Discord e mais!
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
