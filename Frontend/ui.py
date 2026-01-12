# NOTE: Benutzeroberfläche (Gradio Frontend)
# Hier wird das Layout und der ganze Klick-Kram definiert.

import gradio as gr
import sys
import os
import re

from pathlib import Path
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# Ensure we can import from team04
# Fix damit die Imports aus team04 klappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from team04.services.workflow import PodcastWorkflow
from team04.services.login_service import request_login_link, verify_login_link
from team04.services.exceptions import AuthenticationError
from team04.database.database import get_db


workflow = PodcastWorkflow()
available_voices = workflow.get_voices()
available_voices_2 = available_voices + ["Keine"]

ROLE_OPTIONS = [
    "Moderator",
    "Erzähler",
    "Fragesteller (Interviewer)",
    "Experte",
    "Co-Host",
    "Interviewpartner",
]


def navigate(target):
    """Schaltet die Sichtbarkeit der Seiten um."""
    page_names = [
        "home",
        "skript bearbeiten",
        "deine podcasts",
        "audio player",
        "loading script",
        "loading podcast",
        "login_page",
    ]
    results = []

    for page in page_names:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))

    return tuple(results)


def navigate_and_refresh_podcasts(user_data):
    """Lädt die Podcasts neu, aber nur für den eingeloggten User."""
    user_id = user_data["id"] if user_data else None
    data = workflow.get_podcasts_data(user_id=user_id)
    return navigate("deine podcasts") + (data,)


def on_play_click(audio_path):
    """Startet den Audio-Player mit dem richtigen File."""
    nav_updates = navigate("audio player")
    full_path = os.path.abspath(audio_path) if audio_path else None
    return nav_updates + (gr.update(value=full_path, autoplay=True),)


def generate_script_wrapper(thema, dauer, sprache, speaker1, role1, speaker2, role2, source_text):
    """Skript generieren mit Check ob man 1 oder 2 Sprecher hat."""
    if not speaker2 or speaker2 == "Keine" or speaker2 == speaker1:
        speaker2 = None
        role2 = None

    speakers = 2 if speaker2 else 1
    roles = {speaker1: role1}
    if speaker2 and role2 and role2 != "Keine":
        roles[speaker2] = role2

    script_text = workflow._generate_script(
        thema=thema,
        sprache=sprache,
        dauer=int(dauer),
        speakers=speakers,
        roles=roles,
        hauptstimme=speaker1,
        zweitstimme=speaker2,
        source_text=source_text,
    )
    
    # We return the script text AND the update commands for the pages
    return (script_text,) + navigate("skript bearbeiten")


# Optional / Legacy – bleibt drin, falls irgendwo benutzt
def generate_audio_wrapper(script_text, thema, dauer, sprache, speaker1, speaker2):
    return workflow.generate_audio_step(
        script_text=script_text,
        thema=thema,
        dauer=int(dauer),
        sprache=sprache,
        hauptstimme=speaker1,
        zweitstimme=speaker2,
    )


def run_audio_gen(script_text, thema, dauer, sprache, s1, s2, user_data):
    """Podcast aus dem Skript bauen und navigieren."""
    if not s2 or s2 == "Keine" or s2 == s1:
        s2 = None

    user_id = user_data["id"] if user_data else 1
    workflow.generate_audio_step(
        script_text, thema, int(dauer), sprache, s1, s2, user_id=user_id
    )
    return navigate_and_refresh_podcasts(user_data)



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


# Hilfer Funktion für daten hochladen
def extract_text_from_file(file_path: str) -> str:
    if not file_path:
        return ""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""


def fetch_text_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text.strip()


def build_source_text(file_path, url):
    file_text = extract_text_from_file(file_path) if file_path else ""
    url_text = fetch_text_from_url(url.strip()) if url else ""
    combined = file_text if file_text else url_text  # Datei > URL
    return (combined or "")[:12000]


# --- Login Logic ---
def validate_email(email):
    return "smail" in email.lower() if email else False


def handle_login_request(email):
    if not validate_email(email):
        return gr.update(value="Bitte eine gültige Smail-Adresse eingeben!", visible=True), gr.update(visible=False)
    try:
        db = get_db()
        request_login_link(db, email)
        return gr.update(value="Ein Code wurde an deine E-Mail gesendet.", visible=True), gr.update(visible=True)
    except Exception as e:
        return gr.update(value=f"Fehler: {str(e)}", visible=True), gr.update(visible=False)


def handle_code_verify(email, code):
    try:
        db = get_db()
        user = verify_login_link(db, email, code)
        user_data = {"id": user.userId, "email": user.smailAdresse}
        msg = gr.update(value=f"Erfolgreich eingeloggt als {user.smailAdresse}!", visible=True)
        btn_update = gr.update(value=f"Logout ({user.smailAdresse})", variant="secondary")
        return (msg, user_data, btn_update) + navigate("home")
    except AuthenticationError as e:
        return (gr.update(value=f"Login fehlgeschlagen: {str(e)}", visible=True), None, gr.update()) + tuple(
            [gr.update()] * 7
        )
    except Exception as e:
        return (gr.update(value=f"Fehler: {str(e)}", visible=True), None, gr.update()) + tuple([gr.update()] * 7)


def handle_login_click(current_user):
    if current_user:  # Logout
        return (None, gr.update(value="🔑 Login", variant="secondary"), *navigate("home"))
    else:  # Login Page zeigen
        return (current_user, gr.update(), *navigate("login_page"))


with gr.Blocks() as demo:
    # --- Global State ---
    current_user_state = gr.State(None)
    audio_state = gr.State()
    podcast_list_state = gr.State([])

    with gr.Column(visible=True) as home:
        with gr.Row():
            gr.Markdown("# KI Podcast Generator")
            with gr.Column(scale=0.2, min_width=100):
                btn_goto_login = gr.Button("🔑 Login", size="sm", variant="secondary")

        gr.Markdown("## Willkommen! Thema eingeben und Podcast abholen.")

        # Dauer + Sprache
        with gr.Row():
            dropdown_dauer = gr.Dropdown(
                choices=["1", "2", "3", "4", "5"],
                label="Dauer",
                value="1",
                interactive=True,
            )
            dropdown_sprache = gr.Dropdown(
                choices=["Deutsch", "English"],
                label="Sprache",
                value="Deutsch",
                interactive=True,
            )

        # Sprecher + Rollen
        with gr.Row():
            dropdown_speaker1 = gr.Dropdown(choices=available_voices, label="Sprecher 1 (Hauptstimme)")
            dropdown_role1 = gr.Dropdown(choices=ROLE_OPTIONS, label="Rolle von Sprecher 1", value="Moderator")

        with gr.Row():
            dropdown_speaker2 = gr.Dropdown(choices=available_voices_2, label="Sprecher 2 (Optional)", value="Keine")
            dropdown_role2 = gr.Dropdown(choices=ROLE_OPTIONS + ["Keine"], label="Rolle von Sprecher 2", value="Keine")

        textbox_thema = gr.Textbox(
            label="Thema",
            placeholder="Geben Sie das Thema ein...",
            lines=5,
            interactive=True,
        )

        # Upload Felder
        with gr.Row():
            file_upload = gr.File(
                label="PDF/TXT hochladen",
                file_types=[".pdf", ".txt", ".md"],
                type="filepath",
            )
            source_url = gr.Textbox(
                label="Quelle / URL (optional)",
                placeholder="https://...",
                lines=1,
            )

        btn_quelle = gr.Button("Quelle übernehmen")

        source_preview = gr.Textbox(
            label="Quelle (Text, der ins Skript einfließt)",
            lines=6,
            interactive=True,
        )

        btn_quelle.click(
            fn=build_source_text,
            inputs=[file_upload, source_url],
            outputs=source_preview,
        )

        btn_skript_generieren = gr.Button("Skript Generieren")

    # --- Skript Bearbeiten ---
    with gr.Column(visible=False) as skript_bearbeiten:
        gr.Markdown("## Skript Bearbeiten")
        text = gr.Textbox(label="Podcast Skript", lines=15)
        with gr.Row():
            btn_zuruck_skript = gr.Button("Zurück")
            btn_podcast_generieren = gr.Button("Podcast Generieren")

    # --- Deine Podcasts ---
    with gr.Column(visible=False) as deine_podcasts:
        gr.Markdown("# Deine Podcasts")

        @gr.render(inputs=podcast_list_state)
        def render_podcasts(podcasts):
            if not podcasts:
                gr.Markdown("Keine Podcasts gefunden.")
                return

            for p in podcasts:
                with gr.Group():
                    with gr.Row(variant="panel"):
                        with gr.Column(scale=4):
                            gr.Markdown(f"### {p['titel']}")
                            gr.Markdown(f"📅 {p['datum']} | ⏱️ {p['dauer']} Min")
                        with gr.Column(scale=1):
                            btn_card_play = gr.Button("▶ Play", variant="primary")
                            btn_card_play.click(
                                fn=on_play_click,
                                inputs=[gr.State(p["path"])],
                                outputs=pages + [audio_player],
                            )

        btn_zuruck_deinepodcasts = gr.Button("Zurück")

    # --- Player ---
    with gr.Column(visible=False) as audio_player_page:
        gr.Markdown("## Audio Player")
        audio_player = gr.Audio(label="Podcast", type="filepath")
        btn_zuruck_audio = gr.Button("Zurück zu Deinen Podcasts")

    # --- Loading ---
    with gr.Column(visible=False) as loading_page_script:
        gr.HTML(get_loader_html("Skript wird generiert..."))
        btn_cancel_skript = gr.Button("Abbrechen", variant="secondary")

    with gr.Column(visible=False) as loading_page_podcast:
        gr.HTML(get_loader_html("Podcast wird generiert..."))
        btn_cancel_podcast = gr.Button("Abbrechen", variant="secondary")

    # --- Login Page ---
    with gr.Column(visible=False) as login_page:
        gr.Markdown("# Login")
        gr.Markdown("Bitte gib deine Smail-Adresse ein, um einen Login-Code zu erhalten.")

        with gr.Row():
            with gr.Column(scale=1):
                pass  # Linker Spacer
            with gr.Column(scale=2):
                login_email_input = gr.Textbox(label="E-Mail Adresse", placeholder="dein.name@smail.th-koeln.de")
                login_status_msg = gr.Markdown("", visible=False)
                btn_request_code = gr.Button("Code anfordern", variant="primary")

                with gr.Group(visible=False) as code_input_group:
                    gr.Markdown("### Code eingeben")
                    login_code_input = gr.Textbox(label="8-stelliger Code", placeholder="Code aus der E-Mail")
                    btn_verify_code = gr.Button("Anmelden")

                btn_back_from_login = gr.Button("Zurück zum Start")
            with gr.Column(scale=1):
                pass  # Rechter Spacer

    pages = [
        home,
        skript_bearbeiten,
        deine_podcasts,
        audio_player_page,
        loading_page_script,
        loading_page_podcast,
        login_page,
    ]

    # --- Events ---
    btn_goto_login.click(
        fn=handle_login_click,
        inputs=[current_user_state],
        outputs=[current_user_state, btn_goto_login] + pages,
    )
    btn_back_from_login.click(fn=lambda: navigate("home"), outputs=pages)
    btn_request_code.click(fn=handle_login_request, inputs=[login_email_input], outputs=[login_status_msg, code_input_group])
    btn_verify_code.click(
        fn=handle_code_verify,
        inputs=[login_email_input, login_code_input],
        outputs=[login_status_msg, current_user_state, btn_goto_login] + pages,
    )

    # Skript generieren (mit Rollen + source_preview) + Cancel
    skript_task = btn_skript_generieren.click(
        fn=lambda: navigate("loading script"),
        inputs=None,
        outputs=pages,
    ).then(
        fn=generate_script_wrapper,
        inputs=[
            textbox_thema,
            dropdown_dauer,
            dropdown_sprache,
            dropdown_speaker1,
            dropdown_role1,
            dropdown_speaker2,
            dropdown_role2,
            source_preview,
        ],
        outputs=[text] + pages
    )

    btn_cancel_skript.click(
        fn=lambda: navigate("home"),
        inputs=None,
        outputs=pages,
        cancels=skript_task,
    )

    btn_zuruck_deinepodcasts.click(fn=lambda: navigate("skript bearbeiten"), outputs=pages)
    btn_zuruck_skript.click(fn=lambda: navigate("home"), outputs=pages)

    podcast_task = btn_podcast_generieren.click(
        fn=lambda: navigate("loading podcast"),
        outputs=pages,
    ).success(
        fn=run_audio_gen,
        inputs=[text,
                textbox_thema,
                dropdown_dauer,
                dropdown_sprache,
                dropdown_speaker1,
                dropdown_speaker2,
                current_user_state],
        outputs=pages + [podcast_list_state],
    )

    btn_cancel_podcast.click(
        fn=lambda: navigate("skript bearbeiten"),
        inputs=None,
        outputs=pages,
        cancels=podcast_task,
    )

    btn_zuruck_audio.click(fn=navigate_and_refresh_podcasts, inputs=[current_user_state], outputs=pages + [podcast_list_state])


if __name__ == "__main__":
    demo.queue().launch()
