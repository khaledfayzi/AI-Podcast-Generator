# NOTE: Workflow Orchestrierung (Business Logic)
# Hier läuft alles zusammen. Diese Datei steuert den Ablauf "Prompt -> Audio".
# Sie verbindet die Datenbank, den LLM-Service und den TTS-Service.
#
# Einzufügen / Umzusetzen:
# - Klasse 'PodcastWorkflow':
#   - Initialisiert LLMService und TTSService.
#   - Methode 'run_pipeline(user_prompt)':
#     1. Ruft LLMService auf -> erhält Skript.
#     2. Speichert das Skript als 'Textbeitrag' in der DB.
#     3. Ruft TTSService auf -> erhält Audio-Pfad.
#     4. Speichert das Ergebnis als 'Podcast' in der DB.
#
# Dies ist die Schnittstelle, die später vom UI aufgerufen wird.

# services/workflow.py

import logging
from datetime import date

from .llm_service import LLMService
from .tts_service import GoogleTTSService
from repositories.voice_repo import VoiceRepo
from models import (
    AuftragsStatus,
    Konvertierungsauftrag,
    Textbeitrag,
    Podcast,
    PodcastStimme
)
from database import get_db
from dotenv import load_dotenv
import os

load_dotenv() # Lese die .env Datei
logger = logging.getLogger(__name__)

# Zugriff auf die Variablen im Code:
gemini_key = os.getenv("GEMINI_API_KEY")
db_user = os.getenv("DB_USER")
# etc.

class DummyPodcastStimme:
    """Simuliert das nötige Datenbank-Stimmenobjekt."""
    def __init__(self, voice_id, name, tts_voice_string):
        self.stimmeId = voice_id
        self.name = name 
        self.ttsVoice = tts_voice_string


class Workflow:
    """
    Orchestriert den kompletten Podcast-Prozess:
    Prompt → Skript → Audio → DB
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.tts_service = GoogleTTSService()

    # ------------------------------------------------------------------
    # 1) Stimmen laden
    # ------------------------------------------------------------------
    def _load_voices(self, session, hauptstimme: str, zweitstimme: str | None):
        repo = VoiceRepo(session)

        primary = repo.get_voice_by_name(hauptstimme)
        if not primary:
            raise ValueError(f"Hauptstimme '{hauptstimme}' nicht gefunden")

        secondary = None
        if zweitstimme:
            secondary = repo.get_voice_by_name(zweitstimme)
            if not secondary:
                logger.warning(
                    f"Zweitstimme '{zweitstimme}' nicht gefunden → Solo"
                )

        return primary, secondary

    # ------------------------------------------------------------------
    # 2) LLM → Skript
    # ------------------------------------------------------------------
    def _generate_script(
        self,
        thema: str,
        sprache: str,
        dauer: int,
        speakers: int,
        roles: dict | None,
        hauptstimme: str,
        zweitstimme: str | None
    ) -> str:

        config = {
            "language": sprache,
            "dauer": dauer,
            "speakers": speakers,
            "roles": roles or {}
        }

        script = self.llm_service.generate_script(
            thema=thema,
            config=config,
            hauptstimme=hauptstimme,
            zweitstimme=zweitstimme
        )

        logger.info("Skript generiert")
        return script

    # ------------------------------------------------------------------
    # 3) Metadaten speichern (Commit #1)
    # ------------------------------------------------------------------
    def _save_metadata(
        self,
        session,
        user_id: int,
        llm_id: int,
        tts_id: int,
        user_prompt: str,
        script: str,
        thema: str,
        dauer: int,
        sprache: str,
        primary_voice,
        secondary_voice
    ):
        text = Textbeitrag(
            userId=user_id,
            llmId=llm_id,
            userPrompt=user_prompt,
            erzeugtesSkript=script,
            titel=thema,
            erstelldatum=date.today(),
            sprache=sprache
        )
        session.add(text)
        session.flush()  # textId verfügbar machen

        job = Konvertierungsauftrag(
            textId=text.textId,
            modellId=tts_id,
            hauptstimmeId=primary_voice.stimmeId,
            zweitstimmeId=secondary_voice.stimmeId if secondary_voice else None,
            gewuenschteDauer=dauer,
            status=AuftragsStatus.IN_BEARBEITUNG
        )
        session.add(job)
        session.commit()

        logger.info(f"Konvertierungsauftrag {job.auftragId} angelegt")
        return text, job

    # ------------------------------------------------------------------
    # 4) TTS → Audio
    # ------------------------------------------------------------------
    def _generate_audio(self, script, primary_voice, secondary_voice):
        audio_path = self.tts_service.generate_audio(
            script_text=script,
            primary_voice=primary_voice,
            secondary_voice=secondary_voice
        )
        if not audio_path:
            raise RuntimeError("TTS lieferte kein Audio")

        return audio_path

    # ------------------------------------------------------------------
    # 5) Podcast speichern (Commit #2)
    # ------------------------------------------------------------------
    def _save_podcast(self, session, job, thema, dauer, audio_path):
        job.status = AuftragsStatus.ABGESCHLOSSEN
        session.add(job)

        podcast = Podcast(
            auftragId=job.auftragId,
            titel=thema,
            realdauer=dauer * 60,
            dateipfadAudio=audio_path,
            erstelldatum=date.today(),
            isPublic=True
        )
        session.add(podcast)
        session.commit()

        logger.info(f"Podcast {podcast.podcastId} gespeichert")
        return podcast

    # ------------------------------------------------------------------
    # PUBLIC API (UI Entry Point)
    # ------------------------------------------------------------------
    # services/workflow.py (Auszug)
# ... (Imports und Class Workflow Definition)

    # ------------------------------------------------------------------
    # PUBLIC API (UI Entry Point) - NUR ZUM TESTEN VON LLM & TTS
    # ------------------------------------------------------------------
    
    def run_pipeline(
        self,
        user_prompt: str,
        # DB-bezogene Parameter werden ignoriert
        #user_id: int,
        #llm_id: int,
        #tts_id: int,
        thema: str,
        dauer: int,
        sprache: str,
        hauptstimme: str,
        zweitstimme: str | None = None,
        speakers: int = 1,
        roles: dict | None = None
    ) -> str:
        
        # session = get_db()  # DB-Session wird nicht mehr benötigt

        try:
            # 1. STIMMEN LADEN (Muss angepasst werden, da VoiceRepo die DB braucht)
            # Da wir die DB ignorieren, verwenden wir Dummy-Stimmen-Objekte
            # und übergeben die Namen direkt an den TTS-Service.
            primary_voice = DummyPodcastStimme(
                voice_id=1,
                name=hauptstimme,
                tts_voice_string="de-DE-Wavenet-D") # Wir nutzen den Namen als Dummy-Objekt
            
            secondary_voice = None
            if zweitstimme:
             secondary_voice = DummyPodcastStimme(
                voice_id=2, 
                name=zweitstimme, 
                tts_voice_string="de-DE-Wavenet-F" 
            )
            
            
            
            # 2. LLM -> Skript generieren (TEST LLM)
            script = self._generate_script(
                thema, sprache, dauer, speakers, roles,
                hauptstimme, zweitstimme
            )
            logger.info("Skript generiert (LLM-Test erfolgreich)")

            # 3. Metadaten speichern (ÜBERSPRINGEN)
            # _, job = self._save_metadata(...)

            # 4. TTS -> Audio generieren (TEST TTS)
            audio_path = self._generate_audio(script, primary_voice, secondary_voice)
            logger.info(f"Audio generiert (TTS-Test erfolgreich): {audio_path}")
            
            # 5. Podcast speichern (ÜBERSPRINGEN)
            # self._save_podcast(...)

            return audio_path

        except Exception as e:
            # session.rollback() # Rollback nicht nötig, da keine DB-Transaktion
            logger.error(f"Workflow fehlgeschlagen: {e}", exc_info=True)
            raise 

        # finally:
        #     session.close() # Schließen nicht nötig