import sqlite3, sys

src = r"db_files/metrics.db"
dump = r"db_files/metrics_recovered.sql"
try:
    con = sqlite3.connect(src)
    with open(dump, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(f"{line}\n")
    con.close()
    print("Wrote:", dump)
except Exception as e:
    print("iterdump failed:", e)
    sys.exit(1)
