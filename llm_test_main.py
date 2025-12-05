from dotenv import load_dotenv
load_dotenv()

from services.llm_service import LLMService
from datetime import datetime
import os


def save_script(text: str):
    os.makedirs("scripts", exist_ok=True)
    filename = f"scripts/podcast_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Skript gespeichert unter: {filename}")

def main():
    thema = "KI im Alltag"
    config = {"dauer": 2, "speakers": 2}

    llm = LLMService(use_dummy=False)  

    script = llm.generate_script(thema, config)

    print("\n===== GENERIERTES PODCAST-SKRIPT =====\n")
    print(script)

    save_script(script)

if __name__ == "__main__":
    main()
