import logging
from datetime import date
from dotenv import load_dotenv
import os
import uuid
from paramiko import RSAKey
# DSSKey nicht mehr verwenden


from .llm_service import LLMService
from .tts_service import GoogleTTSService
from .exceptions import TTSServiceError
from database.database import get_db
from database.models import PodcastStimme, Textbeitrag, Konvertierungsauftrag, Podcast, AuftragsStatus
from repositories import VoiceRepo, TextRepo, JobRepo, PodcastRepo


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
        zweitstimme: str | None,
        
        
        
    ) -> str:

        config = {
            "language": sprache,
            "dauer": dauer,
            "speakers": speakers,
            "roles": roles or {"Max": "Moderator",
            "Sara": "Expertin"},
            "hauptstimme": hauptstimme,
            "zweitstimme": zweitstimme,   # oder None
            "style": "gechillt"

        }

        script = self.llm_service.generate_script(
            thema=thema,
            config=config,
            #hauptstimme=hauptstimme,
            #zweitstimme=zweitstimme
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

        audio_segment = self.tts_service.generate_audio(
            script_text=script,
            primary_voice=primary_voice,
            secondary_voice=secondary_voice
        )

        if not audio_segment:
            raise TTSServiceError("TTS lieferte kein Audio")

        # Speichern des Audios (jetzt im Workflow)
        try:
            filename = f"podcast_google_{uuid.uuid4()}.mp3"
            # Pfad relativ zum Projekt-Root oder absolut, hier einfach Dateiname im aktuellen Dir
            # Falls ein spezieller Output-Ordner gewünscht ist, hier anpassen.
            audio_segment.export(filename, format="mp3", bitrate="192k")
            logger.info(f"Audio erfolgreich gespeichert: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Audiodatei: {e}")
            raise TTSServiceError(f"IO Error beim Speichern: {e}")

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
        text_repo = TextRepo(session)
        job_repo = JobRepo(session)
        podcast_repo = PodcastRepo(session)

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
            # Add via Repo (commits internally)
            text = text_repo.add(text)

            # Konvertierungsauftrag
            job = Konvertierungsauftrag(
                textId=text.textId,
                modellId=tts_id,
                hauptstimmeId=primary_voice.stimmeId,
                zweitstimmeId=secondary_voice.stimmeId if secondary_voice else None,
                gewuenschteDauer=dauer,
                status=AuftragsStatus.IN_BEARBEITUNG
            )
            job = job_repo.add(job)

            # Podcast (Audio-Datei)
            podcast = Podcast(
                auftragId=job.auftragId,
                titel=thema,
                realdauer=dauer,
                dateipfadAudio=audio_path,
                erstelldatum=date.today()
            )
            podcast = podcast_repo.add(podcast)

            logger.info(f"Workflow erfolgreich in DB gespeichert: Auftrag {job.auftragId}")
            return text, job, podcast

        except Exception:
            # session.rollback() # Not needed or effective as repo.add commits
            logger.error("Fehler beim Speichern der Metadaten", exc_info=True)
            raise

    # --------------------------------------------------
    # PUBLIC API for UI Integration
    # --------------------------------------------------
    def generate_script_step(self, thema: str, dauer: int, sprache: str, hauptstimme: str = "Max", zweitstimme: str = "Sarah") -> str:
        """ Wrapper für den Skript-Generierungsschritt der UI """
        
        # Check if second voice is selected
        has_second_voice = zweitstimme and zweitstimme != "Keine"
        speakers = 2 if has_second_voice else 1
        
        return self._generate_script(
            thema=thema,
            sprache=sprache,
            dauer=dauer,
            speakers=speakers,
            roles={},
            hauptstimme=hauptstimme,
            zweitstimme=zweitstimme if has_second_voice else None
        )

    def generate_audio_step(self, script_text: str, thema: str, dauer: int, sprache: str, hauptstimme: str, zweitstimme: str | None) -> str:
        """ Wrapper für den Audio-Generierungsschritt der UI """
        user_id = 1
        llm_id = 1
        tts_id = 1
        
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            
            # Stimmen laden via Repo
            primary_voice_db = None
            voices_p = voice_repo.get_voices_by_names([hauptstimme])
            if voices_p:
                primary_voice_db = voices_p[0]

            secondary_voice_db = None
            if zweitstimme and zweitstimme != "Keine":
                voices_s = voice_repo.get_voices_by_names([zweitstimme])
                if voices_s:
                    secondary_voice_db = voices_s[0]

            if not primary_voice_db:
                 # Fallback
                 voices_fallback = voice_repo.get_voices_by_names(["Max"])
                 if voices_fallback:
                     primary_voice_db = voices_fallback[0]
                 else:
                    raise ValueError(f"Stimme '{hauptstimme}' nicht gefunden und Standardstimme 'Max' auch nicht.")
            
            primary_voice = VoiceDTO(primary_voice_db.stimmeId, primary_voice_db.name, primary_voice_db.ttsVoice)
            secondary_voice = None
            if secondary_voice_db:
                secondary_voice = VoiceDTO(secondary_voice_db.stimmeId, secondary_voice_db.name, secondary_voice_db.ttsVoice)

            # Audio erzeugen
            audio_path = self._generate_audio(script_text, primary_voice, secondary_voice)

            # Metadaten speichern (nutzt Repos)
            self._save_metadata(
                session=session,
                user_id=user_id,
                llm_id=llm_id,
                tts_id=tts_id,
                user_prompt="", 
                script=script_text,
                thema=thema,
                dauer=dauer,
                sprache=sprache,
                primary_voice=primary_voice,
                secondary_voice=secondary_voice,
                audio_path=audio_path
            )
            return audio_path
        finally:
            session.close()

    def get_podcasts(self):
        """ Gibt eine Liste aller Podcasts für die UI Tabelle zurück """
        session = get_db()
        try:
            podcast_repo = PodcastRepo(session)
            podcasts = podcast_repo.get_all_sorted_by_date_desc()
            result = []
            for p in podcasts:
                result.append([p.titel, str(p.realdauer) + " min", str(p.erstelldatum)])
            return result
        finally:
            session.close()

    '''
    def get_audio_path_by_index(self, index: int) -> str:
        """ Gibt den Pfad anhand des Tabellen-Index zurück """
        session = get_db()
        try:
            podcast_repo = PodcastRepo(session)
            podcasts = podcast_repo.get_all_sorted_by_date_desc()
            if 0 <= index < len(podcasts):
                return podcasts[index].dateipfadAudio
            return ""
        finally:
            session.close()
    '''
    
    def get_podcasts_data(self):
        """ Returns list of dicts for the UI cards """
        session = get_db()
        try:
            podcast_repo = PodcastRepo(session)
            podcasts = podcast_repo.get_all_sorted_by_date_desc()
            result = []
            for p in podcasts:
                result.append({
                    "titel": p.titel,
                    "dauer": p.realdauer,
                    "datum": str(p.erstelldatum),
                    "path": p.dateipfadAudio
                })
            return result
        finally:
            session.close()

    def get_voices(self):
        """ Gibt Liste verfügbarer Stimmen zurück """
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            voices = voice_repo.get_all()
            return [v.name for v in voices]
        finally:
            session.close()

    # --------------------------------------------------
    # PUBLIC API (Legacy / Full Pipeline)
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
            voice_repo = VoiceRepo(session)
            # ------------------------------
            # Stimmen aus DB laden
            # ------------------------------
            primary_voice_db = None
            voices_p = voice_repo.get_voices_by_names([hauptstimme])
            if voices_p:
                primary_voice_db = voices_p[0]

            if not primary_voice_db:
                raise ValueError(f"Hauptstimme '{hauptstimme}' nicht in der DB gefunden")

            secondary_voice_db = None
            if zweitstimme:
                voices_s = voice_repo.get_voices_by_names([zweitstimme])
                if voices_s:
                    secondary_voice_db = voices_s[0]
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
    