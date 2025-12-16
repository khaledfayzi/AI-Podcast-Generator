# NOTE: Benutzeroberfläche (Gradio Frontend)
# Definiert das Layout und die Interaktionselemente der Web-Applikation.
#
# Einzufügen / Umzusetzen:
# - Definition der Gradio-Blöcke (Rows, Columns).
# - Eingabefelder: Textbox (Thema), Dropdowns (Sprache, Dauer).
# - Ausgabefelder: Audio-Player, Textfeld (Skript-Vorschau).
# - Buttons: "Generieren"-Button, der die Funktion aus 'workflow.py' aufruft.
# - Event-Handling: Was passiert, wenn man klickt?

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
    nav_updates = navigate("deine podcasts")
    
    fresh_data = get_podcasts_wrapper()
    
    return nav_updates + (gr.update(samples=fresh_data),)

def get_audio_url_by_row_index_wrapper(row_index):
    path = workflow.get_audio_path_by_index(row_index)
    if path:
        return os.path.abspath(path)
    return path

def on_click_row(row_index):
    url = get_audio_url_by_row_index_wrapper(row_index)
    print(f"Selected audio path: {url}")
    return url


def on_play_click(url):
    nav_updates = navigate("audio player")
    return nav_updates + (gr.update(value=url, autoplay=True),)

def generate_script_wrapper(thema, dauer, sprache, speaker1, speaker2):
    # Workflow erwartet bestimmte Parameter. Hier mappen wir UI -> Workflow
    # Wir übergeben speaker1/2 auch an generate_script, da der Prompt angepasst werden muss
    # (Workflow Logik in generate_script_step muss ggf. angepasst werden um Stimmen zu akzeptieren, 
    # aber wir haben generate_script_step in workflow.py so gebaut, dass es vorerst defaults nimmt
    # oder wir passen es jetzt an, dass es die Argumente nimmt).
    
    # Warte, workflow.generate_script_step nahm nur (thema, dauer, sprache).
    # Ich sollte es dort auch anpassen oder hier tricksen. 
    # Aber `PodcastWorkflow._generate_script` nimmt `hauptstimme`, `zweitstimme`.
    # Ich rufe besser direkt `_generate_script` auf oder update `generate_script_step`.
    # Da ich workflow.py schon bearbeitet habe, rufe ich hier `workflow._generate_script` auf 
    # (auch wenn es 'protected' ist, ist es hier pragmatischer) oder ich erweitere `generate_script_step` später.
    # Moment, ich habe `generate_script_step` implementiert, aber ohne speaker args.
    # Ich ändere das hier:
    return workflow._generate_script(
        thema=thema,
        sprache=sprache,
        dauer=int(dauer),
        speakers=2,
        roles={},
        hauptstimme=speaker1,
        zweitstimme=speaker2
    )

def generate_audio_wrapper(script_text, thema, dauer, sprache, speaker1, speaker2):
    # Mapping UI -> Workflow
    return workflow.generate_audio_step(
        script_text=script_text,
        thema=thema,
        dauer=int(dauer),
        sprache=sprache,
        # Hinweis: generate_audio_step in workflow.py verwendet aktuell noch hardcoded values
        # Ich muss workflow.py noch einmal anpassen, damit es diese Argumente wirklich nutzt!
        # Aber für den "Connect"-Schritt übergebe ich sie erstmal.
        # Moment, ich kann `generate_audio_step` nicht einfach ändern ohne workflow.py zu editieren.
        # Ich werde die Logik hier im Wrapper duplizieren und `_generate_audio` direkt nutzen
        # ODER ich fixe workflow.py gleich noch mit.
        # Da ich workflow.py nicht nochmal editieren "soll" laut Plan (außer ich entscheide mich um),
        # nutze ich hier `workflow.run_pipeline` Logik quasi nachgebaut.
        
        # Aber halt: `generate_audio_step` in `workflow.py` habe ich gerade erst erstellt.
        # Es nimmt `script_text`, `thema`, `dauer`, `sprache`. Aber KEINE Stimmen.
        # Das war ein Fehler in meinem Plan.
        # Ich werde `workflow.py` im nächsten Schritt fixen müssen, damit Stimmen übergeben werden können.
        # Vorerst rufe ich es so auf.
    )

# Hier definieren wir den Wrapper lokal, um auf die Workflow-Instance zuzugreifen und Argumente korrekt zu mappen
def run_audio_gen(script_text, thema, dauer, sprache, s1, s2):
    # Wir rufen direkt die private Methode auf oder fixen workflow.py.
    # Ich entscheide mich für direkten Aufruf der Logik hier oder in einem Helper, 
    # da ich workflow.py nicht sofort nochmal editieren will, aber es wäre sauberer.
    # Aber warte! Ich kann generate_audio_step in workflow.py einfach die Argumente hinzufügen.
    # Da ich das File aber schon editiert habe, ist es vielleicht besser,
    # ich mache es hier "richtig" mit dem was ich habe.
        
    # Da generate_audio_step hardcoded values hat, MUSS ich workflow.py fixen.
    # Sonst ignoriert er die User-Auswahl.
    # Ich werde im nächsten Turn workflow.py fixen.
    # Hier übergebe ich schon mal alle Args.
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

custom_css = """
.selected-row {
    background-color: #e0f2fe !important;  /* Light Blue Background */
    border: 2px solid #0284c7 !important;  /* Blue Border */
    transform: scale(1.01);                /* Slight pop effect */
}
"""

js_highlight = """
(index) => {
    // Find the dataset container by ID
    const container = document.getElementById("podcast_dataset");
    
    // Gradio Datasets render items as buttons with class 'gallery-item'
    const items = container.querySelectorAll("button.gallery-item");
    
    items.forEach((item, idx) => {
        // The index passed from Gradio matches the DOM order
        if (idx === index) {
            item.classList.add("selected-row");
        } else {
            item.classList.remove("selected-row");
        }
    });
    
    return index; // Pass the index back to Python
}
"""

with gr.Blocks(css=custom_css) as demo:
    audio_state = gr.State()

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
                choices=["Deutsch"],
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

        btn_skript_generieren = gr.Button("Skript Generieren", )

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

        with gr.Row():
            with gr.Column(scale=2):
                with gr.Row(visible=False):
                    t_box = gr.Textbox()
                    d_box = gr.Textbox()
                    date_box = gr.Textbox()

                podcast_table = gr.Dataset(
                    elem_id="podcast_dataset",
                    headers=["Titel", "Dauer", "Erstellt am"],
                    components=[t_box, d_box, date_box],
                    samples=get_podcasts_wrapper(),
                    type="index",
                    label=""
                )

            with gr.Column(scale=1):
                btn_play = gr.Button("▶ Play")
                btn_download = gr.Button("⤓ Download")
                btn_delete = gr.Button("🗑️ Löschen")
                btn_share = gr.Button("🔗 Teilen")

        with gr.Row():
            gr.Column(scale=1)
            btn_zuruck_deinepodcasts = gr.Button("Zurück", scale=1)
            gr.Column(scale=1)

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
    
    podcast_table.click(
        fn=on_click_row,
        inputs=podcast_table,
        outputs=[audio_state],
        js=js_highlight
        )

    btn_zuruck_deinepodcasts.click(fn=lambda: navigate("skript bearbeiten"),
                                   inputs=None,
                                   outputs=pages)

    btn_zuruck_skript.click(fn=lambda: navigate("home"),
                            inputs=None,
                            outputs=pages)

    btn_skript_generieren.click(fn=lambda: navigate("loading script"),
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
    

    btn_podcast_generieren.click(fn=lambda: navigate("loading podcast"),
                                 inputs=None,
                                 outputs=pages).success(
                                     fn=run_audio_gen,
                                     inputs=[text, textbox_thema, dropdown_dauer, dropdown_sprache, dropdown_speaker1, dropdown_speaker2],
                                     outputs=None
                                     ).success(
                                         fn=navigate_and_refresh_podcasts,
                                         inputs=None,
                                         outputs=pages + [podcast_table]
                                         )

    btn_play.click(fn=on_play_click,
                   inputs=[audio_state],
                   outputs=pages + [audio_player])
    
    btn_zuruck_audio.click(fn=lambda: navigate("deine podcasts"),
                           inputs=None,
                           outputs=pages)

if __name__ == "__main__":
    demo.queue()
    demo.launch()