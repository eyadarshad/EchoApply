import os
import psycopg
from app.config import settings

# Force development mode during test execution by clearing the JWT secret
os.environ["SUPABASE_JWT_SECRET"] = ""

# Automatically migrate the test database on conftest import
if settings.DATABASE_URL:
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations"))
            if os.path.exists(migrations_dir):
                migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
                for file_name in migration_files:
                    file_path = os.path.join(migrations_dir, file_name)
                    with open(file_path, "r", encoding="utf-8") as f:
                        sql = f.read()
                    try:
                        cur.execute(sql)
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        pass
        conn.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("WARNING: Test database migration failed. Test database is unreachable.")
