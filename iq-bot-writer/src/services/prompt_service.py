"""Service for generating and managing prompts."""
import hashlib
import json
import logging
import re
import uuid
from typing import Dict, Any, List, Set

from iq_bot_global.constants import REDIS_KEYS, CACHE_TTL
from iq_bot_global.services.redis_service import RedisService
from iq_bot_global.utils import (
    extract_template_params,
    generate_param_combinations,
    validate_template_params,
    format_template_with_nested_params
)
from services.prompt_template_service import PromptTemplateService

logger = logging.getLogger(__name__)


class PromptService:
    """Service for generating and managing prompts from templates."""

    def __init__(self):
        """Initialize the prompt service with required dependencies."""
        self.redis_service = RedisService()
        self.template_service = PromptTemplateService()



    def initialize_prompts(self, data_sources: Dict[str, List[Any]]):
        """Initialize all prompts from templates and cache them.

        Args:
            data_sources: Dictionary of data sources where keys are parameter names and values are lists
                        of possible values for that parameter. e.g., {'teams': [...], 'seasons': [...]}

        This should be called during application startup, not during service initialization.
        """
        logger.info("Initializing prompts from templates...")
        templates = self.template_service.load_templates()
        prompt_count = 0

        for topic, topic_data in templates.items():
            if not isinstance(topic_data, list):
                logger.warning(f"Expected list of templates for topic {topic}, got {type(topic_data)}")
                continue

            for template in topic_data:
                if not isinstance(template, dict) or 'id' not in template:
                    logger.warning(f"Invalid template format in topic {topic}: {template}")
                    continue

                template_id = template['id']

                # Get the enabled flag
                if not template['enabled']:
                    logger.warning(f"Template {template_id} is disabled, skipping generation")
                    continue

                try:
                    generated = self.generate_prompts_from_template(template_id, data_sources)
                    for prompt in generated:
                        prompt_id = prompt['id']
                        # Cache each prompt
                        self.redis_service.set_cached_response(
                            f"{REDIS_KEYS.GENERATED_PROMPT_PREFIX}:{template_id}:{prompt_id}",
                            json.dumps(prompt),
                            prompt.get('ttl_seconds', CACHE_TTL.DEFAULT)
                        )
                        prompt_count += 1
                except Exception as e:
                    logger.error(f"Error generating prompts for template {template_id}: {e}")
                    continue

        logger.info(f"Initialized {prompt_count} prompts from all templates")

    def generate_prompts_from_template(self, template_id: str, data_sources: Dict[str, List[Any]]) -> List[
        Dict[str, Any]]:
        """
        Generate prompts from a template with all possible combinations of parameters.

        Args:
            template_id: Unique identifier of the template to use for generation
            data_sources: Dictionary of data sources where keys are parameter names and values are lists
                        of possible values for that parameter

        Returns:
            List[Dict[str, Any]]: List of generated prompts with all combinations
        """
        template = self.template_service.get_template_by_id(template_id)
        if not template:
            raise ValueError(f"No template found with id {template_id}")

        # Extract parameters from cache key template
        cache_key_template = template.get('cache_key', '')
        required_params = extract_template_params(cache_key_template)
        logger.debug(f"Required parameters from cache key: {required_params}")

        # Filter data sources to only include required parameters
        template_data_sources = {}
        for param in required_params:
            if param == 'id':  # Skip special parameters
                continue
            # Convert parameter names to match data source keys (e.g., 'team' -> 'teams')
            param_key = param if param in data_sources else f"{param}s"
            if param_key in data_sources:
                template_data_sources[param] = data_sources[param_key]
            else:
                logger.warning(f"No data source available for parameter: {param}")

        # Generate parameter combinations
        param_combinations = generate_param_combinations(template_data_sources)
        logger.info(f"Generating {len(param_combinations)} combinations for template {template_id}")

        generated_prompts = []
        for params in param_combinations:
            try:
                # Create ID from available parameters dynamically
                id_parts = []
                for param_name, param_value in params.items():
                    if isinstance(param_value, dict) and 'id' in param_value:
                        id_parts.append(str(param_value['id']))
                    else:
                        id_parts.append(str(param_value))

                generated_prompt_id = str(uuid.uuid5(
                    uuid.UUID(template_id),
                    ':'.join(sorted(id_parts)) if id_parts else 'default'
                ))

                # Check cache
                cached_prompt = self.redis_service.get_cached_response(
                    f"{REDIS_KEYS.PROMPT_PREFIX}:{generated_prompt_id}")
                if cached_prompt:
                    try:
                        prompt_data = json.loads(cached_prompt)
                        generated_prompts.append(prompt_data)
                        continue
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid cached prompt for {generated_prompt_id}, regenerating")

                # Build format params for title dynamically
                format_params = {}
                for param_name, param_value in params.items():
                    # Remove trailing 's' if present to match template parameter names
                    template_param_name = param_name[:-1] if param_name.endswith('s') else param_name
                    if isinstance(param_value, dict):
                        # For dictionary parameters, add both the raw dict and common fields
                        format_params[template_param_name] = param_value[template_param_name]
                        for key, value in param_value.items():
                            if format_params[template_param_name] != value:
                                format_params[f"{template_param_name}_{key}"] = value
                    else:
                        format_params[template_param_name] = param_value

                # Generate title using available parameters
                try:
                    generated_title = template['title'].format(**format_params)
                except KeyError as e:
                    logger.warning(f"Missing required parameter for title: {e}")
                    continue

                # Format cache key with available parameters
                cache_key_params = {'id': generated_prompt_id}
                for param_name, param_value in params.items():
                    # Remove trailing 's' if present to match template parameter names
                    template_param_name = param_name[:-1] if param_name.endswith('s') else param_name
                    if isinstance(param_value, dict) and 'id' in param_value:
                        cache_key_params[template_param_name] = param_value['id']
                    else:
                        cache_key_params[template_param_name] = param_value

                cache_key_template = template.get('cache_key', '')
                if cache_key_template and validate_template_params(cache_key_template, cache_key_params):
                    response_cache_key = format_template_with_nested_params(cache_key_template, cache_key_params)
                else:
                    logger.warning("Invalid or missing cache key template parameters")
                    response_cache_key = ''

                # Build prompt data with all available parameters
                prompt_data = {
                    'id': generated_prompt_id,
                    'prompt_template_id': template_id,
                    'title': generated_title,
                    'topic': template['topic'],
                    'cache_key': response_cache_key,
                    'context_keys': template['context_keys'],
                    'ttl_seconds': template.get('ttl_seconds', 3600),
                    'enabled': template.get('enabled', True)
                }

                # Add all parameters to prompt data
                for param_name, param_value in params.items():
                    if isinstance(param_value, dict):
                        # For dictionary parameters (like team), add both ID and full object
                        for key, value in param_value.items():
                            prompt_data[f"{param_name}_{key}"] = value
                    else:
                        prompt_data[param_name] = param_value

                generated_prompts.append(prompt_data)

            except Exception as e:
                logger.error(f"Error generating prompt for parameters {params}: {e}")
                continue

        return generated_prompts

    def get_generated_prompt(self, template_key: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a prompt from a template with the given parameters and cache the result.

        Args:
            template_key (str): Key of template to use
            params (Dict[str, Any], optional): Parameters to fill in template. Defaults to None.

        Returns:
            Dict[str, Any]: Dictionary containing generated prompt and metadata

        Raises:
            KeyError: If template_key not found or required parameter missing
        """
        # Generate cache key for this specific generated prompt
        params_hash = hashlib.md5(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()
        cache_key = f"{REDIS_KEYS.PROMPT_PREFIX}:{template_key}:{params_hash}"

        # Try to get from cache first
        cached_prompt = self.redis_service.get_cached_response(cache_key)
        if cached_prompt:
            try:
                return json.loads(cached_prompt)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode cached prompt for {template_key}, regenerating")

        # If not in cache, generate prompt from template
        template_config = self.template_service.get_template(template_key)
        if not template_config:
            raise KeyError(f"Template key '{template_key}' not found")

        template_config = template_config.copy()
        prompt_text = template_config.pop('prompt')  # Remove prompt text from config

        # Fill template parameters if provided
        if params:
            try:
                prompt_text = prompt_text.format(**params)
            except KeyError as e:
                raise KeyError(f"Missing required parameter: {e}")

        # Create generated prompt with metadata
        generated_prompt = {
            'prompt': prompt_text,
            'metadata': template_config
        }

        # Cache the generated prompt
        self.redis_service.set_cached_response(
            cache_key,
            json.dumps(generated_prompt),
            template_config.get("ttl_seconds", CACHE_TTL.DEFAULT)
        )

        return generated_prompt
