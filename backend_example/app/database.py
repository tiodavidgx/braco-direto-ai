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
    'dbname': os.getenv('DB_NAME', 'email'),
    'user': os.getenv('DB_USER', 'david'),
    'password': os.getenv('DB_PASS', '')
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
    """Verifica se o banco de dados está acessível"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Verificar se as tabelas principais existem
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('prestadores', 'montadores', 'lotes_servico', 'envios_montagem')
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            if len(tables) >= 4:
                print(f"✅ Banco de dados conectado! Tabelas encontradas: {', '.join(tables)}")
            else:
                print(f"⚠️  Banco conectado mas apenas {len(tables)} tabelas encontradas.")
                print("   Execute run_migrations() no sistema_original/database.py se necessário.")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        raise

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
