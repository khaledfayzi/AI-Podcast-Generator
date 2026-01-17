# NOTE: Benutzeroberfläche (Gradio Frontend)
# Hier wird das Layout und der ganze Klick-Kram definiert.

import gradio as gr
from gradio.themes import Ocean
import sys
import os
from datetime import datetime

# Fix damit die Imports aus team04 klappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

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
        "share_page",
    ]
    results = []

    for page in page_names:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))

    return tuple(results)


# --- UI Event Handlers (thin wrappers around backend) ---
def on_play_click(audio_path, podcast_title):
    """Startet den Audio-Player mit dem richtigen File."""
    nav_updates = navigate("audio player")
    full_path = get_absolute_audio_path(audio_path)
    title_md = f"<div style='text-align: center; margin-bottom: 20px;'><h2>🎙️ {podcast_title}</h2></div>"
    return nav_updates + (gr.update(value=full_path, autoplay=True), gr.update(value=title_md))


def generate_script_wrapper(thema, dauer, sprache, speaker1, role1, speaker2, role2, source_text, source_url, file_upload):
    """
    Prüft, ob mindestens ein Thema ODER ein Quelltext ODER eine URL vorhanden ist.
    Falls nicht, bleibt der User auf der Home-Seite.
    """
    has_thema = thema and thema.strip()
    has_url = source_url and source_url.strip()
    has_file = file_upload is not None

    if not (has_thema  or has_url or has_file):
        gr.Warning("Bitte gib mindestens ein Thema an, lade eine Datei hoch oder füge eine URL ein!")
        return ("",) + navigate("home")


    if  has_url or has_file:
        try:
            gr.Info("Quelle wird automatisch verarbeitet...")
            source_text = process_source_input(file_upload, source_url)
        except Exception as e:
            gr.Warning(f"Fehler beim Verarbeiten der Quelle: {str(e)}")
            if not has_thema:
                return ("",) + navigate("home")

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
        return (script_text,) + navigate("skript bearbeiten")
    except Exception as e:
        gr.Warning(f"Fehler bei der Skript-Generierung: {str(e)}")
        return ("",) + navigate("home")


def run_audio_gen(script_text, thema, dauer, sprache, s1, s2, r1, r2, user_data):
    """Podcast aus dem Skript bauen, Player starten und Liste aktualisieren."""
    user_id = user_data["id"] if user_data else 1
    
    # Generate audio
    try:
        audio_path = generate_audio(
            script_text=script_text,
            thema=thema,
            dauer=dauer,
            sprache=sprache,
            speaker1=s1,
            speaker2=s2,
            user_id=user_id,
            role1=r1,
            role2=r2
        )
    except Exception as e:
        gr.Error(f"Fehler bei generierung des Podcats! {str(e)}")
    
    # Refresh podcast list
    updated_data = get_podcasts_for_user(user_id=user_id)

    # Navigate to audio player
    nav_updates = navigate("audio player")
    full_path = get_absolute_audio_path(audio_path)
    title_md = f"<div style='text-align: center; margin-bottom: 20px;'><h2>🎙️ {thema}</h2></div>"

    return nav_updates + (
        gr.update(value=full_path, autoplay=True), 
        updated_data, 
        gr.update(value=title_md)
    )


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


# --- Share Handlers ---
def handle_share_click(podcast_data):
    """Opens share page with podcast data."""
    if not podcast_data:
        return navigate("home")
    # Return navigation updates + podcast title for display
    return navigate("share_page") + (podcast_data.get("titel", "Podcast"), gr.update(value=""))


def copy_share_link(share_link):
    """Copies share link to clipboard and returns success message."""
    if share_link:
        # In a real app, JavaScript would copy to clipboard
        # For now, return a message indicating copy action
        return gr.update(value="✅ Link kopiert!", visible=True)
    return gr.update(value="❌ Kein Link vorhanden", visible=True)


def toggle_link_visibility(is_public):
    """Toggles link visibility between public/private."""
    status = "öffentlich" if is_public else "privat"
    return gr.update(value=f"Link ist jetzt {status}")


def go_back_to_home(user_data):
    """Goes back to home and refreshes podcast list."""
    return navigate_home_and_refresh_podcasts(user_data)


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




with gr.Blocks(css=css_content, theme=gr.themes.Soft(primary_hue="indigo")) as demo:
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
                        choices=["Kurz(~5min)","Mittel(~15min)","Lang(~30min)"],
                        label="Dauer",
                        value="Mittel(~15min)",
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
                        max_lines=1,
                        scale=1,
                        elem_id="source_url_input"
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
                        audio_full_path = get_absolute_audio_path(p["path"])
                        with gr.Row(equal_height=True):
                            btn_play_home = gr.Button("▶ Play", variant="primary", size="sm", scale=1, elem_classes="btn-play podcast-btn")
                            
                            btn_download_home = gr.DownloadButton(
                                "⤓ Download", 
                                value=audio_full_path,
                                size="sm", 
                                scale=1,
                                elem_classes="btn-download podcast-btn"
                            )
                            
                            btn_delete_home = gr.Button("🗑️ Löschen", variant="stop", size="sm", scale=1, elem_classes="btn-delete podcast-btn")
                            btn_share_home = gr.Button("📤 Teilen", size="sm", scale=1, elem_classes="btn-share podcast-btn")
                        
                        # --- Card Events ---
                        btn_play_home.click(
                            fn=on_play_click,
                            inputs=[
                                gr.State(p["path"]), 
                                gr.State(p["titel"])
                            ],
                            outputs=pages + [audio_player, player_title_display], # markdown output
                        )
                        
                        podcast_id = p.get("id")
                        btn_delete_home.click(
                            fn=lambda pid=podcast_id, ud=user_data: delete_podcast_handler(pid, ud),
                            inputs=[],
                            outputs=[podcast_list_state]
                        )
                        
                        btn_share_home.click(
                            fn=lambda pod_data=p: handle_share_click(pod_data),
                            inputs=[],
                            outputs=pages + [share_podcast_title, share_link_input]
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
        player_title_display = gr.Markdown("## 🎙️ Unbekannter Podcast", elem_id="player_title_header")
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

    # --- Share Page ---
    with gr.Column(visible=False) as share_page:
        gr.Markdown("# Podcast Teilen!")
        
        with gr.Row():
            with gr.Column(scale=1):
                pass
            with gr.Column(scale=3):
                share_podcast_title = gr.Markdown("### Teile 'Titel das podcast' mit andere")
                
                gr.Markdown("**Link:**")
                
                with gr.Row():
                    share_link_input = gr.Textbox(
                        label="",
                        placeholder="https\\...",
                        interactive=False,
                        show_label=False,
                        max_lines=1,
                        elem_id="share_link_output"
                    )
                    btn_copy_link = gr.Button("📋 Link Kopieren", scale=0)
                
                gr.Markdown("**Link Öffentlich/Privat machen**")
                share_link_toggle = gr.Checkbox(
                    label="Link öffentlich machen",
                    value=False
                )
                
                share_status_msg = gr.Markdown("", visible=False)
                
                btn_cancel_share = gr.Button("Zurück")
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
        share_page,
    ]

    # --- Events ---
    btn_goto_uber.click(fn=lambda: navigate("uber_page"), outputs=pages)
    btn_back_from_uber.click(fn=lambda: navigate("home"), outputs=pages)
    
    # Share page events
    btn_cancel_share.click(
        fn=go_back_to_home,
        inputs=[current_user_state],
        outputs=pages + [podcast_list_state]
    )
    
    btn_copy_link.click(
        fn=copy_share_link,
        inputs=[share_link_input],
        outputs=[share_status_msg]
    )
    
    share_link_toggle.change(
        fn=toggle_link_visibility,
        inputs=[share_link_toggle],
        outputs=[share_status_msg]
    )
    
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
                textbox_thema, # title
                dropdown_dauer,
                dropdown_sprache,
                dropdown_speaker1,
                dropdown_speaker2,
                dropdown_role1,
                dropdown_role2,
                current_user_state],
        outputs=pages + [audio_player, podcast_list_state, player_title_display], # markdown output
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
