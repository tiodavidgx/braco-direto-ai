import io, csv, time
import sys
sys.path.insert(0, "/var/www/braco-direto-ai/backend_example")
from app.database import get_db_connection
from app.routes.dados_bot import clean_value, parse_date, COLUMN_MAP_VENDAS, DB_COLUMNS, DATE_COLUMNS
from datetime import datetime

db_columns = DB_COLUMNS["vendas"]
date_cols = DATE_COLUMNS["vendas"]

files = ["/tmp/v3_p1.csv", "/tmp/v3_p2.csv", "/tmp/v3_p3.csv", "/tmp/v3_p4.csv"]
for fn in files:
    start = time.time()
    with open(fn, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        csv_to_db = {}
        for col in reader.fieldnames:
            n = col.strip().lower()
            n = n.lstrip("\ufeff")
            n = n.replace("ã","a").replace("á","a").replace("â","a").replace("é","e").replace("ê","e")
            n = n.replace("í","i").replace("ó","o").replace("ô","o").replace("ú","u").replace("ç","c")
            n = " ".join(n.split())
            if n in COLUMN_MAP_VENDAS:
                csv_to_db[col] = COLUMN_MAP_VENDAS[n]

        has_pedido = "identificador_pedido" in csv_to_db.values()
        print(f"{fn}: mapped {len(csv_to_db)} cols, has pedido: {has_pedido}", flush=True)

        basename = fn.split("/")[-1].replace(".csv","")
        lote = basename + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        buf = io.StringIO()
        count = 0
        for row in reader:
            pedido_col = [c for c,d in csv_to_db.items() if d=="identificador_pedido"]
            if pedido_col and not clean_value(row.get(pedido_col[0],"")):
                continue
            vals = []
            for dc in db_columns:
                if dc == "lote_importacao":
                    vals.append(lote)
                    continue
                cc = next((c for c,d in csv_to_db.items() if d==dc), None)
                if not cc:
                    vals.append("\\N")
                    continue
                raw = clean_value(row.get(cc,""))
                if raw is None:
                    vals.append("\\N")
                elif dc in date_cols:
                    p = parse_date(raw)
                    vals.append(str(p) if p else "\\N")
                else:
                    vals.append(raw.replace("\\","\\\\").replace("\t"," ").replace("\n"," ").replace("\r",""))
            buf.write("\t".join(vals) + "\n")
            count += 1

        buf.seek(0)
        cols_str = ", ".join(db_columns)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.copy_expert(f"COPY bot_vendas ({cols_str}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            conn.commit()
        dur = int((time.time()-start)*1000)
        print(f"{fn}: {count} inseridas em {dur}ms", flush=True)

print("DONE", flush=True)
Pre