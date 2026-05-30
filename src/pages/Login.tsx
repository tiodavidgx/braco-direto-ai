import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [recaptchaSiteKey, setRecaptchaSiteKey] = useState("");
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    // Se redirecionado por sessão expirada, avisa o usuário e limpa a flag.
    const params = new URLSearchParams(window.location.search);
    if (params.has("expired")) {
      toast.error("Sua sessão expirou. Faça login novamente.");
      params.delete("expired");
      const newSearch = params.toString();
      window.history.replaceState(
        {},
        "",
        window.location.pathname + (newSearch ? `?${newSearch}` : "")
      );
    }
  }, []);

  useEffect(() => {
    // Buscar config pública do reCAPTCHA
    apiClient.get<{ enabled: boolean; site_key: string }>("/integracoes/recaptcha/public")
      .then((data) => {
        if (data.enabled && data.site_key) {
          setRecaptchaSiteKey(data.site_key);
          // Carregar script do Google reCAPTCHA
          const script = document.createElement("script");
          script.src = `https://www.google.com/recaptcha/api.js?render=${data.site_key}`;
          script.async = true;
          document.head.appendChild(script);
        }
      })
      .catch(() => {});
  }, []);

  const getRecaptchaToken = useCallback(async (): Promise<string | null> => {
    if (!recaptchaSiteKey) return null;
    try {
      const grecaptcha = (window as any).grecaptcha;
      if (!grecaptcha) return null;
      return await grecaptcha.execute(recaptchaSiteKey, { action: "login" });
    } catch {
      return null;
    }
  }, [recaptchaSiteKey]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast.error("Preencha email e senha");
      return;
    }

    setLoading(true);
    try {
      const recaptcha_token = await getRecaptchaToken();
      const response = await apiClient.post<{
        access_token: string;
        user: { id: number; email: string; nome: string; role?: string };
      }>("/sistema/login", { email, password, recaptcha_token });

      login(response.access_token, response.user);
      toast.success(`Bem-vindo, ${response.user.nome}!`);
      
      // Motorista vai para página de despesas
      if (response.user.role === "motorista") {
        navigate("/motorista");
      } else {
        navigate("/");
      }
    } catch (error: any) {
      console.error("Erro no login:", error);
      toast.error(error.message || "Email ou senha incorretos");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-2xl font-bold text-primary">BD</span>
          </div>
          <CardTitle className="text-2xl">Braço Direito AI</CardTitle>
          <CardDescription>Entre com suas credenciais para acessar o sistema</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Entrando...
                </>
              ) : (
                "Entrar"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
