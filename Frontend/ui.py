# NOTE: Benutzeroberfläche (Gradio Frontend)
# Definiert das Layout und die Interaktionselemente der Web-Applikation.

import gradio as gr
import sys
import os

# Ensure we can import from team04
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from team04.services.workflow import PodcastWorkflow

workflow = PodcastWorkflow()
available_voices = workflow.get_voices()
available_voices_2 = available_voices + ["Keine"]


def navigate(target):
    page_names = ["home", "skript bearbeiten", "deine podcasts", "audio player", "loading script", "loading podcast"]
    results = []

    for page in page_names:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))

    return tuple(results)


def navigate_and_refresh_podcasts():
    # Fetch fresh data directly from workflow
    data = workflow.get_podcasts_data()
    # Update navigation AND the state variable for the list
    return navigate("deine podcasts") + (data,)


def get_audio_url_by_row_index_wrapper(row_index):
    path = workflow.get_audio_path_by_index(row_index)
    if path:
        return os.path.abspath(path)
    return path


def on_click_row(value):
    # value is the row data when clicked
    if isinstance(value, dict) and 'index' in value:
        idx = value['index']
    else:
        idx = 0
    url = get_audio_url_by_row_index_wrapper(idx)
    print(f"Selected audio path: {url}")
    return url


def on_play_click(audio_path):
    nav_updates = navigate("audio player")
    # Resolve absolute path for the player
    full_path = os.path.abspath(audio_path) if audio_path else None
    return nav_updates + (gr.update(value=full_path, autoplay=True),)


# ✅ FIX: "Keine" -> None + speakers korrekt (1 oder 2)
def generate_script_wrapper(thema, dauer, sprache, speaker1, speaker2):
    # Zweitstimme bereinigen
    if not speaker2 or speaker2 == "Keine" or speaker2 == speaker1:
        speaker2 = None

    speakers = 2 if speaker2 else 1

    return workflow._generate_script(
        thema=thema,
        sprache=sprache,
        dauer=int(dauer),
        speakers=speakers,
        roles={},
        hauptstimme=speaker1,
        zweitstimme=speaker2
    )


# ❗ Diese Funktion war bei dir unvollständig.
# Du kannst sie entfernen oder ignorieren; wir nutzen run_audio_gen.
def generate_audio_wrapper(script_text, thema, dauer, sprache, speaker1, speaker2):
    return workflow.generate_audio_step(
        script_text=script_text,
        thema=thema,
        dauer=int(dauer),
        sprache=sprache,
        hauptstimme=speaker1,
        zweitstimme=speaker2
    )


# ✅ FIX: Auch beim Audio "Keine" -> None
def run_audio_gen(script_text, thema, dauer, sprache, s1, s2):
    if not s2 or s2 == "Keine" or s2 == s1:
        s2 = None

    return workflow.generate_audio_step(script_text, thema, int(dauer), sprache, s1, s2)


def get_podcasts_wrapper():
    return workflow.get_podcasts()


def get_loader_html(message):
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
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>
    """


with gr.Blocks() as demo:
    audio_state = gr.State()
    podcast_list_state = gr.State(workflow.get_podcasts_data())

    gr.Markdown("# KI Podcast Generator")

    with gr.Column(visible=True) as home:
        gr.Markdown("""
                    ## Wilkommen beim KI Poscast Generator! 
                    ### Gib einfach dein Thema ein, lade einen Text oder eine PDF-Datei hoch, wähle die Sprache und die Sprecher - und lass die KI einen professionellen Podcast für dich erstellen.
                    """)

        with gr.Row():
            dropdown_dauer = gr.Dropdown(
                choices=["1", "2", "3", "4", "5"],
                label="Dauer",
                value="1",
                multiselect=False,
                interactive=True
            )

            dropdown_sprache = gr.Dropdown(
                choices=["Deutsch", "English"],
                label="Sprache",
                value="Deutsch",
                multiselect=False,
                interactive=True
            )

        with gr.Row():
            dropdown_speaker1 = gr.Dropdown(
                choices=available_voices,
                label="Hauptstimme",
                value=available_voices[0] if available_voices else None,
                interactive=True
            )
            dropdown_speaker2 = gr.Dropdown(
                choices=available_voices_2,
                label="Zweitstimme",
                value=available_voices[1] if len(available_voices) > 1 else "Keine",
                interactive=True
            )

        textbox_thema = gr.Textbox(
            label="Thema",
            placeholder="Geben Sie das Thema ein...",
            lines=5,
            interactive=True
        )

        btn_skript_generieren = gr.Button("Skript Generieren")

    # Skript Bearbeiten page
    with gr.Column(visible=False) as skript_bearbeiten:
        gr.Markdown("## Skript Bearbeiten")

        text = gr.Textbox(
            label="Podcast Skript",
            placeholder="Hier wird der generierte Podcast Skript angezeigt...",
            lines=15,
            interactive=True
        )

        gr.Markdown("""
                    ### Bearbeite das Skript:
                    Du kannst den generierten Text hier anpassen, bevor er in den Podcsat umgewandelt wird.
                    """)

        with gr.Row():
            btn_zuruck_skript = gr.Button("Zurück")
            btn_podcast_generieren = gr.Button("Podcast Generieren")

    # Deine Podcasts page
    with gr.Column(visible=False) as deine_podcasts:
        gr.Markdown("# Deine Podcasts")

        # Dynamic rendering of cards
        @gr.render(inputs=podcast_list_state)
        def render_podcasts(podcasts):
            if not podcasts:
                gr.Markdown("Noch keine Podcasts vorhanden.")
                return

            for p in podcasts:
                with gr.Group():
                    with gr.Row(variant="panel", equal_height=True):
                        with gr.Column(scale=4):
                            gr.Markdown(f"### {p['titel']}")
                            gr.Markdown(f"📅 {p['datum']} | ⏱️ {p['dauer']} Min")

                        with gr.Column(scale=1, min_width=120):
                            btn_card_play = gr.Button("▶ Play", variant="primary", size="sm")

                            # Bind click directly to this podcast's path
                            btn_card_play.click(
                                fn=on_play_click,
                                inputs=[gr.State(p['path'])],
                                outputs=pages + [audio_player]
                            )

        with gr.Row():
            btn_zuruck_deinepodcasts = gr.Button("Zurück")

    # Audio Player page
    with gr.Column(visible=False) as audio_player_page:
        gr.Markdown("## Audio Player")
        audio_player = gr.Audio(label="Dein generierter Podcast", type="filepath")
        btn_zuruck_audio = gr.Button("Zurück zu Deinen Podcasts")

    # Script loading page
    with gr.Column(visible=False) as loading_page_script:
        spinner_html = get_loader_html("Das Skript wird generiert...")
        gr.HTML(spinner_html)

    with gr.Column(visible=False) as loading_page_podcast:
        spinner_html = get_loader_html("Der Podcast wird generiert...")
        gr.HTML(spinner_html)

    pages = [home, skript_bearbeiten, deine_podcasts, audio_player_page, loading_page_script, loading_page_podcast]

    btn_zuruck_deinepodcasts.click(
        fn=lambda: navigate("skript bearbeiten"),
        inputs=None,
        outputs=pages
    )

    btn_zuruck_skript.click(
        fn=lambda: navigate("home"),
        inputs=None,
        outputs=pages
    )

    btn_skript_generieren.click(
        fn=lambda: navigate("loading script"),
        inputs=None,
        outputs=pages,
    ).then(
        fn=generate_script_wrapper,
        inputs=[textbox_thema, dropdown_dauer, dropdown_sprache, dropdown_speaker1, dropdown_speaker2],
        outputs=text
    ).success(
        fn=lambda: navigate("skript bearbeiten"),
        inputs=None,
        outputs=pages
    )

    btn_podcast_generieren.click(
        fn=lambda: navigate("loading podcast"),
        inputs=None,
        outputs=pages
    ).success(
        fn=run_audio_gen,
        inputs=[text, textbox_thema, dropdown_dauer, dropdown_sprache, dropdown_speaker1, dropdown_speaker2],
        outputs=None
    ).success(
        fn=navigate_and_refresh_podcasts,
        inputs=None,
        outputs=pages + [podcast_list_state]
    )

    btn_zuruck_audio.click(
        fn=lambda: navigate("deine podcasts"),
        inputs=None,
        outputs=pages
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch()
