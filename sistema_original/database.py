import os
import psycopg2
import psycopg2.extras
import datetime
from dotenv import load_dotenv
import json
from pathlib import Path

# Garantir que o .env seja carregado do diretório correto
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

def get_db_connection():
    # Debug: verificar variáveis de ambiente
    db_config = {
        'host': os.getenv("DB_HOST"),
        'dbname': os.getenv("DB_NAME"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASS"),
        'port': os.getenv("DB_PORT")
    }
    
    # Se alguma variável não estiver definida, usar valores padrão
    if not db_config['host']:
        db_config['host'] = 'localhost'
    if not db_config['port']:
        db_config['port'] = '5432'
    
    conn = psycopg2.connect(**db_config)
    return conn

def run_migrations():
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Garante que as tabelas base existam
        cur.execute('''CREATE TABLE IF NOT EXISTS prestadores (id SERIAL PRIMARY KEY, nome TEXT NOT NULL UNIQUE, email TEXT NOT NULL, fornecedor_id TEXT UNIQUE, regra_envio TEXT, dias_envio TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS montadores (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, identificador TEXT NOT NULL UNIQUE, email TEXT NOT NULL, percentual_comissao REAL NOT NULL, auxilio_semanal REAL NOT NULL, ativo BOOLEAN NOT NULL DEFAULT TRUE, fornecedor_id TEXT UNIQUE, regra_envio TEXT, dias_envio TEXT)''')
        
        # Criar tabelas principais ANTES de tentar adicionar colunas
        cur.execute('''CREATE TABLE IF NOT EXISTS lotes_servico (id SERIAL PRIMARY KEY, prestador_id INTEGER REFERENCES prestadores(id), prestador_nome TEXT, periodo TEXT NOT NULL, valor_total REAL NOT NULL, data_envio TIMESTAMP NOT NULL, status TEXT NOT NULL DEFAULT 'Em Aberto', conversation_id TEXT, anexo_path TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS os_enviadas (id SERIAL PRIMARY KEY, lote_id INTEGER REFERENCES lotes_servico(id) ON DELETE CASCADE, os_numero TEXT NOT NULL UNIQUE, detalhes JSONB)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS envios_montagem (id SERIAL PRIMARY KEY, montador_id INTEGER REFERENCES montadores(id), data_envio TIMESTAMP NOT NULL, status TEXT NOT NULL DEFAULT 'Em Aberto', detalhes JSONB, conversation_id TEXT, anexo_path TEXT)''')
        
        # Agora podemos adicionar colunas adicionais se não existirem
        cur.execute("ALTER TABLE prestadores ADD COLUMN IF NOT EXISTS emails_adicionais TEXT;")
        cur.execute("ALTER TABLE montadores ADD COLUMN IF NOT EXISTS emails_adicionais TEXT;")
        
        # **NOVO: Campos para controle de vencimento de pagamentos**
        cur.execute("ALTER TABLE prestadores ADD COLUMN IF NOT EXISTS tempo_vencimento_dias INTEGER DEFAULT 10;")  # Prazo em dias úteis para pagamento
        cur.execute("ALTER TABLE montadores ADD COLUMN IF NOT EXISTS tempo_vencimento_dias INTEGER DEFAULT 10;")  # Prazo em dias úteis para pagamento
        
        # Campos de controle de vencimento nas tabelas de lotes/envios
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_recebimento_nf TIMESTAMP;")  # Quando a NF foi recebida
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_vencimento_pagamento DATE;")  # Data de vencimento calculada
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS pago BOOLEAN DEFAULT FALSE;")  # Se já foi pago
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_pagamento TIMESTAMP;")  # Quando foi marcado como pago
        
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_recebimento_nf TIMESTAMP;")  # Quando a NF foi recebida
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_vencimento_pagamento DATE;")  # Data de vencimento calculada
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS pago BOOLEAN DEFAULT FALSE;")  # Se já foi pago
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_pagamento TIMESTAMP;")  # Quando foi marcado como pago
        
        # Adicionar colunas para sistema de upload de notas fiscais (API DV Processamento)
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS id_controle INTEGER;")  # ID retornado pela API
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS link_upload TEXT;")  # Link de upload recebido da API
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS validade_link DATE;")  # Data de validade do link
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS status_api INTEGER DEFAULT 0;")  # 0=pendente, 1=NF recebida
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS data_envio_api TIMESTAMP;")  # Quando foi enviado para API
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS nota_fiscal_path TEXT;")  # Caminho do arquivo recebido
        cur.execute("ALTER TABLE lotes_servico ADD COLUMN IF NOT EXISTS api_message TEXT;")  # Mensagem retornada pela API
        
        # Adicionar mesmas colunas para envios_montagem (sistema de API para montadores)
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS id_controle INTEGER;")  # ID retornado pela API
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS link_upload TEXT;")  # Link de upload recebido da API
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS validade_link DATE;")  # Data de validade do link
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS status_api INTEGER DEFAULT 0;")  # 0=pendente, 1=NF recebida
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_envio_api TIMESTAMP;")  # Quando foi enviado para API
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS nota_fiscal_path TEXT;")  # Caminho do arquivo recebido
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS api_message TEXT;")  # Mensagem retornada pela API
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS upload_hash TEXT;")  # Hash único para consulta
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS status_arquivo INTEGER DEFAULT 0;")  # 0=Aguardando, 1=Recebido, 2=Baixado
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS data_ultima_consulta TIMESTAMP;")  # Última consulta à API
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS quantidade_os INTEGER;")  # Quantidade de OSs no envio
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS montador_nome TEXT;")  # Nome do montador (cache)
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS periodo TEXT;")  # Período formatado para API (MM/YYYY)
        cur.execute("ALTER TABLE envios_montagem ADD COLUMN IF NOT EXISTS valor_total NUMERIC(10, 2);")  # Valor total do envio
        
        # Criar índices
        cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_montagem ON envios_montagem ((detalhes->>'periodo_relatorio'), montador_id);''')
        cur.execute('''CREATE INDEX IF NOT EXISTS idx_envios_montagem_upload_hash ON envios_montagem(upload_hash);''')
        cur.execute('''CREATE INDEX IF NOT EXISTS idx_envios_montagem_status_api ON envios_montagem(status_api);''')
        
        # Tabela de envios ignorados
        cur.execute('''CREATE TABLE IF NOT EXISTS envios_ignorados (id SERIAL PRIMARY KEY, tipo TEXT NOT NULL, entidade_id INTEGER NOT NULL, ano INTEGER NOT NULL, periodo_chave TEXT NOT NULL, data_ignorada TIMESTAMP NOT NULL)''')
        cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_ignore ON envios_ignorados (tipo, entidade_id, ano, periodo_chave);''')
        
        # Nova tabela para blacklist de boletins (montadores)
        cur.execute('''CREATE TABLE IF NOT EXISTS boletins_blacklist (
            id SERIAL PRIMARY KEY,
            montador_id INTEGER REFERENCES montadores(id) ON DELETE CASCADE,
            boletim TEXT NOT NULL,
            data_adicao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            motivo TEXT
        )''')
        cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_boletim_blacklist ON boletins_blacklist (montador_id, boletim);''')
        
        # Nova tabela para blacklist de OS (prestadores)
        cur.execute('''CREATE TABLE IF NOT EXISTS os_blacklist (
            id SERIAL PRIMARY KEY,
            prestador_id INTEGER REFERENCES prestadores(id) ON DELETE CASCADE,
            os_numero TEXT NOT NULL,
            data_adicao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            motivo TEXT
        )''')
        cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_os_blacklist ON os_blacklist (prestador_id, os_numero);''')

        # **NOVO: Tabela para notificações WhatsApp**
        cur.execute('''CREATE TABLE IF NOT EXISTS notificacoes_whatsapp (
            id SERIAL PRIMARY KEY,
            prestador_id INTEGER REFERENCES prestadores(id),
            montador_id INTEGER REFERENCES montadores(id),
            tipo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'enviado',
            data_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            erro TEXT,
            metadata JSONB
        )''')
        cur.execute('''CREATE INDEX IF NOT EXISTS idx_notificacoes_prestador ON notificacoes_whatsapp(prestador_id);''')
        cur.execute('''CREATE INDEX IF NOT EXISTS idx_notificacoes_montador ON notificacoes_whatsapp(montador_id);''')
        cur.execute('''CREATE INDEX IF NOT EXISTS idx_notificacoes_data ON notificacoes_whatsapp(data_envio);''')
        
        # **NOVO: Tabelas para automação WhatsApp**
        cur.execute('''CREATE TABLE IF NOT EXISTS templates_whatsapp (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            template TEXT NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            variaveis TEXT,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS automacao_whatsapp (
            id SERIAL PRIMARY KEY,
            evento TEXT NOT NULL UNIQUE,
            template_id TEXT,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            condicoes TEXT,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Adicionar campo telefone nas tabelas
        cur.execute("ALTER TABLE prestadores ADD COLUMN IF NOT EXISTS telefone TEXT;")
        cur.execute("ALTER TABLE montadores ADD COLUMN IF NOT EXISTS telefone TEXT;")

    conn.commit()
    conn.close()

# --- Funções de Prestadores ---
def add_prestador(nome, email, fornecedor_id, regra_envio, dias_envio, emails_adicionais=None, tempo_vencimento_dias=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur: 
            cur.execute('INSERT INTO prestadores (nome, email, fornecedor_id, regra_envio, dias_envio, emails_adicionais, tempo_vencimento_dias) VALUES (%s, %s, %s, %s, %s, %s, %s)', 
                       (nome, email, fornecedor_id, regra_envio, dias_envio, emails_adicionais, tempo_vencimento_dias))
        conn.commit()
        return True, "Prestador adicionado!"
    except psycopg2.IntegrityError: return False, f"Erro: Fornecedor ID ou Nome já existe."
    finally: conn.close()

def update_prestador(prestador_id, regra_envio, dias_envio, emails_adicionais=None, tempo_vencimento_dias=None):
    conn = get_db_connection()
    with conn.cursor() as cur:
        if tempo_vencimento_dias is not None:
            cur.execute('UPDATE prestadores SET regra_envio = %s, dias_envio = %s, emails_adicionais = %s, tempo_vencimento_dias = %s WHERE id = %s', 
                       (regra_envio, dias_envio, emails_adicionais, tempo_vencimento_dias, prestador_id))
        elif emails_adicionais is not None:
            cur.execute('UPDATE prestadores SET regra_envio = %s, dias_envio = %s, emails_adicionais = %s WHERE id = %s', 
                       (regra_envio, dias_envio, emails_adicionais, prestador_id))
        else:
            cur.execute('UPDATE prestadores SET regra_envio = %s, dias_envio = %s WHERE id = %s', (regra_envio, dias_envio, prestador_id))
    conn.commit()
    conn.close()

def get_all_prestadores():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM prestadores ORDER BY nome ASC')
        prestadores = cur.fetchall()
    conn.close()
    return prestadores

def get_prestador_by_name(name):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM prestadores WHERE nome = %s', (name,))
        prestador = cur.fetchone()
    conn.close()
    return prestador

def get_montador_by_name(name):
    """Busca montador pelo nome"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM montadores WHERE nome = %s', (name,))
        montador = cur.fetchone()
    conn.close()
    return montador

def delete_prestador(prestador_id):
    conn = get_db_connection()
    with conn.cursor() as cur: cur.execute('DELETE FROM prestadores WHERE id = %s', (prestador_id,))
    conn.commit()
    conn.close()

def get_prestador_emails(prestador_info):
    """Retorna lista de todos os emails do prestador (principal + adicionais)"""
    emails = [prestador_info['email']]  # Email principal
    
    # Adicionar emails adicionais se existirem
    if prestador_info.get('emails_adicionais'):
        emails_extras = [email.strip() for email in prestador_info['emails_adicionais'].split(',') if email.strip()]
        emails.extend(emails_extras)
    
    return emails

def get_montador_emails(montador_info):
    """Retorna lista de todos os emails do montador (principal + adicionais)"""
    emails = [montador_info['email']]  # Email principal
    
    # Adicionar emails adicionais se existirem
    if montador_info.get('emails_adicionais'):
        emails_extras = [email.strip() for email in montador_info['emails_adicionais'].split(',') if email.strip()]
        emails.extend(emails_extras)
    
    return emails

# --- Funções de Lote de Serviço ---
def criar_lote_servico(prestador_id, prestador_nome, periodo, valor_total, items_raw):
    conn = get_db_connection()
    now = datetime.datetime.now()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO lotes_servico (prestador_id, prestador_nome, periodo, valor_total, data_envio) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (prestador_id, prestador_nome, periodo, valor_total, now)
        )
        lote_id = cur.fetchone()[0]
        
        for item in items_raw:
            cur.execute(
                "INSERT INTO os_enviadas (lote_id, os_numero, detalhes) VALUES (%s, %s, %s)",
                (lote_id, item.get('o_s'), psycopg2.extras.Json(item))
            )
    conn.commit()
    conn.close()
    return lote_id

def atualizar_lote_com_conversation_id(lote_id, conversation_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('UPDATE lotes_servico SET conversation_id = %s WHERE id = %s', (conversation_id, lote_id))
    conn.commit()
    conn.close()

def get_all_lotes_servico():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM lotes_servico ORDER BY data_envio DESC')
        lotes = cur.fetchall()
    conn.close()
    return lotes

def get_os_by_lote_id(lote_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM os_enviadas WHERE lote_id = %s', (lote_id,))
        os_list = cur.fetchall()
    conn.close()
    return os_list

def check_os_list(os_numbers):
    if not os_numbers: return []
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT os_numero FROM os_enviadas WHERE os_numero = ANY(%s)', (os_numbers,))
        sent_os = [row['os_numero'] for row in cur.fetchall()]
    conn.close()
    return sent_os

def update_lote_servico_status(lote_id, status):
    conn = get_db_connection()
    with conn.cursor() as cur: cur.execute('UPDATE lotes_servico SET status = %s WHERE id = %s', (status, lote_id))
    conn.commit()
    conn.close()

def update_lote_servico_attachment(lote_id, anexo_path):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('UPDATE lotes_servico SET anexo_path = %s, status = %s WHERE id = %s', (anexo_path, 'N.F. RECEBIDA', lote_id))
    conn.commit()
    conn.close()

def delete_lote_servico(lote_id):
    """Deleta um lote e todos os registros relacionados"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Deletar notificações relacionadas primeiro
            cur.execute('DELETE FROM notificacoes WHERE lote_id = %s', (lote_id,))
            
            # Deletar cards do Trello relacionados
            cur.execute('DELETE FROM trello_cards WHERE lote_id = %s', (lote_id,))
            
            # Deletar o lote (os_enviadas já tem ON DELETE CASCADE)
            cur.execute('DELETE FROM lotes_servico WHERE id = %s', (lote_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_lote_servico_by_conversation_id(conversation_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM lotes_servico WHERE conversation_id = %s', (conversation_id,))
        lote = cur.fetchone()
    conn.close()
    return lote

# --- Funções de Upload de Notas Fiscais (API DV Processamento) ---
def salvar_resposta_api(lote_id, id_controle, link, validade_link, status_api, message, upload_hash=None):
    """Salva a resposta da API após envio do lote"""
    conn = get_db_connection()
    now = datetime.datetime.now()
    with conn.cursor() as cur:
        cur.execute(
            '''UPDATE lotes_servico 
               SET id_controle = %s, link_upload = %s, validade_link = %s, 
                   status_api = %s, data_envio_api = %s, api_message = %s, upload_hash = %s 
               WHERE id = %s''',
            (id_controle, link, validade_link, status_api, now, message, upload_hash, lote_id)
        )
    conn.commit()
    conn.close()

def get_lotes_para_enviar_api():
    """Retorna lotes que ainda não foram enviados para a API"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """SELECT * FROM lotes_servico 
               WHERE id_controle IS NULL 
               AND status != 'N.F. RECEBIDA'
               ORDER BY data_envio DESC"""
        )
        lotes = cur.fetchall()
    conn.close()
    return lotes

def atualizar_status_api(lote_id, status_api):
    """Atualiza o status da API (0=pendente, 1=NF recebida)"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('UPDATE lotes_servico SET status_api = %s WHERE id = %s', (status_api, lote_id))
        if status_api == 1:
            cur.execute('UPDATE lotes_servico SET status = %s WHERE id = %s', ('N.F. RECEBIDA', lote_id))
    conn.commit()
    conn.close()

def salvar_nota_fiscal(lote_id, file_path):
    """Salva o caminho da nota fiscal recebida"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE lotes_servico SET nota_fiscal_path = %s, status_api = %s, status = %s WHERE id = %s',
            (file_path, 1, 'N.F. RECEBIDA', lote_id)
        )
    conn.commit()
    conn.close()
    
    # 📱 Enviar WhatsApp notificando que a NF foi recebida
    try:
        print(f"\n🟢 [NF Recebida] Iniciando envio WhatsApp para lote {lote_id}")
        from whatsapp_triggers import WhatsAppAutomation
        wa = WhatsAppAutomation()
        
        # Buscar info do lote para notificar
        lote = get_lote_by_id(lote_id)
        print(f"🟢 [NF Recebida] Lote encontrado: {lote}")
        
        if lote:
            # Extrair número da NF do nome do arquivo (se possível)
            import os
            numero_nf = os.path.basename(file_path).replace('.pdf', '').replace('.PDF', '')
            print(f"🟢 [NF Recebida] Número NF: {numero_nf}")
            
            print(f"🟢 [NF Recebida] Chamando enviar_prestador_nf_recebida...")
            resultado = wa.enviar_prestador_nf_recebida(
                lote['prestador_id'],
                lote['periodo'],
                lote['valor_total'],  # ✅ Corrigido: usar valor_total
                numero_nf,
                lote_id=lote_id  # ✅ Passar lote_id para registrar no metadata
            )
            print(f"🟢 [NF Recebida] Resultado: {resultado}")
        else:
            print(f"🔴 [NF Recebida] Lote não encontrado!")
    except Exception as e:
        import traceback
        print(f"🔴 [NF Recebida] ERRO: {str(e)}")
        print(f"🔴 [NF Recebida] Traceback: {traceback.format_exc()}")

def get_lotes_com_link_pendente():
    """Retorna lotes que têm link gerado mas ainda não receberam NF"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """SELECT * FROM lotes_servico 
               WHERE link_upload IS NOT NULL 
               AND status_api = 0
               AND validade_link >= CURRENT_DATE
               ORDER BY data_envio DESC"""
        )
        lotes = cur.fetchall()
    conn.close()
    return lotes

def get_lotes_upload_pendente():
    """Retorna lotes que têm upload_hash e estão aguardando download do arquivo"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """SELECT * FROM lotes_servico 
               WHERE upload_hash IS NOT NULL 
               AND (status_arquivo IS NULL OR status_arquivo != 2)
               AND validade_link >= CURRENT_DATE
               ORDER BY data_envio DESC"""
        )
        lotes = cur.fetchall()
    conn.close()
    return lotes

def get_lote_by_id_controle(id_controle):
    """Retorna lote pelo ID de controle da API"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM lotes_servico WHERE id_controle = %s', (id_controle,))
        lote = cur.fetchone()
    conn.close()
    return lote

def get_lote_by_id(lote_id):
    """Retorna lote pelo ID local"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM lotes_servico WHERE id = %s', (lote_id,))
        lote = cur.fetchone()
    conn.close()
    return lote

def verificar_lote_duplicado(lote_id, periodo):
    """Verifica se já existe envio para API deste lote e período"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            'SELECT COUNT(*) FROM lotes_servico WHERE id = %s AND periodo = %s AND id_controle IS NOT NULL',
            (lote_id, periodo)
        )
        count = cur.fetchone()[0]
    conn.close()
    return count > 0

def salvar_arquivos_nf(lote_id, arquivos_dados, estatisticas=None):
    """Salva dados dos arquivos recebidos da nota fiscal"""
    conn = get_db_connection()
    now = datetime.datetime.now()
    
    # Preparar dados completos
    dados_completos = {
        'arquivos': arquivos_dados,
        'estatisticas': estatisticas or {},
        'data_consulta': now.isoformat()
    }
    
    with conn.cursor() as cur:
        cur.execute(
            '''UPDATE lotes_servico 
               SET arquivos_nf = %s, 
                   data_ultima_consulta = %s,
                   status_arquivo = 1
               WHERE id = %s''',
            (json.dumps(dados_completos), now, lote_id)
        )
    conn.commit()
    conn.close()

def get_arquivos_nf(lote_id):
    """Retorna dados dos arquivos de uma nota fiscal"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            'SELECT arquivos_nf, data_ultima_consulta, status_arquivo FROM lotes_servico WHERE id = %s',
            (lote_id,)
        )
        result = cur.fetchone()
    conn.close()
    return result

def atualizar_status_arquivo(lote_id, status):
    """Atualiza status do arquivo (0=Aguardando, 1=Recebido, 2=Baixado)"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE lotes_servico SET status_arquivo = %s WHERE id = %s',
            (status, lote_id)
        )
    conn.commit()
    conn.close()

def get_lotes_com_arquivos():
    """Retorna lotes que já receberam arquivos"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            '''SELECT * FROM lotes_servico 
               WHERE status_arquivo >= 1
               ORDER BY data_ultima_consulta DESC'''
        )
        lotes = cur.fetchall()
    conn.close()
    return lotes

# --- Funções de Notificações ---
def criar_notificacao(tipo, titulo, mensagem, lote_id=None, icone='🔔', prioridade=0):
    """Cria uma nova notificação"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            '''INSERT INTO notificacoes (tipo, titulo, mensagem, lote_id, icone, prioridade)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id''',
            (tipo, titulo, mensagem, lote_id, icone, prioridade)
        )
        notif_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return notif_id

def get_notificacoes_nao_lidas():
    """Retorna todas as notificações não lidas"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            '''SELECT n.*, l.prestador_nome 
               FROM notificacoes n
               LEFT JOIN lotes_servico l ON n.lote_id = l.id
               WHERE n.lida = FALSE
               ORDER BY n.prioridade DESC, n.data_criacao DESC'''
        )
        notifs = cur.fetchall()
    conn.close()
    return notifs

def get_todas_notificacoes(limite=50):
    """Retorna todas as notificações (com limite)"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            '''SELECT n.*, l.prestador_nome 
               FROM notificacoes n
               LEFT JOIN lotes_servico l ON n.lote_id = l.id
               ORDER BY n.data_criacao DESC
               LIMIT %s''',
            (limite,)
        )
        notifs = cur.fetchall()
    conn.close()
    return notifs

def marcar_notificacao_lida(notif_id):
    """Marca uma notificação como lida"""
    conn = get_db_connection()
    now = datetime.datetime.now()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE notificacoes SET lida = TRUE, data_leitura = %s WHERE id = %s',
            (now, notif_id)
        )
    conn.commit()
    conn.close()

def marcar_todas_notificacoes_lidas():
    """Marca todas as notificações como lidas"""
    conn = get_db_connection()
    now = datetime.datetime.now()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE notificacoes SET lida = TRUE, data_leitura = %s WHERE lida = FALSE',
            (now,)
        )
    conn.commit()
    conn.close()

def contar_notificacoes_nao_lidas():
    """Conta quantas notificações não lidas existem"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM notificacoes WHERE lida = FALSE')
        count = cur.fetchone()[0]
    conn.close()
    return count

def deletar_notificacao(notif_id):
    """Deleta uma notificação"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('DELETE FROM notificacoes WHERE id = %s', (notif_id,))
    conn.commit()
    conn.close()

# --- Funções de Jobs Automáticos ---
def get_jobs_config():
    """Retorna configuração de todos os jobs"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM jobs_config ORDER BY nome')
        jobs = cur.fetchall()
    conn.close()
    return jobs

def get_job_config(nome):
    """Retorna configuração de um job específico"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM jobs_config WHERE nome = %s', (nome,))
        job = cur.fetchone()
    conn.close()
    return job

def atualizar_job_config(nome, ativo=None, intervalo_minutos=None):
    """Atualiza configuração de um job"""
    conn = get_db_connection()
    now = datetime.datetime.now()
    
    updates = ['data_atualizacao = %s']
    params = [now]
    
    if ativo is not None:
        updates.append('ativo = %s')
        params.append(ativo)
    
    if intervalo_minutos is not None:
        updates.append('intervalo_minutos = %s')
        params.append(intervalo_minutos)
    
    params.append(nome)
    
    with conn.cursor() as cur:
        cur.execute(
            f'UPDATE jobs_config SET {", ".join(updates)} WHERE nome = %s',
            params
        )
    conn.commit()
    conn.close()

def registrar_execucao_job(nome, sucesso=True, mensagem=''):
    """Registra execução de um job"""
    conn = get_db_connection()
    now = datetime.datetime.now()
    
    with conn.cursor() as cur:
        if sucesso:
            cur.execute(
                '''UPDATE jobs_config 
                   SET ultima_execucao = %s,
                       total_execucoes = total_execucoes + 1,
                       ultima_mensagem = %s,
                       data_atualizacao = %s
                   WHERE nome = %s''',
                (now, mensagem, now, nome)
            )
        else:
            cur.execute(
                '''UPDATE jobs_config 
                   SET ultima_execucao = %s,
                       total_execucoes = total_execucoes + 1,
                       total_erros = total_erros + 1,
                       ultima_mensagem = %s,
                       data_atualizacao = %s
                   WHERE nome = %s''',
                (now, mensagem, now, nome)
            )
    conn.commit()
    conn.close()

def atualizar_proxima_execucao_job(nome, proxima_execucao):
    """Atualiza próxima execução de um job"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE jobs_config SET proxima_execucao = %s WHERE nome = %s',
            (proxima_execucao, nome)
        )
    conn.commit()
    conn.close()

# --- Funções de Montadores ---
def add_montador(nome, identificador, email, percentual_comissao, auxilio_semanal, fornecedor_id, regra_envio, dias_envio, emails_adicionais=None, tempo_vencimento_dias=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur: 
            cur.execute('INSERT INTO montadores (nome, identificador, email, percentual_comissao, auxilio_semanal, fornecedor_id, regra_envio, dias_envio, emails_adicionais, tempo_vencimento_dias) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                       (nome, identificador, email, percentual_comissao, auxilio_semanal, fornecedor_id, regra_envio, dias_envio, emails_adicionais, tempo_vencimento_dias))
        conn.commit()
        return True, "Montador adicionado!"
    except psycopg2.IntegrityError: return False, f"Erro: Identificador ou Fornecedor ID já existem."
    finally: conn.close()

def update_montador(montador_id, email, percentual_comissao, auxilio_semanal, ativo, regra_envio, dias_envio, fornecedor_id=None, emails_adicionais=None, tempo_vencimento_dias=None):
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Construir query dinamicamente baseado nos parâmetros fornecidos
        campos = "email = %s, percentual_comissao = %s, auxilio_semanal = %s, ativo = %s, regra_envio = %s, dias_envio = %s"
        valores = [email, percentual_comissao, auxilio_semanal, ativo, regra_envio, dias_envio]
        
        if fornecedor_id is not None:
            campos += ", fornecedor_id = %s"
            valores.append(fornecedor_id)
        if emails_adicionais is not None:
            campos += ", emails_adicionais = %s"
            valores.append(emails_adicionais)
        if tempo_vencimento_dias is not None:
            campos += ", tempo_vencimento_dias = %s"
            valores.append(tempo_vencimento_dias)
        
        valores.append(montador_id)
        cur.execute(f'UPDATE montadores SET {campos} WHERE id = %s', tuple(valores))
    conn.commit()
    conn.close()

def get_all_montadores(apenas_ativos=False):
    conn = get_db_connection()
    query = 'SELECT * FROM montadores ORDER BY nome ASC'
    if apenas_ativos:
        query = 'SELECT * FROM montadores WHERE ativo = TRUE ORDER BY nome ASC'
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query)
        montadores = cur.fetchall()
    conn.close()
    return montadores

def get_montador_by_id(montador_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM montadores WHERE id = %s', (montador_id,))
        montador = cur.fetchone()
    conn.close()
    return montador

def get_montador_by_identificador(identificador):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM montadores WHERE identificador = %s', (identificador,))
        montador = cur.fetchone()
    conn.close()
    return montador

def log_sent_montagem(montador_id, group_details, conversation_id):
    conn = get_db_connection()
    now = datetime.datetime.now()
    
    # Extrair dados do group_details para colunas cache
    montador_nome = group_details.get('nome_montador')
    quantidade_os = len(group_details.get('items', []))
    valor_total = group_details.get('total_geral', 0)
    periodo_relatorio = group_details.get('periodo_relatorio', '')
    
    # Extrair período no formato MM/YYYY
    periodo = None
    if periodo_relatorio:
        # Formato: "15/10/2025 - 15/10/2025"
        primeira_data = periodo_relatorio.split(' - ')[0].strip()
        # Converter DD/MM/YYYY para MM/YYYY
        if '/' in primeira_data:
            partes = primeira_data.split('/')
            if len(partes) == 3:
                periodo = f"{partes[1]}/{partes[2]}"
    
    # Inserir registro no banco
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO envios_montagem 
               (montador_id, data_envio, detalhes, conversation_id, montador_nome, quantidade_os, valor_total, periodo) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (montador_id, now, psycopg2.extras.Json(group_details), conversation_id, 
             montador_nome, quantidade_os, valor_total, periodo)
        )
        envio_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    
    # 🚀 ENVIAR PARA API IMEDIATAMENTE após criar o registro
    try:
        from api_upload_client import APIUploadClient
        
        print(f"🚀 Enviando envio #{envio_id} para API automaticamente...")
        client = APIUploadClient()
        sucesso, mensagem, dados = client.enviar_e_salvar(envio_id, tipo='montagem')
        
        if sucesso:
            print(f"   ✅ Link gerado: {dados.get('link', 'N/A')[:50]}...")
        else:
            print(f"   ⚠️  Erro ao gerar link: {mensagem}")
            # Não falha o envio do email se a API falhar
    except Exception as e:
        print(f"   ⚠️  Exceção ao chamar API: {e}")
        import traceback
        traceback.print_exc()
        # Não falha o envio do email se a API falhar
    
    return envio_id

def get_envio_montagem_by_conversation_id(conversation_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM envios_montagem WHERE conversation_id = %s', (conversation_id,))
        envio = cur.fetchone()
    conn.close()
    return envio

def update_montagem_attachment(envio_id, anexo_path):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('UPDATE envios_montagem SET anexo_path = %s, status = %s WHERE id = %s', (anexo_path, 'N.F. RECEBIDA', envio_id))
    conn.commit()
    conn.close()

def get_all_sent_montagens():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT e.*, m.nome as montador_nome FROM envios_montagem e LEFT JOIN montadores m ON e.montador_id = m.id ORDER BY data_envio DESC')
        history = cur.fetchall()
    conn.close()
    return history

def get_montagens_by_montador_id(montador_id):
    """Retorna histórico de montagens por montador específico"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT e.*, m.nome as montador_nome FROM envios_montagem e LEFT JOIN montadores m ON e.montador_id = m.id WHERE e.montador_id = %s ORDER BY data_envio DESC', (montador_id,))
        history = cur.fetchall()
    conn.close()
    return history

def update_montagem_status(envio_id, status):
    conn = get_db_connection()
    with conn.cursor() as cur: cur.execute('UPDATE envios_montagem SET status = %s WHERE id = %s', (status, envio_id))
    conn.commit()
    conn.close()

def update_montagem_details(envio_id, details):
    conn = get_db_connection()
    with conn.cursor() as cur: cur.execute('UPDATE envios_montagem SET detalhes = %s WHERE id = %s', (json.dumps(details), envio_id))
    conn.commit()
    conn.close()

def delete_envio_montagem(envio_id):
    """Deleta um envio de montagem e todos os registros relacionados"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Deletar notificações relacionadas primeiro
            cur.execute('DELETE FROM notificacoes WHERE lote_id = %s AND tipo LIKE %s', (envio_id, '%montagem%'))
            
            # Deletar cards do Trello relacionados (se existirem)
            cur.execute('DELETE FROM trello_cards WHERE lote_id = %s', (envio_id,))
            
            # Deletar o envio
            cur.execute('DELETE FROM envios_montagem WHERE id = %s', (envio_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- Funções API para Montadores ---

def get_envios_montagem_sem_api():
    """Retorna envios de montagem que ainda não foram enviados para API"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """SELECT * FROM envios_montagem 
               WHERE id_controle IS NULL 
               AND status != 'N.F. RECEBIDA'
               ORDER BY data_envio DESC"""
        )
        envios = cur.fetchall()
    conn.close()
    return envios

def get_envios_montagem_upload_pendente():
    """Retorna envios de montagem que têm upload_hash e estão aguardando download do arquivo"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """SELECT * FROM envios_montagem 
               WHERE upload_hash IS NOT NULL 
               AND (status_arquivo IS NULL OR status_arquivo != 2)
               AND validade_link >= CURRENT_DATE
               ORDER BY data_envio DESC"""
        )
        envios = cur.fetchall()
    conn.close()
    return envios

def atualizar_status_api_montagem(envio_id, id_controle=None, link=None, validade_link=None, status_api=0, upload_hash=None):
    """
    Atualiza informações da API para envio de montagem
    
    Args:
        envio_id: ID do envio
        id_controle: ID retornado pela API
        link: Link de upload gerado
        validade_link: Data de validade do link
        status_api: Status (0=pendente, 1=recebido)
        upload_hash: Hash para consulta
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            UPDATE envios_montagem 
            SET id_controle = %s,
                link_upload = %s,
                validade_link = %s,
                status_api = %s,
                upload_hash = %s,
                data_envio_api = NOW()
            WHERE id = %s
        ''', (id_controle, link, validade_link, status_api, upload_hash, envio_id))
        
        if status_api == 1:
            cur.execute('UPDATE envios_montagem SET status = %s WHERE id = %s', ('N.F RECEBIDA', envio_id))
    conn.commit()
    conn.close()

def atualizar_status_arquivo_montagem(envio_id, status):
    """Atualiza status do arquivo de montagem (0=Aguardando, 1=Recebido, 2=Baixado)"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE envios_montagem SET status_arquivo = %s WHERE id = %s',
            (status, envio_id)
        )
    conn.commit()
    conn.close()

def salvar_nota_fiscal_montagem(envio_id, file_path):
    """Salva o caminho da nota fiscal recebida de montagem"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE envios_montagem SET nota_fiscal_path = %s, status_api = %s, status = %s WHERE id = %s',
            (file_path, 1, 'N.F RECEBIDA', envio_id)
        )
    conn.commit()
    conn.close()
    
    # 📱 Enviar WhatsApp notificando que a NF foi recebida
    try:
        from whatsapp_triggers import WhatsAppAutomation
        wa = WhatsAppAutomation()
        
        # Buscar info do envio para notificar
        envio = get_envio_montagem_by_id(envio_id)
        if envio:
            # Extrair número da NF do nome do arquivo (se possível)
            import os
            numero_nf = os.path.basename(file_path).replace('.pdf', '').replace('.PDF', '')
            
            wa.enviar_montador_nf_recebida(
                envio['montador_id'],
                envio['relatorio_data'].get('periodo_relatorio', ''),
                envio['relatorio_data'].get('total_geral', 0),
                numero_nf
            )
    except Exception as e:
        print(f"⚠️ Erro ao enviar WhatsApp de NF recebida: {str(e)}")

def get_envio_montagem_by_id(envio_id):
    """Retorna envio de montagem pelo ID"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM envios_montagem WHERE id = %s', (envio_id,))
        envio = cur.fetchone()
    conn.close()
    return envio

def get_envio_montagem_by_id_controle(id_controle):
    """Retorna envio de montagem pelo ID de controle da API"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute('SELECT * FROM envios_montagem WHERE id_controle = %s', (id_controle,))
        envio = cur.fetchone()
    conn.close()
    return envio

def check_boletim_list(boletim_ids):
    if not boletim_ids: return []
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT DISTINCT elem ->> 'boletim' as sent_boletim FROM envios_montagem, jsonb_array_elements(detalhes -> 'items') elem WHERE elem ->> 'boletim' = ANY(%s)", (boletim_ids,))
        sent_boletins = [row['sent_boletim'] for row in cur.fetchall()]
    conn.close()
    return sent_boletins

def atualizar_dados_cache_montagem():
    """
    Atualiza campos cache (montador_nome, quantidade_os, periodo, valor_total) 
    a partir do JSONB detalhes para todos os envios de montagem
    """
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Buscar todos os envios
        cur.execute("SELECT id, detalhes FROM envios_montagem WHERE detalhes IS NOT NULL")
        envios = cur.fetchall()
        
        atualizados = 0
        for envio in envios:
            envio_id = envio['id']
            detalhes = envio['detalhes']
            
            if isinstance(detalhes, str):
                import json
                detalhes = json.loads(detalhes)
            
            # Extrair dados
            montador_nome = detalhes.get('nome_montador')
            quantidade_os = len(detalhes.get('items', []))
            total_geral = detalhes.get('total_geral', 0)
            periodo_relatorio = detalhes.get('periodo_relatorio', '')
            
            # Extrair período no formato MM/YYYY da primeira data
            periodo = None
            if periodo_relatorio:
                # Formato: "15/10/2025 - 15/10/2025"
                primeira_data = periodo_relatorio.split(' - ')[0].strip()
                # Converter DD/MM/YYYY para MM/YYYY
                if '/' in primeira_data:
                    partes = primeira_data.split('/')
                    if len(partes) == 3:
                        periodo = f"{partes[1]}/{partes[2]}"
            
            # Atualizar envio
            cur.execute("""
                UPDATE envios_montagem 
                SET montador_nome = %s,
                    quantidade_os = %s,
                    valor_total = %s,
                    periodo = %s
                WHERE id = %s
            """, (montador_nome, quantidade_os, total_geral, periodo, envio_id))
            
            atualizados += 1
        
        conn.commit()
    conn.close()
    
    return atualizados

def get_envios_na_semana(tipo, entidade_id, ano, semana):
    conn = get_db_connection()
    table = "lotes_servico" if tipo == 'prestador' else "envios_montagem"
    id_col = "prestador_id" if tipo == 'prestador' else "montador_id"
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {id_col} = %s AND EXTRACT(YEAR FROM data_envio) = %s AND EXTRACT(WEEK FROM data_envio) = %s", (entidade_id, ano, semana))
        count = cur.fetchone()[0]
    conn.close()
    return count > 0

def foi_ignorado_na_semana(tipo, entidade_id, ano, semana):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM envios_ignorados WHERE tipo = %s AND entidade_id = %s AND ano = %s AND periodo_chave = %s", (tipo, entidade_id, ano, f"semana_{semana}"))
        count = cur.fetchone()[0]
    conn.close()
    return count > 0

def ignorar_envio_semanal(tipo, entidade_id, ano, semana):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO envios_ignorados (tipo, entidade_id, ano, periodo_chave, data_ignorada) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (tipo, entidade_id, ano, periodo_chave) DO NOTHING", (tipo, entidade_id, ano, f"semana_{semana}", datetime.datetime.now()))
    conn.commit()
    conn.close()

# --- Funções de Blacklist de Boletins ---
def adicionar_boletim_blacklist(montador_id, boletim, motivo=None):
    """Adiciona um boletim à blacklist de um montador"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO boletins_blacklist (montador_id, boletim, motivo) VALUES (%s, %s, %s)",
                (montador_id, boletim, motivo)
            )
        conn.commit()
        return True, "Boletim adicionado à blacklist!"
    except psycopg2.IntegrityError:
        return False, "Este boletim já está na blacklist"
    finally:
        conn.close()

def remover_boletim_blacklist(montador_id, boletim):
    """Remove um boletim da blacklist de um montador"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM boletins_blacklist WHERE montador_id = %s AND boletim = %s",
            (montador_id, boletim)
        )
    conn.commit()
    conn.close()

def get_boletins_blacklist(montador_id=None):
    """Retorna todos os boletins na blacklist, filtrados por montador se especificado"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        if montador_id:
            cur.execute('''
                SELECT b.*, m.nome as montador_nome 
                FROM boletins_blacklist b 
                JOIN montadores m ON b.montador_id = m.id 
                WHERE b.montador_id = %s 
                ORDER BY b.data_adicao DESC
            ''', (montador_id,))
        else:
            cur.execute('''
                SELECT b.*, m.nome as montador_nome 
                FROM boletins_blacklist b 
                JOIN montadores m ON b.montador_id = m.id 
                ORDER BY b.data_adicao DESC
            ''')
        return cur.fetchall()

def check_boletins_blacklist(boletim_ids):
    """Verifica quais boletins estão na blacklist"""
    if not boletim_ids:
        return []
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT boletim FROM boletins_blacklist WHERE boletim = ANY(%s)",
            (boletim_ids,)
        )
        blacklisted = [row[0] for row in cur.fetchall()]
    conn.close()
    return blacklisted

# --- Funções de Blacklist de OS (Prestadores) ---
def adicionar_os_blacklist(prestador_id, os_numero, motivo=None):
    """Adiciona uma OS à blacklist de um prestador"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO os_blacklist (prestador_id, os_numero, motivo) VALUES (%s, %s, %s)",
                (prestador_id, os_numero, motivo)
            )
        conn.commit()
        return True, "OS adicionada à blacklist!"
    except psycopg2.IntegrityError:
        return False, "Esta OS já está na blacklist"
    finally:
        conn.close()

def remover_os_blacklist(prestador_id, os_numero):
    """Remove uma OS da blacklist de um prestador"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM os_blacklist WHERE prestador_id = %s AND os_numero = %s",
            (prestador_id, os_numero)
        )
    conn.commit()
    conn.close()

def get_os_blacklist(prestador_id=None):
    """Retorna todas as OS na blacklist, filtradas por prestador se especificado"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        if prestador_id:
            cur.execute('''
                SELECT o.*, p.nome as prestador_nome 
                FROM os_blacklist o 
                JOIN prestadores p ON o.prestador_id = p.id 
                WHERE o.prestador_id = %s 
                ORDER BY o.data_adicao DESC
            ''', (prestador_id,))
        else:
            cur.execute('''
                SELECT o.*, p.nome as prestador_nome 
                FROM os_blacklist o 
                JOIN prestadores p ON o.prestador_id = p.id 
                ORDER BY o.data_adicao DESC
            ''')
        return cur.fetchall()


# --- Funções de Controle de Vencimento de Pagamentos ---

def calcular_dias_uteis(data_inicial, dias_uteis):
    """
    Calcula a data após X dias úteis (não conta sábados e domingos)
    
    Args:
        data_inicial: Data inicial (datetime.date ou datetime.datetime)
        dias_uteis: Número de dias úteis a adicionar
    
    Returns:
        datetime.date: Data final após adicionar os dias úteis
    """
    from datetime import timedelta
    
    # Converter para date se for datetime
    if isinstance(data_inicial, datetime.datetime):
        data_inicial = data_inicial.date()
    
    data_atual = data_inicial
    dias_adicionados = 0
    
    while dias_adicionados < dias_uteis:
        data_atual += timedelta(days=1)
        # Verificar se não é final de semana (Monday=0, Sunday=6)
        if data_atual.weekday() < 5:  # Segunda a sexta
            dias_adicionados += 1
    
    return data_atual


def calcular_data_vencimento(data_recebimento, dias_uteis):
    """
    Calcula a data de vencimento baseada na data de recebimento da NF
    
    Args:
        data_recebimento: Data que a NF foi recebida
        dias_uteis: Prazo em dias úteis configurado
    
    Returns:
        datetime.date: Data de vencimento do pagamento
    """
    return calcular_dias_uteis(data_recebimento, dias_uteis)


def atualizar_vencimento_lote(lote_id, data_recebimento_nf):
    """
    Atualiza a data de recebimento da NF e calcula o vencimento para um lote de serviço
    
    Args:
        lote_id: ID do lote
        data_recebimento_nf: Data que a NF foi recebida
    """
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Buscar o prestador do lote para pegar o tempo de vencimento
        cur.execute('''
            SELECT l.*, p.tempo_vencimento_dias 
            FROM lotes_servico l
            JOIN prestadores p ON l.prestador_id = p.id
            WHERE l.id = %s
        ''', (lote_id,))
        lote = cur.fetchone()
        
        if lote:
            tempo_vencimento = lote['tempo_vencimento_dias'] or 10
            data_vencimento = calcular_data_vencimento(data_recebimento_nf, tempo_vencimento)
            
            cur.execute('''
                UPDATE lotes_servico 
                SET data_recebimento_nf = %s, data_vencimento_pagamento = %s
                WHERE id = %s
            ''', (data_recebimento_nf, data_vencimento, lote_id))
    
    conn.commit()
    conn.close()


def atualizar_vencimento_montagem(envio_id, data_recebimento_nf):
    """
    Atualiza a data de recebimento da NF e calcula o vencimento para um envio de montagem
    
    Args:
        envio_id: ID do envio
        data_recebimento_nf: Data que a NF foi recebida
    """
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Buscar o montador do envio para pegar o tempo de vencimento
        cur.execute('''
            SELECT e.*, m.tempo_vencimento_dias 
            FROM envios_montagem e
            JOIN montadores m ON e.montador_id = m.id
            WHERE e.id = %s
        ''', (envio_id,))
        envio = cur.fetchone()
        
        if envio:
            tempo_vencimento = envio['tempo_vencimento_dias'] or 10
            data_vencimento = calcular_data_vencimento(data_recebimento_nf, tempo_vencimento)
            
            cur.execute('''
                UPDATE envios_montagem 
                SET data_recebimento_nf = %s, data_vencimento_pagamento = %s
                WHERE id = %s
            ''', (data_recebimento_nf, data_vencimento, envio_id))
    
    conn.commit()
    conn.close()


def marcar_lote_como_pago(lote_id):
    """Marca um lote de serviço como pago"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            UPDATE lotes_servico 
            SET status = 'PAGO', data_pagamento = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (lote_id,))
    conn.commit()
    conn.close()


def marcar_montagem_como_paga(envio_id):
    """Marca um envio de montagem como pago"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            UPDATE envios_montagem 
            SET status = 'PAGO', data_pagamento = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (envio_id,))
    conn.commit()
    conn.close()


def marcar_todos_nao_pendentes_como_pagos():
    """
    Marca como PAGO todos os lotes/montagens que têm NF recebida mas ainda não estão marcados como pagos.
    Isso é útil para marcar como pago em lote todos que já foram processados mas não foram marcados.
    
    Returns:
        dict: quantidade de lotes e montagens marcados
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Marcar lotes de serviço que têm NF recebida mas não estão pagos
        cur.execute('''
            UPDATE lotes_servico 
            SET status = 'PAGO', data_pagamento = CURRENT_TIMESTAMP
            WHERE status != 'PAGO' 
            AND data_recebimento_nf IS NOT NULL
        ''')
        lotes_marcados = cur.rowcount
        
        # Marcar montagens que têm NF recebida mas não estão pagas
        cur.execute('''
            UPDATE envios_montagem 
            SET status = 'PAGO', data_pagamento = CURRENT_TIMESTAMP
            WHERE status != 'PAGO' 
            AND data_recebimento_nf IS NOT NULL
        ''')
        montagens_marcadas = cur.rowcount
    
    conn.commit()
    conn.close()
    
    return {
        'lotes': lotes_marcados,
        'montagens': montagens_marcadas,
        'total': lotes_marcados + montagens_marcadas
    }


def desmarcar_todos_como_pagos():
    """
    ROLLBACK: Desmarca TODOS os pagamentos, voltando status para 'N.F. RECEBIDA' 
    onde havia data_recebimento_nf, ou 'Em Aberto' caso contrário.
    
    Returns:
        dict: quantidade de lotes e montagens desmarcados
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Desmarcar lotes de serviço pagos
        cur.execute('''
            UPDATE lotes_servico 
            SET status = CASE 
                WHEN data_recebimento_nf IS NOT NULL THEN 'N.F. RECEBIDA'
                ELSE 'Em Aberto'
            END,
            data_pagamento = NULL
            WHERE status = 'PAGO'
        ''')
        lotes_desmarcados = cur.rowcount
        
        # Desmarcar montagens pagas
        cur.execute('''
            UPDATE envios_montagem 
            SET status = CASE 
                WHEN data_recebimento_nf IS NOT NULL THEN 'N.F. RECEBIDA'
                ELSE 'Em Aberto'
            END,
            data_pagamento = NULL
            WHERE status = 'PAGO'
        ''')
        montagens_desmarcadas = cur.rowcount
    
    conn.commit()
    conn.close()
    
    return {
        'lotes': lotes_desmarcados,
        'montagens': montagens_desmarcadas,
        'total': lotes_desmarcados + montagens_desmarcadas
    }


def get_pagamentos_vencidos():
    """
    Retorna todos os pagamentos vencidos (lotes e montagens) que ainda não foram pagos
    
    Returns:
        dict com duas listas: 'servicos' e 'montagens'
    """
    conn = get_db_connection()
    resultado = {'servicos': [], 'montagens': []}
    
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Buscar lotes de serviço vencidos
        cur.execute('''
            SELECT 
                l.*,
                p.nome as prestador_nome,
                p.tempo_vencimento_dias,
                CURRENT_DATE - l.data_vencimento_pagamento as dias_vencidos
            FROM lotes_servico l
            JOIN prestadores p ON l.prestador_id = p.id
            WHERE l.pago = FALSE
              AND l.data_vencimento_pagamento IS NOT NULL
              AND l.data_vencimento_pagamento < CURRENT_DATE
            ORDER BY l.data_vencimento_pagamento ASC
        ''')
        resultado['servicos'] = cur.fetchall()
        
        # Buscar envios de montagem vencidos
        cur.execute('''
            SELECT 
                e.*,
                m.nome as montador_nome,
                m.tempo_vencimento_dias,
                CURRENT_DATE - e.data_vencimento_pagamento as dias_vencidos
            FROM envios_montagem e
            JOIN montadores m ON e.montador_id = m.id
            WHERE e.pago = FALSE
              AND e.data_vencimento_pagamento IS NOT NULL
              AND e.data_vencimento_pagamento < CURRENT_DATE
            ORDER BY e.data_vencimento_pagamento ASC
        ''')
        resultado['montagens'] = cur.fetchall()
    
    conn.close()
    return resultado


def get_pagamentos_proximos_vencimento(dias=3):
    """
    Retorna pagamentos que vencem nos próximos X dias
    
    Args:
        dias: Número de dias para considerar como "próximo"
    
    Returns:
        dict com duas listas: 'servicos' e 'montagens'
    """
    conn = get_db_connection()
    resultado = {'servicos': [], 'montagens': []}
    
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Buscar lotes de serviço próximos do vencimento
        cur.execute('''
            SELECT 
                l.*,
                p.nome as prestador_nome,
                p.tempo_vencimento_dias,
                l.data_vencimento_pagamento - CURRENT_DATE as dias_restantes
            FROM lotes_servico l
            JOIN prestadores p ON l.prestador_id = p.id
            WHERE l.pago = FALSE
              AND l.data_vencimento_pagamento IS NOT NULL
              AND l.data_vencimento_pagamento BETWEEN CURRENT_DATE AND CURRENT_DATE + %s
            ORDER BY l.data_vencimento_pagamento ASC
        ''', (dias,))
        resultado['servicos'] = cur.fetchall()
        
        # Buscar envios de montagem próximos do vencimento
        cur.execute('''
            SELECT 
                e.*,
                m.nome as montador_nome,
                m.tempo_vencimento_dias,
                e.data_vencimento_pagamento - CURRENT_DATE as dias_restantes
            FROM envios_montagem e
            JOIN montadores m ON e.montador_id = m.id
            WHERE e.pago = FALSE
              AND e.data_vencimento_pagamento IS NOT NULL
              AND e.data_vencimento_pagamento BETWEEN CURRENT_DATE AND CURRENT_DATE + %s
            ORDER BY e.data_vencimento_pagamento ASC
        ''', (dias,))
        resultado['montagens'] = cur.fetchall()
    
    conn.close()
    return resultado


def get_todos_pagamentos_pendentes():
    """
    Retorna TODOS os pagamentos pendentes (vencidos, hoje, amanhã, futuros)
    organizados com informação de dias até/desde o vencimento
    
    Returns:
        dict com duas listas: 'servicos' e 'montagens'
        Cada item tem 'dias_para_vencimento' (negativo se vencido, 0 se hoje, positivo se futuro)
    """
    conn = get_db_connection()
    resultado = {'servicos': [], 'montagens': []}
    
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Buscar todos os lotes de serviço não pagos com vencimento definido
        cur.execute('''
            SELECT 
                l.*,
                p.nome as prestador_nome,
                p.fornecedor_id as prestador_fornecedor_id,
                p.tempo_vencimento_dias,
                l.data_vencimento_pagamento - CURRENT_DATE as dias_para_vencimento
            FROM lotes_servico l
            JOIN prestadores p ON l.prestador_id = p.id
            WHERE l.status != 'PAGO'
              AND l.data_vencimento_pagamento IS NOT NULL
            ORDER BY l.data_vencimento_pagamento ASC
        ''')
        resultado['servicos'] = cur.fetchall()
        
        # Buscar todos os envios de montagem não pagos com vencimento definido
        cur.execute('''
            SELECT 
                e.*,
                m.nome as montador_nome,
                m.fornecedor_id as montador_fornecedor_id,
                m.tempo_vencimento_dias,
                e.data_vencimento_pagamento - CURRENT_DATE as dias_para_vencimento
            FROM envios_montagem e
            JOIN montadores m ON e.montador_id = m.id
            WHERE e.status != 'PAGO'
              AND e.data_vencimento_pagamento IS NOT NULL
            ORDER BY e.data_vencimento_pagamento ASC
        ''')
        resultado['montagens'] = cur.fetchall()
    
    conn.close()
    return resultado


def check_os_blacklist(os_numbers):
    """Verifica quais OS estão na blacklist"""
    if not os_numbers:
        return []
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT os_numero FROM os_blacklist WHERE os_numero = ANY(%s)",
            (os_numbers,)
        )
        blacklisted = [row[0] for row in cur.fetchall()]
    conn.close()
    return blacklisted

run_migrations()