import gradio as gr
from gradio.themes import Ocean
import sys
import os

# Fix damit die Imports aus team04 klappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

logo_with_text_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "logo", "logo_mit_text.png"))

try:
    from . import ui_handlers as handlers
except ImportError:
    import ui_handlers as handlers

from .controller import (
    get_available_voices,
    get_absolute_audio_path,
)

# Get available voices on startup
available_voices_primary, available_voices_secondary = get_available_voices()
available_voices_secondary_with_none = available_voices_secondary + ["Keine"]

with gr.Blocks(
    css=css_content,
    theme=gr.themes.Soft(primary_hue="indigo"),
    title="KI Podcast Generator",
) as demo:
    # --- Global State ---
    current_user_state = gr.State(None)
    audio_state = gr.State()
    podcast_list_state = gr.State([])
    current_podcast_state = gr.State({})

    with gr.Column(visible=True) as home:
        with gr.Row():
            with gr.Column(scale=1):
                gr.Image(
                    logo_with_text_path,
                    show_label=False,
                    show_download_button=False,
                    show_fullscreen_button=False,
                    interactive=False,
                    height=100,
                    width=500,
                    elem_id="header-logo",
                    container=False,
                )

            with gr.Column(scale=0):
                with gr.Row():
                    btn_goto_nutzungs = gr.Button(
                        "⚖️ Nutzungsbedingungen",
                        size="md",
                        variant="secondary",
                        scale=0,
                        elem_classes="header-btn",
                    )

                    btn_goto_uber = gr.Button(
                        "ℹ️ Über",
                        size="md",
                        variant="secondary",
                        scale=0,
                        elem_classes="header-btn",
                    )

                    btn_goto_login = gr.Button(
                        "🔑 Login",
                        size="md",
                        variant="secondary",
                        scale=0,
                        elem_classes="header-btn",
                    )

        gr.Markdown("## Willkommen! Thema eingeben und Podcast abholen.")

        # Main content
        with gr.Row():
            with gr.Column(scale=1):
                pass
            with gr.Column(scale=3):
                # Dauer + Sprache
                with gr.Row():
                    dropdown_dauer = gr.Dropdown(
                        choices=["Kurz (~5min)", "Mittel (~15min)", "Lang (~30min)"],
                        label="Dauer",
                        value="Kurz (~5min)",
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

                # Sprecher 1
                with gr.Row():
                    dropdown_speaker1 = gr.Dropdown(
                        choices=available_voices_primary,
                        label="Sprecher 1 (Hauptstimme)",
                        value=(
                            available_voices_primary[0]
                            if available_voices_primary
                            else None
                        ),
                        interactive=True,
                        scale=1,
                    )
                    dropdown_role1 = gr.Dropdown(
                        choices=handlers._get_roles(1),
                        label="Rolle von Sprecher 1",
                        value="Moderator",
                        scale=1,
                    )

                # Sprecher 2
                with gr.Row():
                    dropdown_speaker2 = gr.Dropdown(
                        choices=available_voices_secondary_with_none,
                        label="Sprecher 2 (Optional)",
                        value="Keine",
                        interactive=True,
                        scale=1,
                    )
                    dropdown_role2 = gr.Dropdown(
                        choices=handlers._get_roles(2) + ["Keine"],
                        label="Rolle von Sprecher 2",
                        value="Keine",
                        scale=1,
                    )

                dropdown_speaker2.change(
                    fn=handlers._get_matching_role,
                    inputs=[dropdown_speaker2, dropdown_role1],
                    outputs=dropdown_role2,
                )

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
                        elem_id="source_url_input",
                    )

                btn_quelle = gr.Button("Quelle übernehmen", visible=False)

                source_preview = gr.Textbox(
                    label="Quelle (Text, der ins Skript einfließt)",
                    lines=5,
                    interactive=True,
                    visible=False,
                )

                file_upload.change(
                    fn=handlers.toggle_quelle_button,
                    inputs=[file_upload, source_url],
                    outputs=btn_quelle,
                )

                source_url.change(
                    fn=handlers.toggle_quelle_button,
                    inputs=[file_upload, source_url],
                    outputs=btn_quelle,
                )

                btn_quelle.click(
                    fn=handlers.show_source_preview,
                    inputs=[file_upload, source_url, textbox_thema],
                    outputs=[source_preview, textbox_thema],
                )

                btn_skript_generieren = gr.Button(
                    "Skript Generieren", variant="primary"
                )
            with gr.Column(scale=1):
                pass

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

                        formatted_date = handlers.format_podcast_date(p["datum"])
                        metadata_lines = [
                            f"📅 {formatted_date} · ⏱️ {p['dauer']} Min · 🗣️ {p['sprache']}"
                        ]

                        if p.get("sprecher"):
                            metadata_lines.append(f"**Sprecher:** {p['sprecher']}")
                        if p.get("rollen"):
                            metadata_lines.append(f"**Rollen:** {p['rollen']}")

                        gr.Markdown("\n\n".join(metadata_lines))

                    # Action Buttons Column
                    with gr.Column(scale=1):
                        audio_full_path = get_absolute_audio_path(p["path"])
                        with gr.Row(equal_height=True):
                            btn_play_home = gr.Button(
                                "▶ Play",
                                variant="primary",
                                size="sm",
                                scale=1,
                                elem_classes="btn-play podcast-btn",
                            )

                            btn_download_home = gr.DownloadButton(
                                "⤓ Download",
                                value=audio_full_path,
                                size="sm",
                                scale=1,
                                elem_classes="btn-download podcast-btn",
                            )

                            btn_delete_home = gr.Button(
                                "🗑️ Löschen",
                                variant="stop",
                                size="sm",
                                scale=1,
                                elem_classes="btn-delete podcast-btn",
                            )
                            btn_share_home = gr.Button(
                                "📤 Teilen",
                                size="sm",
                                scale=1,
                                elem_classes="btn-share podcast-btn",
                            )

                        # --- Card Events ---
                        btn_play_home.click(
                            fn=handlers.on_play_click,
                            inputs=[gr.State(p["path"]), gr.State(p["titel"])],
                            outputs=pages + [audio_player, player_title_display],
                        )

                        podcast_id = p.get("id")
                        btn_delete_home.click(
                            fn=lambda pid=podcast_id, ud=user_data: handlers.delete_podcast_handler(
                                pid, ud
                            ),
                            inputs=[],
                            outputs=[podcast_list_state],
                        )

                        btn_share_home.click(
                            fn=lambda pod_data=p: handlers.handle_share_click(pod_data),
                            inputs=[],
                            outputs=pages + [share_podcast_title, share_link_input],
                        )

        # --- Main List Renderer ---
        @gr.render(inputs=[podcast_list_state, current_user_state])
        def render_home_podcasts_list(podcasts, user_data):
            if not podcasts:
                gr.Markdown(
                    "<i>Noch keine Podcasts vorhanden. Erstelle deinen ersten Podcast!</i>"
                )
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
        player_title_display = gr.Markdown(
            "## 🎙️ Unbekannter Podcast", elem_id="player_title_header"
        )
        audio_player = gr.Audio(label="Podcast", type="filepath")
        
        with gr.Row():
            btn_download_finish = gr.DownloadButton("⤓ Download", size="md", visible=False)
            btn_delete_finish = gr.Button("🗑️ Löschen", variant="stop", size="md", visible=False)
            btn_share_finish = gr.Button("📤 Teilen", size="md", visible=False)

        btn_zuruck_audio = gr.Button("Zurück zur Startseite")

    # --- Loading ---
    with gr.Column(visible=False) as loading_page_script:
        gr.HTML(
            handlers.get_loader_html(
                "Das Skript wird gerade erstellt, das kann einen Moment dauern."
            )
        )
        btn_cancel_skript = gr.Button("Abbrechen", variant="secondary")

    with gr.Column(visible=False) as loading_page_podcast:
        gr.HTML(handlers.get_loader_html("Podcast wird generiert, das kann einen Moment dauern."))
        btn_cancel_podcast = gr.Button("Abbrechen", variant="secondary")

    # --- Login Page ---
    with gr.Column(visible=False) as login_page:
        gr.Markdown("# Login")
        gr.Markdown(
            "Bitte gib deine Smail-Adresse ein, um einen Login-Code zu erhalten."
        )

        with gr.Row():
            with gr.Column(scale=1):
                pass
            with gr.Column(scale=2):
                login_email_input = gr.Textbox(
                    label="E-Mail Adresse", placeholder="dein.name@smail.th-koeln.de"
                )
                login_status_msg = gr.Markdown("", visible=False)
                btn_request_code = gr.Button("Code anfordern", variant="primary")

                with gr.Group(visible=False) as code_input_group:
                    gr.Markdown("### Code eingeben")
                    login_code_input = gr.Textbox(
                        label="8-stelliger Code", placeholder="Code aus der E-Mail"
                    )
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
                share_podcast_title = gr.Markdown(
                    "### Teile 'Titel des Podcasts' mit anderen"
                )

                gr.Markdown("**Link:**")

                with gr.Row():
                    share_link_input = gr.Textbox(
                        label="",
                        placeholder="https\\...",
                        interactive=False,
                        show_label=False,
                        max_lines=1,
                        elem_id="share_link_output",
                    )
                    btn_copy_link = gr.Button("📋 Link Kopieren", scale=0)

                gr.Markdown("**Link Öffentlich/Privat machen**")
                share_link_toggle = gr.Checkbox(
                    label="Link öffentlich machen", value=False
                )

                share_status_msg = gr.Markdown("", visible=False)

                btn_cancel_share = gr.Button("Zurück")
            with gr.Column(scale=1):
                pass

    # Nutzungsbedingungen Page
    with gr.Column(visible=False) as nutzungs_page:
        gr.Markdown("# Nutzungsbedingungen des Podcast Generators")

        with gr.Row():
            with gr.Column(scale=1):
                pass
            with gr.Column(scale=10):
                gr.Markdown("""
                            ## ⚖️ Rechtliche Hinweise und Richtlinien

                            Herzlich willkommen beim **KI Podcast Generator**. Durch die Nutzung dieses Tools erklärst du dich mit den folgenden Bedingungen einverstanden. Bitte lies diese sorgfältig durch.

                            ---

                            ### 1. Zulässige Nutzung und Inhaltsbeschränkungen
                            Dieser Generator dient der Erstellung von Audio-Inhalten mittels künstlicher Intelligenz. Es ist streng untersagt, Inhalte zu generieren, die:
                            * **Hassrede oder Diskriminierung:** Personen oder Gruppen aufgrund von Rasse, Religion, Geschlecht, sexueller Orientierung oder Behinderung angreifen oder herabwürdigen.
                            * **Explizite Inhalte:** Pornografische, sexuell explizite oder jugendgefährdende Darstellungen enthalten.
                            * **Gewalt:** Gewalt verherrlichen, dazu aufrufen oder extremistische Propaganda verbreiten.
                            * **Rechtswidrigkeit:** Gegen geltendes deutsches Recht verstoßen oder zu Straftaten anleiten.

                            ### 2. Datenschutz und Privatsphäre
                            * **Keine personenbezogenen Daten:** Es ist untersagt, private Daten wie Klarnamen, Adressen, Telefonnummern oder andere sensible Informationen von dir oder Dritten in die Textfelder einzugeben oder hochzuladen.
                            * **Vertraulichkeit:** Lade keine Dokumente (PDFs) hoch, die Geschäftsgeheimnisse oder vertrauliche Informationen enthalten.
                            * **Speicherung:** Bitte beachte, dass dieses Projekt zu akademischen Zwecken dient. Gib keine Daten ein, die nicht für die Öffentlichkeit bestimmt sind.

                            ### 3. Urheberrecht und Verantwortung
                            * **Input:** Du bestätigst, dass du die Rechte an den hochgeladenen Texten/PDFs besitzt oder deren Nutzung für die Podcast-Erstellung rechtlich zulässig ist.
                            * **Output:** Die KI-generierten Stimmen und Inhalte sind als solche zu kennzeichnen. Eine Irreführung Dritter (z.B. Deepfakes zur Täuschung über die Identität einer realen Person) ist untersagt.
                            * **Haftung:** Das Team 04 und die TH Köln übernehmen keine Haftung für die Richtigkeit der generierten Inhalte oder für Schäden, die aus der Nutzung des Tools resultieren.

                            ### 4. Akademischer Rahmen
                            Dieses Tool ist im Rahmen eines Moduls an der **TH Köln** entstanden. Es handelt sich um einen Prototypen (Version 1.0). Die Verfügbarkeit des Dienstes kann jederzeit ohne Vorankündigung eingeschränkt oder eingestellt werden.

                            ---
                            *Durch die Nutzung des "Generate" Buttons bestätigst du, dass du diese Regeln verstanden hast und einhältst.*

                            **Version 1.0 | Team 04 | TH Köln**
                            """)

                btn_back_from_nutzungs = gr.Button("Zurück", variant="primary")
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
        nutzungs_page,
        share_page,
    ]

    # --- Events ---
    btn_goto_nutzungs.click(fn=lambda: handlers.navigate("nutzungs_page"), outputs=pages)
    btn_back_from_nutzungs.click(fn=lambda: handlers.navigate("home"), outputs=pages)

    btn_goto_uber.click(fn=lambda: handlers.navigate("uber_page"), outputs=pages)
    btn_back_from_uber.click(fn=lambda: handlers.navigate("home"), outputs=pages)

    # Share page events
    btn_cancel_share.click(
        fn=handlers.go_back_to_home,
        inputs=[current_user_state],
        outputs=pages + [podcast_list_state],
    )

    btn_copy_link.click(
        fn=handlers.copy_share_link, inputs=[share_link_input], outputs=[share_status_msg]
    )

    share_link_toggle.change(
        fn=handlers.toggle_link_visibility,
        inputs=[share_link_toggle],
        outputs=[share_status_msg],
    )

    btn_goto_login.click(
        fn=handlers.handle_login_click,
        inputs=[current_user_state],
        outputs=[current_user_state, btn_goto_login]
        + pages
        + [
            podcast_list_state,
            login_email_input,
            login_code_input,
            login_status_msg,
            code_input_group,
            btn_quelle,
        ],
    )

    btn_back_from_login.click(fn=lambda: handlers.navigate("home"), outputs=pages)
    btn_request_code.click(
        fn=handlers.handle_login_request,
        inputs=[login_email_input],
        outputs=[login_status_msg, code_input_group],
    )
    btn_verify_code.click(
        fn=handlers.handle_code_verify,
        inputs=[login_email_input, login_code_input],
        outputs=[login_status_msg, current_user_state, btn_goto_login]
        + pages
        + [btn_quelle],
    ).then(
        fn=handlers.refresh_podcasts_for_user,
        inputs=[current_user_state],
        outputs=[podcast_list_state],
    )

    # Skript generieren + Cancel
    skript_task = btn_skript_generieren.click(
        fn=handlers.validate_and_show_loading,
        inputs=[textbox_thema, source_url, file_upload],
        outputs=pages,
    ).then(
        fn=handlers.generate_script_wrapper,
        inputs=[
            textbox_thema,
            dropdown_dauer,
            dropdown_sprache,
            dropdown_speaker1,
            dropdown_role1,
            dropdown_speaker2,
            dropdown_role2,
            source_preview,
            source_url,
            file_upload,
        ],
        outputs=[text] + pages + [textbox_thema],
    )

    btn_cancel_skript.click(
        fn=lambda: handlers.navigate("home"),
        inputs=None,
        outputs=pages,
        cancels=skript_task,
    )

    btn_zuruck_skript.click(fn=lambda: handlers.navigate("home"), outputs=pages)

    podcast_task = btn_podcast_generieren.click(
        fn=lambda: handlers.navigate("loading podcast"),
        outputs=pages,
    ).success(
        fn=handlers.run_audio_gen,
        inputs=[
            text,
            textbox_thema,
            dropdown_dauer,
            dropdown_sprache,
            dropdown_speaker1,
            dropdown_speaker2,
            dropdown_role1,
            dropdown_role2,
            current_user_state,
        ],
        outputs=pages
        + [
            audio_player,
            podcast_list_state,
            player_title_display,
            current_podcast_state,
            btn_download_finish,
            btn_share_finish,
            btn_delete_finish,
        ],
    )

    btn_cancel_podcast.click(
        fn=lambda: handlers.navigate("skript bearbeiten"),
        inputs=None,
        outputs=pages,
        cancels=podcast_task,
    )

    btn_delete_finish.click(
        fn=handlers.handle_delete_finish,
        inputs=[current_podcast_state, current_user_state],
        outputs=[podcast_list_state],
    ).then(fn=lambda: handlers.navigate("home"), outputs=pages)

    btn_share_finish.click(
        fn=handlers.handle_share_click,
        inputs=[current_podcast_state],
        outputs=pages + [share_podcast_title, share_link_input],
    )

    btn_zuruck_audio.click(
        fn=handlers.navigate_home_and_refresh_podcasts,
        inputs=[current_user_state],
        outputs=pages + [podcast_list_state],
    )

    demo.load(
        fn=handlers.refresh_podcasts_for_user,
        inputs=[current_user_state],
        outputs=[podcast_list_state],
    )


if __name__ == "__main__":
    demo.queue().launch()