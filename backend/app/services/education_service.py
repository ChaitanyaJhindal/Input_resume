import re
from typing import Any, List, Optional, Tuple


class EducationService:
    DEGREE_RANK = {
        "Postdoctoral": 7,
        "PhD / Doctorate": 6,
        "PhD (In Progress)": 5,
        "Postgraduate / Masters": 4,
        "Undergraduate": 3,
        "Diploma": 2,
        "Certification": 1,
        "Other": 0,
    }

    _POSTDOC_RE = re.compile(r"\bpost[\s-]?doc(?:toral)?\b", re.IGNORECASE)
    _PHD_RE = re.compile(
        r"\b(?:"
        r"ph\.?\s*d\.?|"
        r"doctor\s+of\s+philosophy|"
        r"d\.?\s*phil\.?|"
        r"doctorate|"
        r"d\.?\s*sc\.?|"
        r"doctor\s+of\s+business\s+administration|"
        r"d\.?\s*b\.?\s*a\.?|"
        r"ed\.?\s*d\.?|"
        r"fellow\s+programme\s+in\s+management|"
        r"fpm|"
        r"fellowship\s+in\s+management|"
        r"fellow\s+in\s+management"
        r")\b",
        re.IGNORECASE,
    )
    _PHD_IN_PROGRESS_RE = re.compile(
        r"\b(?:abd|candidate|pursuing|expected|in\s+progress|ongoing|enrolled|visiting\s+ph\.?\s*d\.?)\b",
        re.IGNORECASE,
    )
    _SCHOOL_RE = re.compile(
        r"\b(?:10th|12th|high\s+school|intermediate|matriculation|ssc|hsc|senior\s+secondary)\b",
        re.IGNORECASE,
    )
    _MASTERS_RE = re.compile(
        r"\b(?:"
        r"m\.?\s*tech|mtech|"
        r"m\.?\s*phil\.?|mphil|"
        r"m\.?\s*sc\.?|msc|"
        r"m\.?\s*com\.?|mcom|"
        r"m\.?\s*b\.?\s*a\.?|mba|"
        r"m\.?\s*c\.?\s*a\.?|mca|"
        r"ll\.?\s*m\.?|llm|"
        r"m\.?\s*ed\.?|m\.?\s*des\.?|"
        r"m\.?\s*e\.?(?!\w)|"
        r"m\.?\s*s\.?(?!\w)|"
        r"m\.?\s*a\.?(?!\w)|"
        r"masters?|master(?:'s)?|"
        r"post\s*graduate|postgraduate|"
        r"executive\s+management\s+program|executive\s+program|executive\s+mba|"
        r"executive\s+pgdm|pgdm|advanced\s+studies"
        r")\b",
        re.IGNORECASE,
    )
    _UG_RE = re.compile(
        r"\b(?:"
        r"b\.?\s*tech|btech|"
        r"b\.?\s*eng|beng|"
        r"b\.?\s*sc\.?|bsc|"
        r"b\.?\s*com\.?|bcom|"
        r"b\.?\s*b\.?\s*a\.?|bba|"
        r"b\.?\s*b\.?\s*m\.?|bbm|"
        r"b\.?\s*c\.?\s*a\.?|bca|"
        r"b\.?\s*arch\.?|"
        r"b\.?\s*e\.?(?!\w)|"
        r"b\.?\s*s\.?(?!\w)|"
        r"b\.?\s*a\.?(?!\w)|"
        r"bachelor\w*|undergraduate|ll\.?\s*b\.?|llb|b\.?\s*ed\.?|mbbs|blis"
        r")\b",
        re.IGNORECASE,
    )
    _DIPLOMA_RE = re.compile(r"\b(?:diploma|pgd|pgdba|pgdbm|polytechnic)\b", re.IGNORECASE)
    _CERT_RE = re.compile(
        r"\b(?:certificate|certification|certified|pgchrm|course|bootcamp|specialization|training|program|programme)\b",
        re.IGNORECASE,
    )

    @classmethod
    def sort_by_highest_degree(cls, entries: List[Any]) -> List[Any]:
        """Sort education entries from highest academic rank to lowest."""
        return sorted(
            entries,
            key=lambda e: (
                cls.DEGREE_RANK.get(getattr(e, "normalized_degree", "Other"), 0),
                getattr(e, "graduation_year", None) or 0,
                getattr(e, "confidence", 0.0) or 0.0,
            ),
            reverse=True,
        )

    @classmethod
    def select_highest_education(cls, entries: List[Any]) -> Optional[Any]:
        """Return the highest-ranked education entry regardless of input list order."""
        if not entries:
            return None
        return cls.sort_by_highest_degree(entries)[0]

    @classmethod
    def normalize_degree(cls, raw_degree: str) -> Tuple[str, float]:
        """
        Classifies degree title into the standard taxonomy using word-boundary patterns:
        - Postdoctoral
        - PhD / Doctorate
        - PhD (In Progress)
        - Postgraduate / Masters
        - Undergraduate
        - Diploma
        - Certification
        - Other

        Returns: (normalized_degree, confidence)
        """
        if not raw_degree or not str(raw_degree).strip():
            return "Other", 0.0

        deg = str(raw_degree).strip()

        if cls._POSTDOC_RE.search(deg):
            return "Postdoctoral", 0.98

        if cls._PHD_RE.search(deg):
            if cls._PHD_IN_PROGRESS_RE.search(deg):
                return "PhD (In Progress)", 0.92
            return "PhD / Doctorate", 0.99

        if cls._SCHOOL_RE.search(deg):
            return "Other", 0.95

        if cls._MASTERS_RE.search(deg):
            return "Postgraduate / Masters", 0.95

        if cls._UG_RE.search(deg):
            return "Undergraduate", 0.95

        if cls._DIPLOMA_RE.search(deg):
            return "Diploma", 0.90

        if cls._CERT_RE.search(deg):
            return "Certification", 0.90

        return "Other", 0.50


education_service = EducationService()
