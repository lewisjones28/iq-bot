"""Writer service for generating and managing prompt-contents responses."""
import inspect
import json
import logging
from typing import Any

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
        redis_key = f"prompt:{prompt_template_id}:{prompt_id}"
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

    def _get_api_data(self, params: dict, context_keys: list) -> dict:
        """
        Fetch and transform API data for all required context keys.

        Args:
            params: Parameters extracted from context
            context_keys: List of API methods to call

        Returns:
            dict: Combined API response data
        """
        context_data = params.copy()

        for context_key in context_keys:
            api_data = self._get_context_data(context_key, params)
            context_data[context_key] = api_data

        return context_data

    def _get_context_data(self, context_key: str, params: dict) -> Any:
        """
        Get resources based on context key from configuration.
        Dynamically maps parameters from prompt contexts to method arguments
        and includes all enriched parameters in the result.

        Args:
            context_key: The method name to call on the API client
            params: Dictionary of parameters extracted from prompt contexts

        Returns:
            Any: The resources returned from the API client method, merged with all params

        Raises:
            ValueError: If method not found or parameters invalid
        """
        try:
            method = getattr(self.api_client, context_key)

            # Get the method's required parameters
            method_params = inspect.signature(method).parameters

            # Build parameters dictionary based on method's requirements
            call_params = {}
            for param_name in method_params:
                # Try exact match first
                if param_name in params:
                    call_params[param_name] = params[param_name]
                # If not found and param ends with '_id', try without '_id'
                elif param_name.endswith('_id'):
                    base_name = param_name[:-3]  # Remove '_id'
                    if base_name in params:
                        call_params[param_name] = params[base_name]

            # Get the raw response from the API
            raw_response = method(**call_params)
            return raw_response
        except AttributeError:
            raise ValueError(f"Method {context_key} not found in API client")
        except Exception as e:
            raise ValueError(f"Error calling {context_key}: {str(e)}")

    def _build_prompt(self, prompt_data: dict, context_data: dict) -> tuple[str, str]:
        """
        Build the final prompt and system message.

        Args:
            prompt_data: The prompt configuration
            context_data: The context data including API responses

        Returns:
            tuple[str, str]: The prompt content and system message
        """
        # Get style guide
        style_guide = self.style_parser.get_style_guide()

        # Build the content prompt with API data
        prompt_content = self._build_prompt_data(prompt_data['topic'], context_data)

        # Build the prompt question and system message
        prompt_question = prompt_data['title'].format(**context_data)
        system = self._build_system(prompt_question, style_guide)

        return prompt_content, system

    def _build_prompt_data(self, prompt_topic: str, context_data: dict) -> str:
        """Build prompt-contents resources using all context keys from the resources dictionary.""
        """
        with open(f'../resources/prompt-contents/{prompt_topic}.txt', 'r') as file:
            content_template = file.read()

        # Create formatting dictionary where each key is prefixed with 'f'
        format_dict = {
            f"f{key}": value
            for key, value in context_data.items()
        }

        try:
            return content_template.format(**format_dict)
        except KeyError as e:
            raise ValueError(f"Missing required key in template: {e}")

    def _build_system(self, question: str, style_guide: str) -> str:
        """Build system prompt-contents with style guide context."""
        with open('../resources/system/system.txt', 'r') as file:
            system_template = file.read()
        return system_template.format(
            fprompt=str(question),
            fstyle_guide=str(style_guide)
        )