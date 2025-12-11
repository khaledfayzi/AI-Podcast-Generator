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

def navigate(target):
    pages_names = ["home", "skript bearbeiten", "deine podcasts", "audio player"]
    results = []

    for page in pages_names:
        if page == target:
            results.append(gr.update(visible=True))
        else:
            results.append(gr.update(visible=False))

    return tuple(results)


with gr.Blocks() as demo:
    gr.Markdown("# KI Podcast Generator")

    with gr.Column(visible=True) as home:
        gr.Markdown("""
                    ## Wilkommen beim KI Poscast Generator! 
                    ### Gib einfach dein Thema ein, lade einen Text oder eine PDF-Datei hoch, wähle die Sprache und die Sprecher - und lass die KI einen professionellen Podcast für dich erstellen.
                    """)
        
        with gr.Row():
            dropdown_dauer = gr.Dropdown(
            choices=["15", "30","45", "60"],
            label="Dauer",
            value="15",  
            multiselect=False,
            interactive=True
            )

            dropdown_sprache = gr.Dropdown(
            choices=["Deutsch", "Englisch"],
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
                gr.Markdown("""
                            **Titel von Podcast**  
                            Ein KI-generierter Podcast auf Deutsch.
                            """)

            with gr.Column(scale=1):
                btn_play = gr.Button("▶ Play")
                btn_download = gr.Button("⤓ Download")
                btn_delete = gr.Button("🗑️ Löschen")
                btn_share = gr.Button("🔗 Teilen")

        with gr.Row():
            gr.Column(scale=1)
            btn_zuruck_deinepodcasts = gr.Button("Zurück", scale=1)
            gr.Column(scale=1)


    with gr.Column(visible =False) as audio_player_col:
        gr.Markdown("## Audio Player")
        audio_player = gr.Audio(label="Dein generierter Podcast", type="filepath")

        
    pages = [home, skript_bearbeiten, deine_podcasts, audio_player_col]

    btn_zuruck_deinepodcasts.click(fn=lambda: navigate("skript bearbeiten"),
                                   inputs=None,
                                   outputs=pages)

    btn_zuruck_skript.click(fn=lambda: navigate("home"),
                            inputs=None,
                            outputs=[home, skript_bearbeiten, deine_podcasts, audio_player_col])
        
    btn_skript_generieren.click(fn=lambda: navigate("skript bearbeiten"),
                                inputs=None,
                                outputs=[home, skript_bearbeiten, deine_podcasts, audio_player_col])
    
    btn_podcast_generieren.click(fn=lambda: navigate("deine podcasts"),
                                 inputs=None,
                                 outputs=[home, skript_bearbeiten, deine_podcasts, audio_player_col])
    
    btn_play.click(fn=lambda: navigate("audio player"),
                   inputs=None,
                   outputs=[home, skript_bearbeiten, deine_podcasts, audio_player_col])

demo.launch()
