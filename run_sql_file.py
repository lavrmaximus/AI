#!/usr/bin/env python3
import os
import sys
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from dotenv import load_dotenv

# Load env vars (DATABASE_URL or PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD)
load_dotenv()

def build_dsn_from_env() -> str:
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "postgres")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def read_sql_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        sql_text = f.read()
    # Naive split by ';' (safe enough for our simple migration scripts)
    statements = [stmt.strip() for stmt in sql_text.split(';')]
    # Remove empty
    return [s for s in statements if s]


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_sql_file.py <path_to_sql_file>")
        print("Examples:")
        print("  python run_sql_file.py add_sorting_index.sql")
        print("  python run_sql_file.py fix_column_order.sql")
        sys.exit(1)

    sql_path = sys.argv[1]
    if not os.path.isfile(sql_path):
        print(f"❌ File not found: {sql_path}")
        sys.exit(1)

    dsn = build_dsn_from_env()
    print("🔌 Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        conn.autocommit = True
        cur = conn.cursor()
        print("✅ Connected.")

        statements = read_sql_file(sql_path)
        print(f"📄 Executing {len(statements)} statements from {sql_path}...")
        for idx, stmt in enumerate(statements, 1):
            try:
                cur.execute(stmt)
                print(f"  ✅ [{idx}/{len(statements)}] OK")
            except Exception as e:
                print(f"  ❌ [{idx}/{len(statements)}] Error: {e}")
                conn.rollback()
                cur.close()
                conn.close()
                sys.exit(1)

        cur.close()
        conn.close()
        print("🎉 Done.")
    except Exception as e:
        print(f"❌ Connection/Execution error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
