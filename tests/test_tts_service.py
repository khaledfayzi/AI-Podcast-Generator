import pytest
from unittest.mock import MagicMock, patch
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from services.tts_service import GoogleTTSService
from database.models import PodcastStimme


@pytest.fixture
def tts_service():
    """
    Initialisiert den GoogleTTSService mit verbesserten Mocks.
    """
    with patch("services.tts_service.texttospeech.TextToSpeechClient") as MockClient:
        with patch("services.tts_service.nltk.sent_tokenize") as mock_tokenize:
            # Der Mock trennt nun den Text an ". " auf, um echte Sätze zu simulieren
            # Das ermöglicht den Test von smart_chunking ohne echte NLTK-Daten
            mock_tokenize.side_effect = lambda text, language: [
                s.strip() + "." for s in text.split(".") if s.strip()
            ]

            service = GoogleTTSService()
            service.client = MockClient.return_value
            yield service


@pytest.fixture
def voice_max():
    """
    Erstellt ein Mock-Objekt für einen männlichen Sprecher.
    """
    return PodcastStimme(
        stimmeId=1,
        name="Max",
        geschlecht="m",
        tts_voice_de="de-DE-Chirp3-HD-Achird",
        tts_voice_en="en-US-Chirp3-HD-Achird",
        ui_slot=1
    )


@pytest.fixture
def voice_sara():
    """
    Erstellt ein Mock-Objekt für eine weibliche Sprecherin.
    """
    return PodcastStimme(
        stimmeId=2,
        name="Sarah",
        geschlecht="w",
        tts_voice_de="de-DE-Chirp3-HD-Erinome",
        tts_voice_en="en-US-Chirp3-HD-Erinome",
        ui_slot=2
    )


def test_validierung_ssml_Transformation(tts_service):
    """
    Prüft die korrekte Umwandlung von Markdown und Custom-Shortcodes in SSML.

    Validiert, ob die interne Methode `_prepare_final_ssml` Markdown-Styles
    in <emphasis>-Tags und Shortcodes wie [pause] oder [spell] in die
    entsprechenden Google SSML-Elemente übersetzt.
    """
    input_text = "Hallo **Welt**, das ist *ein Test*. [pause: 500ms] [spell: ABC] [year: 2024] [dur: 2m]."
    expected_parts = [
        "<speak>",
        '<emphasis level="strong">Welt</emphasis>',
        '<emphasis level="moderate">ein Test</emphasis>',
        '<break time="500ms"/>',
        '<say-as interpret-as="characters">ABC</say-as>',
        '<say-as interpret-as="date" format="y">2024</say-as>',
        '<say-as interpret-as="duration">2m</say-as>',
        "</speak>",
    ]

    ssml = tts_service._prepare_final_ssml(input_text, nltk_lang="german")

    for part in expected_parts:
        assert part in ssml


def test_sprecherwechsel(tts_service, voice_max, voice_sara):
    """
    Verifiziert die korrekte Stimmenzuordnung bei einem Dialog-Skript.

    Stellt sicher, dass der Service bei einem Skript mit mehreren Sprechern
    für jeden Abschnitt die korrekte VoiceSelectionParams an die Google API übergibt
    und die Segmente in der richtigen Reihenfolge verarbeitet.
    """
    script = """
    Max: Hallo Sarah.
    Sarah: Hallo Max, wie geht es?
    Max: Mir geht es gut.
    """

    tts_service.client.synthesize_speech.return_value.audio_content = (
        b"RIFF_DUMMY_AUDIO"
    )

    tts_service.generate_audio(script, "Deutsch", voice_max, voice_sara)

    calls = tts_service.client.synthesize_speech.call_args_list
    assert len(calls) >= 3
    assert calls[0].kwargs["voice"].name == "de-DE-Chirp3-HD-Achird"
    assert calls[1].kwargs["voice"].name == "de-DE-Chirp3-HD-Erinome"
    assert calls[2].kwargs["voice"].name == "de-DE-Chirp3-HD-Achird"


def test_smart_chunking(tts_service):
    """
    Testet das Aufteilen von überlangen Texten in kleinere Abschnitte.

    Überprüft, ob der `_text_splitter` Texte, die das Zeichenlimit überschreiten,
    intelligent an Satzenden (mittels NLTK) trennt, statt Wörter hart abzuschneiden.
    """
    sentence = "Dies ist ein sehr langer Satz, der wiederholt wird. "
    long_text = sentence * 100

    chunks = tts_service._text_splitter(long_text, max_chars=200, nltk_lang="german")

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200
        assert chunk.endswith(".")


def test_retry_logic(tts_service, voice_max):
    """
    Überprüft die Widerstandsfähigkeit des Service bei API-Fehlern.

    Simuliert aufeinanderfolgende Quota-Überschreitungen und Serverfehler.
    Der Test ist erfolgreich, wenn der Service die konfigurierten Retries
    durchläuft und beim dritten Versuch (nach Simulation eines Erfolgs)
    das Ergebnis liefert.
    """
    script = "Ein kurzer Test."

    tts_service.client.synthesize_speech.side_effect = [
        ResourceExhausted("Quota exceeded"),
        ServiceUnavailable("Service down"),
        MagicMock(audio_content=b"RIFF_DUMMY_AUDIO"),
    ]

    with patch("time.sleep"):
        tts_service.generate_audio(script, "Deutsch", voice_max)

    assert tts_service.client.synthesize_speech.call_count == 3


def test_audio_generation_success(tts_service, voice_max):
    """
    Validiert den erfolgreichen Standard-Workflow der Audiogenerierung.

    Prüft, ob bei validem Input und funktionierender API ein nicht-leerer
    Byte-Stream als Audio-Ergebnis zurückgegeben wird.
    """
    script = "Das ist ein Test."
    tts_service.client.synthesize_speech.return_value.audio_content = (
        b"RIFF_DUMMY_AUDIO"
    )

    audio = tts_service.generate_audio(script, "Deutsch", voice_max)

    assert audio is not None
    assert len(audio) > 0
