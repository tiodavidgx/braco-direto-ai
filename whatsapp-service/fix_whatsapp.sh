#!/bin/bash

echo "🔧 Iniciando correção do serviço WhatsApp..."

# Diretório do script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Matar processos antigos
echo "🔪 Matando processos antigos do Node..."
pkill -f "node server.js" || true

# Perguntar se quer limpar a sessão
read -p "Deseja limpar a sessão antiga do WhatsApp (exigirá novo QR Code)? (s/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]
then
    echo "🧹 Limpando sessão antiga..."
    rm -rf .wwebjs_auth
    rm -rf .wwebjs_cache
    echo "✅ Sessão limpa."
fi

# Instalar dependências se necessário
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependências..."
    npm install
fi

# Iniciar servidor
echo "🚀 Iniciando servidor WhatsApp..."
npm start
