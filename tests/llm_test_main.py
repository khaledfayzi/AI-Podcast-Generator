from services.llm_service import LLMService
from datetime import datetime
import os


def save_script(text: str):
    os.makedirs("../scripts", exist_ok=True)
    filename = f"scripts/podcast_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Skript gespeichert unter: {filename}")


def main():
    llm = LLMService(use_dummy=False)

    config = {
        "dauer": 2
    }

    text = llm.generate_script(
        thema="KI im Alltag",
        config=config,
        hauptstimme="Max",
        zweitstimme="Sarah"
    )

    print("\n===== GENERIERTES PODCAST-SKRIPT =====\n")
    print(text)

    save_script(text)


if __name__ == "__main__":
    main()
