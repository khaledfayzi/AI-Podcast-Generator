from database.models import Konvertierungsauftrag, AuftragsStatus
from .base_repo import BaseRepo


class JobRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, Konvertierungsauftrag)

    def get_pending_jobs(self):
        """
        Liefert alle Aufträge, die noch nicht abgeschlossen sind
        """
        return (
            self.db.query(Konvertierungsauftrag)
            .filter_by(status=AuftragsStatus.IN_BEARBEITUNG)
            .all()
        )
