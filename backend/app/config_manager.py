import copy
import threading
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.utils.json_utils import atomic_write_text


class _LiteralDumper(yaml.SafeDumper):
    """YAML SafeDumper that renders multiline strings as clean literal blocks (|)."""


def _str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_LiteralDumper.add_representer(str, _str_representer)


_DEFAULT_SUPPORTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]
_DEFAULT_IGNORED_DIRECTORIES = [
    ".venv",
    "venv",
    "data",
    "apps",
    "backend",
    "tests",
    "scripts",
    "paddle_env",
    "node_modules",
    ".git",
]


class ConfigManager:
    """
    Thread-safe, hot-reloadable configuration manager for modular YAML configs:
    - config/app_config.yaml
    - config/llm_config.yaml
    - config/prompts.yaml
    """

    def __init__(self, config_dir: Path, env_settings: Any = None):
        self.config_dir = Path(config_dir)
        self.env_settings = env_settings
        self._lock = threading.RLock()
        self._app_config: Dict[str, Any] = {}
        self._llm_config: Dict[str, Any] = {}
        self._prompts: Dict[str, Any] = {}
        self.reload()

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}

    def _write_yaml(self, filename: str, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError(f"Configuration payload for {filename} must be a mapping")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        path = self.config_dir / filename
        serialized = yaml.dump(
            data,
            Dumper=_LiteralDumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        atomic_write_text(path, serialized)

    def reload(self) -> None:
        with self._lock:
            self._app_config = self._load_yaml("app_config.yaml")
            self._llm_config = self._load_yaml("llm_config.yaml")
            self._prompts = self._load_yaml("prompts.yaml")

    @property
    def app_config(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._app_config)

    @property
    def llm_config(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._llm_config)

    @property
    def prompts(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._prompts)

    def get_groq_models(self) -> Dict[str, str]:
        with self._lock:
            models = {
                "reasoning": getattr(self.env_settings, "groq_reasoning_model", "openai/gpt-oss-20b"),
                "vision": getattr(self.env_settings, "groq_vision_model", "qwen/qwen3.8-27b"),
                "advanced": getattr(self.env_settings, "groq_advanced_model", "openai/gpt-oss-120b"),
            }
            yaml_models = self._llm_config.get("groq", {}).get("models", {})
            if isinstance(yaml_models, dict):
                for key, val in yaml_models.items():
                    if isinstance(val, str) and val.strip():
                        models[key] = val.strip()
            return models

    def get_groq_defaults(self) -> Dict[str, Any]:
        with self._lock:
            defaults = {
                "max_tokens": int(getattr(self.env_settings, "groq_max_tokens", 800)),
                "temperature": float(getattr(self.env_settings, "groq_temperature", 0.1)),
            }
            yaml_defaults = self._llm_config.get("groq", {}).get("defaults", {})
            if isinstance(yaml_defaults, dict):
                if yaml_defaults.get("max_tokens") is not None:
                    defaults["max_tokens"] = int(yaml_defaults["max_tokens"])
                if yaml_defaults.get("temperature") is not None:
                    defaults["temperature"] = float(yaml_defaults["temperature"])
            return defaults

    def resolve_model(self, model_ref: Optional[str], fallback_alias: str = "reasoning") -> str:
        models = self.get_groq_models()
        if isinstance(model_ref, str) and model_ref.strip():
            cleaned = model_ref.strip()
            return models.get(cleaned, cleaned)
        return models.get(fallback_alias, models["reasoning"])

    def get_task_config(self, task_name: str, fallback_alias: str = "reasoning") -> Dict[str, Any]:
        with self._lock:
            raw = self._llm_config.get("tasks", {}).get(task_name, {})
            cfg = copy.deepcopy(raw) if isinstance(raw, dict) else {}

        defaults = self.get_groq_defaults()
        cfg["model"] = self.resolve_model(cfg.get("model"), fallback_alias=fallback_alias)
        if cfg.get("max_tokens") is None:
            cfg["max_tokens"] = defaults["max_tokens"]
        else:
            cfg["max_tokens"] = int(cfg["max_tokens"])

        if cfg.get("temperature") is None:
            cfg["temperature"] = defaults["temperature"]
        else:
            cfg["temperature"] = float(cfg["temperature"])

        extra_kwargs: Dict[str, Any] = {}
        for opt_key in ("reasoning_format", "reasoning_effort"):
            val = cfg.get(opt_key)
            if isinstance(val, str) and val.strip():
                extra_kwargs[opt_key] = val.strip()
        if cfg.get("top_p") is not None:
            extra_kwargs["top_p"] = float(cfg["top_p"])
        cfg["extra_completion_kwargs"] = extra_kwargs
        return cfg

    def get_pool_config(self) -> Dict[str, Any]:
        with self._lock:
            pool_cfg = self._llm_config.get("groq", {}).get("pool", {})
            if not isinstance(pool_cfg, dict):
                pool_cfg = {}
            return {
                "cooldown_seconds": float(pool_cfg.get("cooldown_seconds", 8.0)),
                "max_cooldown_wait_seconds": float(pool_cfg.get("max_cooldown_wait_seconds", 5.0)),
                "max_retries": int(pool_cfg.get("max_retries", 12)),
                "pacing_delay_seconds": float(pool_cfg.get("pacing_delay_seconds", 0.1)),
                "client_max_retries": int(pool_cfg.get("client_max_retries", 0)),
                "request_timeout_seconds": float(pool_cfg.get("request_timeout_seconds", 60.0)),
            }

    def get_jev_config(self) -> Dict[str, Any]:
        with self._lock:
            jev_cfg = self._llm_config.get("jev", {})
            if not isinstance(jev_cfg, dict):
                jev_cfg = {}
            default_model = getattr(self.env_settings, "jev_model", "jev-v1-fast")
            default_url = getattr(self.env_settings, "typesafe_base_url", "https://api.typesafe.ai")
            model_val = jev_cfg.get("model") or default_model
            url_val = jev_cfg.get("base_url") or default_url
            return {
                "model": str(model_val),
                "base_url": str(url_val).rstrip("/"),
                "timeout_seconds": float(jev_cfg.get("timeout_seconds", 5.0)),
                "confidence_threshold": float(jev_cfg.get("confidence_threshold", 0.85)),
            }

    def get_prompt(self, section: str, key: str, default: str = "", **kwargs: Any) -> str:
        with self._lock:
            sec = self._prompts.get(section, {})
            template = sec.get(key) if isinstance(sec, dict) else None
            if template is None:
                template = default
            text = str(template)
        if kwargs:
            return text.format(**kwargs)
        return text

    def get_pipeline_config(self) -> Dict[str, Any]:
        with self._lock:
            raw = self._app_config.get("pipeline", {})
            if not isinstance(raw, dict):
                raw = {}
            return {
                "version": str(raw.get("version", "1.0.0")),
                "agentic_version": str(raw.get("agentic_version", "2.0.0-agentic")),
                "vision_scale": float(raw.get("vision_scale", 2.0)),
                "image_quality": int(raw.get("image_quality", 85)),
                "max_pages_per_resume": int(raw.get("max_pages_per_resume", 8)),
                "cache_processed_results": bool(raw.get("cache_processed_results", True)),
                "hash_algorithm": str(raw.get("hash_algorithm", "sha256")),
                "supported_extensions": list(raw.get("supported_extensions") or _DEFAULT_SUPPORTED_EXTENSIONS),
                "ignored_directories": list(raw.get("ignored_directories") or _DEFAULT_IGNORED_DIRECTORIES),
                "batch_upload_delay_seconds": float(raw.get("batch_upload_delay_seconds", 0.3)),
                "max_upload_size_mb": int(raw.get("max_upload_size_mb", 25)),
            }

    def get_review_config(self) -> Dict[str, Any]:
        with self._lock:
            raw = self._app_config.get("review", {})
            if not isinstance(raw, dict):
                raw = {}
            return {
                "high_confidence_threshold": float(raw.get("high_confidence_threshold", 0.90)),
                "queue_confidence_threshold": float(raw.get("queue_confidence_threshold", 0.85)),
                "queue_min_teaching_years": float(raw.get("queue_min_teaching_years", 2.0)),
            }

    def get_taxonomy(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        with self._lock:
            taxonomy = self._app_config.get("taxonomy", {})
            if isinstance(taxonomy, dict) and isinstance(taxonomy.get(key), list):
                return list(taxonomy[key])
            return list(default) if default is not None else []

    def get_enrichment_config(self) -> Dict[str, Any]:
        with self._lock:
            raw = self._app_config.get("external_enrichment", {})
            if not isinstance(raw, dict):
                raw = {}
            return {
                "enabled": bool(raw.get("enabled", True)),
                "timeout_seconds": float(raw.get("timeout_seconds", 5.0)),
                "enable_orcid_api": bool(raw.get("enable_orcid_api", True)),
                "enable_openalex_api": bool(raw.get("enable_openalex_api", True)),
                "cache_ttl_hours": int(raw.get("cache_ttl_hours", 168)),
            }

    def get_evaluation_config(self) -> Dict[str, Any]:
        with self._lock:
            raw = self._app_config.get("evaluation", {})
            if not isinstance(raw, dict):
                raw = {}
            weights_raw = raw.get("default_weights", {})
            if not isinstance(weights_raw, dict):
                weights_raw = {}
            return {
                "allow_compensating_strengths": bool(raw.get("allow_compensating_strengths", True)),
                "default_weights": {
                    "requirement_fit": float(weights_raw.get("requirement_fit", 0.35)),
                    "domain_semantic_fit": float(weights_raw.get("domain_semantic_fit", 0.25)),
                    "teaching_fit": float(weights_raw.get("teaching_fit", 0.15)),
                    "research_and_impact": float(weights_raw.get("research_and_impact", 0.15)),
                    "alternative_strength_credit": float(weights_raw.get("alternative_strength_credit", 0.10)),
                },
                "strong_match_threshold": float(raw.get("strong_match_threshold", 78.0)),
                "alternative_fit_threshold": float(raw.get("alternative_fit_threshold", 65.0)),
                "conditional_threshold": float(raw.get("conditional_threshold", 50.0)),
            }

    def get_resolved_task_models(self) -> Dict[str, str]:
        with self._lock:
            task_names = list((self._llm_config.get("tasks") or {}).keys())
        return {name: self.get_task_config(name)["model"] for name in task_names}

    def update_llm_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("LLM configuration payload must be an object")
        if "providers" in data and "groq" not in data:
            raise ValueError("Invalid LLM schema: expected top-level 'groq' and 'tasks' sections")
        if not isinstance(data.get("groq"), dict) or not isinstance(data.get("tasks"), dict):
            raise ValueError("LLM configuration must contain 'groq' and 'tasks' mapping sections")
        if not isinstance(data["groq"].get("models"), dict):
            raise ValueError("LLM configuration 'groq.models' must be a mapping")
        with self._lock:
            self._write_yaml("llm_config.yaml", data)
            self.reload()
            return self.llm_config

    def update_prompts(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict) or not data:
            raise ValueError("Prompts payload must be a non-empty mapping of sections")
        for section, entries in data.items():
            if not isinstance(entries, dict):
                raise ValueError(f"Prompt section '{section}' must be a mapping")
            for k, v in entries.items():
                if not isinstance(v, str):
                    raise ValueError(f"Prompt '{section}.{k}' must be a string")
        with self._lock:
            self._write_yaml("prompts.yaml", data)
            self.reload()
            return self.prompts

    def update_app_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("App configuration payload must be a mapping")
        if not any(isinstance(data.get(sec), dict) for sec in ("pipeline", "review", "taxonomy")):
            raise ValueError("App configuration must contain at least one of 'pipeline', 'review', or 'taxonomy'")
        with self._lock:
            self._write_yaml("app_config.yaml", data)
            self.reload()
            return self.app_config
