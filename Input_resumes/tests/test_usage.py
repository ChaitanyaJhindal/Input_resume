import sys, os
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

prompt_text = full_text[:14000]
messages = [
    {"role": "system", "content": "You are a senior academic recruitment document parser. Output ONLY valid JSON matching the schema."},
    {"role": "user", "content": f"{EXTRACTION_SYSTEM_PROMPT}\n\nDocument Text:\n{prompt_text}"}
]

print("Executing completion on openai/gpt-oss-20b...")
comp = groq_pool.execute_completion(
    model="openai/gpt-oss-20b",
    messages=messages,
    max_tokens=4000,
    temperature=0.1,
    reasoning_format="hidden",
    reasoning_effort="low"
)
print("Finish Reason:", comp.choices[0].finish_reason)
print("Usage:", comp.usage)
content = comp.choices[0].message.content or ""
print("Content length:", len(content))
print("Sample content:\n", content[:800])
