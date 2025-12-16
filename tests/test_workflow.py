# main_test_run.py (ACHTUNG: Führt ECHTE API-Aufrufe aus!)

import logging
from unittest.mock import MagicMock, patch
from services.workflow import PodcastWorkflow
import os
from dotenv import load_dotenv

# --- KONFIGURATION ---
load_dotenv()
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MAIN")

# -----------------------------
# START DES WORKFLOWS MIT MINIMALEM PATCHING
# -----------------------------

def main_full_api_test():
    
    # Patch get_db() und VoiceRepo, um Datenbankfehler zu vermeiden
    with patch("services.workflow.get_db") as MockGetDB, \
         patch("services.tts_service.get_db") as MockTTSGetDB, \
         patch("services.tts_service.VoiceRepo") as MockTTSVoiceRepo:
        
        # Mocking der DB-Session und des Repositories, da sie nicht benötigt werden
        MockGetDB.return_value = MagicMock()
        MockTTSGetDB.return_value = MagicMock()
        MockTTSVoiceRepo.return_value.get_voices_by_names.return_value = [] # Wir nutzen Hardcoding im Workflow

        logger.info("Starte ECHTEN API-Workflow (LLM + TTS)...")
        
        try:
            workflow = PodcastWorkflow()
            
            # Echte Parameter für den Lauf
            audio_path = workflow.run_pipeline(
                user_prompt="Erkläre kurz, wie generative KI-Modelle funktionieren und nenne ein Beispiel.",
                #user_id=1,
                #llm_id=1,
                #tts_id=1,
                thema="Generative KI und ihre Anwendungen",
                dauer=1,
                sprache="de",
                hauptstimme="Max", # Muss mit dem Namen in _load_voices übereinstimmen
                zweitstimme="Sara" 
            )

            logger.info(f"✅ Workflow erfolgreich. Audio generiert und gespeichert als: {audio_path}")

        except Exception as e:
            logger.error(f"❌ Der Haupt-Workflow ist fehlgeschlagen: {e}", exc_info=True)


if __name__ == "__main__":
    main_full_api_test()