import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Settings, TestTube, ExternalLink } from "lucide-react";
import { integracoesService } from "@/services/integracoes.service";

export default function Integracoes() {
  const { toast } = useToast();
  const [config, setConfig] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [token, setToken] = useState("");
  const [boardId, setBoardId] = useState("");
  const [listId, setListId] = useState("");
  const [ativo, setAtivo] = useState(false);

  useEffect(() => {
    carregarConfig();
  }, []);

  const carregarConfig = async () => {
    try {
      const data: any = await integracoesService.getTrelloConfig();
      setConfig(data);
      setApiKey(data.trello_api_key || "");
      setToken(data.trello_token || "");
      setBoardId(data.trello_board_id || "");
      setListId(data.trello_list_id || "");
      setAtivo(data.trello_ativo || false);
    } catch (error) {
      console.error("Erro ao carregar config:", error);
    }
  };

  const salvarConfig = async () => {
    setLoading(true);
    try {
      await integracoesService.saveTrelloConfig({
        trello_api_key: apiKey,
        trello_token: token,
        trello_board_id: boardId,
        trello_list_id: listId,
        trello_ativo: ativo,
      });
      toast({ title: "Sucesso", description: "Configuração salva!" });
      carregarConfig();
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

  const testarConexao = async () => {
    setLoading(true);
    try {
      const result: any = await integracoesService.testTrelloConnection();
      if (result.success) {
        toast({ title: "Sucesso", description: "Conexão OK!" });
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
      setLoading(false);
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
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="trello">
            <Settings className="mr-2 h-4 w-4" />
            Trello
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
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Sua chave de API do Trello"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="token">Token</Label>
                    <Input
                      id="token"
                      type="password"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="Seu token de autorização"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="font-semibold">Destino dos Cards</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="boardId">Board ID</Label>
                    <Input
                      id="boardId"
                      value={boardId}
                      onChange={(e) => setBoardId(e.target.value)}
                      placeholder="ID do board"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="listId">List ID</Label>
                    <Input
                      id="listId"
                      value={listId}
                      onChange={(e) => setListId(e.target.value)}
                      placeholder="ID da lista"
                    />
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
                  checked={ativo}
                  onCheckedChange={setAtivo}
                />
              </div>

              <Separator />

              <div className="flex gap-2">
                <Button onClick={salvarConfig} disabled={loading}>
                  Salvar Configuração
                </Button>
                <Button variant="outline" onClick={testarConexao} disabled={loading}>
                  <TestTube className="mr-2 h-4 w-4" />
                  Testar Conexão
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Histórico de Cards Criados</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-center text-muted-foreground py-8">
                Nenhum card criado ainda
              </p>
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
