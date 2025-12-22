const express = require('express');
const { 
    default: makeWASocket, 
    useMultiFileAuthState, 
    DisconnectReason,
    fetchLatestBaileysVersion,
    makeCacheableSignalKeyStore
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode');
const qrTerminal = require('qrcode-terminal');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
const pino = require('pino');

const app = express();
const PORT = 3000;

// Logger silencioso para Baileys
const logger = pino({ level: 'silent' });

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Estado da aplicacao
let sock = null;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;
let isInitializing = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Caminho para autenticacao
const AUTH_PATH = path.join(__dirname, 'auth_info_baileys');

// Funcao para limpar sessao
function clearSession() {
    console.log('Limpando sessao antiga/corrompida...');
    try {
        if (fs.existsSync(AUTH_PATH)) {
            fs.rmSync(AUTH_PATH, { recursive: true, force: true });
            console.log('Sessao limpa com sucesso.');
        }
    } catch (err) {
        console.error('Erro ao limpar sessao:', err);
    }
}

// Formatar numero para o padrao WhatsApp
function formatNumber(number) {
    let cleaned = number.replace(/\D/g, '');
    if (cleaned.length === 11 || cleaned.length === 10) {
        cleaned = '55' + cleaned;
    }
    return cleaned;
}

// Inicializar cliente WhatsApp com Baileys
async function initializeClient() {
    if (isInitializing) return;
    isInitializing = true;
    
    console.log('Inicializando WhatsApp com Baileys...');
    console.log('Usando diretorio de autenticacao: ' + AUTH_PATH);
    
    try {
        const { state, saveCreds } = await useMultiFileAuthState(AUTH_PATH);
        const { version } = await fetchLatestBaileysVersion();
        console.log('Usando WA versao: ' + version.join('.'));
        
        sock = makeWASocket({
            version,
            logger,
            printQRInTerminal: false,
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger)
            },
            generateHighQualityLinkPreview: true,
            getMessage: async () => undefined
        });
        
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                console.log('\nQR Code gerado! Escaneie com o WhatsApp:');
                qrTerminal.generate(qr, { small: true });
                
                qrcode.toDataURL(qr, (err, url) => {
                    if (err) {
                        console.error('Erro ao gerar QR Code:', err);
                        return;
                    }
                    qrCodeData = url;
                    console.log('QR Code disponivel em: http://localhost:3000/qr');
                });
                isInitializing = false;
            }
            
            if (connection === 'close') {
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                
                console.log('Conexao fechada. Codigo: ' + statusCode);
                isReady = false;
                clientInfo = null;
                qrCodeData = null;
                isInitializing = false;
                
                if (shouldReconnect && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttempts++;
                    console.log('Tentando reconectar... (' + reconnectAttempts + '/' + MAX_RECONNECT_ATTEMPTS + ')');
                    setTimeout(() => initializeClient(), 3000);
                } else if (statusCode === DisconnectReason.loggedOut) {
                    console.log('Usuario fez logout. Limpando sessao...');
                    clearSession();
                }
            }
            
            if (connection === 'open') {
                console.log('WhatsApp conectado e pronto!');
                isReady = true;
                qrCodeData = null;
                isInitializing = false;
                reconnectAttempts = 0;
                
                try {
                    const user = sock.user;
                    if (user) {
                        clientInfo = {
                            name: user.name || user.verifiedName || 'Usuario',
                            number: user.id.split(':')[0].split('@')[0],
                            platform: 'Baileys'
                        };
                        console.log('Usuario: ' + clientInfo.name + ' (' + clientInfo.number + ')');
                    }
                } catch (error) {
                    console.error('Erro ao obter info do cliente:', error);
                }
            }
        });
        
        sock.ev.on('creds.update', saveCreds);
        
        sock.ev.on('messages.upsert', async ({ messages }) => {
            for (const msg of messages) {
                if (!msg.key.fromMe && msg.message) {
                    const sender = msg.key.remoteJid;
                    const text = msg.message.conversation || msg.message.extendedTextMessage?.text || '[Midia]';
                    console.log('Mensagem de ' + sender + ': ' + text.substring(0, 50) + '...');
                }
            }
        });
        
    } catch (err) {
        console.error('Erro fatal ao criar cliente:', err);
        isInitializing = false;
    }
}

initializeClient();

// ROTAS DA API

app.get('/', (req, res) => {
    const statusClass = isReady ? 'connected' : qrCodeData ? 'waiting' : 'error';
    const statusText = isReady ? 'Conectado' : qrCodeData ? 'Aguardando QR Code' : isInitializing ? 'Inicializando...' : 'Desconectado';
    const userInfo = clientInfo ? '<p>Usuario: <strong>' + clientInfo.name + '</strong> (' + clientInfo.number + ')</p>' : '';
    
    res.send('<html><head><title>WhatsApp Service - Baileys</title><style>body{font-family:Arial,sans-serif;max-width:800px;margin:50px auto;padding:20px;background:#f5f5f5}.card{background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);margin-bottom:20px}.status{display:inline-block;padding:5px 15px;border-radius:20px;font-weight:bold}.status.connected{background:#4CAF50;color:white}.status.waiting{background:#FF9800;color:white}.status.error{background:#F44336;color:white}code{background:#f5f5f5;padding:2px 6px;border-radius:3px}h1{color:#25D366}a,button{display:inline-block;margin:10px 10px 0 0;padding:10px 20px;background:#25D366;color:white;text-decoration:none;border-radius:5px;border:none;cursor:pointer;font-size:16px}a:hover,button:hover{background:#128C7E}.danger{background:#F44336}.danger:hover{background:#D32F2F}.badge{background:#007bff;color:white;padding:3px 8px;border-radius:3px;font-size:12px;margin-left:10px}</style></head><body><div class="card"><h1>WhatsApp Service <span class="badge">Baileys</span></h1><p>Servico ativo na porta ' + PORT + '</p><p>Status: <span class="status ' + statusClass + '">' + statusText + '</span></p>' + userInfo + '</div><div class="card"><h2>Acoes</h2><a href="/qr">Ver QR Code</a><a href="/status">Ver Status JSON</a><form action="/restart" method="POST" style="display:inline;"><button type="submit" class="danger">Reiniciar</button></form><form action="/disconnect" method="POST" style="display:inline;"><button type="submit" class="danger">Desconectar</button></form></div><div class="card"><h2>Endpoints da API</h2><ul><li><code>GET /status</code> - Status da conexao</li><li><code>GET /qr</code> - QR Code</li><li><code>GET /info</code> - Info do usuario</li><li><code>POST /send</code> - Enviar mensagem</li><li><code>POST /send-bulk</code> - Envio em massa</li><li><code>POST /disconnect</code> - Desconectar</li><li><code>POST /restart</code> - Reiniciar</li></ul></div></body></html>');
});

app.get('/status', (req, res) => {
    res.json({
        success: true,
        status: isReady ? 'connected' : (qrCodeData ? 'qr_ready' : isInitializing ? 'initializing' : 'disconnected'),
        hasQrCode: !!qrCodeData,
        info: clientInfo,
        library: 'baileys'
    });
});

app.get('/info', (req, res) => {
    if (!isReady) return res.status(400).json({ success: false, error: 'WhatsApp nao esta conectado' });
    res.json({ success: true, info: clientInfo });
});

app.get('/qr', (req, res) => {
    if (!qrCodeData) {
        const content = isReady ? '<p>WhatsApp ja esta conectado!</p><a href="/">Voltar</a>' : '<p>Aguardando QR Code...</p><p>A pagina sera atualizada automaticamente.</p>';
        res.send('<html><head><title>WhatsApp QR Code</title><meta http-equiv="refresh" content="2"><style>body{font-family:Arial,sans-serif;text-align:center;padding:50px;background:#f5f5f5}h1{color:#25D366}</style></head><body><h1>WhatsApp</h1>' + content + '</body></html>');
        return;
    }
    res.send('<html><head><title>WhatsApp QR Code</title><meta http-equiv="refresh" content="30"><style>body{font-family:Arial,sans-serif;text-align:center;padding:50px;background:#f5f5f5}img{max-width:400px;border:2px solid #25D366;border-radius:10px}h1{color:#25D366}</style></head><body><h1>Escaneie o QR Code</h1><p>Abra o WhatsApp no seu celular e escaneie o codigo abaixo:</p><img src="' + qrCodeData + '" alt="QR Code"><p style="margin-top:20px;color:#666;">A pagina sera atualizada automaticamente.</p></body></html>');
});

app.get('/qr-image', (req, res) => {
    if (!qrCodeData) {
        return res.status(404).json({ success: false, error: 'QR Code nao disponivel' });
    }
    res.json({ success: true, qrCode: qrCodeData });
});

app.post('/send', async (req, res) => {
    if (!isReady || !sock) {
        return res.status(400).json({ success: false, error: 'WhatsApp nao esta conectado' });
    }
    
    const { number, message } = req.body;
    if (!number || !message) {
        return res.status(400).json({ success: false, error: 'Dados incompletos. Envie: { number, message }' });
    }
    
    try {
        const formattedNumber = formatNumber(number);
        const jid = formattedNumber + '@s.whatsapp.net';
        
        await sock.sendMessage(jid, { text: message });
        
        console.log('Mensagem enviada para ' + formattedNumber);
        res.json({ success: true, message: 'Mensagem enviada com sucesso', number: formattedNumber });
    } catch (error) {
        console.error('Erro ao enviar:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/send-bulk', async (req, res) => {
    if (!isReady || !sock) {
        return res.status(400).json({ success: false, error: 'WhatsApp nao esta conectado' });
    }
    
    const { numbers, message, delay = 3000 } = req.body;
    
    if (!numbers || !Array.isArray(numbers) || !message) {
        return res.status(400).json({ success: false, error: 'Dados incompletos. Envie: { numbers: [], message }' });
    }
    
    const results = { 
        success: true,
        sent: 0, 
        failed: 0, 
        results: [] 
    };
    
    console.log('Iniciando envio em massa para ' + numbers.length + ' numeros...');
    
    for (let i = 0; i < numbers.length; i++) {
        const number = numbers[i];
        try {
            const formattedNumber = formatNumber(number);
            const jid = formattedNumber + '@s.whatsapp.net';
            
            await sock.sendMessage(jid, { text: message });
            
            results.sent++;
            results.results.push({ number: formattedNumber, success: true });
            console.log('[' + (i + 1) + '/' + numbers.length + '] ' + formattedNumber);
        } catch (error) {
            results.failed++;
            results.results.push({ number, success: false, error: error.message });
            console.error('[' + (i + 1) + '/' + numbers.length + '] ' + number + ': ' + error.message);
        }
        
        if (i < numbers.length - 1) {
            await new Promise(r => setTimeout(r, delay));
        }
    }
    
    console.log('Envio em massa concluido: ' + results.sent + ' enviadas, ' + results.failed + ' falhas');
    res.json(results);
});

app.post('/disconnect', async (req, res) => {
    try {
        if (sock) {
            await sock.logout();
            sock = null;
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        console.log('WhatsApp desconectado manualmente');
        res.json({ success: true, message: 'Desconectado com sucesso' });
    } catch (error) {
        console.error('Erro ao desconectar:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/restart', async (req, res) => {
    console.log('Reiniciando servico WhatsApp...');
    try {
        if (sock) {
            try { await sock.end(); } catch (e) {}
            sock = null;
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        reconnectAttempts = 0;
        
        setTimeout(() => initializeClient(), 1000);
        
        res.json({ success: true, message: 'Servico sendo reiniciado...' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/clear-session', async (req, res) => {
    console.log('Limpando sessao...');
    try {
        if (sock) {
            try { await sock.end(); } catch (e) {}
            sock = null;
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        
        clearSession();
        
        setTimeout(() => initializeClient(), 1000);
        
        res.json({ success: true, message: 'Sessao limpa. Reiniciando...' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

process.on('SIGINT', async () => {
    console.log('\nEncerrando servidor...');
    if (sock) {
        console.log('Fechando conexao do WhatsApp...');
        try { await sock.end(); } catch (e) {}
    }
    process.exit(0);
});

process.on('uncaughtException', (err) => {
    console.error('Erro nao tratado:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Promise rejeitada:', reason);
});

app.listen(PORT, () => {
    console.log('\nServidor WhatsApp (Baileys) rodando em http://localhost:' + PORT);
    console.log('Biblioteca: @whiskeysockets/baileys v7.0.0');
});
