from .base_repo import BaseRepo
from sqlalchemy.orm import Session
from database.models import PodcastStimme


class VoiceRepo(BaseRepo):
    def __init__(self, db: Session):
        self.db = db
        super().__init__(db, PodcastStimme)


    def get_voices_by_names(self, names: list[str]) -> list[PodcastStimme]:
        """
        Lädt mehrere Stimmen basierend auf einer Liste von Namen.
        """
        # Prüfen, ob die Liste leer ist, um unnötige DB Calls zu vermeiden
        if not names:
            return []

        return self.db.query(PodcastStimme).filter(PodcastStimme.name.in_(names)).all()

    def get_voices_by_slot(self, slot: int) -> list[PodcastStimme]:
        """
        NEU: Holt alle Sprecher-Identitäten für einen bestimmten UI-Slot.
        slot=1 -> Gruppe A (Max, Sarah, Thomas, Julia)
        slot=2 -> Gruppe B (Lukas, Mia, Felix, Lena)
        """
        return self.db.query(PodcastStimme).filter(PodcastStimme.ui_slot == slot).all()