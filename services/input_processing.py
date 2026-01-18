import os
import requests
from typing import Tuple, Optional
from pathlib import Path
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup


def extract_text_from_file(file_path: str) -> Tuple[str, str]:
    """Reads text from PDF or TXT files and returns (text, title)."""
    if not file_path:
        return "", ""

    # Check extension
    path_obj = Path(file_path)
    ext = path_obj.suffix.lower()
    title = path_obj.stem.replace("_", " ").title()

    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts).strip(), title
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return "", title

    # Default to text file
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip(), title
    except Exception as e:
        print(f"Error reading file: {e}")
        return "", title


def fetch_text_from_url(url: str) -> Tuple[str, str]:
    """Scrapes text from a given URL and returns (text, title)."""
    if not url:
        return "", ""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return "", ""

    soup = BeautifulSoup(r.text, "html.parser")
    # Extract title
    page_title = (
        soup.title.string.strip() if soup.title and soup.title.string else "Webseite"
    )

    # Clean up scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    # Clean up whitespace
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text.strip(), page_title


def build_source_text(file_path, url) -> Tuple[str, str]:
    """Orchestrator: decides whether to use file or URL. Returns (text, title)."""
    file_text, file_title = extract_text_from_file(file_path) if file_path else ("", "")
    url_text, url_title = fetch_text_from_url(url.strip()) if url else ("", "")

    # Prioritize file if both are present
    combined_text = file_text if file_text else url_text

    # Prioritize file title if present
    combined_title = file_title if file_title else url_title

    # Limit character count to prevent crashing the LLM
    return (combined_text or "")[:12000], combined_title
