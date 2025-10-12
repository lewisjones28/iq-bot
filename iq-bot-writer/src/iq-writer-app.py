"""IQ Writer Application."""
import datetime
import logging
import os

from dotenv import load_dotenv

from services.writer_service import WriterService

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the writer service."""
    logger.info(f"Starting iq-writer-app at {datetime.datetime.now()}")

    writer_service = WriterService()

    # prompt-contents contexts - this would normally come from the API and config
    prompt_contexts = {
        "promptContexts": [

        ]
    }

    try:
        # Generate response using the writer service
        prompt_id = "5a6412f7-22b7-4a1a-8113-d36d4a9f0b6f"  # General statistics prompt-contents
        responses = writer_service.generate_prompt_response(prompt_id, prompt_contexts)
        logger.info(f"Generated responses: {responses}")
    except Exception as e:
        logger.error(f"Error generating response: {e}")

    logger.info(f"Finishing iq-writer-app at {datetime.datetime.now()}")


if __name__ == "__main__":
    main()
