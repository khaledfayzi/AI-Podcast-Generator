from abc import ABC, abstractmethod
from models import PodcastStimme

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