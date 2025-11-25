import logging
import time
import os
from datetime import datetime


# ---------------------------------------------------------
# 1. Dummy-Klasse für PodcastStimme (zum Testen ohne Datenbank)
# ---------------------------------------------------------
class MockPodcastStimme:
    def __init__(self, name):
        self.name = name


# ---------------------------------------------------------
# 2. Imports aus deinem Projekt
# ---------------------------------------------------------
try:
    # Versuche den Service zu importieren
    # (Stelle sicher, dass du das Skript aus dem Ordner 'SYP' ausführst)
    from team04.services.tts_service import BarkTTSService
    from exceptions import TTSServiceError
except ImportError as e:
    print("FEHLER: Konnte Module nicht importieren.")
    print(f"Stelle sicher, dass du im Root-Verzeichnis bist (SYP). Details: {e}")
    exit(1)

# ---------------------------------------------------------
# 3. Logging Konfiguration (Das Herzstück)
# ---------------------------------------------------------
LOG_FILE = "test_run_report.log"


def setup_logging():
    # Wir konfigurieren den "Root Logger".
    # Das fängt ALLES ab: Deine Main, den TTSService, Bark, etc.

    # Formatierung: Zeit - Level - Modul - Nachricht
    log_format = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"

    logging.basicConfig(
        level=logging.INFO,  # Alles ab INFO wird gespeichert (DEBUG ignorieren wir für Übersicht)
        format=log_format,
        handlers=[
            logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
            # In Datei schreiben ('w' überschreibt jedes Mal)
            logging.StreamHandler()  # UND in die Konsole schreiben
        ]
    )


# ---------------------------------------------------------
# 4. Die Test-Funktion
# ---------------------------------------------------------
def run_test():
    logger = logging.getLogger("TestMain")

    logger.info("========================================")
    logger.info("      START TESTLAUF TTS SERVICE        ")
    logger.info("========================================")

    # Metadaten zum Testzeitpunkt
    now = datetime.now()
    logger.info(f"Test-Datum: {now.strftime('%d.%m.%Y')}")
    logger.info(f"Startzeit:  {now.strftime('%H:%M:%S')}")

    # --- SETUP ---
    logger.info("1. Initialisiere Service...")
    start_init = time.perf_counter()

    try:
        tts_service = BarkTTSService()  # Hier werden Hardware-Infos geloggt (automatisch durch dein Skript)
    except Exception as e:
        logger.critical(f"Service konnte nicht gestartet werden: {e}")
        return

    end_init = time.perf_counter()
    logger.info(f"-> Initialisierung dauerte: {end_init - start_init:.2f} Sekunden")

    # --- TEST DATEN ---
    test_text = """
Max: Hallo Sara! [laughs] Wie geht es dir heute?
Sara: [sighs] Ach Max, ich bin etwas müde, aber die KI läuft super.
    """.strip()

    voice_1 = MockPodcastStimme("Max")
    voice_2 = MockPodcastStimme("Sara")

    # Text-Metriken
    char_count = len(test_text)
    word_count = len(test_text.split())

    logger.info("----------------------------------------")
    logger.info("2. Test-Parameter")
    logger.info(f"Input Text Länge: {char_count} Zeichen")
    logger.info(f"Input Wortanzahl: {word_count} Wörter")
    logger.info(f"Stimmen: {voice_1.name} & {voice_2.name}")
    logger.info("----------------------------------------")

    # --- AUSFÜHRUNG ---
    logger.info("3. Starte Audio-Generierung...")
    start_gen = time.perf_counter()

    try:
        output_path = tts_service.generate_audio(
            skript=test_text,
            hauptstimme=voice_1,
            zweitstimme=voice_2
        )

        # --- ERGEBNISSE ---
        end_gen = time.perf_counter()
        duration = end_gen - start_gen

        logger.info("========================================")
        logger.info("           TEST ERGEBNIS                ")
        logger.info("========================================")

        if output_path and os.path.exists(output_path):
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

            logger.info("STATUS:        ERFOLGREICH")
            logger.info(f"Dauer:         {duration:.2f} Sekunden")
            logger.info(f"Geschwindigk.: {char_count / duration:.2f} Zeichen/Sekunde")
            logger.info(f"Dateipfad:     {output_path}")
            logger.info(f"Dateigröße:    {file_size_mb:.2f} MB")
        else:
            logger.error("STATUS:        FEHLGESCHLAGEN (Keine Datei zurückgegeben)")

    except TTSServiceError as e:
        logger.error(f"STATUS: ABBRUCH DURCH SERVICE EXCEPTION: {e}")
    except Exception as e:
        logger.critical(f"STATUS: UNERWARTETER CRASH: {e}", exc_info=True)


if __name__ == "__main__":
    setup_logging()
    run_test()