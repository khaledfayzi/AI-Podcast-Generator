# Login Logik - Hier wird alles geregelt, was mit dem Anmelden zu tun hat
import datetime
import secrets
import string

from passlib.hash import argon2

from database.database import get_db
from repositories.user_repo import UserRepo
from services.exceptions import AuthenticationError
from services.email_service import EmailService


def request_login_link(db_session, email):
    """
    Hier wird der Code für den Login erstellt. 
    Wir hashen das Teil direkt für die DB und schicken den Klartext per Mail raus.
    """
    repo = UserRepo(db_session)
    user = repo.get_by_email(email)

    # Wenn der User noch nicht da ist, legen wir ihn halt einfach an (Auto-Registrierung)
    if not user:
        user = repo.create_user(email)

    # Wir machen jetzt einen 8-stelligen Code, weil sich das keiner merken kann sonst
    alphabet = string.ascii_letters + string.digits
    plain_token = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    # Sicher ist sicher: Argon2 Hash für die Datenbank
    hash_token = argon2.hash(plain_token)

    now = datetime.datetime.now()

    # Man kann nur alle 5 Minuten einen Link sich schicken lassen
    if user.token_timestamp and (now - user.token_timestamp < datetime.timedelta(minutes=5)):
        remaining = datetime.timedelta(minutes=5) - (now - user.token_timestamp)
        minutes, seconds = divmod(remaining.seconds, 60)
        raise AuthenticationError(f"Zu schnell. Du kannst erst in {minutes}:{seconds:02d} Min wieder einen Code anfordern.")


    # Ab in die DB mit dem Hash und dem Zeitstempel
    repo.set_login_token(user, hash_token, now)
    
    # Den EmailService rufen wir hier auch direkt auf
    email_service = EmailService()
    email_service.send_login_token(email, plain_token)
    
    return plain_token


def verify_login_link(db_session, email, input_token):
    """
    Checkt ob der Code, den der User eingegeben hat, auch wirklich passt.
    Wir prüfen: Gibt's den User? Ist der Code noch frisch (15 Min)? Stimmt der Hash?
    """
    repo = UserRepo(db_session)
    user = repo.get_by_email(email)

    if not user:
        raise AuthenticationError("Den User gibt's gar nicht...")

    # Hat er überhaupt nach einem Login gefragt?
    if not user.token or not user.token_timestamp:
        raise AuthenticationError("Kein Login-Vorgang aktiv.")

    # Zeit-Check: Nach 15 Minuten ist Schicht im Schacht
    if datetime.datetime.now() - user.token_timestamp > datetime.timedelta(minutes=15):
        repo.clear_login_token(user)  # Token wegwerfen, ist eh abgelaufen
        raise AuthenticationError("Code leider abgelaufen, probier's nochmal.")

    # Jetzt der eigentliche Vergleich vom Code mit dem Hash aus der DB
    if not argon2.verify(input_token, user.token):
        raise AuthenticationError("Code falsch eingegeben, Tippfehler?")

    # Wenn alles passt: Token löschen (Sicherheit!) und User-Objekt zurückgeben
    repo.clear_login_token(user)
    return user

def process_login_request(email: str):
    """
    Wrapper that manages the DB session for a login request.
    """
    db = get_db()
    try:
        result = request_login_link(db, email)
        db.commit()  # Ensure changes (like the new token) are saved
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def process_verify_login(email: str, code: str):
    """
    Wrapper that manages the DB session for login verification.
    Returns a dictionary with user data to avoid detached instance errors.
    """
    db = get_db()
    try:
        user = verify_login_link(db, email, code)
        db.commit()  # Save the token clearance
        
        # Return a dict (DTO) so we don't pass a detached SQLAlchemy object to the UI
        return {
            "id": user.userId,
            "email": user.smailAdresse
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()