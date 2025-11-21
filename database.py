# NOTE: Datenbankverbindung
# Verwaltet die technische Verbindung zur MariaDB
#
# Einzufügen / Umzusetzen:
# - Funktion 'init_db()':
#   1. Erstellt einen asynchronen Motor-Client.
#   2. Verbindet sich mit der Datenbank 'podcast_db'.
#   3. Initialisiert Beanie mit den Modellen aus models.py.
#
# Diese Datei stellt sicher, dass die Datenbank bereit ist, bevor die App startet.

# Module Import
import mariadb
import sys

