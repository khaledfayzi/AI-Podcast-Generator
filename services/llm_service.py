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

import requests 

class LLMService:
    """
        Service für Textgenerierung mit einem Sprachmodell.
        - Baut System- und User-Prompts
        - Sendet Anfrage an Ollama
        - Gibt reinen Podcast-Text zurück
    """
        

    def __init__(self, model_name: str = "llama3", use_dummy: bool = False):
        """
        Initialisiert den Service.
        model_name: welches Ollama-Modell benutzt wird
        use_dummy: wenn True → KI wird NICHT gefragt, Dummy-Text wird benutzt
        """

        self.model = model_name
        self.use_dummy = use_dummy
        self.api_url = "http://localhost:11434/api/chat"   # OLLAMA-URL



    def _system_prompt(self,config:dict) ->str:
        """
        Baut den System-Prompt.
        Dieser beschreibt der KI *wie* sie schreiben soll.
        (Sprache, Schreibstil)
        """

        language=config.get("language","de")
        style=config.get("style","neutral")

        if language=="en":
            base="You are a professional English podcast author. Write clearly and well-structured."
        else:
            base = (
                "Du bist ein professioneller deutschsprachiger Podcast-Autor. "
                "DU MUSST ALLES AUSSCHLIESSLICH AUF DEUTSCH SCHREIBEN. "
                "Kein einziger englischer Satz ist erlaubt. "
            )

        if language=="en":
            if style=="komisch":
                style_text="Your writing style should be funny and humorous."
            elif style=="freudig":
                style_text="Your writing style should be happy, bright and uplifting."
            elif style=="gechillt":
                style_text="Your writing style should be relaxed, calm and casual."
            else:
                style_text="Keep a neutral and factual tone."
        else:
            if style=="komisch":
                style_text="Dein Schreibstil soll komisch und humorvoll sein."
            elif style=="freudig":
                style_text="Dein Schreibstil soll freudig, fröhlich und positiv sein."
            elif style=="gechillt":
                style_text="Dein Schreibstil soll gechillt, entspannt und locker sein."
            else:
                style_text="Halte einen neutralen und sachlichen Ton."

        return f"{base} {style_text}"


       
    

    def _user_prompt(self, thema:str,config:dict) ->str:

        """
        Baut den User-Prompt.
        Dieser enthält *was* geschrieben werden soll:
        Thema, Dauer, Sprecher, PDF-Inhalt usw.
        """

        dauer=config.get("dauer",15)
        speakers=config.get("speakers",1)
        pdf_text=config.get("pdf_text","")
        roles=config.get("roles",{})
        speaker1=roles.get("speaker1","Moderator")
        speaker2=roles.get("speaker2","Experte")

        prompt=(f"Erstelle ein Podcast-Skript über das Thema {thema}. "
        f"Der Podcast soll etwa {dauer} Minuten dauern. ")
        
        if speakers==2:
            prompt += (f"Schreibe einen Dialog zwischen {speaker1} und {speaker2}. ")

        else :
            prompt +="Schreibe das Skript für einen einzelnen Sprecher. "

        if pdf_text:
            prompt +=f"Verwende zusätzlich folgenden Text:\n{pdf_text}\n"
        prompt +="Strukturiere das Skript in: Intro, Hauptteil und Outro."

        return prompt
    

    def _build_prompt(self, thema :str,config:dict)-> str:
        """
        Kombiniert System-Prompt + User-Prompt
        in das Format, das der Chat-API-Endpunkt erwartet.
        """

        return [
            {"role": "system", "content": self._system_prompt(config)},
            {"role": "user",   "content": self._user_prompt(thema, config)}
        ]
    


    def _dummy_output(self,thema:str)-> str:
        """
        Gibt Test-Text zurück, falls kein echtes KI-Modell genutzt wird.
        Hilfreich für lokale Tests ohne KI.
        """

        return(f"==Dummy Podcast über {thema}==\n"
               "Dies ist eine Testausgabe..."
               )
    

    def _ask_ollama(self, messages) -> str:
        """
        Sendet die Anfrage an Ollama und gibt den generierten Text zurück.
        Behandelt auch Fehlerfälle und unterschiedliche Antwortformate.
        """

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            res = requests.post(self.api_url, json=payload)
            res.raise_for_status()
            data = res.json()
            if "message" in data:
                return data["message"]["content"]
            if "messages" in data:
                return data["messages"][-1]["content"]

            raise KeyError("Kein gültiges Antwortformat gefunden.")

        except Exception as e:
            print(f"[LLMService] OLLAMA Fehler: {e}")
            return None

   
    def generate_script(self, thema: str, config: dict | None = None) -> str:
        """
        Öffentliche Methode.
          Baut den Prompt
          Fragt das KI-Modell an
          Gibt das fertige Podcast-Skript zurück
        """

        if config is None:
            config={}

        #Dummy?
        if self.use_dummy:
            return self._dummy_output(thema)
        
        #Prompt bauen
        messages=self._build_prompt(thema,config)

        #Echte Anfrage
        response = self._ask_ollama(messages)

        #falls Ollama nicht läuft
        if response is None:
            return self._dummy_output(thema)
        return response

