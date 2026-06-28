import logging
import psycopg
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Static defaults for common domains/majors
DEFAULT_TECHNIQUES = {
    "computer science": [
        {
            "technique": "Anchor Line Technique",
            "applies_to_major": ["Computer Science", "Software Engineering", "Computer Engineering"],
            "reader_weight": 1.2,
            "description": "Place a highly focused one-line tagline directly under the name showing exact technical domain alignment."
        },
        {
            "technique": "Highlights Strip Technique",
            "applies_to_major": ["Computer Science", "Software Engineering"],
            "reader_weight": 1.5,
            "description": "Build a 'Golden Zone' skills highlights bar showcasing the top 4-5 relevant core skills aligned with the job spec."
        },
        {
            "technique": "Quantified Front-loading Technique",
            "applies_to_major": ["Computer Science", "Software Engineering"],
            "reader_weight": 1.3,
            "description": "Front-load achievements with bolded numerical metrics (digits act as visual anchors in human scan)."
        }
    ],
    "general": [
        {
            "technique": "Anchor Line Technique",
            "applies_to_major": ["General"],
            "reader_weight": 1.0,
            "description": "Add a tailored value proposition tagline below the name."
        },
        {
            "technique": "Highlights Strip Technique",
            "applies_to_major": ["General"],
            "reader_weight": 1.0,
            "description": "Create a highlights section targeting the core skills specified in the job description."
        },
        {
            "technique": "Quantified Front-loading Technique",
            "applies_to_major": ["General"],
            "reader_weight": 1.0,
            "description": "Structure experience bullet points to lead with action verbs and metrics."
        }
    ]
}

def get_db_connection():
    """Helper to connect to database. Returns None if unreachable."""
    if not settings.DATABASE_URL:
        return None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
        return conn
    except Exception:
        return None

def select_techniques(major: str) -> List[Dict[str, Any]]:
    """
    Selects resume optimization techniques for the candidate's major.
    First tries to query the Supabase database, and falls back to local static
    rules if database is offline or lacks matches.
    """
    normalized_major = (major or "").strip().lower()
    logger.info(f"Selecting techniques for major: '{major}'")

    # 1. Try database connection
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Search using pg_trgm-like checking or simple array contains
                cursor.execute(
                    """
                    SELECT technique, applies_to_major, reader_weight, source_url
                    FROM technique_library
                    WHERE %s = ANY(applies_to_major) OR %s ILIKE ANY(applies_to_major);
                    """,
                    (major, f"%{major}%")
                )
                rows = cursor.fetchall()
                if rows:
                    techniques = []
                    for row in rows:
                        techniques.append({
                            "technique": row[0],
                            "applies_to_major": row[1],
                            "reader_weight": float(row[2]) if row[2] is not None else 1.0,
                            "source_url": row[3]
                        })
                    logger.info(f"Retrieved {len(techniques)} techniques from database.")
                    return techniques
        except Exception as e:
            logger.warning(f"Database query for techniques failed: {str(e)}. Falling back to local rules.")
        finally:
            conn.close()
    else:
        logger.info("Database is unreachable. Using local fallback rules.")

    # 2. Fallback to static rules
    # Try exact match, then substring matches, then default to general
    for key, techniques in DEFAULT_TECHNIQUES.items():
        if key in normalized_major:
            logger.info(f"Matched fallback domain: '{key}'")
            return techniques

    logger.info("No matching major found. Using general fallback techniques.")
    return DEFAULT_TECHNIQUES["general"]
