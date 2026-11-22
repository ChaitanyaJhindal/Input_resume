import logging
from typing import Dict, Any
from backend.app.schemas.resume import ResumeProfile, ScreeningResult
from backend.app.services.screening_service import screening_service

logger = logging.getLogger("FacultyScreen.ScreeningAgent")

class ScreeningAgent:
    """
    Agent responsible for evaluating candidate facts against configurable hiring rules
    and synthesizing transparent, explainable decisions.
    """

    def evaluate(self, profile: ResumeProfile) -> ScreeningResult:
        return screening_service.evaluate_candidate(profile)

screening_agent = ScreeningAgent()
