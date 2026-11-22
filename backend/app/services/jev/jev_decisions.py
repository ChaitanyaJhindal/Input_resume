from typing import Tuple
from backend.app.config import config_manager
from backend.app.services.jev.jev_router import jev_router
from backend.app.services.institution_service import institution_service
from backend.app.services.education_service import EducationService


class JevDecisions:
    """
    High-level decision facade applying JEV fast routing to specific resume attributes.
    """

    @classmethod
    def resolve_institution_category(cls, raw_institution: str) -> Tuple[str, str, str, float]:
        """
        Resolves (normalized_name, category, tier, confidence).
        Attempts database lookup -> JEV classification -> fallback.
        """
        det_norm, det_cat, det_tier, det_conf = institution_service.classify_institution(raw_institution)

        def deterministic_fn():
            if det_cat != "Other" or det_conf >= 0.85:
                return ((det_norm, det_cat, det_tier), det_conf, f"Matched in curated institutional taxonomy as {det_cat}")
            return (None, 0.5, "Unresolved in database")

        inst_options = config_manager.get_taxonomy(
            "institution_categories",
            [
                "IIT", "NIT", "IIIT", "Central University", "State University",
                "Deemed University", "Private University", "Research Institute",
                "International University", "Other",
            ],
        )
        decision, confidence, _rationale, _source = jev_router.route_decision(
            task="classify_institution",
            context={"institution_name": raw_institution},
            deterministic_fn=deterministic_fn,
            candidate_options=inst_options,
        )

        if isinstance(decision, tuple) and len(decision) == 3:
            norm, cat, tier = decision
            return str(norm), str(cat), str(tier), float(confidence)

        cat = str(decision) if decision and str(decision) != "unresolved" else "Other"
        return det_norm or raw_institution.strip(), cat, det_tier, float(confidence)

    @classmethod
    def resolve_degree_level(cls, raw_degree: str) -> Tuple[str, float]:
        """
        Resolves normalized degree category (PhD / Doctorate, Postgraduate / Masters, Undergraduate, etc.)
        """
        def deterministic_fn():
            level, conf = EducationService.normalize_degree(raw_degree)
            if level != "Other" and conf >= 0.85:
                return (level, conf, f"Deterministic degree pattern match for {level}")
            return (None, conf, "Unrecognized degree format")

        deg_options = config_manager.get_taxonomy(
            "degree_levels",
            [
                "PhD / Doctorate", "PhD (In Progress)", "Postdoctoral",
                "Postgraduate / Masters", "Undergraduate", "Diploma",
                "Certification", "Other",
            ],
        )
        decision, confidence, _rationale, _source = jev_router.route_decision(
            task="classify_degree",
            context={"raw_degree": raw_degree},
            deterministic_fn=deterministic_fn,
            candidate_options=deg_options,
        )

        if isinstance(decision, (tuple, list)):
            decision = str(decision[0])
        elif not isinstance(decision, str):
            decision = str(decision)

        return (str(decision), float(confidence))
