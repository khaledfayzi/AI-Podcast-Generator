from dotenv import load_dotenv

from database import init_db_connection, get_db
from models import LLMModell, TTSModell, Benutzer
import os

load_dotenv()


def seed_data(db):
    if db.query(LLMModell).count() == 0:
        print("Lege LLM Modelle an")
        gpt4 = LLMModell(modellName="GPT-4", version="4.0", typ="Cloud")
        llama = LLMModell(modellName="Llama 3", version="70B", typ="Local")
        db.add_all([gpt4, llama])
        db.commit()

    # TODO hier noch den Rest initialisieren

    print("Datenbank initialisiert")


if __name__ == "__main__":
    init_db_connection()
    db = get_db()
    seed_data(db)
    db.close()
