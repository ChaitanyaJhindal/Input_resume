import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.resume import ResumeProfile
from backend.app.services.education_service import EducationService

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

_PLACEHOLDER_STRINGS = {
    "null",
    "none",
    "n/a",
    "na",
    "not specified",
    "unspecified",
    "unknown",
    "email@example.com",
    "+1-xxx",
    "phone or null",
    "location or null",
    "title or null",
}

_STOPWORDS = {
    "university",
    "college",
    "institute",
    "institution",
    "school",
    "faculty",
    "department",
    "center",
    "centre",
    "technology",
    "science",
    "sciences",
    "engineering",
    "management",
    "studies",
    "research",
    "academy",
    "national",
    "international",
    "state",
    "degree",
    "bachelor",
    "master",
    "masters",
    "doctor",
    "philosophy",
    "the",
    "and",
    "for",
    "with",
    "from",
    "india",
    "prof",
    "professor",
}


class ValidationReport(BaseModel):
    grounding_score: float = 1.0
    extraction_failed: bool = False
    json_repaired: bool = False
    flags: List[str] = Field(default_factory=list)
    checked_items: int = 0
    verified_items: int = 0
    employment_modified: bool = False


class ValidationService:
    """
    Deterministic anti-hallucination validation & grounding layer.
    Sanitizes LLM placeholders, validates dates/emails/durations, deduplicates entries,
    and cross-checks extracted claims against raw source text without inventing facts.
    """

    @staticmethod
    def _clean_placeholder(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        if not s or s.lower() in _PLACEHOLDER_STRINGS:
            return None
        return s

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())

    @classmethod
    def _significant_tokens(cls, text: str) -> List[str]:
        norm = cls._normalize_text(text)
        return [t for t in norm.split() if len(t) >= 3 and t not in _STOPWORDS]

    @classmethod
    def _is_grounded(cls, query: str, norm_source: str, min_overlap: float = 0.40) -> bool:
        if not query or not norm_source:
            return False
        norm_query = cls._normalize_text(query)
        if not norm_query:
            return False
        if norm_query in norm_source:
            return True
        tokens = cls._significant_tokens(query)
        if not tokens:
            raw_words = [w for w in norm_query.split() if len(w) >= 2]
            if not raw_words:
                return True
            matched = sum(1 for w in raw_words if re.search(rf"\b{re.escape(w)}\b", norm_source))
            return (matched / len(raw_words)) >= min_overlap

        matched = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", norm_source))
        return (matched / len(tokens)) >= min_overlap

    @classmethod
    def validate_and_clean(
        cls,
        profile: ResumeProfile,
        raw_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        meta = extraction_meta or {}
        extraction_method = str(meta.get("_extraction_method") or "groq_text")
        json_repaired = bool(meta.get("_json_repaired", False))
        flags: List[str] = []

        if extraction_method == "failed":
            err = meta.get("_extraction_error") or "Extraction failed"
            flags.append(f"Document extraction failed: {err}")
            return ValidationReport(
                grounding_score=0.0,
                extraction_failed=True,
                json_repaired=False,
                flags=flags,
            )

        if json_repaired:
            flags.append("LLM JSON response was truncated and partially repaired — manual verification recommended")

        # 1. Clean placeholder scalar fields
        profile.email = cls._clean_placeholder(profile.email)
        profile.phone = cls._clean_placeholder(profile.phone)
        profile.location = cls._clean_placeholder(profile.location)
        profile.current_designation = cls._clean_placeholder(profile.current_designation)
        profile.summary = cls._clean_placeholder(profile.summary)

        # 2. Validate email syntax
        if profile.email and not _EMAIL_RE.match(profile.email):
            flags.append(f"Removed malformed email extracted by parser: '{profile.email}'")
            profile.email = None

        # 3. Validate years, clean placeholders & deduplicate education
        max_year = datetime.now().year + 2
        seen_edu = set()
        deduped_edu = []
        for edu in profile.education:
            edu.field = cls._clean_placeholder(edu.field)
            edu.evidence = cls._clean_placeholder(edu.evidence)
            if edu.graduation_year is not None:
                try:
                    gy = int(edu.graduation_year)
                    if gy < 1950 or gy > max_year:
                        flags.append(f"Removed out-of-range graduation year ({gy}) for {edu.degree}")
                        edu.graduation_year = None
                    else:
                        edu.graduation_year = gy
                except (ValueError, TypeError):
                    edu.graduation_year = None

            dedup_key = (
                (edu.normalized_degree or "").strip().lower(),
                (edu.institution_normalized or edu.institution or "").strip().lower(),
                edu.graduation_year,
            )
            if dedup_key not in seen_edu:
                seen_edu.add(dedup_key)
                deduped_edu.append(edu)

        profile.education = EducationService.sort_by_highest_degree(deduped_edu)

        # 4. Validate, clean & deduplicate publications
        seen_pubs = set()
        deduped_pubs = []
        for pub in profile.research.publications:
            pub.evidence = cls._clean_placeholder(pub.evidence)
            pub.venue = cls._clean_placeholder(pub.venue)
            if pub.year is not None:
                try:
                    py = int(pub.year)
                    if py < 1950 or py > max_year:
                        flags.append(f"Removed out-of-range publication year ({py}) for '{pub.title[:40]}'")
                        pub.year = None
                    else:
                        pub.year = py
                except (ValueError, TypeError):
                    pub.year = None

            pub_key = cls._normalize_text(pub.title)
            if pub_key not in seen_pubs:
                seen_pubs.add(pub_key)
                deduped_pubs.append(pub)
        profile.research.publications = deduped_pubs

        # 5. Clean, clamp & deduplicate employment records
        seen_emp = set()
        deduped_emp = []
        orig_emp_count = len(profile.employment)
        for emp in profile.employment:
            emp.evidence = cls._clean_placeholder(emp.evidence)
            emp.description = cls._clean_placeholder(emp.description)
            if emp.duration_years < 0.0:
                flags.append(f"Clamped negative employment duration ({emp.duration_years} yrs) for '{emp.title}'")
                emp.duration_years = 0.0
            elif emp.duration_years > 50.0:
                flags.append(f"Implausible employment duration ({emp.duration_years} yrs) for '{emp.title}'")

            emp_key = (
                (emp.title or "").strip().lower(),
                (emp.organization or "").strip().lower(),
                (emp.start_date or "").strip().lower(),
                (emp.end_date or "").strip().lower(),
            )
            if emp_key not in seen_emp:
                seen_emp.add(emp_key)
                deduped_emp.append(emp)
        profile.employment = deduped_emp
        employment_modified = len(deduped_emp) != orig_emp_count

        # Clean source_evidence placeholders & deduplicate courses/highlights
        for ev in profile.source_evidence:
            ev.evidence = cls._clean_placeholder(ev.evidence) or ""
        for edu in profile.education:
            edu.thesis_title = cls._clean_placeholder(edu.thesis_title)
            edu.advisor = cls._clean_placeholder(edu.advisor)
            edu.gpa_or_honors = cls._clean_placeholder(edu.gpa_or_honors)
        for crs in profile.courses_taught:
            crs.evidence = cls._clean_placeholder(crs.evidence)
            crs.course_code = cls._clean_placeholder(crs.course_code)
            crs.institution = cls._clean_placeholder(crs.institution)

        # Deduplicate courses_taught by normalized course name
        seen_courses = set()
        deduped_courses = []
        for crs in profile.courses_taught:
            ckey = cls._normalize_text(crs.course_name)
            if ckey and ckey not in seen_courses:
                seen_courses.add(ckey)
                deduped_courses.append(crs)
        profile.courses_taught = deduped_courses

        # 6. Deterministic Grounding Check against embedded source text
        checked = 0
        verified = 0
        has_text_layer = len(raw_text.strip()) >= 100

        if has_text_layer and extraction_method != "mock":
            norm_source = cls._normalize_text(raw_text)
            raw_lower = raw_text.lower()
            raw_compact = re.sub(r"\s+", "", raw_lower)

            if profile.email:
                checked += 1
                email_l = profile.email.lower()
                if email_l in raw_lower or email_l in raw_compact:
                    verified += 1
                else:
                    flags.append(f"Removed unverified email not found in source document: {profile.email}")
                    profile.email = None

            for edu in profile.education:
                checked += 1
                inst_ok = cls._is_grounded(edu.institution, norm_source, min_overlap=0.40)
                deg_ok = cls._is_grounded(edu.degree, norm_source, min_overlap=0.40)
                if inst_ok or deg_ok:
                    verified += 1
                else:
                    edu.confidence = round(min(edu.confidence, 0.50), 2)
                    flags.append(f"Education entry not grounded in source text: {edu.degree} ({edu.institution})")

                if edu.evidence and len(cls._significant_tokens(edu.evidence)) >= 3:
                    if not cls._is_grounded(edu.evidence, norm_source, min_overlap=0.45):
                        flags.append(f"Education quote not matched verbatim in source text for {edu.degree}")

            for emp in profile.employment:
                checked += 1
                if cls._is_grounded(f"{emp.organization} {emp.title}", norm_source, min_overlap=0.35):
                    verified += 1
                else:
                    flags.append(f"Employment entry not grounded in source text: {emp.title} at {emp.organization}")

            for pub in profile.research.publications:
                checked += 1
                if cls._is_grounded(pub.title, norm_source, min_overlap=0.45):
                    verified += 1
                else:
                    flags.append(f"Publication not grounded in source text: {pub.title[:60]}")

            for ev in profile.source_evidence:
                if ev.evidence and len(cls._significant_tokens(ev.evidence)) >= 3:
                    if not cls._is_grounded(ev.evidence, norm_source, min_overlap=0.40):
                        flags.append(f"Source evidence quote for '{ev.field}' not matched in source text")

            grounded_courses = []
            for crs in profile.courses_taught:
                if cls._is_grounded(crs.course_name, norm_source, min_overlap=0.40):
                    grounded_courses.append(crs)
                else:
                    flags.append(f"Removed unverified course not found in source text: {crs.course_name}")
            profile.courses_taught = grounded_courses

            grounded_highlights = []
            for hl in profile.notable_highlights:
                if cls._is_grounded(f"{hl.title} {hl.evidence or ''}", norm_source, min_overlap=0.35):
                    grounded_highlights.append(hl)
                else:
                    flags.append(f"Removed unverified highlight not grounded in source text: {hl.title}")
            profile.notable_highlights = grounded_highlights

            for edu in profile.education:
                if edu.thesis_title and not cls._is_grounded(edu.thesis_title, norm_source, min_overlap=0.40):
                    flags.append(f"Removed unverified thesis title for {edu.degree}")
                    edu.thesis_title = None

            if checked == 0:
                grounding_score = 0.50
                flags.append("Text-rich document yielded zero verifiable claims — manual verification required")
            else:
                grounding_score = round(verified / checked, 2)
                if grounding_score < 0.75:
                    flags.append(f"Low source text grounding score ({int(grounding_score * 100)}%) — manual verification required")
        elif not has_text_layer and extraction_method == "groq_vision":
            grounding_score = 0.80
            flags.append("Scanned/image document extracted via vision OCR (no embedded text layer)")
        else:
            grounding_score = 1.0

        return ValidationReport(
            grounding_score=grounding_score,
            extraction_failed=False,
            json_repaired=json_repaired,
            flags=flags,
            checked_items=checked,
            verified_items=verified,
            employment_modified=employment_modified,
        )
