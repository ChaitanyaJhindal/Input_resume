import logging
from typing import Tuple, Optional
from backend.app.config import settings, config_manager
from backend.app.services.education_service import EducationService
from backend.app.services.jev.jev_router import jev_router
from backend.app.groq.pool import groq_pool
from backend.app.utils.json_utils import parse_llm_json, safe_float

logger = logging.getLogger("FacultyScreen.EducationAgent")

DEGREE_PROMPT = config_manager.get_prompt("education_agent", "system")


class EducationAgent:
    """
    Agent responsible for degree standardization and academic equivalence analysis.
    Routes through the unified 3-tier hierarchy:
    1. Deterministic boundary patterns (EducationService)
    2. JEV structured decision layer
    3. Groq reasoning LLM escalation when ambiguity persists
    """

    def __init__(self, reasoning_model: Optional[str] = None):
        self._model_override = reasoning_model

    @property
    def reasoning_model(self) -> str:
        return self._model_override or config_manager.get_task_config("education_agent", "reasoning")["model"]

    def normalize_detailed(self, raw_degree: str) -> Tuple[str, float, str]:
        """Returns (normalized_degree, confidence, tier_source)."""
        if not raw_degree or len(raw_degree.strip()) < 2:
            return "Other", 0.5, "deterministic"

        cfg = config_manager.get_task_config("education_agent", "reasoning")
        esc_threshold = float(cfg.get("escalation_confidence_threshold", 0.75))
        deg_options = config_manager.get_taxonomy(
            "degree_levels",
            [
                "PhD / Doctorate",
                "PhD (In Progress)",
                "Postdoctoral",
                "Postgraduate / Masters",
                "Undergraduate",
                "Diploma",
                "Certification",
                "Other",
            ],
        )

        def deterministic_fn():
            level, conf = EducationService.normalize_degree(raw_degree)
            if level != "Other" or conf >= esc_threshold:
                return (level, conf, f"Deterministic degree pattern matched '{level}'")
            return (None, conf, "Ambiguous degree format")

        escalation_fn = None
        if not settings.mock_mode and groq_pool.size > 0:
            def _escalate():
                system_prompt = config_manager.get_prompt("education_agent", "system", default=DEGREE_PROMPT)
                user_prompt = config_manager.get_prompt(
                    "education_agent",
                    "user_template",
                    default="Degree to classify: {raw_degree}",
                    raw_degree=raw_degree,
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                logger.info(f"EducationAgent escalating '{raw_degree}' to {self.reasoning_model}")
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
                    raise ValueError("Unparseable JSON from EducationAgent LLM")
                raw_norm = str(res.get("normalized_degree") or "Other").strip()
                norm_deg = raw_norm if raw_norm in deg_options else "Other"
                conf_val = max(0.0, min(1.0, safe_float(res.get("confidence"), 0.85)))
                return norm_deg, conf_val, str(res.get("reason") or "LLM degree classification")

            escalation_fn = _escalate

        decision, confidence, _rationale, tier_source = jev_router.route_decision(
            task="classify_degree",
            context={"raw_degree": raw_degree},
            deterministic_fn=deterministic_fn,
            candidate_options=deg_options,
            confidence_threshold=esc_threshold,
            escalation_fn=escalation_fn,
        )

        final_deg = str(decision) if str(decision) in deg_options else "Other"
        final_conf = max(0.0, min(1.0, float(confidence)))
        return final_deg, final_conf, tier_source

    def normalize_with_meta(self, raw_degree: str) -> Tuple[str, float, bool]:
        """Returns (normalized_degree, confidence, used_llm)."""
        norm_deg, conf_val, tier_source = self.normalize_detailed(raw_degree)
        return norm_deg, conf_val, (tier_source == "groq_escalation")

    def normalize(self, raw_degree: str) -> Tuple[str, float]:
        norm_deg, conf_val, _ = self.normalize_detailed(raw_degree)
        return norm_deg, conf_val


education_agent = EducationAgent()
