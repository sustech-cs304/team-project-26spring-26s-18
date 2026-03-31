import pdfplumber
import io
import base64

def extract_pdf_text(base64_pdf: str, max_len=5000) -> str:
    pdf_bytes = base64.b64decode(base64_pdf)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        all_text = ""
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            all_text += page_text
            if len(all_text) >= max_len:
                break
    return all_text[:max_len]