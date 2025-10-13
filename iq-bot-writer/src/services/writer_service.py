"""Writer service for generating and managing prompt-contents responses."""
import json
import logging
from iq_bot_global import (
    RedisService,
    extract_context_params
)
from .api.client import ApiClient
from .openai_service import OpenAIService
from .style_parser import StyleParser
logger = logging.getLogger(__name__)


class WriterService:
    """Service for handling prompt-contents generation and response caching."""

    def __init__(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        self.openai_service = OpenAIService()
        self.style_parser = StyleParser()
        self.api_client = ApiClient()

    def generate_prompt_response(self, prompt_template_id: str, prompt_id: str) -> dict:
        """
        Generate a response using the cached prompt from Redis.

        Args:
            prompt_template_id: ID of the template to use for finding prompts
            prompt_id: The ID of the prompt to use

        Returns:
            dict: Generated response with metadata

        Raises:
            ValueError: If prompt not found or invalid
        """
        # Get prompt configuration from Redis
        redis_key = f"{prompt_template_id}:{prompt_id}"
        cached_prompt = self.redis_service.get_cached_response(redis_key)

        if not cached_prompt:
            logger.debug(f"No cached prompt found for key: {redis_key}")
            raise ValueError(f"No prompt found with key {redis_key}")

        try:
            # Parse and validate prompt configuration
            prompt_data = json.loads(cached_prompt.decode('utf-8'))
            required_fields = ['topic', 'title', 'context_keys']
            if not all(field in prompt_data for field in required_fields):
                raise ValueError(f"Invalid prompt configuration: missing required fields {required_fields}")

            # Generate response using prompt configuration
            response = self._process_cached_prompt(prompt_data)

            # Add metadata to response
            response.update({
                "prompt_id": prompt_id,
                "prompt_template_id": prompt_template_id,
                "topic": prompt_data['topic'],
                "context_keys": prompt_data['context_keys']
            })

            return response

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in cached prompt: {redis_key}")
            raise ValueError("Invalid prompt configuration format")
        except Exception as e:
            logger.error(f"Error generating response using cached prompt: {e}")
            raise

    def _process_cached_prompt(self, prompt_data: dict) -> dict:
        """
        Process a cached prompt and generate a response.

        Args:
            prompt_data: The cached prompt data

        Returns:
            dict: Generated response data
        """
        # Build context and get cache key
        params, cache_key = self._build_context(prompt_data)

        # Check cache if available
        if cache_key:
            cached_response = self.redis_service.get_cached_response(cache_key)
            if cached_response:
                return {"response": cached_response.decode('utf-8')}

        # Get API data for context
        context_data = self._get_api_data(params, prompt_data.get("context_keys", []))

        # Build prompt and system message
        prompt_content, system = self._build_prompt(prompt_data, context_data)

        # Generate response
        response = self.openai_service.generate_response(prompt_content, system)

        # Cache if cache key is available
        if cache_key:
            self.redis_service.set_cached_response(
                cache_key,
                response,
                prompt_data.get('ttl_seconds', 3600)
            )

        return {
            "response": response,
            "context_data": context_data
        }

    def _build_context(self, prompt_data: dict) -> tuple[dict, str]:
        """
        Build context data and cache key from prompt configuration.
        Ensures prompt_data has required context values.

        Args:
            prompt_data: The prompt configuration from Redis

        Returns:
            tuple[dict, str]: Context data and cache key
        """

        # Format contexts structure
        formatted_contexts = {
            "promptContexts": [
                {
                    "name": key,
                    "values": value if isinstance(value, list) else [value],
                    "compare": prompt_data.get('compare', False)
                }
                for key, value in prompt_data.items()
            ]
        }

        # Extract parameters for API calls and cache key
        params = extract_context_params(prompt_data['id'], formatted_contexts)
        cache_key = prompt_data['cache_key'].format(**params) if 'cache_key' in prompt_data else None

        return params, cache_key
