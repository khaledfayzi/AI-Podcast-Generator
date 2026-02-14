import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

# Basisklasse für die Deklaration von Klassen-Mappings
Base = declarative_base()


# --- Enum für AuftragsStatus (LD06) ---
class AuftragsStatus(enum.Enum):
    IN_BEARBEITUNG = "in Bearbeitung"
    ABGESCHLOSSEN = "Abgeschlossen"
    FEHLGESCHLAGEN = "Fehlgeschlagen"


# --- Hardcoded Classes (Keine DB-Modelle mehr) ---


class PodcastStimme:
    """
    Repräsentiert eine Stimme (früher DB-Tabelle, jetzt Hardcoded).
    """

    def __init__(self, stimmeId, name, geschlecht, tts_voice_de, tts_voice_en, ui_slot):
        self.stimmeId = stimmeId
        self.name = name
        self.geschlecht = geschlecht
        self.ttsVoice_de = tts_voice_de
        self.ttsVoice_en = tts_voice_en
        self.ui_slot = ui_slot


# --- 1. Kern-Entitäten ---


class Benutzer(Base):
    """
    Repräsentiert einen Benutzer der Plattform (LD01).
    """

    __tablename__ = "Benutzer"
    userId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")
    smailAdresse = Column(String(255), unique=True, nullable=False)
    token: Optional[str] = Column(String(255), unique=True, nullable=True)  # type: ignore
    status = Column(String(255), unique=True, nullable=False)
    registrierungsdatum = Column(Date, nullable=False)
    token_timestamp: Optional[datetime] = Column(DateTime, nullable=True)  # type: ignore

    # Beziehungen (1:n)
    textbeitraege = relationship("Textbeitrag", back_populates="ersteller")
    quelldateien = relationship("Quelldatei", back_populates="besitzer")


# --- 2. Inhalts- & Quelldaten ---


class Textbeitrag(Base):
    """
    Speichert den Generierungsvorgang eines Skripts (LD02).
    """

    __tablename__ = "Textbeitrag"
    textId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    userId = Column(Integer, ForeignKey("Benutzer.userId"), comment="FK")

    userPrompt = Column(Text)
    erzeugtesSkript = Column(Text, nullable=False)
    titel = Column(String(255), nullable=False)
    erstelldatum = Column(Date, nullable=False)
    sprache = Column(String(10), nullable=False)
    loeschzeitpunkt = Column(Date)

    # Beziehungen (n:1)
    ersteller = relationship("Benutzer", back_populates="textbeitraege")

    # Beziehungen (1:n)
    quelldateien = relationship("Quelldatei", back_populates="textbeitrag")
    konvertierungsauftraege = relationship(
        "Konvertierungsauftrag", back_populates="textbeitrag"
    )


class Quelldatei(Base):
    """
    Verwaltet Metadaten zu hochgeladenen Dateien (LD03).
    """

    __tablename__ = "Quelldatei"
    dateiId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    textId = Column(
        Integer, ForeignKey("Textbeitrag.textId"), nullable=True, comment="FK"
    )
    userId = Column(Integer, ForeignKey("Benutzer.userId"), nullable=True, comment="FK")

    dateipfad = Column(String(512), nullable=False)
    mimeType = Column(String(100), nullable=False)
    dateigroesse = Column(Integer)
    dateiname = Column(String(255), nullable=False)
    loeschzeitpunkt = Column(Date)

    # Beziehungen (n:1)
    textbeitrag = relationship("Textbeitrag", back_populates="quelldateien")
    besitzer = relationship("Benutzer", back_populates="quelldateien")


# --- 3. Konvertierung & Podcast ---


class Konvertierungsauftrag(Base):
    __tablename__ = "Konvertierungsauftrag"
    auftragId = Column(Integer, primary_key=True, autoincrement=True)

    textId = Column(Integer, ForeignKey("Textbeitrag.textId"))

    hauptstimmeName = Column(String(50), nullable=True)
    zweitstimmeName = Column(String(50), nullable=True)

    # Rollen speichern
    hauptstimmeRolle = Column(String(100), nullable=True)
    zweitstimmeRolle = Column(String(100), nullable=True)

    gewuenschteDauer = Column(Integer, nullable=False)
    status = Column(Enum(AuftragsStatus), nullable=False)

    # Relationships
    textbeitrag = relationship("Textbeitrag", back_populates="konvertierungsauftraege")

    podcast = relationship(
        "Podcast", back_populates="konvertierungsauftrag", uselist=False
    )


class Podcast(Base):
    """
    Repräsentiert das finale Audio-Produkt (LD08).
    """

    __tablename__ = "Podcast"
    podcastId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    # 1:1 Beziehung zum Konvertierungsauftrag
    auftragId = Column(
        Integer,
        ForeignKey("Konvertierungsauftrag.auftragId"),
        unique=True,
        comment="FK",
    )

    titel = Column(String(255), nullable=False)
    realdauer = Column(Integer, nullable=False)
    dateipfadAudio = Column(String(512), nullable=False)
    erstelldatum = Column(Date, nullable=False)
    isPublic = Column(Boolean, default=False, nullable=False)
    loeschzeitpunkt = Column(Date)

    # Beziehungen (n:1)
    konvertierungsauftrag = relationship(
        "Konvertierungsauftrag", back_populates="podcast"
    )
