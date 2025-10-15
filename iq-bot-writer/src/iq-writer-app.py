"""IQ Writer Application."""
import datetime
import logging
import os

from dotenv import load_dotenv

from iq_bot_global.constants import REDIS_GENERATED_PROMPT_KEY
from services.prompt_service import PromptService
from services.prompt_template_service import PromptTemplateService
from services.writer_service import WriterService

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_services():
    """Initialize all required services and data."""
    logger.info("Initializing services...")
    prompt_service = PromptService()

    logger.info("Gathering data sources...")
    try:
        # Gather all required data upfront
        data_sources = {
        }
        logger.info("Generating initial prompts...")
        prompt_service.initialize_prompts(data_sources)
        logger.info("Successfully initialized all prompts")
    except Exception as e:
        logger.error(f"Error initializing prompts: {e}")
        raise


def main():
    """Main entry point for the writer service."""
    logger.info(f"Starting iq-bot-writer at {datetime.datetime.now()}")

    # Initialize all services and data
    initialize_services()

    writer_service = WriterService()
    template_service = PromptTemplateService()

    try:
        # Get all templates directly from template service
        templates = template_service.load_templates()
        total_prompts_processed = 0

        # Loop through all topics and their templates
        for topic, topic_templates in templates.items():
            if not isinstance(topic_templates, list):
                logger.warning(f"Invalid template format for topic {topic}, skipping")
                continue

            logger.info(f"Processing templates for topic: {topic}")

            for template in topic_templates:
                if not isinstance(template, dict) or 'id' not in template:
                    logger.warning(f"Invalid template in topic {topic}, skipping")
                    continue

                template_id = template['id']
                logger.info(f"Processing template {template_id}")

                # Get all prompts for this template from Redis
                redis_service = writer_service.redis_service
                prompt_keys = redis_service.get_keys(f"{REDIS_GENERATED_PROMPT_KEY}{template_id}:*")

                if not prompt_keys:
                    logger.warning(f"No prompts found for template {template_id}")
                    continue

                logger.info(f"Found {len(prompt_keys)} prompts for template {template_id}")

                # Generate responses for each prompt
                successful_prompts = 0
                for prompt_key in prompt_keys:
                    try:
                        # Extract prompt ID from key format "iq:generated-prompt:template_id:prompt_id"
                        parts = prompt_key.split(":")
                        if len(parts) < 4:
                            logger.error(f"Invalid prompt key format: {prompt_key}")
                            continue
                        # Take the last two parts as template_id and prompt_id
                        template_id_from_key, prompt_id = parts[-2:]

                        logger.info(f"Generating response for prompt {prompt_id} (template: {template_id})")
                        response = writer_service.generate_prompt_response(template_id, prompt_id)
                        logger.info(f"Successfully generated response {response} for prompt {prompt_id}")

                        successful_prompts += 1
                        total_prompts_processed += 1

                    except Exception as e:
                        logger.error(f"Error generating response for prompt {prompt_id}: {e}")
                        continue

                logger.info(
                    f"Completed template {template_id}: {successful_prompts}/{len(prompt_keys)} prompts processed successfully")

    except Exception as e:
        logger.error(f"Error in batch response generation: {e}")

    logger.info(f"Finishing iq-bot-writer at {datetime.datetime.now()}")
    logger.info(f"Total prompts processed successfully: {total_prompts_processed}")


if __name__ == "__main__":
    main()
