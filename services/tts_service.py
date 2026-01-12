import nltk
import logging
import io
import time
import re

from dotenv import load_dotenv
from google.cloud import texttospeech
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from pydub import AudioSegment

from Interfaces.IServices import ITTSService
from database.models import PodcastStimme
from .exceptions import TTSServiceError
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

        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab')

    def generate_audio(self, script_text: str, sprache: str, primary_voice: PodcastStimme,
                       secondary_voice: PodcastStimme = None) -> AudioSegment | None:
        """
        Wandelt ein Skript in ein Audio-Objekt um.
        Nutzt direkt die PodcastStimme-Objekte und wählt die ID basierend auf 'sprache'.
        """

        # 1. Konfiguration basierend auf der Sprache wählen
        is_de = sprache.lower() == "deutsch"

        p_id = primary_voice.ttsVoice_de if is_de else primary_voice.ttsVoice_en
        voice_params_map = {
            primary_voice.name: self._create_params_from_string(p_id)
        }

        if secondary_voice:
            s_id = secondary_voice.ttsVoice_de if is_de else secondary_voice.ttsVoice_en
            voice_params_map[secondary_voice.name] = self._create_params_from_string(s_id)

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000,
            speaking_rate=0.92,
            effects_profile_id=['headphone-class-device']
        )

        # 2. Parsing & Batching
        dialog_blocks = []
        lines = script_text.split('\n')

        current_params = voice_params_map[primary_voice.name]
        current_text_buffer = []

        for line in lines:
            line = line.strip()
            if not line: continue

            next_params = current_params
            clean_text = line

            if line.startswith(f"{primary_voice.name}:"):
                next_params = voice_params_map[primary_voice.name]
                clean_text = line.split(":", 1)[1].strip()
            elif secondary_voice and line.startswith(f"{secondary_voice.name}:"):
                next_params = voice_params_map[secondary_voice.name]
                clean_text = line.split(":", 1)[1].strip()

            if not clean_text: continue

            if next_params != current_params and current_text_buffer:
                dialog_blocks.append((current_params, " ".join(current_text_buffer)))
                current_text_buffer = []
                current_params = next_params

            current_text_buffer.append(clean_text)

        if current_text_buffer:
            dialog_blocks.append((current_params, " ".join(current_text_buffer)))

        # 3. API Calls & Verarbeitung
        audio_segments = []

        for params, text_block in dialog_blocks:
            chunks = self._text_splitter(text_block, max_chars=1000)

            for chunk in chunks:
                ssml_chunk = self._prepare_final_ssml(chunk)

                for attempt in range(3):
                    try:
                        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_chunk)
                        response = self.client.synthesize_speech(
                            input=synthesis_input,
                            voice=params,
                            audio_config=audio_config
                        )
                        audio_segments.append(AudioSegment.from_file(io.BytesIO(response.audio_content), format="wav"))
                        break
                    except (ResourceExhausted, ServiceUnavailable):
                        if attempt < 2:
                            time.sleep(2 * (attempt + 1))
                        else:
                            logger.error(f"TTS retries failed for chunk.")
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
                        break

                time.sleep(0.1)

            audio_segments.append(AudioSegment.silent(duration=200))

        if not audio_segments: return None

        combined_audio = sum(audio_segments, AudioSegment.empty())
        return combined_audio

    @staticmethod
    def _text_splitter(text: str, max_chars: int) -> list[str]:
        if len(text) <= max_chars: return [text]
        chunks_list = []
        current_chunk_str = ""
        sentence_list = nltk.sent_tokenize(text)
        for sentence in sentence_list:
            if len(current_chunk_str) + len(sentence) < max_chars:
                current_chunk_str += " " + sentence
            else:
                chunks_list.append(current_chunk_str.strip())
                current_chunk_str = sentence
        if current_chunk_str: chunks_list.append(current_chunk_str.strip())
        return chunks_list

    @staticmethod
    def _create_params_from_string(tts_voice_string: str):
        return texttospeech.VoiceSelectionParams(
            language_code=tts_voice_string[:5],
            name=tts_voice_string
        )

    def _prepare_final_ssml(self, text: str) -> str:
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        for p_text in paragraphs:
            if not p_text.strip(): continue
            sentences = nltk.sent_tokenize(p_text)
            s_joined = " ".join([f"<s>{s}</s>" for s in sentences])
            processed_paragraphs.append(f"<p>{s_joined}</p>")

            full_ssml = "".join(processed_paragraphs)

            # **Text** wird zu einer starken Betonung (höhere Lautstärke/langsameres Sprechen).
            full_ssml = re.sub(r'\*\*(.*?)\*\*', r'<emphasis level="strong">\1</emphasis>', full_ssml)

            # *Text* wird zu einer moderaten Betonung.
            full_ssml = re.sub(r'\*(.*?)\*', r'<emphasis level="moderate">\1</emphasis>', full_ssml)

            # 3. SPEZIAL-SHORTCODES (PAUSEN UND AUSSPRACHE)
            # Erlaubt Pausen wie [pause: 500ms] oder [pause: 1s].
            full_ssml = re.sub(r'\[pause:\s*(.*?)\]', r'<break time="\1"/>', full_ssml)

            # Buchstabiert den Inhalt (z.B. [spell: USA] -> U-S-A).
            full_ssml = re.sub(r'\[spell:\s*(.*?)\]', r'<say-as interpret-as="characters">\1</say-as>', full_ssml)

            # Löst das Problem mit Jahreszahlen (z.B. 1976 als "Neunzehnhundert..." statt "Eintausend...").
            full_ssml = re.sub(r'\[year:\s*(\d{4})\]', r'<say-as interpret-as="date" format="y">\1</say-as>', full_ssml)

            # Korrekte Aussprache von Zeitangaben (z.B. [dur: 2h 30m]).
            full_ssml = re.sub(r'\[dur:\s*(.*?)\]', r'<say-as interpret-as="duration">\1</say-as>', full_ssml)
        return f"<speak>{full_ssml}</speak>"