import pytest
from unittest.mock import MagicMock, patch

import services.workflow as workflow_module
from services.exceptions import TTSServiceError
from database.models import PodcastStimme


# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------


@pytest.fixture
def mock_session():
    """
    Simulierte Datenbank-Session.
    Ersetzt eine echte SQLAlchemy-Session und erlaubt Assertions
    auf close() und commit().
    """
    session = MagicMock()
    session.close = MagicMock()
    session.commit = MagicMock()
    return session


@pytest.fixture(autouse=True)
def _mock_db_for_all_tests(mock_session):
    """
    Autouse-Fixture:
    Patcht get_db() für ALLE Tests automatisch.
    Dadurch wird garantiert, dass niemals eine echte DB-
    oder SSH-Verbindung aufgebaut wird.
    """
    with patch.object(workflow_module, "get_db", return_value=mock_session):
        yield


@pytest.fixture
def voice_max():
    """
    Mock für die Hauptstimme aus der Datenbank.
    """
    v = PodcastStimme(
        name="Max",
        ttsVoice_de="de-DE-Voice-Max",
        ttsVoice_en="en-US-Voice-Max",
    )
    v.stimmeId = 1
    return v


@pytest.fixture
def voice_sarah():
    """
    Mock für die Zweitstimme aus der Datenbank.
    """
    v = PodcastStimme(
        name="Sarah",
        ttsVoice_de="de-DE-Voice-Sarah",
        ttsVoice_en="en-US-Voice-Sarah",
    )
    v.stimmeId = 2
    return v


@pytest.fixture
def workflow():
    """
    Initialisiert den Workflow isoliert:
    - keine echte DB
    - kein echtes LLM (kein GEMINI_API_KEY nötig)
    - kein echtes TTS
    """
    mock_llm = MagicMock()
    mock_tts = MagicMock()
    return workflow_module.PodcastWorkflow(llm_service=mock_llm, tts_service=mock_tts)


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------


def test_skripterstellung_ein_sprecher(workflow):
    """
    Prüft die Skripterstellung mit nur einem Sprecher.
    """
    with patch.object(workflow, "generate_script", return_value="Max: Hallo.") as m:
        text = workflow.generate_script_step("Test", 2, "Deutsch", "Max", "Keine")

    assert "Max:" in text

    _, kwargs = m.call_args
    assert kwargs["speakers"] == 1
    assert kwargs["zweitstimme"] is None


def test_skripterstellung_zwei_sprecher(workflow):
    """
    Prüft, ob bei zwei Sprechern speakers korrekt auf 2 gesetzt wird.
    """
    with patch.object(
        workflow, "generate_script", return_value="Max: Hi\nSarah: Hallo."
    ) as m:
        workflow.generate_script_step("Test", 2, "Deutsch", "Max", "Sarah")

    _, kwargs = m.call_args
    assert kwargs["speakers"] == 2
    assert kwargs["zweitstimme"] == "Sarah"


def test_audiogenerierung_erfolgreich(workflow, mock_session, voice_max, voice_sarah):
    """
    Erfolgsfall der Audiogenerierung.
    """
    voice_repo = MagicMock()
    voice_repo.get_voices_by_names.side_effect = [[voice_max], [voice_sarah]]

    with (
        patch.object(workflow_module, "VoiceRepo", return_value=voice_repo),
        patch.object(workflow, "_generate_audio", return_value="Output/test.mp3"),
        patch.object(workflow, "_save_metadata"),
    ):
        path = workflow.generate_audio_step(
            "Max: Hallo\nSarah: Hi", "Thema", 2, "Deutsch", "Max", "Sarah"
        )

    assert path == "Output/test.mp3"
    mock_session.close.assert_called_once()


def test_audiogenerierung_tts_fehler(workflow, mock_session, voice_max):
    """
    Prüft, ob ein Fehler aus dem TTS-Service korrekt weitergereicht wird.
    """
    voice_repo = MagicMock()
    voice_repo.get_voices_by_names.return_value = [voice_max]

    with (
        patch.object(workflow_module, "VoiceRepo", return_value=voice_repo),
        patch.object(workflow, "_generate_audio", side_effect=TTSServiceError("fail")),
    ):
        with pytest.raises(TTSServiceError):
            workflow.generate_audio_step(
                "Max: Hallo", "Thema", 1, "Deutsch", "Max", "Keine"
            )

    mock_session.close.assert_called_once()


def test_podcast_loeschen_erfolgreich(workflow, mock_session):
    """
    Testet das Löschen eines Podcasts, wenn er dem Benutzer gehört.
    """
    podcast_repo = MagicMock()
    p = MagicMock()
    p.podcastId = 1
    podcast_repo.get_by_user_id.return_value = [p]

    with patch.object(workflow_module, "PodcastRepo", return_value=podcast_repo):
        ok = workflow.delete_podcast(podcast_id=1, user_id=1)

    assert ok is True
    podcast_repo.delete_by_id.assert_called_once_with(1)
    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()


def test_podcast_xml_zeichen_loeschen_erfolgreich(workflow):
    """
    Testet, ob XML-Zeichen entfernt werden und Markdown erhalten bleibt.
    """
    workflow.llm_service.generate_script.return_value = (
        "Max: Hallo <break/> **etwas** [pause: 1s]"
    )

    out = workflow.generate_script(
        thema="Podcast",
        sprache="Deutsch",
        dauer=5,
        speakers=1,
        roles=None,
        hauptstimme="Max",
        zweitstimme=None,
        source_text=None,
    )

    assert "<break/>" not in out
    assert "**etwas**" in out
    assert "[pause: 1s]" in out


def test_generate_audio_passing_roles_and_stimmen_objekte(
    workflow, mock_session, voice_max, voice_sarah
):
    """
    Prüft, ob Rollen und Voice-Objekte korrekt an _save_metadata übergeben werden.
    """
    voice_repo = MagicMock()
    voice_repo.get_voices_by_names.side_effect = [[voice_max], [voice_sarah]]

    with (
        patch.object(workflow_module, "VoiceRepo", return_value=voice_repo),
        patch.object(workflow, "_generate_audio", return_value="Output/test.mp3"),
        patch.object(workflow, "_save_metadata") as save_meta,
    ):
        out_path = workflow.generate_audio_step(
            script_text="Max: Hallo\nSarah: Hi",
            thema="Thema",
            dauer=2,
            sprache="Deutsch",
            hauptstimme="Max",
            zweitstimme="Sarah",
            user_id=7,
            role1="Moderator",
            role2="Co-Host",
        )

    assert out_path == "Output/test.mp3"

    args, _ = save_meta.call_args
    assert args[0] == mock_session
    assert args[1] == 7
    assert args[9] == voice_max
    assert args[10] == voice_sarah
    assert args[11] == "Output/test.mp3"
    assert args[12] == "Moderator"
    assert args[13] == "Co-Host"

    mock_session.close.assert_called_once()
