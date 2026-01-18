import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Pfad anpassen, damit Module gefunden werden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from team04.services.tts_service import GoogleTTSService
from team04.database.models import PodcastStimme
from team04.services.exceptions import TTSServiceError


class TestGoogleTTSService(unittest.TestCase):

    def setUp(self):
        """
        Wird vor jedem Test ausgeführt.
        Hier patchen wir den Google Client weg.
        """
        # Patch startet hier
        self.patcher = patch(
            "team04.services.tts_service.texttospeech.TextToSpeechClient"
        )
        self.MockClient = self.patcher.start()

        # Wir konfigurieren den Mock so, dass er eine synthesize_speech Methode hat
        self.mock_instance = self.MockClient.return_value

        # Response simulieren: Ein Objekt mit .audio_content
        mock_response = MagicMock()
        # Wir geben ein valides minimales WAV zurück (Header + Stille), damit AudioSegment nicht meckert
        # 44 Bytes RIFF header für leeres WAV
        dummy_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        mock_response.audio_content = dummy_wav
        self.mock_instance.synthesize_speech.return_value = mock_response

        # Service instanziieren (nutzt jetzt den gemockten Client)
        self.service = GoogleTTSService()

    def tearDown(self):
        """
        Wird nach jedem Test ausgeführt.
        Patch wieder beenden.
        """
        self.patcher.stop()

    def test_generate_audio_simple(self):
        """
        Testet den einfachsten Fall: Ein Sprecher, kurzer Text.
        """
        # 1. Dummy Daten vorbereiten (keine DB nötig!)
        stimme1 = PodcastStimme(
            name="Hans",
            ttsVoice_de="de-DE-Wavenet-A",
            ttsVoice_en="en-US-Wavenet-A",
            geschlecht="m",
        )

        script = "Hans: Hallo Welt."

        # 2. Methode aufrufen
        audio = self.service.generate_audio(
            script_text=script, sprache="Deutsch", primary_voice=stimme1
        )

        # 3. Assertions (Überprüfungen)
        self.assertIsNotNone(audio)

        # Wurde synthesize_speech überhaupt aufgerufen?
        self.mock_instance.synthesize_speech.assert_called()

        # Prüfen wir die Parameter des letzten Aufrufs
        call_args = self.mock_instance.synthesize_speech.call_args
        kwargs = call_args.kwargs

        # Wurde die richtige Stimme gewählt?
        self.assertEqual(kwargs["voice"].name, "de-DE-Wavenet-A")
        self.assertEqual(kwargs["voice"].language_code, "de-DE")

    def test_ssml_generation_features(self):
        """
        Testet ob unsere SSML-Tags (Pause, Betonung) korrekt umgewandelt werden.
        """
        stimme1 = PodcastStimme(
            name="Lisa", ttsVoice_de="de-DE-C", ttsVoice_en="en-US-C", geschlecht="w"
        )

        # Input mit Custom-Tags
        script = "Lisa: Das ist **wichtig**. [pause: 1s] Und das ist *ok*."

        # Wir müssen hier ein bisschen "white-box" testen und schauen, was an die API geht
        self.service.generate_audio(script, "Deutsch", stimme1)

        call_args = self.mock_instance.synthesize_speech.call_args
        input_arg = call_args.kwargs["input"]
        ssml_sent = input_arg.ssml

        # Prüfen ob unsere Tags im SSML gelandet sind
        self.assertIn('<emphasis level="strong">wichtig</emphasis>', ssml_sent)
        self.assertIn('<break time="1s"/>', ssml_sent)
        self.assertIn('<emphasis level="moderate">ok</emphasis>', ssml_sent)
        self.assertIn("<speak>", ssml_sent)

    def test_dialog_switching(self):
        """
        Testet ob zwischen zwei Sprechern korrekt gewechselt wird.
        """
        stimme1 = PodcastStimme(
            name="A", ttsVoice_de="voice-A", ttsVoice_en="voice-A", geschlecht="m"
        )
        stimme2 = PodcastStimme(
            name="B", ttsVoice_de="voice-B", ttsVoice_en="voice-B", geschlecht="w"
        )

        script = """
        A: Hallo B.
        B: Hallo A.
        A: Tschüss.
        """

        self.service.generate_audio(script, "Deutsch", stimme1, stimme2)

        # Wir erwarten 3 Aufrufe an die API (A -> B -> A)
        # Hinweis: Der Service macht auch Calls für Pausen oder Silence, aber die eigentlichen Calls sollten 3 Text-Calls sein.
        # Da wir im Code chunking haben und dann Stille einfügen, schauen wir uns die Stimmen der Calls an.

        calls = self.mock_instance.synthesize_speech.call_args_list

        # Filtern wir nur die Calls, die eine 'voice' parameter haben (die Silence-Generierung macht das ggf. anders,
        # aber im Code oben sehen wir: audio_segments.append(AudioSegment.silent...))
        # Ah, der Code macht `AudioSegment.silent` lokal mit pydub, ruft dafür NICHT Google auf.
        # Also sollten wir exakt 3 Calls an Google haben.

        self.assertEqual(len(calls), 3)

        # 1. Call: Stimme A
        self.assertEqual(calls[0].kwargs["voice"].name, "voice-A")
        # 2. Call: Stimme B
        self.assertEqual(calls[1].kwargs["voice"].name, "voice-B")
        # 3. Call: Stimme A
        self.assertEqual(calls[2].kwargs["voice"].name, "voice-A")


if __name__ == "__main__":
    unittest.main()
