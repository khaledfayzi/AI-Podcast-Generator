# NOTE: TTS Service (Audioerzeugung)
# Kapselt die Logik für die Umwandlung von Text in Sprache (Text-to-Speech).

# Kommentare sind von KI generiert

import torch
import nltk  # Wird benötigt, um Texte sinnvoll in Sätze zu unterteilen
import numpy as np
import os
import time
from datetime import datetime
from pydub import AudioSegment  # Notwendig für den Export als MP3

from team04.Interfaces.interface_tts_service import ITTSService
from team04.models import PodcastStimme
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

OUTPUT_DIR = "test_podcasts"
LOG_FILE = "test_podcasts/generation_history.txt"


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
        print("Initializing TTSService...")

        # 1. Hardware checken und Konfiguration ermitteln
        use_small_models, device_type = self._check_hardware()

        print(f"--> Konfiguration: Gerät={device_type}, Kleine Modelle={use_small_models}")

        # 2. Modelle basierend auf Hardware laden
        preload_models(
            text_use_small=use_small_models,
            coarse_use_small=use_small_models,
            fine_use_small=use_small_models,
            text_use_gpu=(device_type == "cuda"),
            coarse_use_gpu=(device_type == "cuda"),
            fine_use_gpu=(device_type == "cuda")
        )

        self.output_dir = "test_podcasts"
        os.makedirs(self.output_dir, exist_ok=True)

        os.makedirs(OUTPUT_DIR, exist_ok=True)

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

                print(f"GPU erkannt: {name} ({vram_gb:.2f} GB VRAM)")

                device = "cuda"

                # ENTSCHEIDUNGSLOGIK:
                # Bark "Large" braucht ca. 10-12 GB VRAM um stabil zu laufen.
                # Alles unter 10 GB sollte lieber die "Small" Modelle nutzen,
                # um Out-Of-Memory (OOM) Abstürze zu verhindern.
                if vram_gb >= 10.0:
                    print("VRAM ausreichend: Nutze GROSSE Modelle für beste Qualität.")
                    use_small = False
                else:
                    print("⚠VRAM < 10GB: Nutze KLEINE Modelle zur Sicherheit.")
                    use_small = True
            else:
                print("Keine GPU gefunden (oder Treiber nicht erkannt). Nutze CPU.")

        except Exception as e:
            print(f"Fehler bei der Hardware-Erkennung: {e}. Fallback auf CPU.")

        return use_small, device

#------------------------------------------------------------------------------------

    def generate_audio(self, skript: str, hauptstimme: PodcastStimme, zweitstimme: PodcastStimme = None) -> str | None:
        """
        Hauptmethode zur Audioerzeugung.

        Unterscheidet zwei Fälle:
        1. Monolog: Wenn 'zweitstimme' None ist.
        2. Dialog: Wenn 'zweitstimme' gesetzt ist. Das Skript muss dann das Format "Name: Text" haben.

        Args:
            skript (str): Der zu sprechende Text.
            hauptstimme (PodcastStimme): Datenbank-Objekt der ersten Stimme.
            zweitstimme (PodcastStimme, optional): Datenbank-Objekt der zweiten Stimme.

        Returns:
            str: Absoluter Pfad zur generierten MP3-Datei.
            None: Falls ein Fehler auftrat.
        """

        # --- START ZEITMESSUNG ---
        start_time = time.time()
        timestamp_start = datetime.now().strftime("%H:%M:%S")
        print(f"\n--- Start Generierung um {timestamp_start} ---")

        # Konfiguration für die Generierung
        GEN_TEMP = 0.6  # Kreativität der KI (0.6 ist ein guter Standardwert für Stabilität)
        SILENCE = np.zeros(int(0.25 * SAMPLE_RATE))  # Erzeugt 0.25 Sekunden Stille als Array

        pieces = []  # Hier sammeln wir alle generierten Audio-Schnipsel (Numpy Arrays)

        # ---------------------------------------
        # FALL 1: Nur eine Stimme (Monolog)
        # ---------------------------------------
        if zweitstimme is None:
            print(f"Generiere Monolog für: {hauptstimme.name}")
            skript = skript.replace("\n", " ").strip()  # Zeilenumbrüche entfernen für flüssigen Text

            try:
                # Hole die technische Bark-ID (z.B. "v2/de_speaker_0") anhand des Namens
                voice_id = StimmenManager.get_voice_id(hauptstimme.name, sprache="ger")

                # Text in Sätze zerlegen, da Bark bei zu langen Texten halluziniert
                sentences = nltk.sent_tokenize(skript)

                for sentence in sentences:
                    # Audio für den einzelnen Satz generieren
                    audio_array = self.generate_sentence(sentence, voice_id, GEN_TEMP)
                    # Audio + Stille an die Liste anhängen
                    pieces += [audio_array, SILENCE.copy()]

            except Exception as e:
                print(f"Fehler im Monolog: {e}")
                return None

        # ---------------------------------------
        # FALL 2: Zwei Stimmen (Dialog)
        # ---------------------------------------
        else:
            print(f"Generiere Dialog zwischen {hauptstimme.name} und {zweitstimme.name}")

            # Technische IDs für beide Sprecher laden
            id_main = StimmenManager.get_voice_id(hauptstimme.name, sprache="ger")
            id_sec = StimmenManager.get_voice_id(zweitstimme.name, sprache="ger")

            # Skript zeilenweise verarbeiten, um Sprecherwechsel zu erkennen
            lines = skript.split('\n')

            for line in lines:
                line = line.strip()
                if not line: continue  # Leere Zeilen ignorieren

                current_voice_id = id_main  # Fallback auf Hauptstimme
                text_to_speak = line

                # Parsen des Formats "Name: Text"
                if line.startswith(f"{hauptstimme.name}:"):
                    current_voice_id = id_main
                    text_to_speak = line.split(":", 1)[1].strip()  # Alles nach dem ersten Doppelpunkt

                elif line.startswith(f"{zweitstimme.name}:"):
                    current_voice_id = id_sec
                    text_to_speak = line.split(":", 1)[1].strip()

                print(f"  -> {current_voice_id} spricht: '{text_to_speak[:20]}...'")

                # Auch Dialogzeilen können lang sein -> Unterteilen in Sätze
                sub_sentences = nltk.sent_tokenize(text_to_speak)
                for sub in sub_sentences:
                    try:
                        audio_array = self.generate_sentence(sub, current_voice_id, GEN_TEMP)
                        pieces += [audio_array, SILENCE.copy()]
                    except Exception as e:
                        print(f"Fehler bei Satz '{sub}': {e}")
                        continue

        # Prüfen, ob überhaupt Audio erzeugt wurde
        if not pieces:
            print("Kein Audio generiert.")
            return None

        # Alle Schnipsel zu einem langen Audio-Array zusammenfügen
        full_audio = np.concatenate(pieces)

        end_time = time.time()
        duration_seconds = end_time - start_time


        # Speichern und Pfad zurückgeben
        return self.save_audiofile(full_audio, duration_seconds)

    @staticmethod
    def generate_sentence(text, voice_id, temp):
        """
        Interne Hilfsmethode: Ruft die Bark-API für einen einzelnen Satz auf.

        Prozess:
        1. Text -> Semantische Tokens (Bedeutung/Rhythmus)
        2. Semantische Tokens -> Waveform (Rohes Audio)
        """
        semantic_tokens = generate_text_semantic(
            text,
            history_prompt=voice_id,  # Bestimmt die Stimmfarbe
            temp=temp,
            min_eos_p=0.05
        )
        return semantic_to_waveform(semantic_tokens, history_prompt=voice_id)

    def save_audiofile(self, audio_data_float,duration_sec):
        """
        Konvertiert das Roh-Audio (Float32) in MP3 und speichert es.

        Args:
            audio_data_float (np.array): Audio-Daten von Bark (Wertebereich -1.0 bis 1.0).

        Returns:
            str: Dateipfad zur erstellten MP3.
        """
        try:
            # Formatierung der Dauer (z.B. "1m_30s")
            minutes = int(duration_sec // 60)
            seconds = int(duration_sec % 60)
            duration_str = f"{minutes}m_{seconds}s"

            # 1. Konvertierung Float32 -> Int16 (PCM Standard)
            # Bark liefert Werte zwischen -1.0 und 1.0.
            # 16-Bit Audio geht von -32768 bis 32767.
            audio_data_int16 = (audio_data_float * 32767).astype(np.int16)

            # 2. Pydub AudioSegment erstellen
            sound = AudioSegment(
                audio_data_int16.tobytes(),
                frame_rate=SAMPLE_RATE,  # 24000 Hz bei Bark
                sample_width=2,  # 2 Byte = 16 Bit
                channels=1  # Mono (Wichtig! Sonst klingt es wie Mickey Mouse)
            )

            duration_readable = f"{minutes} min {seconds} sek"
            # --- A: DATEINAME GENERIEREN ---
            # Format: podcast_YYYY-MM-DD_HH-MM-SS_Dauer-XM_YS.mp3
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"podcast_{timestamp}_Dauer-{duration_str}.mp3"
            file_path = os.path.join(self.output_dir, file_name)

            # 4. Exportieren
            sound.export(file_path, format="mp3", bitrate="192k")

            print(f"Datei gespeichert: {file_path}")

            # --- B: LOGBUCH SCHREIBEN ---
            # Wir hängen eine Zeile an die Textdatei an
            log_entry = f"[{timestamp.replace('_', ' ')}] Datei: {file_name} | Dauer: {duration_readable}\n"

            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry)

            print(f"📝 Logbuch aktualisiert: {LOG_FILE}")
            return file_path

        except Exception as e:
            print(f"Fehler beim Speichern der Datei: {e}")
            return None


class StimmenManager:
    """
    Verwaltet das Mapping zwischen lesbaren Namen (Datenbank) und technischen IDs (Bark).
    """

    # Statische Liste der verfügbaren Stimmen
    VOICE_MAP = {
        # Deutsch
        "Max": "v2/de_speaker_0",
        "Sara": "v2/de_speaker_3",
        "Tom": "v2/de_speaker_1",
        "Corinna": "v2/de_speaker_8",
        # Englisch
        "Peter": "v2/en_speaker_1",
        "Glenn": "v2/en_speaker_2",
        "Lois": "v2/en_speaker_6",
    }

    @staticmethod
    def get_voice_id(name: str, sprache: str = "ger") -> str:
        """
        Holt die Bark-ID zu einem Namen.

        Args:
            name (str): Der Name des Sprechers (z.B. "Max").
            sprache (str): "ger" oder "eng" für Fallback-Logik.

        Returns:
            str: Die technische ID (z.B. "v2/de_speaker_0").
        """
        try:
            voice_id = StimmenManager.VOICE_MAP.get(name)

            # Fallback: Wenn Name nicht gefunden, nimm Standardstimme je nach Sprache
            if voice_id is None:
                if sprache == "ger":
                    return "v2/de_speaker_0"  # Standard Deutsch
                return "v2/en_speaker_1"  # Standard Englisch

            return voice_id
        except Exception as e:
            print(f"Fehler beim Stimme holen: {e}")
            return "v2/de_speaker_0"  # Absoluter Notfall-Fallback


# ==========================================
# TEST BEREICH (MAIN) von KI generiert
# ==========================================
if __name__ == "__main__":
    print("--- 🚀 STARTE TTS SERVICE TEST ---")
    print("Prüfe Hardware und generiere Test-Audio...\n")


    # 1. Mock-Klasse erstellen (Simuliert dein DB-Objekt für den Test)
    class MockStimme:
        def __init__(self, name):
            self.name = name  # Das ist das Feld, das der Service braucht


    # 2. Service starten
    # ACHTUNG: Hier solltest du gleich im Terminal sehen, ob er
    # deine AMD Karte ("cuda") oder die CPU wählt!
    service = BarkTTSService()

    max_stimme = PodcastStimme(
        name="Max",
        rolle="Host",
        emotion="neutral",
        geschlecht="male"
    )

    sara_stimme = PodcastStimme(
        name="Sara",
        rolle="Guest",
        emotion="happy",
        geschlecht="female"
    )

    # -------------------------------------------------
    # TEST 1: Kurzer Monolog
    # -------------------------------------------------
    print("\n[Test 1] Generiere Monolog (Max)...")
    text_mono = "Hallo! Ich teste gerade, ob die TTS-Engine funktioniert."

    file_path_mono = service.generate_audio(
        skript=text_mono,
        hauptstimme=max_stimme
    )

    if file_path_mono:
        print(f" Monolog fertig: {file_path_mono}")
    else:
        print(" Monolog fehlgeschlagen.")

    print("\n--- TEST ENDE ---")