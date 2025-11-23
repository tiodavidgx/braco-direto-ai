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

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Iniciar o backend usando o Python do ambiente virtual
./venv/bin/python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
