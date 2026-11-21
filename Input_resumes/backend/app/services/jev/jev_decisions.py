from typing import Tuple, Optional, List
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
        def deterministic_fn():
            norm, cat, tier, conf = institution_service.classify_institution(raw_institution)
            # If known in taxonomy database
            if cat != "Other" or conf >= 0.85:
                return ((norm, cat, tier), conf, f"Matched in curated institutional taxonomy as {cat}")
            return (None, 0.5, "Unresolved in database")

        decision, confidence, rationale, source = jev_router.route_decision(
            task="classify_institution",
            context={"institution_name": raw_institution},
            deterministic_fn=deterministic_fn,
            candidate_options=["IIT", "NIT", "IIIT", "Central University", "State University", "Deemed University", "Private University", "Research Institute", "International University", "Other"]
        )

        if isinstance(decision, tuple):
            norm, cat, tier = decision
            return norm, cat, tier, confidence
        else:
            norm_name = raw_institution.strip()
            cat = decision if decision != "unresolved" else "Other"
            tier = "Unknown / Unclassified"
            return norm_name, cat, tier, confidence

    @classmethod
    def resolve_degree_level(cls, raw_degree: str) -> Tuple[str, float]:
        """
        Resolves normalized degree category (PhD / Doctorate, Postgraduate / Masters, Undergraduate, etc.)
        """
        def deterministic_fn():
            level = EducationService.normalize_degree(raw_degree)
            if level != "Other":
                return (level, 0.95, f"Deterministic degree pattern match for {level}")
            return (None, 0.5, "Unrecognized degree format")

        decision, confidence, rationale, source = jev_router.route_decision(
            task="classify_degree",
            context={"raw_degree": raw_degree},
            deterministic_fn=deterministic_fn,
            candidate_options=["PhD / Doctorate", "Postdoctoral", "Postgraduate / Masters", "Undergraduate", "Diploma", "Certification", "Other"]
        )

        if isinstance(decision, (tuple, list)):
            decision = str(decision[0])
        elif not isinstance(decision, str):
            decision = str(decision)

        return (str(decision), confidence)
