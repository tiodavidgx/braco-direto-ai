"""
Utilitário para gerar links de upload internos.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from pathlib import Path

# Carregar .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://72.60.244.138")


def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "email"),
        user=os.getenv("DB_USER", "bracodireto"),
        password=os.getenv("DB_PASSWORD", "BracoDireto2025Prod!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )


def gerar_link_upload_interno(
    tipo: str,
    lote_id: Optional[int] = None,
    envio_montagem_id: Optional[int] = None,
    validade_dias: int = 30
) -> Dict[str, Any]:
    try:
        print(f"📝 Gerando link: tipo={tipo}, lote_id={lote_id}")
        
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            data_expiracao = datetime.now() + timedelta(days=validade_dias)
            
            cur.execute("SELECT gerar_hash_upload() as hash")
            hash_upload = cur.fetchone()["hash"]
            print(f"   Hash: {hash_upload}")
            
            cur.execute("""
                INSERT INTO uploads_nf (hash, tipo, lote_id, envio_montagem_id, data_expiracao, sistema)
                VALUES (%s, %s, %s, %s, %s, 'interno')
                RETURNING id, hash, data_expiracao
            """, (
                hash_upload, 
                tipo, 
                lote_id if tipo == "prestador" else None,
                envio_montagem_id if tipo == "montador" else None,
                data_expiracao
            ))
            
            registro = cur.fetchone()
            conn.commit()
            
            link = f"{FRONTEND_URL}/upload/nf/{registro['hash']}"
            print(f"   ✅ Link: {link}")
            
            return {
                "success": True,
                "id_controle": registro["id"],
                "hash": registro["hash"],
                "link": link,
                "validade_link": registro["data_expiracao"].strftime("%Y-%m-%d %H:%M:%S"),
                "status": 0,
                "sistema": "interno"
            }
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return {"success": False, "message": str(e)}


def verificar_link_interno(hash: str) -> Optional[Dict[str, Any]]:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, hash, tipo, lote_id, envio_montagem_id, 
                       status, data_criacao, data_expiracao, data_upload
                FROM uploads_nf WHERE hash = %s AND data_expiracao > NOW()
            """, (hash,))
            return cur.fetchone()
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None


def registrar_upload(hash: str, arquivo_nome: str, arquivo_path: str) -> bool:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE uploads_nf 
                SET status = 1, data_upload = NOW(), arquivo_nome = %s, arquivo_path = %s
                WHERE hash = %s
            """, (arquivo_nome, arquivo_path, hash))
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
