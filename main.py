import logging
import sys
import os
from dotenv import load_dotenv

# --------------------------------------------------
# Logging Setup
# --------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MAIN_SCRIPT")


def main():
    """
    Starts the Podcast Generator UI.
    """
    # Load .env file explicitly
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(env_path)

    try:
        # Add project root to path to ensure imports work correctly
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Import Demo after path setup
        from team04.Frontend.ui import demo

        logger.info("Starting Gradio UI...")
        print("Starting Podcast Generator UI...")

        # Wir nehmen jetzt den Servernamen und den Port aus der .env Datei
        server_name = os.getenv("HOST", "127.0.0.1")
        server_port = int(os.getenv("PORT", "7860"))

        demo.queue()
        demo.launch(server_name=server_name, server_port=server_port)

    except Exception as e:
        logger.error(f"Failed to start UI: {e}", exc_info=True)
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
