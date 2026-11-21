import io
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pypdfium2 as pdfium
from PIL import Image

from backend.app.core.config import settings
from backend.app.integrations.groq.groq_pool import groq_pool

logger = logging.getLogger("FacultyScreen.VisionAgent")

VISION_PROMPT = """You are a senior academic document understanding agent and OCR vision engine.
Read the provided resume image frames and extract structured academic credentials into strict JSON.

CRITICAL INSTRUCTIONS:
1. Never hallucinate or fabricate missing credentials. Return null or empty lists if not explicitly present.
2. For every education entry, job title, and publication, provide the exact verbatim source evidence snippet from the document.
3. Preserve exact wording for degrees, institutions, and research domains.
4. Output ONLY valid JSON matching this schema:

{
  "name": "Full Name",
  "email": "email@example.com or null",
  "phone": "phone or null",
  "location": "location or null",
  "current_designation": "title or null",
  "summary": "1-2 sentence profile summary or null",
  "education": [
    {
      "degree": "Exact degree text",
      "field": "Specialization or branch",
      "institution": "Exact institution text",
      "graduation_year": 2020,
      "confidence": 0.95,
      "evidence": "Exact source quote citing degree and institution",
      "source_page": 1
    }
  ],
  "employment": [
    {
      "title": "Exact job title",
      "organization": "Exact organization name",
      "category": "teaching|research|industry|administrative",
      "start_date": "2020",
      "end_date": "Present",
      "duration_years": 4.0,
      "is_current": true,
      "description": "Responsibilities and lecture topics",
      "evidence": "Exact line showing appointment and duration",
      "source_page": 1
    }
  ],
  "research": {
    "publications": [
      {
        "title": "Paper Title",
        "venue": "Journal or Conference",
        "year": 2023,
        "doi": "10.1109/...",
        "indexed": "Scopus, SCI or Peer-Reviewed",
        "evidence": "Citation text from CV"
      }
    ],
    "patents": [],
    "research_projects": [],
    "research_domains": ["Area 1", "Area 2"]
  },
  "certifications": [],
  "awards": [],
  "skills": [],
  "source_evidence": [
    {
      "field": "highest_degree",
      "value": "PhD",
      "evidence": "Exact text quote",
      "source_page": 1,
      "confidence": 0.95
    }
  ]
}
"""

class VisionAgent:
    """
    Agent responsible for Multimodal Visual Document Understanding.
    Uses Groq Qwen Vision (qwen/qwen3.8-27b) via the distributed key pool.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.groq_vision_model

    def render_pdf_frames(self, pdf_path: Path, max_pages: int = 2) -> List[str]:
        data_urls = []
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            pages = min(len(pdf), max_pages)
            for i in range(pages):
                page = pdf[i]
                bitmap = page.render(scale=1.8)
                pil_img = bitmap.to_pil()
                pil_img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)

                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=85)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                data_urls.append(f"data:image/jpeg;base64,{b64}")
            pdf.close()
        except Exception as e:
            logger.error(f"Error rendering PDF frames for {pdf_path.name}: {e}")
        return data_urls

    def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Extracts structured facts from PDF/image files using distributed Groq Vision.
        """
        # Render image frames
        data_urls = []
        if file_path.suffix.lower() == ".pdf":
            data_urls = self.render_pdf_frames(file_path, max_pages=2)
        elif file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                mime = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
                data_urls.append(f"data:{mime};base64,{b64}")

        if not data_urls:
            raise ValueError(f"Could not render visual frames from {file_path.name}")

        content_items: List[Dict[str, Any]] = [
            {"type": "text", "text": "Extract all academic credentials and verifiable evidence snippets from these resume frames into strict JSON."}
        ]
        for url in data_urls:
            content_items.append({"type": "image_url", "image_url": {"url": url}})

        messages = [
            {"role": "system", "content": VISION_PROMPT},
            {"role": "user", "content": content_items}
        ]

        logger.info(f"VisionAgent invoking model '{self.model}' on {file_path.name} ({len(data_urls)} frames)")

        completion = groq_pool.execute_completion(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=settings.groq_max_tokens,
            temperature=settings.groq_temperature
        )

        raw_json_str = completion.choices[0].message.content.strip()
        parsed = json.loads(raw_json_str)
        return parsed

vision_agent = VisionAgent()
