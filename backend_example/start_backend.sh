#!/bin/bash

# Carregar ambiente do Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Adicionar Node.js e outras ferramentas do Homebrew ao PATH
export PATH="/opt/homebrew/bin:$PATH"

# Configurar biblioteca paths para WeasyPrint
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig"

# Navegar para o diretório correto
cd /Users/david/Documents/GitHub/braco-direto-ai/backend_example

# Ativar ambiente virtual (verifica no diretório atual, no pai, ou no workspace root)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "/Users/david/Documents/GitHub/braco-direto-ai/venv" ]; then
    source /Users/david/Documents/GitHub/braco-direto-ai/venv/bin/activate
fi

# Usar o python do venv se disponível, senão usar o python3 do sistema
PYTHON_BIN="${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python3}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "🐍 Usando Python: $("$PYTHON_BIN" --version 2>&1)"

# Iniciar o backend
"$PYTHON_BIN" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
