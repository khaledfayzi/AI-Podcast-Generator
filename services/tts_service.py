import nltk
import logging
import io
import time

from dotenv import load_dotenv
from google.cloud import texttospeech
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from pydub import AudioSegment

from Interfaces.IServices import ITTSService
from database.models import PodcastStimme
from .exceptions import TTSServiceError
from repositories.voice_repo import VoiceRepo
from database.database import get_db

load_dotenv()
logger = logging.getLogger(__name__)


class GoogleTTSService(ITTSService):
    """
    Implementiert den TTS-Service über die Google Cloud API.
    Features: Batching von Dialogen, intelligentes Chunking und Retry-Logik.
    """

    def __init__(self):
        """Initialisiert den Google-Client und prüft NLTK-Abhängigkeiten."""
        try:
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            logger.error(f"Google TTS Client init error: {e}")
            raise TTSServiceError("Google Client start failed.")

        # NLTK Daten für Satz-Tokenisierung nachladen, falls nötig
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab')

    def generate_audio(self, script_text: str, primary_voice: PodcastStimme,
                       secondary_voice: PodcastStimme = None) -> AudioSegment | None:
        """
        Wandelt ein Skript in ein Audio-Objekt um.

        Args:
            script_text: Der vollständige Dialogtext.
            primary_voice: Die Hauptstimme.
            secondary_voice: Optionale Zweitstimme.

        Returns:
            AudioSegment-Objekt oder None bei Fehler.
        """

        # 1. Konfiguration laden
        required_names = [primary_voice.name]
        if secondary_voice:
            required_names.append(secondary_voice.name)

        voice_params_map = self._get_voice_configs(required_names)

        # Fallback: Falls Stimme nicht in DB gefunden, nutze String aus Objekt
        if primary_voice.name not in voice_params_map:
            if primary_voice.ttsVoice:
                voice_params_map[primary_voice.name] = self._create_params_from_string(primary_voice.ttsVoice)
            else:
                raise TTSServiceError(f"Keine TTS-Konfiguration für '{primary_voice.name}' gefunden.")

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000,
            speaking_rate=0.92,
            effects_profile_id=['headphone-class-device']
        )

        # 2. Parsing & Batching
        # Wir gruppieren Sätze desselben Sprechers, um API-Calls zu sparen.
        dialog_blocks = []
        lines = script_text.split('\n')

        current_params = voice_params_map[primary_voice.name]
        current_text_buffer = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            next_params = current_params
            clean_text = line

            # Sprecherwechsel erkennen ("Name: Text")
            if line.startswith(f"{primary_voice.name}:"):
                next_params = voice_params_map[primary_voice.name]
                clean_text = line.split(":", 1)[1].strip()
            elif secondary_voice and line.startswith(f"{secondary_voice.name}:"):
                next_params = voice_params_map[secondary_voice.name]
                clean_text = line.split(":", 1)[1].strip()

            if not clean_text:
                continue

            # Wenn Sprecher wechselt: Alten Block speichern und neuen beginnen
            if next_params != current_params and current_text_buffer:
                dialog_blocks.append((current_params, " ".join(current_text_buffer)))
                current_text_buffer = []
                current_params = next_params

            current_text_buffer.append(clean_text)

        # Letzten Block hinzufügen
        if current_text_buffer:
            dialog_blocks.append((current_params, " ".join(current_text_buffer)))

        # 3. API Calls & Verarbeitung
        audio_segments = []

        for params, text_block in dialog_blocks:
            # Chunking: Lange Blöcke (>1000 Zeichen) sicher aufteilen
            chunks = self._text_splitter(text_block, max_chars=1000)

            for chunk in chunks:
                # Retry-Loop für API-Stabilität (z.B. bei Rate Limits)
                for attempt in range(3):
                    try:
                        synthesis_input = texttospeech.SynthesisInput(ssml=f"<speak>{chunk}</speak>")
                        response = self.client.synthesize_speech(
                            input=synthesis_input,
                            voice=params,
                            audio_config=audio_config
                        )
                        audio_segments.append(AudioSegment.from_file(io.BytesIO(response.audio_content), format="wav"))
                        break  # Erfolg -> Weiter zum nächsten Chunk
                    except (ResourceExhausted, ServiceUnavailable):
                        # Exponential Backoff
                        if attempt < 2:
                            time.sleep(2 * (attempt + 1))
                        else:
                            logger.error(f"TTS retries failed for chunk.")
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
                        break

                time.sleep(0.1)  # Kurze Pause zur API-Schonung

            # Natürliche Pause nach jedem Sprecherwechsel
            audio_segments.append(AudioSegment.silent(duration=400))

        if not audio_segments:
            return None

        # 4. Zusammenfügen ('sum' ist speichereffizienter als '+=' in Loops)
        combined_audio = sum(audio_segments, AudioSegment.empty())
        return combined_audio

    @staticmethod
    def _text_splitter(text: str, max_chars: int) -> list[str]:
        """Teilt Text intelligent an Satzgrenzen, um API-Limits einzuhalten."""
        if len(text) <= max_chars:
            return [text]

        chunks_list = []
        current_chunk_str = ""
        sentence_list = nltk.sent_tokenize(text)

        for sentence in sentence_list:
            # Falls ein einzelner Satz das Limit sprengt (extrem selten)
            if len(sentence) > max_chars:
                if current_chunk_str:
                    chunks_list.append(current_chunk_str)
                    current_chunk_str = ""
                chunks_list.append(sentence)
                continue

            # Passt der Satz noch in den aktuellen Chunk?
            if len(current_chunk_str) + len(sentence) < max_chars:
                current_chunk_str += " " + sentence
            else:
                chunks_list.append(current_chunk_str.strip())
                current_chunk_str = sentence

        if current_chunk_str:
            chunks_list.append(current_chunk_str.strip())

        return chunks_list

    def _get_voice_configs(self, names: list[str]) -> dict:
        """Lädt die technischen Stimmen-Parameter (z.B. 'de-DE-Wavenet-A') aus der DB."""
        voice_map = {}
        with get_db() as db:
            voice_repo = VoiceRepo(db)
            voices = voice_repo.get_voices_by_names(names)
            for voice in voices:
                if voice.ttsVoice:
                    voice_map[voice.name] = self._create_params_from_string(voice.ttsVoice)
        return voice_map

    @staticmethod
    def _create_params_from_string(tts_voice_string: str):
        """Erstellt das Google VoiceSelectionParams Objekt."""
        return texttospeech.VoiceSelectionParams(
            language_code=tts_voice_string[:5],
            name=tts_voice_string
        )