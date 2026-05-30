import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";

interface PrivateRouteProps {
  children: React.ReactNode;
  adminOnly?: boolean;
  requiredPermission?: "pode_pre_cadastro" | "pode_revisao_cadastro" | "crm_access" | "acesso_montagem";
}

export function PrivateRoute({ children, adminOnly = false, requiredPermission }: PrivateRouteProps) {
  const { isAuthenticated, isLoading, isAdmin, user } = useAuth();

  // Enquanto está carregando, mostra loading (não renderiza nada do conteúdo)
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Se não está autenticado, redireciona para login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Se é motorista, redireciona para página do motorista
  if (user?.role === "motorista") {
    return <Navigate to="/motorista" replace />;
  }

  // Se a rota requer admin e o usuário não é admin, redireciona
  if (adminOnly && !isAdmin) {
    return <Navigate to="/custos-extras" replace />;
  }

  // Se a rota requer uma permissão específica e o usuário não a tem (e não é admin)
  if (requiredPermission && !isAdmin) {
    if (requiredPermission === 'crm_access') {
      if (!user?.crm_solicitante && !user?.crm_analista) {
        return <Navigate to="/custos-extras" replace />;
      }
    } else if (requiredPermission === 'acesso_montagem') {
      if (!user?.acesso_montagem) {
        return <Navigate to="/custos-extras" replace />;
      }
    } else if (!user?.[requiredPermission]) {
      return <Navigate to="/custos-extras" replace />;
    }
  }

  return <>{children}</>;
}
