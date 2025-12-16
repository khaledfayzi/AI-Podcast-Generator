# poc_run.py - Startdatei für den API-Workflow (Proof of Concept)

import logging
from services.workflow import Workflow
from dotenv import load_dotenv

# --- KONFIGURATION UND LOGGING ---
load_dotenv()
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("POC_RUN")

def main_poc():
    """
    Startet den Workflow zur Generierung eines Podcasts unter Verwendung
    der echten Gemini- und Google TTS-APIs.
    """
    logger.info("Starte ECHTEN POC des API-Workflows (LLM → TTS)...")

    # DB-Parameter (user_id, llm_id, tts_id) werden NICHT übergeben, 
    # da sie in services/workflow.py entfernt wurden.
    
    workflow = Workflow()
    
    try:
        # Hier werden nur die für die Generierung notwendigen Argumente übergeben.
        audio_path = workflow.run_pipeline(
            # Erforderlich für die Skriptgenerierung
            user_prompt="Erkläre kurz in einfachen Worten, wie künstliche neuronale Netze funktionieren und wofür sie heutzutage verwendet werden.",
            
            # Konfigurationsparameter
            thema="Neuronale Netze kurz erklärt",
            dauer=1,
            sprache="de",
            hauptstimme="Max", # Wird als Dummy-Objekt an TTS übergeben
            zweitstimme="Sara", # Wird als Dummy-Objekt an TTS übergeben
            speakers=2
        )
        
        # Der Audio-Pfad wird von der _generate_audio Methode zurückgegeben und 
        # vom Workflow am Ende protokolliert.
        logger.info(f"🎉 POC erfolgreich abgeschlossen! Die Podcast-Datei liegt unter: {audio_path}")
        
    except Exception as e:
        logger.error(f"❌ Der POC ist fehlgeschlagen: {e}", exc_info=True)

if __name__ == "__main__":
    main_poc()