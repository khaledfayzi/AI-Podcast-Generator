from database.models import Podcast, Textbeitrag, Konvertierungsauftrag
from .base_repo import BaseRepo

class PodcastRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, Podcast)
    
    def get_by_user_id(self, user_id):
        """
        Liefert alle Podcasts eines Benutzers
        """
        return (self.db.query(Podcast)
                .join(Konvertierungsauftrag)
                .join(Textbeitrag)
                .filter(Textbeitrag.userId == user_id)
                .all())

    def get_all_sorted_by_date_desc(self):
        """
        Liefert alle Podcasts nach Erstelldatum absteigend sortiert
        """
        return self.db.query(Podcast).order_by(Podcast.erstelldatum.desc()).all()