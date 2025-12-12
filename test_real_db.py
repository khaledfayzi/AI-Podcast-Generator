import logging
import os
import sys
from dotenv import load_dotenv

# Deine Projekt-Imports
from database import init_db_connection, get_db
from models import PodcastStimme
from services.tts_service import GoogleTTSService

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_real_test():
    print("--- Start Realer Datenbank Integrationstest (SSML Edition) ---")

    # 1. Umgebungsvariablen laden
    load_dotenv()

    # 2. Datenbankverbindung initialisieren
    try:
        print("Initialisiere Datenbankverbindung...")
        init_db_connection()
    except Exception as e:
        logger.error(f"Konnte Datenbank nicht verbinden: {e}")
        return

    # 3. Stimmen aus der DB holen
    session = get_db()

    # Namen anpassen, falls sie in deiner DB anders heißen (z.B. "Max" und "Sarah")
    primary_name = "Max"
    secondary_name = "Sarah"

    voice_primary = session.query(PodcastStimme).filter_by(name=primary_name).first()
    voice_secondary = session.query(PodcastStimme).filter_by(name=secondary_name).first()

    if not voice_primary:
        logger.error(f"❌ Stimme '{primary_name}' nicht gefunden!")
        _cleanup_and_exit()
        return

    # Falls keine Zweitstimme da ist, nutzen wir die erste doppelt
    s2_name = voice_secondary.name if voice_secondary else voice_primary.name

    print(f"Test startet mit: {voice_primary.name} (Primär) und {s2_name} (Sekundär)")
    session.close()

    # 4. Google TTS Service starten
    try:
        tts_service = GoogleTTSService()
    except Exception as e:
        logger.error(f"Fehler beim Starten des Google Services: {e}")
        _cleanup_and_exit()
        return

    # 5. Längeres Skript mit SSML-Tags
    # Wir nutzen <break> für Pausen, <emphasis> für Betonung und <prosody> für Geschwindigkeit
    script_text = f"""
    {voice_primary.name}: <speak>Hallo! Willkommen zu unserem <emphasis level="strong">großen Integrationstest</emphasis>. <break time="1s"/> Kannst du mich gut hören?</speak>

    {s2_name}: <speak>Absolut! <break time="500ms"/> Es ist faszinierend. Meine Stimme wird gerade durch einen <prosody rate="slow">verschlüsselten S S H Tunnel</prosody> direkt aus der Datenbank geladen.</speak>

    {voice_primary.name}: <speak>Genau. Wir nutzen hier S S M L, um die Sprache natürlicher zu machen. <break time="800ms"/> Wir können Pausen einlegen, <prosody pitch="+2st">die Tonhöhe verändern</prosody> oder wichtige Begriffe betonen.</speak>

    {s2_name}: <speak>Das macht den Podcast viel lebendiger. <break time="1s"/> Wenn wir jetzt fertig sind, generiert das System eine hochwertige M P 3 Datei für uns. <emphasis level="moderate">Ist das nicht unglaublich?</emphasis></speak>

    {voice_primary.name}: <speak>Das ist es. Test Ende. <break time="500ms"/> Auf Wiedersehen!</speak>
    """

    print("\n--- Generiere Audio mit SSML (Dauert etwas länger...) ---")

    # 6. Ausführen
    try:
        # Hinweis: Dein GoogleTTSService muss so programmiert sein, dass er SSML-Tags
        # innerhalb des Skript-Textes erkennt und an die Google API weitergibt.
        filename = tts_service.generate_audio(
            script_text=script_text,
            primary_voice=voice_primary,
            secondary_voice=voice_secondary if voice_secondary else voice_primary
        )

        if filename:
            print(f"\n✅ ERFOLG! Datei erstellt: {filename}")
            print(f"Pfad: {os.path.abspath(filename)}")
        else:
            print("\n❌ FEHLER: Keine Datei zurückgegeben.")

    except Exception as e:
        logger.error(f"Fehler während der Generierung: {e}", exc_info=True)
    finally:
        _cleanup_and_exit()


def _cleanup_and_exit():
    """Schließt den SSH Tunnel sauber"""
    from database import tunnel as db_tunnel
    if db_tunnel and db_tunnel.is_active:
        print("Schließe SSH Tunnel...")
        db_tunnel.stop()
    print("Test beendet.")


if __name__ == "__main__":
    run_real_test()