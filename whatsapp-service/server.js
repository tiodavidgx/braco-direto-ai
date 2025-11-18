const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const qrTerminal = require('qrcode-terminal');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Estado da aplicação
let whatsappClient;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;

// Inicializar cliente WhatsApp
console.log('🚀 Inicializando WhatsApp Web...');

whatsappClient = new Client({
    authStrategy: new LocalAuth({
        dataPath: './.wwebjs_auth'
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

// Event handlers
whatsappClient.on('qr', (qr) => {
    console.log('\n📱 QR Code gerado! Escaneie com o WhatsApp:');
    qrTerminal.generate(qr, { small: true });
    
    // Gerar QR Code para exibição no navegador
    qrcode.toDataURL(qr, (err, url) => {
        if (err) {
            console.error('Erro ao gerar QR Code:', err);
            return;
        }
        qrCodeData = url;
        console.log('✅ QR Code disponível em: http://localhost:3000/qr');
    });
});

whatsappClient.on('ready', async () => {
    console.log('✅ WhatsApp conectado e pronto!');
    isReady = true;
    qrCodeData = null;
    
    // Obter informações do cliente
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
});

whatsappClient.on('disconnected', (reason) => {
    console.log('❌ WhatsApp desconectado:', reason);
    isReady = false;
    clientInfo = null;
});

// Inicializar cliente
whatsappClient.initialize();

// ============ ROTAS DA API ============

// Página inicial
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsApp Service</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .card {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }
                .status {
                    display: inline-block;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-weight: bold;
                }
                .status.connected { background: #4CAF50; color: white; }
                .status.waiting { background: #FF9800; color: white; }
                .status.error { background: #F44336; color: white; }
                code {
                    background: #f5f5f5;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }
                h1 { color: #25D366; }
                a {
                    display: inline-block;
                    margin: 10px 10px 0 0;
                    padding: 10px 20px;
                    background: #25D366;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
                a:hover { background: #128C7E; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>📱 WhatsApp Service</h1>
                <p>Serviço ativo e rodando na porta ${PORT}</p>
                <p>Status: <span class="status ${isReady ? 'connected' : qrCodeData ? 'waiting' : 'error'}">
                    ${isReady ? 'Conectado ✅' : qrCodeData ? 'Aguardando QR Code 📱' : 'Inicializando... ⏳'}
                </span></p>
                ${clientInfo ? `<p>👤 Usuário: <strong>${clientInfo.name}</strong> (${clientInfo.number})</p>` : ''}
            </div>
            
            <div class="card">
                <h2>🔗 Endpoints Disponíveis</h2>
                <ul>
                    <li><code>GET /status</code> - Verificar status da conexão</li>
                    <li><code>GET /info</code> - Informações do usuário conectado</li>
                    <li><code>GET /qr</code> - Visualizar QR Code (se disponível)</li>
                    <li><code>POST /send</code> - Enviar mensagem individual</li>
                    <li><code>POST /send-bulk</code> - Enviar mensagens em massa</li>
                    <li><code>POST /disconnect</code> - Desconectar WhatsApp</li>
                </ul>
                <a href="/qr">📱 Ver QR Code</a>
                <a href="/status">📊 Ver Status JSON</a>
            </div>
        </body>
        </html>
    `);
});

// Verificar status
app.get('/status', (req, res) => {
    res.json({
        success: true,
        status: isReady ? 'connected' : (qrCodeData ? 'qr_ready' : 'initializing'),
        hasQrCode: !!qrCodeData,
        info: clientInfo
    });
});

// Obter informações do usuário
app.get('/info', (req, res) => {
    if (!isReady) {
        return res.status(400).json({
            success: false,
            error: 'WhatsApp não está conectado'
        });
    }
    
    res.json({
        success: true,
        info: clientInfo
    });
});

// Visualizar QR Code
app.get('/qr', (req, res) => {
    if (!qrCodeData) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp QR Code</title>
                <meta http-equiv="refresh" content="2">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        text-align: center;
                        padding: 50px;
                        background: #f5f5f5;
                    }
                    .message {
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        max-width: 500px;
                        margin: 0 auto;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 { color: #25D366; }
                </style>
            </head>
            <body>
                <div class="message">
                    <h1>📱 WhatsApp</h1>
                    ${isReady ? 
                        '<p>✅ <strong>WhatsApp já está conectado!</strong></p>' : 
                        '<p>⏳ Aguardando QR Code...</p><p><small>Esta página atualiza automaticamente</small></p>'
                    }
                </div>
            </body>
            </html>
        `);
        return;
    }
    
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsApp QR Code</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: #f5f5f5;
                }
                .qr-container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    display: inline-block;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                img {
                    max-width: 400px;
                    border: 2px solid #25D366;
                    border-radius: 10px;
                }
                h1 { color: #25D366; }
                .instructions {
                    max-width: 500px;
                    margin: 20px auto;
                    text-align: left;
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                }
                .instructions li {
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="qr-container">
                <h1>📱 Escaneie o QR Code</h1>
                <img src="${qrCodeData}" alt="QR Code">
            </div>
            
            <div class="instructions">
                <h3>Como conectar:</h3>
                <ol>
                    <li>Abra o WhatsApp no seu celular</li>
                    <li>Toque em <strong>Menu</strong> ou <strong>Configurações</strong></li>
                    <li>Selecione <strong>Aparelhos conectados</strong></li>
                    <li>Toque em <strong>Conectar um aparelho</strong></li>
                    <li>Aponte a câmera para este código</li>
                </ol>
            </div>
        </body>
        </html>
    `);
});

// Enviar mensagem individual
app.post('/send', async (req, res) => {
    if (!isReady) {
        return res.status(400).json({
            success: false,
            error: 'WhatsApp não está conectado'
        });
    }
    
    const { number, message } = req.body;
    
    if (!number || !message) {
        return res.status(400).json({
            success: false,
            error: 'Número e mensagem são obrigatórios'
        });
    }
    
    try {
        // Formatar número
        const chatId = number.includes('@c.us') ? number : `${number}@c.us`;
        
        // Enviar mensagem
        await whatsappClient.sendMessage(chatId, message);
        
        console.log(`✅ Mensagem enviada para ${number}`);
        
        res.json({
            success: true,
            message: 'Mensagem enviada com sucesso',
            to: number
        });
    } catch (error) {
        console.error('❌ Erro ao enviar mensagem:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Enviar mensagens em massa
app.post('/send-bulk', async (req, res) => {
    if (!isReady) {
        return res.status(400).json({
            success: false,
            error: 'WhatsApp não está conectado'
        });
    }
    
    const { numbers, message, delay = 3000 } = req.body;
    
    if (!numbers || !Array.isArray(numbers) || numbers.length === 0) {
        return res.status(400).json({
            success: false,
            error: 'Lista de números é obrigatória'
        });
    }
    
    if (!message) {
        return res.status(400).json({
            success: false,
            error: 'Mensagem é obrigatória'
        });
    }
    
    const results = {
        success: [],
        failed: []
    };
    
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
        
        // Aguardar delay entre mensagens
        if (numbers.indexOf(number) < numbers.length - 1) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    console.log(`📊 Envio concluído: ${results.success.length} sucesso, ${results.failed.length} falhas`);
    
    res.json({
        success: true,
        message: 'Envio em massa concluído',
        results: results,
        total: numbers.length,
        sent: results.success.length,
        failed: results.failed.length
    });
});

// Desconectar
app.post('/disconnect', async (req, res) => {
    try {
        await whatsappClient.destroy();
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        
        console.log('❌ WhatsApp desconectado manualmente');
        
        res.json({
            success: true,
            message: 'WhatsApp desconectado'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`\n🌐 Servidor rodando em http://localhost:${PORT}`);
    console.log(`📱 Acesse http://localhost:${PORT}/qr para ver o QR Code\n`);
});
