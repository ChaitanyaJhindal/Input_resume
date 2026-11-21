import time
import httpx
import logging
from typing import Optional, Dict, Any
from backend.app.core.config import settings
from backend.app.services.jev.jev_schemas import JevDecisionRequest, JevDecisionResponse

logger = logging.getLogger("FacultyScreen.JEV")

class JevClient:
    """
    Client for TypeSafe AI / JEV fast structured decision layer.
    Gracefully falls back to deterministic decisioning when API keys are not provided
    or when network endpoints are unreachable.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.typesafe_api_key
        self.base_url = (base_url or settings.typesafe_base_url).rstrip("/")
        self.model = model or settings.jev_model
        self.timeout = 5.0  # Fast sub-second SLA expected for JEV

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def execute_decision(self, request: JevDecisionRequest) -> JevDecisionResponse:
        """
        Executes a structured decision call.
        If JEV API key is not configured or fails, falls back gracefully.
        """
        start_time = time.time()

        if not self.is_configured:
            # Deterministic / local heuristics fallback
            return self._local_fallback(request, latency_ms=(time.time() - start_time) * 1000)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FacultyScreen-Engine/1.0"
        }

        payload = {
            "model": self.model,
            "task": request.task,
            "context": request.context,
            "candidate_options": request.candidate_options,
            "confidence_threshold": request.confidence_threshold
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/v1/decisions", json=payload, headers=headers)
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    return JevDecisionResponse(
                        decision=data.get("decision", ""),
                        confidence=float(data.get("confidence", 0.95)),
                        rationale=data.get("rationale", "JEV structured evaluation"),
                        is_escalated=bool(data.get("is_escalated", False)),
                        metadata={"latency_ms": latency_ms, "model": self.model},
                        source="jev"
                    )
                else:
                    logger.warning(f"JEV API returned status {resp.status_code}. Using deterministic fallback.")
                    return self._local_fallback(request, latency_ms=latency_ms)

        except Exception as e:
            logger.warning(f"JEV service connection failed: {e}. Gracefully reverting to deterministic fallback.")
            latency_ms = (time.time() - start_time) * 1000
            return self._local_fallback(request, latency_ms=latency_ms)

    def _local_fallback(self, request: JevDecisionRequest, latency_ms: float = 0.5) -> JevDecisionResponse:
        """
        High-speed deterministic fallback implementing JEV contract locally.
        """
        task = request.task
        ctx = request.context

        if task == "classify_institution":
            name = str(ctx.get("institution_name", "")).lower()
            if "indian institute of technology" in name or "iit" in name:
                decision = "IIT"
            elif "national institute of technology" in name or "nit" in name:
                decision = "NIT"
            elif "international institute of information technology" in name or "iiit" in name or "indian institute of information technology" in name:
                decision = "IIIT"
            elif "university" in name:
                if any(u in name for u in ["delhi", "hyderabad", "jnu", "bhu", "aligarh", "amu", "central"]):
                    decision = "Central University"
                else:
                    decision = "State University"
            elif "institute of science" in name or "research" in name or "laboratory" in name:
                decision = "Research Institute"
            else:
                decision = "Private University" if "private" in name or "amity" in name or "thapar" in name or "vit" in name or "manipal" in name else "Other"

            return JevDecisionResponse(
                decision=decision,
                confidence=0.92,
                rationale=f"Deterministic fallback matched institution pattern for '{ctx.get('institution_name')}'",
                is_escalated=False,
                metadata={"latency_ms": latency_ms, "fallback": True},
                source="deterministic"
            )

        elif task == "classify_degree":
            raw = str(ctx.get("raw_degree", "")).lower()
            if any(k in raw for k in ["phd", "ph.d", "doctorate", "d.phil", "doctor of philosophy"]):
                decision = "PhD / Doctorate"
            elif any(k in raw for k in ["postdoc", "post doctoral", "post-doc"]):
                decision = "Postdoctoral"
            elif any(k in raw for k in ["m.tech", "mtech", "m.s", "ms", "m.e", "m.sc", "msc", "mba", "mca", "master"]):
                decision = "Postgraduate / Masters"
            elif any(k in raw for k in ["b.tech", "btech", "b.e", "be", "b.sc", "bsc", "bca", "bachelor"]):
                decision = "Undergraduate"
            elif "diploma" in raw:
                decision = "Diploma"
            else:
                decision = "Other"

            return JevDecisionResponse(
                decision=decision,
                confidence=0.94,
                rationale=f"Deterministic fallback classified degree string '{ctx.get('raw_degree')}'",
                is_escalated=False,
                metadata={"latency_ms": latency_ms, "fallback": True},
                source="deterministic"
            )

        elif task == "evaluate_rule":
            # Fast check
            op = ctx.get("operator", "==")
            req = ctx.get("required_value")
            actual = ctx.get("candidate_value")

            passed = False
            if op == ">=":
                passed = float(actual or 0) >= float(req or 0)
            elif op == "in":
                passed = actual in (req if isinstance(req, list) else [req])
            elif op == "==":
                passed = actual == req

            return JevDecisionResponse(
                decision="pass" if passed else "fail",
                confidence=0.99,
                rationale=f"Rule evaluated '{actual}' {op} '{req}'",
                is_escalated=False,
                metadata={"latency_ms": latency_ms},
                source="deterministic"
            )

        return JevDecisionResponse(
            decision="unresolved",
            confidence=0.5,
            rationale="No deterministic rule matched task",
            is_escalated=True,
            metadata={"latency_ms": latency_ms},
            source="fallback"
        )
