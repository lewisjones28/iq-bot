"""Writer service for generating and managing prompt-contents responses."""
import inspect
import logging
from typing import Any

logger = logging.getLogger(__name__)

from iq_bot_global import (
    get_prompt_by_id,
    RedisService,
    extract_context_params,
    build_single_context
)
from services.api.client import ApiClient
from services.openai_service import OpenAIService
from services.style_parser import StyleParser


class WriterService:
    """Service for handling prompt-contents generation and response caching."""

    def __init__(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        self.openai_service = OpenAIService()
        self.style_parser = StyleParser()
        self.api_client = ApiClient()

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

    def _get_context_data(self, context_key: str, params: dict) -> Any:
        """
        Get resources based on context key from configuration.
        Dynamically maps parameters from prompt contexts to method arguments
        and includes all enriched parameters in the result.

        Args:
            context_key: The method name to call on the client
            params: Dictionary of parameters extracted from prompt contexts

        Returns:
            Any: The resources returned from the client method, merged with all params

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
                # Remove '_id' suffix for matching
                base_name = param_name.replace('_id', '')
                # Check if we have this parameter in our contexts
                if base_name in params:
                    call_params[param_name] = params[base_name]

            # Get the raw response from the API
            raw_response = method(**call_params)
            return raw_response
        except AttributeError:
            raise ValueError(f"Method {context_key} not found in API client")
        except Exception as e:
            raise ValueError(f"Error calling {context_key}: {str(e)}")

    def _generate_response(self, prompt_id: str, context_values: dict) -> dict:
        """
        Generate a response for a specific combination of context values.
        
        Args:
            prompt_id: The ID of the prompt to use
            context_values: Dictionary with single values for each context
            
        Returns:
            dict: Response resources including the generated text and context values used
        """
        prompt_config = get_prompt_by_id(prompt_id)
        if not prompt_config:
            raise ValueError(f"No prompt found with ID: {prompt_id}")

        # Format the context values into the expected structure
        formatted_contexts = {
            "promptContexts": []
        }

        # Add main context
        for key, value in context_values.items():
            if not key.startswith("compared_") and not key.endswith("_compare"):
                formatted_contexts["promptContexts"].append({
                    "name": key,
                    "values": [value] if not isinstance(value, list) else value,
                    "compare": context_values.get(f"{key}_compare", False)
                })

                # If this is a comparison context, add the compared value
                if context_values.get(f"{key}_compare", False):
                    compared_value = context_values.get(f"compared_{key}")
                    if compared_value:
                        formatted_contexts["promptContexts"][-1]["compare_with"] = compared_value

        # Extract parameters and format cache key
        params = extract_context_params(prompt_id, formatted_contexts)

        # Store enriched params to use in context data later
        enriched_params = params.copy()

        # Use original params for cache key to maintain backwards compatibility
        cache_key = prompt_config["cache_key"].format(**params)

        # Check cache first
        logger.debug(f"Checking cache for key: {cache_key}")
        cached_response = self.redis_service.get_cached_response(cache_key)
        if cached_response:
            logger.info(f"Cache hit for key: {cache_key}")
            return {
                "response": cached_response.decode('utf-8'),
            }
        logger.debug(f"Cache miss for key: {cache_key}")

        # Get the style guide (only need to do this once)
        logger.debug(f"Loading style guide for prompt_id: {prompt_id}")
        style_guide = self.style_parser.get_style_guide()

        # Fetch resources based on context keys
        context_data = enriched_params.copy()  # Start with all enriched params
        for context_key in prompt_config["context_keys"]:
            api_data = self._get_context_data(context_key, enriched_params)
            # Store API response under the context key to avoid conflicts
            context_data[context_key] = api_data

        # Build prompts
        logger.debug(f"Building prompts for topic: {prompt_config['topic']}")
        prompt_data = self._build_prompt_data(prompt_config["topic"], context_data)
        prompt_question = prompt_config["title"].format(**context_data)
        system = self._build_system(prompt_question, style_guide)
        logger.debug(f"Prompts built successfully")

        # Generate response using OpenAI
        response = self.openai_service.generate_response(prompt_data, system)

        # Cache the response
        logger.debug(f"Caching response with key: {cache_key}")
        self.redis_service.set_cached_response(
            cache_key,
            response,
            prompt_config["ttl_seconds"]
        )
        logger.debug(f"Response cached successfully")

        return {
            "response": response
        }

    def _generate_responses(self, prompt_id: str, context: dict) -> list:
        """
        Recursively generate responses for all combinations of context values.
        
        Args:
            prompt_id: The ID of the prompt to use
            context: Dictionary of context values, where values can be single items or lists
            
        Returns:
            list: List of generated responses, one for each combination
        """
        responses = []

        # Create new context with this single value
        new_context = build_single_context(context)
        # Recursively process this new context
        sub_responses = self._generate_responses(prompt_id, new_context)
        responses.extend(sub_responses)
        # No more lists to process, generate response for this combination

        try:
            response_data = self._generate_response(prompt_id, context)
            responses.append(response_data)
        except Exception as e:
            logger.error(f"Error generating response for context {context}: {e}")
            responses.append({
                "error": str(e)})

        return responses


    def generate_prompt_response(self, prompt_id: str, prompt_contexts: dict) -> list:
        """
        Generate responses for all combinations of prompt contexts.

        Args:
            prompt_id: The ID of the prompt to use
            prompt_contexts: Dictionary containing context values for the prompt

        Returns:
            list: List of generated responses with their context values

        Raises:
            ValueError: If prompt not found or context resources invalid
        """

        # Generate responses recursively
        return self._generate_responses(prompt_id, prompt_contexts)
