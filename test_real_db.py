import logging
import os
import sys
from dotenv import load_dotenv

# Deine Projekt-Imports
from database import init_db_connection, get_db, tunnel
from models import PodcastStimme
from services.tts_service import GoogleTTSService

# HINWEIS: Passe den Import oben an, falls die Datei anders heißt (z.B. services.tts_service)

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_real_test():
    print("--- Start Realer Datenbank Integrationstest ---")

    # 1. Umgebungsvariablen laden
    load_dotenv()

    # 2. Datenbankverbindung initialisieren (Startet auch den SSH Tunnel falls nötig)
    try:
        print("Initialisiere Datenbankverbindung...")
        init_db_connection()
    except Exception as e:
        logger.error(f"Konnte Datenbank nicht verbinden: {e}")
        return

    # 3. Stimmen aus der DB prüfen
    # Wir holen uns kurz eine Session, um zu schauen, welche Stimmen wir testen können.
    session = get_db()

    # ACHTUNG: Ersetze diese Namen mit Namen, die WIRKLICH in deiner DB stehen!
    primary_name = "Max"  # Beispiel: Name in deiner DB
    secondary_name = "Sara"  # Beispiel: Name in deiner DB

    print(f"Suche nach Stimmen: '{primary_name}' und '{secondary_name}'...")

    voice_primary = session.query(PodcastStimme).filter_by(name=primary_name).first()
    voice_secondary = session.query(PodcastStimme).filter_by(name=secondary_name).first()

    if not voice_primary:
        logger.error(f"❌ Stimme '{primary_name}' nicht in der DB gefunden! Bitte Namen im Test-Skript anpassen.")
        _cleanup_and_exit()
        return

    if not voice_secondary:
        logger.warning(f"⚠️ Zweitstimme '{secondary_name}' nicht gefunden. Test läuft nur mit einer Stimme.")

    # Session schließen, der Service holt sich gleich seine eigene
    session.close()

    # 4. Service instanziieren
    try:
        tts_service = GoogleTTSService()
    except Exception as e:
        logger.error(f"Fehler beim Starten des Google Services: {e}")
        _cleanup_and_exit()
        return

    # 5. Test-Skript definieren
    # Hier nutzen wir die Namen, die wir oben definiert haben
    script_text = f"""
    {voice_primary.name}: Hallo! Dies ist ein echter Test mit der Datenbank.
    {voice_secondary.name if voice_secondary else voice_primary.name}: Das ist super. Die Daten für meine Stimme kommen direkt aus der Tabelle PodcastStimme.
    {voice_primary.name}: Genau. Und jetzt wird eine MP3 Datei generiert.
    """

    print("\n--- Generiere Audio (ruft Google API auf) ---")

    # 6. Ausführen
    try:
        filename = tts_service.generate_audio(
            script_text=script_text,
            primary_voice=voice_primary,
            secondary_voice=voice_secondary
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
    """Hilfsfunktion um den SSH Tunnel sauber zu schließen"""
    # Da 'tunnel' in database.py global ist, importieren wir es von dort
    from database import tunnel as db_tunnel

    if db_tunnel and db_tunnel.is_active:
        print("Schließe SSH Tunnel...")
        db_tunnel.stop()
    print("Test beendet.")


if __name__ == "__main__":
    run_real_test()