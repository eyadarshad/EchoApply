import io
import logging
from typing import Dict, Any
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from app.schemas import ResumeParsedData

logger = logging.getLogger(__name__)

def generate_resume_pdf(data: ResumeParsedData) -> bytes:
    """
    Renders structured resume data to PDF using WeasyPrint and an elegant,
    single-column HTML template.
    """
    try:
        from weasyprint import HTML
    except ImportError as e:
        logger.error("WeasyPrint is not installed or could not load shared libraries (GTK+).")
        raise e

    # Render HTML template string
    links_html = "".join([f'<a href="{l}">{l}</a> | ' for l in data.links])
    if links_html.endswith(" | "):
        links_html = links_html[:-3]

    skills_html = ", ".join(data.skills)

    anchor_html = ""
    if data.anchor_line:
        anchor_html = f'<div class="anchor-line" style="font-style: italic; font-weight: bold; margin-top: 4px; font-size: 11.5pt; color: #333333; text-align: center;">{data.anchor_line}</div>'

    highlights_html = ""
    if data.highlights_strip:
        highlights_bullets = "".join([f"<li><strong>{h.get('skill', '')}</strong>: {h.get('relevance_reason', '')}</li>" for h in data.highlights_strip])
        highlights_html = f"""
        <div class="section-title">Relevance & Highlights</div>
        <ul class="bullet-list" style="margin-bottom: 12px;">{highlights_bullets}</ul>
        """

    experience_html = ""
    for exp in data.experience:
        bullets_list = "".join([f"<li>{b}</li>" for b in exp.get("bullets", [])])
        end_date = exp.get("end_date") or "Present"
        location_str = f" | {exp.get('location')}" if exp.get("location") else ""
        
        experience_html += f"""
        <div class="item">
            <div class="item-header">
                <span>{exp.get('role', '')}</span>
                <span>{exp.get('start_date', '')} &ndash; {end_date}</span>
            </div>
            <div class="item-subheader">
                <span>{exp.get('company', '')}{location_str}</span>
            </div>
            {f'<ul class="bullet-list">{bullets_list}</ul>' if bullets_list else ''}
        </div>
        """

    education_html = ""
    for edu in data.education:
        degree_major = f"{edu.get('degree', '')}"
        if edu.get("major"):
            degree_major += f" in {edu.get('major')}"
        
        gpa_str = f"<p>GPA: {edu.get('gpa')}</p>" if edu.get("gpa") else ""
        
        education_html += f"""
        <div class="item">
            <div class="item-header">
                <span>{degree_major}</span>
                <span>{edu.get('date', '')}</span>
            </div>
            <div class="item-subheader">
                <span>{edu.get('school', '')}</span>
            </div>
            {gpa_str}
        </div>
        """

    projects_html = ""
    for proj in data.projects:
        bullets_list = "".join([f"<li>{b}</li>" for b in proj.get("bullets", [])])
        link_str = f' &middot; <a href="{proj.get("link")}">{proj.get("link")}</a>' if proj.get("link") else ""
        
        projects_html += f"""
        <div class="item">
            <div class="item-header">
                <span>{proj.get('name', '')}{link_str}</span>
            </div>
            {f'<ul class="bullet-list">{bullets_list}</ul>' if bullets_list else ''}
        </div>
        """

    # Combine everything into an elegant ATS-friendly single-column layout
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: letter;
                margin: 0.75in;
            }}
            body {{
                font-family: 'Arial', sans-serif;
                color: #222222;
                line-height: 1.35;
                font-size: 10pt;
            }}
            .header {{
                text-align: center;
                margin-bottom: 15px;
            }}
            .name {{
                font-size: 20pt;
                font-weight: bold;
                color: #111111;
                margin: 0 0 4px 0;
            }}
            .contact {{
                font-size: 9pt;
                color: #555555;
            }}
            .contact a {{
                color: #555555;
                text-decoration: none;
            }}
            .section-title {{
                font-size: 11pt;
                font-weight: bold;
                color: #111111;
                border-bottom: 1px solid #111111;
                padding-bottom: 1px;
                margin-top: 15px;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .item {{
                margin-bottom: 10px;
                page-break-inside: avoid;
            }}
            .item-header {{
                display: flex;
                justify-content: space-between;
                font-weight: bold;
                color: #111111;
            }}
            .item-subheader {{
                display: flex;
                justify-content: space-between;
                font-style: italic;
                color: #444444;
                font-size: 9.5pt;
                margin-top: 1px;
                margin-bottom: 3px;
            }}
            .bullet-list {{
                margin: 0;
                padding-left: 18px;
            }}
            .bullet-list li {{
                margin-bottom: 2px;
            }}
            .skills {{
                font-size: 9.5pt;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="name">{data.name}</h1>
            <div class="contact">
                {data.email} {f'| {data.phone}' if data.phone else ''} {f'| {links_html}' if links_html else ''}
            </div>
            {anchor_html}
        </div>

        {highlights_html}

        {f'<div class="section-title">Skills</div><div class="skills">{skills_html}</div>' if skills_html else ''}

        {f'<div class="section-title">Experience</div>{experience_html}' if experience_html else ''}

        {f'<div class="section-title">Projects</div>{projects_html}' if projects_html else ''}

        {f'<div class="section-title">Education</div>{education_html}' if education_html else ''}
    </body>
    </html>
    """

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes

def generate_resume_docx(data: ResumeParsedData) -> bytes:
    """
    Renders structured resume data to DOCX using python-docx.
    Configures standard margins, tab-stops for dates, and basic styling.
    """
    doc = Document()

    # Configure 0.75-inch margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Configure default style font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(10)

    # Header Name
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_name = p_name.add_run(data.name)
    run_name.font.size = Pt(18)
    run_name.font.bold = True

    # Contact Info
    p_contact = doc.add_paragraph()
    p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact_parts = [data.email]
    if data.phone:
        contact_parts.append(data.phone)
    contact_parts.extend(data.links)
    p_contact.add_run("  |  ".join(contact_parts))

    # Anchor Line
    if data.anchor_line:
        p_anchor = doc.add_paragraph()
        p_anchor.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_anchor.paragraph_format.space_after = Pt(8)
        run_anchor = p_anchor.add_run(data.anchor_line)
        run_anchor.italic = True
        run_anchor.bold = True
        run_anchor.font.size = Pt(11)

    # Helper to add section headings with bottom border lines
    def add_section_heading(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text.upper())
        run.font.size = Pt(11)
        run.font.bold = True
        # Insert a bottom border under heading paragraph
        pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="000000"/></w:pBdr>')
        p._p.get_or_add_pPr().append(pBdr)

    # Highlights Strip Section
    if data.highlights_strip:
        add_section_heading("Relevance & Highlights")
        for h in data.highlights_strip:
            p_hl = doc.add_paragraph(style='List Bullet')
            p_hl.paragraph_format.space_after = Pt(2)
            run_skill = p_hl.add_run(h.get("skill", "") + ": ")
            run_skill.bold = True
            p_hl.add_run(h.get("relevance_reason", ""))

    # 1. Skills Section
    if data.skills:
        add_section_heading("Skills")
        doc.add_paragraph(", ".join(data.skills))

    # 2. Experience Section
    if data.experience:
        add_section_heading("Experience")
        for exp in data.experience:
            p_title = doc.add_paragraph()
            p_title.paragraph_format.space_before = Pt(4)
            p_title.paragraph_format.space_after = Pt(2)
            p_title.paragraph_format.keep_with_next = True

            role_company = f"{exp.get('role', '')} - {exp.get('company', '')}"
            end_date = exp.get("end_date") or "Present"
            dates_location = f"{exp.get('start_date', '')} - {end_date}"
            if exp.get("location"):
                dates_location += f" ({exp.get('location')})"

            run_title = p_title.add_run(role_company)
            run_title.bold = True
            p_title.add_run("\t" + dates_location)
            
            # Align dates to right margin (at 7.0 inches)
            p_title.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), alignment=2) # 2 is right alignment

            bullets = exp.get("bullets", [])
            for bullet in bullets:
                p_bullet = doc.add_paragraph(style='List Bullet')
                p_bullet.paragraph_format.space_after = Pt(2)
                p_bullet.add_run(bullet)

    # 3. Projects Section
    if data.projects:
        add_section_heading("Projects")
        for proj in data.projects:
            p_proj = doc.add_paragraph()
            p_proj.paragraph_format.space_before = Pt(4)
            p_proj.paragraph_format.space_after = Pt(2)
            p_proj.paragraph_format.keep_with_next = True

            proj_name = proj.get("name", "")
            proj_link = proj.get("link", "")
            title_text = f"{proj_name}"
            if proj_link:
                title_text += f" ({proj_link})"

            run_title = p_proj.add_run(title_text)
            run_title.bold = True

            bullets = proj.get("bullets", [])
            for bullet in bullets:
                p_bullet = doc.add_paragraph(style='List Bullet')
                p_bullet.paragraph_format.space_after = Pt(2)
                p_bullet.add_run(bullet)

    # 4. Education Section
    if data.education:
        add_section_heading("Education")
        for edu in data.education:
            p_edu = doc.add_paragraph()
            p_edu.paragraph_format.space_before = Pt(4)
            p_edu.paragraph_format.space_after = Pt(2)

            degree_major = f"{edu.get('degree', '')}"
            if edu.get("major"):
                degree_major += f" in {edu.get('major')}"
            
            school = edu.get("school", "")
            edu_dates = edu.get("date", "")

            run_edu = p_edu.add_run(f"{degree_major}, {school}")
            run_edu.bold = True
            p_edu.add_run("\t" + edu_dates)
            
            p_edu.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), alignment=2)

            if edu.get("gpa"):
                p_gpa = doc.add_paragraph(style='List Bullet')
                p_gpa.paragraph_format.space_after = Pt(2)
                p_gpa.add_run(f"GPA: {edu.get('gpa')}")

    # Output to an in-memory byte buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
