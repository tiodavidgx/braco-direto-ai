#!/bin/bash

# Script permanente para iniciar o WhatsApp Service
# Garante que o Node.js seja encontrado no PATH

echo "🚀 Iniciando WhatsApp Service..."

# Adicionar caminhos comuns do Node.js ao PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Ir para o diretório do WhatsApp service
cd "$(dirname "$0")"

# Verificar se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não está instalado ou não foi encontrado no PATH"
    echo "📍 Caminhos verificados: $PATH"
    exit 1
fi

echo "✅ Node.js encontrado: $(node --version)"

# Verificar se npm está instalado
if ! command -v npm &> /dev/null; then
    echo "❌ npm não está instalado ou não foi encontrado no PATH"
    exit 1
fi

echo "✅ npm encontrado: $(npm --version)"

# Parar processos antigos
echo "🔪 Parando processos antigos..."
pkill -f "node server.js" 2>/dev/null || true
sleep 1

# Verificar se node_modules existe
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependências..."
    npm install
fi

# Iniciar o servidor
echo "▶️  Iniciando servidor..."
npm start
