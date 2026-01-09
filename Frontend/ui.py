import gradio as gr
import sys
import os
import time

# -------------------------------------------------------------------------
# Pfad-Konfiguration
# -------------------------------------------------------------------------
# Fügt das Hauptverzeichnis dem Systempfad hinzu, damit Module wie 'team04' importiert werden können.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from team04.services.workflow import PodcastWorkflow

# -------------------------------------------------------------------------
# Initialisierung
# -------------------------------------------------------------------------
# Erstellt eine Instanz des Podcast-Workflows, der die Logik für Skript- und Audio-Erstellung enthält.
workflow = PodcastWorkflow()

# Lädt die verfügbaren Stimmen direkt beim Start der Anwendung.
available_voices = workflow.get_voices()
# Erstellt eine zweite Liste für die Zweitstimme, die auch "Keine" als Option enthält.
available_voices_2 = available_voices + ["Keine"]

# -------------------------------------------------------------------------
# Hilfsfunktionen (UI & Status)
# -------------------------------------------------------------------------
def create_status_html(message, status_type="processing"):
    """
    Erzeugt einen HTML-String für eine Status-Benachrichtigung (z.B. Erfolg, Fehler, Ladebalken).

    Args:
        message (str): Der anzuzeigende Text.
        status_type (str): Der Typ des Status ('processing', 'success', 'error').

    Returns:
        str: HTML-Code für die Status-Box.
    """
    # Farb-Definitionen für verschiedene Status-Zustände (Hintergrund, Text)
    styles = {
        "processing": ("#FF9800", "#FFFFFF"), # Orange für Prozesse
        "success":    ("#4CAF50", "#FFFFFF"), # Grün für Erfolg
        "error":      ("#F44336", "#FFFFFF")  # Rot für Fehler
    }

    bg_color, text_color = styles.get(status_type, styles["processing"])

    return f"""
    <div style="
        background-color: {bg_color};
        color: {text_color};
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 1.1em;
        margin: 15px 0;
        font-family: sans-serif;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        {message}
    </div>
    """

def hide_status_delayed():
    """
    Wartet 5 Sekunden und gibt dann ein Update zurück, um die Status-Box auszublenden.
    Wird nach Abschluss einer Aktion verwendet, damit die Erfolgsmeldung nicht ewig stehen bleibt.
    """
    time.sleep(5)
    return gr.update(visible=False)

def get_latest_podcasts():
    """
    Lädt die aktuelle Liste der generierten Podcasts aus dem Workflow.
    """
    return workflow.get_podcasts_data()

# -------------------------------------------------------------------------
# Prozess-Logik (Backend-Verbindung)
# -------------------------------------------------------------------------

def process_script_generation(thema, dauer, sprache, s1, s2):
    """
    Ruft den Workflow auf, um ein Skript basierend auf dem Thema zu generieren.
    """
    try:
        # Aufruf der eigentlichen Generierungs-Logik im Backend
        script_content = workflow.generate_script_step(thema, int(dauer), sprache, s1, s2)

        # Erfolgsmeldung vorbereiten
        success_html = create_status_html("✅ Skript erfolgreich generiert!", "success")

        # UI-Updates zurückgeben: Status anzeigen, Skript-Bereich anzeigen, Skript-Text setzen
        return {
            status_box: gr.update(visible=True, value=success_html),
            script_area: gr.update(visible=True),
            txt_script: script_content
        }
    except Exception as e:
        # Fehlermeldung bei Problemen
        error_html = create_status_html(f"❌ Fehler: {str(e)}", "error")
        return {
            status_box: gr.update(visible=True, value=error_html),
            script_area: gr.update(visible=False),
            txt_script: ""
        }

def process_audio_generation(script, thema, dauer, sprache, s1, s2):
    """
    Ruft den Workflow auf, um aus dem (ggf. bearbeiteten) Skript das Audio zu erzeugen.
    """
    try:
        # Audio-Generierung anstoßen
        workflow.generate_audio_step(script, thema, int(dauer), sprache, s1, s2)

        # Podcast-Liste aktualisieren, damit die neue Datei angezeigt wird
        new_list = get_latest_podcasts()

        success_html = create_status_html("✅ Podcast erfolgreich erstellt!", "success")

        return {
            status_box: gr.update(visible=True, value=success_html),
            podcast_list_state: new_list
        }
    except Exception as e:
        error_html = create_status_html(f"❌ Fehler: {str(e)}", "error")
        return {
            status_box: gr.update(visible=True, value=error_html),
            podcast_list_state: gr.NoValue()
        }

# -------------------------------------------------------------------------
# UI Event Handler (Zwischenschritte für Feedback)
# -------------------------------------------------------------------------

def start_script_gen():
    """Zeigt sofort 'Laden...' an, während das Skript generiert wird."""
    html = create_status_html("⏳ Skript wird generiert... Bitte warten.", "processing")
    return {
        status_box: gr.update(visible=True, value=html),
        script_area: gr.update(visible=False)
    }

def start_audio_gen():
    """Zeigt sofort 'Laden...' an, während das Audio generiert wird."""
    html = create_status_html("🎙️ Podcast wird aufgenommen... Das kann einen Moment dauern.", "processing")
    return {
        status_box: gr.update(visible=True, value=html),
        script_area: gr.update(visible=False)
    }

# -------------------------------------------------------------------------
# Haupt-UI Aufbau (Gradio Blocks)
# -------------------------------------------------------------------------
with gr.Blocks() as demo:

    # State-Variable für die Podcast-Liste (damit sie dynamisch aktualisiert werden kann)
    podcast_list_state = gr.State(get_latest_podcasts())

    gr.Markdown("# KI Podcast Generator")

    # --- Bereich 1: Einstellungen & Eingabe ---
    with gr.Column():
        gr.Markdown("""
                    ## Willkommen beim KI Podcast Generator!
                    ### Gib einfach dein Thema ein, wähle die Sprache und die Sprecher - und lass die KI einen professionellen Podcast für dich erstellen.
                    """)

        with gr.Row():
            dd_dauer = gr.Dropdown(choices=["1", "2", "3", "4", "5"], label="Dauer (Minuten)", value="1", interactive=True)
            dd_sprache = gr.Dropdown(choices=["Deutsch"], label="Sprache", value="Deutsch", interactive=True)

        with gr.Row():
            dd_s1 = gr.Dropdown(choices=available_voices, label="Hauptstimme", value=available_voices[0] if available_voices else None, interactive=True)
            dd_s2 = gr.Dropdown(choices=available_voices_2, label="Zweitstimme", value="Keine", interactive=True)

        txt_thema = gr.Textbox(label="Thema", placeholder="Worüber soll der Podcast handeln?", lines=5, interactive=True)

        btn_gen_script = gr.Button("Skript Generieren", variant="primary")

    # --- Bereich 2: Dynamische Status- und Ergebnis-Anzeige ---

    # Platzhalter für Status-Meldungen (Erfolg/Fehler/Laden)
    status_box = gr.HTML(visible=False)

    # Gruppe für Skript-Anzeige (erst sichtbar nach Generierung)
    with gr.Group(visible=False) as script_area:
        gr.Markdown("### Skript Bearbeiten")
        txt_script = gr.Textbox(label="Generiertes Podcast Skript", lines=15, interactive=True)
        gr.Markdown("_Du kannst den generierten Text hier anpassen, bevor er in Audio umgewandelt wird._")
        btn_gen_audio = gr.Button("Podcast Generieren (Audio)", variant="primary")

    # --- Bereich 3: Historie / Ergebnis-Liste ---
    gr.Markdown("---")
    gr.Markdown("## Deine bisherigen Podcasts")

    # Dieser Decorator sorgt dafür, dass die Liste neu gerendert wird, wenn sich 'podcast_list_state' ändert
    @gr.render(inputs=podcast_list_state)
    def render_podcasts(podcasts):
        if not podcasts:
            gr.Markdown("_Noch keine Podcasts vorhanden._")
            return

        # Iteriert durch die Podcasts und zeigt Player sowie Metadaten an
        for p in podcasts:
            with gr.Group():
                with gr.Row(variant="panel", equal_height=True):
                    with gr.Column(scale=4):
                        gr.Markdown(f"### {p['titel']}")
                        gr.Markdown(f"📅 {p['datum']} | ⏱️ {p['dauer']} Min")
                    with gr.Column(scale=3):
                        if p['path'] and os.path.exists(p['path']):
                            gr.Audio(value=p['path'], type="filepath", show_label=False)
                        else:
                            gr.Markdown("_Datei nicht gefunden_")

    # -------------------------------------------------------------------------
    # Event-Verkettung (Click Handler)
    # -------------------------------------------------------------------------

    # Ablauf: Klick -> Lade-Status zeigen -> Skript generieren -> Status ausblenden
    btn_gen_script.click(
        fn=start_script_gen,
        outputs=[status_box, script_area],
        show_progress="hidden"
    ).then(
        fn=process_script_generation,
        inputs=[txt_thema, dd_dauer, dd_sprache, dd_s1, dd_s2],
        outputs=[status_box, script_area, txt_script],
        show_progress="hidden"
    ).then(
        fn=hide_status_delayed,
        inputs=None,
        outputs=[status_box]
    )

    # Ablauf: Klick -> Lade-Status zeigen -> Audio generieren -> Status ausblenden & Liste aktualisieren
    btn_gen_audio.click(
        fn=start_audio_gen,
        outputs=[status_box, script_area],
        show_progress="hidden"
    ).then(
        fn=process_audio_generation,
        inputs=[txt_script, txt_thema, dd_dauer, dd_sprache, dd_s1, dd_s2],
        outputs=[status_box, podcast_list_state],
        show_progress="hidden"
    ).then(
        fn=hide_status_delayed,
        inputs=None,
        outputs=[status_box]
    )

# Start der Applikation
if __name__ == "__main__":
    demo.launch()