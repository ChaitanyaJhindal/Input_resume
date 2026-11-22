from typing import List
from backend.app.schemas.resume import ResumeProfile

class MarkdownGenerator:
    """
    Renders canonical ResumeProfile objects into structured, highly-readable Markdown
    for recruiter inspection.
    """

    @classmethod
    def generate_markdown(cls, profile: ResumeProfile) -> str:
        lines: List[str] = []

        # Candidate Header
        lines.append(f"# {profile.name}")
        if profile.current_designation:
            lines.append(f"**{profile.current_designation}**")
        lines.append("")

        # Contact Info
        contact_parts = []
        if profile.email:
            contact_parts.append(f"📧 {profile.email}")
        if profile.phone:
            contact_parts.append(f"📞 {profile.phone}")
        if profile.location:
            contact_parts.append(f"📍 {profile.location}")
        if contact_parts:
            lines.append(" | ".join(contact_parts))
            lines.append("")

        # Academic Profile Links & Verified External Metrics
        if profile.academic_links:
            link_parts = []
            for lnk in profile.academic_links:
                badge = " (Verified)" if lnk.verified else ""
                link_parts.append(f"[{lnk.platform.replace('_', ' ').title()}{badge}]({lnk.url})")
            lines.append("**Academic Profiles**: " + " | ".join(link_parts))
            lines.append("")

        ev_ext = profile.external_verification
        if ev_ext and (ev_ext.citation_count is not None or ev_ext.h_index is not None):
            lines.append(
                f"> **Verified Research Impact ({ev_ext.match_method})**: "
                f"Citations: `{ev_ext.citation_count or 0}`, h-index: `{ev_ext.h_index or 0}`, Works: `{ev_ext.works_count or 0}`"
            )
            lines.append("")

        # Summary
        if profile.summary:
            lines.append("## Professional Summary")
            lines.append(profile.summary)
            lines.append("")

        # Screening Status Callout
        screening = profile.screening
        status_emoji = "✅" if screening.eligibility_status == "eligible" else ("⚠️" if screening.eligibility_status == "needs_review" else "❌")
        lines.append(f"> **Recruiter Screening Status**: {status_emoji} **{screening.eligibility_status.upper().replace('_', ' ')}** (Score: {screening.overall_score}%, Confidence: {int(screening.confidence * 100)}%)")
        if screening.flags:
            lines.append("> ")
            for f in screening.flags:
                lines.append(f"> - {f}")
        lines.append("")

        # Education
        lines.append("## Education")
        if profile.education:
            for edu in profile.education:
                lines.append(f"### {edu.degree}")
                norm_info = f"{edu.institution_normalized or edu.institution} ({edu.institution_category or 'Other'} - {edu.institution_tier or 'Unclassified'})"
                lines.append(f"- **Institution**: {norm_info}")
                if edu.graduation_year:
                    lines.append(f"- **Year of Completion**: {edu.graduation_year}")
                if edu.thesis_title:
                    lines.append(f"- **Thesis**: {edu.thesis_title}")
                if edu.gpa_or_honors:
                    lines.append(f"- **Honors / GPA**: {edu.gpa_or_honors}")
                if edu.field:
                    lines.append(f"- **Field / Specialization**: {edu.field}")
                if edu.evidence:
                    lines.append(f"- *Source Evidence*: `{edu.evidence}` (Page {edu.source_page or 1}, Confidence: {int(edu.confidence * 100)}%)")
                lines.append("")
        else:
            lines.append("No explicit education records identified.")
            lines.append("")

        # Experience Breakdown
        exp = profile.experience
        lines.append("## Experience Overview")
        lines.append(f"- **Total Career Experience**: {exp.total_years} years")
        lines.append(f"- **Academic Teaching Experience**: {exp.teaching_years} years")
        lines.append(f"- **Research & Postdoctoral**: {exp.research_years} years")
        lines.append(f"- **Industry / Corporate**: {exp.industry_years} years")
        lines.append(f"- **Academic Administration**: {exp.administrative_years} years")
        lines.append("")

        # Employment History
        if profile.employment:
            lines.append("### Employment History")
            for emp in profile.employment:
                duration_str = f"({emp.start_date or 'N/A'} – {emp.end_date or 'Present'}, ~{emp.duration_years} yrs)"
                lines.append(f"#### {emp.title} — {emp.organization} {duration_str}")
                lines.append(f"- **Classification**: `{emp.category.upper()}`")
                if emp.description:
                    lines.append(f"- {emp.description}")
                if emp.evidence:
                    lines.append(f"- *Evidence*: `{emp.evidence}`")
                lines.append("")

        # Research & Publications
        lines.append("## Research & Scholarship")
        if profile.research.research_domains:
            lines.append(f"**Research Domains**: {', '.join(profile.research.research_domains)}")
            lines.append("")

        if profile.research.publications:
            lines.append(f"### Publications ({len(profile.research.publications)})")
            for idx, pub in enumerate(profile.research.publications, 1):
                venue_str = f" — *{pub.venue}*" if pub.venue else ""
                year_str = f" ({pub.year})" if pub.year else ""
                doi_str = f" [DOI: {pub.doi}]" if pub.doi else ""
                indexed_str = f" `[{pub.indexed}]`" if pub.indexed else ""
                lines.append(f"{idx}. **{pub.title}**{venue_str}{year_str}{indexed_str}{doi_str}")
                if pub.evidence:
                    lines.append(f"   > Evidence: `{pub.evidence}`")
            lines.append("")

        if profile.research.patents:
            lines.append("### Patents & IP")
            for pat in profile.research.patents:
                title = pat.get("title", "Patent")
                num = pat.get("patent_number", "")
                status = pat.get("status", "")
                lines.append(f"- **{title}** ({num}) - *{status}*")
            lines.append("")

        # Skills & Certifications
        if profile.skills:
            lines.append("## Core Competencies & Skills")
            lines.append(", ".join(profile.skills))
            lines.append("")

        if profile.certifications:
            lines.append("## Certifications")
            for cert in profile.certifications:
                lines.append(f"- {cert}")
            lines.append("")

        # Courses Taught & Supervision
        if profile.courses_taught:
            lines.append(f"## Courses Taught ({len(profile.courses_taught)})")
            for crs in profile.courses_taught:
                code = f"[{crs.course_code}] " if crs.course_code else ""
                meta = f" ({crs.level}, {crs.institution or 'Academic'})"
                lines.append(f"- **{code}{crs.course_name}**{meta}")
            lines.append("")

        sup = profile.supervision
        if sup and (sup.phd_completed or sup.phd_ongoing or sup.masters_guided or sup.ug_projects_guided):
            lines.append("## Academic Supervision")
            lines.append(
                f"- PhD Completed: {sup.phd_completed} | PhD Ongoing: {sup.phd_ongoing} | "
                f"Masters Guided: {sup.masters_guided} | UG Projects: {sup.ug_projects_guided}"
            )
            lines.append("")

        if profile.notable_highlights:
            lines.append("## Distinctive Highlights")
            for hl in profile.notable_highlights:
                imp = f" — {hl.impact}" if hl.impact else ""
                lines.append(f"- **[{hl.category.upper()}] {hl.title}**{imp}")
            lines.append("")

        # Traceable Source Evidence
        if profile.source_evidence:
            lines.append("## Traceable Source Evidence")
            for ev in profile.source_evidence:
                lines.append(f"- **{ev.field}**: `{ev.value}` — \"*{ev.evidence}*\" (Page {ev.source_page or 1}, Confidence: {int(ev.confidence * 100)}%)")
            lines.append("")

        return "\n".join(lines)
