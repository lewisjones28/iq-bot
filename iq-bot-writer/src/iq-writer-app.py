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


def initialize_services():
    """Initialize all required services and data."""
    from services.prompt_service import PromptService

    logger.info("Initializing services...")
    prompt_service = PromptService()

    logger.info("Generating initial prompts...")
    try:
        prompt_service.initialize_prompts()
        logger.info("Successfully initialized all prompts")
    except Exception as e:
        logger.error(f"Error initializing prompts: {e}")
        raise


def main():
    """Main entry point for the writer service."""
    logger.info(f"Starting iq-writer at {datetime.datetime.now()}")

    # Initialize all services and data
    initialize_services()

    writer_service = WriterService()

    try:
        # Template ID for general information
        template_id = "5a6412f7-22b7-4a1a-8113-d36d4a9f0b6f"

        # Get all prompts for this template from Redis
        redis_service = writer_service.redis_service
        prompt_keys = redis_service.get_keys(f"{template_id}:*")

        if not prompt_keys:
            logger.error(f"No prompts found for template {template_id}")
            return

        logger.info(f"Found {len(prompt_keys)} prompts for template {template_id}")

        # Generate responses for each prompt
        for prompt_key in prompt_keys:
            try:
                # Extract prompt ID from key format "prompt:{template_id}:{id}"
                _, _, prompt_id = prompt_key.split(":", 2)

                logger.info(f"Generating response for prompt {prompt_id}")
                response = writer_service.generate_prompt_response(template_id, prompt_id)
                logger.info(f"Generated response for prompt {prompt_id}: {response}")

            except Exception as e:
                logger.error(f"Error generating response for prompt {prompt_id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error in batch response generation: {e}")

    logger.info(f"Finishing iq-writer at {datetime.datetime.now()}")


if __name__ == "__main__":
    main()
