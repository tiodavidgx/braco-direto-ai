
import psycopg2
from app.database import get_db_connection

def check_table_schema():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    tc.constraint_name, 
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.table_name = 'os_enviadas';
            """)
            constraints = cur.fetchall()
            print("Constraints on os_enviadas:")
            for c in constraints:
                print(c)

            cur.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'os_enviadas';
            """)
            indexes = cur.fetchall()
            print("\nIndexes on os_enviadas:")
            for i in indexes:
                print(i)

if __name__ == "__main__":
    check_table_schema()
