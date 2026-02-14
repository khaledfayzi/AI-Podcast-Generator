from dotenv import load_dotenv

from database import init_db_connection, get_db
import os

load_dotenv()


def seed_data(db):
    print("Datenbank initialisiert (Keine Seed-Daten mehr nötig)")


if __name__ == "__main__":
    init_db_connection()
    db = get_db()
    seed_data(db)
    db.close()
