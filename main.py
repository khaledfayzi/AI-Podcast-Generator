# NOTE: Einstiegspunkt der Anwendung (Entry Point)
# Diese Datei startet die gesamte Applikation.
#
# Einzufügen / Umzusetzen:
# - Asynchrone 'start_app()' Funktion:
#   1. Ruft 'database.init_db()' auf (DB Verbindung herstellen).
#   2. Erstellt das UI via 'ui.create_ui()'.
#   3. Startet den Webserver (demo.launch).
#
# Wenn man 'python main.py' ausführt, muss hier alles hochfahren.