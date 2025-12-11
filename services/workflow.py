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
        roles: dict = None) -> str:
        
        session = get_db()
        audio_path = None
        
        # ----------------------------------------------------------------------
        # 1) Stimmen aus DB laden und prüfen (Validierung)
        # ----------------------------------------------------------------------
        
        try:
            primary_voice_obj = session.scalar(
                select(PodcastStimme).where(PodcastStimme.name == hauptstimme)
            )
            if primary_voice_obj is None:
                raise ValueError(f"Hauptstimme '{hauptstimme}' nicht gefunden in der Datenbank.")
            
            secondary_voice_obj = None
            if zweitstimme:
                secondary_voice_obj = session.scalar(
                    select(PodcastStimme).where(PodcastStimme.name == zweitstimme)
                )
                if secondary_voice_obj is None:
                    logger.warning(f"Zweitstimme '{zweitstimme}' nicht gefunden. Nur Hauptstimme wird verwendet.")
        
        except Exception as e:
            logger.error(f"Fehler beim Laden der Stimmen aus der Datenbank: {e}")
            # Wenn die Stimmen fehlen, wird der Workflow sofort beendet
            raise RuntimeError(f"Fehler beim Abrufen der Stimmen: {e}")
        
        # ----------------------------------------------------------------------
        # 2) LLM-Service → Skript generieren
        # ----------------------------------------------------------------------
        
        config = {
            "language": sprache, "style": "neutral", "dauer": dauer, 
            "speakers": speakers, "roles": roles if roles is not None else {}
        }
        
        # Der LLMService fängt seinen eigenen Fehler ab und liefert ggf. Dummy-Text zurück.
        script = self.llm_service.generate_script(user_prompt, config)
        logger.info(f"Skript erfolgreich generiert (Auszug: {script[:50]}...)")
        
        # ----------------------------------------------------------------------
        # 3) Metadaten speichern (Commit #1 - Vor externem Service-Aufruf)
        # ----------------------------------------------------------------------
        
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

        
        # ----------------------------------------------------------------------
        # 4) TTS → Audio erstellen (mit Transaktionsschutz)
        # ----------------------------------------------------------------------
        
        try:
            audio_path = self.tts_service.generate_audio(
                script_text=script, primary_voice=primary_voice_obj, secondary_voice=secondary_voice_obj,
            )
            logger.info(f"Audio generiert und gespeichert unter: {audio_path}")
            
            # --- ERFOLGSFALL: DB-Update (Commit #2) ---
            
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
            
            return audio_path

        except Exception as e:
            # --- FEHLERFALL: Rollback und Status-Update (Commit #3) ---
            
            session.rollback() # Änderungen im Try-Block verwerfen
            
            konvertierungsauftrag.status = AuftragsStatus.FEHLGESCHLAGEN
            session.add(konvertierungsauftrag) 
            session.commit() # Speichert nur den Fehlerstatus
            
            logger.error(f"Pipeline-Fehler, Auftrag ID {konvertierungsauftrag.auftragId} auf FEHLGESCHLAGEN gesetzt: {e}")
            
            raise RuntimeError(f"Fehler im Podcast-Workflow aufgetreten: {e}")