import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { handleUnauthorized } from "@/services/api";

interface User {
  id: number;
  email: string;
  nome: string;
  role: "admin" | "operador" | "motorista";
  pode_pre_cadastro?: boolean;
  pode_revisao_cadastro?: boolean;
  crm_solicitante?: boolean;
  crm_analista?: boolean;
  acesso_montagem?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "braco_direto_token";
const USER_KEY = "braco_direto_user";

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (typeof payload.exp !== "number") return false;
    return payload.exp * 1000 < Date.now();
  } catch {
    // Token malformado — trata como expirado
    return true;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Carregar dados do localStorage ao iniciar
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);

    if (storedToken && storedUser) {
      if (isTokenExpired(storedToken)) {
        // Token já expirou — limpa tudo e força login
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setIsLoading(false);
        return;
      }
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));

        // Revalida o usuário no backend para trazer permissões/campos novos
        // (evita que alterações de permissão só valham após logout/login).
        const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";
        fetch(`${API_BASE}/sistema/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
        })
          .then(async (r) => {
            if (r.status === 401) {
              // Token rejeitado pelo backend (usuário desativado, senha trocada, etc.)
              setToken(null);
              setUser(null);
              handleUnauthorized();
              return null;
            }
            return r.ok ? r.json() : null;
          })
          .then((fresh) => {
            if (fresh && fresh.id) {
              setUser(fresh as User);
              localStorage.setItem(USER_KEY, JSON.stringify(fresh));
            }
          })
          .catch(() => {
            /* erro de rede — mantém dados locais */
          });
      } catch {
        // Se falhar ao parsear, limpa os dados
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        isAdmin: user?.role === "admin",
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth deve ser usado dentro de um AuthProvider");
  }
  return context;
}
