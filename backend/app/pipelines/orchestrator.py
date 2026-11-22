import logging
from pathlib import Path
from typing import List, Optional

from backend.app.agents.orchestration_agent import OrchestrationAgent, orchestration_agent
from backend.app.config import settings, config_manager
from backend.app.schemas.resume import ResumeProfile

logger = logging.getLogger("FacultyScreen.Orchestrator")


class ResumeProcessingOrchestrator:
    """
    Unified orchestration facade for FacultyScreen:
    discovers source resumes and delegates individual document processing to OrchestrationAgent.
    """

    def __init__(self, resumes_dir: Optional[str] = None, data_dir: Optional[Path] = None):
        self.resumes_dir = Path(resumes_dir or settings.resumes_dir).resolve()
        self.data_dir = Path(data_dir or settings.data_dir).resolve()
        self.processed_dir = self.data_dir / "processed"
        self.results_dir = self.data_dir / "results"
        self.logs_dir = self.data_dir / "logs"

        # Ensure directory structure exists without touching original resumes folder
        for d in [self.processed_dir, self.results_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_candidate_id(file_path: Path, file_hash: Optional[str] = None) -> str:
        """
        Creates a deterministic content-based candidate ID using the file's SHA-256 hash.
        """
        return OrchestrationAgent.generate_candidate_id(file_path, file_hash=file_hash)

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        return OrchestrationAgent.compute_file_hash(file_path)

    def discover_resumes(self) -> List[Path]:
        """
        Recursively scans the configured source-of-truth directory for supported documents.
        Supports PDF, PNG, JPG, JPEG.
        Does NOT scan generated data or virtual environments.
        """
        pipeline_cfg = config_manager.get_pipeline_config()
        supported_exts = set(pipeline_cfg["supported_extensions"])
        ignored_dirs = set(pipeline_cfg["ignored_directories"])
        found_files = []

        if not self.resumes_dir.exists():
            logger.warning(f"Configured resumes directory does not exist: {self.resumes_dir}")
            return []

        for p in self.resumes_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in supported_exts:
                rel_parts = p.relative_to(self.resumes_dir).parts
                if any(ignored in rel_parts for ignored in ignored_dirs):
                    continue
                found_files.append(p)

        found_files.sort(key=lambda x: x.name)
        return found_files

    def process_resume(self, file_path: Path, force_reprocess: bool = False) -> ResumeProfile:
        """
        Processes an individual resume through the unified agentic pipeline.
        """
        if self.data_dir == orchestration_agent.data_dir:
            return orchestration_agent.process_document(file_path, force_reprocess=force_reprocess)
        agent = OrchestrationAgent(data_dir=self.data_dir)
        return agent.process_document(file_path, force_reprocess=force_reprocess)

    def process_all_resumes(self, force_reprocess: bool = False, max_count: Optional[int] = None) -> List[ResumeProfile]:
        """
        Discovers and processes all candidate resumes in the source-of-truth directory.
        """
        files = self.discover_resumes()
        if max_count:
            files = files[:max_count]

        profiles = []
        logger.info(f"Processing {len(files)} discovered resume files...")
        for p in files:
            try:
                prof = self.process_resume(p, force_reprocess=force_reprocess)
                profiles.append(prof)
            except Exception as e:
                logger.error(f"Failed to process {p.name}: {e}", exc_info=True)

        return profiles


orchestrator = ResumeProcessingOrchestrator()
