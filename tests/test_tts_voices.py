import sys
import os
import logging
from pydub import AudioSegment

# Add the parent directory to sys.path to allow imports from team04
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import get_db, init_db_connection
from repositories.voice_repo import VoiceRepo
from services.tts_service import GoogleTTSService
from database.models import PodcastStimme

# ==========================================
# KONFIGURATION: Hier die Namen ändern!
# ==========================================
SPEAKER_1_NAME = "Max"  # Name des ersten Sprechers (muss exakt so in DB sein)
SPEAKER_2_NAME = "Lena"  # Name des zweiten Sprechers (muss exakt so in DB sein)
SPRACHE = "Deutsch"  # "Deutsch" oder "Englisch"
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_test():
    print(f"Starte TTS Test für: {SPEAKER_1_NAME} und {SPEAKER_2_NAME}...")

    # 1. Datenbank initialisieren
    # Wir fangen RuntimeError ab, falls wir nicht im Flask-Context sind (was hier der Fall ist)
    try:
        init_db_connection()
        db = get_db()
    except Exception as e:
        print(f"Datenbank-Verbindungsfehler: {e}")
        return

    # 2. Repo und Service laden
    voice_repo = VoiceRepo(db)
    try:
        tts_service = GoogleTTSService()
    except Exception as e:
        print(f"Fehler beim Starten des TTS Service (Credentials prüfen?): {e}")
        return

    # 3. Stimmen laden
    print("Lade Stimmen aus der Datenbank...")
    voices = voice_repo.get_voices_by_names([SPEAKER_1_NAME, SPEAKER_2_NAME])

    # Zuordnung sicherstellen
    voice1 = next((v for v in voices if v.name == SPEAKER_1_NAME), None)
    voice2 = next((v for v in voices if v.name == SPEAKER_2_NAME), None)

    if not voice1:
        print(
            f"FEHLER: Stimme '{SPEAKER_1_NAME}' nicht gefunden! Bitte Namen in DB prüfen."
        )
        return
    if not voice2:
        print(
            f"FEHLER: Stimme '{SPEAKER_2_NAME}' nicht gefunden! Bitte Namen in DB prüfen."
        )
        return

    print(
        f"Gefunden: {voice1.name} (ID: {voice1.stimmeId}) und {voice2.name} (ID: {voice2.stimmeId})"
    )

    # 4. Dummy Dialog erstellen
    script = f"""
    {SPEAKER_1_NAME}: Hallo {SPEAKER_2_NAME}, willkommen zu unserem großen Stresstest für die neue Sprachausgabe. Wir haben heute einiges vor, um die Engine mal so richtig an ihre Grenzen zu bringen.
    {SPEAKER_2_NAME}: Hallo {SPEAKER_1_NAME}! Ich bin bereit. Es ist wichtig, dass wir nicht nur kurze Sätze testen, sondern auch längere Monologe und komplexe Satzgefüge. Wie ist dein erster Eindruck von der Latenz?
    {SPEAKER_1_NAME}: Bisher wirkt alles extrem reaktionsschnell. Aber die wahre Herausforderung liegt ja oft in der Betonung von zusammengesetzten Substantiven. Wörter wie „Donaudampfschifffahrtsgesellschaftskapitänswitwe“ sind zwar klischeehaft, zeigen aber gut, ob die KI die Wortstruktur versteht.
    {SPEAKER_2_NAME}: Das stimmt. Aber viel wichtiger für den Alltag sind die feinen Nuancen. Versteht die KI den Unterschied zwischen einer Frage, einer Feststellung und einer rhetorischen Pause? Manchmal macht ein kurzes Zögern an der richtigen Stelle den ganzen Unterschied zwischen „roboterhaft“ und „menschlich“.
    {SPEAKER_1_NAME}: Absolut richtig. Lass uns mal einen Absatz über Technik einbauen. Die Konfiguration der neuronalen Netzwerke erfolgt über eine Vielzahl von Parametern, wobei die Gewichtungen mit einer Präzision von 99,9 Prozent berechnet werden müssen, um Artefakte in der MP3-Ausgabe zu vermeiden. 
    {SPEAKER_2_NAME}: Das klang sehr flüssig. Ich merke auch, dass die Dynamik in der Stimme viel natürlicher wirkt als bei den alten Modellen. Früher klang das Ende eines Satzes oft so abgehackt, aber hier schwingt die Stimme sanft aus.
    {SPEAKER_1_NAME}: Lass uns auch kurz über Zahlen sprechen. Heute ist der 14. Januar 2026, und wir testen die Version 4.2 der Software. Wenn ich sage: „Die Kosten belaufen sich auf 1.250,50 Euro bei einer Inflationsrate von 2,3 Prozent“, muss die Betonung der Dezimalstellen sitzen.
    {SPEAKER_2_NAME}: Ein guter Punkt. Ein weiteres Thema ist die emotionale Färbung. Wenn wir ein Hörbuch vertonen würden, müssten wir auch Spannung erzeugen können. Stell dir vor, wir lesen eine Geschichte: „Es war eine dunkle und stürmische Nacht. Plötzlich hörte er ein Geräusch hinter der schweren Eichentür...“
    {SPEAKER_1_NAME}: Wow, das hatte fast schon etwas Mysteriöses! Man merkt, wie die KI versucht, den Kontext zu erfassen. Je mehr Text wir füttern, desto besser kann das Modell den roten Faden der Konversation beibehalten.
    {SPEAKER_2_NAME}: Genau. Wir sollten auch darauf achten, dass die Stimmen nicht ermüdend wirken, wenn man ihnen 15 oder 20 Minuten lang zuhört. Die kognitive Last für den Zuhörer sollte so gering wie möglich sein. Eine angenehme Sprachmelodie ist da das A und O.
    {SPEAKER_1_NAME}: Ich denke, für diesen Testdurchlauf haben wir jetzt eine hervorragende Datenbasis. Wir haben technische Begriffe, Zahlen, Emotionen und unterschiedliche Satzlängen abgedeckt. 
    {SPEAKER_2_NAME}: Einverstanden. Ich bin mit dem bisherigen Verlauf sehr zufrieden. Sollen wir die Aufnahme nun abschließen und das Rendering für die finale MP3-Datei starten?
    {SPEAKER_1_NAME}: Ja, machen wir es so. Ich stoppe die Aufnahme in drei, zwei, eins... jetzt.
    """
    print("\n--- Generiere Audio für folgenden Dialog ---")
    print(script)
    print("--------------------------------------------")

    # 5. Audio generieren
    try:
        audio = tts_service.generate_audio(
            script_text=script,
            sprache=SPRACHE,
            primary_voice=voice1,
            secondary_voice=voice2,
        )

        if audio:
            # Dateiname erstellen
            filename = f"tts_test_{SPEAKER_1_NAME}_{SPEAKER_2_NAME}_{SPRACHE}.mp3"
            # Im selben Ordner speichern wie das Skript
            output_path = os.path.join(os.path.dirname(__file__), filename)

            # Speichern
            audio.export(output_path, format="mp3")
            print(f"\n✅ ERFOLG! Datei gespeichert unter:\n{output_path}")
        else:
            print("\n❌ FEHLER: Keine Audio-Daten zurückbekommen (None).")

    except Exception as e:
        print(f"\n❌ FEHLER beim Generieren: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_test()
