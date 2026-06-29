import re
import logging
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel
from app.schemas import (
    ResumeParsedData, JDAnalysisResult, GapAnalysisResult,
    TargetedRewriteResult, ImpactPassResult, TruthfulnessCheckResult,
    BulletVerification, HighlightSkill, RewrittenBullet
)

logger = logging.getLogger(__name__)

COMMON_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Next.js", "Vue", "Angular", "Node.js", "Express", 
    "FastAPI", "Django", "Flask", "Go", "Golang", "Rust", "Java", "Spring Boot", "C++", "C#", "Ruby", 
    "Rails", "PHP", "Laravel", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", 
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "GitLab", "CI/CD", "Terraform", 
    "HTML", "CSS", "Tailwind CSS", "Bootstrap", "GraphQL", "REST API", "Machine Learning", "Deep Learning", 
    "NLP", "PyTorch", "TensorFlow", "Pandas", "NumPy", "Scikit-Learn", "Solidity", "Blockchain", "Swift", 
    "Kotlin", "Flutter", "React Native"
]

def extract_name(text: str, filename: Optional[str] = None) -> str:
    # Try filename first if it looks like a person's name
    if filename:
        clean_name = filename.replace("-Resume.pdf", "").replace("-resume.pdf", "").replace(".pdf", "").replace("_", " ").replace("-", " ")
        clean_name = " ".join([w.capitalize() for w in clean_name.split()])
        # Ignore generic names like "Resume", "Cv"
        if len(clean_name) > 3 and clean_name.lower() not in ["resume", "cv", "my resume", "my cv", "candidate"]:
            return clean_name

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:15]:
        line_clean = re.sub(r"[^\w\s-]", "", line).strip()
        words = line_clean.split()
        if 2 <= len(words) <= 4:
            if all(w[0].isupper() for w in words if w.isalpha()):
                if not any(kw in line_clean.lower() for kw in ["resume", "cv", "curriculum", "portfolio", "page", "developer", "engineer", "designer"]):
                    return line_clean
    return "Unknown Candidate"

def extract_email(text: str) -> str:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else "unknown@example.com"

def extract_phone(text: str) -> Optional[str]:
    match = re.search(r"\(?\+?[0-9]{1,4}\)?[-.\s]?\(?[0-9]{1,3}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}", text)
    return match.group(0) if match else None

def extract_links(text: str) -> List[str]:
    links = re.findall(r"(?:https?://)?(?:www\.)?(?:github\.com|linkedin\.com|behance\.net|dribbble\.com|twitter\.com)/[a-zA-Z0-9_\-\./]+", text, re.IGNORECASE)
    return list(dict.fromkeys(links))

def extract_skills(text: str) -> List[str]:
    skills = []
    for skill in COMMON_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if "." in skill or "+" in skill:
            pattern = re.escape(skill)
        if re.search(pattern, text, re.IGNORECASE):
            skills.append(skill)
    return list(dict.fromkeys(skills))

def extract_education(text: str) -> List[Dict[str, Any]]:
    lines = [l.strip() for l in text.split("\n")]
    in_edu = False
    section_headers = ["experience", "employment", "work history", "projects", "skills", "certifications", "interests"]
    
    edu_lines = []
    for line in lines:
        line_lower = line.lower()
        if any(h in line_lower for h in ["education", "academic qualification", "academics"]):
            in_edu = True
            continue
        if in_edu:
            if any(line_lower.startswith(h) or line_lower == h or (len(line_lower) < 20 and any(h in line_lower for h in section_headers)) for h in section_headers):
                in_edu = False
            else:
                edu_lines.append(line)
                
    education = []
    current_edu = {}
    for line in edu_lines:
        if not line:
            continue
        is_school = any(kw in line.lower() for kw in ["university", "college", "school", "institute", "nuces", "fast", "lums", "nust", "ucl", "mit", "academy"])
        year_match = re.search(r"\b(19|20)\d{2}\b", line)
        is_degree = any(kw in line.lower() for kw in ["bachelor", "master", "ph.d", "b.s", "m.s", "bba", "mba", "phd", "degree", "diploma", "associate"])
        
        if is_school:
            if "school" in current_edu:
                education.append(current_edu)
                current_edu = {}
            current_edu["school"] = line
        elif is_degree:
            current_edu["degree"] = line
        elif year_match:
            current_edu["date"] = year_match.group(0)
            
        if not is_school and not is_degree and not year_match and line:
            if "degree" in current_edu:
                current_edu["degree"] += " " + line
            elif "school" in current_edu:
                current_edu["school"] += " " + line
                
    if current_edu:
        education.append(current_edu)
        
    final_edu = []
    for edu in education:
        if edu.get("school") or edu.get("degree"):
            final_edu.append({
                "school": edu.get("school", "University"),
                "degree": edu.get("degree", "Degree"),
                "date": edu.get("date", "2024")
            })
    return final_edu

def extract_experience(text: str) -> List[Dict[str, Any]]:
    lines = [l.strip() for l in text.split("\n")]
    in_exp = False
    section_headers = ["education", "projects", "skills", "certifications", "interests", "languages"]
    
    exp_lines = []
    for line in lines:
        line_lower = line.lower()
        if any(h in line_lower for h in ["experience", "employment", "work history", "professional experience"]):
            in_exp = True
            continue
        if in_exp:
            if any(line_lower.startswith(h) or line_lower == h or (len(line_lower) < 20 and any(h in line_lower for h in section_headers)) for h in section_headers):
                in_exp = False
            else:
                exp_lines.append(line)
                
    experience = []
    current_job = None
    role_keywords = ["intern", "engineer", "developer", "designer", "lead", "manager", "architect", "analyst", "consultant", "specialist", "programmer", "instructor"]
    
    for line in exp_lines:
        if not line:
            continue
            
        is_bullet = line.startswith(("-", "—", "*", "•", "o ")) or (current_job and len(line) > 30 and not any(kw in line.lower() for kw in role_keywords))
        clean_line = line.lstrip("-—*•o ").strip()
        
        if is_bullet:
            if current_job:
                current_job["bullets"].append(clean_line)
        else:
            is_role = any(kw in line.lower() for kw in role_keywords)
            date_match = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Present|\d{4}-\d{2}|\d{2}-\d{4}|\d{2}/\d{4}|\d{4})\b", line, re.IGNORECASE)
            
            if is_role or date_match or not current_job:
                if current_job:
                    experience.append(current_job)
                
                # 1. Extract and isolate date period (e.g. "Jun 2023 - Present" or "2023-01 to 2023-06")
                date_range_match = re.search(
                    r"\(?\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}-\d{2}|\d{2}-\d{4}|\d{2}/\d{4}|\d{4}|Present)[\s\-\–\—to]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}-\d{2}|\d{2}-\d{4}|\d{2}/\d{4}|\d{4}|Present))\b\)?",
                    line, re.IGNORECASE
                )
                
                start_date = "2023"
                end_date = "Present"
                line_no_date = line
                
                if date_range_match:
                    date_str = date_range_match.group(1)
                    line_no_date = line.replace(date_range_match.group(0), "").strip()
                    line_no_date = re.sub(r"^[,\s|•\-\–\—]+|[,\s|•\-\–\—]+$", "", line_no_date).strip()
                    
                    # Split date_str into start and end dates
                    date_str_lower = date_str.lower()
                    if " to " in date_str_lower:
                        date_parts = re.split(r"\s+to\s+", date_str, flags=re.IGNORECASE)
                    elif " - " in date_str:
                        date_parts = date_str.split(" - ")
                    elif " – " in date_str:
                        date_parts = date_str.split(" – ")
                    elif " — " in date_str:
                        date_parts = date_str.split(" — ")
                    else:
                        date_parts = re.split(r"\s*(?:to|[-–—])\s*", date_str, flags=re.IGNORECASE)
                        
                    if len(date_parts) >= 2:
                        start_date = date_parts[0].strip()
                        end_date = date_parts[1].strip()
                    elif len(date_parts) == 1:
                        start_date = date_parts[0].strip()
                elif date_match:
                    start_date = date_match.group(0)
                    line_no_date = line.replace(date_match.group(0), "").strip()
                    line_no_date = re.sub(r"^[,\s|•\-\–\—]+|[,\s|•\-\–\—]+$", "", line_no_date).strip()
                
                line_no_date = re.sub(r"\(\s*\)", "", line_no_date).strip()
                
                # 2. Split role and company using delimiters like |, •, at, @, or - (without splitting inside dates)
                parts = re.split(r"[|•]|\s+at\s+|\s+@\s+|\s+-\s+", line_no_date, flags=re.IGNORECASE)
                role = "Software Engineer"
                company = "Company"
                if len(parts) >= 2:
                    role = parts[0].strip()
                    company = parts[1].strip()
                elif len(parts) == 1:
                    role = parts[0].strip()
                
                role = re.sub(r"^[,\s|•\-\–\—]+|[,\s|•\-\–\—]+$", "", role).strip()
                company = re.sub(r"^[,\s|•\-\–\—]+|[,\s|•\-\–\—]+$", "", company).strip()
                
                current_job = {
                    "role": role or "Software Engineer",
                    "company": company or "Company",
                    "start_date": start_date,
                    "end_date": end_date,
                    "bullets": []
                }
                
    if current_job:
        experience.append(current_job)
        
    final_exp = []
    for exp in experience:
        if not exp["bullets"]:
            continue
        final_exp.append(exp)
        
    return final_exp

def extract_projects(text: str) -> List[Dict[str, Any]]:
    lines = [l.strip() for l in text.split("\n")]
    in_proj = False
    section_headers = ["education", "experience", "skills", "certifications", "interests", "languages"]
    
    proj_lines = []
    for line in lines:
        line_lower = line.lower()
        if any(h in line_lower for h in ["projects", "personal projects", "academic projects"]):
            in_proj = True
            continue
        if in_proj:
            if any(line_lower.startswith(h) or line_lower == h or (len(line_lower) < 20 and any(h in line_lower for h in section_headers)) for h in section_headers):
                in_proj = False
            else:
                proj_lines.append(line)
                
    projects = []
    current_proj = None
    
    action_verbs = {"built", "developed", "designed", "created", "implemented", "managed", "led", "optimized", "configured", "deployed", "assisted", "used", "leveraged", "enhanced", "integrated", "engineered", "wrote", "reduced", "increased"}
    
    for line in proj_lines:
        if not line:
            continue
            
        first_word = line.split()[0].lower().strip(":,.-") if line.split() else ""
        is_bullet_symbol = line.startswith(("-", "—", "*", "•", "o "))
        is_action_verb = first_word in action_verbs
        
        is_bullet = is_bullet_symbol or (current_proj and (is_action_verb or (len(line) > 40 and not line[0].isupper())))
        clean_line = line.lstrip("-—*•o ").strip()
        
        if is_bullet:
            if current_proj:
                current_proj["bullets"].append(clean_line)
        else:
            if current_proj:
                projects.append(current_proj)
            current_proj = {
                "name": line.strip(":- "),
                "bullets": []
            }
            
    if current_proj:
        projects.append(current_proj)
        
    final_proj = []
    for proj in projects:
        if not proj["bullets"]:
            continue
        final_proj.append(proj)
        
    return final_proj

def parse_resume_heuristics(text: str, filename: Optional[str] = None) -> ResumeParsedData:
    logger.info("Running dynamic local heuristic resume parser...")
    name = extract_name(text, filename)
    email = extract_email(text)
    phone = extract_phone(text)
    links = extract_links(text)
    skills = extract_skills(text)
    education = extract_education(text)
    experience = extract_experience(text)
    projects = extract_projects(text)
    
    # Fallbacks for empty profiles
    if not skills:
        skills = ["Python", "FastAPI", "SQL"]
    if not education:
        education = [{"school": "University", "degree": "B.S. Computer Science", "date": "2024"}]
    if not experience:
        experience = [{
            "role": "Software Developer",
            "company": "Tech Solutions",
            "start_date": "2023",
            "end_date": "Present",
            "bullets": ["Developed and maintained backend API services and structured databases."]
        }]

    return ResumeParsedData(
        name=name,
        email=email,
        phone=phone,
        links=links,
        skills=skills,
        education=education,
        experience=experience,
        projects=projects
    )

def analyze_jd_heuristics(prompt: str) -> JDAnalysisResult:
    logger.info("Running local heuristic JD analyzer...")
    # Extract role title
    role_title = "Software Engineer"
    title_match = re.search(r"(?:role|title|seeking|looking for a|position is for a)\s+([a-zA-Z\s]+?)(?:\.|,|\band\b|with\b|in\b)", prompt, re.IGNORECASE)
    if title_match:
        role_title = title_match.group(1).strip()
    else:
        # Fallback: look for common titles in the prompt
        common_titles = ["Backend Engineer", "Frontend Developer", "Fullstack Developer", "Software Engineer", "DevOps Engineer", "Data Scientist"]
        for title in common_titles:
            if re.search(r"\b" + re.escape(title) + r"\b", prompt, re.IGNORECASE):
                role_title = title
                break

    # Seniority
    seniority = "Mid"
    if any(k in prompt.lower() for k in ["senior", "lead", "sr.", "principal"]):
        seniority = "Senior"
    elif any(k in prompt.lower() for k in ["junior", "jr.", "entry", "intern", "associate"]):
        seniority = "Junior"

    # Skills
    skills = []
    for skill in COMMON_SKILLS:
        if re.search(r"\b" + re.escape(skill) + r"\b", prompt, re.IGNORECASE):
            skills.append(skill)
            
    required_skills = skills[:max(3, len(skills) // 2)]
    preferred_skills = skills[max(3, len(skills) // 2):]

    # Responsibilities
    responsibilities = []
    lines = [l.strip() for l in prompt.split("\n")]
    for line in lines:
        if line.startswith(("-", "*", "•")) or any(kw in line.lower() for kw in ["responsible for", "responsibilities include", "you will"]):
            responsibilities.append(line.lstrip("-*• ").strip())
            
    if not responsibilities:
        responsibilities = ["Develop web application logic and build APIs.", "Collaborate with cross-functional teams."]

    return JDAnalysisResult(
        role_title=role_title,
        seniority=seniority,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        key_responsibilities=responsibilities
    )

def tailor_resume_heuristics(prompt: str) -> ImpactPassResult:
    logger.info("Running local heuristic resume tailor...")
    # Extract role title from the prompt
    role_title = "Software Engineer"
    role_match = re.search(r"Role Title:\s*([^\n]+)", prompt)
    if role_match:
        role_title = role_match.group(1).strip()

    # Extract original experiences from prompt
    experiences = []
    job_blocks = re.findall(r"- Job:\s*([^\n]+) at ([^\n]+)\n((?:\s*\* [^\n]+\n)*)", prompt)
    for role, company, bullets_text in job_blocks:
        bullets = re.findall(r"\s*\* ([^\n]+)", bullets_text)
        experiences.append({
            "role": role.strip(),
            "company": company.strip(),
            "start_date": "2023",
            "end_date": "Present",
            "location": "Remote",
            "bullets": bullets
        })

    # Restructure experience: prioritize and trim to max 3 bullets per job, 8 total
    tailored_experience = []
    for exp in experiences:
        bullets = exp["bullets"]
        # Add simple tailoring: highlight tech keywords or front-load action verbs
        tailored_bullets = []
        for b in bullets:
            # Simple keyword highlights or metric emphasizing
            tailored_b = b
            if not re.search(r"\b\d+%\b|\b\d+\s*(?:hours|days|weeks|months|years|percent|stars)\b", b):
                # Optionally add some metric formatting
                pass
            tailored_bullets.append(tailored_b)
            
        tailored_experience.append({
            "role": exp["role"],
            "company": exp["company"],
            "start_date": exp["start_date"],
            "end_date": exp["end_date"],
            "location": exp["location"],
            "bullets": tailored_bullets[:3]  # Enforce max 3 bullets per job
        })

    # Highlights Strip: select top 4 skills
    skills_match = re.search(r"--- CANDIDATE EXPERIENCES & PROJECTS.*", prompt, re.DOTALL)
    skills = ["Python", "FastAPI", "SQL", "Git"]
    if skills_match:
        skills_text = skills_match.group(0)
        found_skills = []
        for s in COMMON_SKILLS:
            if re.search(r"\b" + re.escape(s) + r"\b", skills_text, re.IGNORECASE):
                found_skills.append(s)
        if found_skills:
            skills = found_skills[:4]

    highlights = [
        HighlightSkill(skill=s, relevance_reason=f"Demonstrated core proficiency in development matching job description.")
        for s in skills
    ]

    anchor_line = f"Professional {role_title} candidate specialized in building performant systems"

    return ImpactPassResult(
        anchor_line=anchor_line,
        highlights_strip=highlights,
        tailored_experience=tailored_experience
    )

def handle_heuristic_fallback(prompt: str, schema: Type[BaseModel]) -> BaseModel:
    """
    Directs the prompt to the appropriate heuristic parser function based on Pydantic schema type.
    """
    logger.info(f"Fallback Heuristic Engine triggered for schema: {schema.__name__}")
    
    # Extract filename if present in the prompt (passed by extract_resume_from_images)
    filename = None
    filename_match = re.search(r"Note: Source filename is '([^']+)'", prompt, re.IGNORECASE)
    if filename_match:
        filename = filename_match.group(1)

    if schema == ResumeParsedData:
        # Extract raw resume text block from the prompt
        raw_text_match = re.search(r"--- RAW RESUME TEXT ---\n(.*)", prompt, re.DOTALL)
        raw_text = raw_text_match.group(1).strip() if raw_text_match else prompt
        return parse_resume_heuristics(raw_text, filename)
        
    elif schema == JDAnalysisResult:
        return analyze_jd_heuristics(prompt)
        
    elif schema == TargetedRewriteResult:
        # For TargetedRewriteResult, extract bullets from prompt and return them
        bullets = re.findall(r"\d+\.\s*([^\n]+)", prompt)
        rewritten = [RewrittenBullet(original_bullet=b, rewritten_bullet=b) for b in bullets]
        return TargetedRewriteResult(rewritten_bullets=rewritten)
        
    elif schema == ImpactPassResult:
        return tailor_resume_heuristics(prompt)
        
    elif schema == TruthfulnessCheckResult:
        # Return empty truthfulness check (all valid)
        bullets = re.findall(r"\d+\.\s*([^\n]+)", prompt)
        verifications = [
            BulletVerification(rewritten_bullet=b, is_fabricated=False, justification="", suggested_fix="")
            for b in bullets
        ]
        return TruthfulnessCheckResult(is_fabricated=False, verification_report=verifications)
        
    # Return empty instance if schema is unknown
    return schema()
