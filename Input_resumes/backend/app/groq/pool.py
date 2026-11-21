import time
import threading
import logging
from typing import List, Dict, Any, Optional
from groq import Groq, RateLimitError
from backend.app.config import settings

logger = logging.getLogger("FacultyScreen.GroqPool")

class KeyState:
    def __init__(self, key: str, index: int):
        self.key = key
        self.index = index
        self.client = Groq(api_key=key, max_retries=0)
        self.requests_count = 0
        self.cooldown_until = 0.0
        self.is_active = True

    @property
    def is_available(self) -> bool:
        return self.is_active and time.time() > self.cooldown_until

    def mark_rate_limited(self, duration_sec: float = 8.0):
        self.cooldown_until = time.time() + duration_sec
        logger.warning(f"Groq Key #{self.index + 1} ({self.key[:10]}...) rate limited. Cooling down for {duration_sec}s.")

class GroqKeyPool:
    """
    Distributed Round-Robin Groq Client Pool Manager.
    Automatically rotates across multiple API keys, detects 429 rate limits,
    cools down exhausted keys, and fails over to the next key seamlessly.
    """

    def __init__(self, keys: Optional[List[str]] = None):
        raw_keys = keys or settings.get_all_groq_keys()
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
        with self._lock:
            if not self.key_states:
                raise RuntimeError("No Groq API keys configured in pool.")

            # Search for available key
            now = time.time()
            for _ in range(len(self.key_states)):
                candidate = self.key_states[self._current_idx]
                self._current_idx = (self._current_idx + 1) % len(self.key_states)
                if candidate.is_available:
                    candidate.requests_count += 1
                    return candidate

            # If all are cooling down, select the one with earliest cooldown expiry
            earliest = min(self.key_states, key=lambda k: k.cooldown_until)
            wait_time = max(0.0, earliest.cooldown_until - now)
            if wait_time > 0 and wait_time < 5.0:
                logger.info(f"All keys cooling down. Sleeping {wait_time:.1f}s for earliest key...")
                time.sleep(wait_time)
            earliest.requests_count += 1
            return earliest

    def execute_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 12,
        **extra_kwargs
    ) -> Any:
        """
        Executes chat completion with automatic distributed key failover on 429 errors.
        """
        attempts = 0
        last_error = None

        tokens = max_tokens or settings.groq_max_tokens
        temp = temperature if temperature is not None else settings.groq_temperature

        while attempts < max_retries:
            attempts += 1
            key_state = self.get_next_client()

            try:
                # Small inter-request pacing (100ms) to prevent burst drops
                time.sleep(0.1)

                kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temp,
                    "max_completion_tokens": tokens,
                    **extra_kwargs
                }
                if response_format:
                    kwargs["response_format"] = response_format

                completion = key_state.client.chat.completions.create(**kwargs)
                return completion

            except RateLimitError as e:
                self.total_rotations += 1
                key_state.mark_rate_limited(duration_sec=8.0)
                last_error = e
                logger.info(f"Failing over to next available key in pool (Attempt {attempts}/{max_retries})...")
                continue

            except Exception as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "429" in err_str or "tokens per minute" in err_str:
                    self.total_rotations += 1
                    key_state.mark_rate_limited(duration_sec=8.0)
                    last_error = e
                    continue
                else:
                    # Non-rate-limit error (e.g., bad parameter)
                    raise e

        raise last_error or RuntimeError("Exceeded maximum Groq key rotation retries.")

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "total_keys": len(self.key_states),
            "active_available_keys": sum(1 for k in self.key_states if k.is_available),
            "rotations_handled": self.total_rotations,
            "key_distribution": [
                {"key_index": k.index + 1, "requests": k.requests_count, "cooling_down": not k.is_available}
                for k in self.key_states
            ]
        }

groq_pool = GroqKeyPool()
