import hashlib
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pypdfium2 as pdfium

from backend.app.config import config_manager, settings
from backend.app.groq.pool import groq_pool
from backend.app.schemas.jd import JDRequirement, JDWeights, JobDescriptionSpec
from backend.app.utils.json_utils import parse_llm_json, safe_int, safe_str_list

logger = logging.getLogger("FacultyScreen.JDIntelligenceAgent")

_VALID_PRIORITIES = {"must_have", "strong_preference", "nice_to_have"}
_VALID_STRICTNESS = {"strict", "flexible_with_equivalence"}
_VALID_CATEGORIES = {"qualification", "experience", "teaching", "research", "domain_skill", "leadership", "other"}


class JDIntelligenceAgent:
    """
    Parses uploaded Job Description files (.pdf, .docx, .txt, .md) or pasted text into
    a structured, configurable JobDescriptionSpec rubric with zero hardcoded criteria.
    """

    @staticmethod
    def compute_jd_id(raw_text: str) -> str:
        digest = hashlib.sha256(raw_text.strip().encode("utf-8")).hexdigest()
        return f"jd_{digest[:10]}"

    @staticmethod
    def extract_text_from_file(file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            doc = pdfium.PdfDocument(str(file_path))
            try:
                pages = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
                return "\n".join(pages).strip()
            finally:
                doc.close()

        if suffix == ".docx":
            chunks: List[str] = []
            with zipfile.ZipFile(file_path, "r") as zf:
                if "word/document.xml" in zf.namelist():
                    xml_bytes = zf.read("word/document.xml")
                    root = ET.fromstring(xml_bytes)
                    for elem in root.iter():
                        if elem.tag.endswith("}p"):
                            texts = [t.text for t in elem.iter() if t.tag.endswith("}t") and t.text]
                            if texts:
                                chunks.append("".join(texts))
            return "\n".join(chunks).strip()

        return file_path.read_text(encoding="utf-8", errors="ignore").strip()

    @staticmethod
    def _deterministic_parse(jd_id: str, raw_text: str, title_hint: Optional[str] = None) -> JobDescriptionSpec:
        lines = [ln.strip(" •-*-\t") for ln in raw_text.splitlines() if len(ln.strip()) >= 6]
        inferred_title = title_hint or (lines[0][:120] if lines else "Academic / Faculty Position")

        reqs: List[JDRequirement] = []
        seen = set()
        for idx, line in enumerate(lines[:35]):
            low = line.lower()
            is_req_line = any(
                k in low
                for k in (
                    "require", "must", "prefer", "phd", "ph.d", "master", "degree",
                    "experience", "year", "teach", "course", "research", "publication",
                    "industry", "grant", "leadership", "skill", "domain", "knowledge",
                )
            )
            if not is_req_line:
                continue
            norm_key = re.sub(r"[^a-z0-9]+", " ", low).strip()
            if norm_key in seen or len(norm_key) < 8:
                continue
            seen.add(norm_key)

            if any(k in low for k in ("phd", "ph.d", "doctorate", "degree", "qualification", "master")):
                cat = "qualification"
            elif any(k in low for k in ("teach", "course", "curriculum", "lecture")):
                cat = "teaching"
            elif any(k in low for k in ("research", "publication", "scopus", "grant", "journal")):
                cat = "research"
            elif any(k in low for k in ("leadership", "dean", "chair", "director", "head", "mentoring")):
                cat = "leadership"
            elif any(k in low for k in ("experience", "years", "tenure", "industry")):
                cat = "experience"
            else:
                cat = "domain_skill"

            priority = "must_have" if any(w in low for w in ("must", "mandatory", "essential", "required")) else "strong_preference"
            strictness = "strict" if any(w in low for w in ("strictly mandatory", "no exception", "statutorily required")) else "flexible_with_equivalence"

            reqs.append(
                JDRequirement(
                    id=f"REQ_{len(reqs) + 1}",
                    category=cat,
                    label=line[:180],
                    priority=priority,
                    weight=20 if priority == "must_have" else 12,
                    strictness=strictness,
                    jd_quote=line[:220],
                )
            )
            if len(reqs) >= 10:
                break

        if not reqs:
            reqs.append(
                JDRequirement(
                    id="REQ_1",
                    category="other",
                    label=inferred_title,
                    priority="must_have",
                    weight=25,
                    strictness="flexible_with_equivalence",
                    jd_quote=lines[0][:200] if lines else inferred_title,
                )
            )

        eval_cfg = config_manager.get_evaluation_config()
        return JobDescriptionSpec(
            jd_id=jd_id,
            title=inferred_title,
            role_archetype="balanced",
            summary=raw_text[:280].replace("\n", " ").strip(),
            requirements=reqs,
            allow_compensating_strengths=bool(eval_cfg["allow_compensating_strengths"]),
            weights=JDWeights(**eval_cfg["default_weights"]),
        )

    def parse_jd(
        self,
        raw_text: str,
        title_hint: Optional[str] = None,
        department_hint: Optional[str] = None,
    ) -> JobDescriptionSpec:
        cleaned_text = (raw_text or "").strip()
        if len(cleaned_text) < 20:
            raise ValueError("Job Description text is too short (minimum 20 characters)")

        jd_id = self.compute_jd_id(cleaned_text)
        eval_cfg = config_manager.get_evaluation_config()
        default_weights = JDWeights(**eval_cfg["default_weights"])
        allow_comp = bool(eval_cfg["allow_compensating_strengths"])

        if not settings.mock_mode and groq_pool.size > 0:
            try:
                t_cfg = config_manager.get_task_config("jd_parser", "reasoning")
                sys_prompt = config_manager.get_prompt("jd_parser", "system")
                user_prompt = config_manager.get_prompt(
                    "jd_parser",
                    "user_template",
                    default="Parse this Job Description.\nTitle hint: {title_hint}\n\nJD Text:\n{jd_text}",
                    title_hint=title_hint or "Not specified",
                    jd_text=cleaned_text[:18000],
                )
                messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                completion = groq_pool.execute_completion(
                    model=t_cfg["model"],
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=t_cfg["max_tokens"],
                    temperature=t_cfg["temperature"],
                    **t_cfg.get("extra_completion_kwargs", {}),
                )
                parsed, _ = parse_llm_json(completion.choices[0].message.content)
                if parsed and (parsed.get("title") or parsed.get("requirements")):
                    reqs: List[JDRequirement] = []
                    for idx, r in enumerate(parsed.get("requirements") or []):
                        if not isinstance(r, dict) or not str(r.get("label") or "").strip():
                            continue
                        cat = str(r.get("category") or "other").strip().lower()
                        prio = str(r.get("priority") or "must_have").strip().lower()
                        strict = str(r.get("strictness") or "flexible_with_equivalence").strip().lower()
                        reqs.append(
                            JDRequirement(
                                id=str(r.get("id") or f"REQ_{idx + 1}"),
                                category=cat if cat in _VALID_CATEGORIES else "other",
                                label=str(r.get("label")).strip(),
                                priority=prio if prio in _VALID_PRIORITIES else "must_have",
                                weight=max(5, min(50, safe_int(r.get("weight"), 15) or 15)),
                                strictness=strict if strict in _VALID_STRICTNESS else "flexible_with_equivalence",
                                jd_quote=str(r.get("jd_quote")).strip() if r.get("jd_quote") else None,
                            )
                        )

                    if reqs:
                        return JobDescriptionSpec(
                            jd_id=jd_id,
                            title=str(title_hint or parsed.get("title") or "Untitled Position").strip(),
                            department=str(department_hint or parsed.get("department") or "").strip() or None,
                            level=str(parsed.get("level") or "").strip() or None,
                            role_archetype=str(parsed.get("role_archetype") or "balanced").strip().lower(),
                            summary=str(parsed.get("summary") or "").strip() or None,
                            requirements=reqs,
                            required_domains=safe_str_list(parsed.get("required_domains")),
                            preferred_courses=safe_str_list(parsed.get("preferred_courses")),
                            research_expectations=str(parsed.get("research_expectations") or "").strip() or None,
                            industry_practice_value=str(parsed.get("industry_practice_value") or "").strip() or None,
                            allow_compensating_strengths=allow_comp,
                            weights=default_weights,
                        )
            except Exception as e:
                logger.warning(f"LLM JD parsing failed, using deterministic fallback: {e}")

        spec = self._deterministic_parse(jd_id, cleaned_text, title_hint=title_hint)
        if department_hint:
            spec.department = department_hint
        return spec


jd_agent = JDIntelligenceAgent()
