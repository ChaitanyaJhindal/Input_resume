import time
import httpx
import logging
from typing import Optional
from backend.app.config import settings, config_manager
from backend.app.services.jev.jev_schemas import JevDecisionRequest, JevDecisionResponse

logger = logging.getLogger("FacultyScreen.JEV")


class JevClient:
    """
    Client for TypeSafe AI / JEV fast structured decision layer.
    Gracefully falls back to canonical deterministic services when JEV API
    credentials are unconfigured or endpoints are unreachable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.typesafe_api_key
        self._base_url_override = base_url.rstrip("/") if base_url else None
        self._model_override = model
        self._timeout_override = timeout

    @property
    def base_url(self) -> str:
        return self._base_url_override or config_manager.get_jev_config()["base_url"]

    @property
    def model(self) -> str:
        return self._model_override or config_manager.get_jev_config()["model"]

    @property
    def timeout(self) -> float:
        if self._timeout_override is not None:
            return float(self._timeout_override)
        return float(config_manager.get_jev_config()["timeout_seconds"])

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def execute_decision(self, request: JevDecisionRequest) -> JevDecisionResponse:
        start_time = time.time()

        if not self.is_configured:
            return self._local_fallback(request, latency_ms=(time.time() - start_time) * 1000)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FacultyScreen-Engine/1.0",
        }

        payload = {
            "model": self.model,
            "task": request.task,
            "context": request.context,
            "candidate_options": request.candidate_options,
            "confidence_threshold": request.confidence_threshold,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/v1/decisions", json=payload, headers=headers)
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    return JevDecisionResponse(
                        decision=str(data.get("decision", "")),
                        confidence=float(data.get("confidence", 0.95)),
                        rationale=str(data.get("rationale", "JEV structured evaluation")),
                        is_escalated=bool(data.get("is_escalated", False)),
                        metadata={"latency_ms": latency_ms, "model": self.model},
                        source="jev",
                    )
                logger.warning(f"JEV API returned status {resp.status_code}. Using deterministic fallback.")
                return self._local_fallback(request, latency_ms=latency_ms)

        except Exception as e:
            logger.warning(f"JEV service connection failed: {e}. Gracefully reverting to deterministic fallback.")
            latency_ms = (time.time() - start_time) * 1000
            return self._local_fallback(request, latency_ms=latency_ms)

    def _local_fallback(self, request: JevDecisionRequest, latency_ms: float = 0.5) -> JevDecisionResponse:
        """
        Delegates strictly to the curated, boundary-guarded domain services rather than
        duplicating brittle keyword checks.
        """
        task = request.task
        ctx = request.context

        if task == "classify_institution":
            from backend.app.services.institution_service import institution_service

            raw_inst = str(ctx.get("institution_name", ""))
            norm, cat, tier, conf = institution_service.classify_institution(raw_inst)
            needs_escalation = cat == "Other" or conf < request.confidence_threshold
            return JevDecisionResponse(
                decision=cat,
                confidence=conf,
                rationale=f"Curated taxonomy lookup for '{raw_inst}' -> {cat} ({tier})",
                is_escalated=needs_escalation,
                metadata={
                    "latency_ms": latency_ms,
                    "canonical_name": norm,
                    "tier": tier,
                    "fallback": True,
                },
                source="deterministic",
            )

        if task == "classify_degree":
            from backend.app.services.education_service import EducationService

            raw_deg = str(ctx.get("raw_degree", ""))
            decision, conf = EducationService.normalize_degree(raw_deg)
            needs_escalation = decision == "Other" or conf < request.confidence_threshold
            return JevDecisionResponse(
                decision=decision,
                confidence=conf,
                rationale=f"Deterministic boundary check classified '{raw_deg}' as {decision}",
                is_escalated=needs_escalation,
                metadata={"latency_ms": latency_ms, "fallback": True},
                source="deterministic",
            )

        if task == "classify_role":
            from backend.app.services.experience_service import ExperienceService

            cat, conf = ExperienceService.categorize_employment_with_confidence(
                str(ctx.get("title", "")),
                str(ctx.get("organization", "")),
                str(ctx.get("description", "")),
            )
            return JevDecisionResponse(
                decision=cat,
                confidence=conf,
                rationale=f"Deterministic role check classified '{ctx.get('title', '')}' as {cat}",
                is_escalated=(conf < request.confidence_threshold),
                metadata={"latency_ms": latency_ms, "fallback": True},
                source="deterministic",
            )

        if task == "evaluate_rule":
            from backend.app.services.screening_service import screening_service

            op = str(ctx.get("operator", "=="))
            req = ctx.get("required_value")
            actual = ctx.get("candidate_value")
            passed, detail = screening_service._evaluate_condition(actual, op, req)
            return JevDecisionResponse(
                decision="pass" if passed else "fail",
                confidence=0.99,
                rationale=detail,
                is_escalated=False,
                metadata={"latency_ms": latency_ms},
                source="deterministic",
            )

        return JevDecisionResponse(
            decision="unresolved",
            confidence=0.5,
            rationale="No deterministic rule matched task",
            is_escalated=True,
            metadata={"latency_ms": latency_ms},
            source="fallback",
        )
