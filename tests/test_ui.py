import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.ui_fixtures import driver, gradio_server, mock_controller

def perform_login(driver):
    """
    Helper to log in the user, assuming the driver is already at the Login page.
    Uses the mock credentials and flow defined in conftest.py.
    """
    email_input = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[placeholder='dein.name@smail.th-koeln.de']"))
    )
    email_input.clear()
    email_input.send_keys("test@smail.th-koeln.de")

    request_btn = driver.find_element(By.XPATH, "//button[contains(., 'Code anfordern')]")
    request_btn.click()

    code_input = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[placeholder='Code aus der E-Mail']"))
    )
    code_input.send_keys("12345678")

    verify_btn = driver.find_element(By.XPATH, "//button[contains(., 'Anmelden')]")
    verify_btn.click()

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Deine Podcasts')]"))
    )


def test_app_starts_on_login_page(driver, gradio_server):
    """
    Verifies that the application starts specifically on the Login page
    and NOT the Home page.
    """
    driver.get(gradio_server)
    
    # Wait for page to be ready
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Assert we see the Login Header
    print("\n[Check] Looking for Login Header...")
    login_header = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Login')]"))
    )
    assert login_header.is_displayed(), "The Login header should be visible on startup"

    # Assert we don't see Home page unique elements
    home_elements = driver.find_elements(By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
    if len(home_elements) > 0:
        assert not home_elements[0].is_displayed(), "Home page content should be hidden on startup"


def test_login_flow(driver, gradio_server):
    """
    Tests the flow: Login Page -> Enter Email -> Get Code -> Enter Code -> Home Page.
    """
    driver.get(gradio_server)
    perform_login(driver)
    
    home_header = driver.find_element(By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
    assert home_header.is_displayed()


def test_navigation_header(driver, gradio_server):
    """
    Tests navigation from Home to 'Über' and 'Nutzungsbedingungen' pages and back.
    """
    driver.get(gradio_server)
    perform_login(driver)

    btn_uber = driver.find_element(By.XPATH, "//button[contains(., 'ℹ️ Über')]")
    btn_uber.click()
    
    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Über den KI Podcast Generator')]"))
    )
    
    driver.find_element(By.XPATH, "//button[contains(., 'Zurück')]").click()
    
    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Deine Podcasts')]"))
    )

    btn_nutzung = driver.find_element(By.XPATH, "//button[contains(., '⚖️ Nutzungsbedingungen')]")
    btn_nutzung.click()
    
    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Nutzungsbedingungen')]"))
    )
    
    driver.find_element(By.XPATH, "//button[contains(., 'Zurück')]").click()
    
    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Deine Podcasts')]"))
    )

def test_input_validation_empty_topic(driver, gradio_server):
    """
    Tests that clicking 'Skript Generieren' without a topic/file triggers a warning
    and does NOT navigate to the script editor.
    """
    driver.get(gradio_server)
    perform_login(driver)

    topic_input = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Geben Sie das Thema ein...']")
    topic_input.clear()

    btn_script = driver.find_element(By.XPATH, "//button[contains(., 'Skript Generieren')]")
    btn_script.click()

    home_header = driver.find_element(By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
    assert home_header.is_displayed()

    script_headers = driver.find_elements(By.XPATH, "//h2[contains(., 'Skript Bearbeiten')]")
    
    if len(script_headers) > 0:
        assert not script_headers[0].is_displayed(), "Should not navigate to Script Editor with empty input"

def test_podcast_generation_flow(driver, gradio_server):
    """
    Tests the full creation flow: Input Topic -> Generate Script -> Generate Audio -> Player.
    """
    driver.get(gradio_server)
    perform_login(driver)

    topic_input = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Geben Sie das Thema ein...']"))
    )
    topic_input.send_keys("Selenium Test Topic")

    btn_script = driver.find_element(By.XPATH, "//button[contains(., 'Skript Generieren')]")
    btn_script.click()

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Skript Bearbeiten')]"))
    )

    script_box = driver.find_element(By.CSS_SELECTOR, "textarea[data-testid='textbox']") 
    
    assert "mock script" in script_box.get_attribute("value")

    btn_audio = driver.find_element(By.XPATH, "//button[contains(., 'Podcast Generieren')]")
    btn_audio.click()

    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.ID, "player_title_header"))
    )
    
    audio_player = driver.find_element(By.TAG_NAME, "audio")
    assert audio_player is not None

    btn_back = driver.find_element(By.XPATH, "//button[contains(., 'Zurück zur Startseite')]")
    btn_back.click()

    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Deine Podcasts')]"))
    )


def test_home_podcast_play(driver, gradio_server):
    """
    Tests playing an existing podcast from the list.
    Relies on MOCK_PODCASTS from conftest.py containing 'Test Podcast'.
    """
    driver.get(gradio_server)
    perform_login(driver)

    podcast_card = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h3[contains(., 'Test Podcast')]"))
    )
    assert podcast_card.is_displayed()

    btn_play = driver.find_element(By.XPATH, "//button[contains(., '▶ Play')]")
    btn_play.click()

    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.ID, "player_title_header"))
    )
    
    driver.find_element(By.XPATH, "//button[contains(., 'Zurück zur Startseite')]").click()
    
    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Deine Podcasts')]"))
    )

def test_logout_flow(driver, gradio_server):
    """
    Tests that a logged-in user can log out and return to the Login page.
    """
    driver.get(gradio_server)
    perform_login(driver)

    logout_btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Logout')]"))
    )
    logout_btn.click()

    login_header = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Login')]"))
    )
    assert login_header.is_displayed()
