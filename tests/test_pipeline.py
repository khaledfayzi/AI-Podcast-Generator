import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Fixture to mock environment variables for all tests in this file
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "DUMMY_KEY")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/dummy/path.json")

# Import after env setup (though safe with imports usually, better to be clean)
from services.workflow import PodcastWorkflow
from services.llm_service import LLMService

@patch("services.workflow.get_db")
@patch("services.workflow.LLMService")
@patch("services.workflow.GoogleTTSService")
@patch("services.workflow.VoiceRepo")
@patch("services.workflow.TextRepo")
@patch("services.workflow.JobRepo")
@patch("services.workflow.PodcastRepo")
@patch("uuid.uuid4")
def test_workflow_run_pipeline_success(
    MockUUID,
    MockPodcastRepo,
    MockJobRepo,
    MockTextRepo,
    MockVoiceRepo,
    MockTTSService,
    MockLLMService,
    MockGetDB,
):
    # Setup Mocks
    mock_session = MagicMock()
    MockGetDB.return_value = mock_session
    MockUUID.return_value = "1234"

    # Repos with fluent add() returns
    MockTextRepo.return_value.add.side_effect = lambda x: x
    MockJobRepo.return_value.add.side_effect = lambda x: x
    MockPodcastRepo.return_value.add.side_effect = lambda x: x

    # Voice Repo
    mock_voice_obj = MagicMock()
    mock_voice_obj.stimmeId = 1
    mock_voice_obj.name = "Max"
    mock_voice_obj.ttsVoice = "de-DE-Wavenet-A"
    MockVoiceRepo.return_value.get_voices_by_names.return_value = [mock_voice_obj]

    # Services
    mock_llm = MockLLMService.return_value
    mock_llm.generate_script.return_value = "Dies ist ein generiertes Skript."

    mock_tts = MockTTSService.return_value
    mock_audio_obj = MagicMock()
    mock_audio_obj.export.return_value = None
    mock_tts.generate_audio.return_value = mock_audio_obj

    # Execution
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
        zweitstimme="Sara",
    )

    # Assertions
    mock_llm.generate_script.assert_called_once()
    mock_tts.generate_audio.assert_called_once()
    MockTextRepo.return_value.add.assert_called_once()
    
    # Native assert instead of self.assertEqual
    assert result_path == "Output/podcast_google_1234.mp3"
