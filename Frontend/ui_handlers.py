import gradio as gr
import sys
import os
import shutil
import re
from datetime import datetime

# Fix imports to ensure team04 module is found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from .controller import (
    generate_script,
    get_podcasts_for_user,
    delete_podcast,
    get_absolute_audio_path,
    request_login_code,
    verify_login_code,
    get_user_display_name,
    process_source_input,
    generate_audio_only,
    save_generated_podcast,
)

# Page names must match the order of pages in ui.py
PAGE_NAMES = [
    "home",
    "skript bearbeiten",
    "audio player",
    "loading script",
    "loading podcast",
    "login_page",
    "uber_page",
    "nutzungs_page",
    "share_page",
]

# --- Helper Functions ---

def _get_roles(speaker: int) -> list:
    """Hilfsmethode um die verfügbaren Rollen im Dropdown anzeigen"""
    if speaker == 1:
        return [
            "Moderator",
            "Erzähler",
            "Fragensteller (Interviewer)",
        ]

    if speaker == 2:
        return ["Co-Host", "Experte", "Interviewpartner"]
    return []


def _get_matching_role(speaker2, role1) -> str:
    """Bestimmt die Rolle des zweiten Sprechers basierend auf der Rolle des ersten."""
    if not speaker2 or speaker2 == "Keine":
        return "Keine"

    if role1 == "Moderator":
        return "Co-Host"
    elif role1 == "Erzähler":
        return "Experte"
    elif role1 == "Fragensteller (Interviewer)":
        return "Interviewpartner"

    return "Co-Host"  # Fallback


def format_podcast_date(date_string: str) -> str:
    """Formats a podcast date string from YYYY-MM-DD to DD.MM.YYYY."""
    try:
        date_obj = datetime.strptime(date_string, "%Y-%m-%d")
        return date_obj.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return date_string


def get_loader_html(message):
    """Spinner-HTML für die Ladezeit."""
    return f"""
    <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; min-height: 300px;">
        <div class="loader"></div>
        <h2 style="margin-top: 20px; font-family: sans-serif; color: #444;">{message}</h2>
    </div>
    <style>
    .loader {{
        border: 10px solid #f3f3f3;
        border-top: 10px solid #3498db;
        border-radius: 50%;
        width: 80px;
        height: 80px;
        animation: spin 1s linear infinite;
    }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
    """

# --- Navigation Helper ---
def navigate(target):
    """Schaltet die Sichtbarkeit der Seiten um."""
    results = []
    for page in PAGE_NAMES:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))
    return tuple(results)


# --- Event Handlers ---

def on_play_click(audio_path, podcast_title):
    """Startet den Audio-Player mit dem richtigen File."""
    nav_updates = navigate("audio player")
    full_path = get_absolute_audio_path(audio_path)
    title_md = f"<div style='text-align: center; margin-bottom: 20px;'><h2>🎙️ {podcast_title}</h2></div>"
    return nav_updates + (
        gr.update(value=full_path, autoplay=True),
        gr.update(value=title_md),
    )


def generate_script_wrapper(
    thema,
    dauer,
    sprache,
    speaker1,
    role1,
    speaker2,
    role2,
    source_text,
    source_url,
    file_upload,
):
    """
    Generates a podcast script from validated input.
    """
    has_thema = thema and thema.strip()
    has_source_url = source_url and source_url.strip()
    has_file = file_upload is not None

    if not (has_thema or has_source_url or has_file):
        return ("",) + navigate("home") + (gr.update(),)

    has_url = source_url and source_url.strip()
    has_file = file_upload is not None

    thema_update = gr.update()

    if has_url or has_file:
        try:
            gr.Info("Quelle wird automatisch verarbeitet...")
            source_text, source_title = process_source_input(file_upload, source_url)

            if (not thema or not thema.strip()) and source_title:
                thema = source_title
                thema_update = gr.update(value=thema)

        except Exception as e:
            gr.Warning(f"Fehler beim Verarbeiten der Quelle: {str(e)}")
            has_thema = thema and thema.strip()
            if not has_thema:
                return ("",) + navigate("home") + (gr.update(),)

    try:
        script_text = generate_script(
            thema=thema,
            dauer=dauer,
            sprache=sprache,
            speaker1=speaker1,
            role1=role1,
            speaker2=speaker2,
            role2=role2,
            source_text=source_text,
        )
        return (script_text,) + navigate("skript bearbeiten") + (thema_update,)
    except Exception as e:
        gr.Warning(f"Fehler bei der Skript-Generierung: {str(e)}")
        return ("",) + navigate("home") + (gr.update(),)


def validate_and_show_loading(thema, source_url, file_upload):
    """Validates input before showing loading page. Returns navigation updates or warning."""
    has_thema = thema and thema.strip()
    has_url = source_url and source_url.strip()
    has_file = file_upload is not None

    if not (has_thema or has_url or has_file):
        gr.Warning(
            "Bitte gib mindestens ein Thema an, lade eine Datei hoch oder füge eine URL ein!"
        )
        return navigate("home")

    return navigate("loading script")


def run_audio_gen(script_text, thema, dauer, sprache, s1, s2, r1, r2, user_data):
    """Podcast aus dem Skript bauen, Player starten und Liste aktualisieren."""
    user_id = user_data["id"] if user_data else 1

    # GENERATE IN MEMORY
    try:
        audio_obj = generate_audio_only(
            script_text=script_text, sprache=sprache, speaker1=s1, speaker2=s2
        )
    except Exception as e:
        gr.Error(f"Fehler bei Generierung des Podcasts! {str(e)}")
        yield tuple([gr.update() for _ in range(16)])
        return

    # YIELD CONTROL
    yield tuple([gr.update() for _ in range(16)])

    # save to disk & db
    try:
        audio_path, podcast_data = save_generated_podcast(
            script_text=script_text,
            thema=thema,
            dauer=dauer,
            sprache=sprache,
            speaker1=s1,
            speaker2=s2,
            audio_obj=audio_obj,
            user_id=user_id,
            role1=r1,
            role2=r2,
        )
    except Exception as e:
        gr.Error(f"Fehler beim Speichern! {str(e)}")
        yield tuple([gr.update() for _ in range(16)])
        return

    # Create user download file
    try:
        safe_thema = re.sub(r'[\\/*?:"<>|]', "", thema).replace(" ", "_")
        date_str = datetime.now().strftime("%Y-%m-%d")
        download_filename = f"Podcast-{safe_thema}-{date_str}.mp3"
        
        abs_audio_path = get_absolute_audio_path(audio_path)
        output_dir = os.path.dirname(abs_audio_path)
        download_path = os.path.join(output_dir, download_filename)
        
        shutil.copy2(abs_audio_path, download_path)
    except Exception as e:
        print(f"Error creating download file: {e}")
        download_path = get_absolute_audio_path(audio_path)

    # refresh and navigate
    updated_data = get_podcasts_for_user(user_id=user_id)
    nav_updates = navigate("audio player")
    full_path = get_absolute_audio_path(audio_path)
    title_md = f"<div style='text-align: center; margin-bottom: 20px;'><h2>🎙️ {thema}</h2></div>"

    yield nav_updates + (
        gr.update(value=full_path, autoplay=True),
        updated_data,
        gr.update(value=title_md),
        podcast_data,  # current_podcast_state
        gr.update(value=download_path, visible=True),  # btn_download_finish
        gr.update(visible=True),  # btn_share_finish
        gr.update(visible=True),  # btn_delete_finish
    )


def delete_podcast_handler(podcast_id: int, user_data):
    """Handles podcast deletion and returns updated list."""
    if not user_data:
        return get_podcasts_for_user(user_id=None)

    user_id = user_data["id"]
    delete_podcast(podcast_id, user_id)
    return get_podcasts_for_user(user_id=user_id)


def handle_login_request(email):
    """Handles login code request."""
    success, message = request_login_code(email)
    if success:
        return gr.update(value=message, visible=True), gr.update(visible=True)
    return gr.update(value=message, visible=True), gr.update(visible=False)


def handle_code_verify(email, code):
    """Handles login code verification."""
    success, user_data, message = verify_login_code(email, code)

    # Check how many pages exist in navigate() to prevent errors
    num_pages = len(PAGE_NAMES)

    if success:
        short_name = get_user_display_name(user_data)
        msg = gr.update(value=message, visible=True)
        btn_update = gr.update(value=f"Logout ({short_name})", variant="secondary")

        return (
            (msg, user_data, btn_update)
            + navigate("home")
            + (gr.update(visible=False),)
        )

    else:
        page_updates = tuple([gr.update() for _ in range(num_pages)])
        return (
            (gr.update(value=message, visible=True), None, gr.update())
            + page_updates
            + (gr.update(),)
        )


def handle_login_click(current_user):
    return (
        None,  # Reset current_user_state to None
        gr.update(value="🔑 Login", variant="secondary"),  # Reset button appearance
        *navigate("login_page"),  # Force navigation to Login Page
        [],  # Clear podcast_list_state
        gr.update(value=""),  # Clear login_email_input
        gr.update(value=""),  # Clear login_code_input
        gr.update(visible=False),  # Hide login_status_msg
        gr.update(visible=False),  # Hide code_input_group
        gr.update(visible=False),  # Hide btn_quelle
    )


def refresh_podcasts_for_user(user_data):
    """Refreshes podcast list for the current user."""
    user_id = user_data["id"] if user_data else None
    return get_podcasts_for_user(user_id=user_id)


def navigate_home_and_refresh_podcasts(user_data):
    """Navigates to home page and refreshes podcast list."""
    user_id = user_data["id"] if user_data else None
    podcast_list = get_podcasts_for_user(user_id=user_id)
    return navigate("home") + (podcast_list,)


def handle_share_click(podcast_data):
    """Opens share page with podcast data."""
    if not podcast_data:
        return navigate("home")
    return navigate("share_page") + (
        podcast_data.get("titel", "Podcast"),
        gr.update(value=""),
    )


def copy_share_link(share_link):
    """Copies share link to clipboard and returns success message."""
    if share_link:
        return gr.update(value="✅ Link kopiert!", visible=True)
    return gr.update(value="❌ Kein Link vorhanden", visible=True)


def toggle_link_visibility(is_public):
    """Toggles link visibility between public/private."""
    status = "öffentlich" if is_public else "privat"
    return gr.update(value=f"Link ist jetzt {status}")


def go_back_to_home(user_data):
    """Goes back to home and refreshes podcast list."""
    return navigate_home_and_refresh_podcasts(user_data)


def show_source_preview(file_path, url, current_thema):
    """Process source and show preview if text exists. Also updates topic if empty."""
    text, title = process_source_input(file_path, url)

    preview_vis = bool(text and text.strip())
    preview_update = gr.update(value=text, visible=preview_vis)

    # Update thema if empty and title found
    if (not current_thema or not current_thema.strip()) and title:
        thema_update = gr.update(value=title)
    else:
        thema_update = gr.update()

    return preview_update, thema_update


def toggle_quelle_button(file_obj, url_text):
    """Show button if either file is uploaded or URL is entered."""
    has_file = file_obj is not None
    has_url = url_text and url_text.strip()
    return gr.update(visible=has_file or has_url)


def handle_delete_finish(podcast_data, user_data):
    """Deletes podcast from completion page."""
    if not podcast_data or not user_data:
        return get_podcasts_for_user(user_data["id"] if user_data else None)
    pid = podcast_data.get("id")
    if pid:
        delete_podcast(pid, user_data["id"])
    return get_podcasts_for_user(user_data["id"])