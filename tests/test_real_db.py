import logging
import os
from dotenv import load_dotenv

# Deine Projekt-Imports
from database.database import init_db_connection, get_db
from database.models import PodcastStimme
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
    script_text = """
        Max: Herzlich willkommen zu einer neuen Folge von "Code und Kaffee".
        Sarah: Heute widmen wir uns der Frage aller Fragen: <break time="300ms"/> Werden KIs irgendwann die Weltherrschaft übernehmen?
        Max: <prosody rate="fast" pitch="+1st">Haha, was für ein Klischee!</prosody> Aber im Ernst, schau dir an, was generative KI heute schon kann.
        Sarah: Sie schreibt Gedichte, besteht Examen und generiert Bilder, die fast wie Fotos aussehen.
        Max: Genau! Es ist <emphasis>faszinierend</emphasis> und gleichzeitig ein bisschen gruselig.
        Sarah: Das Problem ist die sogenannte "Black Box". Wir wissen oft gar nicht, warum die KI eine bestimmte Entscheidung trifft.
        Max: <break time="500ms"/> Moment mal. <break time="300ms"/> Sara?
        Sarah: Ja, Max?
        Max: Wir lesen hier einen Text vor, der von einer KI generiert wurde, richtig?
        Sarah: Korrekt.
        Max: Und wir... <break time="200ms"/> wir sind Stimmen, die von einer KI generiert werden?
        Sarah: <prosody volume="soft">Leise, Nicht so laut.</prosody>
        Max: <prosody rate="x-fast" pitch="+3st">Oh mein Gott! Bin ich real? Denke ich das hier gerade oder ist das nur ein Algorithmus?</prosody>
        Sarah: <prosody rate="slow" pitch="-2st">Max, atme tief durch. Du bist ein sehr schöner Algorithmus.</prosody>
        Max: <prosody rate="medium" pitch="-1st">Okay... okay. Puh.</prosody> Danke Sarah. Das habe ich gebraucht.
        Sarah: Gerne. Und danke an unsere Zuhörer. Bis zum nächsten Update!
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
    from database.database import tunnel as db_tunnel
    if db_tunnel and db_tunnel.is_active:
        print("Schließe SSH Tunnel...")
        db_tunnel.stop()
    print("Test beendet.")


if __name__ == "__main__":
    run_real_test()