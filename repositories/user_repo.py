from datetime import date

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

    def create_user(self, email):
        new_user = Benutzer(smailAdresse=email, status="neu", registrierungsdatum=date.today())
        self.db.add(new_user)
        self.db.commit()
        return new_user

    def set_login_token(self, user ,token, token_timestamp):
        user.token = token
        user.token_timestamp = token_timestamp

        self.db.commit()

    def clear_login_token(self, user):
        user.token = None
        user.token_timestamp = None
        self.db.commit()