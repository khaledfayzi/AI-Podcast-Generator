import pytest
import threading
import time
import sys
import os
import requests
from unittest.mock import MagicMock, patch
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure a dummy audio file exists for the player to "load"
MOCK_AUDIO_FILE = os.path.join(TEST_DIR, "test_podcast.mp3")
if not os.path.exists(MOCK_AUDIO_FILE):
    with open(MOCK_AUDIO_FILE, "wb") as f:
        f.write(b"ID3" + b"\x00"*10)  # Minimal header

MOCK_VOICES = (["Hans", "Greta"], ["Robot", "Alien"])

class MockBackend:
    """
    A stateful mock backend to allow testing of CRUD operations (Create, Delete)
    within the UI tests without needing a real database.
    """
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.podcasts = [
            {
                "id": 1, 
                "titel": "Test Podcast", 
                "dauer": "5:00", 
                "datum": "2025-01-01", 
                "path": MOCK_AUDIO_FILE,
                "sprache": "Deutsch",
                "sprecher": "Hans",
                "rollen": "Moderator"
            }
        ]
        self.counter = 2

    def get_podcasts(self, user_id):
        return self.podcasts

    def delete_podcast(self, pid, uid):
        initial_len = len(self.podcasts)
        self.podcasts = [p for p in self.podcasts if p['id'] != pid]
        return len(self.podcasts) < initial_len
    
    def save_podcast(self, script_text, thema, dauer, sprache, speaker1, speaker2, audio_obj, user_id, role1, role2):
        new_id = self.counter
        self.counter += 1
        
        # Simulate logic from controller
        new_pod = {
            "id": new_id,
            "titel": thema if thema else "Generated Podcast",
            "dauer": dauer if isinstance(dauer, str) else "5:00", 
            "datum": "2025-01-02",
            "path": MOCK_AUDIO_FILE,
            "sprache": sprache,
            "sprecher": speaker1,
            "rollen": role1
        }
        
        self.podcasts.append(new_pod)
        # Return path and data dict as controller does
        return MOCK_AUDIO_FILE, new_pod

    def process_source(self, file_path, url):
        return "MOCK EXTRACTED TEXT CONTENT", "Mock Title from Source"

# Singleton instance for the session
backend = MockBackend()

@pytest.fixture(scope="session")
def mock_controller():
    """
    Patches the controller functions globally for the test session using the MockBackend.
    """
    p1 = patch("frontend.controller.get_available_voices", return_value=MOCK_VOICES)
    p2 = patch("frontend.controller.get_podcasts_for_user", side_effect=backend.get_podcasts)
    p3 = patch("frontend.controller.request_login_code", return_value=(True, "Code sent!"))
    p4 = patch("frontend.controller.verify_login_code", return_value=(True, {"id": 1, "email": "test@smail.th-koeln.de"}, "Success"))
    p5 = patch("frontend.controller.generate_script", return_value="This is a mock script.")
    p6 = patch("frontend.controller.generate_audio_only", return_value="mock_audio_obj")
    p7 = patch("frontend.controller.save_generated_podcast", side_effect=backend.save_podcast)
    p8 = patch("frontend.controller.process_source_input", side_effect=backend.process_source)
    p9 = patch("frontend.controller.delete_podcast", side_effect=backend.delete_podcast)
    
    with p1, p2, p3, p4, p5, p6, p7, p8, p9:
        yield

@pytest.fixture(scope="function", autouse=True)
def reset_backend():
    """Resets the mock backend state before every test function."""
    backend.reset()

@pytest.fixture(scope="session")
def gradio_server(mock_controller):
    """
    Starts the Gradio app in a separate thread.
    """
    from frontend.ui import demo
    
    port = 7866  # Use a distinct port to avoid conflicts
    server_thread = threading.Thread(target=demo.launch, kwargs={
        "server_name": "127.0.0.1", 
        "server_port": port, 
        "prevent_thread_lock": True,
        "quiet": True
    })
    server_thread.start()
    
    base_url = f"http://127.0.0.1:{port}"
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(base_url)
            if response.status_code == 200:
                break
        except requests.ConnectionError:
            time.sleep(0.5)
    else:
        raise RuntimeError("Gradio server failed to start within timeout")

    yield base_url
    
    demo.close()

@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()