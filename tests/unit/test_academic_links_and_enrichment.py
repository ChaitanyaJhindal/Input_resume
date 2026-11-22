import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.schemas.resume import (
    AcademicLink,
    PublicationEntry,
    ResearchProfile,
    ResumeProfile,
)
from backend.app.services.academic_profile_service import AcademicProfileService
from backend.app.utils.link_extractor import extract_academic_links, is_valid_orcid


def test_orcid_checksum_and_canonical_link_extraction(tmp_path: Path):
    assert is_valid_orcid("0000-0001-6233-6720") is True
    assert is_valid_orcid("0009-0002-6452-0390") is True
    assert is_valid_orcid("0000-0001-6233-6729") is False

    # Build a synthetic PDF with compressed /URI link annotation inside FlateDecode stream
    uri_stream = zlib.compress(b"1 0 obj << /S /URI /URI (https://scholar.google.co.in/citations?user=kLIQjKsAAAAJ&hl=en) >> endobj")
    pdf_bytes = (
        b"%PDF-1.4\nstream\n" + uri_stream + b"\nendstream\n"
        b"2 0 obj << /URI (https://github.com/prof-tester) >> endobj\n"
    )
    pdf_file = tmp_path / "links_test.pdf"
    pdf_file.write_bytes(pdf_bytes)

    raw_text = (
        "ORCID ID: 0000-0001-6233-6720\n"
        "Scopus Author ID: 57192345678\n"
        "Profile: https://www.linkedin.com/in/prof-tester-ai\n"
    )
    links = extract_academic_links(pdf_file, raw_text)
    by_platform = {lnk.platform: lnk for lnk in links}

    assert "google_scholar" in by_platform
    assert by_platform["google_scholar"].identifier == "kLIQjKsAAAAJ"
    assert by_platform["google_scholar"].url == "https://scholar.google.com/citations?user=kLIQjKsAAAAJ"
    assert by_platform["google_scholar"].source == "pdf_annotation"

    assert "orcid" in by_platform
    assert by_platform["orcid"].verified is True
    assert by_platform["orcid"].identifier == "0000-0001-6233-6720"

    assert "scopus" in by_platform
    assert by_platform["scopus"].identifier == "57192345678"

    assert "github" in by_platform
    assert by_platform["github"].source == "pdf_annotation"
    assert "linkedin" in by_platform


def test_academic_profile_service_orcid_exact_and_doi_fallback():
    svc = AcademicProfileService()
    profile = ResumeProfile(
        candidate_id="cand_ext_1",
        name="Dr. Jane Researcher",
        academic_links=[
            AcademicLink(
                platform="orcid",
                url="https://orcid.org/0000-0001-6233-6720",
                identifier="0000-0001-6233-6720",
                source="cv_text",
                verified=True,
            )
        ],
    )

    class MockClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url, **_kwargs):
            if "pub.orcid.org" in url:
                return SimpleNamespace(status_code=200, json=lambda: {"orcid-identifier": {"path": "0000-0001-6233-6720"}})
            if "api.openalex.org/authors/https://orcid.org/" in url:
                return SimpleNamespace(
                    status_code=200,
                    json=lambda: {
                        "id": "https://openalex.org/A5001234567",
                        "cited_by_count": 412,
                        "works_count": 28,
                        "summary_stats": {"h_index": 11, "i10_index": 12},
                    },
                )
            return SimpleNamespace(status_code=404, json=lambda: {})

    with patch("backend.app.services.academic_profile_service.httpx.Client", MockClient):
        ver = svc.enrich_profile(profile)

    assert ver.orcid_verified is True
    assert ver.match_method == "orcid_exact"
    assert ver.citation_count == 412
    assert ver.h_index == 11
    assert ver.works_count == 28

    # DOI fallback when ORCID is absent
    doi_profile = ResumeProfile(
        candidate_id="cand_ext_2",
        name="Dr. Alan Researcher",
        research=ResearchProfile(
            publications=[PublicationEntry(title="Test Paper", doi="10.1109/TEST.2023.12345")]
        ),
    )

    class MockDoiClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url, **_kwargs):
            if "api.openalex.org/works/https://doi.org/" in url:
                return SimpleNamespace(
                    status_code=200,
                    json=lambda: {
                        "authorships": [
                            {"author": {"id": "https://openalex.org/A999", "display_name": "Alan Researcher"}}
                        ]
                    },
                )
            if url.endswith("/A999"):
                return SimpleNamespace(
                    status_code=200,
                    json=lambda: {
                        "id": "https://openalex.org/A999",
                        "cited_by_count": 88,
                        "works_count": 9,
                        "summary_stats": {"h_index": 5, "i10_index": 3},
                    },
                )
            return SimpleNamespace(status_code=404, json=lambda: {})

    with patch("backend.app.services.academic_profile_service.httpx.Client", MockDoiClient):
        ver2 = svc.enrich_profile(doi_profile)

    assert ver2.match_method == "doi_verified"
    assert ver2.citation_count == 88
    assert ver2.h_index == 5


def test_academic_profile_service_handles_offline_gracefully():
    svc = AcademicProfileService()
    profile = ResumeProfile(
        candidate_id="cand_ext_offline",
        name="Dr. Offline",
        academic_links=[AcademicLink(platform="google_scholar", url="https://scholar.google.com/citations?user=abc")],
    )

    class OfflineClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, *_args, **_kwargs):
            raise TimeoutError("Network disabled")

    with patch("backend.app.services.academic_profile_service.httpx.Client", OfflineClient):
        ver = svc.enrich_profile(profile)

    assert ver.match_method == "link_only"
    assert ver.citation_count is None
    assert ver.h_index is None
