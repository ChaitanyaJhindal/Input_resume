import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.schemas.resume import EmploymentEntry, ExperienceBreakdown
from backend.app.services.experience_service import ExperienceService
from backend.app.integrations.groq.groq_pool import groq_pool

logger = logging.getLogger("FacultyScreen.ExperienceAgent")

ROLE_PROMPT = """You are an academic career analyst.
Classify the following employment entry into one of the exact categories:
- teaching (Lecturer, Assistant/Associate Professor, Instructor)
- research (Postdoc, Research Fellow, Scientist, Lab Researcher)
- industry (Corporate engineering, Software developer, Consultant)
- administrative (Dean, HOD, Director, Registrar)

Output ONLY valid JSON:
{
  "category": "teaching|research|industry|administrative",
  "confidence": 0.95
}
"""

class ExperienceAgent:
    """
    Agent responsible for disaggregating employment records into academic classifications
    and calculating mathematically non-overlapping experience totals.
    """

    def __init__(self, reasoning_model: Optional[str] = None):
        self.reasoning_model = reasoning_model or settings.groq_reasoning_model

    def classify_role(self, title: str, organization: str = "", description: str = "") -> str:
        # Fast deterministic classification
        cat = ExperienceService.categorize_employment(title, organization, description)
        if cat in ["teaching", "research", "administrative"]:
            return cat

        # If ambiguous, consult LLM
        try:
            messages = [
                {"role": "system", "content": ROLE_PROMPT},
                {"role": "user", "content": f"Title: {title}\nOrganization: {organization}\nDescription: {description}"}
            ]
            completion = groq_pool.execute_completion(
                model=self.reasoning_model,
                messages=messages,
                response_format={"type": "json_object"},
                reasoning_format="hidden",
                max_tokens=100,
                temperature=0.0
            )
            res = json.loads(completion.choices[0].message.content.strip())
            return res.get("category", "industry")
        except Exception:
            return cat

    def process_experience(self, employment_entries: List[EmploymentEntry]) -> ExperienceBreakdown:
        for entry in employment_entries:
            if not entry.category or entry.category == "other":
                entry.category = self.classify_role(entry.title, entry.organization, entry.description or "")

        return ExperienceService.calculate_experience(employment_entries)

experience_agent = ExperienceAgent()
