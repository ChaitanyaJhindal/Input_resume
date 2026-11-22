import logging
from typing import Dict, Any, List
from backend.app.schemas.resume import ResearchProfile
from backend.app.services.research_service import ResearchService

logger = logging.getLogger("FacultyScreen.ResearchAgent")

class ResearchAgent:
    """
    Agent responsible for scholarly publication extraction, DOI verification,
    and bibliographic indexing detection (Scopus, SCI, IEEE).
    """

    def process(self, raw_research_data: Dict[str, Any]) -> ResearchProfile:
        return ResearchService.process_research_profile(raw_research_data)

research_agent = ResearchAgent()
