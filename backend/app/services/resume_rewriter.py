"""
AI Resume Rewriter Service — generates psychologically optimized, ATS-calibrated resume content
tailored to each template style (Classic, Modern, Minimal, Creative, Executive).

Each style executes high-end psychological prompts that produce:
1. Psychological scroll-stop hooks (taglines and role openers that halt recruiter scanning in <3s).
2. Psychologically amplified, reality-anchored capability expressions (XYZ formula, high-agency verbs).
3. Exact ATS vs Cold-Outreach optimization (Classic = 100% ATS simple, Executive = Cold email luxury).
4. Strict single A4 page content budgeting and density calibration.
"""

import logging
import copy
from typing import Optional
from app.schemas import ResumeParsedData
from app.services.llm_client import llm_client_resume as llm_client

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Per-Template High-End AI Rewriting Prompts
# ═══════════════════════════════════════════

STYLE_PROMPTS = {
    "classic": """You are optimizing a resume for the CLASSIC template — the #1 MOST ATS-FRIENDLY layout.
TARGET AUDIENCE: Corporate ATS systems (Workday, Taleo, Greenhouse, Lever, iCIMS) + conservative hiring committees (Finance, Law, Consulting, Enterprise, Government).

PSYCHOLOGICAL & ATS STRATEGY:
- ATS Priority: 100% MAXIMUM MACHINE READABILITY. Use standard, unambiguous section labels.
- Tone: High-authority, formal institutional confidence. Zero buzzword fluff.
- Psychological Capability Framing: Reframe every contribution as an indispensable institutional asset. Use authoritative verbs: "Directed", "Orchestrated", "Instituted", "Governed", "Spearheaded".
- XYZ Impact Formula: Structure every bullet as: Accomplished [X - high value objective] as measured by [Y - tangible metric/scope] by executing [Z - formal methodology/system].
- Project Explanation: Reframe projects as mission-critical enterprise initiatives with documented outcomes.
- Scroll-Stop Hook: Craft an authoritative anchor tagline emphasizing domain mastery, years/scope, and core credential (e.g., "Senior Software Architect | High-Concurrency Enterprise Systems | Scaled Core Platforms to 10M+ Users").
- Font Family: "Georgia", "Times New Roman", serif
- Color Theory Palette (Corporate Trust & Authority):
  * primary: "#1e3a5f" (Deep Navy Blue — authority, stability, institutional trust)
  * accent: "#b8860b" (Muted Gold — prestige, excellence, quality)
  * text: "#1e293b" (Deep charcoal text for maximum contrast)
  * background: "#ffffff" (Pure White)

SCROLL-STOP RULE: The opening bullet for every role and project MUST start with a bold action verb + quantifiable impact metric ($ savings, % growth, headcount, latency reduction).
""",

    "modern": """You are optimizing a resume for the MODERN template — balanced ATS-friendly & tech-forward design.
TARGET AUDIENCE: Tech companies, VC-backed startups, SaaS unicorns, Product teams, and modern engineering managers.

PSYCHOLOGICAL & ATS STRATEGY:
- ATS Priority: 95% ATS Safe. Single-column or clean top-accent semantic structure packed with high-value technical keywords.
- Tone: High-agency builder, technical leader, velocity-driven problem solver.
- Psychological Capability Framing: Paint the candidate as a high-impact technical force who ships resilient, scalable systems rapidly. Power verbs: "Architected", "Engineered", "Scaled", "Automated", "Pioneered".
- XYZ Impact Formula: Lead with technical action, specify exact stack/architecture, end with quantifiable performance/developer velocity gain.
- Project Explanation: Describe user's projects with systems-level depth (e.g. "Architected a distributed async processing engine in Python/PostgreSQL handling 50K+ events/min with sub-second SLA").
- Scroll-Stop Hook: Punchy, high-octane engineering tagline (e.g., "Full-Stack Systems Engineer | Distributed Architecture & Real-Time APIs | Shipped Systems Powering 500K+ DAU").
- Font Family: "Inter", "Helvetica Neue", Arial, sans-serif
- Color Theory Palette (Innovation & Modern Tech):
  * primary: "#0f172a" (Slate Dark — modern, sleek, commanding)
  * accent: "#14b8a6" (Premium Teal — technology, growth, clarity)
  * sidebar_bg: "#111827" (Rich charcoal sidebar)
  * sidebar_accent: "#818cf8" (Indigo-violet sidebar accent)
  * text: "#1e293b" (Slate text)
  * background: "#ffffff" (Clean white)

SCROLL-STOP RULE: Each role's first bullet MUST spotlight the core tech stack AND a measured technical outcome.
""",

    "minimal": """You are optimizing a resume for the MINIMAL template — surgical precision and extreme clarity.
TARGET AUDIENCE: Elite engineering bars, Principal Engineers, Data Scientists, Quantitative Researchers, and Senior Consultants.

PSYCHOLOGICAL & ATS STRATEGY:
- ATS Priority: 98% ATS Safe. Pristine semantic hierarchy, distraction-free typographic clarity.
- Tone: Understated mastery, zero fluff, telegraphic precision. Let monumental results speak for themselves.
- Psychological Capability Framing: Eliminate filler words. Present engineering decisions with mathematical clarity.
- XYZ Impact Formula: Compressed, high-signal statements (12-18 words max per bullet).
- Project Explanation: Highlight core algorithmic/infrastructure challenges solved with minimal footprint and maximum efficiency.
- Scroll-Stop Hook: Clean, laser-targeted value equation (e.g., "Distributed Systems Engineer · Rust / Go · 99.999% Fault-Tolerant Infrastructure").
- Font Family: "Inter", "Helvetica Neue", Arial, sans-serif
- Color Theory Palette (Precision & Balance):
  * primary: "#2d2d2d" (Charcoal Black — clean, focused, professional)
  * accent: "#4a7c6f" (Sage Green — balance, stability, calm authority)
  * sidebar_bg: "#faf9f7" (Warm off-white background)
  * text: "#2d2d2d" (Charcoal text)
  * background: "#ffffff" (White panel)

SCROLL-STOP RULE: First bullet per role = pure metric (number + result). No fluff, no warm-up. Instant impact.
""",

    "creative": """You are optimizing a resume for the CREATIVE template — bold branding, storytelling, and visual punch.
TARGET AUDIENCE: Design studios, Growth & Product Marketing, Brand agencies, Creative Directors, and modern startup founders.

PSYCHOLOGICAL & ATS STRATEGY:
- ATS Priority: Moderate ATS / Optimized for direct recruiter and hiring manager eyes.
- Tone: Magnetic, vision-driven, charismatic brand builder.
- Psychological Capability Framing: Paint vivid before-and-after transformations. Words: "Reimagined", "Transformed", "Crafted", "Ignited", "Spearheaded".
- XYZ Impact Formula: "Transformed [baseline friction] into [delightful high-converting experience], generating [Y% growth/engagement] by designing [Z]".
- Project Explanation: Highlight storytelling, user empathy, brand cohesion, and interactive flair.
- Scroll-Stop Hook: Magnetic creative manifesto (e.g., "Product Designer & Visual Strategist · Crafting High-Converting Digital Ecosystems & Viral Consumer Brands").
- Font Family: "Inter", "Helvetica Neue", Arial, sans-serif
- Color Theory Palette (Energy & Distinction):
  * primary: "#4a1942" (Dark Plum — deep luxury, artistic weight)
  * accent: "#ec4899" (Vibrant Rose — passion, modern energy)
  * accent2: "#f97316" (Sunset Amber — creativity, warmth)
  * text: "#4a1942" (Plum text color)
  * background: "#fdf8f0" (Warm cream)

SCROLL-STOP RULE: Each role opens with a dramatic transformation narrative ("Transformed X into Y driving Z% increase in adoption").
""",

    "executive": """You are optimizing a resume for the EXECUTIVE template — luxury two-column cold outreach layout.
TARGET AUDIENCE: C-Suite Executives, VPs, Managing Directors, Board Members, and Investors in DIRECT COLD EMAILS and executive recruiting.

PSYCHOLOGICAL & ATS STRATEGY:
- ATS Priority: LEAST ATS-FRIENDLY / MAXIMUM HUMAN VISUAL IMPACT. Optimized to impress human executives reading a PDF on desktop or tablet.
- Tone: Boardroom commanding, strategic vision, revenue & P&L ownership, global scale.
- Psychological Capability Framing: Elevate every project and role into enterprise-scale leadership, market dominance, and strategic alignment. Verbs: "Commanded", "Delivered", "Championed", "Accelerated", "Overhauled".
- XYZ Impact Formula: "Championed [strategic growth/operational overhaul], unlocking [$X revenue/scale] across [Y global teams] by architecting [Z high-yield strategy]".
- Project Explanation: Reframe projects as strategic technical assets, IP creation, or multi-stakeholder initiatives with commercial leverage.
- Scroll-Stop Hook: Commanding C-suite / VP power statement (e.g., "VP of Engineering & Technology Leader | Scaling $50M+ ARR Platforms | Leading Global 60+ Distributed Eng Teams").
- Font Family: "Georgia", "Times New Roman", serif
- Color Theory Palette (Prestige & Executive Gold):
  * primary: "#0f172a" (Deeper Slate Navy — executive status, commanding presence)
  * accent: "#c9a55c" (Champagne Gold — distinction, luxury, board-level success)
  * text: "#1e293b" (Executive slate)
  * background: "#fefdfb" (Warm ivory background)

SCROLL-STOP RULE: First bullet per role MUST lead with bottom-line business value ($ revenue, $ cost savings, headcount, or market expansion).
"""
}

# Aliases for variations
STYLE_PROMPTS["classic_executive"] = STYLE_PROMPTS["classic"]
STYLE_PROMPTS["modern_executive"] = STYLE_PROMPTS["executive"]

REWRITE_SYSTEM_INSTRUCTION = """You are the world's most sophisticated AI Resume Optimization and Psychological Career Positioning Engine.

ABSOLUTE OPERATIONAL MANDATES:
1. COMPLETE DATA PRESERVATION — NEVER DROP OR DISCARD CANDIDATE ASSETS:
   - Preserve ALL of the candidate's authentic projects (e.g. all 3–5 projects from the original data). For each project, rewrite and elevate 1–2 punchy XYZ impact bullets.
   - Preserve ALL of the candidate's technical skills, languages, frameworks, libraries, and tools. Organize them cleanly into categories.
   - Preserve the candidate's executive summary / professional profile, elevating it into a 2–3 sentence high-impact opening.
   - Preserve ALL education entries, degrees, universities, coursework, and certifications.
   - NEVER drop candidate projects or skills unless explicitly requested.

2. PSYCHOLOGICAL SCROLL-STOP HOOKS:
   - Generate a magnetic, high-status `scroll_stop_hook` tagline for the candidate header that grabs recruiter attention within 3 seconds.
   - The first bullet of EVERY experience role and EVERY project must be a powerful scroll-stop hook (starting with a high-agency action verb and quantified outcome).

3. PSYCHOLOGICALLY AMPLIFIED, REALITY-ANCHORED CAPABILITY EXPRESSION:
   - Enhance the explanation of the user's projects and experience using high-agency, executive-grade language.
   - Follow Google's XYZ Formula: "Accomplished [X - high impact objective] as measured by [Y - quantified scale/metric/efficiency] by doing/architecting [Z - technology/methodology]".
   - Elevate the candidate's authentic contributions to their highest professional potential.
   - ABSOLUTE TRUTHFULNESS: NEVER invent non-existent companies, fake universities, or fabricated degrees. Enhance and amplify EXISTING capabilities, projects, and skills with superior framing.

4. 1-PAGE A4 PROPORTIONAL BUDGETING:
   - Calibrate bullet lengths (14–20 words per bullet) so all sections fill exactly ONE A4 PAGE with balanced vertical rhythm.
   - 2–3 bullets per experience role.
   - 1–2 high-octane bullets per project.

5. ATS KEYWORD PRESERVATION & TARGET MATCHING:
   - If a Target Job Description is provided, naturally weave relevant keywords into skills, bullets, and summary without keyword-stuffing.

6. COMPLETE SCHEMA RETURN:
   - Return the complete JSON matching ResumeParsedData.
   - Preserve candidate's original name, email, phone, and links EXACTLY.
   - Populate color_theme, font_family, executive_summary, highlights_strip (3-4 items), scroll_stop_hook, certifications, and languages.
"""


def rewrite_resume_for_style(
    parsed_resume: ResumeParsedData,
    template_style: str,
    job_description: Optional[str] = None
) -> ResumeParsedData:
    """
    Use LLM to rewrite and optimize resume content for a specific template style.
    
    Executes psychological scroll-stop hooks, reality-anchored capability amplification (XYZ formula),
    ATS calibration, and strict 1-page A4 content density budgeting.
    """
    clean_style = template_style.lower().strip()
    style_prompt = STYLE_PROMPTS.get(clean_style, STYLE_PROMPTS["modern"])
    
    # Build user prompt
    resume_json = parsed_resume.model_dump_json(indent=2)
    
    jd_section = ""
    if job_description and len(job_description.strip()) > 20:
        jd_section = f"""
## Target Job Description (Tailor resume keywords and impact to match this target role):
<DATA>
{job_description[:3500]}
</DATA>
"""
    
    prompt = f"""Rewrite, elevate, and psychologically optimize this resume for the {clean_style.upper()} template style.

{style_prompt}

## Original Candidate Resume Data:
<DATA>
{resume_json}
</DATA>
{jd_section}

CRITICAL EXECUTION REQUIREMENTS:
1. Apply the psychological scroll-stop hook and XYZ formula to all experience bullets and project explanations.
2. Ensure content is strictly budgeted to fill exactly ONE A4 PAGE cleanly.
3. Keep name, email, phone, links EXACTLY as-is. Enhance and elevate everything else.
4. Return valid, well-formed JSON matching the ResumeParsedData schema.
"""

    system_instruction = REWRITE_SYSTEM_INSTRUCTION + "\n\n" + style_prompt
    
    try:
        result = llm_client.generate_structured(
            prompt=prompt,
            response_schema=ResumeParsedData,
            model_type="flash",
            max_retries=2,
            system_instruction=system_instruction
        )
        
        # Safety: preserve exact original contact info (LLM must not alter contact coordinates)
        result.name = parsed_resume.name
        result.email = parsed_resume.email
        result.phone = parsed_resume.phone
        result.links = parsed_resume.links
        
        # Enforce strict single-page A4 density limits
        if result.experience:
            for exp in result.experience:
                if exp.bullets:
                    exp.bullets = exp.bullets[:3]
        if result.projects:
            result.projects = result.projects[:3]
            for proj in result.projects:
                if proj.bullets:
                    proj.bullets = proj.bullets[:2]
        if result.skills:
            result.skills = result.skills[:12]
        if result.education:
            result.education = result.education[:2]
        
        # Thorough sanitization pass: eliminate any stray JSON syntax or prompt instructions
        from app.services.heuristic_parser import _is_invalid_resume_line, _sanitize_resume_string
        
        if result.experience:
            for exp in result.experience:
                exp.role = _sanitize_resume_string(exp.role) or "Software Engineer"
                exp.company = _sanitize_resume_string(exp.company) or "Company"
                if exp.bullets:
                    exp.bullets = [
                        _sanitize_resume_string(b)
                        for b in exp.bullets
                        if b and not _is_invalid_resume_line(b)
                    ]
        if result.projects:
            for proj in result.projects:
                proj.name = _sanitize_resume_string(proj.name)
                if proj.bullets:
                    proj.bullets = [
                        _sanitize_resume_string(b)
                        for b in proj.bullets
                        if b and not _is_invalid_resume_line(b)
                    ]
        if result.education:
            for edu in result.education:
                edu.school = _sanitize_resume_string(edu.school) or "University"
                edu.degree = _sanitize_resume_string(edu.degree) or "Degree"
                if edu.major:
                    edu.major = _sanitize_resume_string(edu.major)
        if result.skills:
            result.skills = [_sanitize_resume_string(s) for s in result.skills if s and not _is_invalid_resume_line(s)]
            
        logger.info(f"AI resume rewrite for '{template_style}' style completed successfully with high-end psychological prompts.")
        return result
        
    except Exception as e:
        logger.error(f"AI resume rewrite failed for style '{template_style}': {e}")
        # Robust fallback: return enhanced copy of original
        fallback = copy.deepcopy(parsed_resume)
        if not fallback.scroll_stop_hook:
            skills_preview = " · ".join(fallback.skills[:3]) if fallback.skills else "Core Competencies"
            recent_role = fallback.experience[0].role if fallback.experience else "Candidate"
            fallback.scroll_stop_hook = f"{recent_role} | {skills_preview}"
            fallback.anchor_line = fallback.scroll_stop_hook
        return fallback
