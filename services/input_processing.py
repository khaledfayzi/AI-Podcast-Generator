import os
import requests
from pathlib import Path
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup

def extract_text_from_file(file_path: str) -> str:
    """Reads text from PDF or TXT files."""
    if not file_path:
        return ""
    
    # Check extension
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts).strip()
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    # Default to text file
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading file: {e}")
        return ""

def fetch_text_from_url(url: str) -> str:
    """Scrapes text from a given URL."""
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return ""

    soup = BeautifulSoup(r.text, "html.parser")
    # Clean up scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    # Clean up whitespace
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text.strip()

def build_source_text(file_path, url):
    """Orchestrator: decides whether to use file or URL."""
    file_text = extract_text_from_file(file_path) if file_path else ""
    url_text = fetch_text_from_url(url.strip()) if url else ""
    
    # Prioritize file if both are present, or combine them
    combined = file_text if file_text else url_text
    
    # Limit character count to prevent crashing the LLM
    return (combined or "")[:12000]