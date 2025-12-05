# NOTE: LLM Service (Textgenerierung)
# Kapselt die Logik für die Interaktion mit Sprachmodellen (Large Language Models).
# Hier findet das Prompt Engineering statt.
#
# Einzufügen / Umzusetzen:
# - Klasse 'LLMService':
#   - Methode 'generate_script(prompt, language, ...)'
#   - MVP: Simuliert erst einmal nur die Antwort (Dummy-Text), um Kosten zu sparen.
#   - Später: Sendet den Prompt an die OpenAI API und gibt das bereinigte Skript zurück.
#   - Trennung von System-Prompt (Rollenbeschreibung) und User-Prompt.

from .exceptions import LLMServiceError
import requests
import os

class LLMService:
    """
        Service für Textgenerierung mit einem Sprachmodell.
        - Baut System- und User-Prompts
        - Sendet Anfrage an Gemini
        - Gibt reinen Podcast-Text zurück
    """

    def __init__(self, model: str = "models/gemini-2.5-flash",use_dummy=False):
        """
        Initialisiert den Service.
        model_name: welches gemini modell benutzt wird
        use_dummy: wenn True → KI wird NICHT gefragt, Dummy-Text wird benutzt
        """
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMServiceError("Umgebungsvariable LLM_API_KEY fehlt.")

        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1/{self.model}:generateContent?key={self.api_key}"
        self.use_dummy=use_dummy

    # ---------------------------------------------------------
    # SYSTEM PROMPT
    # ---------------------------------------------------------
    def _system_prompt(self) -> str:
        """
        Baut den System-Prompt.
        Dieser beschreibt der KI *wie* sie schreiben soll.
        (Sprache, Schreibstil)
        """

        return (
            "Du bist ein professioneller deutscher Podcast-Autor.\n"
            "Regeln:\n"
            "- Schreibe ausschließlich auf Deutsch.\n"
            "- Jede Sprecherzeile darf höchstens 1–2 Sätze enthalten.\n"
            "- Verwende kurze, klare Sprecherabschnitte für eine natürliche TTS-Stimme.\n"
            "- Keine langen Monologe: längere Inhalte in mehrere Sprecherzeilen aufteilen.\n"
            "- Nur Sprecherlabels 'M:' (Moderator) und 'F:' (Frau/Expertin).\n"
            "- Keine Regieanweisungen wie [Musik], [Intro], [Klatschen].\n"
            "- Kein Markdown, keine Listen, keine Bullet-Points.\n"
            "- Nur normaler Text.\n"
            "- Emotionen nur als (lacht) oder (seufzt).\n"
            "- Der Text muss TTS-freundlich sein.\n"
            "WICHTIG: Die Ausgabe MUSS diese drei Überschriften enthalten – exakt so geschrieben:\n"
            "INTRO\n"
            "HAUPTTEIL\n"
            "OUTRO\n"
            "Wenn eine dieser drei Überschriften fehlt, ist die Ausgabe UNGÜLTIG.\n"
    )

    def _dummy_output(self, thema: str):
        """
        Gibt Test-Text zurück, falls kein echtes KI-Modell genutzt wird.
        Hilfreich für lokale Tests ohne KI.
        """
        return (
            f"INTRO\nDummy Podcast über {thema}.\n"
            f"HAUPTTEIL\nDies ist eine Testausgabe.\n"
            f"OUTRO\nDas war unser Podcast – bis zum nächsten Mal!"
        )


    # ---------------------------------------------------------
    # USER PROMPT
    # ---------------------------------------------------------
    def _user_prompt(self, thema: str, config: dict) -> str:
        """
        Baut den User-Prompt.
        Dieser enthält *was* geschrieben werden soll:
        Thema, Dauer, Sprecher, PDF-Inhalt usw.
        """
        dauer = config.get("dauer", 2)
        speakers = config.get("speakers", 2)
        wortzahl = dauer * 150  

        base = (
            f"Erstelle ein Podcast-Skript zum Thema '{thema}'.\n"
            f"Der Text soll ungefähr {dauer} Minuten dauern (ca. {wortzahl} Wörter).\n\n"
        )

        if speakers == 2:
            base += (
                "Verwende diese Sprecher:\n"
                "- M: Moderator (männlich)\n"
                "- F: Expertin (weiblich)\n\n"
                "Nutze ausschließlich diese Labels: M: und F:\n\n"
            )
        else:
            base += (
                "Es gibt nur einen Sprecher: M: Moderator.\n"
                "Nutze ausschließlich das Label M:\n\n"
            )

        base += (
            "Die Struktur MUSS so aussehen:\n"
            "INTRO\n"
            "M: Begrüßung & Einstieg\n\n"
            "HAUPTEIL\n"
            "M: Erklärungen\n"
        )

        if speakers == 2:
            base += "F: Antworten & Ergänzungen\n"

        base += (
            "\nOUTRO\n"
            "M: Zusammenfassung\n"
        )

        if speakers == 2:
            base += "F: kurzer Abschlusskommentar\n"

        base += (
            "\nDer letzte Satz MUSS sein:\n"
            "'Das war unser Podcast – bis zum nächsten Mal!'\n"
        )

        return base

    # ---------------------------------------------------------
    # Anfrage an Google Gemini
    # ---------------------------------------------------------
    def _ask_gemini(self, prompt: str) -> str:
        """
        Sendet die Anfrage an Gemini und gibt den generierten Text zurück.
        Behandelt auch Fehlerfälle und unterschiedliche Antwortformate.
        """

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }

        # Netzwerkfehler abfangen
        try:
            response = requests.post(self.url, json=body, timeout=15)
        except requests.RequestException as e:
            raise LLMServiceError(f"Netzwerkfehler beim Zugriff auf Gemini: {e}")

        # Falscher API-Status
        if response.status_code != 200:
            raise LLMServiceError(f"Gemini API-Fehler: HTTP {response.status_code} - {response.text}")

        data = response.json()

        # Parsing-Fehler abfangen
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            raise LLMServiceError("Gemini-Antwort konnte nicht gelesen werden.")
    # ---------------------------------------------------------
    # PUBLIC METHOD
    # ---------------------------------------------------------

    def generate_script(self, thema: str, config: dict) -> str:
        """
        Öffentliche Methode.
          Baut den Prompt
          Fragt das KI-Modell an
          Gibt das fertige Podcast-Skript zurück
        """
        # Dummy-Modus
        if self.use_dummy:
            return self._dummy_output(thema)

        #Prompt bauen
        prompt = self._system_prompt() + "\n" + self._user_prompt(thema, config)

        # Versuch, echte KI anzufragen
        try:
            return self._ask_gemini(prompt)
        except LLMServiceError as e:
            print("[WARNUNG] KI-Fehler → Dummy wird verwendet:", e)
            return self._dummy_output(thema)

