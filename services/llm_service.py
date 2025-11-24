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

from builtins import Exception, print, str
import requests 

class LLMService:


    def __init__(self, model_name: str = "llama3", use_dummy: bool = False):
        """
        model_name: welches Ollama-Modell benutzt wird
        use_dummy: wenn True → KI wird NICHT gefragt, Dummy-Text wird benutzt
        """
        self.model = model_name
        self.use_dummy = use_dummy
        self.api_url = "http://localhost:11434/api/chat"   # OLLAMA-URL



    def _system_prompt(self) ->str:
        return("Du bist ein professioneller deutschsprachiger Podcast-Autor. "
        "Schreibe alle Inhalte ausschließlich auf Deutsch. "
        "Der Stil soll klar, spannend und gut strukturiert sein."
        )
    

    def _user_prompt(self, thema:str) ->str:
        
        return(f"Erstelle ein Podcast-Skript über folgendes Thema: {thema}")
    

    #Ergibt den kompletten Text, der an die KI geschickt wird.
    def _build_prompt(self, thema :str)-> str:

        return (f"System:\n{self._system_prompt()}\n\n"
                f"User:\n{self._user_prompt(thema)}\n\n")
    

    #Wird benutzt, wenn echte KI nicht genutzt wird oder ein Fehler passiert
    def _dummy_output(self,thema:str)-> str:
        return(f"==Dummy Podcast über {thema}==\n"
               "Dies ist eine Testausgabe..."
               )
    def _ask_ollama(self, prompt: str) -> str:
        payload = {
         "model": self.model,
            "messages": [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": prompt}
         ],
         "stream": False
        }

        try:
            res = requests.post(self.api_url, json=payload)
            res.raise_for_status()
            data = res.json()
            return data["message"]["content"]
        except Exception as e:
            print(f"[LLMService] OLLAMA Fehler: {e}")
            return None


   

    #Öffentliche Methode
    def generate_script(self,thema:str)->str:

        #Dummy?
        if self.use_dummy:
            return self._dummy_output(thema)
        
        #Prompt bauen
        prompt=self._build_prompt(thema)

        #Echte Anfrage
        response = self._ask_ollama(prompt)

        #falls Ollama nicht läuft
        if response is None:
            return self._dummy_output(thema)
        return response

