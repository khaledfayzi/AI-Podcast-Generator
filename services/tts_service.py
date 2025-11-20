# NOTE: TTS Service (Audioerzeugung)
# Kapselt die Logik für die Umwandlung von Text in Sprache (Text-to-Speech).
# Abstrahiert den Anbieter (gTTS, ElevenLabs, OpenAI), damit er leicht tauschbar ist (QA-W-10).
#
# Einzufügen / Umzusetzen:
# - Klasse 'TTSService':
#   - Methode 'generate_audio(text, voice_id, ...)'
#   - Speichert die generierte Audio-Datei im Dateisystem (z.B. im Ordner /output).
#   - Gibt den Dateipfad zur erstellten MP3 zurück.
#   - MVP: Nutzung von gTTS (kostenlos).