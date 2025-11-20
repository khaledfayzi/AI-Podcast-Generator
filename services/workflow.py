# NOTE: Workflow Orchestrierung (Business Logic)
# Hier läuft alles zusammen. Diese Datei steuert den Ablauf "Prompt -> Audio".
# Sie verbindet die Datenbank, den LLM-Service und den TTS-Service.
#
# Einzufügen / Umzusetzen:
# - Klasse 'PodcastWorkflow':
#   - Initialisiert LLMService und TTSService.
#   - Methode 'run_pipeline(user_prompt)':
#     1. Ruft LLMService auf -> erhält Skript.
#     2. Speichert das Skript als 'Textbeitrag' in der DB.
#     3. Ruft TTSService auf -> erhält Audio-Pfad.
#     4. Speichert das Ergebnis als 'Podcast' in der DB.
#
# Dies ist die Schnittstelle, die später vom UI aufgerufen wird.