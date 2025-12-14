from database.models import Quelldatei
from .base_repo import BaseRepo

class FileRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, Quelldatei)
    
    def get_by_user_id(self, user_id):
        """
        Liefert alle Quelldateien eines Benutzers
        """
        return self.db.query(Quelldatei).filter_by(userId=user_id).all()
    
    def get_by_text_id(self, text_id):
        """
        Liefert alle Quelldateien eines Textbeitrags
        """
        return self.db.query(Quelldatei).filter_by(textId=text_id).all()