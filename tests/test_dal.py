import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from database.models import (
    Base,
    AuftragsStatus,
    PodcastStimme,
    Textbeitrag,
    Konvertierungsauftrag,
    Podcast,
)
from repositories.user_repo import UserRepo
from repositories.job_repo import JobRepo
from repositories.podcast_repo import PodcastRepo
from repositories.text_repo import TextRepo
from repositories.voice_repo import VoiceRepo
import hashlib


@pytest.fixture
def db_session():
    """Erstellt eine In-Memory SQLite Datenbank und liefert eine Session zurück."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_user_repository(db_session):
    repo = UserRepo(db_session)
    user = repo.create_user("test@example.com")

    fetched = repo.get_by_email("test@example.com")
    assert fetched is not None
    expected_hash = hashlib.sha256("test@example.com".encode("utf-8")).hexdigest()
    assert fetched.smailAdresse == expected_hash
    assert fetched.status == "neu"

    assert repo.get_by_email("wrong@example.com") is None


def test_text_repository(db_session):
    user_repo = UserRepo(db_session)
    user = user_repo.create_user("author@example.com")
    db_session.commit()

    text_repo = TextRepo(db_session)
    t = Textbeitrag(
        userId=user.userId,
        userPrompt="Hello",
        erzeugtesSkript="Script Content",
        titel="My Script",
        erstelldatum=date.today(),
        sprache="de",
    )
    saved = text_repo.add(t)
    db_session.commit()

    assert saved.textId is not None
    assert saved.titel == "My Script"


def test_job_repository_and_relationships(db_session):
    user = UserRepo(db_session).create_user("jobuser@example.com")
    
    # Stimmen sind jetzt hardcoded, wir nehmen einfach Namen
    v_name_1 = "Max"
    v_name_2 = "Sarah"

    text_repo = TextRepo(db_session)
    text = text_repo.add(
        Textbeitrag(
            userId=user.userId,
            erzeugtesSkript="...",
            titel="Job Test",
            erstelldatum=date.today(),
            sprache="de",
            userPrompt="",
        )
    )
    db_session.commit()

    job_repo = JobRepo(db_session)
    job = Konvertierungsauftrag(
        textId=text.textId,
        hauptstimmeName=v_name_1,
        zweitstimmeName=v_name_2,
        hauptstimmeRolle="Host",
        zweitstimmeRolle="Guest",
        gewuenschteDauer=5,
        status=AuftragsStatus.IN_BEARBEITUNG,
    )
    saved_job = job_repo.add(job)
    db_session.commit()

    assert saved_job.hauptstimmeName == "Max"
    assert saved_job.zweitstimmeName == "Sarah"

    pending = job_repo.get_pending_jobs()
    assert len(pending) == 1

    saved_job.status = AuftragsStatus.ABGESCHLOSSEN
    db_session.commit()
    pending_after = job_repo.get_pending_jobs()
    assert len(pending_after) == 0


def test_podcast_repository(db_session):
    user = UserRepo(db_session).create_user("poduser@example.com")

    db_session.add(
        Textbeitrag(
            userId=user.userId,
            erzeugtesSkript="...",
            titel="P",
            erstelldatum=date.today(),
            sprache="de",
            userPrompt="",
        )
    )
    db_session.commit()
    text = db_session.query(Textbeitrag).first()

    db_session.add(
        Konvertierungsauftrag(
            textId=text.textId,
            gewuenschteDauer=10,
            status=AuftragsStatus.ABGESCHLOSSEN,
        )
    )
    db_session.commit()
    job = db_session.query(Konvertierungsauftrag).first()

    repo = PodcastRepo(db_session)
    p = Podcast(
        auftragId=job.auftragId,
        titel="Alpha Podcast",
        realdauer=10,
        dateipfadAudio="/tmp/audio.mp3",
        erstelldatum=date(2023, 1, 1),
    )
    repo.add(p)

    job2 = Konvertierungsauftrag(
        textId=text.textId,
        gewuenschteDauer=5,
        status=AuftragsStatus.ABGESCHLOSSEN,
    )
    db_session.add(job2)
    db_session.commit()

    p2 = Podcast(
        auftragId=job2.auftragId,
        titel="Beta Podcast",
        realdauer=5,
        dateipfadAudio="/tmp/b.mp3",
        erstelldatum=date(2023, 2, 1),
    )
    repo.add(p2)
    db_session.commit()

    all_pods = repo.get_all_sorted_by_date_desc()
    assert len(all_pods) == 2
    assert all_pods[0].titel == "Beta Podcast"
    assert all_pods[1].titel == "Alpha Podcast"


def test_voice_repo(db_session):
    # Das VoiceRepo nutzt jetzt VOICES aus database.voices
    repo = VoiceRepo(db_session)
    voices = repo.get_all()
    names = [v.name for v in voices]
    
    # Check ob die Standard-Stimmen da sind
    assert "Max" in names
    assert "Sarah" in names

    slot1 = repo.get_voices_by_slot(1)
    assert any(v.name == "Max" for v in slot1)
    # Sarah ist in Slot 2 (laut voices.py)
    assert not any(v.name == "Sarah" for v in slot1)
