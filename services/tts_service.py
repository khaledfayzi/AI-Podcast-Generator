# NOTE: TTS Service (Audioerzeugung)
# Kapselt die Logik für die Umwandlung von Text in Sprache (Text-to-Speech).

# Kommentare sind von KI generiert

import uuid
import torch
import nltk  # Wird benötigt, um Texte sinnvoll in Sätze zu unterteilen
import numpy as np
import os
import logging
from pydub import AudioSegment  # Notwendig für den Export als MP3

from team04.Interfaces.interface_tts_service import ITTSService
from team04.models import PodcastStimme
from exceptions import TTSServiceError

# Logger
logger = logging.getLogger(__name__)


os.environ["SUNO_OFFLOAD_CPU"] = "True"



# ------------------------------------ KI generiert
# FIX FÜR PYTORCH 2.6+ & BARK KOMPATIBILITÄT
# ------------------------------------
# Hintergrund: Bark verwendet alte Checkpoint-Dateien. Neuere PyTorch-Versionen
# blockieren das Laden aus Sicherheitsgründen (weights_only=True ist jetzt Standard).
# Wir müssen die Ladefunktion kurzzeitig "patchen", um das zu umgehen.
_original_load = torch.load


def _patched_load(*args, **kwargs):
    """
    Wrapper für torch.load, der weights_only=False erzwingt.
    Verhindert Abstürze beim Laden der Bark-Modelle.
    """
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)


torch.load = _patched_load
# ----------------------------------- Bis hier

from bark.generation import (
    generate_text_semantic,
    preload_models,
)
from bark.api import semantic_to_waveform
from bark import SAMPLE_RATE



class BarkTTSService(ITTSService):
    """
    Dienst für die Generierung von Sprache aus Text (Text-to-Speech).

    Verwendet das 'Bark'-Modell von Suno AI.
    Features:
    - Automatische Erkennung von Mono-Logs vs. Dialogen.
    - Speichern als MP3.
    - Nutzung von 'Small'-Modellen für CPU-Freundlichkeit.
    """

    def __init__(self):
        logger.info("Initializing TTSService...")  # <--- NEU: Logger statt print

        # 1. Hardware checken und Konfiguration ermitteln
        use_small_models, device_type = self._check_hardware()

        logger.info(f"--> Konfiguration: Gerät={device_type}, Kleine Modelle={use_small_models}")

        # 2. Modelle basierend auf Hardware laden
        preload_models(
            text_use_small=use_small_models,
            coarse_use_small=use_small_models,
            fine_use_small=use_small_models,
            text_use_gpu=(device_type == "cuda"),
            coarse_use_gpu=(device_type == "cuda"),
            fine_use_gpu=(device_type == "cuda")
        )

        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab')

#------------------------------------------------------------------------------
# Hat Ki generiert
    def _check_hardware(self):
        """
        Prüft GPU-Verfügbarkeit und VRAM-Größe.
        Returns:
            tuple: (use_small_models: bool, device_type: str)
        """
        # Standard: Vorsichtshalber CPU und kleine Modelle
        use_small = True
        device = "cpu"

        try:
            # Prüfen ob CUDA (NVIDIA) oder ROCm (AMD unter Linux) verfügbar ist
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                name = torch.cuda.get_device_name(0)

                # VRAM in GB umrechnen
                # total_memory gibt Bytes zurück -> / 1024^3 = GB
                vram_bytes = torch.cuda.get_device_properties(0).total_memory
                vram_gb = vram_bytes / (1024 ** 3)

                logger.info(f"GPU erkannt: {name} ({vram_gb:.2f} GB VRAM)")  # <--- NEU

                device = "cuda"

                # ENTSCHEIDUNGSLOGIK:
                if vram_gb >= 10.0:
                    logger.info("VRAM ausreichend: Nutze GROSSE Modelle für beste Qualität.") # <--- NEU
                    use_small = False
                else:
                    logger.warning("⚠ VRAM < 10GB: Nutze KLEINE Modelle zur Sicherheit.") # <--- NEU: Warning
                    use_small = True
            else:
                logger.info("Keine GPU gefunden (oder Treiber nicht erkannt). Nutze CPU.") # <--- NEU

        except Exception as e:
            logger.error(f"Fehler bei der Hardware-Erkennung: {e}. Fallback auf CPU.", exc_info=True)

        return use_small, device

#------------------------------------------------------------------------------------

    def generate_audio(self, skript: str, hauptstimme: PodcastStimme, zweitstimme: PodcastStimme = None) -> str | None:
        """
        Hauptmethode zur Audioerzeugung.
        ...
        """
        # Konfiguration für die Generierung
        GEN_TEMP = 0.6
        SILENCE = np.zeros(int(0.25 * SAMPLE_RATE))

        pieces = []

        # ---------------------------------------
        # FALL 1: Nur eine Stimme (Monolog)
        # ---------------------------------------
        if zweitstimme is None:
            skript = skript.replace("\n", " ").strip()

            try:
                voice_id = StimmenManager.get_voice_id(hauptstimme.name, sprache="ger")
                sentences = nltk.sent_tokenize(skript)

                for sentence in sentences:
                    audio_array = self._generate_sentence(sentence, voice_id, GEN_TEMP)
                    pieces += [audio_array, SILENCE.copy()]

            except Exception as e:
                logger.error(f"Kritischer Fehler im Monolog: {e}", exc_info=True)
                raise TTSServiceError(f"Monolog konnte nicht generiert werden: {e}")

        # ---------------------------------------
        # FALL 2: Zwei Stimmen (Dialog)
        # ---------------------------------------
        else:
            id_main = StimmenManager.get_voice_id(hauptstimme.name, sprache="ger")
            id_sec = StimmenManager.get_voice_id(zweitstimme.name, sprache="ger")

            lines = skript.split('\n')

            for line in lines:
                line = line.strip()
                if not line: continue

                current_voice_id = id_main
                text_to_speak = line

                if line.startswith(f"{hauptstimme.name}:"):
                    current_voice_id = id_main
                    text_to_speak = line.split(":", 1)[1].strip()

                elif line.startswith(f"{zweitstimme.name}:"):
                    current_voice_id = id_sec
                    text_to_speak = line.split(":", 1)[1].strip()

                logger.debug(f"  -> {current_voice_id} spricht: '{text_to_speak[:20]}...'")

                sub_sentences = nltk.sent_tokenize(text_to_speak)
                for sub in sub_sentences:
                    try:
                        audio_array = self._generate_sentence(sub, current_voice_id, GEN_TEMP)
                        pieces += [audio_array, SILENCE.copy()]
                    except Exception as e:
                        logger.error(f"Fehler bei Satz '{sub}': {e}", exc_info=True)
                        continue

        # Prüfen, ob überhaupt Audio erzeugt wurde
        if not pieces:
            logger.warning("Kein Audio generiert.")
            return None

        full_audio = np.concatenate(pieces)
        return self._save_audiofile(full_audio)

    @staticmethod
    def _generate_sentence(text, voice_id, temp):
        semantic_tokens = generate_text_semantic(
            text,
            history_prompt=voice_id,
            temp=temp,
            min_eos_p=0.05
        )
        return semantic_to_waveform(semantic_tokens, history_prompt=voice_id)

    def _save_audiofile(self, audio_data_float):
        try:
            audio_data_int16 = (audio_data_float * 32767).astype(np.int16)

            sound = AudioSegment(
                audio_data_int16.tobytes(),
                frame_rate=SAMPLE_RATE,
                sample_width=2,
                channels=1
            )

            file_name = f"podcast_{uuid.uuid4()}.mp3"
            file_path = os.path.join(file_name)

            sound.export(file_path, format="mp3", bitrate="192k")

            logger.info(f"Datei erfolgreich gespeichert: {file_path}") # <--- NEU
            return file_path

        except Exception as e:
            logger.error(f"Fehler beim Speichern der Datei: {e}", exc_info=True)
            raise TTSServiceError(f"Speichern fehlgeschlagen: {e}")


class StimmenManager:
    """
    Verwaltet das Mapping zwischen lesbaren Namen (Datenbank) und technischen IDs (Bark).
    """
    VOICE_MAP = {
        "Max": "v2/de_speaker_0",
        "Sara": "v2/de_speaker_3",
        "Tom": "v2/de_speaker_1",
        "Corinna": "v2/de_speaker_8",
        "Peter": "v2/en_speaker_1",
        "Glenn": "v2/en_speaker_2",
        "Lois": "v2/en_speaker_6",
    }

    @staticmethod
    def get_voice_id(name: str, sprache: str = "ger") -> str:
        try:
            voice_id = StimmenManager.VOICE_MAP.get(name)

            if voice_id is None:
                if sprache == "ger":
                    return "v2/de_speaker_0"
                return "v2/en_speaker_1"

            return voice_id
        except Exception as e:
            logger.error(f"Fehler beim Stimme holen: {e}", exc_info=True) # <--- NEU
            return "v2/de_speaker_0"