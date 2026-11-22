import time
import threading
import logging
from typing import List, Dict, Any, Optional
from groq import Groq, RateLimitError, APIConnectionError, APITimeoutError, InternalServerError
from backend.app.config import settings, config_manager

logger = logging.getLogger("FacultyScreen.GroqPool")


class KeyState:
    def __init__(self, key: str, index: int):
        self.key = key
        self.index = index
        pool_cfg = config_manager.get_pool_config()
        client_retries = int(pool_cfg["client_max_retries"])
        request_timeout = float(pool_cfg["request_timeout_seconds"])
        self.client = Groq(api_key=key, max_retries=client_retries, timeout=request_timeout)
        self.requests_count = 0
        self.cooldown_until = 0.0
        self.is_active = True

    @property
    def is_available(self) -> bool:
        return self.is_active and time.time() > self.cooldown_until

    def mark_rate_limited(self, duration_sec: Optional[float] = None):
        if duration_sec is None:
            duration_sec = float(config_manager.get_pool_config()["cooldown_seconds"])
        self.cooldown_until = time.time() + max(0.5, duration_sec)
        logger.warning(f"Groq Key #{self.index + 1} rate limited. Cooling down for {duration_sec:.1f}s.")


class GroqKeyPool:
    """
    Thread-safe Distributed Round-Robin Groq Client Pool Manager.
    Automatically rotates across multiple API keys, detects 429 rate limits and transient 5xx/timeouts,
    cools down exhausted keys without holding mutex locks while sleeping, and fails over cleanly.
    """

    def __init__(self, keys: Optional[List[str]] = None):
        raw_keys = keys if keys is not None else settings.get_all_groq_keys()
        self.key_states: List[KeyState] = [
            KeyState(k, i) for i, k in enumerate(raw_keys)
        ]
        self._current_idx = 0
        self._lock = threading.Lock()
        self.total_rotations = 0

        logger.info(f"Initialized GroqKeyPool with {len(self.key_states)} distributed API keys.")

    @property
    def size(self) -> int:
        return len(self.key_states)

    def get_next_client(self) -> KeyState:
        wait_time = 0.0
        with self._lock:
            if not self.key_states:
                raise RuntimeError("No Groq API keys configured in pool.")

            now = time.time()
            for _ in range(len(self.key_states)):
                candidate = self.key_states[self._current_idx]
                self._current_idx = (self._current_idx + 1) % len(self.key_states)
                if candidate.is_active and now > candidate.cooldown_until:
                    candidate.requests_count += 1
                    return candidate

            earliest = min(self.key_states, key=lambda k: k.cooldown_until)
            max_wait = float(config_manager.get_pool_config()["max_cooldown_wait_seconds"])
            raw_wait = max(0.0, earliest.cooldown_until - now)
            if 0.0 < raw_wait < max_wait:
                wait_time = raw_wait
            else:
                earliest.requests_count += 1
                return earliest

        if wait_time > 0.0:
            logger.info(f"All keys cooling down. Sleeping {wait_time:.1f}s outside lock for earliest key...")
            time.sleep(wait_time)

        with self._lock:
            now = time.time()
            for _ in range(len(self.key_states)):
                candidate = self.key_states[self._current_idx]
                self._current_idx = (self._current_idx + 1) % len(self.key_states)
                if candidate.is_active and now > candidate.cooldown_until:
                    candidate.requests_count += 1
                    return candidate
            earliest = min(self.key_states, key=lambda k: k.cooldown_until)
            earliest.requests_count += 1
            return earliest

    @staticmethod
    def _extract_retry_after(err: Exception, default_cooldown: float) -> float:
        resp = getattr(err, "response", None)
        headers = getattr(resp, "headers", None)
        if headers:
            retry_after = headers.get("retry-after") or headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return max(default_cooldown, float(retry_after))
                except (ValueError, TypeError):
                    pass
        return default_cooldown

    @staticmethod
    def _is_rate_limit_error(err: Exception) -> bool:
        if isinstance(err, RateLimitError):
            return True
        err_str = str(err).lower()
        return "rate limit" in err_str or "429" in err_str or "tokens per minute" in err_str

    @staticmethod
    def _is_transient_error(err: Exception) -> bool:
        if isinstance(err, (APIConnectionError, APITimeoutError, InternalServerError)):
            return True
        status_code = getattr(err, "status_code", None)
        if status_code in {500, 502, 503, 504}:
            return True
        err_str = str(err).lower()
        return any(tok in err_str for tok in ("timeout", "timed out", "connection reset", "temporarily unavailable", "502", "503", "504"))

    def execute_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: Optional[int] = None,
        **extra_kwargs
    ) -> Any:
        """
        Executes chat completion with automatic distributed key failover on 429s
        and exponential backoff on transient 5xx/network errors.
        """
        attempts = 0
        last_error: Optional[Exception] = None

        pool_cfg = config_manager.get_pool_config()
        groq_defaults = config_manager.get_groq_defaults()
        retries = max_retries if max_retries is not None else int(pool_cfg["max_retries"])
        tokens = max_tokens if max_tokens is not None else int(groq_defaults["max_tokens"])
        temp = temperature if temperature is not None else float(groq_defaults["temperature"])
        pacing = float(pool_cfg["pacing_delay_seconds"])
        cooldown_sec = float(pool_cfg["cooldown_seconds"])

        while attempts < retries:
            attempts += 1
            key_state = self.get_next_client()

            try:
                if pacing > 0:
                    time.sleep(pacing)

                kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temp,
                    "max_completion_tokens": tokens,
                    **extra_kwargs
                }
                if response_format:
                    kwargs["response_format"] = response_format

                return key_state.client.chat.completions.create(**kwargs)

            except Exception as e:
                if self._is_rate_limit_error(e):
                    dur = self._extract_retry_after(e, cooldown_sec)
                    with self._lock:
                        self.total_rotations += 1
                        key_state.mark_rate_limited(duration_sec=dur)
                    last_error = e
                    logger.info(f"Failing over to next available key in pool (Attempt {attempts}/{retries})...")
                    continue

                if self._is_transient_error(e):
                    last_error = e
                    backoff = min(2.0, 0.5 * (2 ** min(attempts - 1, 2)))
                    logger.warning(f"Transient Groq error on Key #{key_state.index + 1} (Attempt {attempts}/{retries}): {e}. Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                    continue

                raise e

        raise last_error or RuntimeError("Exceeded maximum Groq key rotation retries.")

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            return {
                "total_keys": len(self.key_states),
                "active_available_keys": sum(1 for k in self.key_states if k.is_active and now > k.cooldown_until),
                "rotations_handled": self.total_rotations,
                "key_distribution": [
                    {
                        "key_index": k.index + 1,
                        "requests": k.requests_count,
                        "cooling_down": not (k.is_active and now > k.cooldown_until),
                    }
                    for k in self.key_states
                ],
            }


groq_pool = GroqKeyPool()
