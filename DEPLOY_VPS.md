# 🚀 Guia de Deploy - Braço Direto AI

## Requisitos da VPS

- **OS**: Ubuntu 22.04 ou 24.04 LTS (recomendado)
- **RAM**: Mínimo 2GB (recomendado 4GB)
- **CPU**: 2 vCPUs
- **Disco**: 20GB SSD
- **Acesso**: SSH com usuário root ou sudo

---

## 📋 Arquitetura do Sistema

```
                         Internet
                            │
                            ▼
                    ┌───────────────┐
                    │  Nginx (443)  │
                    │   SSL/HTTPS   │
                    └───────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  Frontend   │  │   Backend   │  │  WhatsApp   │
    │   (3000)    │  │   (3080)    │  │   (3001)    │
    │   React     │  │   FastAPI   │  │   Baileys   │
    └─────────────┘  └─────────────┘  └─────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  PostgreSQL   │
                    │    (5432)     │
                    └───────────────┘
```

---

## 🔧 Passo 1: Preparar a VPS

### 1.1 Conectar na VPS
```bash
ssh root@SEU_IP_DA_VPS
```

### 1.2 Atualizar o sistema
```bash
apt update && apt upgrade -y
```

### 1.3 Instalar dependências básicas
```bash
apt install -y curl git build-essential nginx certbot python3-certbot-nginx
```

### 1.4 Instalar Node.js 20 LTS
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
```

### 1.5 Instalar PM2 (gerenciador de processos)
```bash
npm install -g pm2
```

### 1.6 Instalar Python 3.11+ e pip
```bash
apt install -y python3 python3-pip python3-venv
```

### 1.7 Instalar PostgreSQL
```bash
apt install -y postgresql postgresql-contrib
```

---

## 🗄️ Passo 2: Configurar PostgreSQL

### 2.1 Acessar o PostgreSQL
```bash
sudo -u postgres psql
```

### 2.2 Criar usuário e banco de dados
```sql
CREATE USER bracodireto WITH PASSWORD 'SUA_SENHA_FORTE_AQUI';
CREATE DATABASE bracodireto OWNER bracodireto;
GRANT ALL PRIVILEGES ON DATABASE bracodireto TO bracodireto;
\q
```

### 2.3 Importar schema do banco (depois de clonar o projeto)
```bash
sudo -u postgres psql bracodireto < /var/www/braco-direto-ai/backend_example/scripts/schema.sql
```

---

## 📁 Passo 3: Clonar o Projeto

### 3.1 Criar diretório
```bash
mkdir -p /var/www
cd /var/www
```

### 3.2 Clonar repositório
```bash
git clone https://github.com/davidgsas/braco-direto-ai.git
cd braco-direto-ai
```

---

## ⚙️ Passo 4: Configurar Backend (FastAPI)

### 4.1 Criar ambiente virtual Python
```bash
cd /var/www/braco-direto-ai/backend_example
python3 -m venv venv
source venv/bin/activate
```

### 4.2 Instalar dependências
```bash
pip install -r requirements.txt
```

### 4.3 Criar arquivo .env
```bash
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://bracodireto:SUA_SENHA_FORTE_AQUI@localhost:5432/bracodireto
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bracodireto
DB_USER=bracodireto
DB_PASSWORD=SUA_SENHA_FORTE_AQUI

# Server
HOST=0.0.0.0
PORT=3080

# WhatsApp Service
WHATSAPP_SERVICE_URL=http://localhost:3001

# Environment
ENVIRONMENT=production
EOF
```

### 4.4 Testar backend
```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 3080
# Ctrl+C para parar após testar
```

---

## 📱 Passo 5: Configurar WhatsApp Service (Baileys)

### 5.1 Instalar dependências
```bash
cd /var/www/braco-direto-ai/whatsapp-service
npm install
```

### 5.2 Atualizar porta para 3001
Editar `server.js` e mudar a porta de 3000 para 3001:
```bash
sed -i 's/const PORT = 3000/const PORT = 3001/' server.js
```

### 5.3 Testar serviço
```bash
node server.js
# Ctrl+C para parar após testar
```

---

## 🎨 Passo 6: Configurar Frontend (React)

### 6.1 Instalar dependências
```bash
cd /var/www/braco-direto-ai
npm install
```

### 6.2 Criar arquivo .env.production
```bash
cat > .env.production << 'EOF'
VITE_API_URL=https://SEU_DOMINIO/api
EOF
```

### 6.3 Build do frontend
```bash
npm run build
```

---

## 🔄 Passo 7: Configurar PM2

### 7.1 Criar arquivo ecosystem
```bash
cat > /var/www/braco-direto-ai/ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'braco-backend',
      cwd: '/var/www/braco-direto-ai/backend_example',
      script: 'venv/bin/python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 3080',
      env: {
        NODE_ENV: 'production',
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
    },
    {
      name: 'braco-whatsapp',
      cwd: '/var/www/braco-direto-ai/whatsapp-service',
      script: 'server.js',
      env: {
        NODE_ENV: 'production',
        PORT: 3001,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
    },
  ],
};
EOF
```

### 7.2 Iniciar serviços com PM2
```bash
cd /var/www/braco-direto-ai
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 7.3 Verificar status
```bash
pm2 status
pm2 logs
```

---

## 🌐 Passo 8: Configurar Nginx

### 8.1 Criar configuração do site
```bash
cat > /etc/nginx/sites-available/braco-direto << 'EOF'
server {
    listen 80;
    server_name SEU_DOMINIO www.SEU_DOMINIO;

    # Frontend - arquivos estáticos
    root /var/www/braco-direto-ai/dist;
    index index.html;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    # API Backend
    location /api/ {
        proxy_pass http://localhost:3080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket para WhatsApp
    location /ws/ {
        proxy_pass http://localhost:3001/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Frontend SPA - todas as outras rotas
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache de assets estáticos
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
```

### 8.2 Ativar o site
```bash
ln -s /etc/nginx/sites-available/braco-direto /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # Remove config padrão
nginx -t  # Testar configuração
systemctl reload nginx
```

---

## 🔒 Passo 9: Configurar SSL (HTTPS)

### 9.1 Obter certificado SSL com Let's Encrypt
```bash
certbot --nginx -d SEU_DOMINIO -d www.SEU_DOMINIO
```

### 9.2 Renovação automática (já configurada pelo certbot)
```bash
# Testar renovação
certbot renew --dry-run
```

---

## 🔥 Passo 10: Configurar Firewall

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

---

## ✅ Passo 11: Verificação Final

### 11.1 Verificar serviços
```bash
pm2 status
systemctl status nginx
systemctl status postgresql
```

### 11.2 Testar endpoints
```bash
# Backend
curl http://localhost:3080/health

# WhatsApp
curl http://localhost:3001/status

# Frontend (via Nginx)
curl http://localhost
```

### 11.3 Acessar no navegador
```
https://SEU_DOMINIO
```

---

## 🔄 Comandos Úteis

### Reiniciar serviços
```bash
pm2 restart all
# ou individual
pm2 restart braco-backend
pm2 restart braco-whatsapp
```

### Ver logs
```bash
pm2 logs
pm2 logs braco-backend
pm2 logs braco-whatsapp
```

### Atualizar código
```bash
cd /var/www/braco-direto-ai
git pull origin main
npm install
npm run build
pm2 restart all
```

### Backup do banco
```bash
pg_dump -U bracodireto bracodireto > backup_$(date +%Y%m%d).sql
```

---

## 🆘 Troubleshooting

### Erro de permissão
```bash
chown -R www-data:www-data /var/www/braco-direto-ai
chmod -R 755 /var/www/braco-direto-ai
```

### PM2 não inicia após reboot
```bash
pm2 startup systemd -u root --hp /root
pm2 save
```

### Erro de conexão com PostgreSQL
```bash
# Verificar se PostgreSQL está rodando
systemctl status postgresql

# Ver logs
journalctl -u postgresql
```

### WhatsApp não conecta
```bash
# Limpar sessão e reconectar
rm -rf /var/www/braco-direto-ai/whatsapp-service/auth_info_baileys
pm2 restart braco-whatsapp
# Acessar https://SEU_DOMINIO e escanear QR Code novamente
```

---

## 📞 Suporte

Em caso de dúvidas, verifique:
1. Logs do PM2: `pm2 logs`
2. Logs do Nginx: `tail -f /var/log/nginx/error.log`
3. Status dos serviços: `pm2 status`
