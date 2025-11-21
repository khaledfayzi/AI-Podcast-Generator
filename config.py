# NOTE: Konfiguration und Secrets
# Lädt Umgebungsvariablen aus der .env Datei.
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()


class Config:
    """Basisklasse für die Anwendungskonfiguration."""

    # Datenbankkonfiguration (direkt aus der .env-Datei geladen)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')