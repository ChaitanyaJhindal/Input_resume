import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class InstitutionService:
    def __init__(self, data_path: Optional[str] = None):
        if not data_path:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            data_path = str(base_dir / "data" / "institutions" / "institutions.json")
        
        self.data_path = data_path
        self.canonical_map: Dict[str, Dict[str, Any]] = {}
        self.alias_lookup: Dict[str, str] = {}
        self._load_database()

    def _clean_str(self, text: str) -> str:
        """Lowercase, remove punctuation and extra whitespace for fuzzy matching."""
        if not text:
            return ""
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        return " ".join(cleaned.split())

    def _load_database(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("institutions", []):
                        canonical = item["canonical_name"]
                        self.canonical_map[canonical] = item
                        
                        # Map canonical name
                        self.alias_lookup[self._clean_str(canonical)] = canonical
                        
                        # Map all aliases
                        for alias in item.get("aliases", []):
                            self.alias_lookup[self._clean_str(alias)] = canonical
            except Exception as e:
                print(f"[!] Warning: Failed loading institutions database: {e}")

    def normalize_name(self, raw_name: str) -> str:
        """Deterministic normalization of common acronyms and prefixes."""
        if not raw_name:
            return ""
        
        cleaned = raw_name.strip()
        
        # Standardize Indian Institutes
        cleaned = re.sub(r'(?i)\bI\.?I\.?T\.?\s*(?:-\s*)?', 'IIT ', cleaned)
        cleaned = re.sub(r'(?i)\bN\.?I\.?T\.?\s*(?:-\s*)?', 'NIT ', cleaned)
        cleaned = re.sub(r'(?i)\bI\.?I\.?I\.?T\.?\s*(?:-\s*)?', 'IIIT ', cleaned)
        cleaned = re.sub(r'(?i)\bI\.?I\.?S\.?c\.?\b', 'IISc', cleaned)
        cleaned = re.sub(r'(?i)\bIndian Institute of Technology\b', 'IIT', cleaned)
        cleaned = re.sub(r'(?i)\bNational Institute of Technology\b', 'NIT', cleaned)
        cleaned = re.sub(r'(?i)\bInternational Institute of Information Technology\b', 'IIIT', cleaned)
        
        return " ".join(cleaned.split())

    def lookup_institution(self, raw_name: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], str]:
        """
        Lookup institution using deterministic rules first, then alias table.
        Returns: (canonical_name, metadata_dict, resolution_method)
        """
        if not raw_name:
            return None, None, "empty"
        
        normalized = self.normalize_name(raw_name)
        cleaned_key = self._clean_str(normalized)
        
        # 1. Direct match on alias/canonical lookup
        if cleaned_key in self.alias_lookup:
            canonical = self.alias_lookup[cleaned_key]
            return canonical, self.canonical_map.get(canonical), "deterministic_exact"
        
        # 2. Substring matching against known canonical institutions
        for key, canonical in self.alias_lookup.items():
            if len(key) > 4 and (key in cleaned_key or cleaned_key in key):
                return canonical, self.canonical_map.get(canonical), "deterministic_substring"
        
        # 3. Rule-based heuristic classification if not explicitly in database
        heuristics = self._classify_by_heuristics(normalized)
        if heuristics:
            return normalized, heuristics, "deterministic_heuristic"
        
        return normalized, {
            "category": "Other",
            "tier": "Unknown / Unclassified",
            "country": "Unknown"
        }, "unresolved"

    def _classify_by_heuristics(self, name: str) -> Optional[Dict[str, Any]]:
        n = name.lower()
        if "indian institute of technology" in n or re.search(r"\biit\b", n):
            return {"category": "IIT", "tier": "Tier 1", "country": "India"}
        if "national institute of technology" in n or re.search(r"\bnit\b", n):
            return {"category": "NIT", "tier": "Tier 2", "country": "India"}
        if "indian institute of information technology" in n or re.search(r"\biiit\b", n):
            return {"category": "IIIT", "tier": "Tier 2", "country": "India"}
        if "central university" in n or "delhi university" in n or "university of delhi" in n or "jawaharlal nehru university" in n:
            return {"category": "Central University", "tier": "Tier 2", "country": "India"}
        if "state university" in n or "anna university" in n or "jadavpur university" in n or "delhi technological university" in n:
            return {"category": "State University", "tier": "Tier 3", "country": "India"}
        if "bits pilani" in n or "birla institute" in n:
            return {"category": "Deemed University", "tier": "Tier 2", "country": "India"}
        if "harvard" in n or "stanford" in n or "oxford" in n or "cambridge" in n or "mit" in n:
            return {"category": "International University", "tier": "Tier 0", "country": "International"}
        if "university" in n or "institute" in n or "college" in n:
            return {"category": "State University", "tier": "Tier 3", "country": "India"}
        return None

    def classify_institution(self, raw_name: str) -> Tuple[str, str, str, float]:
        """
        Classifies an institution string into (canonical_name, category, tier, confidence).
        """
        canonical, meta, method = self.lookup_institution(raw_name)
        if not canonical:
            return raw_name, "Other", "Unknown / Unclassified", 0.5

        category = meta.get("category", "Other") if meta else "Other"
        tier = meta.get("tier", "Unknown / Unclassified") if meta else "Unknown / Unclassified"

        confidence = 0.98 if method == "deterministic_exact" else (
            0.92 if method == "deterministic_substring" else (
                0.88 if method == "deterministic_heuristic" else 0.60
            )
        )
        return canonical, category, tier, confidence

    def get_evidence(self, raw_name: str) -> Dict[str, Any]:
        canonical, meta, method = self.lookup_institution(raw_name)
        return {
            "raw_input": raw_name,
            "canonical_name": canonical,
            "metadata": meta,
            "resolution_method": method
        }

    @property
    def categories(self):
        return [
            "IIT", "NIT", "IIIT", "Central University", "State University",
            "Deemed University", "Private University", "International University",
            "Research Institute", "Other"
        ]

    @property
    def institutions_db(self):
        return list(self.canonical_map.values())

institution_service = InstitutionService()
