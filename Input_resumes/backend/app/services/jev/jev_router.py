import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from backend.app.services.jev.jev_client import JevClient
from backend.app.services.jev.jev_schemas import JevDecisionRequest, JevDecisionResponse

logger = logging.getLogger("FacultyScreen.JevRouter")

class JevRouter:
    """
    Tiered Decision Router implementing the core strategy:
    1. Deterministic database/lookup first
    2. JEV / TypeSafe AI structured decisions second
    3. Groq LLM reasoning only when ambiguity persists
    """

    def __init__(self, jev_client: Optional[JevClient] = None):
        self.jev_client = jev_client or JevClient()
        self.stats = {
            "deterministic_resolutions": 0,
            "jev_decision_calls": 0,
            "groq_api_calls": 0,
            "escalations": 0,
            "total_latency_ms": 0.0
        }

    def route_decision(
        self,
        task: str,
        context: Dict[str, Any],
        deterministic_fn=None,
        candidate_options: Optional[List[str]] = None,
        confidence_threshold: float = 0.85
    ) -> Tuple[str, float, str, str]:
        """
        Routes the task through the 3-tier hierarchy.
        Returns: (decision_value, confidence, rationale, tier_source)
        tier_source: 'deterministic' | 'jev' | 'groq_escalation'
        """
        start = time.time()

        # Step 1: Try Deterministic resolution first
        if deterministic_fn:
            try:
                det_result = deterministic_fn()
                if det_result and det_result[0] is not None:
                    value, conf, rationale = det_result
                    if conf >= confidence_threshold:
                        self.stats["deterministic_resolutions"] += 1
                        latency = (time.time() - start) * 1000
                        self.stats["total_latency_ms"] += latency
                        return (value, conf, rationale, "deterministic")
            except Exception as e:
                logger.debug(f"Deterministic handler failed: {e}")

        # Step 2: Use JEV structured decision layer
        req = JevDecisionRequest(
            task=task,
            context=context,
            candidate_options=candidate_options,
            confidence_threshold=confidence_threshold
        )
        jev_resp = self.jev_client.execute_decision(req)
        self.stats["jev_decision_calls"] += 1

        if jev_resp.confidence >= confidence_threshold and not jev_resp.is_escalated:
            latency = (time.time() - start) * 1000
            self.stats["total_latency_ms"] += latency
            return (jev_resp.decision, jev_resp.confidence, jev_resp.rationale, "jev")

        # Step 3: Escalate to LLM only if necessary
        self.stats["escalations"] += 1
        self.stats["groq_api_calls"] += 1
        latency = (time.time() - start) * 1000
        self.stats["total_latency_ms"] += latency

        # Return best available decision with escalation tag
        return (
            jev_resp.decision,
            jev_resp.confidence,
            f"Escalated due to ambiguity: {jev_resp.rationale}",
            "groq_escalation"
        )

    def get_telemetry(self) -> Dict[str, Any]:
        return dict(self.stats)

# Global router singleton
jev_router = JevRouter()
