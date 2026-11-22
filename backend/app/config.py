import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FacultyScreen"
    environment: str = "development"
    debug: bool = True
    mock_mode: bool = False

    host: str = "127.0.0.1"
    port: int = 8000
    frontend_port: int = 3000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    def get_cors_origins(self) -> List[str]:
        origins = [o.strip() for o in (self.cors_origins or "").split(",") if o.strip()]
        return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Path to resumes folder (defaults to workspace directory containing PDF resumes)
    resumes_dir: str = "./Input_resumes"

    # Groq Multi-Key & Multi-Model Settings
    groq_api_keys: str = ""
    groq_api_key: str = ""
    groq_vision_model: str = "qwen/qwen3.8-27b"
    groq_reasoning_model: str = "openai/gpt-oss-20b"
    groq_advanced_model: str = "openai/gpt-oss-120b"
    groq_max_tokens: int = 800
    groq_temperature: float = 0.1

    # TypeSafe / JEV Settings
    typesafe_api_key: str = ""
    jev_model: str = "jev-v1-fast"
    typesafe_base_url: str = "https://api.typesafe.ai"

    # Database
    database_url: str = "sqlite:///./data/facultyscreen.db"

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    config_dir: Path = base_dir / "config"
    data_dir: Path = base_dir / "data"

    def get_all_groq_keys(self) -> List[str]:
        keys = []
        if self.groq_api_keys:
            for k in self.groq_api_keys.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)
        if self.groq_api_key and self.groq_api_key.strip() not in keys:
            keys.append(self.groq_api_key.strip())
        return [k for k in keys if k.startswith("gsk_")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

# Enable mock mode only if no valid Groq keys exist
if not settings.get_all_groq_keys():
    settings.mock_mode = True
else:
    settings.mock_mode = False

from backend.app.config_manager import ConfigManager

config_manager = ConfigManager(settings.config_dir, settings)
