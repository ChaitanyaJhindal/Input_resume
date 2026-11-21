import glob
import sys
import os
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding='utf-8')

import pypdfium2 as pdfium

pdfs = glob.glob("*.pdf")
print(f"Total PDFs found: {len(pdfs)}")

candidates_info = []

for p in pdfs:
    try:
        doc = pdfium.PdfDocument(p)
        text = ""
        for i in range(min(len(doc), 6)):
            text += doc[i].get_textpage().get_text_range() + "\n"
        doc.close()
        
        t_lower = text.lower()
        has_phd = any(kw in t_lower for kw in ["ph.d", "phd", "doctor of philosophy", "doctorate"])
        has_teaching = any(kw in t_lower for kw in ["assistant professor", "associate professor", "professor", "lecturer", "instructor", "faculty"])
        has_pub = any(kw in t_lower for kw in ["publication", "journal", "ieee", "springer", "elsevier", "conference"])
        
        candidates_info.append({
            "file": p,
            "has_phd": has_phd,
            "has_teaching": has_teaching,
            "has_pub": has_pub,
            "text_len": len(text)
        })
    except Exception as e:
        print(f"Error reading {p}: {e}")

likely_qualified = [c for c in candidates_info if c["has_phd"] and c["has_teaching"] and c["has_pub"]]
print(f"\nCandidates with PhD + Teaching + Publications keywords ({len(likely_qualified)}):")
for c in likely_qualified:
    print(f" - {c['file']}")
