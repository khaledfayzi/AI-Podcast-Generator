from datetime import date
import os
import uuid
import re


from .llm_service import LLMService
from .tts_service import GoogleTTSService
from .exceptions import TTSServiceError
from database.database import get_db
from database.models import PodcastStimme, Textbeitrag, Konvertierungsauftrag, Podcast, AuftragsStatus
from repositories import VoiceRepo, TextRepo, JobRepo, PodcastRepo


import logging
from dotenv import load_dotenv


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
            source_text: str | None = None,
    ) -> str:

        config = {
            "language": sprache,
            "dauer": dauer,
            "speakers": speakers,
            "roles": roles or {},
            "hauptstimme": hauptstimme,
            "zweitstimme": zweitstimme,
            "source_text": (source_text or "").strip(),
            "source_max_chars": 12000,
        }

        # Skript vom LLM generieren lassen (nutzt jetzt Markdown laut System-Prompt)
        script = self.llm_service.generate_script(
            thema=thema,
            config=config
        )

        # WICHTIG: Falls das LLM trotz Anweisung XML-Tags (<...>) liefert,
        # löschen wir diese hier für die UI-Anzeige heraus.
        # Markdown wie **Text** oder [pause] bleibt erhalten!
        clean_script = re.sub(r'<[^>]*>', '', script)

        logger.info("Skript erfolgreich generiert und XML-Tags für UI entfernt.")
        return clean_script.strip()

    # --------------------------------------------------
    # 2) TTS → Audio (VERARBEITET NUTZER-MARKDOWN)
    # --------------------------------------------------

    # --------------------------------------------------
    # 2) TTS → Audio
    # --------------------------------------------------
    """
    Wird nicht mehr benutzt, keeping it just in case
    
    def _generate_audio(self, script: str, sprache: str, primary_voice: PodcastStimme,
                        secondary_voice: PodcastStimme | None) -> str:
        audio_segment = self.tts_service.generate_audio(
            script_text=script,
            sprache=sprache,
            primary_voice=primary_voice,
            secondary_voice=secondary_voice
        )

        if not audio_segment:
            raise TTSServiceError("TTS lieferte kein Audio")

        try:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Output")
            os.makedirs(output_dir, exist_ok=True)
            filename = f"podcast_google_{uuid.uuid4()}.mp3"
            filepath = os.path.join(output_dir, filename)
            db_path = os.path.join("Output", filename)

            audio_segment.export(filepath, format="mp3")
            logger.info(f"Audio erfolgreich gespeichert: {filepath}")
            return db_path
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Audiodatei: {e}")
            raise TTSServiceError(f"IO Error beim Speichern: {e}")
    """
    
    # --------------------------------------------------
    # 3) Metadaten speichern
    # --------------------------------------------------
    def _save_metadata(self, session, user_id, llm_id, tts_id, user_prompt, script, thema, dauer, sprache,
                       primary_voice, secondary_voice, audio_path, primary_role=None, secondary_role=None):
        text_repo = TextRepo(session)
        job_repo = JobRepo(session)
        podcast_repo = PodcastRepo(session)
        try:
            text = text_repo.add(Textbeitrag(
                userId=user_id, llmId=llm_id, userPrompt=user_prompt,
                erzeugtesSkript=script, titel=thema, erstelldatum=date.today(), sprache=sprache
            ))
            job = job_repo.add(Konvertierungsauftrag(
                textId=text.textId, modellId=tts_id,
                hauptstimmeId=primary_voice.stimmeId,
                zweitstimmeId=secondary_voice.stimmeId if secondary_voice else None,
                hauptstimmeRolle=primary_role,  # NEU
                zweitstimmeRolle=secondary_role if secondary_voice else None,  # NEU
                gewuenschteDauer=dauer, status=AuftragsStatus.IN_BEARBEITUNG
            ))
            podcast = podcast_repo.add(Podcast(
                auftragId=job.auftragId, titel=thema, realdauer=dauer,
                dateipfadAudio=audio_path, erstelldatum=date.today()
            ))
            return text, job, podcast
        except Exception:
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
            zweitstimme=zweitstimme if has_second_voice else None,
            
        )

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

    def get_podcasts_data(self, user_id: int = None):
        """ Returns list of dicts for the UI cards, filtered by user_id if provided. """
        session = get_db()
        try:
            podcast_repo = PodcastRepo(session)
            if user_id:
                podcasts = podcast_repo.get_by_user_id(user_id)
                podcasts.sort(key=lambda x: x.erstelldatum, reverse=True)
            else:
                return []
                
            result = []
            for p in podcasts:
                job = p.konvertierungsauftrag
                
                # Build speaker and role strings
                speakers = []
                roles = []
                
                if job.hauptstimme:
                    speakers.append(job.hauptstimme.name)
                    # NEU: Nutze die gespeicherte Rolle
                    roles.append(job.hauptstimmeRolle or "Sprecher")
                    
                if job.zweitstimme:
                    speakers.append(job.zweitstimme.name)
                    # NEU: Nutze die gespeicherte Rolle
                    roles.append(job.zweitstimmeRolle or "Sprecher")
                
                text = job.textbeitrag
                sprache = text.sprache if text else "Deutsch"
                
                speaker_str = " & ".join(speakers) if speakers else "Unbekannt"
                roles_str = ", ".join(roles) if roles else ""
                
                result.append({
                    "id": p.podcastId,
                    "titel": p.titel,
                    "dauer": p.realdauer,
                    "datum": str(p.erstelldatum),
                    "path": p.dateipfadAudio,
                    "sprecher": speaker_str,
                    "rollen": roles_str,
                    "sprache": sprache
                })
            return result
        finally:
            session.close()

    def get_voices_for_ui(self):
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            # Wir holen die Namen getrennt nach Slot 1 und 2
            primary_names = [v.name for v in voice_repo.get_voices_by_slot(1)]
            secondary_names = [v.name for v in voice_repo.get_voices_by_slot(2)]
            return primary_names, secondary_names
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

    def generate_audio_obj_step(self, script_text, sprache, hauptstimme, zweitstimme):
        """Generates the audio object in MEMORY (does not save to disk)."""
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            db_p = voice_repo.get_voices_by_names([hauptstimme])[0]
            db_s = None
            if zweitstimme and zweitstimme != "Keine":
                db_s = voice_repo.get_voices_by_names([zweitstimme])[0]
            
            # Return the Pydub AudioSegment directly without exporting
            return self.tts_service.generate_audio(
                script_text=script_text,
                sprache=sprache,
                primary_voice=db_p,
                secondary_voice=db_s
            )
        finally:
            session.close()

    def save_audio_file(self, audio_segment) -> str:
        """Saves an audio segment to the Output folder"""
        if not audio_segment:
             raise TTSServiceError("Kein Audio zum Speichern vorhanden")
        
        try:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Output")
            os.makedirs(output_dir, exist_ok=True)
            filename = f"podcast_google_{uuid.uuid4()}.mp3"
            filepath = os.path.join(output_dir, filename)
            db_path = os.path.join("Output", filename)

            audio_segment.export(filepath, format="mp3")
            logger.info(f"Audio erfolgreich gespeichert: {filepath}")
            return db_path
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Audiodatei: {e}")
            raise TTSServiceError(f"IO Error beim Speichern: {e}")
        
    def save_podcast_db(self, user_id, script, thema, dauer, sprache, hauptstimme, zweitstimme, audio_path, role1, role2):
        """
        Saves podcast metadata to the database
        Called by the UI backend after the file has been successfully generated and saved
        """
        llm_id, tts_id = 1, 1 # Fixed IDs for now
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            
            # Resolve Voice Names to DB Objects
            # Primary voice is assumed to exist
            db_p = voice_repo.get_voices_by_names([hauptstimme])[0]
            
            # Secondary voice is optional
            db_s = None
            if zweitstimme and zweitstimme != "Keine":
                voices_s = voice_repo.get_voices_by_names([zweitstimme])
                if voices_s:
                    db_s = voices_s[0]

            self._save_metadata(
                session=session, 
                user_id=user_id, 
                llm_id=llm_id, 
                tts_id=tts_id, 
                user_prompt="", 
                script=script, 
                thema=thema, 
                dauer=dauer, 
                sprache=sprache, 
                primary_voice=db_p, 
                secondary_voice=db_s,
                audio_path=audio_path, 
                primary_role=role1, 
                secondary_role=role2
            )
            
        except Exception as e:
            logger.error(f"Error saving podcast to DB: {e}")
            raise e
        finally:
            session.close()

    # --------------------------------------------------
    # PUBLIC API (Legacy / Full Pipeline)
    # --------------------------------------------------
    def generate_audio_step(self, script_text, thema, dauer, sprache, hauptstimme, zweitstimme, user_id=1, role1=None, role2=None):
        llm_id, tts_id = 1, 1
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            db_p = voice_repo.get_voices_by_names([hauptstimme])[0]
            db_s = None
            if zweitstimme and zweitstimme != "Keine":
                db_s = voice_repo.get_voices_by_names([zweitstimme])[0]

            audio_path = self._generate_audio(script_text, sprache, db_p, db_s)

            self._save_metadata(session, user_id, llm_id, tts_id, "", script_text, thema, dauer, sprache, db_p, db_s,
                                audio_path, role1, role2)  # NEU: Rollen übergeben
            return audio_path
        finally:
            session.close()

    def run_pipeline(self, user_id, llm_id, tts_id, thema, dauer, sprache, hauptstimme, zweitstimme=None,
                     **kwargs) -> str:
        session = get_db()
        try:
            voice_repo = VoiceRepo(session)
            db_p = voice_repo.get_voices_by_names([hauptstimme])[0]
            db_s = voice_repo.get_voices_by_names([zweitstimme])[0] if zweitstimme else None

            script = self._generate_script(thema, sprache, dauer, 2 if db_s else 1, {}, hauptstimme, zweitstimme)

            audio_path = self._generate_audio(script, sprache, db_p, db_s)

            self._save_metadata(session, user_id, llm_id, tts_id, "", script, thema, dauer, sprache, db_p, db_s,
                                audio_path)
            return audio_path
        finally:
            session.close()

    def delete_podcast(self, podcast_id: int, user_id: int) -> bool:
        """Deletes a podcast by ID, verifying user ownership."""
        session = get_db()
        try:
            podcast_repo = PodcastRepo(session)
            # Verify ownership before deletion
            user_podcasts = podcast_repo.get_by_user_id(user_id)
            if any(p.podcastId == podcast_id for p in user_podcasts):
                podcast_repo.delete_by_id(podcast_id)
                session.commit()
                return True
            return False
        finally:
            session.close()


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


