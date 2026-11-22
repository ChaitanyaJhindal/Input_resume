import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_VALID_CANDIDATE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")


def validate_candidate_id(candidate_id: str) -> str:
    """Validate that candidate_id matches the safe filesystem/DB identifier pattern."""
    cleaned = str(candidate_id or "").strip()
    if not _VALID_CANDIDATE_ID_RE.match(cleaned):
        raise ValueError(f"Invalid candidate_id format: '{candidate_id}'")
    return cleaned


def safe_child_path(base_dir: Path, child_name: str) -> Path:
    """Resolve child_name inside base_dir and guarantee no path traversal escapes base_dir."""
    base_resolved = base_dir.resolve()
    target = (base_resolved / child_name).resolve()
    if not target.is_relative_to(base_resolved) or target == base_resolved:
        raise ValueError(f"Path traversal blocked for '{child_name}'")
    return target


def sanitize_filename(filename: Optional[str], fallback: str = "resume.pdf") -> str:
    """Strip directory traversal segments and unsafe characters from uploaded filenames."""
    raw_name = Path(str(filename or "")).name.strip()
    if not raw_name or raw_name in {".", ".."}:
        raw_name = fallback
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw_name)
    return cleaned[:200] or fallback


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text content via a same-directory temp file and os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, data: Any, indent: int = 2) -> None:
    """Atomically serialize and write JSON data to disk."""
    atomic_write_text(path, json.dumps(data, indent=indent))


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    if val is None or isinstance(val, bool):
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    s = str(val).strip()
    if not s:
        return default
    match = re.search(r"-?\d+", s)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return default
    return default


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or isinstance(val, bool):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", s)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return default
    return default


def safe_str_list(val: Any) -> List[str]:
    if not isinstance(val, list):
        return []
    out: List[str] = []
    for item in val:
        if item is None:
            continue
        if isinstance(item, dict):
            title = item.get("name") or item.get("title") or item.get("value")
            if title and str(title).strip():
                out.append(str(title).strip())
        else:
            s = str(item).strip()
            if s:
                out.append(s)
    return out


def safe_dict_list(val: Any, fallback_key: str = "title") -> List[Dict[str, Any]]:
    if not isinstance(val, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in val:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str) and item.strip():
            out.append({fallback_key: item.strip()})
    return out


def _close_truncated_json_lifo(candidate: str) -> str:
    """
    Close unclosed JSON structures in exact LIFO nesting order while respecting string literals.
    If truncated mid-string, closes the string quote cleanly before balancing brackets/braces.
    """
    stack: List[str] = []
    in_string = False
    escaped = False

    for ch in candidate:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()

    suffix = ""
    if in_string:
        if escaped:
            candidate = candidate[:-1]
        suffix += '"'
    suffix += "".join(reversed(stack))
    return candidate + suffix


def parse_llm_json(raw_text: Optional[str]) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Parse LLM JSON output robustly, returning (parsed_dict, was_repaired).
    Ensures parsed object is always a JSON object (dict). Handles markdown fences,
    control characters, and string-aware LIFO repair for truncated JSON responses.
    """
    if not raw_text:
        return None, False

    text = str(raw_text).strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    for attempt_text in (text, re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)):
        try:
            loaded = json.loads(attempt_text, strict=False)
            if isinstance(loaded, dict):
                return loaded, False
        except Exception:
            pass

        match = re.search(r"\{.*\}", attempt_text, re.DOTALL)
        if match:
            try:
                loaded = json.loads(match.group(0), strict=False)
                if isinstance(loaded, dict):
                    return loaded, False
            except Exception:
                pass

    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    start = cleaned.find("{")
    if start == -1:
        return None, False
    cleaned = cleaned[start:]

    candidate = cleaned
    for _ in range(80):
        # First try direct close on current candidate slice
        repaired_str = _close_truncated_json_lifo(candidate)
        try:
            loaded = json.loads(repaired_str, strict=False)
            if isinstance(loaded, dict):
                return loaded, True
        except Exception:
            pass

        last_comma = candidate.rfind(",")
        last_nl = candidate.rfind("\n")
        cut_idx = max(last_comma, last_nl)
        if cut_idx <= 0:
            break
        candidate = candidate[:cut_idx].rstrip(" \t\r\n,:")

    return None, False
