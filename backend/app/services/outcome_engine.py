import logging
from typing import Dict, Any, List
import psycopg
from app.config import settings
from app.utils import clean_uuid

logger = logging.getLogger(__name__)

def get_outcome_insights(user_id: str) -> List[Dict[str, Any]]:
    """
    Analyzes historical application outcome data to deliver actionable,
    data-driven insights back to the candidate.
    """
    uid = clean_uuid(user_id)
    insights = []
    
    try:
        with psycopg.connect(settings.DATABASE_URL, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                # Insight 1: Callback rate on Remote vs On-site
                cur.execute(
                    """
                    SELECT 
                        j.remote,
                        COUNT(*),
                        COUNT(CASE WHEN a.outcome = 'interview' OR a.outcome = 'offer' THEN 1 END) as callbacks
                    FROM applications a
                    JOIN jobs j ON a.job_id = j.id
                    WHERE a.user_id = %s
                    GROUP BY j.remote;
                    """,
                    (uid,)
                )
                rows = cur.fetchall()
                remote_callbacks = 0
                remote_total = 0
                onsite_callbacks = 0
                onsite_total = 0
                
                for remote_flag, total, callbacks in rows:
                    if remote_flag:
                        remote_total = total
                        remote_callbacks = callbacks
                    else:
                        onsite_total = total
                        onsite_callbacks = callbacks
                        
                if remote_total > 0 and onsite_total > 0:
                    remote_rate = remote_callbacks / remote_total
                    onsite_rate = onsite_callbacks / onsite_total
                    if remote_rate > onsite_rate:
                        factor = round(remote_rate / max(onsite_rate, 0.01), 1)
                        insights.append({
                            "category": "location_strategy",
                            "title": "Remote Advantage",
                            "text": f"Your applications for remote roles generated {factor}x more callbacks than on-site or hybrid roles ({remote_callbacks}/{remote_total} vs {onsite_callbacks}/{onsite_total})."
                        })
                    elif onsite_rate > remote_rate:
                        factor = round(onsite_rate / max(remote_rate, 0.01), 1)
                        insights.append({
                            "category": "location_strategy",
                            "title": "On-Site / Hybrid Advantage",
                            "text": f"Your applications for hybrid and on-site roles generated {factor}x more callbacks than remote applications ({onsite_callbacks}/{onsite_total} vs {remote_callbacks}/{remote_total})."
                        })
                
                # Insight 2: Performance based on outcome history
                cur.execute(
                    """
                    SELECT 
                        a.outcome,
                        COUNT(*),
                        array_agg(j.title)
                    FROM applications a
                    JOIN jobs j ON a.job_id = j.id
                    WHERE a.user_id = %s AND a.outcome IS NOT NULL
                    GROUP BY a.outcome;
                    """,
                    (uid,)
                )
                rows = cur.fetchall()
                total_outcomes = 0
                interviews = 0
                rejections = 0
                for outcome, cnt, titles in rows:
                    total_outcomes += cnt
                    if outcome in ['interview', 'offer']:
                        interviews += cnt
                    elif outcome == 'rejected':
                        rejections += cnt
                        
                if total_outcomes > 0:
                    callback_rate = round((interviews / total_outcomes) * 100, 1)
                    if interviews > 0:
                        insights.append({
                            "category": "resume_performance",
                            "title": "Application Conversion",
                            "text": f"Your callback rate is {callback_rate}% ({interviews} callbacks from {total_outcomes} applications with tracked outcomes)."
                        })
                    else:
                        insights.append({
                            "category": "resume_performance",
                            "title": "No Callbacks Yet",
                            "text": f"You have {total_outcomes} applications with tracked outcomes but no interview callbacks yet. Consider tailoring your resume more closely to each JD."
                        })
                        
    except Exception as e:
        logger.warning(f"Failed to generate outcome insights: {e}")
        
    if not insights:
        # Honest fallback when no data exists — no fabricated statistics
        insights = [
            {
                "category": "general",
                "title": "Build Momentum",
                "text": "Not enough application outcome data yet. Track your results by updating application statuses to see personalized insights here."
            }
        ]
        
    return insights
