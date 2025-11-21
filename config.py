# NOTE: Konfiguration und Secrets
# Lädt Umgebungsvariablen aus der .env Datei.
import os
from dotenv import load_dotenv

# Lade die .env Datei aus dem aktuellen Verzeichnis
load_dotenv()

# Hier werden die Variablen aus der .env-Datei gelesen.
# Wenn MONGODB_URI nicht gefunden wird, wird eine Fehlermeldung ausgegeben.
MONGODB_URI = os.getenv("MONGODB_URI", "")

if not MONGODB_URI:
    # Dies ist wichtig, damit die App nicht mit fehlender Konfiguration startet.
    raise ValueError(
        "Die Umgebungsvariable MONGODB_URI wurde nicht gefunden. "
        "Bitte legen Sie eine .env-Datei an und fügen Sie den Connection String dort ein."
    )