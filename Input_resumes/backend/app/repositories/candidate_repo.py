"""
Backward-compatibility re-export for CandidateRepository.
The primary implementation lives in backend.app.database.repository.
"""
from backend.app.database.repository import CandidateRepository, candidate_repo

__all__ = ["CandidateRepository", "candidate_repo"]
