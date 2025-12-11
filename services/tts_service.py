import uuid
import nltk
import logging
import io
import time

from dotenv import load_dotenv
from google.cloud import texttospeech
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from pydub import AudioSegment

# Eigene Imports
from team04.Interfaces.interface_tts_service import ITTSService
from team04.models import PodcastStimme
from exceptions import TTSServiceError

# Lädt Umgebungsvariablen (z.B. GOOGLE_APPLICATION_CREDENTIALS)
load_dotenv()

logger = logging.getLogger(__name__)


class GoogleTTSService(ITTSService):
    """
    Implementierung des TTS Services mittels Google Cloud TTS API.
    Nutzt 'Chirp' oder 'Neural2' Stimmen für hochwertige Sprachsynthese.

    Diese Klasse kümmert sich um:
    1. Die Authentifizierung bei Google.
    2. Das Aufteilen langer Texte (Chunking), um API-Limits zu umgehen.
    3. Das Zusammenfügen (Stitching) einzelner Audio-Schnipsel zu einer Datei.
    4. Fehlerbehandlung und Retries bei API-Überlastung.
    """

    def __init__(self):
        """
        Initialisiert den Google Text-to-Speech Client.

        Raises:
            TTSServiceError: Wenn der Client nicht initialisiert werden kann (z.B. fehlende Credentials).
        """
        try:
            # Erstellt den Client. Google sucht automatisch nach der Umgebungsvariable
            # GOOGLE_APPLICATION_CREDENTIALS für die Authentifizierung.
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            logger.error(f"Google TTS Client Initialisierungsfehler: {e}")
            raise TTSServiceError("Google Client konnte nicht starten.")

    def generate_audio(self, script_text: str, primary_voice: PodcastStimme,
                       secondary_voice: PodcastStimme = None) -> str | None:
        """
        Generiert eine Audiodatei aus dem übergebenen Skripttext.
        Unterstützt Dialoge zwischen zwei Stimmen und handhabt lange Texte automatisch.

        Ablauf:
        1. Text wird zeilenweise verarbeitet.
        2. Erkennung, welcher Sprecher (Primary/Secondary) gerade spricht.
        3. Text wird in API-konforme Häppchen (Chunks) geteilt.
        4. Audio wird von Google abgerufen und mittels pydub zusammengefügt.

        Args:
            script_text (str): Der komplette Text des Podcasts/Dialogs.
            primary_voice (PodcastStimme): Die Hauptstimme (Objekt mit Name/Eigenschaften).
            secondary_voice (PodcastStimme, optional): Eine zweite Stimme für Dialoge.

        Returns:
            str | None: Der Dateiname der generierten MP3-Datei oder None bei Fehler/leerem Ergebnis.
        """
        # Initialisiere ein leeres Audio-Segment, an das wir später anhängen
        combined_audio = AudioSegment.empty()

        # Konfiguration für die Audio-Ausgabe (hier MP3)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        lines = script_text.split('\n')
        has_generated_content = False

        # Mapping erstellen: Name des Sprechers -> Google Voice Parameter
        voice_params_map = {
            primary_voice.name: self._get_google_voice_params(primary_voice.name),
        }
        if secondary_voice:
            voice_params_map[secondary_voice.name] = self._get_google_voice_params(secondary_voice.name)

        # Standardmäßig mit der primären Stimme beginnen
        current_params = voice_params_map[primary_voice.name]

        logger.info(f"Sende {len(lines)} Zeilen an Google TTS API...")

        # Hauptschleife: Zeile für Zeile durchgehen
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            text_to_speak = line

            # --- Logik zur Sprechererkennung ---
            # Prüft, ob die Zeile mit "Name:" beginnt, um die Stimme zu wechseln.
            if secondary_voice and line.startswith(f"{primary_voice.name}:"):
                current_params = voice_params_map[primary_voice.name]
                # Entfernt den Präfix "Name:", damit er nicht mitgesprochen wird
                text_to_speak = line.split(":", 1)[1].strip()
            elif secondary_voice and line.startswith(f"{secondary_voice.name}:"):
                current_params = voice_params_map[secondary_voice.name]
                text_to_speak = line.split(":", 1)[1].strip()

            if not text_to_speak:
                continue

            # --- Chunking ---
            # Google hat ein Limit (oft 5000 Bytes). Wir splitten sicherheitshalber bei 4000 Zeichen.
            text_chunks = self._text_splitter(text_to_speak, max_chars=4000)

            for chunk in text_chunks:
                # --- Retry Mechanismus ---
                # Falls Google "Rate Limited" (429) oder "Service Unavailable" (503) sendet,
                # versuchen wir es bis zu 3 Mal erneut.
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # SSML (Speech Synthesis Markup Language) ermöglicht genauere Steuerung,
                        # hier nutzen wir es als Wrapper.
                        ssml_text = f"<speak>{chunk}</speak>"

                        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

                        # Der eigentliche API Call an Google
                        response = self.client.synthesize_speech(
                            input=synthesis_input,
                            voice=current_params,
                            audio_config=audio_config
                        )

                        # Umwandlung der Bytes (API Antwort) in ein pydub AudioSegment
                        segment = AudioSegment.from_file(io.BytesIO(response.audio_content), format="mp3")

                        # An das Gesamtaudio anhängen
                        combined_audio += segment
                        has_generated_content = True

                        # Wenn erfolgreich, brechen wir die Retry-Schleife ab
                        break

                    except (ResourceExhausted, ServiceUnavailable) as e:
                        # Exponential Backoff: Wartezeit erhöht sich bei jedem Fehlversuch
                        if attempt < max_retries - 1:
                            wait_time = 2 * (attempt + 1)
                            logger.warning(
                                f"Google Rate Limit (429/503). Warte {wait_time}s... (Versuch {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Endgültig gescheitert bei Chunk '{chunk[:15]}...': {e}")

                    except Exception as e:
                        # Andere Fehler (z.B. falsche Parameter) brechen sofort ab
                        logger.error(f"Unerwarteter Fehler bei Chunk '{chunk[:15]}...': {e}")
                        break

                # Kurze technische Pause, um die API nicht zu fluten
                time.sleep(0.3)

            # --- Pacing ---
            # Fügt eine kurze Stille (350ms) nach jedem Absatz/Satz ein, damit es natürlicher klingt.
            combined_audio += AudioSegment.silent(duration=350)

        if not has_generated_content:
            logger.warning("Es wurde kein Audio generiert.")
            return None

        # Speichert das fertig zusammengesetzte Audio
        return self._save_audio(combined_audio)

    @staticmethod
    def _text_splitter(text: str, max_chars: int) -> list[str]:
        """
        Teilt einen langen Text intelligent in kleinere Stücke auf.

        Logik:
        Nutzt NLTK (Natural Language Toolkit), um Sätze zu erkennen.
        Es wird versucht, den Text so aufzuteilen, dass Sätze nicht mittendrin
        abgeschnitten werden, solange das max_chars Limit nicht überschritten wird.

        Args:
            text (str): Der zu teilende Text.
            max_chars (int): Maximale Zeichenanzahl pro Chunk.

        Returns:
            list[str]: Liste der Text-Chunks.
        """
        if len(text) <= max_chars:
            return [text]

        chunks_list = []
        current_chunk_str = ""
        # Zerlegt Text in grammatikalisch korrekte Sätze
        sentence_list = nltk.sent_tokenize(text)

        for sentence in sentence_list:
            # Fall: Ein einzelner Satz ist bereits größer als das Limit (selten, aber möglich)
            if len(sentence) > max_chars:
                if current_chunk_str:
                    chunks_list.append(current_chunk_str)
                    current_chunk_str = ""
                chunks_list.append(sentence)  # Muss akzeptiert werden oder weiter gesplittet (hier vereinfacht)
                continue

            # Prüfen, ob der aktuelle Satz noch in den aktuellen Chunk passt
            if len(current_chunk_str) + len(sentence) < max_chars:
                current_chunk_str += " " + sentence
            else:
                # Chunk voll: Speichern und neuen beginnen
                chunks_list.append(current_chunk_str.strip())
                current_chunk_str = sentence

        # Den Rest hinzufügen
        if current_chunk_str:
            chunks_list.append(current_chunk_str.strip())

        return chunks_list

    def _get_google_voice_params(self, name: str):
        """
        Wählt die spezifische Google Voice Konfiguration basierend auf dem internen Namen.

        Hier werden die 'Chirp'-Modelle (Deutsch) verwendet, da diese besonders natürlich klingen.

        Args:
            name (str): Der Name des Sprechers (z.B. "Max").

        Returns:
            texttospeech.VoiceSelectionParams: Das Konfigurationsobjekt für die Google API.
        """
        # Hardcodiertes Mapping unserer Charaktere zu Google Stimmen IDs
        name_mapping = {
            "Max": "de-DE-Chirp3-HD-Enceladus",  # Tiefe, männliche Stimme
            "Tom": "de-DE-Chirp3-HD-Achird",  # Andere männliche Stimme
            "Sara": "de-DE-Chirp3-HD-Erinome",  # Weibliche Stimme
        }

        # Fallback auf Standardstimme, wenn Name unbekannt
        voice_name = name_mapping.get(name, "de-DE-Chirp3-HD-Enceladus")

        # Extrahiert den Sprachcode (de-DE) aus dem Namen
        lang_code = voice_name[:5]

        return texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=voice_name
        )

    @staticmethod
    def _save_audio(audio_obj: AudioSegment) -> str:
        """
        Speichert das AudioSegment Objekt als MP3 Datei auf der Festplatte.

        Args:
            audio_obj (AudioSegment): Das zusammengesetzte Audio-Objekt.

        Returns:
            str: Der generierte Dateiname.

        Raises:
            TTSServiceError: Bei Schreibfehlern auf der Festplatte.
        """
        try:
            filename = f"podcast_google_{uuid.uuid4()}.mp3"
            # Export mit fester Bitrate für Konsistenz
            audio_obj.export(filename, format="mp3", bitrate="192k")
            logger.info(f"Google TTS fertig: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Speichern fehlgeschlagen: {e}", exc_info=True)
            raise TTSServiceError(f"IO Fehler beim Speichern der Audio-Datei: {e}")