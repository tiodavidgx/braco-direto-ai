import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3080/api/v1';

interface User {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'braco_token';
const USER_KEY = 'braco_user';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Verificar token salvo ao carregar
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUser = localStorage.getItem(USER_KEY);

    if (savedToken && savedUser) {
      // Verificar se o token ainda é válido
      verifyToken(savedToken)
        .then((userData) => {
          setToken(savedToken);
          setUser(userData);
        })
        .catch(() => {
          // Token inválido, limpar storage
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, []);

  const verifyToken = async (tokenToVerify: string): Promise<User> => {
    const response = await fetch(`${API_URL}/user-auth/verify`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${tokenToVerify}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Token inválido');
    }

    const data = await response.json();
    return data.user;
  };

  const login = async (username: string, password: string): Promise<void> => {
    const response = await fetch(`${API_URL}/user-auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao fazer login');
    }

    const data = await response.json();
    
    // Salvar token e usuário
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    
    setToken(data.access_token);
    setUser(data.user);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    isAdmin: user?.role === 'admin'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
}

// Hook para adicionar token automaticamente nas requisições
export function useAuthFetch() {
  const { token, logout } = useAuth();

  const authFetch = async (url: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers);
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    // Se receber 401, fazer logout
    if (response.status === 401) {
      logout();
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    return response;
  };

  return authFetch;
}
