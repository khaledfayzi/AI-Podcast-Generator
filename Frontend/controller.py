import os
import logging
from typing import Optional, Tuple, Dict, Any, List

from Interfaces.IServices import IWorkflow
from services.login_service import process_login_request, process_verify_login
from services.exceptions import AuthenticationError
from services.input_processing import build_source_text

logger = logging.getLogger(__name__)

# Use Interface for typing
_workflow: Optional[IWorkflow] = None

DURATION_MAP = {"Kurz (~5min)": 5, "Mittel (~15min)": 15, "Lang (~30min)": 30}


def get_workflow() -> IWorkflow:
    """
    Returns a singleton instance of the Workflow.
    Uses lazy loading to import the concrete implementation only when needed.
    """
    global _workflow
    if _workflow is None:
        from services.workflow import PodcastWorkflow
        from services.llm_service import LLMService
        from services.tts_service import GoogleTTSService
        
        # Dependency Injection (Modularity)
        llm = LLMService()
        tts = GoogleTTSService()
        _workflow = PodcastWorkflow(llm_service=llm, tts_service=tts)
    return _workflow


# --- Voice Management ---
def get_available_voices() -> Tuple[List[str], List[str]]:
    """Returns primary and secondary voice options."""
    workflow = get_workflow()
    return workflow.get_voices_for_ui()


# --- Script Generation ---
def generate_script(
    thema: str,
    dauer: str,
    sprache: str,
    speaker1: str,
    role1: str,
    speaker2: Optional[str],
    role2: Optional[str],
    source_text: str,
) -> str:
    """
    Generates a podcast script based on the given parameters.
    """
    workflow = get_workflow()

    # Normalize speaker2
    if not speaker2 or speaker2 == "Keine" or speaker2 == speaker1:
        speaker2 = None
        role2 = None

    speakers = 2 if speaker2 else 1

    # Build roles dict
    roles = {speaker1: role1}
    if speaker2 and role2 and role2 != "Keine":
        roles[speaker2] = role2

    duration_int = DURATION_MAP.get(dauer, 15)

    # Uses the public interface method
    return workflow.generate_script(
        thema=thema,
        sprache=sprache,
        dauer=duration_int,
        speakers=speakers,
        roles=roles,
        hauptstimme=speaker1,
        zweitstimme=speaker2,
        source_text=source_text,
    )


# --- Audio Generation ---
def generate_audio_only(
    script_text: str, sprache: str, speaker1: str, speaker2: Optional[str]
):
    """Wrapper to generate audio object"""
    workflow = get_workflow()
    if not speaker2 or speaker2 == "Keine" or speaker2 == speaker1:
        speaker2 = None

    # Calls the new 'obj' step
    return workflow.generate_audio_obj_step(script_text, sprache, speaker1, speaker2)


def save_generated_podcast(
    script_text,
    thema,
    dauer,
    sprache,
    speaker1,
    speaker2,
    audio_obj,
    user_id,
    role1,
    role2,
):
    """Wrapper to save file and metadata."""
    workflow = get_workflow()

    # save file if not cancelled
    audio_path = workflow.save_audio_file(audio_obj)

    # save metadata
    if not speaker2 or speaker2 == "Keine" or speaker2 == speaker1:
        speaker2 = None
        role2 = None

    duration_int = DURATION_MAP.get(dauer, 15)

    _, _, podcast = workflow.save_podcast_db(
        user_id=user_id,
        script=script_text,
        thema=thema,
        dauer=duration_int,
        sprache=sprache,
        hauptstimme=speaker1,
        zweitstimme=speaker2,
        audio_path=audio_path,
        role1=role1,
        role2=role2,
    )

    podcast_data = {
        "id": podcast.podcastId,
        "titel": podcast.titel,
        "dauer": podcast.realdauer,
        "datum": str(podcast.erstelldatum),
        "path": podcast.dateipfadAudio,
    }

    # Return the new path so the UI can play it
    return audio_path, podcast_data


def generate_audio(
    script_text: str,
    thema: str,
    dauer: str,
    sprache: str,
    speaker1: str,
    speaker2: Optional[str],
    user_id: int = 1,
    role1: Optional[str] = None,
    role2: Optional[str] = None,
) -> str:
    """
    Generates audio from a script.
    """
    workflow = get_workflow()

    # Normalize speaker2
    if not speaker2 or speaker2 == "Keine" or speaker2 == speaker1:
        speaker2 = None
        role2 = None

    duration_int = DURATION_MAP.get(dauer, 15)

    return workflow.generate_audio_step(
        script_text=script_text,
        thema=thema,
        dauer=duration_int,
        sprache=sprache,
        hauptstimme=speaker1,
        zweitstimme=speaker2,
        user_id=user_id,
        role1=role1,
        role2=role2,
    )


# --- Podcast Management ---
def get_podcasts_for_user(user_id: Optional[int]) -> List[Dict[str, Any]]:
    """Returns list of podcasts for a user."""
    workflow = get_workflow()
    return workflow.get_podcasts_data(user_id=user_id)


def delete_podcast(podcast_id: int, user_id: int) -> bool:
    """Deletes a podcast by ID."""
    workflow = get_workflow()
    return workflow.delete_podcast(podcast_id, user_id)


def get_absolute_audio_path(audio_path: Optional[str]) -> Optional[str]:
    """Converts relative audio path to absolute path."""
    if audio_path:
        return os.path.abspath(audio_path)
    return None


# --- Authentication ---
def validate_smail_email(email: str) -> bool:
    """Validates that email is a valid Smail address."""
    return "smail" in email.lower() if email else False


def request_login_code(email: str) -> Tuple[bool, str]:
    """
    Requests a login code for the given email.
    """
    if not validate_smail_email(email):
        return False, "Bitte eine gültige Smail-Adresse eingeben!"

    try:
        process_login_request(email)
        return (
            True,
            "Check deine Mails 👀 — dein Code ist da! Er gilt 15 Minuten. In 5 Minuten kannst du dir einen neuen schicken lassen.",
        )
    except AuthenticationError as e:
        return False, f"Fehler: {str(e)}"
    except Exception as e:
        logger.error(f"Login request error: {e}")
        return False, f"Fehler: {str(e)}"


def verify_login_code(email: str, code: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Verifies a login code.
    """
    try:
        user_data = process_verify_login(email, code)
        return True, user_data, f"Erfolgreich eingeloggt als {user_data['email']}!"
    except AuthenticationError as e:
        return False, None, f"Login fehlgeschlagen: {str(e)}"
    except Exception as e:
        logger.error(f"Login verification error: {e}")
        return False, None, f"Fehler: {str(e)}"


def get_user_display_name(user_data: Optional[Dict]) -> str:
    """Extracts display name from user data."""
    if user_data and "email" in user_data:
        return user_data["email"].split("@")[0]
    return ""


def process_source_input(
    file_path: Optional[str], url: Optional[str]
) -> Tuple[str, str]:
    """Processes file upload and URL to extract source text and title."""
    return build_source_text(file_path, url)