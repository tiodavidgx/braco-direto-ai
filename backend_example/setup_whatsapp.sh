#!/bin/bash

# Script para instalar dependências do servidor WhatsApp

echo "📦 Instalando dependências do servidor WhatsApp..."

cd "$(dirname "$0")"

# Verificar se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não está instalado!"
    echo "Por favor, instale Node.js: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js encontrado: $(node --version)"

# Instalar dependências
if [ -f "package.json" ]; then
    echo "📥 Instalando pacotes npm..."
    npm install
    
    if [ $? -eq 0 ]; then
        echo "✅ Dependências instaladas com sucesso!"
        echo ""
        echo "🚀 O servidor WhatsApp está pronto para ser iniciado."
        echo "   Você pode iniciá-lo pela interface em: http://localhost:14002/whatsapp"
        echo ""
    else
        echo "❌ Erro ao instalar dependências"
        exit 1
    fi
else
    echo "❌ package.json não encontrado!"
    exit 1
fi
