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

import logging
from datetime import date

from sqlalchemy import select

# Relative Imports innerhalb des 'services' Pakets
from llm_service import LLMService
from repositories.voice_repo import VoiceRepo
from tts_service import GoogleTTSService
from models import (
    AuftragsStatus,
    Konvertierungsauftrag,
    PodcastStimme,
    Textbeitrag,
    Podcast
)
from database import get_db

# Absoluter Import zur Ausnahme, da sie wahrscheinlich außerhalb von 'services' liegt (z.B. in team04/exceptions.py)

logger = logging.getLogger(__name__)

class Workflow:
    """
    Steuert den gesamten Prozess der Podcast-Generierung (Prompt -> Skript -> Audio).
    Kapselt die Geschäftslogik und sorgt für Transaktionssicherheit.
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.tts_service = GoogleTTSService()
        # ----------------------------------------------------------------------
        # 1) Stimmen aus DB laden und prüfen (Validierung)
        # ----------------------------------------------------------------------

    def _load_voices(self, voice_repo: VoiceRepo, hauptstimme: str, zweitstimme: str = None):
        """Lädt Stimmen über das Repository."""
        primary = voice_repo.get_voices_by_names(hauptstimme)
        if not primary:
            raise ValueError(f"Hauptstimme '{hauptstimme}' nicht gefunden.")

        secondary = None
        if zweitstimme:
            secondary = voice_repo.get_voices_by_names(zweitstimme)
            if not secondary:
                logger.warning(f"Zweitstimme '{zweitstimme}' nicht gefunden. Fallback auf Solo.")

        return primary, secondary

        # ----------------------------------------------------------------------
        # 2) LLM-Service → Skript generieren
        # ----------------------------------------------------------------------

    def _generate_script(self,user_prompt: str, thema: str,sprache: str,dauer: int, speaker: int,roles:dict):

        config = {
            "language": sprache, "style": "neutral", "dauer": dauer,
            "speakers": speaker, "roles": roles if roles else {}, "thema":thema
        }

        # Der LLMService fängt seinen eigenen Fehler ab und liefert ggf. Dummy-Text zurück.
        script = self.llm_service.generate_script(user_prompt, config)
        logger.info(f"Skript erfolgreich generiert (Auszug: {script[:50]}...)")
        return script

        # ----------------------------------------------------------------------
        # 3) Metadaten speichern (Commit #1 - Vor externem Service-Aufruf)
        # ----------------------------------------------------------------------
    def _save_metadata(self,session,user_id,llm_id,tts_id,user_prompt,script,thema,dauer,sprache):

        textbeitrag = Textbeitrag(
            userId=user_id, llmId=llm_id, userPrompt=user_prompt,
            erzeugtesSkript=script, titel=thema,
            erstelldatum=date.today(), sprache=sprache)
        session.add(textbeitrag)

        konvertierungsauftrag = Konvertierungsauftrag(
            textId=textbeitrag.textId, modellId=tts_id, gewuenschteDauer=dauer,
            status=AuftragsStatus.IN_BEARBEITUNG)
        session.add(konvertierungsauftrag)

        session.commit()
        logger.info(f"Metadaten gespeichert. Auftrag ID: {konvertierungsauftrag.auftragId} im Status IN_BEARBEITUNG.")
        return textbeitrag, konvertierungsauftrag


        # ----------------------------------------------------------------------
        # 4) TTS → Audio erstellen (mit Transaktionsschutz)
        # ----------------------------------------------------------------------
    def _generate_audio(self,script,primary_voice,secondary_voice):

        audio_path = self.tts_service.generate_audio(
            script_text=script, primary_voice=primary_voice, secondary_voice=secondary_voice,
        )
        logger.info(f"Audio generiert und gespeichert unter: {audio_path}")
        return audio_path

            # --- ERFOLGSFALL: DB-Update (Commit #2) ---
    def _save_podcast(self,session,konvertierungsauftrag,thema,dauer,audio_path):
        # Auftrag als abgeschlossen markieren
        konvertierungsauftrag.status = AuftragsStatus.ABGESCHLOSSEN
        session.add(konvertierungsauftrag)

            # Ergebnis als Podcast in der DB speichern
        podcast = Podcast(
            auftragId=konvertierungsauftrag.auftragId,
            titel=thema,
            realdauer=dauer * 60, # Umwandlung von Minuten in Sekunden
            dateipfadAudio=audio_path,
            erstelldatum=date.today(),
            isPublic=True
        )
        session.add(podcast)
        # Finaler Commit speichert beide Änderungen
        session.commit()
        logger.info(f"Podcast mit ID {podcast.podcastId} erfolgreich abgeschlossen.")

        return podcast

    def run_pipeline(self,user_prompt, user_id, llm_id, tts_id, thema,
                     dauer, sprache, hauptstimme, zweitstimme=None,
                     speakers=1, roles=None):
        session =get_db()

        # 1) Stimmen laden
        primary_voice, secondary_voice = self._load_voices(session, hauptstimme, zweitstimme)

        # 2) Skript generieren
        script = self._generate_script(user_prompt, thema, sprache, dauer, speakers, roles)

        # 3) Metadaten speichern
        textbeitrag, konvertierungsauftrag = self._save_metadata(
            session, user_id, llm_id, tts_id, user_prompt, script, thema, dauer, sprache
        )

        # 4) Audio erzeugen & Podcast speichern
        try:
            audio_path = self._generate_audio(script, primary_voice, secondary_voice)
            self._save_podcast(session, konvertierungsauftrag, thema, dauer, audio_path)
            return audio_path

        except Exception as e:
            session.rollback()
            konvertierungsauftrag.status = AuftragsStatus.FEHLGESCHLAGEN
            session.add(konvertierungsauftrag)
            session.commit()
            logger.error(f"Pipeline-Fehler, Auftrag ID {konvertierungsauftrag.auftragId}: {e}")
            raise RuntimeError(f"Fehler im Podcast-Workflow: {e}")