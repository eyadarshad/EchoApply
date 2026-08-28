import os
import json
import logging
from typing import Optional, Dict, Any, List

import psycopg

from app.config import settings
from app.utils import clean_uuid
from app.services.embedding_service import cosine_similarity
from app.services.llm_client import llm_client_search as llm_client

logger = logging.getLogger(__name__)

LOCAL_KB_FILE = os.path.join(settings.DATA_DIR, "screening_kb.json")


def save_screening_answer(user_id: str, question: str, answer: str) -> bool:
    """Save a screening question and answer to the vector database or local fallback."""
    uid = clean_uuid(user_id)
    logger.info(f"Saving screening answer for user {uid}. Question: '{question}' -> '{answer}'")
    
    # 1. Generate semantic embedding
    embedding = llm_client.generate_embedding(question)
    
    # 2. Try DB first
    db_saved = False
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=1)
        with conn.cursor() as cur:
            # Check if this exact question is already in DB for this user
            cur.execute(
                "SELECT id FROM screening_kb WHERE user_id = %s AND LOWER(question_text) = LOWER(%s);",
                (uid, question)
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE screening_kb SET answer_text = %s, question_embedding = %s::vector WHERE id = %s;",
                    (answer, embedding, row[0])
                )
            else:
                cur.execute(
                    """
                    INSERT INTO screening_kb (user_id, question_text, answer_text, question_embedding)
                    VALUES (%s, %s, %s, %s::vector);
                    """,
                    (uid, question, answer, embedding)
                )
            conn.commit()
        conn.close()
        db_saved = True
        logger.info("Saved screening answer to database.")
    except Exception as e:
        logger.warning(f"Database save failed for screening KB, falling back: {e}")
        
    if not db_saved:
        # Local JSON file fallback
        kb_data = []
        if os.path.exists(LOCAL_KB_FILE):
            try:
                with open(LOCAL_KB_FILE, "r", encoding="utf-8") as f:
                    kb_data = json.load(f)
            except Exception:
                pass
                
        # Update if exists, else append
        updated = False
        for entry in kb_data:
            if entry.get("user_id") == uid and entry.get("question").lower() == question.lower():
                entry["answer"] = answer
                entry["embedding"] = embedding
                updated = True
                break
                
        if not updated:
            kb_data.append({
                "user_id": uid,
                "question": question,
                "answer": answer,
                "embedding": embedding
            })
            
        try:
            os.makedirs(os.path.dirname(LOCAL_KB_FILE), exist_ok=True)
            with open(LOCAL_KB_FILE, "w", encoding="utf-8") as f:
                json.dump(kb_data, f)
            logger.info("Saved screening answer to local JSON fallback.")
        except Exception as e:
            logger.error(f"Failed to write to local KB file: {e}")
            return False
            
    return True

def search_screening_answer(user_id: str, question: str, min_similarity: float = 0.82) -> Optional[str]:
    """Search for the most semantically similar question in the candidate memory."""
    uid = clean_uuid(user_id)
    logger.info(f"Querying screening KB memory for user {uid}. Question: '{question}'")
    
    # 1. Generate query embedding
    query_emb = llm_client.generate_embedding(question)
    
    # 2. Try DB first
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=1)
        with conn.cursor() as cur:
            # Vector cosine distance comparison
            cur.execute(
                """
                SELECT answer_text, 1 - (question_embedding <=> %s::vector) AS similarity
                FROM screening_kb
                WHERE user_id = %s
                ORDER BY similarity DESC
                LIMIT 1;
                """,
                (query_emb, uid)
            )
            row = cur.fetchone()
            if row:
                answer, similarity = row
                logger.info(f"DB vector match found. Similarity: {similarity:.4f}")
                if similarity >= min_similarity:
                    conn.close()
                    return answer
        conn.close()
    except Exception as e:
        logger.warning(f"Database query failed for screening KB, falling back: {e}")
        
    # 3. Local JSON file fallback
    if os.path.exists(LOCAL_KB_FILE):
        try:
            with open(LOCAL_KB_FILE, "r", encoding="utf-8") as f:
                kb_data = json.load(f)
                
            best_match = None
            best_similarity = -1.0
            
            for entry in kb_data:
                if entry.get("user_id") == uid and "embedding" in entry:
                    sim = cosine_similarity(query_emb, entry["embedding"])
                    if sim > best_similarity:
                        best_similarity = sim
                        best_match = entry.get("answer")
                        
            logger.info(f"Local JSON vector match found. Best similarity: {best_similarity:.4f}")
            if best_similarity >= min_similarity:
                return best_match
        except Exception as e:
            logger.error(f"Failed to read local KB file: {e}")
            
    return None
