import re
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from backend.app.schemas.resume import AcademicLink

_URL_RE = re.compile(r"https?://[^\s<>\"'\]\)>,;]+", re.IGNORECASE)
_PDF_URI_RE = re.compile(rb"/URI\s*\(([^)]{4,500})\)")
_ORCID_RAW_RE = re.compile(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b", re.IGNORECASE)
_ORCID_LABELED_RE = re.compile(r"orcid(?:\s*id|\s*no\.?|\s*#)?\s*[:\-]?\s*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE)
_SCOPUS_LABELED_RE = re.compile(r"scopus(?:\s*author)?\s*id\s*[:\-]?\s*(\d{8,14})", re.IGNORECASE)
_STREAM_RE = re.compile(rb"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)


def is_valid_orcid(orcid_id: str) -> bool:
    """Verify ORCID 16-char ISO 7064 Mod 11-2 checksum."""
    digits = re.sub(r"[^0-9X]", "", str(orcid_id or "").upper())
    if len(digits) != 16:
        return False
    total = 0
    for ch in digits[:-1]:
        if not ch.isdigit():
            return False
        total = (total + int(ch)) * 2
    rem = total % 11
    check = (12 - rem) % 11
    expected = "X" if check == 10 else str(check)
    return digits[-1] == expected


def _extract_pdf_uri_annotations(pdf_path: Path) -> List[str]:
    """Scan uncompressed & FlateDecode PDF streams for embedded /URI (...) link annotations."""
    urls: List[str] = []
    try:
        raw_bytes = pdf_path.read_bytes()
    except Exception:
        return urls

    def _collect(blob: bytes) -> None:
        for m in _PDF_URI_RE.finditer(blob):
            try:
                uri = m.group(1).decode("utf-8", errors="ignore").replace("\\(", "(").replace("\\)", ")").strip()
                if uri.lower().startswith(("http://", "https://")):
                    urls.append(uri)
            except Exception:
                pass

    _collect(raw_bytes)
    for sm in _STREAM_RE.finditer(raw_bytes):
        chunk = sm.group(1)
        if b"/URI" in chunk:
            _collect(chunk)
        else:
            try:
                dec = zlib.decompress(chunk)
                if b"/URI" in dec:
                    _collect(dec)
            except Exception:
                pass
    return urls


def _classify_url(raw_url: str, source: str) -> Optional[AcademicLink]:
    cleaned = raw_url.strip().rstrip(".,;:)")
    try:
        parsed = urlparse(cleaned)
    except Exception:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    path = parsed.path or ""

    if "scholar.google." in host:
        qs = parse_qs(parsed.query)
        user_vals = qs.get("user")
        if user_vals and user_vals[0]:
            uid = user_vals[0].strip()
            canon = f"https://scholar.google.com/citations?user={uid}"
            return AcademicLink(platform="google_scholar", url=canon, identifier=uid, source=source)
        return AcademicLink(platform="google_scholar", url=cleaned, identifier=None, source=source)

    if "orcid.org" in host:
        m = _ORCID_RAW_RE.search(path)
        if m:
            oid = m.group(1).upper()
            valid = is_valid_orcid(oid)
            return AcademicLink(
                platform="orcid",
                url=f"https://orcid.org/{oid}",
                identifier=oid,
                source=source,
                verified=valid,
            )

    if "scopus.com" in host:
        qs = parse_qs(parsed.query)
        aid = (qs.get("authorId") or qs.get("authorid") or [None])[0]
        return AcademicLink(platform="scopus", url=cleaned, identifier=aid, source=source)

    if "linkedin.com" in host and ("/in/" in path.lower() or "/pub/" in path.lower()):
        slug = path.strip("/").split("/")[-1] if path.strip("/") else None
        return AcademicLink(platform="linkedin", url=cleaned, identifier=slug, source=source)

    if "github.com" in host:
        parts = [p for p in path.split("/") if p]
        ident = parts[0] if parts else None
        return AcademicLink(platform="github", url=cleaned, identifier=ident, source=source)

    if "researchgate.net" in host:
        return AcademicLink(platform="researchgate", url=cleaned, source=source)

    if "dblp.org" in host:
        return AcademicLink(platform="dblp", url=cleaned, source=source)

    if "ssrn.com" in host or "webofscience.com" in host or "clarivate.com" in host or "publons.com" in host:
        return AcademicLink(platform="researcherid" if "publons" in host or "clarivate" in host or "webofscience" in host else "ssrn", url=cleaned, source=source)

    # Generic faculty/personal site only if non-publisher (skip doi.org/ieee.org/springer paper links)
    skip_domains = {
        "doi.org", "dx.doi.org", "ieeexplore.ieee.org", "dl.acm.org",
        "link.springer.com", "sciencedirect.com", "arxiv.org", "nature.com",
        "onlinelibrary.wiley.com", "w3.org", "schemas.openxmlformats.org",
    }
    if any(sd in host for sd in skip_domains):
        return None
    if ".edu" in host or ".ac." in host or "sites.google.com" in host:
        return AcademicLink(platform="website", url=cleaned, source=source)

    return None


def extract_academic_links(file_path: Optional[Path], raw_text: str = "") -> List[AcademicLink]:
    """
    Deterministically extracts, validates, and canonicalizes academic profile links
    (Google Scholar, ORCID, Scopus, LinkedIn, GitHub, DBLP, etc.) from both PDF
    embedded hyperlink annotations and plain CV text.
    """
    candidates: List[Tuple[str, str]] = []
    if file_path and file_path.exists() and file_path.suffix.lower() == ".pdf":
        for uri in _extract_pdf_uri_annotations(file_path):
            candidates.append((uri, "pdf_annotation"))

    for m in _URL_RE.finditer(raw_text or ""):
        candidates.append((m.group(0), "cv_text"))

    by_key: Dict[Tuple[str, str], AcademicLink] = {}

    for url, src in candidates:
        link = _classify_url(url, src)
        if not link:
            continue
        dedup_key = (link.platform, (link.identifier or link.url).lower())
        if dedup_key not in by_key:
            by_key[dedup_key] = link
        elif src == "pdf_annotation" and by_key[dedup_key].source != "pdf_annotation":
            by_key[dedup_key] = link

    # Detect labeled plain-text ORCID / Scopus IDs written without full URL
    if raw_text:
        for m in _ORCID_LABELED_RE.finditer(raw_text):
            oid = m.group(1).upper()
            dedup_key = ("orcid", oid.lower())
            if dedup_key not in by_key:
                by_key[dedup_key] = AcademicLink(
                    platform="orcid",
                    url=f"https://orcid.org/{oid}",
                    identifier=oid,
                    source="cv_text",
                    verified=is_valid_orcid(oid),
                )

        for m in _SCOPUS_LABELED_RE.finditer(raw_text):
            aid = m.group(1).strip()
            dedup_key = ("scopus", aid.lower())
            if dedup_key not in by_key:
                by_key[dedup_key] = AcademicLink(
                    platform="scopus",
                    url=f"https://www.scopus.com/authid/detail.uri?authorId={aid}",
                    identifier=aid,
                    source="cv_text",
                )

    priority_order = {
        "google_scholar": 0,
        "orcid": 1,
        "scopus": 2,
        "dblp": 3,
        "researchgate": 4,
        "linkedin": 5,
        "github": 6,
        "website": 7,
    }
    return sorted(by_key.values(), key=lambda x: (priority_order.get(x.platform, 9), x.url))
