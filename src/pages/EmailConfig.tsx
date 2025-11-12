import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Mail, Check, X, RefreshCw, LogOut, ExternalLink, AlertCircle, Copy, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { authService, AuthConfig, DeviceFlowResponse } from "@/services/auth.service";

export default function EmailConfig() {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [deviceFlow, setDeviceFlow] = useState<DeviceFlowResponse | null>(null);
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    carregarConfig();
  }, []);

  // Polling automático quando device flow está ativo
  useEffect(() => {
    if (!deviceFlow || !polling) return;

    const pollInterval = setInterval(async () => {
      try {
        const result = await authService.pollDeviceFlow(deviceFlow.device_code);
        
        if (result.success) {
          // Autenticação completa!
          setPolling(false);
          setDeviceFlow(null);
          toast.success("Autenticação realizada com sucesso!");
          await carregarConfig();
        } else if (result.error) {
          // Erro definitivo
          setPolling(false);
          setDeviceFlow(null);
          toast.error(result.message);
        }
        // Se não tiver erro, continua polling (authorization_pending)
      } catch (error: any) {
        console.error("Erro no polling:", error);
        setPolling(false);
        setDeviceFlow(null);
        toast.error("Erro ao verificar autenticação");
      }
    }, (deviceFlow.interval || 5) * 1000);

    return () => clearInterval(pollInterval);
  }, [deviceFlow, polling]);

  const carregarConfig = async () => {
    try {
      setLoading(true);
      const data = await authService.getConfig();
      setConfig(data);
    } catch (error) {
      console.error("Erro ao carregar configuração:", error);
      toast.error("Erro ao carregar configuração de email");
    } finally {
      setLoading(false);
    }
  };

  const iniciarAutenticacao = async () => {
    try {
      setProcessing(true);
      const flow = await authService.startDeviceFlow();
      setDeviceFlow(flow);
      setPolling(true);
      toast.success("Código gerado! Siga as instruções abaixo.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao iniciar autenticação");
    } finally {
      setProcessing(false);
    }
  };

  const copiarCodigo = () => {
    if (deviceFlow) {
      navigator.clipboard.writeText(deviceFlow.user_code);
      toast.success("Código copiado!");
    }
  };

  const abrirPaginaMicrosoft = () => {
    if (deviceFlow) {
      window.open(deviceFlow.verification_uri, "_blank");
    }
  };

  const cancelarAutenticacao = () => {
    setDeviceFlow(null);
    setPolling(false);
    toast.info("Autenticação cancelada");
  };

  const renovarToken = async () => {
    try {
      setProcessing(true);
      await authService.refreshToken();
      toast.success("Token renovado com sucesso!");
      await carregarConfig();
    } catch (error: any) {
      toast.error(error.message || "Erro ao renovar token");
    } finally {
      setProcessing(false);
    }
  };

  const fazerLogout = async () => {
    try {
      setProcessing(true);
      await authService.logout();
      toast.success("Logout realizado com sucesso!");
      await carregarConfig();
    } catch (error: any) {
      toast.error(error.message || "Erro ao fazer logout");
    } finally {
      setProcessing(false);
    }
  };

  const formatarData = (isoDate: string | null) => {
    if (!isoDate) return null;
    return new Date(isoDate).toLocaleString('pt-BR');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Configuração de Email</h1>
          <p className="text-muted-foreground">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Configuração de Email</h1>
        <p className="text-muted-foreground">
          Autenticação Microsoft para envio de relatórios por email
        </p>
      </div>

      {/* Status da Conexão */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Status da Conexão
          </CardTitle>
          <CardDescription>
            Configuração atual da autenticação Microsoft
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status:</span>
            {config?.has_token ? (
              <Badge variant="default" className="gap-1">
                <Check className="h-3 w-3" />
                Conectado
              </Badge>
            ) : (
              <Badge variant="secondary" className="gap-1">
                <X className="h-3 w-3" />
                Não conectado
              </Badge>
            )}
          </div>

          {config?.has_token && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Email:</span>
                <span className="text-sm text-muted-foreground">
                  {config.user_email || "N/A"}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Token expira em:</span>
                <span className="text-sm text-muted-foreground">
                  {formatarData(config.token_expires)}
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Device Flow Ativo */}
      {deviceFlow && (
        <Card className="border-blue-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {polling && <Loader2 className="h-5 w-5 animate-spin" />}
              Autenticação em Andamento
            </CardTitle>
            <CardDescription>
              Siga as instruções abaixo para completar a autenticação
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="ml-2">
                <strong>Passo 1:</strong> Abra a página da Microsoft clicando no botão abaixo<br />
                <strong>Passo 2:</strong> Digite o código: <strong className="text-lg">{deviceFlow.user_code}</strong><br />
                <strong>Passo 3:</strong> Faça login com sua conta Office 365
              </AlertDescription>
            </Alert>

            <div className="flex items-center gap-2 p-4 bg-muted rounded-md">
              <code className="flex-1 text-2xl font-bold text-center">
                {deviceFlow.user_code}
              </code>
              <Button size="sm" variant="ghost" onClick={copiarCodigo}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex gap-2">
              <Button onClick={abrirPaginaMicrosoft} className="flex-1 gap-2">
                <ExternalLink className="h-4 w-4" />
                Abrir Página da Microsoft
              </Button>
              <Button 
                variant="outline" 
                onClick={cancelarAutenticacao}
                disabled={processing}
              >
                Cancelar
              </Button>
            </div>

            <div className="text-center text-sm text-muted-foreground">
              Ou acesse diretamente:{" "}
              <a 
                href={deviceFlow.verification_uri} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline font-medium"
              >
                {deviceFlow.verification_uri}
              </a>
            </div>

            {polling && (
              <p className="text-sm text-muted-foreground text-center">
                Aguardando você completar a autenticação na página da Microsoft...
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Ações */}
      <Card>
        <CardHeader>
          <CardTitle>Ações</CardTitle>
          <CardDescription>
            Gerencie sua autenticação Microsoft
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!config?.has_token && !deviceFlow && (
            <Button 
              onClick={iniciarAutenticacao} 
              disabled={processing}
              className="w-full gap-2"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Iniciando...
                </>
              ) : (
                <>
                  <Mail className="h-4 w-4" />
                  Conectar com Microsoft
                </>
              )}
            </Button>
          )}

          {config?.has_token && (
            <>
              <Button 
                onClick={renovarToken} 
                disabled={processing}
                variant="outline"
                className="w-full gap-2"
              >
                {processing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Renovando...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    Renovar Token
                  </>
                )}
              </Button>

              <Button 
                onClick={fazerLogout} 
                disabled={processing}
                variant="destructive"
                className="w-full gap-2"
              >
                {processing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Desconectando...
                  </>
                ) : (
                  <>
                    <LogOut className="h-4 w-4" />
                    Desconectar
                  </>
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Instruções */}
      <Card>
        <CardHeader>
          <CardTitle>Como Funciona</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong>1.</strong> Clique em "Conectar com Microsoft" para gerar um código
          </p>
          <p>
            <strong>2.</strong> Abra a página da Microsoft que será exibida
          </p>
          <p>
            <strong>3.</strong> Digite o código fornecido
          </p>
          <p>
            <strong>4.</strong> Faça login com sua conta Office 365 corporativa
          </p>
          <p>
            <strong>5.</strong> Autorize as permissões solicitadas
          </p>
          <p>
            <strong>6.</strong> O sistema detectará automaticamente quando você completar o login
          </p>
          <p className="pt-2">
            <strong>Nota:</strong> Este método é seguro e não requer que você informe sua senha neste sistema.
          </p>
        </CardContent>
      </Card>

      {/* Informações de Segurança */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="ml-2">
          <strong>Segurança:</strong> Seus tokens são armazenados de forma segura no banco de dados 
          e renovados automaticamente quando necessário. O sistema nunca tem acesso à sua senha do Microsoft.
        </AlertDescription>
      </Alert>
    </div>
  );
}
