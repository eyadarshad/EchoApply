import os
import pytest
import psycopg
from app.config import settings

def get_db_connection():
    """Helper to connect to the database, returns None if unreachable."""
    if not settings.DATABASE_URL:
        return None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
        return conn
    except psycopg.OperationalError:
        return None

# Check database availability
db_conn_available = get_db_connection() is not None

@pytest.mark.skipif(not db_conn_available, reason="PostgreSQL database is not running or unreachable")
def test_database_migrations_and_constraints():
    """
    Applies migrations to the active database, verifies tables exist, and
    asserts that unique_user_job_hash constraint blocks duplicate applications.
    """
    # 1. Connect and initialize cursor
    conn = psycopg.connect(settings.DATABASE_URL)
    cursor = conn.cursor()

    try:
        # 2. Read migration file
        migration_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "supabase", "migrations", "20260628000000_init.sql"
        )
        with open(migration_path, "r", encoding="utf-8") as f:
            migration_sql = f.read()

        # 3. Apply migrations
        cursor.execute(migration_sql)
        conn.commit()

        # 4. Verify table existence
        tables_to_check = ["users", "profiles", "jobs", "applications", "tailored_resumes", "technique_library", "job_cache"]
        for table in tables_to_check:
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
                (table,)
            )
            exists = cursor.fetchone()[0]
            assert exists, f"Table {table} was not created by the migration."

        # 5. Insert test data
        user_id = "00000000-0000-0000-0000-000000000001"
        job_id = "00000000-0000-0000-0000-000000000002"
        job_hash = "test_job_hash_sha256_value"

        # Insert user (upsert if exists)
        cursor.execute(
            """
            INSERT INTO users (id, email, major, location)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
            """,
            (user_id, "test_user@example.com", "Computer Science", "Karachi")
        )

        # Insert job (upsert if exists)
        cursor.execute(
            """
            INSERT INTO jobs (id, source, title, company, jd_text, job_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (job_hash) DO UPDATE SET title = EXCLUDED.title;
            """,
            (job_id, "JSearch", "Software Engineer", "TechCorp", "Job details...", job_hash)
        )
        conn.commit()

        # Clear existing application matching this constraint for repeatability
        cursor.execute("DELETE FROM applications WHERE user_id = %s AND job_hash = %s;", (user_id, job_hash))
        conn.commit()

        # 6. Insert first application (should succeed)
        cursor.execute(
            """
            INSERT INTO applications (user_id, job_id, job_hash, status)
            VALUES (%s, %s, %s, %s);
            """,
            (user_id, job_id, job_hash, "pending")
        )
        conn.commit()

        # 7. Attempt duplicate insert (should fail with UniqueViolation)
        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            cursor.execute(
                """
                INSERT INTO applications (user_id, job_id, job_hash, status)
                VALUES (%s, %s, %s, %s);
                """,
                (user_id, job_id, job_hash, "applied")
            )
        
        # Rollback the aborted transaction caused by the unique violation
        conn.rollback()

        # Verify details of constraint block
        assert "unique_user_job_hash" in str(excinfo.value)

    finally:
        # Clean up test rows
        try:
            cursor.execute("DELETE FROM applications WHERE user_id = %s;", (user_id,))
            cursor.execute("DELETE FROM jobs WHERE id = %s;", (job_id,))
            cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            conn.commit()
        except Exception:
            conn.rollback()
        
        cursor.close()
        conn.close()
