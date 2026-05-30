# Deploy - Braço Direito AI

## Visão Geral

Este diretório contém todos os scripts e configurações necessários para fazer deploy do sistema na VPS.

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `install.sh` | Instalação inicial da VPS (dependências, PostgreSQL, Node.js, etc) |
| `deploy.sh` | Deploy completo do sistema (executa após install.sh) |
| `upload_to_vps.sh` | Script para enviar arquivos do Mac para VPS |
| `setup_backend.sh` | Configuração isolada do backend Python |
| `setup_frontend.sh` | Configuração isolada do frontend React |
| `setup_whatsapp.sh` | Configuração isolada do WhatsApp Server |
| `setup_services.sh` | Configuração dos serviços systemd |
| `nginx.conf` | Configuração do Nginx (proxy reverso) |
| `braco-backend.service` | Serviço systemd para o backend Python |
| `braco-whatsapp.service` | Serviço systemd para o WhatsApp Server |
| `database_backup.sql` | Backup completo do banco de dados |
| `.env.production` | Variáveis de ambiente para produção |

## Requisitos da VPS

- **Sistema Operacional:** Ubuntu 24.04 LTS
- **RAM:** Mínimo 2GB (recomendado 4GB)
- **Disco:** Mínimo 20GB
- **Acesso:** SSH como root

## Deploy Rápido (Do Mac)

### 1. Fazer upload dos arquivos

```bash
cd /Users/david/Documents/GitHub/braco-direto-ai/deploy
bash upload_to_vps.sh
```

### 2. Conectar na VPS

```bash
ssh root@<IP_DA_VPS>
# Credenciais em local seguro (cofre de senhas / 1Password)
```

### 3. Executar instalação inicial (apenas primeira vez)

```bash
cd /var/www/braco-direto-ai/deploy
bash install.sh
```

### 4. Importar banco de dados

```bash
sudo -u postgres psql braco_db < /var/www/braco-direto-ai/deploy/database_backup.sql
```

### 5. Executar deploy

```bash
cd /var/www/braco-direto-ai/deploy
bash deploy.sh
```

## Estrutura na VPS

```
/var/www/braco-direto-ai/
├── backend_example/          # Backend Python (FastAPI)
│   ├── app/                  # Código da aplicação
│   ├── venv/                 # Ambiente virtual Python
│   ├── whatsapp_server.js    # Servidor WhatsApp
│   ├── requirements.txt      # Dependências Python
│   ├── package.json          # Dependências Node.js
│   └── .env                  # Variáveis de ambiente
├── frontend/
│   └── dist/                 # Build de produção do React
├── uploads/                  # Arquivos enviados
├── logs/                     # Logs da aplicação
└── deploy/                   # Scripts de deploy
```

## Portas Utilizadas

| Serviço | Porta | Acesso |
|---------|-------|--------|
| Nginx (HTTP) | 80 | Público |
| Backend Python | 8000 | Interno (via Nginx) |
| WhatsApp Server | 3000 | Interno (via Nginx) |
| PostgreSQL | 5432 | Interno |

## Credenciais

> **As credenciais reais NÃO devem ficar neste repositório.**
> Mantenha em cofre de senhas (1Password, Bitwarden, etc.) e use o `.env` local
> do servidor (`/var/www/braco-direto-ai/backend_example/.env`) como fonte da verdade.

### Banco de Dados (Produção)
- **Host:** localhost
- **Database:** braco_db
- **User:** (ver cofre)
- **Password:** (ver cofre)

### VPS
- **IP:** (ver cofre)
- **User:** (ver cofre; recomendado: login apenas via chave SSH)
- **Password:** (ver cofre)

## Comandos Úteis

### Ver status dos serviços
```bash
systemctl status braco-backend
systemctl status braco-whatsapp
systemctl status nginx
systemctl status postgresql
```

### Ver logs em tempo real
```bash
# Backend Python
journalctl -u braco-backend -f

# WhatsApp Server
journalctl -u braco-whatsapp -f

# Nginx
tail -f /var/log/nginx/braco-direto-ai.error.log
```

### Reiniciar serviços
```bash
# Todos
systemctl restart braco-backend braco-whatsapp nginx

# Individual
systemctl restart braco-backend
systemctl restart braco-whatsapp
systemctl restart nginx
```

### Verificar se API está respondendo
```bash
curl http://localhost:8000/health
curl http://72.60.244.138/api/v1/dashboard/stats
```

## Troubleshooting

### Backend não inicia
```bash
# Ver logs detalhados
journalctl -u braco-backend -n 100

# Testar manualmente
cd /var/www/braco-direto-ai/backend_example
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Erro de conexão com banco
```bash
# Verificar se PostgreSQL está rodando
systemctl status postgresql

# Testar conexão
psql -U braco -d braco_db -h localhost -c "SELECT 1"
```

### WhatsApp não conecta
```bash
# Ver logs
journalctl -u braco-whatsapp -n 100

# Testar manualmente
cd /var/www/braco-direto-ai/backend_example
node whatsapp_server.js
```

### Nginx retorna 502 Bad Gateway
```bash
# Backend provavelmente não está rodando
systemctl restart braco-backend
sleep 5
curl http://localhost:8000/health
```

## Atualização do Sistema

Para atualizar o sistema após mudanças no código:

```bash
# No Mac - enviar arquivos
cd /Users/david/Documents/GitHub/braco-direto-ai/deploy
bash upload_to_vps.sh

# Na VPS - reiniciar serviços
ssh root@72.60.244.138
systemctl restart braco-backend braco-whatsapp nginx
```

## SSL/HTTPS (Futuro)

Quando tiver um domínio, instalar certificado SSL:

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d seu-dominio.com
```

---

**Última atualização:** Janeiro 2026
