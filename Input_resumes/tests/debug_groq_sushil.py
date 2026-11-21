import sys
import os
sys.path.insert(0, os.path.abspath("."))
import pypdfium2 as pdfium
from backend.app.config import settings
from backend.app.groq.pool import groq_pool
from backend.app.groq.extractor import EXTRACTION_SYSTEM_PROMPT

sys.stdout.reconfigure(encoding='utf-8')

file_path = "01-SUSHIL-CV.pdf (1).pdf"
doc = pdfium.PdfDocument(file_path)
full_text = ""
for i in range(len(doc)):
    full_text += f"\n--- Page {i+1} ---\n" + doc[i].get_textpage().get_text_range()
doc.close()

prompt_text = full_text[:18000]
messages = [
    {"role": "system", "content": "You are a senior academic recruitment document parser and visual OCR engine. Output ONLY valid JSON matching the schema."},
    {"role": "user", "content": f"{EXTRACTION_SYSTEM_PROMPT}\n\nDocument Text:\n{prompt_text}"}
]

print("Calling Groq...")
completion = groq_pool.execute_completion(
    model=settings.groq_reasoning_model,
    messages=messages,
    max_tokens=4096,
    reasoning_format="hidden",
    temperature=0.1
)
raw_text = completion.choices[0].message.content.strip()
print("=== RAW GROQ RESPONSE ===")
print(raw_text)
