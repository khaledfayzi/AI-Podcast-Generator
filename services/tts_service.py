import uuid
import nltk
import os
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

load_dotenv()

logger = logging.getLogger(__name__)



class GoogleTTSService(ITTSService):
    """
    Implementierung des TTS Services mittels Google Cloud TTS API (Chirp/Neural2).
    """

    def __init__(self):
        try:
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise TTSServiceError("Google Client konnte nicht starten.")

    def generate_audio(self, script_text: str, primary_voice: PodcastStimme,
                       secondary_voice: PodcastStimme = None) -> str | None:
        """
        Generiert Audio über die Google API mit SSML Support und Text-Chunking.
        """
        combined_audio = AudioSegment.empty()

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        lines = script_text.split('\n')
        has_generated_content = False

        voice_params_map = {
            primary_voice.name: self._get_google_voice_params(primary_voice.name),
        }
        if secondary_voice:
            voice_params_map[secondary_voice.name] = self._get_google_voice_params(secondary_voice.name)

        current_params = voice_params_map[primary_voice.name]

        logger.info(f"Sende {len(lines)} Zeilen an Google...")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            text_to_speak = line

            # Sprecherwechsel erkennen
            if secondary_voice and line.startswith(f"{primary_voice.name}:"):
                current_params = voice_params_map[primary_voice.name]
                text_to_speak = line.split(":", 1)[1].strip()
            elif secondary_voice and line.startswith(f"{secondary_voice.name}:"):
                current_params = voice_params_map[secondary_voice.name]
                text_to_speak = line.split(":", 1)[1].strip()

            if not text_to_speak:
                continue

            # Text splitten (Google Limit beachten)
            text_chunks = self._text_splitter(text_to_speak, max_chars=4000)

            for chunk in text_chunks:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # SSML Wrapper für den Chunk
                        ssml_text = f"<speak>{chunk}</speak>"

                        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

                        response = self.client.synthesize_speech(
                            input=synthesis_input,
                            voice=current_params,
                            audio_config=audio_config
                        )

                        segment = AudioSegment.from_file(io.BytesIO(response.audio_content), format="mp3")
                        combined_audio += segment
                        has_generated_content = True
                        break

                    except (ResourceExhausted, ServiceUnavailable) as e:
                        if attempt < max_retries - 1:
                            wait_time = 2 * (attempt + 1)
                            logger.warning(f"Google Rate Limit (429/503). Warte {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Endgültig gescheitert bei Chunk '{chunk[:15]}...': {e}")

                    except Exception as e:
                        logger.error(f"Fehler bei Chunk '{chunk[:15]}...': {e}")
                        break

                time.sleep(0.3)

            # Kurze Pause zwischen Sätzen/Zeilen
            combined_audio += AudioSegment.silent(duration=350)

        if not has_generated_content:
            return None

        return self._save_audio(combined_audio)

    @staticmethod
    def _text_splitter(text: str, max_chars: int) -> list[str]:
        """
        Teilt Text basierend auf Sätzen auf, um das Zeichenlimit einzuhalten.
        """
        if len(text) <= max_chars:
            return [text]

        chunks_list = []
        current_chunk_str = ""
        sentence_list = nltk.sent_tokenize(text)

        for sentence in sentence_list:
            if len(sentence) > max_chars:
                if current_chunk_str:
                    chunks_list.append(current_chunk_str)
                    current_chunk_str = ""
                chunks_list.append(sentence)
                continue

            if len(current_chunk_str) + len(sentence) < max_chars:
                current_chunk_str += " " + sentence
            else:
                chunks_list.append(current_chunk_str.strip())
                current_chunk_str = sentence

        if current_chunk_str:
            chunks_list.append(current_chunk_str.strip())

        return chunks_list

    def _get_google_voice_params(self, name: str):
        """
        Wählt die Google Voice Konfiguration basierend auf dem Namen.
        """
        name_mapping = {
            "Max": "de-DE-Chirp3-HD-Enceladus",
            "Tom": "de-DE-Chirp3-HD-Achird",
            "Sara": "de-DE-Chirp3-HD-Erinome",
        }

        voice_name = name_mapping.get(name, "de-DE-Chirp3-HD-Enceladus")
        lang_code = voice_name[:5]

        return texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=voice_name
        )

    @staticmethod
    def _save_audio(audio_obj: AudioSegment) -> str:
        try:
            filename = f"podcast_google_{uuid.uuid4()}.mp3"
            audio_obj.export(filename, format="mp3", bitrate="192k")
            logger.info(f"Google TTS fertig: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Speichern fehlgeschlagen: {e}", exc_info=True)
            raise TTSServiceError(f"IO Fehler: {e}")
