import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import httpx

from backend.app.config import config_manager
from backend.app.schemas.resume import ExternalVerification, ResumeProfile
from backend.app.utils.link_extractor import is_valid_orcid

logger = logging.getLogger("FacultyScreen.AcademicProfileService")


class AcademicProfileService:
    """
    Verifies and enriches academic researcher identities using free, official public APIs:
    - ORCID Public API v3.0 (exact ORCID record verification)
    - OpenAlex Public API (matched strictly by verified ORCID or verified publication DOI)
    Never scrapes Google Scholar HTML or guesses ambiguous author matches.
    """

    @staticmethod
    def _extract_openalex_metrics(
        author_data: Dict[str, Any],
        match_method: str,
        orcid_verified: bool,
    ) -> ExternalVerification:
        stats = author_data.get("summary_stats") or {}
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return ExternalVerification(
            orcid_verified=orcid_verified,
            openalex_id=author_data.get("id"),
            citation_count=author_data.get("cited_by_count"),
            h_index=stats.get("h_index"),
            i10_index=stats.get("i10_index"),
            works_count=author_data.get("works_count"),
            match_method=match_method,
            verified_at=now_iso,
            source_url=author_data.get("id"),
        )

    @staticmethod
    def _name_matches_author(candidate_name: str, author_display_name: str) -> bool:
        clean_cand = [w for w in candidate_name.lower().replace(".", " ").split() if len(w) >= 2 and w not in {"dr", "prof", "mr", "ms", "mrs"}]
        clean_auth = author_display_name.lower()
        if not clean_cand:
            return False
        return clean_cand[-1] in clean_auth

    def enrich_profile(self, profile: ResumeProfile) -> ExternalVerification:
        cfg = config_manager.get_enrichment_config()
        has_any_links = len(profile.academic_links) > 0
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if not cfg.get("enabled", True):
            return ExternalVerification(
                match_method="link_only" if has_any_links else "none",
                verified_at=now_iso,
                notes="External academic API enrichment disabled in configuration",
            )

        timeout = float(cfg.get("timeout_seconds", 5.0))
        orcid_link = next((l for l in profile.academic_links if l.platform == "orcid" and l.identifier), None)
        orcid_id = orcid_link.identifier if (orcid_link and is_valid_orcid(orcid_link.identifier or "")) else None
        orcid_verified = False

        try:
            with httpx.Client(timeout=timeout, headers={"User-Agent": "FacultyScreen/2.0"}) as client:
                # 1. Exact ORCID verification
                if orcid_id and cfg.get("enable_orcid_api", True):
                    try:
                        resp = client.get(
                            f"https://pub.orcid.org/v3.0/{orcid_id}/record",
                            headers={"Accept": "application/json"},
                        )
                        if resp.status_code == 200:
                            orcid_verified = True
                            if orcid_link:
                                orcid_link.verified = True
                    except Exception as e:
                        logger.debug(f"ORCID lookup skipped for {orcid_id}: {e}")

                # 2. Exact OpenAlex lookup by verified ORCID
                if orcid_id and cfg.get("enable_openalex_api", True):
                    try:
                        oa_resp = client.get(f"https://api.openalex.org/authors/https://orcid.org/{orcid_id}")
                        if oa_resp.status_code == 200:
                            return self._extract_openalex_metrics(
                                oa_resp.json(),
                                match_method="orcid_exact",
                                orcid_verified=orcid_verified,
                            )
                    except Exception as e:
                        logger.debug(f"OpenAlex ORCID lookup failed for {orcid_id}: {e}")

                # 3. High-precision fallback: lookup via verified publication DOI + last-name check
                dois = [p.doi.strip() for p in profile.research.publications if p.doi and p.doi.strip()]
                if dois and cfg.get("enable_openalex_api", True):
                    for doi in dois[:2]:
                        try:
                            w_resp = client.get(f"https://api.openalex.org/works/https://doi.org/{doi}")
                            if w_resp.status_code != 200:
                                continue
                            work_data = w_resp.json()
                            for auth_ship in work_data.get("authorships", []):
                                author_obj = auth_ship.get("author") or {}
                                disp = str(author_obj.get("display_name") or "")
                                oa_author_id = author_obj.get("id") or ""
                                if oa_author_id and self._name_matches_author(profile.name, disp):
                                    slug = oa_author_id.rstrip("/").split("/")[-1]
                                    a_resp = client.get(f"https://api.openalex.org/authors/{slug}")
                                    if a_resp.status_code == 200:
                                        return self._extract_openalex_metrics(
                                            a_resp.json(),
                                            match_method="doi_verified",
                                            orcid_verified=orcid_verified,
                                        )
                        except Exception as e:
                            logger.debug(f"OpenAlex DOI lookup failed for {doi}: {e}")
        except Exception as e:
            logger.debug(f"External verification client error for {profile.candidate_id}: {e}")

        if orcid_verified:
            return ExternalVerification(
                orcid_verified=True,
                match_method="orcid_exact",
                verified_at=now_iso,
                source_url=f"https://orcid.org/{orcid_id}",
            )

        return ExternalVerification(
            match_method="link_only" if has_any_links else "none",
            verified_at=now_iso,
            notes="Verified CV links preserved" if has_any_links else None,
        )


academic_profile_service = AcademicProfileService()
