from services.llm_service import LLMService
from datetime import datetime
import os
from pypdf import PdfReader

def save_script(text: str):
    os.makedirs("scripts", exist_ok=True)
    filename = f"scripts/podcast_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Skript gespeichert unter: {filename}")

def load_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    pages_text = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")
    return "\n".join(pages_text)

def main():
    llm = LLMService(use_dummy=False)

    pdf_path = "/home/khaled/Dokumente/syp_projekt/team04/pdfs_test/distributed_systems_lecture_4.pdf"   # <--- anpassen
    source_text = load_pdf_text(pdf_path)

    config = {
         "dauer": 2,
        "language": "Deutsch",
        "hauptstimme": "Max",
        "zweitstimme": None,                  # ✅ nur ein Erzähler
        "roles": {"Max": "Erzähler"},         # ✅ optional
        "style": "neutral",
        "source_text": source_text,
        "source_name": os.path.basename(pdf_path),
        "source_max_chars": 12000
    }

    text = llm.generate_script(
        thema="Zusammenfassung der PDF",   # optionaler Fokus
        config=config
    )

    print(text)
    save_script(text)

if __name__ == "__main__":
    main()
