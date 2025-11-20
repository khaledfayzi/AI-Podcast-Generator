# 📌 Implementierungs-Reihenfolge: KI Podcast Generator (Walking Skeleton)

Dieser Plan beschreibt die **strikte logische Reihenfolge**, in der die Dateien erstellt werden müssen — von hinten (Datenbank) nach vorne (UI).

---
# Ihr müsst noch eine .env datei erstellen mit den nötigen API Keys und DB Verbindungsdaten.

# 1. Das Daten-Fundament (Backend)

Ohne definierte Datenstrukturen kann nichts gespeichert werden.

## 1.1. Datenmodelle definieren (`models.py`)

**Ziel:** Strukturierung der Datenobjekte.

**Warum zuerst?**  
Als allererstes muss festgelegt werden, wie ein *Benutzer*, ein *Textbeitrag* oder ein *Podcast* aussieht.

**Inhalt:**  
Erstellung der Klassen für:
- Benutzer  
- Text  
- Auftrag  
- Podcast  

---

## 1.2. Datenbank-Verbindung herstellen (`database.py`)

Sobald die Modelle existieren, muss der Weg zur Datenbank geebnet werden.

**Ziel:**  
Die Anwendung muss sich beim Start mit der Datenbank verbinden können.

**Inhalt:**  
Funktion implementieren, die:
- die DB-Verbindung öffnet  
- die Modelle aus Schritt **1.1** registriert  

---

# 2. Die Kern-Logik (Services)

Bevor der Workflow gebaut werden kann, müssen die Funktionsbausteine existieren (Text-KI & Audio).

## 2.1. Text-KI simulieren (`services/llm_service.py`)

**Ziel:**  
Eine Funktion bereitstellen, die Text empfängt und ein *simuliertes Skript* zurückgibt.

**Warum Mock?**  
Damit der Workflow getestet werden kann, ohne echte API-Aufrufe oder Wartezeiten.

---

## 2.2. Audio-Erzeugung implementieren (`services/tts_service.py`)

**Ziel:**  
Eine Funktion bereitstellen, die Text in eine MP3-Datei umwandelt.

**Inhalt:**  
Basis-Implementierung, z. B. über Google TTS oder einen Dummy-TTS, der:
- eine Datei erzeugt  
- sie im Dateisystem ablegt  

---

# 3. Die Verknüpfung (Workflow)

Jetzt werden Datenbank und Services miteinander verdrahtet.

## 3.1. Prozess-Steuerung (`services/workflow.py`)

**Ziel:**  
Einen kompletten Ablauf definieren:

Input → KI → DB-Speichern → Audio → DB-Speichern


**Abhängigkeiten:**  
- Schritt 1 (Datenbank & Modelle)
- Schritt 2 (Services)

---

# 4. Die Oberfläche (Frontend)

Erst wenn die Logik steht, wird die Benutzeroberfläche gebaut.

## 4.1. Benutzeroberfläche erstellen (`ui.py`)

**Ziel:**  
Ein visuelles Fenster erstellen, das der Nutzer bedienen kann.

**Inhalt:**
- Eingabefeld für das Thema  
- Button **„Generieren“**  
- Audio-Player für das Ergebnis  

**Verknüpfung:**  
Der Button ruft den Workflow aus **3.1** auf.

---

# 5. Der Start (Main)

Hier wird die komplette Anwendung zusammengeführt.

## 5.1. Start-Skript erstellen (`main.py`)

**Ziel:**  
Alles in der richtigen Reihenfolge starten.

**Ablauf:**
1. Datenbank initialisieren (Schritt 1.2)  
2. UI laden (Schritt 4.1)  
3. Server starten  

---

# 🔗 Zusammenfassung der Abhängigkeiten

| Datei | Benötigt |
|-------|----------|
| `models.py` | — |
| `database.py` | `models.py` |
| `services/*` | — |
| `workflow.py` | `models.py`, `services/*` |
| `ui.py` | `workflow.py` |
| `main.py` | `database.py`, `ui.py` |
