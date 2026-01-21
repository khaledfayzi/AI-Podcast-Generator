import pytest
import threading
import time
import sys
import os
import requests
from unittest.mock import MagicMock, patch
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

MOCK_AUDIO_FILE = os.path.join(TEST_DIR, "test_podcast.mp3")

MOCK_VOICES = (["Hans", "Greta"], ["Robot", "Alien"])

MOCK_PODCASTS = [
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

MOCK_GENERATED_PODCAST_RETURN = (
    "mock_audio.mp3",
    {
        "id": 2,
        "titel": "Generated Mock Podcast",
        "dauer": "5:00",
        "datum": "2025-01-01",
        "path": MOCK_AUDIO_FILE,
        "sprache": "Deutsch"
    }
)

@pytest.fixture(scope="session")
def mock_controller():
    """
    Patches the controller functions globally for the test session.
    Critically, this must happen BEFORE 'frontend.ui' is imported.
    """
    with patch("frontend.controller.get_available_voices", return_value=MOCK_VOICES), \
         patch("frontend.controller.get_podcasts_for_user", return_value=MOCK_PODCASTS), \
         patch("frontend.controller.request_login_code", return_value=(True, "Code sent!")), \
         patch("frontend.controller.verify_login_code", return_value=(True, {"id": 1, "email": "test@smail.th-koeln.de"}, "Success")), \
         patch("frontend.controller.generate_script", return_value="This is a mock script."), \
         patch("frontend.controller.generate_audio_only", return_value="mock_audio_obj"), \
         patch("frontend.controller.save_generated_podcast", return_value=MOCK_GENERATED_PODCAST_RETURN):
        
        yield

@pytest.fixture(scope="session")
def gradio_server(mock_controller):
    """
    Starts the Gradio app in a separate thread.
    """
    from frontend.ui import demo
    
    port = 7865
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
    # chrome_options.add_argument("--headless")  # Uncomment to run invisible

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()
