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
from mock_backendUi import *

def navigate(target):
    pages_names = ["home", "skript bearbeiten", "deine podcasts", "audio player", "loading script", "loading podcast"]
    results = []

    for page in pages_names:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))

    return tuple(results)

def on_click_row(row_index):
    url = get_audio_url_by_row_index(row_index)
    
    return url

def on_play_click(url):
    nav_updates = navigate("audio player")
    
    return nav_updates + (gr.update(value=url, autoplay=True),)

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

    gr.Markdown("# KI Podcast Generator")

    with gr.Column(visible=True) as home:
        gr.Markdown("""
                    ## Wilkommen beim KI Poscast Generator! 
                    ### Gib einfach dein Thema ein, lade einen Text oder eine PDF-Datei hoch, wähle die Sprache und die Sprecher - und lass die KI einen professionellen Podcast für dich erstellen.
                    """)
        
        with gr.Row():
            dropdown_dauer = gr.Dropdown(
            choices=["1", "2","3", "4", "5"],
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

        textbox_thema = gr.Textbox(
            label="Thema",
            placeholder="Geben Sie das Thema ein...",
            lines=5,
            interactive=True
        )

        btn_skript_generieren = gr.Button("Skript Generieren",)
        
    # Skript Bearbeiten page
    with gr.Column(visible =False) as skript_bearbeiten:
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
    with gr.Column(visible =False) as deine_podcasts:
        gr.Markdown("# Deine Podcasts")

        with gr.Row():
            with gr.Column(scale=2):

                with gr.Row(visible=False):
                    t_box = gr.Textbox()
                    d_box = gr.Textbox()
                    date_box = gr.Textbox()

                podcast_table = gr.Dataset(
                    headers=["Titel", "Dauer", "Erstellt am"],
                    components=[t_box, d_box, date_box],
                    samples=get_podcasts(),
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
    with gr.Column(visible =False) as audio_player_col:
        gr.Markdown("## Audio Player")
        audio_player = gr.Audio(label="Dein generierter Podcast", type="filepath")

    # Script loading page
    with gr.Column(visible=False) as loading_page_script:
        spinner_html = get_loader_html("Das Skript wird generiert...")
        
        gr.HTML(spinner_html)

    with gr.Column(visible=False) as loading_page_podcast:
        spinner_html = get_loader_html("Der Podcast wird generiert...")
        
        gr.HTML(spinner_html)    
    
    podcast_table.click(
        fn=on_click_row,
        inputs=podcast_table,
        outputs=[audio_state]
    )
    
    pages = [home, skript_bearbeiten, deine_podcasts, audio_player_col, loading_page_script, loading_page_podcast]

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
                                    fn=generate_script,
                                    inputs=[textbox_thema, dropdown_dauer, dropdown_sprache],
                                    outputs=text
                                    ).success(
                                        fn=lambda: navigate("skript bearbeiten"),
                                        inputs=None,
                                        outputs=pages
                                        )         
    
    btn_podcast_generieren.click(fn=lambda: navigate("loading podcast"),
                                inputs=None,
                                outputs=pages,).success(
                                    fn=generate_audio,
                                    inputs=[text],
                                    outputs=None
                                    ).success(
                                        fn=lambda: navigate("deine podcasts"),
                                        inputs=None,
                                        outputs=pages
                                        )
    
    btn_play.click(fn=on_play_click,
                   inputs=[audio_state],
                   outputs=pages + [audio_player])

demo.queue()
demo.launch()