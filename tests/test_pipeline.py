import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["GEMINI_API_KEY"] = "DUMMY_KEY"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/dummy/path.json"

from services.workflow import PodcastWorkflow
from services.llm_service import LLMService

class TestPodcastWorkflowCI(unittest.TestCase):
    @patch("services.workflow.get_db")
    @patch("services.workflow.LLMService")
    @patch("services.workflow.GoogleTTSService")
    @patch("services.workflow.VoiceRepo")
    @patch("services.workflow.TextRepo")
    @patch("services.workflow.JobRepo")
    @patch("services.workflow.PodcastRepo")
    @patch("uuid.uuid4")
    def test_workflow_run_pipeline_success(
        self, MockUUID, MockPodcastRepo, MockJobRepo, MockTextRepo, MockVoiceRepo, 
        MockTTSService, MockLLMService, MockGetDB
    ):
        mock_session = MagicMock()
        MockGetDB.return_value = mock_session
        MockUUID.return_value = "1234-5678"
        
        mock_text_repo = MockTextRepo.return_value
        mock_text_repo.add.side_effect = lambda x: x 
        
        mock_job_repo = MockJobRepo.return_value
        mock_job_repo.add.side_effect = lambda x: x
        
        mock_podcast_repo = MockPodcastRepo.return_value
        mock_podcast_repo.add.side_effect = lambda x: x
        
        mock_voice_repo = MockVoiceRepo.return_value
        mock_voice_obj = MagicMock()
        mock_voice_obj.stimmeId = 1
        mock_voice_obj.name = "Max"
        mock_voice_obj.ttsVoice = "de-DE-Wavenet-A"
        mock_voice_repo.get_voices_by_names.return_value = [mock_voice_obj]

        mock_llm = MockLLMService.return_value
        mock_llm.generate_script.return_value = "Dies ist ein generiertes Skript."

        mock_tts = MockTTSService.return_value
        mock_audio_obj = MagicMock()
        mock_audio_obj.export.return_value = None
        mock_tts.generate_audio.return_value = mock_audio_obj
        
        workflow = PodcastWorkflow()
        workflow.llm_service = mock_llm 
        workflow.tts_service = mock_tts

        result_path = workflow.run_pipeline(
            user_id=1,
            llm_id=1,
            tts_id=1,
            thema="Test Thema",
            dauer=5,
            sprache="Deutsch",
            hauptstimme="Max",
            zweitstimme="Sara"
        )

        mock_llm.generate_script.assert_called_once()
        mock_tts.generate_audio.assert_called_once()
        mock_text_repo.add.assert_called_once()
        
        self.assertEqual(result_path, "Output/podcast_google_1234-5678.mp3")

if __name__ == "__main__":
    unittest.main()
