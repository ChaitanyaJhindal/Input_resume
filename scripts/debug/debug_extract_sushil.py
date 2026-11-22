import sys
import os
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.groq.extractor import groq_extractor

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = Path("Input_resumes/01-SUSHIL-CV.pdf (1).pdf")
try:
    print("Testing extract_document...")
    res = groq_extractor.extract_document(pdf_path)
    print("Name:", res.get("name"))
    print("Education:", res.get("education"))
    print("Employment Count:", len(res.get("employment", [])))
    for emp in res.get("employment", []):
        print(" ", emp.get("title"), "|", emp.get("organization"), "|", emp.get("category"), "|", emp.get("duration_years"))
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
