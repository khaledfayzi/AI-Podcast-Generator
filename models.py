from datetime import date
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated
from beanie import Document

# --- Hilfs-Typ für MongoDB ObjectIds ---
# Damit Pydantic die MongoDB "_id" als String behandeln kann,
# obwohl sie in der Datenbank als ObjectId gespeichert sind.
PyObjectId = Annotated[str, BeforeValidator(str)]


class AuftragsStatus(Enum):
    """
    Definiert die möglichen Zustände im Lebenszyklus eines Konvertierungsauftrags.

    Values:
        IN_BEARBEITUNG: Der Auftrag wurde erstellt und wird aktuell verarbeitet (z.B. TTS läuft).
        ABGESCHLOSSEN: Die Audiodatei wurde erfolgreich erstellt und ist bereit.
        FEHLGESCHLAGEN: Es trat ein Fehler auf (z.B. API-Timeout, ungültiges Format).
    """
    IN_BEARBEITUNG = "in Bearbeitung"
    ABGESCHLOSSEN = "Abgeschlossen"
    FEHLGESCHLAGEN = "Fehlgeschlagen"


class PodcastStimme(BaseModel):
    """
    Repräsentiert die Konfiguration einer Sprecherstimme (vgl. LD07).

    Hinweis zur Architektur:
    In diesem MongoDB-Schema wird diese Klasse als **Embedded Document** innerhalb
    von `Konvertierungsauftrag` verwendet. Es gibt keine eigene Collection dafür.
    Dies ermöglicht den performanten Zugriff auf alle Stimmen eines Auftrags ohne JOINs.

    Attributes:
        rolle (str): Die Rolle im Skript (z. B. 'Moderator', 'Experte', 'Kritiker').
        emotion (str): Die gewünschte Stimmung der Stimme (z. B. 'neutral', 'freudig').
        geschlecht (str): Das Geschlecht der Stimme (dient der Vorauswahl der KI-Stimme).
    """
    rolle: str = Field(..., description="Rolle im Skript, z.B. 'Erzähler'")
    emotion: str = Field(..., description="Gewünschte Emotion")
    geschlecht: str = Field(..., description="Geschlecht der Stimme")


# --- Collection Models (Haupt-Dokumente) ---

class Benutzer(Document):
    """
    Repräsentiert einen Benutzer der Plattform (vgl. LD01).

    Dies ist der zentrale Akteur. Die Authentifizierung erfolgt über die smailAdresse
    (Magic-Link Verfahren), daher werden keine Passwörter gespeichert.

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        smailAdresse (str): Hochschul-Mailadresse, dient als Identifikator für Login.
        registrierungsdatum (date): Datum der ersten Anmeldung/Registrierung.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    smailAdresse: str
    registrierungsdatum: date

    class Settings:
        name = "benutzer"


class LLMModell(Document):
    """
    Metadaten für ein Large Language Model (LLM) (vgl. LD04).

    Dient der Abstraktion des verwendeten KI-Modells für die Texterstellung.
    Unterstützt die Anforderung QA-W-10 (Austauschbarkeit der Komponenten).

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        modellName (str): Name des Modells (z. B. 'GPT-4', 'Llama 3').
        version (str): Versionierung, um Reproduzierbarkeit zu gewährleisten.
        typ (str): Art des Modells (z. B. 'Chat', 'Instruct').
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    modellName: str
    version: str
    typ: str

    class Settings:
        name = "llm_modelle"


class TTSModell(Document):
    """
    Metadaten für ein Text-to-Speech (TTS) Modell (vgl. LD05).

    Abstrahiert die genutzte Sprachsynthese-Engine. Ermöglicht den Wechsel
    des Anbieters (z. B. von OpenAI zu ElevenLabs) ohne Code-Änderung (QA-W-10).

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        modellName (str): Name der Engine (z. B. 'ElevenLabs Multilingual v2').
        version (str): Version der TTS-Engine.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    modellName: str
    version: str

    class Settings:
        name = "tts_modelle"


class Textbeitrag(Document):
    """
    Speichert den Generierungsvorgang eines Skripts (vgl. LD02).

    Verbindet den User-Input (Prompt) mit dem generierten Ergebnis.
    Dient als Basis für die spätere Audio-Konvertierung.

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        userId: PyObjectId: Referenz auf den Ersteller (Dokument in 'benutzer').
        llmId: PyObjectId: Referenz auf das verwendete Modell (Dokument in 'llm_modelle').
        userPrompt (Optional[str]): Die ursprüngliche Eingabe des Nutzers.
        erzeugtesSkript (str): Der vom LLM generierte Dialogtext.
        titel (str): Titel des Beitrags zur Anzeige in der UI.
        erstelldatum (date): Erstellungszeitpunkt.
        sprache (str): Gewählte Sprache (z. B. 'DE', 'EN').
        loeschzeitpunkt (date): Datum für automatische Bereinigung gemäß QA-S-30.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    userId: Optional[PyObjectId] = None
    llmId: Optional[PyObjectId] = None

    userPrompt: Optional[str] = None
    erzeugtesSkript: str
    titel: str
    erstelldatum: date
    sprache: str
    loeschzeitpunkt: date

    class Settings:
        name = "textbeitraege"


class Quelldatei(Document):
    """
    Verwaltet Metadaten zu hochgeladenen Dateien (vgl. LD03).

    Dateien dienen der Kontextanreicherung (RAG - Retrieval Augmented Generation).
    Sie können an einem Textbeitrag hängen oder in der User-Library liegen.

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        textId (Optional[PyObjectId]): Verweis auf einen spezifischen Textbeitrag (falls zutreffend).
        userId (Optional[PyObjectId]): Verweis auf den Besitzer (für User Library Funktion).
        dateipfad (str): Physischer Pfad zur Datei im Storage/Dateisystem.
        mimeType (str): Dateityp (z. B. 'application/pdf').
        dateigroesse (int): Größe in Bytes.
        dateiname (str): Ursprünglicher Dateiname beim Upload.
        loeschzeitpunkt (date): Datum für automatische Löschung (QA-S-30).
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    textId: Optional[PyObjectId] = None
    userId: Optional[PyObjectId] = None

    dateipfad: str
    mimeType: str
    dateigroesse: int
    dateiname: str
    loeschzeitpunkt: date

    class Settings:
        name = "quelldateien"


class Konvertierungsauftrag(Document):
    """
    Steuert den Prozess der Audio-Erzeugung (vgl. LD06).

    Verknüpft ein fertiges Skript (Textbeitrag) mit Audio-Parametern.
    Beinhaltet die Sprecherkonfiguration direkt als eingebettete Liste.

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        textId (PyObjectId): Referenz auf den Quelltext (Dokument in 'textbeitraege').
        modellId (PyObjectId): Referenz auf die TTS-Engine (Dokument in 'tts_modelle').
        gewuenschteDauer (int): Zielvorgabe für die Länge in Minuten.
        status (AuftragsStatus): Aktueller Fortschritt der Generierung.
        stimmen (List[PodcastStimme]): Liste der konfigurierten Sprecher (Embedded).
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    textId: Optional[PyObjectId] = None
    modellId: Optional[PyObjectId] = None
    gewuenschteDauer: int
    status: AuftragsStatus

    stimmen: List[PodcastStimme] = []

    class Settings:
        name = "auftraege"


class Podcast(Document):
    """
    Repräsentiert das finale Audio-Produkt (vgl. LD08).

    Enthält den Pfad zur generierten Datei und Statusinformationen.

    Attributes:
        id (PyObjectId): Die von MongoDB generierte eindeutige _id.
        auftragsId (PyObjectId): Referenz auf den Auftrag, aus dem der Podcast entstand.
        realdauer (int): Tatsächliche Laufzeit des Audios in Sekunden.
        dateipfadAudio (str): Pfad zur MP3/WAV-Datei.
        erstelldatum (date): Zeitpunkt der Fertigstellung.
        titel (str): Titel des Podcasts.
        isPublic (bool): Steuert die Sichtbarkeit für andere Nutzer (vgl. QA-S-10).
        loeschzeitpunkt (date): Datum für automatische Löschung (QA-S-30).
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    auftragsId: Optional[PyObjectId] = None
    realdauer: int
    dateipfadAudio: str
    erstelldatum: date
    titel: str
    isPublic: bool
    loeschzeitpunkt: date

    class Settings:
        name = "podcasts"