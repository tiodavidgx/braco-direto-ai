import { useEffect, useCallback, useRef } from 'react';

// Função para obter URL do WebSocket dinamicamente
const getWsUrl = (): string => {
  const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
  if (isProduction) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/v1/ws/notifications`;
  }
  return 'ws://localhost:8000/api/v1/ws/notifications';
};

export interface NotificationData {
  tipo: 'success' | 'info' | 'warning' | 'error';
  titulo: string;
  mensagem: string;
  timestamp: string;
  dados?: {
    lote_id?: number;
    tipo?: string;
    prestador?: string;
    montador?: string;
    periodo?: string;
    valor?: number;
    total_arquivos?: number;
    tamanho_total?: string;
    nota_fiscal?: string;
  };
}

export function useNotifications(onNotification?: (notification: NotificationData) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Limpar timeout de reconexão se existir
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Não criar nova conexão se já existe uma ativa
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const websocket = new WebSocket(getWsUrl());

    websocket.onopen = () => {
      console.log('✅ Conectado ao servidor de notificações');
      
      // Enviar ping a cada 30 segundos para manter conexão viva
      pingIntervalRef.current = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.send('ping');
        }
      }, 30000);
    };

    websocket.onmessage = (event) => {
      if (event.data === 'pong') {
        return; // Ignorar resposta de ping
      }

      try {
        const notification = JSON.parse(event.data) as NotificationData;
        if (onNotification) {
          onNotification(notification);
        }
      } catch (error) {
        console.error('Erro ao processar notificação:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('❌ Erro no WebSocket:', error);
    };

    websocket.onclose = () => {
      console.log('🔌 Desconectado do servidor de notificações');
      
      // Limpar ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // Tentar reconectar após 5 segundos
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('🔄 Tentando reconectar...');
        connect();
      }, 5000);
    };

    wsRef.current = websocket;
  }, [onNotification]);

  const disconnect = useCallback(() => {
    // Limpar intervalos e timeouts
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Fechar conexão
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { disconnect, reconnect: connect };
}
