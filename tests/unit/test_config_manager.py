import shutil
from pathlib import Path

import yaml

from backend.app.agents.education_agent import EducationAgent
from backend.app.agents.experience_agent import ExperienceAgent
from backend.app.agents.institution_agent import InstitutionAgent
from backend.app.agents.vision_agent import VisionAgent
from backend.app.config import config_manager, settings
from backend.app.config_manager import ConfigManager
from backend.app.groq.extractor import GroqExtractor
from backend.app.services.jev.jev_client import JevClient


def test_real_configs_loaded():
    models = config_manager.get_groq_models()
    assert models["reasoning"] == "openai/gpt-oss-20b"
    assert models["vision"] == "qwen/qwen3.8-27b"
    assert models["advanced"] == "openai/gpt-oss-120b"

    resolved = config_manager.get_resolved_task_models()
    assert resolved["text_extraction"] == "openai/gpt-oss-20b"
    assert resolved["vision_extraction"] == "qwen/qwen3.8-27b"
    assert resolved["vision_agent"] == "qwen/qwen3.8-27b"
    assert resolved["education_agent"] == "openai/gpt-oss-20b"
    assert resolved["institution_agent"] == "openai/gpt-oss-20b"
    assert resolved["experience_agent"] == "openai/gpt-oss-20b"
    assert resolved["cli_markdown_parser"] == "qwen/qwen3.8-27b"

    for section in ("extractor", "vision_agent", "education_agent", "institution_agent", "experience_agent", "cli_markdown_parser"):
        assert section in config_manager.prompts


def test_model_alias_and_literal_resolution():
    assert config_manager.resolve_model("reasoning") == "openai/gpt-oss-20b"
    assert config_manager.resolve_model("vision") == "qwen/qwen3.8-27b"
    assert config_manager.resolve_model("llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"
    assert config_manager.resolve_model(None, fallback_alias="vision") == "qwen/qwen3.8-27b"


def test_task_inheritance_and_optional_reasoning_kwargs():
    vision_task = config_manager.get_task_config("vision_extraction", "vision")
    assert vision_task["model"] == "qwen/qwen3.8-27b"
    assert vision_task["max_tokens"] == 800
    assert vision_task["temperature"] == 0.1
    assert vision_task["extra_completion_kwargs"] == {}

    exp_task = config_manager.get_task_config("experience_agent", "reasoning")
    assert exp_task["extra_completion_kwargs"] == {"reasoning_format": "hidden"}

    text_task = config_manager.get_task_config("text_extraction", "reasoning")
    assert text_task["max_tokens"] == 4096
    assert text_task["extra_completion_kwargs"] == {
        "reasoning_format": "hidden",
        "reasoning_effort": "low",
    }


def test_prompt_template_rendering_with_json_braces():
    instructions = config_manager.get_prompt("extractor", "extraction_instructions")
    assert '"name": "Candidate Full Name"' in instructions

    rendered = config_manager.get_prompt(
        "extractor",
        "text_user_template",
        extraction_instructions=instructions,
        document_text="Dr. Jane Doe\nPhD IIT Delhi",
    )
    assert '"name": "Candidate Full Name"' in rendered
    assert "Document Text:\nDr. Jane Doe\nPhD IIT Delhi" in rendered


def test_hot_reload_and_persistence_in_tmp_dir(tmp_path: Path):
    for name in ("app_config.yaml", "llm_config.yaml", "prompts.yaml"):
        shutil.copy(settings.config_dir / name, tmp_path / name)

    mgr = ConfigManager(tmp_path, settings)
    assert mgr.resolve_model("reasoning") == "openai/gpt-oss-20b"

    updated_llm = mgr.llm_config
    updated_llm["groq"]["models"]["reasoning"] = "llama-3.3-70b-versatile"
    updated_llm["tasks"]["education_agent"]["model"] = "custom-deg-model"
    updated_llm["tasks"]["education_agent"]["reasoning_format"] = None
    updated_llm["tasks"]["education_agent"]["reasoning_effort"] = None
    mgr.update_llm_config(updated_llm)

    assert mgr.resolve_model("reasoning") == "llama-3.3-70b-versatile"
    edu_cfg = mgr.get_task_config("education_agent")
    assert edu_cfg["model"] == "custom-deg-model"
    assert edu_cfg["extra_completion_kwargs"] == {}

    updated_prompts = mgr.prompts
    updated_prompts["education_agent"]["user_template"] = "Classify: {raw_degree}"
    mgr.update_prompts(updated_prompts)
    assert mgr.get_prompt("education_agent", "user_template", raw_degree="PhD") == "Classify: PhD"

    # Verify disk file persisted cleanly
    reloaded_disk = yaml.safe_load((tmp_path / "llm_config.yaml").read_text(encoding="utf-8"))
    assert reloaded_disk["groq"]["models"]["reasoning"] == "llama-3.3-70b-versatile"


def test_agents_and_clients_respect_overrides_and_defaults():
    assert GroqExtractor().model == "qwen/qwen3.8-27b"
    assert GroqExtractor(model="custom-vision").model == "custom-vision"

    assert VisionAgent().model == "qwen/qwen3.8-27b"
    assert VisionAgent(model="custom-vision-2").model == "custom-vision-2"

    assert EducationAgent().reasoning_model == "openai/gpt-oss-20b"
    assert EducationAgent(reasoning_model="custom-edu").reasoning_model == "custom-edu"

    assert InstitutionAgent().reasoning_model == "openai/gpt-oss-20b"
    assert InstitutionAgent(reasoning_model="custom-inst").reasoning_model == "custom-inst"

    assert ExperienceAgent().reasoning_model == "openai/gpt-oss-20b"
    assert ExperienceAgent(reasoning_model="custom-exp").reasoning_model == "custom-exp"

    jev_default = JevClient()
    assert jev_default.model == "jev-v1-fast"
    assert jev_default.timeout == 5.0
    jev_custom = JevClient(base_url="https://custom.example/", model="jev-custom", timeout=2.5)
    assert jev_custom.base_url == "https://custom.example"
    assert jev_custom.model == "jev-custom"
    assert jev_custom.timeout == 2.5
