# NOTE: LLM Service (Textgenerierung)
# Kapselt die Logik für die Interaktion mit Sprachmodellen (Large Language Models).
# Hier findet das Prompt Engineering statt.
#
# Einzufügen / Umzusetzen:
# - Klasse 'LLMService':
#   - Methode 'generate_script(prompt, language, ...)'
#   - MVP: Simuliert erst einmal nur die Antwort (Dummy-Text), um Kosten zu sparen.
#   - Später: Sendet den Prompt an die OpenAI API und gibt das bereinigte Skript zurück.
#   - Trennung von System-Prompt (Rollenbeschreibung) und User-Prompt.