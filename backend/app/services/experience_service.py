import re
from datetime import datetime
from typing import List, Tuple, Optional
from backend.app.schemas.resume import EmploymentEntry, ExperienceBreakdown


class ExperienceService:
    """
    Deterministic experience calculation service.
    Separates teaching, research, industry, and administrative experience.
    Normalizes dates (including numeric MM/YYYY, YYYY-MM, 2-digit years, and is_current),
    computes precise durations, and merges overlapping intervals cleanly.
    """

    TEACHING_KEYWORDS = [
        "professor", "assistant professor", "associate professor", "asst professor",
        "asst. professor", "assoc professor", "assoc. professor", "asst prof",
        "asst. prof", "assoc prof", "assoc. prof", "prof.", "prof",
        "lecturer", "senior lecturer", "sr. lecturer", "faculty", "faculty fellow",
        "instructor", "course instructor", "module instructor", "teacher",
        "teaching assistant", "teaching fellow", "guest faculty", "guest lecturer",
        "adjunct", "visiting professor", "visiting faculty", "visiting lecturer",
        "reader", "tutor", "pedagogy",
        "academician", "academic fellow", "educator", "professor of practice",
        "academic instructor", "teaching associate", "graduate teaching assistant",
    ]

    RESEARCH_KEYWORDS = [
        "postdoc", "postdoctoral", "fellow", "researcher", "research associate",
        "research assistant", "scientist", "principal investigator", "phd scholar",
        "jrf", "srf", "project fellow", "research fellow", "post-doctoral",
        "visiting scholar", "doctoral researcher",
    ]

    ADMINISTRATIVE_KEYWORDS = [
        "dean", "director", "head of department", "hod", "principal", "registrar",
        "coordinator", "warden", "controller of examinations", "proctor", "chairperson",
        "placement manager", "director of placements", "chief manager", "placement",
        "placements", "corporate relations", "training & placement", "training and placement",
        "placement officer", "admissions", "academic administrator", "executive - hr", "hr executive",
    ]

    ACADEMIC_ORG_KEYWORDS = [
        "university", "college", "institute", "iit", "nit", "iiit", "iisc",
        "school", "academy", "polytechnic", "campus", "department of",
    ]

    INDUSTRY_KEYWORDS = [
        "software engineer", "developer", "programmer", "architect", "devops",
        "sde", "consultant", "business analyst", "data analyst", "product manager",
        "project manager", "program manager", "engineering manager", "tech lead",
        "team lead", "qa engineer", "test engineer", "intern", "corporate",
        "solutions architect", "director of engineering", "managing director",
        "chief technology officer", "cto", "ceo", "vp engineering",
    ]

    CURRENT_KEYWORDS = [
        "present", "current", "till date", "to date", "up to date", "ongoing", "now", "continuing",
    ]

    @classmethod
    def _has_any_keyword(cls, text: str, keywords: List[str]) -> bool:
        if not text:
            return False
        lower = text.lower()
        for kw in keywords:
            if re.search(rf"(?<!\w){re.escape(kw.strip())}(?!\w)", lower):
                return True
        return False

    MONTHS_MAP = {
        "jan": 0.0, "january": 0.0,
        "feb": 0.08, "february": 0.08,
        "mar": 0.17, "march": 0.17,
        "apr": 0.25, "april": 0.25,
        "may": 0.33,
        "jun": 0.42, "june": 0.42,
        "jul": 0.50, "july": 0.50,
        "aug": 0.58, "august": 0.58,
        "sep": 0.67, "sept": 0.67, "september": 0.67,
        "oct": 0.75, "october": 0.75,
        "nov": 0.83, "november": 0.83,
        "dec": 0.92, "december": 0.92,
    }

    @classmethod
    def parse_date_decimal(cls, date_str: Optional[str]) -> Optional[float]:
        """
        Parses a date string into a decimal year (e.g., 'July 2021' -> 2021.5, '06/2020' -> 2020.42).
        Handles 'Present' by returning the current decimal year.
        """
        if not date_str:
            return None
        s = str(date_str).strip().lower()
        if not s:
            return None

        if cls._has_any_keyword(s, cls.CURRENT_KEYWORDS):
            now = datetime.now()
            return round(now.year + (now.month - 1) / 12.0, 2)

        # YYYY-MM or YYYY/MM
        iso_ym = re.search(r"\b(19\d\d|20\d\d)[-/.](0?[1-9]|1[0-2])\b", s)
        if iso_ym:
            year_val = int(iso_ym.group(1))
            month_num = int(iso_ym.group(2))
            return round(year_val + (month_num - 1) / 12.0, 2)

        # MM/YYYY or MM-YYYY
        m_yyyy = re.search(r"\b(0?[1-9]|1[0-2])[-/.](19\d\d|20\d\d)\b", s)
        if m_yyyy:
            month_num = int(m_yyyy.group(1))
            year_val = int(m_yyyy.group(2))
            return round(year_val + (month_num - 1) / 12.0, 2)

        # 4-digit year match
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", s)
        if not year_match:
            # Check 2-digit year like 'May-18', 'May-25', '05/22'
            short_year = re.search(r"[-/'\s]([012]\d)\b", s)
            if short_year:
                year_val = 2000 + int(short_year.group(1))
            else:
                return None
        else:
            year_val = int(year_match.group(1))

        month_offset = 0.0
        for m_name, offset in cls.MONTHS_MAP.items():
            if re.search(rf"(?<!\w){re.escape(m_name)}(?!\w)", s):
                month_offset = offset
                break

        return round(year_val + month_offset, 2)

    @classmethod
    def categorize_employment_with_confidence(
        cls, title: str, organization: str = "", description: str = ""
    ) -> Tuple[str, float]:
        """Classify employment category cleanly alongside confidence score."""
        text = f"{title} {organization} {description}"
        title_and_org = f"{title} {organization}"

        if cls._has_any_keyword(text, cls.TEACHING_KEYWORDS):
            return "teaching", 0.95
        if cls._has_any_keyword(text, cls.RESEARCH_KEYWORDS):
            return "research", 0.93

        # Guard corporate executive roles (e.g., "Director of Engineering" at Tech Corp)
        is_industry_role = cls._has_any_keyword(text, cls.INDUSTRY_KEYWORDS)
        is_academic_org = cls._has_any_keyword(title_and_org, cls.ACADEMIC_ORG_KEYWORDS)
        if is_industry_role and not is_academic_org:
            return "industry", 0.92

        if cls._has_any_keyword(text, cls.ADMINISTRATIVE_KEYWORDS):
            return "administrative", 0.92

        if is_industry_role:
            return "industry", 0.90

        return "industry", 0.65

    @classmethod
    def categorize_employment(cls, title: str, organization: str = "", description: str = "") -> str:
        cat, _ = cls.categorize_employment_with_confidence(title, organization, description)
        return cat

    @classmethod
    def parse_date_range(
        cls,
        start_str: Optional[str],
        end_str: Optional[str],
        fallback_duration: float = 0.0,
        is_current: bool = False,
    ) -> Tuple[float, float, float]:
        """
        Parses start and end date representations into decimal years.
        Treats is_current=True with missing end_str as ending at the current date.
        Guarantees end_decimal > start_decimal when dates exist.
        Returns: (start_decimal, end_decimal, duration_years).
        """
        start_dec = cls.parse_date_decimal(start_str)
        end_dec = cls.parse_date_decimal(end_str)

        if end_dec is None and is_current:
            end_dec = cls.parse_date_decimal("present")

        if start_dec is None and end_dec is None:
            dur = max(0.0, fallback_duration)
            return (0.0, 0.0, round(dur, 1))

        if start_dec is None and end_dec is not None:
            dur = max(1.0, fallback_duration)
            return (round(end_dec - dur, 2), end_dec, round(dur, 1))

        if start_dec is not None and end_dec is None:
            dur = max(1.0, fallback_duration)
            return (start_dec, round(start_dec + dur, 2), round(dur, 1))

        assert start_dec is not None and end_dec is not None
        if end_dec <= start_dec:
            dur = max(1.0, fallback_duration)
            end_dec = round(start_dec + dur, 2)
        else:
            dur = round(end_dec - start_dec, 2)
            if dur < 0.25:
                dur = 0.5

        return (start_dec, end_dec, round(dur, 1))

    @classmethod
    def merge_intervals(cls, intervals: List[Tuple[float, float]]) -> float:
        """
        Merges overlapping date intervals [(start, end), ...] to compute true non-overlapping years.
        """
        if not intervals:
            return 0.0

        valid_intervals = [(s, e) for s, e in intervals if e > s]
        if not valid_intervals:
            return 0.0

        sorted_intervals = sorted(valid_intervals, key=lambda x: x[0])
        merged: List[List[float]] = []

        for start, end in sorted_intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        total_years = sum(end - start for start, end in merged)
        return round(total_years, 1)

    @classmethod
    def calculate_experience(cls, employment_entries: List[EmploymentEntry]) -> ExperienceBreakdown:
        """
        Calculates distinct experience totals for teaching, research, industry, and administrative,
        along with non-overlapping total career years.
        """
        teaching_intervals: List[Tuple[float, float]] = []
        research_intervals: List[Tuple[float, float]] = []
        industry_intervals: List[Tuple[float, float]] = []
        admin_intervals: List[Tuple[float, float]] = []
        all_intervals: List[Tuple[float, float]] = []

        unanchored_teaching = 0.0
        unanchored_research = 0.0
        unanchored_industry = 0.0
        unanchored_admin = 0.0

        for entry in employment_entries:
            cat = entry.category.lower().strip() if entry.category else ""
            if cls._has_any_keyword(entry.title, cls.TEACHING_KEYWORDS):
                cat = "teaching"
            elif cls._has_any_keyword(entry.title, cls.RESEARCH_KEYWORDS):
                cat = "research"
            elif cls._has_any_keyword(entry.title, cls.ADMINISTRATIVE_KEYWORDS) and not (
                cls._has_any_keyword(entry.title, cls.INDUSTRY_KEYWORDS)
                and not cls._has_any_keyword(f"{entry.title} {entry.organization}", cls.ACADEMIC_ORG_KEYWORDS)
            ):
                cat = "administrative"
            elif cat not in {"teaching", "research", "industry", "administrative"}:
                cat = cls.categorize_employment(entry.title, entry.organization, entry.description or "")
            elif cat == "industry":
                detected = cls.categorize_employment(entry.title, entry.organization, entry.description or "")
                if detected in {"teaching", "research", "administrative"}:
                    cat = detected

            entry.category = cat

            fallback_dur = float(entry.duration_years) if entry.duration_years and entry.duration_years > 0 else 0.0
            start_dec, end_dec, duration = cls.parse_date_range(
                entry.start_date,
                entry.end_date,
                fallback_dur,
                is_current=bool(entry.is_current),
            )
            entry.duration_years = round(duration, 1)

            if start_dec > 0 and end_dec > start_dec:
                interval = (start_dec, end_dec)
                all_intervals.append(interval)

                if cat == "teaching":
                    teaching_intervals.append(interval)
                elif cat == "research":
                    research_intervals.append(interval)
                elif cat == "administrative":
                    admin_intervals.append(interval)
                else:
                    industry_intervals.append(interval)
            elif duration > 0:
                if cat == "teaching":
                    unanchored_teaching += duration
                elif cat == "research":
                    unanchored_research += duration
                elif cat == "administrative":
                    unanchored_admin += duration
                else:
                    unanchored_industry += duration

        teaching_years = round(cls.merge_intervals(teaching_intervals) + unanchored_teaching, 1)
        research_years = round(cls.merge_intervals(research_intervals) + unanchored_research, 1)
        industry_years = round(cls.merge_intervals(industry_intervals) + unanchored_industry, 1)
        admin_years = round(cls.merge_intervals(admin_intervals) + unanchored_admin, 1)
        total_years = round(
            cls.merge_intervals(all_intervals)
            + unanchored_teaching
            + unanchored_research
            + unanchored_industry
            + unanchored_admin,
            1,
        )

        max_cat = max(teaching_years, research_years, industry_years, admin_years)
        if total_years < max_cat:
            total_years = max_cat

        return ExperienceBreakdown(
            total_years=total_years,
            teaching_years=teaching_years,
            research_years=research_years,
            industry_years=industry_years,
            administrative_years=admin_years,
        )
