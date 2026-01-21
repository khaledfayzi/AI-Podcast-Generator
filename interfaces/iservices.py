from abc import ABC, abstractmethod

from pydub import AudioSegment

from database.models import PodcastStimme
from typing import List, Tuple, Dict, Any


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
    def generate_audio(
        self, skript_text: str, sprache:str , primary_voice: PodcastStimme, secondary_voice: PodcastStimme = None
    ) -> AudioSegment | None:
        """
        Muss von der Unterklasse implementiert werden.
        """
        pass


class IWorkflow(ABC):
    """
    Interface für die Workflow-Orchestrierung.
    """

    @abstractmethod
    def get_voices_for_ui(self) -> Tuple[List[str], List[str]]:
        """Gibt primäre und sekundäre Stimmenoptionen zurück."""
        pass

    @abstractmethod
    def generate_script(
        self,
        thema: str,
        sprache: str,
        dauer: int,
        speakers: int,
        roles: dict | None,
        hauptstimme: str,
        zweitstimme: str | None,
        source_text: str | None = None,
    ) -> str:
        """Generiert das Podcast-Skript."""
        pass

    @abstractmethod
    def generate_audio_obj_step(
        self, script_text: str, sprache: str, hauptstimme: str, zweitstimme: str | None
    ) -> Any:
        """Generiert das Audio-Objekt (z.B. Pydub AudioSegment), ohne es zu speichern."""
        pass

    @abstractmethod
    def save_audio_file(self, audio_segment: Any) -> str:
        """Speichert ein Audio-Objekt als Datei und gibt den Pfad zurück."""
        pass

    @abstractmethod
    def save_podcast_db(
        self,
        user_id: int,
        script: str,
        thema: str,
        dauer: int,
        sprache: str,
        hauptstimme: str,
        zweitstimme: str | None,
        audio_path: str,
        role1: str | None,
        role2: str | None,
    ):
        """Speichert die Podcast-Metadaten in der Datenbank."""
        pass

    @abstractmethod
    def generate_audio_step(
        self,
        script_text: str,
        thema: str,
        dauer: int,
        sprache: str,
        hauptstimme: str,
        zweitstimme: str | None,
        user_id: int,
        role1: str | None,
        role2: str | None,
    ) -> str:
        """Generiert Audio und speichert Metadaten in einem Schritt."""
        pass

    @abstractmethod
    def get_podcasts_data(self, user_id: int | None) -> List[Dict[str, Any]]:
        """Gibt eine Liste von Podcasts für einen Benutzer zurück."""
        pass

    @abstractmethod
    def delete_podcast(self, podcast_id: int, user_id: int) -> bool:
        """Löscht einen Podcast."""
        pass
