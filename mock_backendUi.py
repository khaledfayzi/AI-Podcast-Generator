import gradio as gr
import time

MOCK_DB = [
    [1, "Tech Talk: AI Trends", "15 min", "2024-05-01", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"],
    [2, "History Hour: Rome", "45 min", "2024-05-02", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"],
]

def get_podcasts():
    return [row[1:4] for row in MOCK_DB]

def generate_script(thema, dauer, sprache):
   
    time.sleep(1.5) # Simulate work
    
    return thema

def generate_audio(text):
    time.sleep(1.5)
    
    return None

def get_audio_url_by_row_index(row_index: int):
    
    if 0 <= row_index < len(MOCK_DB):
        return MOCK_DB[row_index][4] # Index 4 is the URL
    return None