import pypdfium2 as pdfium
import sys

sys.stdout.reconfigure(encoding='utf-8')

doc = pdfium.PdfDocument('01-SUSHIL-CV.pdf (1).pdf')
print(f"Total Pages: {len(doc)}")
for i, page in enumerate(doc):
    text = page.get_textpage().get_text_range()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    print(f"\n--- Page {i+1} ({len(lines)} lines) ---")
    for line in lines[:25]:
        print("  ", line)
