
from app.database import get_db_connection
import psycopg2.extras

def check_lote():
    lote_id = 127
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM lotes_servico WHERE id = %s", (lote_id,))
            lote = cur.fetchone()
            print(f"Lote {lote_id}: {lote}")

if __name__ == "__main__":
    check_lote()
