import os
import sys
from datetime import datetime

from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    print("❌ Требуется пакет: pip install psycopg2-binary")
    sys.exit(1)


load_dotenv()


def build_dsn_from_env() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    host = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")
    port = os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or "5432"
    db = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB")
    user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER")
    pwd = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    sslmode = os.getenv("PGSSLMODE")

    missing = [k for k, v in {
        "PGHOST": host, "PGDATABASE": db, "PGUSER": user, "PGPASSWORD": pwd
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Нет переменных: {', '.join(missing)} (или задайте DATABASE_URL)")

    parts = [
        f"host={host}",
        f"port={port}",
        f"dbname={db}",
        f"user={user}",
        f"password={pwd}",
    ]
    if sslmode:
        parts.append(f"sslmode={sslmode}")
    return " ".join(parts)


def print_count(cur, table: str):
    try:
        cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
        row = cur.fetchone()
        print(f"{table}: {row['c']} строк")
    except Exception as e:
        print(f"{table}: ошибка запроса: {e}")


def print_sample(cur, table: str, columns: list[str], order_by: str | None = None, limit: int = 5):
    cols = ", ".join(columns)
    sql = f"SELECT {cols} FROM {table}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    sql += f" LIMIT {limit}"
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            print(f"— {table}: пусто")
            return
        print(f"— {table} (первые {len(rows)}):")
        for r in rows:
            print(dict(r))
    except Exception as e:
        print(f"— {table}: ошибка выборки: {e}")


def main():
    dsn = build_dsn_from_env()
    print("🔎 Проверяю данные в PostgreSQL...")
    with psycopg2.connect(dsn, cursor_factory=RealDictCursor) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            print("\nИтоги по количеству строк:")
            for t in ["users", "businesses", "business_snapshots", "conversation_sessions", "messages"]:
                print_count(cur, t)

            print("\nПримеры строк:")
            # У некоторых БД поле created_at в users могло отсутствовать — выбираем без него
            print_sample(cur, "users", ["user_id", "username", "first_name", "last_name"], order_by=None)
            print_sample(cur, "businesses", ["business_id", "user_id", "business_name", "business_type", "is_active", "created_at"], order_by="business_id ASC")
            print_sample(cur, "business_snapshots", [
                "snapshot_id", "business_id", "period_type", "period_date", "revenue", "expenses", "profit",
                "clients", "average_check", "profit_margin", "roi", "overall_health_score", "created_at"
            ], order_by="created_at DESC")


if __name__ == "__main__":
    main()


