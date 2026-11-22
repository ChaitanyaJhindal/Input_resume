import re
import json

def repair_json(raw_text: str):
    if not raw_text:
        return None
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Try standard parse first
    try:
        return json.loads(text, strict=False)
    except Exception:
        pass

    # Extract outermost JSON object candidate
    start = text.find('{')
    if start == -1:
        return None
    text = text[start:]

    # Remove any control chars
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)

    # Iterative repair for truncated JSON:
    # If cut off inside a string or field, backtrack
    # Try successively closing quotes, braces, brackets
    candidate = text
    for _ in range(50):
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError as err:
            pos = err.pos
            # Try to see if unclosed quote
            # Count quotes in candidate
            # Or try removing from last comma or newline
            last_comma = candidate.rfind(',')
            if last_comma == -1:
                break
            candidate = candidate[:last_comma]
            # Try closing open brackets/braces
            open_curlies = candidate.count('{') - candidate.count('}')
            open_squares = candidate.count('[') - candidate.count(']')
            test_cand = candidate + (']' * max(0, open_squares)) + ('}' * max(0, open_curlies))
            try:
                return json.loads(test_cand, strict=False)
            except Exception:
                continue

    return None

test_truncated = '''
{
  "name": "Sushil Chaurasia",
  "employment": [
    {
      "title": "Instructor",
      "organization": "University of New Brunswick",
      "category": "teaching",
      "start_date": "Feb 2020",
      "end_date": "Jan 2024",
      "duration_years": 4.0
    }
  ],
  "publications": [
    {
      "title": "Paper 1",
      "evidence": "truncated here...
'''

res = repair_json(test_truncated)
print("Repaired:", res)
