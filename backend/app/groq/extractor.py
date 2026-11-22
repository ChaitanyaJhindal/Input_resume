import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pypdfium2 as pdfium
from groq import Groq

from backend.app.agents.vision_agent import vision_agent
from backend.app.config import settings, config_manager
from backend.app.groq.pool import groq_pool
from backend.app.utils.json_utils import parse_llm_json
from backend.app.utils.link_extractor import extract_academic_links

logger = logging.getLogger("FacultyScreen.GroqExtractor")

EXTRACTION_SYSTEM_PROMPT = config_manager.get_prompt("extractor", "extraction_instructions")


class GroqExtractor:
    """
    Multimodal Document Understanding Engine powered by Groq Text Reasoning & Vision.
    Extracts embedded PDF text cleanly or renders visual frames via VisionAgent.
    Never invents synthetic fallback profiles when mock_mode=False.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self._model_override = model
        self.client = None
        if self.api_key and len(self.api_key.strip()) > 10:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")

    @property
    def model(self) -> str:
        return self._model_override or config_manager.get_task_config("vision_extraction", "vision")["model"]

    @property
    def is_available(self) -> bool:
        return (groq_pool.size > 0 or self.client is not None) and not settings.mock_mode

    def render_pdf_to_images(self, pdf_path: Path, max_pages: Optional[int] = None) -> List[str]:
        return vision_agent.render_pdf_frames(
            pdf_path, max_pages=max_pages, task_name="vision_extraction"
        )

    def _robust_json_parse_with_status(self, raw_text: Optional[str]) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Delegates to shared string-aware LIFO JSON parser/repairer."""
        return parse_llm_json(raw_text)

    def _robust_json_parse(self, raw_text: Optional[str]) -> Optional[Dict[str, Any]]:
        parsed, _ = parse_llm_json(raw_text)
        return parsed

    def extract_raw_text(self, file_path: Path) -> Tuple[str, int]:
        """Extracts embedded text and exact page count using pypdfium2."""
        full_text = ""
        page_count = 1
        try:
            if file_path.suffix.lower() == ".pdf":
                doc = pdfium.PdfDocument(str(file_path))
                page_count = max(1, len(doc))
                for i in range(len(doc)):
                    full_text += f"\n--- Page {i+1} ---\n" + doc[i].get_textpage().get_text_range()
                doc.close()
        except Exception as e:
            logger.debug(f"Error reading PDF text with pypdfium2 for {file_path.name}: {e}")
        return full_text, page_count

    @staticmethod
    def _clean_name_from_filename(file_path: Path) -> str:
        stem = file_path.stem
        clean_name = (
            stem.replace("Naukri_", "")
            .replace("-CV", "")
            .replace("_CV", "")
            .replace(".docx", "")
            .replace(".doc", "")
            .replace(".PDF", "")
        )
        clean_name = re.sub(r"\[.*?\]", "", clean_name)
        clean_name = re.sub(r"\(.*?\)", "", clean_name)
        clean_name = re.sub(r"_\d+", "", clean_name)
        clean_name = clean_name.replace("_", " ").replace("-", " ").strip()
        if not clean_name or len(clean_name) < 3:
            return "Candidate " + stem[:8]
        return clean_name.title()

    def _call_text_completion(self, t_cfg: Dict[str, Any], messages: List[Dict[str, Any]]) -> Any:
        try:
            return groq_pool.execute_completion(
                model=t_cfg["model"],
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=t_cfg["max_tokens"],
                temperature=t_cfg["temperature"],
                **t_cfg.get("extra_completion_kwargs", {}),
            )
        except Exception as e:
            if "response_format" in str(e).lower() or "json_object" in str(e).lower():
                logger.info("Retrying text completion without response_format constraint...")
                return groq_pool.execute_completion(
                    model=t_cfg["model"],
                    messages=messages,
                    max_tokens=t_cfg["max_tokens"],
                    temperature=t_cfg["temperature"],
                    **t_cfg.get("extra_completion_kwargs", {}),
                )
            raise

    def extract_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Processes a resume file through Groq LLM (with full multi-page text) or VisionAgent.
        Never fabricates synthetic profiles when running in live mode (mock_mode=False).
        """
        full_text, page_count = self.extract_raw_text(file_path)
        extracted_links = [lnk.model_dump() for lnk in extract_academic_links(file_path, full_text)]

        if settings.mock_mode:
            mock_data = self._generate_realistic_profile_from_file(file_path)
            mock_data["_raw_text"] = full_text
            mock_data["_page_count"] = page_count
            mock_data["_academic_links"] = extracted_links
            mock_data["_extraction_method"] = "mock"
            mock_data["_model_used"] = "mock"
            mock_data["_groq_calls"] = 0
            mock_data["_json_repaired"] = False
            return mock_data

        groq_calls = 0
        last_error: Optional[str] = None

        t_cfg = config_manager.get_task_config("text_extraction", "reasoning")
        min_text_chars = int(t_cfg.get("min_text_chars", 100))
        max_text_chars = int(t_cfg.get("max_text_chars", 28000))
        extraction_instructions = config_manager.get_prompt(
            "extractor", "extraction_instructions", default=EXTRACTION_SYSTEM_PROMPT
        )

        # STAGE 2: Groq Reasoning Text Extraction
        if len(full_text.strip()) > min_text_chars and groq_pool.size > 0:
            try:
                prompt_text = full_text[:max_text_chars]
                text_system = config_manager.get_prompt(
                    "extractor",
                    "text_system",
                    default="You are a senior academic recruitment document parser and visual OCR engine. Output ONLY valid JSON matching the schema.",
                )
                text_user = config_manager.get_prompt(
                    "extractor",
                    "text_user_template",
                    default="{extraction_instructions}\n\nDocument Text:\n{document_text}",
                    extraction_instructions=extraction_instructions,
                    document_text=prompt_text,
                )
                messages = [
                    {"role": "system", "content": text_system},
                    {"role": "user", "content": text_user},
                ]

                logger.info(f"Extracting 100% REAL facts for {file_path.name} via Groq Key Pool ({t_cfg['model']})...")
                groq_calls += 1
                completion = self._call_text_completion(t_cfg, messages)
                raw_text = (completion.choices[0].message.content or "").strip()

                parsed, was_repaired = parse_llm_json(raw_text)
                if parsed and (parsed.get("name") or parsed.get("education") or parsed.get("employment")):
                    parsed["_raw_text"] = full_text
                    parsed["_page_count"] = page_count
                    parsed["_academic_links"] = extracted_links
                    parsed["_extraction_method"] = "groq_text"
                    parsed["_model_used"] = t_cfg["model"]
                    parsed["_groq_calls"] = groq_calls
                    parsed["_json_repaired"] = was_repaired
                    return parsed
                last_error = "Text LLM returned incomplete or unparseable JSON"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Groq LLM text parsing error for {file_path.name}: {e}. Trying visual vision...")

        # STAGE 3: Unified Visual Extraction via VisionAgent
        if groq_pool.size > 0:
            try:
                vision_user = config_manager.get_prompt(
                    "extractor",
                    "vision_user",
                    default="Extract all academic resume sections, education, experience, publications, and evidence into the specified JSON format.",
                )
                groq_calls += 1
                parsed, was_repaired = vision_agent.extract_visual_facts(
                    file_path,
                    system_prompt=extraction_instructions,
                    user_prompt=vision_user,
                    task_name="vision_extraction",
                    model_override=self._model_override,
                )
                if parsed:
                    parsed["_raw_text"] = full_text
                    parsed["_page_count"] = page_count
                    parsed["_academic_links"] = extracted_links
                    parsed["_extraction_method"] = "groq_vision"
                    parsed["_model_used"] = self.model
                    parsed["_groq_calls"] = groq_calls
                    parsed["_json_repaired"] = was_repaired
                    return parsed
                last_error = "Vision LLM returned unparseable JSON"
            except Exception as e:
                last_error = str(e)
                logger.error(f"Groq vision extraction failed for {file_path.name}: {e}.")

        logger.error(f"Extraction failed for {file_path.name} (live mode, no synthetic fallback): {last_error}")
        return {
            "name": self._clean_name_from_filename(file_path),
            "email": None,
            "phone": None,
            "location": None,
            "current_designation": None,
            "summary": None,
            "education": [],
            "employment": [],
            "research": {"publications": [], "patents": [], "research_projects": [], "research_domains": []},
            "certifications": [],
            "awards": [],
            "skills": [],
            "projects": [],
            "source_evidence": [],
            "_raw_text": full_text,
            "_page_count": page_count,
            "_academic_links": extracted_links,
            "_extraction_method": "failed",
            "_model_used": "none",
            "_extraction_error": str(last_error or "LLM returned empty or unparseable output"),
            "_groq_calls": groq_calls,
            "_json_repaired": False,
        }

    def _generate_realistic_profile_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Deterministic profile generator strictly for explicit mock_mode=True testing.
        """
        clean_name = self._clean_name_from_filename(file_path)

        raw_text_snippets = []
        try:
            if file_path.suffix.lower() == ".pdf":
                doc = pdfium.PdfDocument(str(file_path))
                for p_idx in range(min(len(doc), 2)):
                    text_page = doc[p_idx].get_textpage()
                    t = text_page.get_text_range()
                    if t:
                        raw_text_snippets.append(t)
                doc.close()
        except Exception:
            pass

        full_raw_text = " ".join(raw_text_snippets)
        has_phd = "ph.d" in full_raw_text.lower() or "doctor of philosophy" in full_raw_text.lower() or "phd" in full_raw_text.lower()
        has_iit = "iit" in full_raw_text.lower() or "indian institute of technology" in full_raw_text.lower()
        has_nit = "nit" in full_raw_text.lower() or "national institute of technology" in full_raw_text.lower()

        institution = "IIT Delhi" if has_iit else ("NIT Trichy" if has_nit else "Delhi Technological University")
        degree = "Ph.D. in Computer Science & Engineering" if has_phd else "M.Tech in Information Technology"
        grad_year = 2020 if has_phd else 2018

        return {
            "name": clean_name.title(),
            "email": f"{clean_name.lower().replace(' ', '.')}@university.edu",
            "phone": "+91-9876543210",
            "location": "New Delhi, India",
            "current_designation": "Associate Professor" if has_phd else "Assistant Professor",
            "summary": "Experienced academician and researcher specializing in computer engineering, distributed computing, and artificial intelligence.",
            "education": [
                {
                    "degree": degree,
                    "field": "Computer Science & Engineering",
                    "institution": institution,
                    "graduation_year": grad_year,
                    "confidence": 0.95,
                    "evidence": f"{degree} from {institution}, graduated {grad_year}",
                    "source_page": 1,
                },
                {
                    "degree": "B.Tech in Computer Science",
                    "field": "Computer Science",
                    "institution": "Guru Gobind Singh Indraprastha University",
                    "graduation_year": grad_year - 5,
                    "confidence": 0.92,
                    "evidence": f"Bachelor of Technology, First Class with Distinction ({grad_year - 5})",
                    "source_page": 1,
                },
            ],
            "employment": [
                {
                    "title": "Associate Professor" if has_phd else "Assistant Professor",
                    "organization": institution,
                    "category": "teaching",
                    "start_date": "2021",
                    "end_date": "Present",
                    "duration_years": 4.0,
                    "is_current": True,
                    "description": "Delivering undergraduate and postgraduate lectures in Machine Learning, Algorithms, and Cloud Systems.",
                    "evidence": f"Faculty appointment at {institution} (2021 - Present)",
                    "source_page": 1,
                },
                {
                    "title": "Postdoctoral Research Fellow",
                    "organization": "National Research Laboratory",
                    "category": "research",
                    "start_date": "2019",
                    "end_date": "2021",
                    "duration_years": 2.0,
                    "is_current": False,
                    "description": "Conducted sponsored research on scalable machine learning workflows.",
                    "evidence": "Postdoctoral appointment order Ref NRL/2019/332",
                    "source_page": 1,
                },
                {
                    "title": "Software Engineer",
                    "organization": "Infosys Technologies",
                    "category": "industry",
                    "start_date": "2016",
                    "end_date": "2018",
                    "duration_years": 2.0,
                    "is_current": False,
                    "description": "Enterprise software development and data pipeline optimization.",
                    "evidence": "Software Engineer, Systems Integration Group",
                    "source_page": 2,
                },
            ],
            "research": {
                "publications": [
                    {
                        "title": "Scalable Federated Learning Architectures for Autonomous Systems",
                        "venue": "IEEE Transactions on Neural Networks and Learning Systems",
                        "year": 2023,
                        "doi": "10.1109/TNNLS.2023.3289114",
                        "indexed": "Scopus, SCI",
                        "evidence": "Published in IEEE TNNLS, Vol 34, Issue 4, pp. 210-224",
                    },
                    {
                        "title": "Efficient Multi-Agent Consensus in Distributed Cyber-Physical Networks",
                        "venue": "ACM Computing Surveys",
                        "year": 2022,
                        "doi": "10.1145/3512345",
                        "indexed": "Scopus, SCI",
                        "evidence": "ACM CSUR Article 48, 2022",
                    },
                    {
                        "title": "Adversarial Robustness in Deep Graph Neural Networks",
                        "venue": "NeurIPS Workshop on Graph Representation",
                        "year": 2021,
                        "doi": None,
                        "indexed": "Peer-Reviewed",
                        "evidence": "Presented at NeurIPS 2021 Workshop",
                    },
                ],
                "patents": [
                    {"title": "System and Method for Adaptive Edge Computing Load Balancing", "patent_number": "IN202211045678", "status": "Granted"}
                ],
                "research_projects": [
                    {"title": "AI in Higher Education Curriculum Enhancement", "funding_agency": "DST SERB", "grant_amount": "INR 25,00,000"}
                ],
                "research_domains": ["Artificial Intelligence", "Distributed Systems", "Data Science", "Computer Vision"],
            },
            "certifications": ["Deep Learning Specialization (DeepLearning.AI)", "AWS Certified Solutions Architect"],
            "awards": ["Outstanding Faculty Award 2023", "Young Scientist Fellowship"],
            "skills": ["Python", "PyTorch", "TensorFlow", "Kubernetes", "Curriculum Architecture", "Peer Reviewing"],
            "projects": [],
            "source_evidence": [
                {
                    "field": "highest_degree",
                    "value": degree,
                    "evidence": f"Awarded {degree} by {institution}",
                    "source_page": 1,
                    "confidence": 0.98,
                },
                {
                    "field": "teaching_tenure",
                    "value": "4.0 years",
                    "evidence": f"Associate Professor at {institution} from 2021 to Present",
                    "source_page": 1,
                    "confidence": 0.95,
                },
            ],
        }


groq_extractor = GroqExtractor()
