from database.voices import VOICES
from database.models import PodcastStimme


class VoiceRepo:
    def __init__(self, db=None):
        # Wir brauchen die db eigentlich nicht mehr für Stimmen, 
        # aber wir lassen sie drin, damit wir woanders im Code nichts kaputt machen.
        self.db = db
        self.voices = VOICES

    def get_all(self) -> list[PodcastStimme]:
        """
        Gibt einfach alle Stimmen aus der Liste zurück.
        """
        return self.voices

    def get_voices_by_names(self, names: list[str]) -> list[PodcastStimme]:
        """
        Sucht die Stimmen in unserer Liste nach Namen.
        """
        if not names:
            return []
        
        ergebnis = []
        for v in self.voices:
            if v.name in names:
                ergebnis.append(v)
        return ergebnis

    def get_voices_by_slot(self, slot: int) -> list[PodcastStimme]:
        """
        Filtert die Stimmen nach dem UI-Slot (1 oder 2).
        """
        ergebnis = []
        for v in self.voices:
            if v.ui_slot == slot:
                ergebnis.append(v)
        return ergebnis
