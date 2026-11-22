import logging
from typing import List, Dict, Optional, Tuple
from backend.app.config import settings, config_manager
from backend.app.schemas.resume import EmploymentEntry, ExperienceBreakdown
from backend.app.services.experience_service import ExperienceService
from backend.app.services.jev.jev_router import jev_router
from backend.app.groq.pool import groq_pool
from backend.app.utils.json_utils import parse_llm_json, safe_float

logger = logging.getLogger("FacultyScreen.ExperienceAgent")

ROLE_PROMPT = config_manager.get_prompt("experience_agent", "system")
VALID_CATEGORIES = {"teaching", "research", "industry", "administrative"}


class ExperienceAgent:
    """
    Agent responsible for disaggregating employment records into academic classifications
    and calculating mathematically non-overlapping experience totals.
    Uses unified JevRouter 3-tier routing (deterministic -> JEV -> Groq LLM escalation).
    """

    def __init__(self, reasoning_model: Optional[str] = None):
        self._model_override = reasoning_model

    @property
    def reasoning_model(self) -> str:
        return self._model_override or config_manager.get_task_config("experience_agent", "reasoning")["model"]

    def classify_role_detailed(
        self, title: str, organization: str = "", description: str = ""
    ) -> Tuple[str, str]:
        """Returns (category, tier_source)."""
        cfg = config_manager.get_task_config("experience_agent", "reasoning")
        esc_threshold = float(cfg.get("escalation_confidence_threshold", 0.85))
        allowed = config_manager.get_taxonomy(
            "experience_categories",
            ["teaching", "research", "industry", "administrative"],
        )

        det_cat, det_conf = ExperienceService.categorize_employment_with_confidence(
            title, organization, description
        )

        def deterministic_fn():
            if det_conf >= esc_threshold:
                return (det_cat, det_conf, f"Deterministic role keywords classified '{title}' as {det_cat}")
            return (None, det_conf, f"Ambiguous role title '{title}'")

        escalation_fn = None
        if not settings.mock_mode and groq_pool.size > 0:
            def _escalate():
                system_prompt = config_manager.get_prompt("experience_agent", "system", default=ROLE_PROMPT)
                user_prompt = config_manager.get_prompt(
                    "experience_agent",
                    "user_template",
                    default="Title: {title}\nOrganization: {organization}\nDescription: {description}",
                    title=title,
                    organization=organization,
                    description=description,
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
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
                    raise ValueError("Unparseable JSON from ExperienceAgent LLM")
                raw_cat = str(res.get("category") or "industry").strip().lower()
                final_cat = raw_cat if raw_cat in VALID_CATEGORIES else det_cat
                conf_val = max(0.0, min(1.0, safe_float(res.get("confidence"), 0.88)))
                return final_cat, conf_val, "LLM role disambiguation"

            escalation_fn = _escalate

        decision, _conf, _rationale, tier_source = jev_router.route_decision(
            task="classify_role",
            context={"title": title, "organization": organization, "description": description},
            deterministic_fn=deterministic_fn,
            candidate_options=allowed,
            confidence_threshold=esc_threshold,
            escalation_fn=escalation_fn,
        )

        raw_final = str(decision or det_cat).strip().lower()
        final_cat = raw_final if raw_final in VALID_CATEGORIES else det_cat
        return final_cat, tier_source

    def classify_role(self, title: str, organization: str = "", description: str = "") -> str:
        cat, _ = self.classify_role_detailed(title, organization, description)
        return cat

    def process_experience_with_meta(
        self, employment_entries: List[EmploymentEntry]
    ) -> Tuple[ExperienceBreakdown, Dict[str, int]]:
        telemetry = {
            "deterministic_resolutions": 0,
            "jev_decision_calls": 0,
            "escalations": 0,
            "groq_api_calls": 0,
        }
        for entry in employment_entries:
            raw_cat = str(entry.category or "").strip().lower()
            if not raw_cat or raw_cat not in VALID_CATEGORIES:
                cat, tier_source = self.classify_role_detailed(
                    entry.title, entry.organization, entry.description or ""
                )
                entry.category = cat
                if tier_source == "deterministic":
                    telemetry["deterministic_resolutions"] += 1
                elif tier_source == "jev":
                    telemetry["jev_decision_calls"] += 1
                elif tier_source == "groq_escalation":
                    telemetry["jev_decision_calls"] += 1
                    telemetry["escalations"] += 1
                    telemetry["groq_api_calls"] += 1
                else:
                    telemetry["jev_decision_calls"] += 1
                    telemetry["escalations"] += 1

        return ExperienceService.calculate_experience(employment_entries), telemetry

    def process_experience(self, employment_entries: List[EmploymentEntry]) -> ExperienceBreakdown:
        breakdown, _ = self.process_experience_with_meta(employment_entries)
        return breakdown


experience_agent = ExperienceAgent()
