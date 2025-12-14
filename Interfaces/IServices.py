from abc import ABC, abstractmethod
from database.models import PodcastStimme

class ILLMService(ABC):
    @abstractmethod
    def generate_script(self, prompt: str, config: dict) -> str:
        """Erzeugt ein Skript basierend auf dem Prompt."""
        pass



class ITTSService(ABC):
    """
    Interface, damit man die TTS-Engine leicht austauschen kann
    """

    @abstractmethod
    def generate_audio(self, skript: str, hauptstimme: PodcastStimme, zweitstimme: PodcastStimme = None) -> str | None:
        """
        Muss von der Unterklasse implementiert werden.
        """
        pass


class IWorkflow(ABC):
    """
    Interface für die Workflow-Orchestrierung.
    """

    @abstractmethod
    def run_pipeline(self, user_prompt: str, user_id: int, llm_id: int, tts_id: int, thema: str,
                     dauer: int, sprache: str, hauptstimme: str, zweitstimme: str = None,
                     speakers: int = 1, roles: dict = None) -> str:
        """
        Führt den gesamten Prozess der Podcast-Generierung aus.
        """
        pass