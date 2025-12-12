from .exceptions import LLMServiceError
import requests
import os
from dotenv import load_dotenv
load_dotenv()

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
        if not use_dummy and not self.api_key:
            raise LLMServiceError("Umgebungsvariable GEMINI_API_KEY fehlt.")

        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1/{self.model}:generateContent?key={self.api_key}"
        self.use_dummy=use_dummy


    # SYSTEM PROMPT   
    def _system_prompt(self,hauptstimme:str,zweitstimme:str |None=None) -> str:
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
                "- Keine langen Monologe: Längere Inhalte auf mehrere Sprecherzeilen aufteilen.\n"
                "- Sprecherlabels MÜSSEN aus dem Namen des Sprechers gefolgt von einem Doppelpunkt (:) bestehen, "
                "z.B. 'Max:' oder 'Sara:'.\n"
                f"- Erlaubte Sprecher sind: {hauptstimme}"
                + (f" und {zweitstimme}.\n" if zweitstimme else ".\n")
                + "- Falls nur ein Sprecher erlaubt ist, schreibe ausschließlich für diesen Sprecher (Monolog).\n"
                "- Keine Regieanweisungen wie [Musik], [Intro], [Klatschen] oder ähnliche.\n"
                "- Erlaubt sind SSML-Tags ausschließlich zur Verbesserung der Sprachausgabe, "
                "z.B. <break time=\"500ms\"/> für Pausen oder <emphasis>wichtig</emphasis> für Betonung.\n"
                "- KEIN Markdown, keine Listen, keine Bullet-Points.\n"
                "- Nur normaler Fließtext, abgesehen von den erlaubten SSML-Tags.\n"
                "- Emotionen nur als (lacht) oder (seufzt).\n"
                "- Der Text muss direkt für Text-to-Speech geeignet sein.\n"
                )


    # Dummy
    def _dummy_output(self, hauptstimme: str, zweitstimme: str | None):          
            """
            Gibt einen einfachen Dummy-Text zurück.
            Wird verwendet, wenn kein echtes LLM aufgerufen wird (z.B. im Dummy-Modus).
            Der Text simuliert die spätere Struktur eines Podcast-Skripts
            mit einem oder zwei Sprechern.
            """

            if zweitstimme:
                return (
                    f"{hauptstimme}: Das ist ein Dummy-Testtext.\n"
                    f"{zweitstimme}: Wir testen nur die Funktionalität.\n"
                )
            else:
                return (
                    f"{hauptstimme}: Das ist ein Dummy-Testtext ohne zweiten Sprecher.\n"
                )


    
    # USER PROMPT
    def _user_prompt(self, thema: str, config: dict) -> str:
        """
        Baut den User-Prompt.
        Dieser Teil beschreibt der KI, WAS geschrieben werden soll.
        Enthält das Thema des Podcasts und die gewünschte Dauer.
        """

        dauer = config.get("dauer", 2)

        return (
            f"Schreibe einen gesprochenen Podcast-Text zum Thema '{thema}'.\n"
            f"Ungefähre Dauer: {dauer} Minuten.\n"
            "Der Text soll natürlich klingen und direkt gesprochen werden können.\n"
        )


    # Anfrage an Google Gemini
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
        

    # PUBLIC METHOD
    def generate_script(self,thema: str,config: dict,hauptstimme: str,zweitstimme: str | None = None) -> str:
        """
            Öffentliche Methode zur Generierung eines Podcast-Skripts.

            Der Ablauf ist wie folgt:
            1. Optionaler Dummy-Modus für lokale Tests ohne API-Zugriff.
            2. Aufbau des Prompts aus System-Prompt 
               und User-Prompt.
            3. Anfrage an das Sprachmodell (Gemini).
            4. Fallback auf Dummy-Text bei Fehlern.
            """
        
        # Dummy-Modus (für lokale Tests)
        if self.use_dummy:
            return self._dummy_output(hauptstimme, zweitstimme)

        prompt = (
            self._system_prompt(hauptstimme, zweitstimme)
            + "\n"
            + self._user_prompt(thema, config)
        )

        try:
            return self._ask_gemini(prompt)
        except Exception:
            return self._dummy_output(hauptstimme, zweitstimme)
