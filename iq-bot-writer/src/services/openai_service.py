import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def generate_response(self, prompt_data: str, system: str) -> str:
        """Generate a response using OpenAI's API with style guide context."""
        try:
            logger.debug(f"Generating OpenAI response with system: {system} and prompt: {prompt_data}")
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt_data}
                ],
                temperature=0.3  # Randomness & Creativity (1.0 for full randomness)
            )
            response_content = response.choices[0].message.content
            logger.debug(f"Generated response: {response_content}")
            return response_content
        except Exception as e:
            error_msg = f"Failed to generate OpenAI response: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
