from datetime import date
import hashlib

from database.models import Benutzer
from .base_repo import BaseRepo


class UserRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, Benutzer)

    def _hash_email(self, email: str) -> str:
        """Hashes the email address using SHA-256."""
        return hashlib.sha256(email.encode("utf-8")).hexdigest()

    def get_by_email(self, email):
        """
        Liefert den Benutzer mit der angegebenen E-Mail-Adresse (Hash).
        """
        hashed_email = self._hash_email(email)
        return self.db.query(Benutzer).filter_by(smailAdresse=hashed_email).first()

    def create_user(self, email):
        hashed_email = self._hash_email(email)
        new_user = Benutzer(
            smailAdresse=hashed_email, status="neu", registrierungsdatum=date.today()
        )
        self.db.add(new_user)
        self.db.commit()
        return new_user

    def set_login_token(self, user, token, token_timestamp):
        user.token = token
        user.token_timestamp = token_timestamp

        self.db.commit()

    def clear_login_token(self, user):
        user.token = None
        user.token_timestamp = None
        self.db.commit()
