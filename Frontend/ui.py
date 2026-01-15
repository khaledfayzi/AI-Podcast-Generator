# gradio 5.49.1
# NOTE: Benutzeroberfläche (Gradio Frontend)
# Hier wird das Layout und der ganze Klick-Kram definiert.

import gradio as gr
from gradio.themes import Ocean
import sys
import os
from datetime import datetime

# Fix damit die Imports aus team04 klappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import backend service instead of direct workflow/service imports
from team04.services.ui_backend import (
    get_available_voices,
    generate_script,
    generate_audio,
    get_podcasts_for_user,
    delete_podcast,
    get_absolute_audio_path,
    request_login_code,
    verify_login_code,
    get_user_display_name,
    process_source_input,
)

# Get available voices on startup
available_voices_primary, available_voices_secondary = get_available_voices()
available_voices_secondary_with_none = available_voices_secondary + ["Keine"]

ROLE_OPTIONS = [
    "Moderator",
    "Erzähler",
    "Fragesteller (Interviewer)",
    "Experte",
    "Co-Host",
    "Interviewpartner",
]


def format_podcast_date(date_string: str) -> str:
    """Formats a podcast date string from YYYY-MM-DD to DD.MM.YYYY."""
    try:
        date_obj = datetime.strptime(date_string, '%Y-%m-%d')
        return date_obj.strftime('%d.%m.%Y')
    except (ValueError, TypeError):
        return date_string


# --- Navigation Helper ---
def navigate(target):
    """Schaltet die Sichtbarkeit der Seiten um."""
    page_names = [
        "home",
        "skript bearbeiten",
        "audio player",
        "loading script",
        "loading podcast",
        "login_page",
        "uber_page",
    ]
    results = []

    for page in page_names:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))

    return tuple(results)


# --- UI Event Handlers (thin wrappers around backend) ---
def on_play_click(audio_path):
    """Startet den Audio-Player mit dem richtigen File."""
    nav_updates = navigate("audio player")
    full_path = get_absolute_audio_path(audio_path)
    return nav_updates + (gr.update(value=full_path, autoplay=True),)


def generate_script_wrapper(thema, dauer, sprache, speaker1, role1, speaker2, role2, source_text):
    """UI wrapper for script generation."""
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
    return (script_text,) + navigate("skript bearbeiten")


def run_audio_gen(script_text, thema, dauer, sprache, s1, s2, r1, r2, user_data):
    """Podcast aus dem Skript bauen, Player starten und Liste aktualisieren."""
    user_id = user_data["id"] if user_data else 1
    
    # Generate audio
    audio_path = generate_audio(
        script_text=script_text,
        thema=thema,
        dauer=dauer,
        sprache=sprache,
        speaker1=s1,
        speaker2=s2,
        user_id=user_id,
        role1=r1,  # NEU
        role2=r2   # NEU
    )
    
    # Refresh podcast list
    updated_data = get_podcasts_for_user(user_id=user_id)

    # Navigate to audio player
    nav_updates = navigate("audio player")
    full_path = get_absolute_audio_path(audio_path)

    return nav_updates + (gr.update(value=full_path, autoplay=True), updated_data)


def delete_podcast_handler(podcast_id: int, user_data):
    """Handles podcast deletion and returns updated list."""
    if not user_data:
        return get_podcasts_for_user(user_id=None)
    
    user_id = user_data["id"]
    delete_podcast(podcast_id, user_id)
    return get_podcasts_for_user(user_id=user_id)


# --- Login Handlers ---
def handle_login_request(email):
    """Handles login code request."""
    success, message = request_login_code(email)
    if success:
        return gr.update(value=message, visible=True), gr.update(visible=True)
    return gr.update(value=message, visible=True), gr.update(visible=False)


def handle_code_verify(email, code):
    """Handles login code verification."""
    success, user_data, message = verify_login_code(email, code)
    
    if success:
        short_name = get_user_display_name(user_data)
        msg = gr.update(value=message, visible=True)
        btn_update = gr.update(value=f"Logout ({short_name})", variant="secondary")
        return (msg, user_data, btn_update) + navigate("home")
    else:
        return (gr.update(value=message, visible=True), None, gr.update()) + tuple([gr.update()] * 7)


def handle_login_click(current_user):
    """Handles login/logout button click."""
    if current_user:  # Logout
        return (
            None,                                    # current_user_state
            gr.update(value="🔑 Login", variant="secondary"),  # btn_goto_login
            *navigate("home"),                       # 7 pages
            [],                                      # podcast_list_state
            gr.update(value=""),                     # login_email_input
            gr.update(value=""),                     # login_code_input
            gr.update(visible=False),                # login_status_msg
            gr.update(visible=False)                 # code_input_group
        )
    else:  # Show login page
        return (
            current_user, 
            gr.update(), 
            *navigate("login_page"), 
            gr.update(),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False)
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


# --- Helper Functions ---
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


# CSS to force buttons to auto-expand and add rounded corners
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body, button, input, textarea, select {
    font-family: 'Inter', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
}

/* Dropdown styling */
.dropdown, .select, select {
    font-family: 'Inter', sans-serif !important;
}

/* Gradio input fields */
input, textarea {
    font-family: 'Inter', sans-serif !important;
}

/* Target Gradio's internal dropdown */
[role="combobox"], [role="listbox"], [role="option"] {
    font-family: 'Inter', sans-serif !important;
}

/* Fallback for all text elements */
* {
    font-family: 'Inter', sans-serif !important;
}

.header-btn {
    width: fit-content !important;
    min-width: 80px !important;
    white-space: nowrap !important;
    flex: 0 0 auto !important;
    display: inline-flex !important;
    justify-content: center !important;
    border-radius: 12px !important;
}

/* Podcast card button styling */
.podcast-btn {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
}

.podcast-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

/* Play button styling */
.btn-play {
    border-radius: 10px !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    font-weight: 600 !important;
}

.btn-play:hover {
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
}

/* Delete button styling */
.btn-delete {
    border-radius: 10px !important;
    background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    margin-top: 10px !important;
}

.btn-delete:hover {
    box-shadow: 0 4px 15px rgba(107, 114, 128, 0.4) !important;
}

/* Download button styling */
.btn-download {
    border-radius: 10px !important;
    background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%) !important;
    color: white !important;
    font-weight: 600 !important;
}

.btn-download:hover {
    box-shadow: 0 4px 15px rgba(107, 114, 128, 0.4) !important;
}

/* Podcast card container - only target the main container */
.podcast-card {
    border-radius: 15px !important;
    border: 1px solid #333333 !important;
    background: #1a1a1a !important;
    padding: 30px !important;
    margin-bottom: 20px !important;
    transition: all 0.3s ease !important;
}

.podcast-card:hover {
    border-color: #667eea !important;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15) !important;
}

/* Remove borders and backgrounds from child elements */
.podcast-card > div,
.podcast-card .block,
.podcast-card [data-testid="group"],
.podcast-card [data-testid="row"],
.podcast-card .row,
.podcast-card .panel {
    border: none !important;
    background: transparent !important;
    background-color: transparent !important;
}

/* Target Gradio's panel variant specifically */
.podcast-card .panel,
.podcast-card [variant="panel"],
.podcast-card .gr-panel {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
}

/* Force dark background for all Gradio groups */
.gradio-group,
[data-testid="group"],
.group {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
}

/* Add gap between buttons in Row */
.podcast-card .row {
    gap: 12px !important;
}

/* General button styling */
button {
    border-radius: 10px !important;
}

/* Hides Gradio footer */
.gradio-footer,
footer,
.footer {
    display: none !important;
}
"""


with gr.Blocks(css=custom_css, theme=gr.themes.Soft(primary_hue="indigo")) as demo:
    # --- Global State ---
    current_user_state = gr.State(None)
    audio_state = gr.State()
    podcast_list_state = gr.State([])

    with gr.Column(visible=True) as home:
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("# KI Podcast Generator")

            with gr.Column(scale=0):
                with gr.Row():
                    btn_goto_uber = gr.Button("ℹ️ Über",
                                            size="sm",
                                            variant="secondary",
                                            scale=0,
                                            elem_classes="header-btn"
                                            )
                            
                    btn_goto_login = gr.Button("🔑 Login",
                                            size="sm",
                                            variant="secondary",
                                            scale=0,
                                            elem_classes="header-btn"
                                            )

        gr.Markdown("## Willkommen! Thema eingeben und Podcast abholen.")

        # Main content with spacers for centering
        with gr.Row():
            with gr.Column(scale=1):
                pass  # Left Spacer
            with gr.Column(scale=3):
                # Dauer + Sprache
                with gr.Row():
                    dropdown_dauer = gr.Dropdown(
                        choices=["1", "2", "3", "4", "5"],
                        label="Dauer",
                        value="1",
                        interactive=True,
                        scale=1,
                    )
                    dropdown_sprache = gr.Dropdown(
                        choices=["Deutsch", "English"],
                        label="Sprache",
                        value="Deutsch",
                        interactive=True,
                        scale=1,
                    )

                # Sprecher 1 (Hauptstimme) nutzt nur Slot 1
                with gr.Row():
                    dropdown_speaker1 = gr.Dropdown(
                        choices=available_voices_primary,
                        label="Sprecher 1 (Hauptstimme)",
                        value=available_voices_primary[0] if available_voices_primary else None,
                        interactive=True,
                        scale=1,
                    )
                    dropdown_role1 = gr.Dropdown(choices=ROLE_OPTIONS, label="Rolle von Sprecher 1", value="Moderator", scale=1)

                # Sprecher 2 (Optional) nutzt nur Slot 2
                with gr.Row():
                    dropdown_speaker2 = gr.Dropdown(
                        choices=available_voices_secondary_with_none,
                        label="Sprecher 2 (Optional)",
                        value="Keine",
                        interactive=True,
                        scale=1,
                    )
                    dropdown_role2 = gr.Dropdown(choices=ROLE_OPTIONS + ["Keine"], label="Rolle von Sprecher 2", value="Keine", scale=1)
                
                textbox_thema = gr.Textbox(
                    label="Thema",
                    placeholder="Geben Sie das Thema ein...",
                    lines=4,
                    interactive=True,
                )

                # Upload Felder
                with gr.Row():
                    file_upload = gr.File(
                        label="PDF/TXT hochladen",
                        file_types=[".pdf", ".txt", ".md"],
                        type="filepath",
                        scale=1,
                    )
                    source_url = gr.Textbox(
                        label="Quelle / URL (optional)",
                        placeholder="https://...",
                        lines=1,
                        scale=1,
                    )

                btn_quelle = gr.Button("Quelle übernehmen")

                source_preview = gr.Textbox(
                    label="Quelle (Text, der ins Skript einfließt)",
                    lines=5,
                    interactive=True,
                )

                btn_quelle.click(
                    fn=process_source_input,
                    inputs=[file_upload, source_url],
                    outputs=source_preview,
                )

                btn_skript_generieren = gr.Button("Skript Generieren", variant="primary")
            with gr.Column(scale=1):
                pass  # Right Spacer

        # Podcast Liste auf der Home Page
        gr.Markdown("---")
        gr.Markdown("## Deine Podcasts")


        # Render Single Card
        def create_podcast_card(p, user_data):
            """Renders a single podcast card with layout and events."""
            with gr.Group(elem_classes="podcast-card"):
                with gr.Row(variant="panel"):
                    # Meta Data Column
                    with gr.Column(scale=4):
                        gr.Markdown(f"### 🎙️ {p['titel']}")
                        
                        formatted_date = format_podcast_date(p['datum'])
                        metadata_lines = [
                            f"📅 {formatted_date} · ⏱️ {p['dauer']} Min · 🗣️ {p['sprache']}"
                        ]
                        
                        if p.get('sprecher'):
                            metadata_lines.append(f"**Sprecher:** {p['sprecher']}")
                        if p.get('rollen'):
                            metadata_lines.append(f"**Rollen:** {p['rollen']}")
                        
                        gr.Markdown("\n\n".join(metadata_lines))

                    # Action Buttons Column
                    with gr.Column(scale=1):
                        with gr.Row(equal_height=True):
                            btn_play_home = gr.Button("▶ Play", variant="primary", size="sm", scale=1, elem_classes="btn-play podcast-btn")
                            audio_full_path = get_absolute_audio_path(p["path"])
                            
                            btn_download_home = gr.DownloadButton(
                                "⤓ Download", 
                                value=audio_full_path,
                                size="sm", 
                                scale=1,
                                elem_classes="btn-download podcast-btn"
                            )
                        
                        btn_delete_home = gr.Button("🗑️ Löschen", variant="stop", size="sm", elem_classes="btn-delete podcast-btn")
                        
                        # --- Card Events ---
                        btn_play_home.click(
                            fn=on_play_click,
                            inputs=[gr.State(p["path"])],
                            outputs=pages + [audio_player],
                        )
                        
                        podcast_id = p.get("id")
                        btn_delete_home.click(
                            fn=lambda pid=podcast_id, ud=user_data: delete_podcast_handler(pid, ud),
                            inputs=[],
                            outputs=[podcast_list_state]
                        )

        # --- Main List Renderer ---
        @gr.render(inputs=[podcast_list_state, current_user_state])
        def render_home_podcasts_list(podcasts, user_data):
            if not podcasts:
                gr.Markdown("<i>Noch keine Podcasts vorhanden. Erstelle deinen ersten Podcast!</i>")
                return

            for p in podcasts:
                create_podcast_card(p, user_data)

    # --- Skript Bearbeiten ---
    with gr.Column(visible=False) as skript_bearbeiten:
        gr.Markdown("## Skript Bearbeiten")

        with gr.Accordion("💡 Anleitung: So gestaltest du die Sprache", open=False):
            gr.Markdown("""
            Du kannst das Skript anpassen. Nutze diese Symbole für eine bessere Sprachausgabe:
            - **Betonung:** Nutze `**Wort**` für starke oder `*Wort*` für mittlere Betonung.
            - **Pausen:** Schreibe `[pause: 1s]` oder `[pause: 500ms]` für Stille.
            - **Buchstabieren:** Nutze `[spell: KI]`, damit es 'K-I' statt 'Ki' ausgesprochen wird.
            - **Datum/Zeit:** Nutze `[date: 10.10.2025]` oder `[dur: 2m 30s]`.
            """)

        text = gr.Textbox(label="Podcast Skript", lines=15)

        with gr.Row():
            btn_zuruck_skript = gr.Button("Zurück")
            btn_podcast_generieren = gr.Button("Podcast Generieren", variant="primary")

    # --- Player ---
    with gr.Column(visible=False) as audio_player_page:
        gr.Markdown("## Audio Player")
        audio_player = gr.Audio(label="Podcast", type="filepath")
        btn_zuruck_audio = gr.Button("Zurück zur Startseite")

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
                pass
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
                pass

    # --- Über Page ---
    with gr.Column(visible=False) as uber_page:
        gr.Markdown("# Über den KI Podcast Generator")
        
        with gr.Row():
            with gr.Column(scale=1):
                pass
            with gr.Column(scale=3):
                gr.Markdown("""
                ## 🎙️ Willkommen beim KI Podcast Generator!
                
                Über den KI Podcast Generator
                Unsere Mission ist es, die Podcast-Erstellung für jeden zugänglich zu
                machen. Mit modernster KI-Technologie verwandeln wir deine Ideen in
                professionelle Podcasts.

                # Technologie

                Unser KI Podcast Generator nutzt modernste Technologien:
                    Text-to-Speech (TTS) Technologie mit natürlich klingenden Stimmen
                    Emotionale Intelligenz für ausdrucksstarke Sprachausgabe
                    Automatische PDF- und Textanalyse
                
                
                ---
                *Version 1.0 | Team04 | TH Köln*
                """)
                
                btn_back_from_uber = gr.Button("Zurück", variant="primary")
            with gr.Column(scale=1):
                pass

    pages = [
        home,
        skript_bearbeiten,
        audio_player_page,
        loading_page_script,
        loading_page_podcast,
        login_page,
        uber_page,
    ]

    # --- Events ---
    btn_goto_uber.click(fn=lambda: navigate("uber_page"), outputs=pages)
    btn_back_from_uber.click(fn=lambda: navigate("home"), outputs=pages)
    
    btn_goto_login.click(
        fn=handle_login_click,
        inputs=[current_user_state],
        outputs=[
            current_user_state, 
            btn_goto_login
        ] + pages + [
            podcast_list_state,
            login_email_input,
            login_code_input,
            login_status_msg,
            code_input_group
        ],
    )
    
    btn_back_from_login.click(fn=lambda: navigate("home"), outputs=pages)
    btn_request_code.click(fn=handle_login_request, inputs=[login_email_input], outputs=[login_status_msg, code_input_group])
    btn_verify_code.click(
        fn=handle_code_verify,
        inputs=[login_email_input, login_code_input],
        outputs=[login_status_msg, current_user_state, btn_goto_login] + pages,
    ).then(
        fn=refresh_podcasts_for_user,
        inputs=[current_user_state],
        outputs=[podcast_list_state]
    )

    # Skript generieren + Cancel
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
                dropdown_role1,  # NEU
                dropdown_role2,  # NEU
                current_user_state],
        outputs=pages + [audio_player, podcast_list_state],
    )

    btn_cancel_podcast.click(
        fn=lambda: navigate("skript bearbeiten"),
        inputs=None,
        outputs=pages,
        cancels=podcast_task,
    )

    btn_zuruck_audio.click(
        fn=navigate_home_and_refresh_podcasts,
        inputs=[current_user_state],
        outputs=pages + [podcast_list_state]
    )

    demo.load(
        fn=refresh_podcasts_for_user,
        inputs=[current_user_state],
        outputs=[podcast_list_state]
    )


if __name__ == "__main__":
    demo.queue().launch()
