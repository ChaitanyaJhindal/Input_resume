import json
import logging
from typing import Tuple, Optional
from backend.app.core.config import settings
from backend.app.services.education_service import EducationService
from backend.app.integrations.groq.groq_pool import groq_pool

logger = logging.getLogger("FacultyScreen.EducationAgent")

DEGREE_PROMPT = """You are a higher education qualifications expert.
Classify the academic credential into one of the following exact standardized levels:
- PhD / Doctorate
- Postdoctoral
- Postgraduate / Masters
- Undergraduate
- Diploma
- Certification
- Other

Output ONLY valid JSON:
{
  "normalized_degree": "Exact level from above",
  "field_of_study": "Detected field or null",
  "confidence": 0.95,
  "reason": "Brief rationale"
}
"""

class EducationAgent:
    """
    Agent responsible for degree standardization and academic equivalence analysis.
    Uses regex patterns first, escalating to Groq LLM (openai/gpt-oss-20b) when ambiguous.
    """

    def __init__(self, reasoning_model: Optional[str] = None):
        self.reasoning_model = reasoning_model or settings.groq_reasoning_model

    def normalize(self, raw_degree: str) -> Tuple[str, float]:
        if not raw_degree or len(raw_degree.strip()) < 2:
            return "Other", 0.5

        # 1. Deterministic pattern matching (0ms)
        level, conf = EducationService.normalize_degree(raw_degree)
        if level != "Other" or conf >= 0.75:
            return level, conf

        # 2. Escalation to Groq reasoning LLM
        try:
            messages = [
                {"role": "system", "content": DEGREE_PROMPT},
                {"role": "user", "content": f"Degree to classify: {raw_degree}"}
            ]
            logger.info(f"EducationAgent escalating '{raw_degree}' to {self.reasoning_model}")
            completion = groq_pool.execute_completion(
                model=self.reasoning_model,
                messages=messages,
                response_format={"type": "json_object"},
                reasoning_format="hidden",
                reasoning_effort="low",
                max_tokens=1000,
                temperature=0.0
            )
            res = json.loads(completion.choices[0].message.content.strip())
            norm_deg = res.get("normalized_degree", "Other")
            conf_val = float(res.get("confidence", 0.90))
            return norm_deg, conf_val
        except Exception as e:
            logger.warning(f"EducationAgent LLM escalation failed for '{raw_degree}': {e}")
            return level, conf

education_agent = EducationAgent()
