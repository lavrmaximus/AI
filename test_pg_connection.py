import os
import sys

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    print("❌ Требуется пакет: pip install psycopg2-binary")
    sys.exit(1)


def build_dsn_from_env() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    host = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")
    port = os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or "5432"
    db = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB")
    user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER")
    pwd = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    sslmode = os.getenv("PGSSLMODE")  # например, 'require' для Railway

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


def main():
    try:
        dsn = build_dsn_from_env()
        print("🔌 Подключение к PostgreSQL...")
        with psycopg2.connect(dsn, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version() AS version")
                row = cur.fetchone()
                print("✅ Успешно! Версия:")
                print(row["version"])
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()


