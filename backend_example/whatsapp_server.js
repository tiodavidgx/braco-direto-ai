const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const qrTerminal = require('qrcode-terminal');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.WHATSAPP_PORT || 14003;

// Middleware
app.use(cors());
app.use(bodyParser.json());

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
            '--single-process', 
            '--disable-gpu'
        ]
    }
});

// Handler de erro global
whatsappClient.on('error', (error) => {
    console.error('❌ Erro no cliente WhatsApp:', error);
});

// Event handlers
whatsappClient.on('qr', (qr) => {
    console.log('\n📱 QR Code gerado! Escaneie com o WhatsApp:');
    qrTerminal.generate(qr, { small: true });
    
    qrcode.toDataURL(qr, (err, url) => {
        if (err) {
            console.error('Erro ao gerar QR Code:', err);
            return;
        }
        qrCodeData = url;
        console.log('✅ QR Code disponível em: http://localhost:' + PORT + '/qr');
    });
});

whatsappClient.on('ready', async () => {
    console.log('✅ WhatsApp conectado e pronto!');
    isReady = true;
    qrCodeData = null;
    
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
whatsappClient.initialize().catch((error) => {
    console.error('❌ Erro ao inicializar WhatsApp:', error);
});

// ============ ROTAS DA API ============

app.get('/status', (req, res) => {
    res.json({
        success: true,
        status: isReady ? 'connected' : (qrCodeData ? 'qr_ready' : 'initializing'),
        hasQrCode: !!qrCodeData,
        qrCode: qrCodeData,
        info: clientInfo
    });
});

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

app.get('/qr', (req, res) => {
    if (!qrCodeData) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp QR Code</title>
                <meta http-equiv="refresh" content="2">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                    .message { background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    h1 { color: #25D366; }
                </style>
            </head>
            <body>
                <div class="message">
                    <h1>📱 WhatsApp</h1>
                    ${isReady ? '<p>✅ <strong>WhatsApp já está conectado!</strong></p>' : '<p>⏳ Aguardando QR Code...</p><p><small>Esta página atualiza automaticamente</small></p>'}
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
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                .qr-container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                img { max-width: 400px; border: 2px solid #25D366; border-radius: 10px; }
                h1 { color: #25D366; }
            </style>
        </head>
        <body>
            <div class="qr-container">
                <h1>📱 Escaneie o QR Code</h1>
                <img src="${qrCodeData}" alt="QR Code">
            </div>
        </body>
        </html>
    `);
});

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
        const chatId = number.includes('@c.us') ? number : `${number}@c.us`;
        
        // Verificar se a mensagem tem botões (formato: [BUTTONS]...[/BUTTONS])
        const buttonRegex = /\[BUTTONS\]([\s\S]*?)\[\/BUTTONS\]/;
        const buttonMatch = message.match(buttonRegex);
        
        if (buttonMatch) {
            // Extrair texto e botões
            const messageText = message.replace(buttonRegex, '').trim();
            const buttonsText = buttonMatch[1].trim();
            
            // Parse dos botões (formato: [Texto do Botão|id_callback])
            const buttonLines = buttonsText.split('\n').filter(line => line.trim());
            const buttons = buttonLines.map((line, index) => {
                const match = line.match(/\[(.*?)\|(.*?)\]/);
                if (match) {
                    return {
                        body: match[1].trim(),
                        id: match[2].trim()
                    };
                }
                return null;
            }).filter(btn => btn !== null);
            
            if (buttons.length > 0) {
                // Enviar mensagem com botões usando Buttons do whatsapp-web.js
                const { Buttons } = require('whatsapp-web.js');
                const buttonMessage = new Buttons(
                    messageText,
                    buttons.map(btn => ({ body: btn.body, id: btn.id })),
                    'Escolha uma opção',
                    'Novo Mundo'
                );
                
                await whatsappClient.sendMessage(chatId, buttonMessage);
                console.log(`✅ Mensagem com ${buttons.length} botões enviada para ${number}`);
            } else {
                // Se não conseguiu parse dos botões, envia mensagem normal
                await whatsappClient.sendMessage(chatId, messageText);
                console.log(`✅ Mensagem enviada para ${number} (sem botões)`);
            }
        } else {
            // Mensagem sem botões
            await whatsappClient.sendMessage(chatId, message);
            console.log(`✅ Mensagem enviada para ${number}`);
        }
        
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
    console.log(`\n🌐 Servidor WhatsApp rodando em http://localhost:${PORT}`);
    console.log(`📱 Acesse http://localhost:${PORT}/qr para ver o QR Code\n`);
});
