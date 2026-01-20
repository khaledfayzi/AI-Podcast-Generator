import datetime
import secrets
import string
from typing import Dict, Any

from passlib.hash import argon2
from database.database import get_db
from repositories.user_repo import UserRepo
from services.exceptions import AuthenticationError
from services.email_service import EmailService


def request_login_link(db_session: Any, email: str) -> str:
    """
    Initiiert den Login-Prozess für einen Benutzer.

    Erstellt bei Bedarf einen neuen Benutzer (Auto-Registrierung), generiert einen
    8-stelligen alphanumerischen Token, hasht diesen mit Argon2 für die Datenbank
    und versendet den Klartext-Token per E-Mail.

    Args:
        db_session: Die aktive Datenbank-Sitzung.
        email: Die E-Mail-Adresse des Benutzers.

    Returns:
        str: Der generierte Klartext-Token (primär für Rückgabewerte in Tests).

    Raises:
        AuthenticationError: Wenn innerhalb der letzten 5 Minuten bereits
                            ein Code angefordert wurde.
    """
    repo = UserRepo(db_session)
    user = repo.get_by_email(email)

    if not user:
        user = repo.create_user(email)

    # Generierung eines sicheren 8-stelligen Tokens
    alphabet = string.ascii_letters + string.digits
    plain_token = "".join(secrets.choice(alphabet) for _ in range(8))

    # Argon2 Hashing für die persistente Speicherung
    hash_token = argon2.hash(plain_token)
    now = datetime.datetime.now()

    # Rate-Limiting: 5 Minuten Sperrfrist zwischen Token-Anfragen
    if user.token_timestamp and (
        now - user.token_timestamp < datetime.timedelta(minutes=5)
    ):
        remaining = datetime.timedelta(minutes=5) - (now - user.token_timestamp)
        minutes, seconds = divmod(remaining.seconds, 60)
        raise AuthenticationError(
            f"Anfrage zu schnell. Bitte warten Sie {minutes}:{seconds:02d} Minuten."
        )

    repo.set_login_token(user, hash_token, now)

    email_service = EmailService()
    email_service.send_login_token(email, plain_token)

    return plain_token


def verify_login_link(db_session: Any, email: str, input_token: str) -> Any:
    """
    Validiert den vom Benutzer eingegebenen Token.

    Prüft die Existenz des Benutzers, die zeitliche Gültigkeit des Tokens (max. 15 Min)
    und verifiziert den kryptografischen Hash. Bei Erfolg wird der Token entwertet.

    Args:
        db_session: Die aktive Datenbank-Sitzung.
        email: Die E-Mail-Adresse des Benutzers.
        input_token: Der vom Benutzer eingegebene Klartext-Token.

    Returns:
        User: Das User-Objekt bei erfolgreicher Validierung.

    Raises:
        AuthenticationError: Wenn der User nicht existiert, kein Token aktiv ist,
                            der Token abgelaufen ist oder der Hash nicht übereinstimmt.
    """
    repo = UserRepo(db_session)
    user = repo.get_by_email(email)

    if not user:
        raise AuthenticationError("Benutzerkonto nicht gefunden.")

    if not user.token or not user.token_timestamp:
        raise AuthenticationError("Kein aktiver Login-Vorgang gefunden.")

    # Gültigkeitsprüfung: Token läuft nach 15 Minuten ab
    if datetime.datetime.now() - user.token_timestamp > datetime.timedelta(minutes=15):
        repo.clear_login_token(user)
        raise AuthenticationError(
            "Der Code ist abgelaufen. Bitte neuen Code anfordern."
        )

    if not argon2.verify(input_token, user.token):
        raise AuthenticationError("Ungültiger Code.")

    # Token nach erfolgreicher Verifizierung sofort löschen
    repo.clear_login_token(user)
    return user


def process_login_request(email: str) -> str:
    """
    Verwaltet den Datenbank-Lebenszyklus für eine Login-Anfrage.

    Inkludiert einen Test-Modus für eine spezifische E-Mail-Adresse,
    um die E-Mail-Zustellung zu umgehen.

    Args:
        email: Die E-Mail-Adresse, für die der Login angefordert wird.

    Returns:
        str: Der Login-Token oder User-Informationen im Testfall.

    Raises:
        Exception: Reicht Datenbank- oder Authentifizierungsfehler nach Rollback weiter.
    """
    TEST_EMAIL = "test@smail.th-koeln.de"

    if email.lower() == TEST_EMAIL:
        db = get_db()
        try:
            user = UserRepo(db).get_by_email(email)
            if not user:
                user = UserRepo(db).create_user(email)
            db.commit()
            return {"id": user.userId, "email": user.smailAdresse}
        finally:
            db.close()

    db = get_db()
    try:
        result = request_login_link(db, email)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_verify_login(email: str, code: str) -> Dict[str, Any]:
    """
    Verwaltet den Datenbank-Lebenszyklus für die Verifizierung eines Tokens.

    Args:
        email: E-Mail-Adresse des Benutzers.
        code: Der eingegebene Verifizierungscode.

    Returns:
        Dict[str, Any]: Ein Dictionary mit der User-ID und E-Mail.

    Raises:
        AuthenticationError: Bei fehlerhafter Verifizierung.
        Exception: Bei Datenbankfehlern.
    """
    TEST_EMAIL = "test@smail.th-koeln.de"
    TEST_CODE = "testtest"

    if email.lower() == TEST_EMAIL:
        if code == TEST_CODE:
            db = get_db()
            try:
                user = UserRepo(db).get_by_email(email)
                if not user:
                    user = UserRepo(db).create_user(email)
                db.commit()
                return {"id": user.userId, "email": user.smailAdresse}
            finally:
                db.close()
        else:
            raise AuthenticationError("Ungültiger Code.")


    db = get_db()
    try:
        user = verify_login_link(db, email, code)
        db.commit()
        return {"id": user.userId, "email": user.smailAdresse}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
