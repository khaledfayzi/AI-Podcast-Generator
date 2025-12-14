from database.models import Benutzer
from .base_repo import BaseRepo

class UserRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, Benutzer)
    
    def get_by_email(self, email):
        """
        Liefert den Benutzer mit der angegebenen E-Mail-Adresse
        """
        return self.db.query(Benutzer).filter_by(smailAdresse=email).first()