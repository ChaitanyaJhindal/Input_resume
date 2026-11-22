import time
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple
from backend.app.config import config_manager
from backend.app.services.jev.jev_client import JevClient
from backend.app.services.jev.jev_schemas import JevDecisionRequest

logger = logging.getLogger("FacultyScreen.JevRouter")


class JevRouter:
    """
    Thread-safe Tiered Decision Router implementing the core 3-tier strategy:
    1. Deterministic database/lookup first
    2. JEV / TypeSafe AI structured decisions second
    3. Groq LLM reasoning only when ambiguity persists
    """

    def __init__(self, jev_client: Optional[JevClient] = None):
        self.jev_client = jev_client or JevClient()
        self._lock = threading.Lock()
        self.stats = {
            "deterministic_resolutions": 0,
            "jev_decision_calls": 0,
            "groq_api_calls": 0,
            "escalations": 0,
            "total_latency_ms": 0.0,
        }

    def _record_stat(self, key: str, latency_ms: float = 0.0) -> None:
        with self._lock:
            self.stats[key] = self.stats.get(key, 0) + 1
            if latency_ms:
                self.stats["total_latency_ms"] += latency_ms

    def route_decision(
        self,
        task: str,
        context: Dict[str, Any],
        deterministic_fn=None,
        candidate_options: Optional[List[str]] = None,
        confidence_threshold: Optional[float] = None,
        escalation_fn=None,
    ) -> Tuple[Any, float, str, str]:
        """
        Routes the task through the 3-tier hierarchy.
        Returns: (decision_value, confidence, rationale, tier_source)
        tier_source: 'deterministic' | 'jev' | 'groq_escalation' | 'unresolved_fallback'
        """
        start = time.time()
        threshold = (
            float(confidence_threshold)
            if confidence_threshold is not None
            else float(config_manager.get_jev_config()["confidence_threshold"])
        )

        # Tier 1: Deterministic resolution first
        if deterministic_fn:
            try:
                det_result = deterministic_fn()
                if det_result and det_result[0] is not None:
                    value, conf, rationale = det_result
                    if conf >= threshold:
                        latency = (time.time() - start) * 1000
                        self._record_stat("deterministic_resolutions", latency)
                        return (value, conf, rationale, "deterministic")
            except Exception as e:
                logger.debug(f"Deterministic handler failed: {e}")

        # Tier 2: JEV structured decision layer
        req = JevDecisionRequest(
            task=task,
            context=context,
            candidate_options=candidate_options,
            confidence_threshold=threshold,
        )
        jev_resp = self.jev_client.execute_decision(req)
        self._record_stat("jev_decision_calls")

        if jev_resp.confidence >= threshold and not jev_resp.is_escalated:
            latency = (time.time() - start) * 1000
            with self._lock:
                self.stats["total_latency_ms"] += latency
            return (jev_resp.decision, jev_resp.confidence, jev_resp.rationale, "jev")

        # Tier 3: Escalate to Groq LLM only if an escalation handler is provided
        self._record_stat("escalations")
        if escalation_fn is not None:
            try:
                esc_val, esc_conf, esc_rationale = escalation_fn()
                latency = (time.time() - start) * 1000
                self._record_stat("groq_api_calls", latency)
                return (esc_val, esc_conf, esc_rationale, "groq_escalation")
            except Exception as e:
                logger.warning(f"LLM escalation handler failed for task {task}: {e}")

        latency = (time.time() - start) * 1000
        with self._lock:
            self.stats["total_latency_ms"] += latency

        return (
            jev_resp.decision,
            jev_resp.confidence,
            f"Unresolved escalation fallback: {jev_resp.rationale}",
            "unresolved_fallback",
        )

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.stats)


jev_router = JevRouter()
