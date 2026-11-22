import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.schemas.resume import PublicationEntry, ResearchProfile
from backend.app.utils.json_utils import safe_int, safe_str_list, safe_dict_list


class ResearchService:
    """
    Normalizes research records, publication metrics, DOIs, venues, and research domains.
    Uses word-boundary matching for indexing detection and deduplicates publications cleanly.
    """

    DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)
    YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")

    KNOWN_INDEX_PATTERNS = [
        (re.compile(r"\bscopus\b", re.IGNORECASE), "Scopus"),
        (re.compile(r"\b(?:sci|scie)\b", re.IGNORECASE), "SCI / SCIE"),
        (re.compile(r"\bieee\b", re.IGNORECASE), "IEEE Xplore"),
        (re.compile(r"\bacm\b", re.IGNORECASE), "ACM Digital Library"),
        (re.compile(r"\bspringer\b", re.IGNORECASE), "Springer"),
        (re.compile(r"\belsevier\b", re.IGNORECASE), "Elsevier"),
        (re.compile(r"\bnature\b", re.IGNORECASE), "Nature"),
        (re.compile(r"\bwiley\b", re.IGNORECASE), "Wiley"),
        (re.compile(r"\bpubmed\b", re.IGNORECASE), "PubMed"),
    ]

    @classmethod
    def extract_doi(cls, text: str) -> Optional[str]:
        if not text:
            return None
        match = cls.DOI_PATTERN.search(text)
        return match.group(0) if match else None

    @classmethod
    def detect_indexing(cls, text: str) -> Optional[str]:
        if not text:
            return None
        matched: List[str] = []
        for pattern, name in cls.KNOWN_INDEX_PATTERNS:
            if pattern.search(text) and name not in matched:
                matched.append(name)
        return ", ".join(matched) if matched else "Peer-Reviewed"

    @classmethod
    def clean_publication(cls, raw: Dict[str, Any]) -> PublicationEntry:
        title = str(raw.get("title") or "").strip() or "Untitled Publication"
        venue_raw = raw.get("venue") or raw.get("journal") or raw.get("conference")
        venue = str(venue_raw).strip() if venue_raw is not None and str(venue_raw).strip() else None

        max_year = datetime.now().year + 2
        y_val = safe_int(raw.get("year"))
        year: Optional[int] = y_val if (y_val is not None and 1950 <= y_val <= max_year) else None

        doi_raw = raw.get("doi")
        doi = str(doi_raw).strip() if doi_raw and str(doi_raw).strip() else cls.extract_doi(f"{title} {venue or ''}")

        if not year and venue:
            year_match = cls.YEAR_PATTERN.search(venue)
            if year_match:
                cand_y = int(year_match.group(1))
                if 1950 <= cand_y <= max_year:
                    year = cand_y

        evidence_raw = raw.get("evidence")
        evidence = str(evidence_raw).strip() if evidence_raw and str(evidence_raw).strip() else None

        raw_idx = raw.get("indexed")
        indexing = (
            str(raw_idx).strip()
            if raw_idx and str(raw_idx).strip()
            else cls.detect_indexing(f"{title} {venue or ''}")
        )

        citation_count = safe_int(raw.get("citation_count"))

        return PublicationEntry(
            title=title,
            venue=venue,
            year=year,
            doi=doi,
            citation_count=citation_count,
            indexed=indexing,
            evidence=evidence,
        )

    @classmethod
    def process_research_profile(cls, raw_data: Any) -> ResearchProfile:
        data = raw_data if isinstance(raw_data, dict) else {}
        raw_pubs = data.get("publications")
        cleaned_pubs: List[PublicationEntry] = []
        seen_titles = set()

        if isinstance(raw_pubs, list):
            for p in raw_pubs:
                if isinstance(p, dict):
                    entry = cls.clean_publication(p)
                elif isinstance(p, str) and p.strip():
                    entry = cls.clean_publication({"title": p})
                else:
                    continue

                norm_title = re.sub(r"[^a-z0-9]+", " ", entry.title.lower()).strip()
                if norm_title and norm_title not in seen_titles:
                    seen_titles.add(norm_title)
                    cleaned_pubs.append(entry)

        return ResearchProfile(
            publications=cleaned_pubs,
            patents=safe_dict_list(data.get("patents")),
            research_projects=safe_dict_list(data.get("research_projects")),
            research_domains=safe_str_list(data.get("research_domains")),
            books=safe_dict_list(data.get("books")),
        )
