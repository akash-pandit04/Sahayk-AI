import io
import hashlib
from bs4 import BeautifulSoup
import PyPDF2
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def generate_hash(content: str) -> str:
    """Generate SHA-256 hash of extracted content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_html(html_bytes: bytes) -> str:
    """Extracts clean text from HTML, removing noise."""
    try:
        soup = BeautifulSoup(html_bytes, "html.parser")
        
        # Remove script, style, header, footer, nav
        for elem in soup(["script", "style", "nav", "header", "footer", "aside"]):
            elem.extract()
            
        text = soup.get_text(separator="\n", strip=True)
        # basic cleaning of multiple newlines
        cleaned = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        return cleaned
    except Exception as e:
        logger.error(f"HTML extraction failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from HTML.")

def extract_pdf(pdf_bytes: bytes) -> str:
    """Extracts text from PDF."""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        
        full_text = "\n".join(text)
        if not full_text.strip():
             raise ValueError("No text found in PDF (might be scanned images).")
             
        return full_text
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from PDF. Document may be malformed or image-based.")
