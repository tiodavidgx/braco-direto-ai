#!/bin/bash
cd /Users/david/Documents/GitHub/braco-direto-ai/sistema_original
python3 job_consultar_notas.py 2>&1 | tee /tmp/job_debug.log
echo ""
echo "======================================"
echo "LOGS SALVOS EM: /tmp/job_debug.log"
echo "======================================"
