/**
 * Cliente Base da API
 * 
 * Este arquivo contém o cliente HTTP base para comunicação com o backend Python.
 * Todos os serviços devem usar este cliente para fazer requisições.
 */

// Função para obter a URL base da API
// É chamada em runtime para garantir acesso ao window.location
const getApiBaseUrl = (): string => {
  // Se variável de ambiente está definida, usa ela
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl !== '') {
    // Se for URL relativa, adiciona origin
    if (envUrl.startsWith('/')) {
      return `${window.location.origin}${envUrl}`;
    }
    return envUrl;
  }
  
  // Em produção (não localhost), usa URL relativa via window.location
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `${window.location.origin}/api/v1`;
  }
  
  // Fallback para desenvolvimento local
  return 'http://localhost:14001/api/v1';
};

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

const TOKEN_KEY = 'braco_direto_token';
const USER_KEY = 'braco_direto_user';
// Refresh quando faltar menos de 7 dias para expirar.
const REFRESH_THRESHOLD_MS = 7 * 24 * 60 * 60 * 1000;

function getTokenExpMs(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/**
 * Limpa credenciais e redireciona para /login com flag de expiração.
 * Evita loop quando já estamos em /login.
 */
export function handleUnauthorized(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
    window.location.assign('/login?expired=1');
  }
}

let refreshInFlight: Promise<void> | null = null;

/**
 * Dispara renovação silenciosa do token se estiver perto de expirar.
 * Não bloqueia a chamada original — falhas são ignoradas (próximo request tenta de novo).
 */
function maybeRefreshToken(baseURL: string): void {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token || refreshInFlight) return;
  const expMs = getTokenExpMs(token);
  if (expMs === null) return;
  const remaining = expMs - Date.now();
  if (remaining > REFRESH_THRESHOLD_MS || remaining <= 0) return;

  refreshInFlight = (async () => {
    try {
      const resp = await fetch(`${baseURL}/sistema/refresh`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) return;
      const data = await resp.json();
      if (data?.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
      }
    } catch {
      /* falha silenciosa — tenta de novo no próximo request */
    } finally {
      refreshInFlight = null;
    }
  })();
}

export class APIClient {
  private baseURL: string;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || getApiBaseUrl();
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      handleUnauthorized();
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        detail: 'Erro desconhecido' 
      }));
      throw new APIError(
        error.detail || error.message || 'Erro na requisição',
        response.status,
        error
      );
    }

    // Renovação silenciosa em background quando token está próximo do fim.
    maybeRefreshToken(this.baseURL);

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseURL}${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers: HeadersInit = {};
    const token = localStorage.getItem('braco_direto_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isFormData) headers['Content-Type'] = 'application/json';

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: isFormData ? data : JSON.stringify(data),
    });

    return this.handleResponse<T>(response);
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers: HeadersInit = {};
    const token = localStorage.getItem('braco_direto_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isFormData) headers['Content-Type'] = 'application/json';

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers,
      body: isFormData ? data : JSON.stringify(data),
    });

    return this.handleResponse<T>(response);
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }
}

export const apiClient = new APIClient();
