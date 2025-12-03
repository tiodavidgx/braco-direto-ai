
from app.database import get_db_connection
import psycopg2.extras

def check_os():
    os_to_check = '66077'
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Check exact match
            cur.execute("SELECT * FROM os_enviadas WHERE os_numero = %s", (os_to_check,))
            exact = cur.fetchall()
            print(f"Exact match for '{os_to_check}': {exact}")

            # Check like match
            cur.execute("SELECT * FROM os_enviadas WHERE os_numero LIKE %s", (f"%{os_to_check}%",))
            like_match = cur.fetchall()
            print(f"Like match for '%{os_to_check}%': {like_match}")
            
            # Check all to see format
            cur.execute("SELECT os_numero FROM os_enviadas LIMIT 10")
            sample = cur.fetchall()
            print(f"Sample data: {sample}")

if __name__ == "__main__":
    check_os()
