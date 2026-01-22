# AI Podcast Generator

Ein KI-gestütztes Tool zur automatischen Erstellung von Podcasts aus verschiedenen Quellen (PDFs, Webseiten, Text). Das System nutzt Google Gemini für die Inhaltserstellung und Google Cloud Text-to-Speech für die Audio-Synthese.

## 🚀 Features

*   **Quellen-Import:** Unterstützung für PDF-Dokumente, Webseiten-URLs und direkten Text-Input.
*   **KI-Skript-Generierung:** Nutzt Google Gemini Pro, um Inhalte zusammenzufassen und ein natürliches Podcast-Skript (Dialog oder Monolog) zu erstellen.
*   **High-Quality Audio:** Verwendet Google Cloud TTS für realistische Stimmen.
*   **Web-Interface:** Benutzerfreundliche Oberfläche basierend auf Gradio.
*   **Benutzerverwaltung:** Login-System und Datenbank-Integration.
*   **Email-Benachrichtigungen:** Integration von Mailgun.

## 📋 Voraussetzungen

Bevor du startest, stelle sicher, dass du folgende Accounts und Zugriffe hast:

1.  **Google Cloud Platform (GCP) Account:**
    *   Aktiviere die **Text-to-Speech API**.
    *   Aktiviere die **Vertex AI API / Gemini API**.
    *   Erstelle einen Service Account und lade den JSON-Key herunter (`google-credentials.json`).
    *   Besorge dir einen API Key für Gemini (`GEMINI_API_KEY`).
2.  **Mailgun Account (Optional):**
    *   Für Email-Funktionalitäten wird ein API Key und eine Domain benötigt.
3.  **Datenbank (MySQL):**
    *   Eine erreichbare MySQL-Datenbank.
    *   Falls die Datenbank auf einem entfernten Server liegt, wird ein SSH-Tunnel unterstützt.

## 🛠 Installation & Setup

### Option 1: Start mit Docker (Empfohlen)

1.  **Repository klonen:**
    ```bash
    git clone <repo-url>
    cd team04
    ```

2.  **Umgebungsvariablen konfigurieren:**
    Erstelle eine `.env` Datei im Hauptverzeichnis (siehe unten für Details).

3.  **Google Credentials:**
    Platziere deine `google-credentials.json` im Projektordner.

4.  **Starten:**
    ```bash
    docker-compose up --build
    ```
    Die Anwendung ist anschließend unter `http://localhost:7860` erreichbar.

### Option 2: Lokale Installation (Entwicklung)

1.  **System-Abhängigkeiten installieren:**
    *   Python 3.11+
    *   **FFmpeg** (wird für die Audio-Verarbeitung benötigt).
        *   Ubuntu/Debian: `sudo apt install ffmpeg`
        *   MacOS: `brew install ffmpeg`
        *   Windows: FFmpeg herunterladen und zum PATH hinzufügen.

2.  **Python-Dependencies installieren:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Datenbank initialisieren:**
    Stelle sicher, dass die DB-Verbindung in der `.env` korrekt ist.

4.  **Starten:**
    ```bash
    python main.py
    ```

## 🔑 Konfiguration (.env)

Erstelle eine `.env` Datei mit folgendem Inhalt (angepasst an deine Daten):

```ini
# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials.json  # Pfad im Docker Container
GOOGLE_KEY_LOCAL_PATH=./google-credentials.json             # Lokaler Pfad für Docker Volume
GEMINI_API_KEY=dein_gemini_api_key_hier

# Mailgun (Optional)
MAILGUN_API_KEY=dein_mailgun_key
MAILGUN_DOMAIN=deine_mailgun_domain

# Datenbank (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_USER=dein_db_user
DB_PASSWORD=dein_db_pw
DB_NAME=podcast_db

# SSH Tunnel (Falls DB remote ist)
SSH_HOST=remote.server.com
SSH_USER=ssh_user
SSH_KEY_PATH=/path/to/ssh/key
SSH_KEY_LOCAL_PATH=./id_rsa  # Lokaler Pfad zum SSH Key für Docker
```

## 📚 Verwendete APIs & Dienste

*   **Google Cloud Text-to-Speech:** Für die Generierung der Audiospuren.
*   **Google Gemini (Generative AI):** Für die Analyse der Quellen und das Schreiben des Podcast-Skripts.
*   **Mailgun:** Für den Versand von E-Mails (z.B. bei Passwort-Reset).
*   **MariaDB:** Zur Speicherung von Benutzern, Jobs und Podcast-Metadaten.

## 📂 Projektstruktur

*   `frontend/`: Gradio UI Code.
*   `services/`: Business Logic (TTS, LLM, Auth, etc.).
*   `database/`: Datenbank-Modelle und Initialisierung.
*   `repositories/`: Datenzugriffsschicht (DAL).
*   `Output/`: Generierte MP3-Dateien.
