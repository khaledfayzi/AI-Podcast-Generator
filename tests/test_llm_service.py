import pytest
from requests.exceptions import RequestException

from services.exceptions import LLMServiceError
from services.llm_service import LLMService

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Setzt standardmäßig einen Dummy-API-Key, damit Tests nicht crashen."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")

BASE_CONFIG = {
    "dauer": 2,
    "language": "Deutsch",
    "style": "neutral",
    "hauptstimme": "Max",
    "zweitstimme": None,
    "roles": {},
}


# Tests
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


def test_user_prompt_invalid_duration():
    service = LLMService(use_dummy=True)

    config = BASE_CONFIG | {"dauer": "abc"}
    prompt = service._user_prompt("Thema", config)

    assert "Ziel-Länge" in prompt


def test_user_prompt_invalid_max_chars():
    service = LLMService(use_dummy=True)

    config = BASE_CONFIG | {"source_text": "abcdefghij", "source_max_chars": "abc"}

    prompt = service._user_prompt("Thema", config)

    assert "abcdefghij" in prompt


def test_user_prompt_negative_duration():
    service = LLMService(use_dummy=True)

    config = BASE_CONFIG | {"dauer": -5}
    prompt = service._user_prompt("Thema", config)

    assert "Ziel-Länge" in prompt


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
    """Ohne API-Key darf der Service im Real-Modus nicht starten."""

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMServiceError):
        LLMService(use_dummy=False)


def test_gemini_error_fallback(monkeypatch):
    """ "Bei API-Fehlern muss auf Dummy-Fallback zurückgefallen werden."""

    service = LLMService(use_dummy=False)

    def fake_post(*args, **kwargs):
        raise RequestException("Netzwerk down")

    monkeypatch.setattr("services.llm_service.requests.post", fake_post)

    text = service.generate_script("KI", BASE_CONFIG)
    assert "Dummy" in text


def test_ask_gemini_success(monkeypatch):
    service = LLMService(use_dummy=False)

    fake_response = type("R", (), {})()
    fake_response.status_code = 200
    fake_response.text = "ok"

    def fake_json():
        return {"candidates": [{"content": {"parts": [{"text": "Hallo von Gemini"}]}}]}

    fake_response.json = fake_json

    monkeypatch.setattr(
        "services.llm_service.requests.post", lambda *a, **k: fake_response
    )

    result = service._ask_gemini("test prompt")
    assert result == "Hallo von Gemini"


def test_retry_on_429(monkeypatch):
    service = LLMService(use_dummy=False)

    responses = []

    def fake_post(*args, **kwargs):
        r = type("R", (), {})()
        if not responses:
            r.status_code = 429
            r.text = "rate limit"
        else:
            r.status_code = 200
            r.text = "ok"
            r.json = lambda: {
                "candidates": [{"content": {"parts": [{"text": "Erfolg nach Retry"}]}}]
            }
        responses.append(r)
        return r

    monkeypatch.setattr("services.llm_service.requests.post", fake_post)

    result = service._ask_gemini("test")
    assert result == "Erfolg nach Retry"


def test_invalid_json_response(monkeypatch):
    service = LLMService(use_dummy=False)

    fake_response = type("R", (), {})()
    fake_response.status_code = 200
    fake_response.text = "not json"

    def bad_json():
        raise ValueError("invalid json")

    fake_response.json = bad_json

    monkeypatch.setattr(
        "services.llm_service.requests.post", lambda *a, **k: fake_response
    )

    with pytest.raises(LLMServiceError):
        service._ask_gemini("test")


def test_unexpected_response_format(monkeypatch):
    service = LLMService(use_dummy=False)

    fake_response = type("R", (), {})()
    fake_response.status_code = 200
    fake_response.text = "ok"
    fake_response.json = lambda: {"irgendwas": "falsch"}

    monkeypatch.setattr(
        "services.llm_service.requests.post", lambda *a, **k: fake_response
    )

    with pytest.raises(LLMServiceError):
        service._ask_gemini("test")


from requests.exceptions import Timeout


def test_timeout_is_handled(monkeypatch):
    service = LLMService(use_dummy=False)

    def fake_post(*args, **kwargs):
        raise Timeout("timeout!")

    monkeypatch.setattr("services.llm_service.requests.post", fake_post)

    with pytest.raises(LLMServiceError):
        service._ask_gemini("test")
