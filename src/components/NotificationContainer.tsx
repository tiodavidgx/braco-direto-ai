import { useEffect, useState } from 'react';
import { NotificationToast, Notification } from './NotificationToast';

const WS_URL = 'ws://localhost:8001/api/v1/ws/notifications';

export function NotificationContainer() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    // Conectar ao WebSocket
    const websocket = new WebSocket(WS_URL);

    websocket.onopen = () => {
      console.log('✅ Conectado ao servidor de notificações');
      
      // Enviar ping a cada 30 segundos para manter conexão viva
      const pingInterval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.send('ping');
        }
      }, 30000);

      // Guardar o interval para limpar depois
      (websocket as any)._pingInterval = pingInterval;
    };

    websocket.onmessage = (event) => {
      if (event.data === 'pong') {
        return; // Ignorar resposta de ping
      }

      try {
        const notification = JSON.parse(event.data) as Notification;
        
        // Adicionar ID único se não tiver
        if (!notification.id) {
          notification.id = `${Date.now()}-${Math.random()}`;
        }

        // Adicionar notificação à lista
        setNotifications((prev) => [...prev, notification]);

        // Reproduzir som (opcional)
        playNotificationSound(notification.tipo);
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
      if ((websocket as any)._pingInterval) {
        clearInterval((websocket as any)._pingInterval);
      }

      // Tentar reconectar após 5 segundos
      setTimeout(() => {
        console.log('🔄 Tentando reconectar...');
        setWs(null); // Isso vai triggerar um novo useEffect
      }, 5000);
    };

    setWs(websocket);

    // Cleanup
    return () => {
      if ((websocket as any)._pingInterval) {
        clearInterval((websocket as any)._pingInterval);
      }
      websocket.close();
    };
  }, []);

  const handleCloseNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const playNotificationSound = (tipo: Notification['tipo']) => {
    // Som sutil para notificações (opcional)
    try {
      const audio = new Audio();
      
      // Frequências diferentes para cada tipo
      const frequencies = {
        success: 800,
        info: 600,
        warning: 500,
        error: 400,
      };

      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const gainNode = context.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(context.destination);

      oscillator.frequency.value = frequencies[tipo];
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.1, context.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.1);

      oscillator.start(context.currentTime);
      oscillator.stop(context.currentTime + 0.1);
    } catch (error) {
      // Ignorar erros de áudio
    }
  };

  return (
    <div className="fixed top-4 right-4 z-[9999] pointer-events-none">
      <div className="pointer-events-auto flex flex-col items-end">
        {notifications.map((notification) => (
          <NotificationToast
            key={notification.id}
            notification={notification}
            onClose={handleCloseNotification}
          />
        ))}
      </div>
    </div>
  );
}
