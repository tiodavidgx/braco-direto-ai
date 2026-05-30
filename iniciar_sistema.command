#!/bin/bash

# Caminho base do projeto
PROJECT_DIR="/Users/david/Documents/GitHub/braco-direto-ai"

echo "🚀 Iniciando Sistema Braço Direto AI..."

# 1. Iniciar Backend (Python/FastAPI)
echo "📦 Iniciando Backend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_DIR/backend_example' && ./start_backend.sh\""

# 2. Iniciar WhatsApp Service (Node.js)
echo "💬 Iniciando WhatsApp Service..."
osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_DIR/whatsapp-service' && npm start\""

# 3. Iniciar Frontend (Vite/React)
echo "💻 Iniciando Frontend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_DIR' && npm run dev\""

# 4. Aguardar e abrir navegador
echo "⏳ Aguardando serviços iniciarem..."
sleep 5
echo "🌐 Abrindo navegador..."
open "http://localhost:5173"

# Fechar esta janela do terminal (opcional, remova se quiser ver logs deste script)
# osascript -e 'tell application "Terminal" to close first window' & exit
