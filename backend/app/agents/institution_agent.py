import logging
from typing import Tuple, Optional
from backend.app.config import settings, config_manager
from backend.app.services.institution_service import institution_service
from backend.app.services.jev.jev_router import jev_router
from backend.app.groq.pool import groq_pool
from backend.app.utils.json_utils import parse_llm_json, safe_float

logger = logging.getLogger("FacultyScreen.InstitutionAgent")

INSTITUTION_CLASSIFICATION_PROMPT = config_manager.get_prompt("institution_agent", "system")


class InstitutionAgent:
    """
    Agent specializing in Institutional Normalization & Taxonomy Classification.
    Routes through the unified 3-tier hierarchy:
    1. Deterministic curated institutional taxonomy
    2. JEV structured decision layer
    3. Groq reasoning LLM escalation when unclassified
    """

    def __init__(self, reasoning_model: Optional[str] = None):
        self._model_override = reasoning_model

    @property
    def reasoning_model(self) -> str:
        return self._model_override or config_manager.get_task_config("institution_agent", "reasoning")["model"]

    def classify_detailed(self, raw_institution: str) -> Tuple[str, str, str, float, str]:
        """
        Returns: (canonical_name, category, tier, confidence, tier_source)
        """
        raw_clean = str(raw_institution or "").strip().lower()
        if not raw_institution or len(raw_clean) < 2 or raw_clean in {
            "unspecified institution", "unspecified", "unknown", "null", "none", "n/a", "other"
        }:
            return "Unspecified Institution", "Other", "Unknown / Unclassified", 0.5, "deterministic"

        cfg = config_manager.get_task_config("institution_agent", "reasoning")
        esc_threshold = float(cfg.get("escalation_confidence_threshold", 0.85))
        allowed_categories = institution_service.categories
        allowed_tiers = config_manager.get_taxonomy(
            "institution_tiers",
            ["Tier 1", "Tier 2", "Tier 3", "Unknown / Unclassified"],
        )

        det_norm, det_cat, det_tier, det_conf = institution_service.classify_institution(raw_institution)

        def deterministic_fn():
            if det_cat != "Other" or det_conf >= esc_threshold:
                return ((det_norm, det_cat, det_tier), det_conf, f"Matched curated institution taxonomy as {det_cat}")
            return (None, det_conf, "Unclassified in local institutional taxonomy")

        escalation_fn = None
        if not settings.mock_mode and groq_pool.size > 0:
            def _escalate():
                system_prompt = config_manager.get_prompt(
                    "institution_agent", "system", default=INSTITUTION_CLASSIFICATION_PROMPT
                )
                user_prompt = config_manager.get_prompt(
                    "institution_agent",
                    "user_template",
                    default="Institution to classify: {raw_institution}",
                    raw_institution=raw_institution,
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]

                logger.info(f"InstitutionAgent escalating '{raw_institution}' to {self.reasoning_model}")
                completion = groq_pool.execute_completion(
                    model=self.reasoning_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=cfg["max_tokens"],
                    temperature=cfg["temperature"],
                    **cfg.get("extra_completion_kwargs", {}),
                )
                res, _ = parse_llm_json(completion.choices[0].message.content)
                if not res:
                    raise ValueError("Unparseable JSON from InstitutionAgent LLM")

                canon = str(res.get("canonical_name") or det_norm).strip() or det_norm
                raw_cat = str(res.get("category") or "Other").strip()
                cat = raw_cat if raw_cat in allowed_categories else "Other"
                raw_tier = str(res.get("tier") or "Unknown / Unclassified").strip()
                tier = raw_tier if raw_tier in allowed_tiers else "Unknown / Unclassified"
                conf_val = max(0.0, min(1.0, safe_float(res.get("confidence"), 0.85)))
                return (canon, cat, tier), conf_val, str(res.get("reason") or "LLM institutional classification")

            escalation_fn = _escalate

        decision, confidence, _rationale, tier_source = jev_router.route_decision(
            task="classify_institution",
            context={"institution_name": raw_institution},
            deterministic_fn=deterministic_fn,
            candidate_options=allowed_categories,
            confidence_threshold=esc_threshold,
            escalation_fn=escalation_fn,
        )

        final_conf = max(0.0, min(1.0, float(confidence)))
        if isinstance(decision, tuple) and len(decision) == 3:
            return str(decision[0]), str(decision[1]), str(decision[2]), final_conf, tier_source

        raw_dec_cat = str(decision or "Other").strip()
        resolved_cat = raw_dec_cat if raw_dec_cat in allowed_categories else "Other"
        return det_norm, resolved_cat, det_tier, final_conf, tier_source

    def classify_with_meta(self, raw_institution: str) -> Tuple[str, str, str, float, bool]:
        """
        Returns: (canonical_name, category, tier, confidence, used_llm)
        """
        canon, cat, tier, conf, tier_source = self.classify_detailed(raw_institution)
        return canon, cat, tier, conf, (tier_source == "groq_escalation")

    def classify(self, raw_institution: str) -> Tuple[str, str, str, float]:
        """
        Returns: (canonical_name, category, tier, confidence)
        """
        norm, cat, tier, conf, _ = self.classify_detailed(raw_institution)
        return norm, cat, tier, conf


institution_agent = InstitutionAgent()
