from Interfaces.IServices import ILLMService
from .exceptions import LLMServiceError
import requests
import os
import time
from dotenv import load_dotenv
load_dotenv()

class LLMService(ILLMService):
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

    #Hilffuntkion für der Regel
    def _roles_instruction(self, config: dict) -> str:
        s1 = config.get("hauptstimme", "Max")
        s2 = config.get("zweitstimme")
        #rolle holen 
        roles = config.get("roles") or {}

        r1 = roles.get(s1)
        r2 = roles.get(s2) if s2 else None

        lines = []
        #erste rolle
        if r1:
            lines.append(f"- {s1} ist {r1}.")
        #gibt es eine zweite person und hat er eine rolle    
        if s2 and r2:
            lines.append(f"- {s2} ist {r2}.")
        #gibt es überhaupt eine zweite person rolle verteilen
        if s2:
            lines.append(f"- {s1} stellt Fragen und moderiert; {s2} erklärt und liefert Fakten/Beispiele.")

        return "\n".join(lines) + ("\n" if lines else "")




    def _system_prompt(self, config: dict) -> str:
        language = config.get("language", "Deutsch")
        s1 = config.get("hauptstimme", "Max")
        s2 = config.get("zweitstimme")
        roles_text = self._roles_instruction(config)

        if language not in ("Deutsch", "English"):
            language = "Deutsch"

        language_line = (
            "- Schreibe ausschließlich auf Deutsch.\n"
            if language == "Deutsch"
            else "- Write exclusively in English.\n"
        )

        return (
                "Du bist ein professioneller Podcast-Autor.\n"
                "DEINE HAUPTAUFGABE:\n"
                "Erstelle ein Skript, das für Menschen gut lesbar ist, aber spezielle Markierungen für die Sprachausgabe (TTS) nutzt.\n\n"
                "REGELN FÜR DEN INHALT:\n"
                + language_line +
                "- Jede Sprecherzeile darf höchstens 1–2 Sätze enthalten.\n"
                "- Keine langen Monologe: Teile Inhalte auf kurze Abschnitte auf.\n"
                "- Sprecherlabels MÜSSEN so aussehen: 'Max:' oder 'Sara:'.\n"
                f"- Erlaubte Sprecher: {s1}" + (f" und {s2}.\n" if s2 else ".\n")
                + roles_text +
                "\nREGELN FÜR DIE FORMATIERUNG (WICHTIG):\n"
                "- Benutze KEINE XML-Tags oder SSML (kein <break/>, kein <emphasis>).\n"
                "- Nutze AUSSCHLIESSLICH dieses Markdown-System zur Steuerung der Stimme:\n"
                "  1. Betonung: Nutze **Wort** für starke Betonung und *Wort* für leichte Betonung.\n"
                "  2. Pausen: Nutze [pause: 500ms] für kurze oder [pause: 1s] für lange Pausen.\n"
                "  3. Buchstabieren: Nutze [spell: ABK] für Abkürzungen, die einzeln gesprochen werden sollen (z.B. [spell: KI]).\n"
                "  4. Datum: Nutze [date: 12.01.2026] für Datumsangaben.\n"
                "  5. Dauer: Nutze [dur: 2m 30s] für Zeitangaben.\n"
                "- Nutze KEIN anderes Markdown wie Überschriften (#), Listen (-) oder Bullet-Points.\n"
                "- Emotionen nur als (lacht) oder (seufzt) im Text einbauen.\n"
                "- Der Text muss flüssig und natürlich klingen.\n"
        )


    
    # USER PROMPT
    def _user_prompt(self, thema: str | None, config: dict) -> str:
        try:
            duration = int(config.get("dauer", 5))
        except Exception:
            duration = 5

        target_words = duration * 140
        style=(config.get("style")or "neutral").lower()
        style_line={
            "neutral":"Ton: neutral, sachlich verständlich.",
            "freudig":"Ton: freundlich motivierend, positiv.",
            "gechillt":"Ton: locker , entspannt, umgangssprachlich.",
            "komisch" :"Ton humorvoll, aber informative aber rezepektvoll.",
        }.get(style,"Ton: neutral , sachlich , verständlich")

        source_text = (config.get("source_text") or "").strip()
        max_chars = int(config.get("source_max_chars", 12000))
        if source_text and len(source_text) > max_chars:
            source_text = source_text[:max_chars]

        # Fall 1: Quelle vorhanden → Thema optional (als Fokus)
        if source_text:
            focus = f"Fokus/Thema: {thema}\n" if thema else ""
            return (
                f"{focus}"
                f"Ziel-Länge: ca. {target_words} Wörter.\n"
                "Erstelle einen gesprochenen Podcast-Text auf Basis der folgenden Quelle.\n"
                "Erfinde keine Fakten, die nicht in der Quelle stehen.\n"
                "Erkläre verständlich und podcast-tauglich.\n\n"
                "QUELLE:\n"
                f"{source_text}\n"
            )

    # Fall 2: keine Quelle → Thema muss genutzt werden
        return (
            f"Thema: {thema}\n"
            f"Ziel-Länge: ca. {target_words} Wörter.\n"
            f"{style_line}.\n"
            "Erstelle einen gesprochenen Podcast-Text zu diesem Thema.\n"
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

        for attempt in range(3):


            # Netzwerkfehler abfangen
            try:
                response = requests.post(self.url, json=body, timeout=15)
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(attempt + 1)   #kurz warten und nochmal versuchen
                    continue
                raise LLMServiceError(f"Gemini ist nicht erreichbar (Internet/Server-Problem): {e}")
            #zu viele Anfragen, bitte warten
            if response.status_code==429 and attempt < 2:
                time.sleep(attempt + 1)  #rate limit --> Warten
                continue


            # Gemini mit einem fehler antwortet(falscher Key, Serverfehler, usw.)
            if response.status_code != 200:
                raise LLMServiceError(f"Gemini API-Fehler: HTTP {response.status_code} - {response.text}")


            # Parsing-Fehler abfangen
            try:
                #lesen den Text aus der KI-Antwort
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            except Exception:
                raise LLMServiceError("Gemini-Antwort konnte nicht gelesen werden.")
    

    # Dummy
    def _dummy_output(self,thema:str,config:dict):          
            """
            Gibt einen einfachen Dummy-Text zurück.
            Wird verwendet, wenn kein echtes LLM aufgerufen wird (z.B. im Dummy-Modus).
            Der Text simuliert die spätere Struktur eines Podcast-Skripts
            mit einem oder zwei Sprechern.
            """

            
            return (
                    f"{thema}: Das ist ein Dummy-Testtext ohne zweiten Sprecher.\n"
                    f"{config}:Das ist eine Dummy Test"
                )

    # PUBLIC METHOD
    def generate_script(self,thema: str,config: dict) -> str:
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
            return self._dummy_output(thema,config)

        prompt = (
            self._system_prompt(config)
            + "\n"
            + self._user_prompt(thema, config)
        )

        try:
            return self._ask_gemini(prompt)
        except LLMServiceError as e:
            print("LLM error:", e)
            return self._dummy_output(thema,config)
