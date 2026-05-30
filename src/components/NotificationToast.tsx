import { useEffect, useState } from 'react';
import { X, CheckCircle2, Info, AlertTriangle, XCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export interface Notification {
  id: string;
  tipo: 'success' | 'info' | 'warning' | 'error';
  titulo: string;
  mensagem: string;
  timestamp: string;
  dados?: Record<string, any>;
}

interface NotificationToastProps {
  notification: Notification;
  onClose: (id: string) => void;
}

const iconMap = {
  success: CheckCircle2,
  info: Info,
  warning: AlertTriangle,
  error: XCircle,
};

const colorMap = {
  success: 'bg-green-50 border-green-200 text-green-900',
  info: 'bg-blue-50 border-blue-200 text-blue-900',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-900',
  error: 'bg-red-50 border-red-200 text-red-900',
};

const iconColorMap = {
  success: 'text-green-600',
  info: 'text-blue-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
};

export function NotificationToast({ notification, onClose }: NotificationToastProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  const Icon = iconMap[notification.tipo];
  const colorClass = colorMap[notification.tipo];
  const iconColor = iconColorMap[notification.tipo];

  useEffect(() => {
    // Animação de entrada
    setTimeout(() => setIsVisible(true), 10);

    // Auto-fechar após 5 segundos
    const timer = setTimeout(() => {
      handleClose();
    }, 5000);

    return () => clearTimeout(timer);
  }, []);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onClose(notification.id);
    }, 300);
  };

  return (
    <Card
      className={`
        mb-3 shadow-lg border-2 transition-all duration-300 overflow-hidden
        ${colorClass}
        ${isVisible && !isExiting ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
      style={{ minWidth: '320px', maxWidth: '420px' }}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Ícone */}
          <div className={`mt-0.5 ${iconColor}`}>
            <Icon className="h-5 w-5" />
          </div>

          {/* Conteúdo */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h4 className="font-semibold text-sm leading-tight">
                {notification.titulo}
              </h4>
              <button
                onClick={handleClose}
                className="text-gray-500 hover:text-gray-700 transition-colors flex-shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-sm mt-1 text-gray-700">
              {notification.mensagem}
            </p>
            
            {/* Dados adicionais */}
            {notification.dados && notification.dados.card_url && (
              <a
                href={notification.dados.card_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline mt-2 inline-block"
              >
                Ver card no Trello →
              </a>
            )}
            
            {notification.dados && notification.dados.valor && (
              <p className="text-xs text-gray-600 mt-1">
                Valor: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(notification.dados.valor)}
              </p>
            )}
          </div>
        </div>

        {/* Barra de progresso */}
        <div className="mt-3 h-1 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${
              notification.tipo === 'success' ? 'bg-green-500' :
              notification.tipo === 'info' ? 'bg-blue-500' :
              notification.tipo === 'warning' ? 'bg-yellow-500' :
              'bg-red-500'
            } animate-progress`}
          />
        </div>
      </CardContent>
    </Card>
  );
}
