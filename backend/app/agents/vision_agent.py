import io
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pypdfium2 as pdfium
from PIL import Image

from backend.app.config import config_manager
from backend.app.groq.pool import groq_pool
from backend.app.utils.json_utils import parse_llm_json

logger = logging.getLogger("FacultyScreen.VisionAgent")

VISION_PROMPT = config_manager.get_prompt("vision_agent", "system")


class VisionAgent:
    """
    Agent responsible for Multimodal Visual Document Understanding.
    Supports PDF frame rendering and image formats (.png, .jpg, .jpeg, .webp),
    and extracts structured JSON via the distributed Groq Vision pool.
    """

    def __init__(self, model: Optional[str] = None):
        self._model_override = model

    @property
    def model(self) -> str:
        return self._model_override or config_manager.get_task_config("vision_agent", "vision")["model"]

    def render_pdf_frames(
        self,
        pdf_path: Path,
        max_pages: Optional[int] = None,
        task_name: str = "vision_agent",
    ) -> List[str]:
        v_cfg = config_manager.get_task_config(task_name, "vision")
        pages_limit = max_pages if max_pages is not None else int(v_cfg.get("max_pages", 2))
        render_scale = float(v_cfg.get("render_scale", 1.8))
        thumb_raw = v_cfg.get("thumbnail_size", [1500, 1500])
        thumb_size = (int(thumb_raw[0]), int(thumb_raw[1]))
        image_quality = int(v_cfg.get("image_quality", 85))

        data_urls: List[str] = []
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            pages = min(len(pdf), pages_limit)
            for i in range(pages):
                page = pdf[i]
                bitmap = page.render(scale=render_scale)
                pil_img = bitmap.to_pil()
                pil_img.thumbnail(thumb_size, Image.Resampling.LANCZOS)

                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=image_quality)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                data_urls.append(f"data:image/jpeg;base64,{b64}")
            pdf.close()
        except Exception as e:
            logger.error(f"Error rendering PDF frames for {pdf_path.name}: {e}")
        return data_urls

    def load_image_frames(self, file_path: Path, task_name: str = "vision_agent") -> List[str]:
        v_cfg = config_manager.get_task_config(task_name, "vision")
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self.render_pdf_frames(
                file_path,
                max_pages=int(v_cfg.get("max_pages", 2)),
                task_name=task_name,
            )

        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            thumb_raw = v_cfg.get("thumbnail_size", [1600, 1600])
            thumb_size = (int(thumb_raw[0]), int(thumb_raw[1]))
            image_quality = int(v_cfg.get("image_quality", 85))
            with Image.open(file_path) as img:
                rgb = img.convert("RGB")
                rgb.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                rgb.save(buf, format="JPEG", quality=image_quality)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                return [f"data:image/jpeg;base64,{b64}"]

        return []

    def extract_visual_facts(
        self,
        file_path: Path,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        task_name: str = "vision_agent",
        model_override: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Extracts structured facts from PDF/image files using distributed Groq Vision,
        returning (parsed_dict, was_repaired).
        """
        v_cfg = config_manager.get_task_config(task_name, "vision")
        data_urls = self.load_image_frames(file_path, task_name=task_name)
        if not data_urls:
            raise ValueError(f"Could not render visual frames from {file_path.name}")

        resolved_sys = system_prompt or config_manager.get_prompt("vision_agent", "system", default=VISION_PROMPT)
        resolved_user = user_prompt or config_manager.get_prompt(
            "vision_agent",
            "user",
            default="Extract all academic credentials and verifiable evidence snippets from these resume frames into strict JSON.",
        )

        content_items: List[Dict[str, Any]] = [{"type": "text", "text": resolved_user}]
        for url in data_urls:
            content_items.append({"type": "image_url", "image_url": {"url": url}})

        messages = [
            {"role": "system", "content": resolved_sys},
            {"role": "user", "content": content_items},
        ]

        chosen_model = model_override or self._model_override or v_cfg["model"]
        logger.info(f"VisionAgent invoking model '{chosen_model}' on {file_path.name} ({len(data_urls)} frames)")

        completion = groq_pool.execute_completion(
            model=chosen_model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=v_cfg["max_tokens"],
            temperature=v_cfg["temperature"],
            **v_cfg.get("extra_completion_kwargs", {}),
        )

        raw_json_str = (completion.choices[0].message.content or "").strip()
        return parse_llm_json(raw_json_str)

    def process_document(self, file_path: Path) -> Dict[str, Any]:
        parsed, _ = self.extract_visual_facts(file_path, task_name="vision_agent")
        if not parsed:
            raise ValueError(f"VisionAgent could not parse structured JSON from {file_path.name}")
        return parsed


vision_agent = VisionAgent()
