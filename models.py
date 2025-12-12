from sqlalchemy import Column, Integer, String, Date, Boolean, Enum, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import date
from typing import List
import enum

# Basisklasse für die Deklaration von Klassen-Mappings
Base = declarative_base()


# --- Enum für AuftragsStatus (LD06) ---
class AuftragsStatus(enum.Enum):
    IN_BEARBEITUNG = "in Bearbeitung"
    ABGESCHLOSSEN = "Abgeschlossen"
    FEHLGESCHLAGEN = "Fehlgeschlagen"


# --- 1. Kern-Entitäten ---

class Benutzer(Base):
    """
    Repräsentiert einen Benutzer der Plattform (LD01).
    """
    __tablename__ = 'Benutzer'
    userId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")
    smailAdresse = Column(String(255), unique=True, nullable=False)
    registrierungsdatum = Column(Date, nullable=False)

    # Beziehungen (1:n)
    textbeitraege = relationship("Textbeitrag", back_populates="ersteller")
    quelldateien = relationship("Quelldatei", back_populates="besitzer")


class LLMModell(Base):
    """
    Metadaten für ein Large Language Model (LD04).
    """
    __tablename__ = 'LLMModell'
    llmId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")
    modellName = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    typ = Column(String(50))

    # Beziehungen (1:n)
    textbeitraege = relationship("Textbeitrag", back_populates="llm_modell")


class TTSModell(Base):
    """
    Metadaten für ein Text-to-Speech (TTS) Modell (LD05).
    """
    __tablename__ = 'TTSModell'
    modellId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")
    modellName = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    typ = Column(String(50))

    # Beziehungen (1:n)
    konvertierungsauftraege = relationship("Konvertierungsauftrag", back_populates="tts_modell")


# --- 2. Inhalts- & Quelldaten ---

class Textbeitrag(Base):
    """
    Speichert den Generierungsvorgang eines Skripts (LD02).
    """
    __tablename__ = 'Textbeitrag'
    textId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    userId = Column(Integer, ForeignKey('Benutzer.userId'), comment="FK")
    llmId = Column(Integer, ForeignKey('LLMModell.llmId'), comment="FK")

    userPrompt = Column(Text)
    erzeugtesSkript = Column(Text, nullable=False)
    titel = Column(String(255), nullable=False)
    erstelldatum = Column(Date, nullable=False)
    sprache = Column(String(10), nullable=False)
    loeschzeitpunkt = Column(Date)

    # Beziehungen (n:1)
    ersteller = relationship("Benutzer", back_populates="textbeitraege")
    llm_modell = relationship("LLMModell", back_populates="textbeitraege")

    # Beziehungen (1:n)
    quelldateien = relationship("Quelldatei", back_populates="textbeitrag")
    konvertierungsauftraege = relationship("Konvertierungsauftrag", back_populates="textbeitrag")


class Quelldatei(Base):
    """
    Verwaltet Metadaten zu hochgeladenen Dateien (LD03).
    """
    __tablename__ = 'Quelldatei'
    dateiId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    textId = Column(Integer, ForeignKey('Textbeitrag.textId'), nullable=True, comment="FK")
    userId = Column(Integer, ForeignKey('Benutzer.userId'), nullable=True, comment="FK")

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
    """
    Steuert den Prozess der Audio-Erzeugung (LD06).
    """
    __tablename__ = 'Konvertierungsauftrag'
    auftragId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    textId = Column(Integer, ForeignKey('Textbeitrag.textId'), comment="FK")
    modellId = Column(Integer, ForeignKey('TTSModell.modellId'), comment="FK")

    gewuenschteDauer = Column(Integer, nullable=False)
    # Verwendung des Python Enum für den Status
    status = Column(Enum(AuftragsStatus), nullable=False)

    # Beziehungen (n:1)
    textbeitrag = relationship("Textbeitrag", back_populates="konvertierungsauftraege")
    tts_modell = relationship("TTSModell", back_populates="konvertierungsauftraege")

    # Beziehungen (1:n)
    stimmen = relationship("PodcastStimme", back_populates="auftrag")
    podcast = relationship("Podcast", back_populates="konvertierungsauftrag", uselist=False)  # 1:1


class Podcast(Base):
    """
    Repräsentiert das finale Audio-Produkt (LD08).
    """
    __tablename__ = 'Podcast'
    podcastId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    # 1:1 Beziehung zum Konvertierungsauftrag
    auftragId = Column(Integer, ForeignKey('Konvertierungsauftrag.auftragId'), unique=True, comment="FK")

    titel = Column(String(255), nullable=False)
    realdauer = Column(Integer, nullable=False)
    dateipfadAudio = Column(String(512), nullable=False)
    erstelldatum = Column(Date, nullable=False)
    isPublic = Column(Boolean, default=False, nullable=False)
    loeschzeitpunkt = Column(Date)

    # Beziehungen (n:1)
    konvertierungsauftrag = relationship("Konvertierungsauftrag", back_populates="podcast")


class PodcastStimme(Base):
    """
    Definiert eine Sprecherstimme und deren Rolle für einen Auftrag (LD07).
    """
    __tablename__ = 'PodcastStimme'
    stimmeId = Column(Integer, primary_key=True, autoincrement=True, comment="PK")

    # Fremdschlüssel
    auftragId = Column(Integer, ForeignKey('Konvertierungsauftrag.auftragId'), comment="FK")

    # Hat gefehlt
    name = Column(String(50), nullable=False, default="Max")

    ttsVoice = Column("tts_voice",String(50), nullable=True, default="de-DE-Chirp3-HD-Enceladus")

    rolle = Column(String(100), nullable=False)
    emotion = Column(String(100), nullable=False)
    geschlecht = Column(String(50), nullable=False)

    # Beziehungen (n:1)
    auftrag = relationship("Konvertierungsauftrag", back_populates="stimmen")
