import logging
from datetime import date
from dotenv import load_dotenv
import os
from paramiko import RSAKey
# DSSKey nicht mehr verwenden


from .llm_service import LLMService
from .tts_service import GoogleTTSService
from .exceptions import TTSServiceError
from database.database import get_db
from database.models import PodcastStimme, Textbeitrag, Konvertierungsauftrag, Podcast, AuftragsStatus


import logging
from dotenv import load_dotenv
from pydub.utils import which
from pydub import AudioSegment

# --------------------------------------------------
# ffmpeg Pfad setzen (wichtig für pydub)
# --------------------------------------------------
#AudioSegment.converter = r"C:\Users\musti\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
#AudioSegment.ffprobe = r"C:\Users\musti\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffprobe.exe"

# --------------------------------------------------
# Logging und ENV laden
# --------------------------------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MAIN")

# --------------------------------------------------
# Setup
# --------------------------------------------------
load_dotenv()
logger = logging.getLogger(__name__)

class VoiceDTO:
    """Einheitliches Voice-Objekt (DTO)"""
    def __init__(self, voice_id: int, name: str, tts_voice: str):
        self.stimmeId = voice_id
        self.name = name
        self.ttsVoice = tts_voice


class PodcastWorkflow:
    """Workflow: LLM → Skript → TTS → DB"""

    def __init__(self):
        self.llm_service = LLMService()
        self.tts_service = GoogleTTSService()

    # --------------------------------------------------
    # 1) LLM → Skript
    # --------------------------------------------------
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
        logger.info("Skript erfolgreich vom LLM generiert")
        return script

    # --------------------------------------------------
    # 2) TTS → Audio
    # --------------------------------------------------
    def _generate_audio(
        self,
        script: str,
        primary_voice: VoiceDTO,
        secondary_voice: VoiceDTO | None
    ) -> str:

        audio_path = self.tts_service.generate_audio(
            script_text=script,
            primary_voice=primary_voice,
            secondary_voice=secondary_voice
        )

        if not audio_path:
            raise TTSServiceError("TTS lieferte kein Audio")

        return audio_path

    # --------------------------------------------------
    # 3) Metadaten speichern
    # --------------------------------------------------
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
        primary_voice: VoiceDTO,
        secondary_voice: VoiceDTO | None,
        audio_path: str
    ):
        try:
            # Textbeitrag
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

            # Konvertierungsauftrag
            job = Konvertierungsauftrag(
                textId=text.textId,
                modellId=tts_id,
                hauptstimmeId=primary_voice.stimmeId,
                zweitstimmeId=secondary_voice.stimmeId if secondary_voice else None,
                gewuenschteDauer=dauer,
                status=AuftragsStatus.IN_BEARBEITUNG
            )
            session.add(job)
            session.flush()  # auftragId verfügbar machen

            # Podcast (Audio-Datei)
            podcast = Podcast(
                auftragId=job.auftragId,
                titel=thema,
                realdauer=dauer,
                dateipfadAudio=audio_path,
                erstelldatum=date.today()
            )
            session.add(podcast)

            session.commit()
            logger.info(f"Workflow erfolgreich in DB gespeichert: Auftrag {job.auftragId}")
            return text, job, podcast

        except Exception:
            session.rollback()
            logger.error("Fehler beim Speichern der Metadaten", exc_info=True)
            raise

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------
    def run_pipeline(
        self,
        user_id: int,
        llm_id: int,
        tts_id: int,
        thema: str,
        dauer: int,
        sprache: str,
        hauptstimme: str,
        zweitstimme: str | None = None,
        speakers: int = 1,
        roles: dict | None = None,
        user_prompt: str = ""
    ) -> str:
        """
        Führt den Workflow aus: DB-Stimmen → LLM → TTS → DB
        Rückgabe: Pfad zur generierten Audio-Datei
        """
        session = get_db()
        try:
            # ------------------------------
            # Stimmen aus DB laden
            # ------------------------------
            primary_voice_db = session.query(PodcastStimme).filter_by(name=hauptstimme).first()
            if not primary_voice_db:
                raise ValueError(f"Hauptstimme '{hauptstimme}' nicht in der DB gefunden")

            secondary_voice_db = None
            if zweitstimme:
                secondary_voice_db = session.query(PodcastStimme).filter_by(name=zweitstimme).first()
                if not secondary_voice_db:
                    raise ValueError(f"Zweitstimme '{zweitstimme}' nicht in der DB gefunden")

            primary_voice = VoiceDTO(
                voice_id=primary_voice_db.stimmeId,
                name=primary_voice_db.name,
                tts_voice=primary_voice_db.ttsVoice
            )
            secondary_voice = None
            if secondary_voice_db:
                secondary_voice = VoiceDTO(
                    voice_id=secondary_voice_db.stimmeId,
                    name=secondary_voice_db.name,
                    tts_voice=secondary_voice_db.ttsVoice
                )

            # ------------------------------
            # 1) LLM → Skript
            # ------------------------------
            script = self._generate_script(
                thema=thema,
                sprache=sprache,
                dauer=dauer,
                speakers=speakers,
                roles=roles,
                hauptstimme=hauptstimme,
                zweitstimme=zweitstimme
            )

            # ------------------------------
            # 2) TTS → Audio
            # ------------------------------
            audio_path = self._generate_audio(
                script=script,
                primary_voice=primary_voice,
                secondary_voice=secondary_voice
            )

            # ------------------------------
            # 3) Metadaten → DB
            # ------------------------------
            self._save_metadata(
                session=session,
                user_id=user_id,
                llm_id=llm_id,
                tts_id=tts_id,
                user_prompt=user_prompt,
                script=script,
                thema=thema,
                dauer=dauer,
                sprache=sprache,
                primary_voice=primary_voice,
                secondary_voice=secondary_voice,
                audio_path=audio_path
            )

            return audio_path

        except Exception:
            logger.error("PodcastWorkflow fehlgeschlagen", exc_info=True)
            raise
        
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MAIN")

    workflow = PodcastWorkflow()

    try:
        audio_file = workflow.run_pipeline(
            user_id=1,          # Dummy-User, z.B. für Test
            llm_id=1,           # Dummy LLM-ID
            tts_id=1,           # Dummy TTS-ID
            thema="Generative KI und ihre Anwendungen",
            dauer=1,
            sprache="de",
            hauptstimme="Max",
            zweitstimme="Sara",
            speakers=2
        )
        logger.info(f"Podcast erfolgreich erstellt: {audio_file}")
    except Exception as e:
        logger.error(f"Fehler beim Testlauf: {e}")
    