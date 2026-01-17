import pytest
from requests.exceptions import RequestException

from services.exceptions import LLMServiceError
from services.llm_service import LLMService

BASE_CONFIG={

    "dauer":2,
    "language":"Deutsch",
    "style":"neutral",
    "hauptstimme":"Max",
    "zweitstimme":None,
    "roles":{}

}   


#Tests
def test_dummy_mode_returns_dummy_text():
    """Dummy-Modus muss immer einen Fallback-Text liefern."""

    service = LLMService(use_dummy=True)
    result = service.generate_script("KI", BASE_CONFIG)
    assert "Dummy" in result


def test_system_prompt_contains_main_speaker():
    """Der Hauptsprecher muss immer im System-Prompt stehen."""

    service = LLMService(use_dummy=True)
    prompt = service._system_prompt(BASE_CONFIG)
    assert "Max" in prompt


def test_system_prompt_without_second_speaker():
    """Wenn keine Zweitstimme gesetzt ist, darf kein zweiter Sprecher erscheinen."""

    service = LLMService(use_dummy=True)
    prompt = service._system_prompt(BASE_CONFIG)
    assert "Lukas" not in prompt   



def test_system_prompt_without_second_speaker_is_not_listed():
    """
    Professioneller als 'und' / zufällige Wörter:
    Wir prüfen das konkrete Sprecherformat.
    """
    service = LLMService(use_dummy=True)
    prompt = service._system_prompt(BASE_CONFIG)

    # Erwartung: Es gibt keinen zweiten Sprecher nach "und"
    assert "Erlaubte Sprecher sind: Max und" not in prompt


def test_system_prompt_english_language():
    """Wenn Englisch gewählt ist, muss die englische Regel erscheinen."""

    service = LLMService(use_dummy=True)
    config = BASE_CONFIG | {"language": "English"}
    prompt = service._system_prompt(config)
    assert "Write exclusively in English" in prompt



def test_roles_instruction_two_speakers():
    """Rollen müssen korrekt in die Rollen-Instruktion eingebaut werden."""

    service = LLMService(use_dummy=True)
    config = BASE_CONFIG | {
        "zweitstimme": "Sarah",
        "roles": {"Max": "Moderator", "Sarah": "Experte"},
    }
    roles = service._roles_instruction(config)
    assert "Moderator" in roles
    assert "Experte" in roles
    assert "Sarah" in roles


def test_user_prompt_without_source_contains_topic():
    """Ohne Quelle muss der User-Prompt das Thema enthalten."""

    service = LLMService(use_dummy=True)
    prompt = service._user_prompt("Test", BASE_CONFIG)
    assert "Thema: Test" in prompt


def test_user_prompt_with_source_contains_source_block():
    """Mit Quelle muss der QUELLE-Block erscheinen."""

    service = LLMService(use_dummy=True)
    config = BASE_CONFIG | {"source_text": "Hallo Welt"}
    prompt = service._user_prompt("Thema", config)
    assert "QUELLE:" in prompt
    assert "Hallo Welt" in prompt


def test_invalid_api_key_raises_error(monkeypatch):
    """Ohne API-Key darf der Service im Real-Mudos nicht starten. """

    monkeypatch.delenv("GEMINI_API_KEY",raising=False)
    with pytest.raises(LLMServiceError):
        LLMService(use_dummy=False)
    

def test_gemini_error_fallback(monkeypatch):

    """"Bei API-Fehlern muss auf Dummy-Fallback zurückgefallen werden. """

    service=LLMService(use_dummy=False)
    def fake_post(*args, **kwargs):
        raise RequestException("Netzwerk down")
    
    monkeypatch.setattr("services.llm_service.requests.post",fake_post)

    text=service.generate_script("KI",BASE_CONFIG)
    assert "Dummy"in text

