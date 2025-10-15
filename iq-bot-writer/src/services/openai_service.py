import logging
import os

from openai import OpenAI

from iq_bot_global.constants import OPENAI_DEFAULTS

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def generate_response(self, prompt_data: str, system: str) -> str:
        """Generate a response using OpenAI's API with style guide context."""
        try:
            logger.debug(f"Generating OpenAI response with system: {system} and prompt: {prompt_data}")
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL") or OPENAI_DEFAULTS.MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt_data}
                ],
                temperature=OPENAI_DEFAULTS.TEMPERATURE  # Randomness & Creativity (1.0 for full randomness)
            )
            response_content = response.choices[0].message.content
            logger.debug(f"Generated response: {response_content}")
            return response_content
        except Exception as e:
            error_msg = f"Failed to generate OpenAI response: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
