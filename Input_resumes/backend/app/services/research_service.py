import re
from typing import List, Dict, Any, Optional
from backend.app.schemas.resume import PublicationEntry, ResearchProfile

class ResearchService:
    """
    Normalizes research records, publication metrics, DOIs, venues, and research domains.
    """

    DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)
    YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")

    KNOWN_INDEXES = {
        "scopus": "Scopus",
        "sci": "SCI / SCIE",
        "ieee": "IEEE Xplore",
        "acm": "ACM Digital Library",
        "springer": "Springer",
        "elsevier": "Elsevier",
        "nature": "Nature",
        "wiley": "Wiley",
        "pubmed": "PubMed"
    }

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
        lower = text.lower()
        matched = []
        for key, name in cls.KNOWN_INDEXES.items():
            if key in lower:
                matched.append(name)
        return ", ".join(matched) if matched else "Peer-Reviewed"

    @classmethod
    def clean_publication(cls, raw: Dict[str, Any]) -> PublicationEntry:
        title = raw.get("title", "").strip() or "Untitled Publication"
        venue = raw.get("venue") or raw.get("journal") or raw.get("conference")
        year = raw.get("year")
        doi = raw.get("doi") or cls.extract_doi(f"{title} {venue or ''}")

        if not year and venue:
            year_match = cls.YEAR_PATTERN.search(venue)
            if year_match:
                year = int(year_match.group(1))

        evidence = raw.get("evidence") or f"{title}. {venue or ''} ({year or ''})"

        indexing = raw.get("indexed") or cls.detect_indexing(f"{title} {venue or ''}")

        return PublicationEntry(
            title=title,
            venue=venue,
            year=year,
            doi=doi,
            citation_count=raw.get("citation_count"),
            indexed=indexing,
            evidence=evidence
        )

    @classmethod
    def process_research_profile(cls, raw_data: Dict[str, Any]) -> ResearchProfile:
        raw_pubs = raw_data.get("publications", [])
        cleaned_pubs = []
        for p in raw_pubs:
            if isinstance(p, dict):
                cleaned_pubs.append(cls.clean_publication(p))
            elif isinstance(p, str):
                cleaned_pubs.append(cls.clean_publication({"title": p}))

        patents = raw_data.get("patents", [])
        projects = raw_data.get("research_projects", [])
        domains = raw_data.get("research_domains", [])
        books = raw_data.get("books", [])

        return ResearchProfile(
            publications=cleaned_pubs,
            patents=patents,
            research_projects=projects,
            research_domains=domains,
            books=books
        )
