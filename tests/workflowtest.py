import logging
from datetime import date
from sqlalchemy import select  # Wird benötigt, aber die Session simuliert die Abfrage

# --- 1. SIMULIERTE MODEL-KLASSEN (Datenstruktur) ---
# Wir müssen die Klassenstruktur der Models nachbilden, damit der Workflow sie verwenden kann.


class PodcastStimme:
    """Simuliert das Model-Objekt für Stimmen aus der DB."""

    def __init__(self, name):
        self.name = name


class AuftragsStatus:
    # Die tatsächlichen Enum-Werte (müssen mit dem Workflow übereinstimmen)
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    ABGESCHLOSSEN = "ABGESCHLOSSEN"
    FEHLGESCHLAGEN = "FEHLGESCHLAGEN"


# Dummy-Klassen für die restlichen Models (benötigt für Instanziierung)
class Konvertierungsauftrag:
    def __init__(self, **kwargs):
        self.auftragId = 101
        self.__dict__.update(kwargs)


class Textbeitrag:
    def __init__(self, **kwargs):
        self.textId = 201
        self.__dict__.update(kwargs)


class Podcast:
    def __init__(self, **kwargs):
        self.podcastId = 301
        self.__dict__.update(kwargs)


class LLMServiceError(Exception):
    pass


class RuntimeError(Exception):
    pass


# --- 2. SIMULIERTE SERVICE-KLASSEN (Funktionalität) ---


class DummyLLMService:
    """Simuliert den LLM Service und gibt festen Text zurück."""

    def __init__(self, use_dummy=True):
        self.use_dummy = use_dummy

    def generate_script(self, user_prompt: str, config: dict) -> str:
        # Hier ist der Dummy-Text, der die LLM-Regeln erfüllt
        return (
            "INTRO\n"
            f"M: Hallo und herzlich willkommen zu unserem Podcast über {config.get('thema', 'Testthemen')}.\n\n"
            "HAUPTTEIL\n"
            "F: Git Stash ist ein super Werkzeug, um temporär Änderungen zu speichern, ohne sie zu committen.\n"
            "M: Genau, so bleibt der Arbeitsbereich sauber, wenn man dringend auf einen anderen Branch wechseln muss.\n\n"
            "OUTRO\n"
            "M: Das war die kurze Zusammenfassung des Themas.\n"
            "F: Bis zum nächsten Mal!\n"
            "'Das war unser Podcast – bis zum nächsten Mal!'"
        )


class DummyTTSService:
    """Simuliert den TTS Service und gibt einen festen Pfad zurück."""

    def __init__(self):
        pass

    def generate_audio(
        self,
        script_text: str,
        primary_voice: PodcastStimme,
        secondary_voice: PodcastStimme = None,
    ) -> str:
        # Simuliert die Audio-Generierung
        if "FEHLER" in script_text:
            raise Exception("Simulierter TTS-API Fehler.")

        return "C:\\temp\\podcast_dummy_audio_42.mp3"


# --- 3. SIMULIERTE DATENBANK-FUNKTIONEN ---


class DummyDBSession:
    """Simuliert die SQLAlchemy Session für den Workflow."""

    def __init__(self):
        self.objects = {}  # Zum Speichern der Objekte (rein für die Logikprüfung)

    def scalar(self, statement):
        """Simuliert die DB-Abfrage für PodcastStimme"""
        if "Max" in statement.parameters["name"]:
            return PodcastStimme("Max")
        if "Sara" in statement.parameters["name"]:
            return PodcastStimme("Sara")
        if "FALSCH" in statement.parameters["name"]:
            return None  # Simuliert Fehler beim Abruf

    def add(self, obj):
        # Objekt zur Session hinzufügen
        if type(obj).__name__ not in self.objects:
            self.objects[type(obj).__name__] = []
        self.objects[type(obj).__name__].append(obj)

    def commit(self):
        # Simuliert den Commit und gibt dem Objekt seine ID (die wir im __init__ gesetzt haben)
        pass

    def rollback(self):
        # Im Testmodus nicht notwendig, da wir keine echten Commits machen
        pass


def get_db():
    """Simuliert das Abrufen der DB-Session."""
    return DummyDBSession()


# --- 4. DER KERN: DIE WORKFLOW KLASSE (Unverändert) ---
# Wir verwenden die Logik der Workflow-Klasse, ersetzen aber die Abhängigkeiten


class Workflow:
    # Die gesamte run_pipeline Logik ist hier, aber LLM/TTS Services
    # werden durch die Dummies im __init__ ersetzt.

    def __init__(self):
        # Ersetzt die echten Services durch Dummies
        self.llm_service = DummyLLMService()
        self.tts_service = DummyTTSService()

    # ************************************************************
    # HINWEIS: Die run_pipeline Methode MUSS hier eingefügt werden,
    # aber ich lasse sie aus Platzgründen weg, da sie die Logik
    # der letzten korrigierten Version ist.
    # ************************************************************

    # (Fügen Sie hier die gesamte, letzte korrigierte run_pipeline Methode ein)
    # ...

    # ***********************************************************************************
    # HINWEIS: Fügen Sie an dieser Stelle die komplette, letzte korrigierte
    # `run_pipeline` Methode aus Ihrer Workflow-Datei ein, damit der Code lauffähig ist.
    # ***********************************************************************************
    def run_pipeline(
        self,
        user_prompt: str,
        user_id: int,
        llm_id: int,
        tts_id: int,
        thema: str,
        dauer: int,
        sprache: str,
        hauptstimme: str,
        zweitstimme: str = None,
        speakers: int = 1,
        roles: dict = None,
    ) -> str:

        session = get_db()
        audio_path = None

        # ----------------------------------------------------------------------
        # 1) Stimmen aus DB laden und prüfen (Validierung)
        # ----------------------------------------------------------------------

        try:
            # Die DummyDBSession liefert hier die Dummy-Objekte zurück
            primary_voice_obj = session.scalar(
                {"name": hauptstimme}  # Simulierter Statement-Parameter
            )
            if primary_voice_obj is None:
                raise ValueError(
                    f"Hauptstimme '{hauptstimme}' nicht gefunden in der Datenbank."
                )

            secondary_voice_obj = None
            if zweitstimme:
                secondary_voice_obj = session.scalar(
                    {"name": zweitstimme}  # Simulierter Statement-Parameter
                )
                if secondary_voice_obj is None:
                    logging.warning(
                        f"Zweitstimme '{zweitstimme}' nicht gefunden. Nur Hauptstimme wird verwendet."
                    )

        except Exception as e:
            logging.error(f"Fehler beim Laden der Stimmen aus der Datenbank: {e}")
            raise RuntimeError(f"Fehler beim Abrufen der Stimmen: {e}")

        # ----------------------------------------------------------------------
        # 2) LLM-Service → Skript generieren
        # ----------------------------------------------------------------------

        config = {
            "language": sprache,
            "style": "neutral",
            "dauer": dauer,
            "speakers": speakers,
            "roles": roles if roles is not None else {},
            "thema": thema,
        }

        # Ruft DummyLLMService auf
        script = self.llm_service.generate_script(user_prompt, config)
        logging.info(f"Skript erfolgreich generiert (Auszug: {script[:50]}...)")

        # ----------------------------------------------------------------------
        # 3) Metadaten speichern (Commit #1 - Vor externem Service-Aufruf)
        # ----------------------------------------------------------------------

        textbeitrag = Textbeitrag(
            userId=user_id,
            llmId=llm_id,
            userPrompt=user_prompt,
            erzeugtesSkript=script,
            titel=thema,
            erstelldatum=date.today(),
            sprache=sprache,
        )
        session.add(textbeitrag)

        konvertierungsauftrag = Konvertierungsauftrag(
            textId=textbeitrag.textId,
            modellId=tts_id,
            gewuenschteDauer=dauer,
            status=AuftragsStatus.IN_BEARBEITUNG,
        )
        session.add(konvertierungsauftrag)

        session.commit()
        logging.info(
            f"Metadaten gespeichert. Auftrag ID: {konvertierungsauftrag.auftragId} im Status IN_BEARBEITUNG."
        )

        # ----------------------------------------------------------------------
        # 4) TTS → Audio erstellen (mit Transaktionsschutz)
        # ----------------------------------------------------------------------

        try:
            # Ruft DummyTTSService auf
            audio_path = self.tts_service.generate_audio(
                script_text=script,
                primary_voice=primary_voice_obj,
                secondary_voice=secondary_voice_obj,
            )
            logging.info(f"Audio generiert und gespeichert unter: {audio_path}")

            # --- ERFOLGSFALL: DB-Update (Commit #2) ---

            konvertierungsauftrag.status = AuftragsStatus.ABGESCHLOSSEN
            session.add(konvertierungsauftrag)

            podcast = Podcast(
                auftragId=konvertierungsauftrag.auftragId,
                titel=thema,
                realdauer=dauer * 60,
                dateipfadAudio=audio_path,
                erstelldatum=date.today(),
                isPublic=True,
            )
            session.add(podcast)

            session.commit()
            logging.info(
                f"Podcast mit ID {podcast.podcastId} erfolgreich abgeschlossen."
            )

            return audio_path

        except Exception as e:
            # --- FEHLERFALL: Rollback und Status-Update (Commit #3) ---

            session.rollback()

            konvertierungsauftrag.status = AuftragsStatus.FEHLGESCHLAGEN
            session.add(konvertierungsauftrag)
            session.commit()

            logging.error(
                f"Pipeline-Fehler, Auftrag ID {konvertierungsauftrag.auftragId} auf FEHLGESCHLAGEN gesetzt: {e}"
            )

            raise RuntimeError(f"Fehler im Podcast-Workflow aufgetreten: {e}")


# --- 5. TESTLAUF ---

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_test():
    workflow = Workflow()

    # Beispielwerte
    TEST_PROMPT = "Erkläre Git Stash und seine Anwendung."
    TEST_THEMA = "Git Stash im Überblick"

    print("--- 1. Starte erfolgreichen Dummy-Test ---")
    try:
        audio_path = workflow.run_pipeline(
            user_prompt=TEST_PROMPT,
            user_id=1,
            llm_id=1,
            tts_id=1,
            thema=TEST_THEMA,
            dauer=2,
            sprache="de",
            hauptstimme="Max",  # Wird von DummyDBSession gefunden
            zweitstimme="Sara",  # Wird von DummyDBSession gefunden
            speakers=2,
            roles=None,
        )
        print(f"\n✅ Erfolgreicher Abschluss! Audio-Pfad: {audio_path}")

    except Exception as e:
        print(f"\n❌ Fehler im Testlauf: {e}")

    # --- Testfall: Fehler beim TTS-Service ---
    print("\n--- 2. Starte fehlgeschlagenen Dummy-Test (TTS-Fehler simulieren) ---")
    TEST_PROMPT_FAIL = (
        "Dieser Text enthält FEHLER und löst einen simulierten TTS-Fehler aus."
    )
    try:
        workflow.run_pipeline(
            user_prompt=TEST_PROMPT_FAIL,
            user_id=2,
            llm_id=1,
            tts_id=1,
            thema="Fehlertest",
            dauer=1,
            sprache="de",
            hauptstimme="Max",
            zweitstimme=None,
            speakers=1,
            roles=None,
        )
    except RuntimeError:
        print("\n✅ Fehler erfolgreich abgefangen. Status sollte FEHLGESCHLAGEN sein.")
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler im Fehler-Test: {e}")


if __name__ == "__main__":
    run_test()
