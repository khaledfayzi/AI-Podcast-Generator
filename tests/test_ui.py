import pytest
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.ui_fixtures import driver, gradio_server, mock_controller, reset_backend


def perform_login(driver):
    """
    Helper to log in the user.
    """
    email_input = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "[placeholder='dein.name@smail.th-koeln.de']")
        )
    )
    email_input.clear()
    email_input.send_keys("test@smail.th-koeln.de")

    request_btn = driver.find_element(
        By.XPATH, "//button[contains(., 'Code anfordern')]"
    )
    request_btn.click()

    code_input = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "[placeholder='Code aus der E-Mail']")
        )
    )
    code_input.send_keys("12345678")

    verify_btn = driver.find_element(By.XPATH, "//button[contains(., 'Anmelden')]")
    verify_btn.click()

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
        )
    )


def test_app_starts_on_login_page(driver, gradio_server):
    driver.get(gradio_server)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    login_header = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Login')]"))
    )
    assert login_header.is_displayed()

    home_elements = driver.find_elements(
        By.XPATH, "//h2[contains(., 'Deine Podcasts')]"
    )
    if len(home_elements) > 0:
        assert not home_elements[0].is_displayed()


def test_login_flow(driver, gradio_server):
    driver.get(gradio_server)
    perform_login(driver)

    home_header = driver.find_element(By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
    assert home_header.is_displayed()


def test_source_extraction_flow(driver, gradio_server):
    """
    Tests the flow: Upload File -> 'Quelle übernehmen' appears -> Click -> Preview shows mock text.
    """
    driver.get(gradio_server)
    perform_login(driver)

    # dummy file for upload
    dummy_file = os.path.abspath("temp_dummy_source.txt")
    with open(dummy_file, "w") as f:
        f.write("Dummy content")

    try:
        # Upload File (Gradio hides input[type=file], so we target it directly)
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(dummy_file)

        # Wait for 'Quelle übernehmen' button to appear
        btn_quelle = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[contains(., 'Quelle übernehmen')]")
            )
        )
        assert btn_quelle.is_displayed()

        btn_quelle.click()

        # Verify preview box appears with mock content
        # The mock returns "MOCK EXTRACTED TEXT CONTENT"
        preview_box = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//label[contains(., 'Quelle (Text')]//textarea")
            )
        )
        # Give Gradio a moment to update the value
        time.sleep(1)
        assert "MOCK EXTRACTED TEXT CONTENT" in preview_box.get_attribute("value")

        # Verify Topic is auto-filled if it was empty
        topic_input = driver.find_element(
            By.CSS_SELECTOR, "textarea[placeholder='Geben Sie das Thema ein...']"
        )
        assert "Mock Title from Source" in topic_input.get_attribute("value")

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)


def test_delete_podcast_home(driver, gradio_server):
    driver.get(gradio_server)
    perform_login(driver)

    # Ensure the test podcast exists initially
    podcast_card = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(., 'Test Podcast')]")
        )
    )

    # Find and click the delete button inside the card
    # Assuming 'Test Podcast' is the first card or unique
    delete_btn = driver.find_element(By.XPATH, "//button[contains(., '🗑️ Löschen')]")
    delete_btn.click()

    # Wait for the card to disappear
    WebDriverWait(driver, 5).until(
        EC.invisibility_of_element_located(
            (By.XPATH, "//h3[contains(., 'Test Podcast')]")
        )
    )

    # Verify list is empty text appears (or card is gone)
    no_podcasts_msg = driver.find_elements(
        By.XPATH, "//i[contains(., 'Noch keine Podcasts vorhanden')]"
    )
    if not no_podcasts_msg:
        # Or just verify the specific card is gone
        cards = driver.find_elements(By.XPATH, "//h3[contains(., 'Test Podcast')]")
        assert len(cards) == 0, "Podcast card should be removed after deletion"


def test_share_flow(driver, gradio_server):
    """
    Tests the Share page functionality.
    """
    driver.get(gradio_server)
    perform_login(driver)

    # Wait for podcast card to be visible (ensures list is loaded)
    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h3[contains(., 'Test Podcast')]")
            )
        )
    except Exception as e:
        # Debugging: check if empty list message is present
        if driver.find_elements(By.XPATH, "//i[contains(., 'Noch keine Podcasts')]"):
            pytest.fail("Test failed: Podcast list is empty, 'Test Podcast' not found.")
        raise e

    # Click Share on the home card (Use CSS Selector for robustness)
    share_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-share"))
    )
    # Ensure element is in view
    driver.execute_script("arguments[0].scrollIntoView(true);", share_btn)
    time.sleep(0.5)
    share_btn.click()

    # Wait for Share Page header
    share_header = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(., 'Podcast Teilen!')]")
        )
    )
    assert share_header.is_displayed()

    # Check that link input is present
    link_input = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#share_link_output textarea, #share_link_output input")
        )
    )
    assert "https://podcast-ai.dedyn.io/share/" in link_input.get_attribute("value")

    # Test 'Make Public' toggle
    toggle = driver.find_element(
        By.XPATH, "//label[contains(., 'Link öffentlich machen')]"
    )
    toggle.click()

    # Check status message updates
    status_msg = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.ID, "share_status_msg"))
    )
    assert "Link ist jetzt" in status_msg.text

    # Go back
    btn_back = driver.find_element(By.XPATH, "//button[contains(., 'Zurück')]")
    btn_back.click()

    # Verify back on home
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
        )
    )


def test_podcast_generation_flow(driver, gradio_server):
    """
    Tests the full creation flow: Input Topic -> Generate Script -> Generate Audio -> Player.
    """
    driver.get(gradio_server)
    perform_login(driver)

    topic_input = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "textarea[placeholder='Geben Sie das Thema ein...']")
        )
    )
    topic_input.send_keys("Selenium Test Topic")

    btn_script = driver.find_element(
        By.XPATH, "//button[contains(., 'Skript Generieren')]"
    )
    btn_script.click()

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(., 'Skript Bearbeiten')]")
        )
    )

    script_box = driver.find_element(By.CSS_SELECTOR, "textarea[data-testid='textbox']")
    assert "mock script" in script_box.get_attribute("value")

    btn_audio = driver.find_element(
        By.XPATH, "//button[contains(., 'Podcast Generieren')]"
    )
    btn_audio.click()

    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.ID, "player_title_header"))
    )

    audio_player = driver.find_element(By.TAG_NAME, "audio")
    assert audio_player is not None

    btn_back = driver.find_element(
        By.XPATH, "//button[contains(., 'Zurück zur Startseite')]"
    )
    btn_back.click()

    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(., 'Deine Podcasts')]")
        )
    )

    # Check that the new podcast appears in the list
    new_podcast = driver.find_element(
        By.XPATH, "//h3[contains(., 'Selenium Test Topic')]"
    )
    assert new_podcast.is_displayed()


def test_logout_flow(driver, gradio_server):
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
