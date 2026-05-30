const express = require('express');
const { default: makeWASocket, DisconnectReason, useMultiFileAuthState, Browsers, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
const pino = require('pino');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Auth por token compartilhado (backend -> whatsapp service)
// Protege TODAS as rotas (exceto /health e /qr que podem ser acessadas internamente via proxy).
const INTERNAL_TOKEN = process.env.WHATSAPP_INTERNAL_TOKEN || '';
app.use((req, res, next) => {
    // Rotas públicas (health check apenas)
    if (req.path === '/health') return next();
    if (!INTERNAL_TOKEN) {
        console.warn('⚠️  WHATSAPP_INTERNAL_TOKEN não configurado — serviço rejeitará todas as chamadas.');
        return res.status(503).json({ error: 'service_not_configured' });
    }
    const provided = req.header('X-Internal-Token') || '';
    // Comparação em tempo constante para evitar timing attacks
    const a = Buffer.from(provided);
    const b = Buffer.from(INTERNAL_TOKEN);
    if (a.length !== b.length) return res.status(401).json({ error: 'unauthorized' });
    try {
        const crypto = require('crypto');
        if (!crypto.timingSafeEqual(a, b)) return res.status(401).json({ error: 'unauthorized' });
    } catch (_) {
        return res.status(401).json({ error: 'unauthorized' });
    }
    next();
});

// Estado da aplicação
let sock = null;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;
let isInitializing = false;
let reconnectAttempts = 0;
let qrCodeAttempts = 0;  // Contador de QR codes gerados sem sucesso
const MAX_RECONNECT_ATTEMPTS = 15;
const MAX_QR_ATTEMPTS = 10;  // Após 10 QR codes não escaneados, limpa sessão

// Caminho para autenticação
const AUTH_PATH = path.join(__dirname, 'auth_info_baileys');

// Logger silencioso
const logger = pino({ level: 'silent' });

// Função para limpar sessão
function clearSession() {
    console.log('🧹 Limpando sessão antiga...');
    try {
        if (fs.existsSync(AUTH_PATH)) {
            fs.rmSync(AUTH_PATH, { recursive: true, force: true });
            console.log('✅ Sessão limpa com sucesso.');
        }
    } catch (err) {
        console.error('❌ Erro ao limpar sessão:', err);
    }
}

// Formatar número para WhatsApp (removendo o nono dígito dos celulares brasileiros)
function formatNumber(number) {
    // Remove caracteres não numéricos
    let cleaned = number.replace(/\D/g, '');
    
    // Se começar com 0, remove
    if (cleaned.startsWith('0')) {
        cleaned = cleaned.substring(1);
    }
    
    // Se não tiver código do país, adiciona 55 (Brasil)
    if (cleaned.length <= 11) {
        cleaned = '55' + cleaned;
    }
    
    // Remover o nono dígito dos celulares brasileiros
    // Formato esperado: 55 + DDD (2 dígitos) + 9 + 8 dígitos = 13 dígitos
    // O WhatsApp brasileiro usa apenas 8 dígitos após o DDD
    if (cleaned.startsWith('55') && cleaned.length === 13) {
        const ddd = cleaned.substring(2, 4);
        const ninthDigit = cleaned.substring(4, 5);
        const restOfNumber = cleaned.substring(5);
        
        // Se o 5º dígito for 9 (nono dígito dos celulares), remove ele
        if (ninthDigit === '9') {
            cleaned = '55' + ddd + restOfNumber;
            console.log(`📞 Número formatado: removido nono dígito -> ${cleaned}`);
        }
    }
    
    return cleaned + '@s.whatsapp.net';
}

// Inicializar cliente WhatsApp com Baileys
async function initializeClient() {
    if (isInitializing) {
        console.log('⏳ Já está inicializando...');
        return;
    }
    
    isInitializing = true;
    console.log('🚀 Inicializando WhatsApp com Baileys...');
    
    try {
        // Carregar estado de autenticação
        const { state, saveCreds } = await useMultiFileAuthState(AUTH_PATH);
        
        // Criar socket
        // Buscar versão mais recente do protocolo (fallback para versão fixa)
        let waVersion = [2, 3000, 1033893291];
        try {
            const { version } = await fetchLatestBaileysVersion();
            waVersion = version;
            console.log(`📋 Versão do protocolo WhatsApp: ${version.join('.')}`);
        } catch (err) {
            console.log(`⚠️ Não foi possível buscar versão mais recente, usando fallback: ${waVersion.join('.')}`);
        }
        
        sock = makeWASocket({
            auth: state,
            printQRInTerminal: true,
            logger: logger,
            browser: Browsers.ubuntu('Chrome'),
            version: waVersion,
            connectTimeoutMs: 60000,
            defaultQueryTimeoutMs: 0,
            keepAliveIntervalMs: 30000,
            emitOwnEvents: true,
            markOnlineOnConnect: false,
            generateHighQualityLinkPreview: false,
        });
        
        // Evento de atualização de conexão
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            // QR Code gerado
            if (qr) {
                qrCodeAttempts++;
                console.log(`\n📱 QR Code gerado! (tentativa ${qrCodeAttempts}/${MAX_QR_ATTEMPTS}) Escaneie com o WhatsApp:`);
                
                // Se já tentou muitos QR codes sem sucesso, limpar sessão
                if (qrCodeAttempts > MAX_QR_ATTEMPTS) {
                    console.log('⚠️ Muitas tentativas de QR code sem sucesso. Limpando sessão...');
                    qrCodeAttempts = 0;
                    if (sock) {
                        sock.ev.removeAllListeners();
                        sock.ws.close();
                        sock = null;
                    }
                    clearSession();
                    isInitializing = false;
                    setTimeout(() => initializeClient(), 3000);
                    return;
                }
                
                try {
                    qrCodeData = await qrcode.toDataURL(qr);
                    console.log('✅ QR Code disponível em: http://localhost:' + PORT + '/qr');
                } catch (err) {
                    console.error('Erro ao gerar QR Code:', err);
                }
                isInitializing = false;
            }
            
            // Conectado
            if (connection === 'open') {
                console.log('✅ WhatsApp conectado e pronto!');
                isReady = true;
                qrCodeData = null;
                isInitializing = false;
                reconnectAttempts = 0;
                qrCodeAttempts = 0;  // Resetar contador de QR codes
                
                // Obter informações do usuário
                if (sock.user) {
                    clientInfo = {
                        name: sock.user.name || 'Usuário',
                        number: sock.user.id.split(':')[0].split('@')[0],
                        platform: 'Baileys'
                    };
                    console.log(`👤 Usuário: ${clientInfo.name} (${clientInfo.number})`);
                }
            }
            
            // Desconectado
            if (connection === 'close') {
                isReady = false;
                qrCodeData = null;
                isInitializing = false;
                
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                console.log(`❌ Conexão fechada. Código: ${statusCode}`);
                
                // Códigos que indicam sessão REALMENTE inválida — limpar e gerar novo QR
                // IMPORTANTE: NÃO incluir códigos transitórios como:
                //   408 (connectionLost) = rede caiu temporariamente
                //   428 (connectionClosed) = WebSocket fechou normalmente
                //   440 (connectionReplaced) = outra conexão aberta
                // Esses são eventos normais e NÃO devem limpar a sessão!
                const SESSION_INVALID_CODES = [
                    DisconnectReason.loggedOut,  // 401 — logout explícito
                    405,                          // Method Not Allowed (protocolo incompatível)
                    410,                          // Gone (sessão removida pelo servidor)
                ];
                
                if (SESSION_INVALID_CODES.includes(statusCode)) {
                    console.log(`🚪 Sessão inválida (código ${statusCode}). Limpando e gerando novo QR...`);
                    clearSession();
                    clientInfo = null;
                    reconnectAttempts = 0;
                    // Reiniciar para gerar novo QR code
                    setTimeout(() => initializeClient(), 3000);
                } else if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                    console.log(`🔄 Reconectando em ${delay/1000}s... (tentativa ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
                    setTimeout(() => initializeClient(), delay);
                } else {
                    // Máximo de tentativas atingido — NÃO limpar sessão!
                    // Apenas esperar mais tempo e tentar novamente
                    console.log(`⏳ Máximo de tentativas (${MAX_RECONNECT_ATTEMPTS}) atingido. Aguardando 5 minutos antes de tentar novamente...`);
                    reconnectAttempts = 0;
                    setTimeout(() => initializeClient(), 5 * 60 * 1000); // 5 minutos
                }
            }
        });
        
        // Salvar credenciais quando atualizadas
        sock.ev.on('creds.update', saveCreds);
        
        // Log de mensagens recebidas (opcional)
        sock.ev.on('messages.upsert', async (m) => {
            if (m.type === 'notify') {
                for (const msg of m.messages) {
                    if (!msg.key.fromMe && msg.message) {
                        const sender = msg.key.remoteJid;
                        const text = msg.message.conversation || 
                                    msg.message.extendedTextMessage?.text || 
                                    '[mídia]';
                        console.log(`📩 Mensagem de ${sender}: ${text.substring(0, 50)}...`);
                    }
                }
            }
        });
        
    } catch (err) {
        console.error('❌ Erro ao inicializar:', err);
        isInitializing = false;
    }
}

// NÃO inicializar aqui - será feito no app.listen

// ============ ROTAS DA API ============

app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsApp Service - Baileys</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
                .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
                .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
                .status.connected { background: #4CAF50; color: white; }
                .status.waiting { background: #FF9800; color: white; }
                .status.error { background: #F44336; color: white; }
                h1 { color: #25D366; }
                a, button { display: inline-block; margin: 10px 10px 0 0; padding: 10px 20px; background: #25D366; color: white; text-decoration: none; border-radius: 5px; border: none; cursor: pointer; font-size: 16px; }
                a:hover, button:hover { background: #128C7E; }
                .danger { background: #F44336; }
                .danger:hover { background: #D32F2F; }
                .badge { background: #128C7E; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>📱 WhatsApp Service <span class="badge">Baileys</span></h1>
                <p>Serviço ativo e rodando na porta ${PORT}</p>
                <p>Status: <span class="status ${isReady ? 'connected' : qrCodeData ? 'waiting' : 'error'}">
                    ${isReady ? 'Conectado ✅' : qrCodeData ? 'Aguardando QR Code 📱' : isInitializing ? 'Inicializando... ⏳' : 'Desconectado ❌'}
                </span></p>
                ${clientInfo ? `<p>👤 Usuário: <strong>${clientInfo.name}</strong> (${clientInfo.number})</p>` : ''}
            </div>
            
            <div class="card">
                <h2>🛠️ Ações</h2>
                <a href="/qr">📱 Ver QR Code</a>
                <a href="/status">📊 Ver Status JSON</a>
                <form action="/restart" method="POST" style="display:inline;">
                    <button type="submit">🔄 Reiniciar</button>
                </form>
                <form action="/force-new-qr" method="POST" style="display:inline;">
                    <button type="submit" style="background:#FF9800;">🔥 Forçar Novo QR</button>
                </form>
                <form action="/logout" method="POST" style="display:inline;">
                    <button type="submit" class="danger">🚪 Logout</button>
                </form>
            </div>
            
            <div class="card">
                <h2>📡 Endpoints da API</h2>
                <ul>
                    <li><code>GET /status</code> - Status da conexão</li>
                    <li><code>GET /qr</code> - QR Code para conexão</li>
                    <li><code>POST /send</code> - Enviar mensagem</li>
                    <li><code>POST /send-bulk</code> - Enviar em massa</li>
                    <li><code>POST /restart</code> - Reiniciar serviço</li>
                    <li><code>POST /logout</code> - Deslogar</li>
                </ul>
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
        info: clientInfo,
        engine: 'baileys'
    });
});

app.get('/info', (req, res) => {
    if (!isReady) {
        return res.status(400).json({ success: false, error: 'WhatsApp não está conectado' });
    }
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
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                    h1 { color: #25D366; }
                    .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #25D366; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                </style>
            </head>
            <body>
                <h1>📱 WhatsApp</h1>
                ${isReady ? '<p>✅ <strong>WhatsApp já está conectado!</strong></p><a href="/">Voltar</a>' : '<div class="spinner"></div><p>⏳ Aguardando QR Code...</p>'}
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
            <meta http-equiv="refresh" content="30">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                img { max-width: 350px; border: 3px solid #25D366; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
                h1 { color: #25D366; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <h1>📱 Escaneie o QR Code</h1>
            <p>Abra o WhatsApp no seu celular > Menu > Aparelhos conectados > Conectar um aparelho</p>
            <img src="${qrCodeData}" alt="QR Code">
            <p><small>Esta página atualiza automaticamente</small></p>
        </body>
        </html>
    `);
});

// Enviar mensagem
app.post('/send', async (req, res) => {
    if (!isReady || !sock) {
        return res.status(400).json({ success: false, error: 'WhatsApp não está conectado' });
    }
    
    const { number, message } = req.body;
    if (!number || !message) {
        return res.status(400).json({ success: false, error: 'Número e mensagem são obrigatórios' });
    }
    
    try {
        const jid = formatNumber(number);
        await sock.sendMessage(jid, { text: message });
        console.log(`✅ Mensagem enviada para ${number}`);
        res.json({ success: true, message: 'Mensagem enviada com sucesso' });
    } catch (error) {
        console.error('❌ Erro ao enviar:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Enviar mensagem em massa
app.post('/send-bulk', async (req, res) => {
    if (!isReady || !sock) {
        return res.status(400).json({ success: false, error: 'WhatsApp não está conectado' });
    }
    
    const { numbers, message, delay = 3000 } = req.body;
    if (!numbers || !Array.isArray(numbers) || !message) {
        return res.status(400).json({ success: false, error: 'Lista de números e mensagem são obrigatórios' });
    }
    
    const results = { success: [], failed: [] };
    console.log(`📤 Iniciando envio em massa para ${numbers.length} números...`);
    
    for (let i = 0; i < numbers.length; i++) {
        const number = numbers[i];
        try {
            const jid = formatNumber(number);
            await sock.sendMessage(jid, { text: message });
            results.success.push(number);
            console.log(`✅ [${i+1}/${numbers.length}] ${number}`);
        } catch (error) {
            results.failed.push({ number, error: error.message });
            console.error(`❌ [${i+1}/${numbers.length}] ${number}: ${error.message}`);
        }
        
        // Delay entre mensagens para evitar ban
        if (i < numbers.length - 1) {
            await new Promise(r => setTimeout(r, delay));
        }
    }
    
    console.log(`📊 Envio concluído: ${results.success.length} sucesso, ${results.failed.length} falha`);
    res.json({ success: true, results });
});

// Reiniciar serviço (reconecta sem perder sessão)
app.post('/restart', async (req, res) => {
    console.log('🔄 Reiniciando serviço WhatsApp...');
    try {
        if (sock) {
            sock.ev.removeAllListeners();
            // NÃO faz logout para preservar a sessão
            sock.ws.close();
            sock = null;
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        reconnectAttempts = 0;
        
        setTimeout(() => initializeClient(), 1000);
        
        res.json({ success: true, message: 'Reiniciando serviço...' });
    } catch (error) {
        console.error('Erro ao reiniciar:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Limpar sessão e gerar novo QR code
app.post('/clear-session', async (req, res) => {
    console.log('🧹 Limpando sessão por requisição manual...');
    try {
        if (sock) {
            sock.ev.removeAllListeners();
            sock.ws.close();
            sock = null;
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        reconnectAttempts = 0;
        qrCodeAttempts = 0;
        
        clearSession();
        
        setTimeout(() => initializeClient(), 2000);
        
        res.json({ success: true, message: 'Sessão limpa. Novo QR Code será gerado.' });
    } catch (error) {
        console.error('Erro ao limpar sessão:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// FORÇAR novo QR Code (limpeza agressiva - use se o QR normal não funcionar)
app.post('/force-new-qr', async (req, res) => {
    console.log('🔥 FORÇANDO nova sessão completa...');
    try {
        // 1. Parar tudo
        if (sock) {
            sock.ev.removeAllListeners();
            try { sock.ws.close(); } catch(e) {}
            try { await sock.end(); } catch(e) {}
            sock = null;
        }
        
        // 2. Reset de todos os estados
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        reconnectAttempts = 0;
        qrCodeAttempts = 0;
        
        // 3. Limpar TODOS os arquivos de sessão
        clearSession();
        
        // 4. Aguardar um pouco e reiniciar
        console.log('⏳ Aguardando 3 segundos para garantir limpeza...');
        setTimeout(() => {
            console.log('🚀 Iniciando nova conexão limpa...');
            initializeClient();
        }, 3000);
        
        res.json({ 
            success: true, 
            message: 'Sessão forçadamente limpa. Novo QR será gerado em 3 segundos.',
            action: 'Acesse /qr para ver o novo QR Code'
        });
    } catch (error) {
        console.error('Erro ao forçar nova sessão:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Logout (desconectar e limpar sessão)
app.post('/logout', async (req, res) => {
    console.log('🚪 Fazendo logout...');
    try {
        if (sock) {
            sock.ev.removeAllListeners();
            await sock.logout();
            sock = null;
        }
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        isInitializing = false;
        
        // Limpar arquivos de autenticação
        clearSession();
        
        // Reiniciar para gerar novo QR
        setTimeout(() => initializeClient(), 2000);
        
        res.json({ success: true, message: 'Logout realizado. Escaneie o QR Code novamente.' });
    } catch (error) {
        console.error('Erro no logout:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        whatsapp: isReady ? 'connected' : 'disconnected',
        uptime: process.uptime()
    });
});

// Graceful Shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Encerrando servidor (mantendo sessão)...');
    if (sock) {
        console.log('🔒 Fechando conexão do WhatsApp (sem logout)...');
        sock.ev.removeAllListeners();
        try { sock.ws.close(); } catch(e) {}
        sock = null;
    }
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n🛑 SIGTERM recebido (mantendo sessão)...');
    if (sock) {
        console.log('🔒 Fechando conexão do WhatsApp (sem logout)...');
        sock.ev.removeAllListeners();
        try { sock.ws.close(); } catch(e) {}
        sock = null;
    }
    process.exit(0);
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n🌐 Servidor WhatsApp (Baileys) rodando em http://0.0.0.0:${PORT}`);
    console.log(`📱 Acesse http://localhost:${PORT}/qr para escanear o QR Code`);
    
    // Inicializar WhatsApp uma única vez ao subir o servidor
    console.log('🚀 Iniciando WhatsApp...');
    initializeClient();
});
