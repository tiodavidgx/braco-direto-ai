#!/bin/bash

echo "🔄 Reiniciando Backend com WebSocket..."
echo ""

# Matar processos antigos do uvicorn
echo "🛑 Parando processos antigos..."
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 2

# Verificar se parou
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "⚠️  Forçando encerramento..."
    pkill -9 -f "uvicorn app.main:app"
    sleep 1
fi

echo "✅ Processos antigos encerrados"
echo ""

# Ir para o diretório do backend
cd "$(dirname "$0")"

# Ativar ambiente virtual e iniciar
echo "🚀 Iniciando backend..."
source venv/bin/activate

# Iniciar uvicorn
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Backend rodando em: http://localhost:14001"
echo "  Documentação: http://localhost:14001/docs"
echo "  WebSocket: ws://localhost:14001/api/v1/ws/notifications"
echo "════════════════════════════════════════════════════════════"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 14001
