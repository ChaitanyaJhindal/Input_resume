import json
import logging
from typing import Tuple, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.services.institution_service import institution_service
from backend.app.integrations.groq.groq_pool import groq_pool

logger = logging.getLogger("FacultyScreen.InstitutionAgent")

INSTITUTION_CLASSIFICATION_PROMPT = """You are an academic accreditation specialist.
Classify the following educational institution into one of the exact categories below:
- IIT
- NIT
- IIIT
- Central University
- State University
- Deemed University
- Private University
- International University
- Research Institute
- Other

Also assign an institutional tier: Tier 1, Tier 2, Tier 3, or Unknown / Unclassified.

Output ONLY valid JSON:
{
  "canonical_name": "Standardized Name",
  "category": "One of the above categories",
  "tier": "Tier 1|Tier 2|Tier 3|Unknown / Unclassified",
  "confidence": 0.95,
  "reason": "Brief rationale citing accreditation/status"
}
"""

class InstitutionAgent:
    """
    Agent specializing in Institutional Normalization & Taxonomy Classification.
    Uses deterministic database first, and escalates to Groq reasoning LLM (openai/gpt-oss-20b)
    for unclassified or ambiguous institutions.
    """

    def __init__(self, reasoning_model: Optional[str] = None):
        self.reasoning_model = reasoning_model or settings.groq_reasoning_model

    def classify(self, raw_institution: str) -> Tuple[str, str, str, float]:
        """
        Returns: (canonical_name, category, tier, confidence)
        """
        raw_clean = str(raw_institution).strip().lower()
        if not raw_institution or len(raw_clean) < 2 or raw_clean in [
            "unspecified institution", "unspecified", "unknown", "null", "none", "n/a", "other"
        ]:
            return "Unspecified Institution", "Other", "Unknown / Unclassified", 0.5

        # 1. Deterministic resolution (0ms, 0 tokens)
        norm, cat, tier, conf = institution_service.classify_institution(raw_institution)
        if cat != "Other" or conf >= 0.85:
            return norm, cat, tier, conf

        # 2. LLM Reasoning Agent Escalation (openai/gpt-oss-20b)
        try:
            messages = [
                {"role": "system", "content": INSTITUTION_CLASSIFICATION_PROMPT},
                {"role": "user", "content": f"Institution to classify: {raw_institution}"}
            ]

            logger.info(f"InstitutionAgent escalating '{raw_institution}' to {self.reasoning_model}")
            completion = groq_pool.execute_completion(
                model=self.reasoning_model,
                messages=messages,
                response_format={"type": "json_object"},
                reasoning_format="hidden",
                reasoning_effort="low",
                max_tokens=600,
                temperature=0.0
            )

            res = json.loads(completion.choices[0].message.content.strip())
            return (
                res.get("canonical_name", norm),
                res.get("category", "Other"),
                res.get("tier", "Unknown / Unclassified"),
                float(res.get("confidence", 0.88))
            )
        except Exception as e:
            logger.warning(f"InstitutionAgent LLM escalation failed for '{raw_institution}': {e}")
            return norm, cat, tier, conf

institution_agent = InstitutionAgent()
