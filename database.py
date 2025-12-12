import os
import urllib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sshtunnel import SSHTunnelForwarder
from models import Base
from flask import g

engine = None
tunnel = None
SessionLocal = None

def init_db_connection():
    """
    Initialisiert die Datenbankverbindung, optional über einen SSH-Tunnel
    """
    global engine, tunnel, SessionLocal

    if engine is not None:
        return

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_port = int(os.getenv("DB_PORT", 3306))
    ssh_host = os.getenv("SSH_HOST")
    ssh_user = os.getenv("SSH_USER")
    ssh_password = os.getenv("SSH_PASSWORD")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    connection_host = os.getenv("DB_HOST")
    connection_port = db_port

    if ssh_host and ssh_user:
        try:
            print("SSH-Tunnel wird gestartet")
            tunnel = SSHTunnelForwarder(
                (ssh_host, int(os.getenv("SSH_PORT", 22))),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key_path,
                ssh_password=ssh_password,
                remote_bind_address=('127.0.0.1', db_port)
            )
            tunnel.start()
            connection_port = tunnel.local_bind_port
            connection_host = '127.0.0.1'
            print("SSH-Tunnel aktiv!")
        except Exception as e:
            print(f"Fehler bei der SSH-Verbindung: {e}")
            raise e
    else:
        print("Datenbank wird lokal verbunden")

    database_url = f"mysql+pymysql://{db_user}:{db_password}@{connection_host}:{connection_port}/{db_name}"
    engine = create_engine(database_url, echo=False)

    # Tabellen anlegen, falls sie noch nicht existieren
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("Datenbank verbunden!")

def get_db():
    """
    Gibt eine Datenbank-Session zurück.
    Unterscheidet zwischen Flask-Request und CLI-Nutzung
    """
    global SessionLocal
    if SessionLocal is None:
        init_db_connection()

    try:
        if 'db' not in g:
            g.db = SessionLocal()
        return g.db
    except RuntimeError:
        return SessionLocal()

def close_db(e=None):
    """
    Schließt die DB-Session am Ende eines Requests
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """
    Registriert die Datenbank-Funktionen in der Flask-App
    """
    init_db_connection()
    app.teardown_appcontext(close_db)