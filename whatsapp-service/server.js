const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const qrTerminal = require('qrcode-terminal');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Auth por token compartilhado
const INTERNAL_TOKEN = process.env.WHATSAPP_INTERNAL_TOKEN || '';
const crypto = require('crypto');
app.use((req, res, next) => {
    if (req.path === '/health') return next();
    if (!INTERNAL_TOKEN) return res.status(503).json({ error: 'service_not_configured' });
    const provided = req.header('X-Internal-Token') || '';
    const a = Buffer.from(provided);
    const b = Buffer.from(INTERNAL_TOKEN);
    if (a.length !== b.length) return res.status(401).json({ error: 'unauthorized' });
    try {
        if (!crypto.timingSafeEqual(a, b)) return res.status(401).json({ error: 'unauthorized' });
    } catch (_) { return res.status(401).json({ error: 'unauthorized' }); }
    next();
});

// Estado da aplicação
let whatsappClient;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;
let isInitializing = false;

// Caminho absoluto para autenticação
const AUTH_PATH = path.join(__dirname, '.wwebjs_auth');

// Função para limpar sessão corrompida
function clearSession() {
    console.log('🧹 Limpando sessão antiga/corrompida...');
    try {
        if (fs.existsSync(AUTH_PATH)) {
            fs.rmSync(AUTH_PATH, { recursive: true, force: true });
            console.log('✅ Sessão limpa com sucesso.');
        }
    } catch (err) {
        console.error('❌ Erro ao limpar sessão:', err);
    }
}

// Inicializar cliente WhatsApp
function initializeClient() {
    if (isInitializing) return;
    isInitializing = true;
    
    console.log('🚀 Inicializando WhatsApp Web...');
    console.log(`📂 Usando diretório de autenticação: ${AUTH_PATH}`);
    
    try {
        whatsappClient = new Client({
            authStrategy: new LocalAuth({
                dataPath: AUTH_PATH
            }),
            puppeteer: {
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            }
        });

        setupEventHandlers();
        whatsappClient.initialize().catch(err => {
            console.error('❌ Erro na inicialização do cliente:', err);
            isInitializing = false;
        });
        
    } catch (err) {
        console.error('❌ Erro fatal ao criar cliente:', err);
        isInitializing = false;
    }
}

function setupEventHandlers() {
    whatsappClient.on('qr', (qr) => {
        console.log('\n📱 QR Code gerado! Escaneie com o WhatsApp:');
        qrTerminal.generate(qr, { small: true });
        
        qrcode.toDataURL(qr, (err, url) => {
            if (err) {
                console.error('Erro ao gerar QR Code:', err);
                return;
            }
            qrCodeData = url;
            console.log('✅ QR Code disponível em: http://localhost:3000/qr');
        });
        isInitializing = false;
    });

    whatsappClient.on('ready', async () => {
        console.log('✅ WhatsApp conectado e pronto!');
        isReady = true;
        qrCodeData = null;
        isInitializing = false;
        
        try {
            const info = await whatsappClient.info;
            clientInfo = {
                name: info.pushname,
                number: info.wid.user,
                platform: info.platform
            };
            console.log(`👤 Usuário: ${clientInfo.name} (${clientInfo.number})`);
        } catch (error) {
            console.error('Erro ao obter info do cliente:', error);
        }
    });

    whatsappClient.on('authenticated', () => {
        console.log('🔐 WhatsApp autenticado!');
        qrCodeData = null;
    });

    whatsappClient.on('auth_failure', (msg) => {
        console.error('❌ Falha na autenticação:', msg);
        qrCodeData = null;
        isInitializing = false;
    });

    whatsappClient.on('disconnected', (reason) => {
        console.log('❌ WhatsApp desconectado:', reason);
        isReady = false;
        clientInfo = null;
        if (reason !== 'LOGOUT') {
            console.log('🔄 Tentando reconectar em 5 segundos...');
            setTimeout(() => {
                initializeClient();
            }, 5000);
        }
    });
}

// Iniciar primeira vez
initializeClient();

// ============ ROTAS DA API ============

app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsApp Service</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
                .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
                .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
                .status.connected { background: #4CAF50; color: white; }
                .status.waiting { background: #FF9800; color: white; }
                .status.error { background: #F44336; color: white; }
                code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
                h1 { color: #25D366; }
                a, button { display: inline-block; margin: 10px 10px 0 0; padding: 10px 20px; background: #25D366; color: white; text-decoration: none; border-radius: 5px; border: none; cursor: pointer; font-size: 16px; }
                a:hover, button:hover { background: #128C7E; }
                .danger { background: #F44336; }
                .danger:hover { background: #D32F2F; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>📱 WhatsApp Service</h1>
                <p>Serviço ativo e rodando na porta ${PORT}</p>
                <p>Status: <span class="status ${isReady ? 'connected' : qrCodeData ? 'waiting' : 'error'}">
                    ${isReady ? 'Conectado ✅' : qrCodeData ? 'Aguardando QR Code 📱' : isInitializing ? 'Inicializando... ⏳' : 'Desconectado ❌'}
                </span></p>
                ${clientInfo ? `<p>👤 Usuário: <strong>${clientInfo.name}</strong> (${clientInfo.number})</p>` : ''}
            </div>
            
            <div class="card">
                <h2>�️ Ações</h2>
                <a href="/qr">📱 Ver QR Code</a>
                <a href="/status">📊 Ver Status JSON</a>
                <form action="/restart" method="POST" style="display:inline;">
                    <button type="submit" class="danger">🔄 Reiniciar Serviço</button>
                </form>
                <form action="/disconnect" method="POST" style="display:inline;">
                    <button type="submit" class="danger">❌ Desconectar</button>
                </form>
            </div>
        </body>
        </html>
    `);
});

app.get('/status', (req, res) => {
    res.json({
        success: true,
        status: isReady ? 'connected' : (qrCodeData ? 'qr_ready' : isInitializing ? 'initializing' : 'disconnected'),
        hasQrCode: !!qrCodeData,
        info: clientInfo
    });
});

app.get('/info', (req, res) => {
    if (!isReady) return res.status(400).json({ success: false, error: 'WhatsApp não está conectado' });
    res.json({ success: true, info: clientInfo });
});

app.get('/qr', (req, res) => {
    if (!qrCodeData) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp QR Code</title>
                <meta http-equiv="refresh" content="2">
                <style>body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; } h1 { color: #25D366; }</style>
            </head>
            <body>
                <h1>📱 WhatsApp</h1>
                ${isReady ? '<p>✅ <strong>WhatsApp já está conectado!</strong></p>' : '<p>⏳ Aguardando QR Code...</p>'}
            </body>
            </html>
        `);
        return;
    }
    res.send(`
        <!DOCTYPE html>
        <html>
        <head><title>WhatsApp QR Code</title><style>body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; } img { max-width: 400px; border: 2px solid #25D366; border-radius: 10px; }</style></head>
        <body>
            <h1>📱 Escaneie o QR Code</h1>
            <img src="${qrCodeData}" alt="QR Code">
        </body>
        </html>
    `);
});

app.post('/send', async (req, res) => {
    if (!isReady) return res.status(400).json({ success: false, error: 'WhatsApp não está conectado' });
    const { number, message } = req.body;
    if (!number || !message) return res.status(400).json({ success: false, error: 'Dados incompletos' });
    
    try {
        const chatId = number.includes('@c.us') ? number : `${number}@c.us`;
        await whatsappClient.sendMessage(chatId, message);
        console.log(`✅ Mensagem enviada para ${number}`);
        res.json({ success: true, message: 'Enviada' });
    } catch (error) {
        console.error('❌ Erro ao enviar:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/send-bulk', async (req, res) => {
    if (!isReady) return res.status(400).json({ success: false, error: 'WhatsApp não está conectado' });
    const { numbers, message, delay = 3000 } = req.body;
    
    const results = { success: [], failed: [] };
    console.log(`📤 Iniciando envio em massa para ${numbers.length} números...`);
    
    for (const number of numbers) {
        try {
            const chatId = number.includes('@c.us') ? number : `${number}@c.us`;
            await whatsappClient.sendMessage(chatId, message);
            results.success.push(number);
            console.log(`✅ ${number}`);
        } catch (error) {
            results.failed.push({ number, error: error.message });
            console.error(`❌ ${number}: ${error.message}`);
        }
        if (numbers.indexOf(number) < numbers.length - 1) await new Promise(r => setTimeout(r, delay));
    }
    res.json({ success: true, results });
});

app.post('/disconnect', async (req, res) => {
    try {
        if (whatsappClient) await whatsappClient.destroy();
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        console.log('❌ WhatsApp desconectado manualmente');
        res.json({ success: true, message: 'Desconectado' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/restart', async (req, res) => {
    console.log('🔄 Reiniciando serviço WhatsApp...');
    try {
        if (whatsappClient) {
            await whatsappClient.destroy();
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        
        setTimeout(() => initializeClient(), 1000);
        
        res.json({ success: true, message: 'Reiniciando...' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Graceful Shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Encerrando servidor...');
    if (whatsappClient) {
        console.log('🔒 Fechando sessão do WhatsApp...');
        await whatsappClient.destroy();
    }
    process.exit(0);
});

app.listen(PORT, () => {
    console.log(`\n🌐 Servidor rodando em http://localhost:${PORT}`);
});