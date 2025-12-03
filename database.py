import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sshtunnel import SSHTunnelForwarder

engine = None
tunnel = None
SessionLocal = None

def init_db():
    """
    Initialisiert die Datenbankverbindung, optional über einen SSH-Tunnel
    """
    global engine, tunnel, SessionLocal

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_port = int(os.getenv("DB_PORT", 3306))
    ssh_host = os.getenv("SSH_HOST")
    ssh_user = os.getenv("SSH_USER")
    ssh_key_path = os.getenv("SSH_KEY_PATH")

    if ssh_host and ssh_user:
        print("SSH-Tunnel wird gestartet")
        tunnel = SSHTunnelForwarder(
            (ssh_host, int(os.getenv("SSH_PORT", 22))),
            ssh_username=ssh_user,
            ssh_pkey=ssh_key_path,
            remote_bind_address=('127.0.0.1', db_port)
        )
        tunnel.start()
        print("SSH-Tunnel aktiv!")

        connection_port = tunnel.local_bind_port
        connection_host = '127.0.0.1'
    else:
        print("Datenbank wird lokal verbunden")
        connection_host = os.getenv("DB_HOST", "127.0.0.1")
        connection_port = db_port

    database_url = f"mysql+pymysql://{db_user}:{db_password}@{connection_host}:{connection_port}/{db_name}"

    engine = create_engine(database_url, echo=False)

    # TODO Hier evtl. noch Tabellen anlegen

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("Datenbank verbunden!")

def close_db_connection():
    """
    Schließt SSH-Tunnel
    """
    global tunnel
    if tunnel:
        tunnel.stop()
