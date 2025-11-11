"""
Gerenciamento de Banco de Dados
PostgreSQL com psycopg2
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'braco_direito'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS', 'postgres')
}

@contextmanager
def get_db_connection():
    """
    Context manager para conexão com banco de dados.
    
    Uso:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM prestadores")
            result = cur.fetchall()
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Inicializa as tabelas do banco de dados"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Criar tabela de prestadores
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prestadores (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                fornecedor_id TEXT UNIQUE,
                telefone TEXT,
                regra_envio TEXT,
                dias_envio TEXT,
                tempo_vencimento_dias INTEGER DEFAULT 10,
                emails_adicionais TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Criar tabela de montadores
        cur.execute("""
            CREATE TABLE IF NOT EXISTS montadores (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                identificador TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                telefone TEXT,
                percentual_comissao REAL NOT NULL,
                auxilio_semanal REAL NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                fornecedor_id TEXT UNIQUE,
                regra_envio TEXT,
                dias_envio TEXT,
                tempo_vencimento_dias INTEGER DEFAULT 10,
                emails_adicionais TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Criar tabela de lotes de serviço
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lotes_servico (
                id SERIAL PRIMARY KEY,
                prestador_id INTEGER REFERENCES prestadores(id),
                prestador_nome TEXT,
                periodo TEXT NOT NULL,
                valor_total REAL NOT NULL,
                data_envio TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'Em Aberto',
                conversation_id TEXT,
                anexo_path TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Criar tabela de OS enviadas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS os_enviadas (
                id SERIAL PRIMARY KEY,
                lote_id INTEGER REFERENCES lotes_servico(id) ON DELETE CASCADE,
                os_numero TEXT NOT NULL UNIQUE,
                detalhes JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        print("✅ Tabelas criadas/verificadas com sucesso")

def test_connection():
    """Testa a conexão com o banco de dados"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"✅ Conexão bem-sucedida! PostgreSQL: {version}")
            return True
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False

if __name__ == "__main__":
    # Testar conexão
    test_connection()
    # Inicializar banco
    init_db()
