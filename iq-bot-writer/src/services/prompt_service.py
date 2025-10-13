"""Service for loading and managing prompts from templates."""
import json
import logging
import re
import uuid
from typing import Dict, Any, Optional, List, Set

from iq_bot_global.prompts import load_prompts
from iq_bot_global.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class PromptService:
    """Service for loading and validating prompts from templates."""

    def __init__(self):
        """Initialize the prompt service and generate initial prompts."""
        self.redis_service = RedisService()
        self.templates = load_prompts()
        # Generate prompts at startup
        self.initialize_prompts()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by its ID.
        
        Args:
            template_id: The ID of the template to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: The template if found, None otherwise
        """
        for template in self.templates.values():
            if template['id'] == template_id:
                return template
        return None

    def get_template_variables(self, template: Dict[str, Any]) -> Set[str]:
        """
        Extract all variables from a template.
        
        Args:
            template: The template to check
            
        Returns:
            Set[str]: Set of variable names found in the template
        """
        return set(re.findall(r'\{(\w+)\}', template['title']))

    def requires_parameters(self, template: Dict[str, Any]) -> bool:
        """
        Check if a template requires any parameters.
        
        Args:
            template: The template to check
            
        Returns:
            bool: True if the template requires parameters
        """
        return len(self.get_template_variables(template)) > 0

    def _generate_prompt_uuid(self, template: Dict[str, Any], parameters: Optional[Dict[str, str]] = None) -> str:
        """
        Generate a deterministic UUID based on template and parameters.
        Always returns the same UUID for the same input values.
        """
        # Create a unique string combining template id, topic, and parameters
        unique_string = f"{template['id']}:{template['topic']}"
        if parameters:
            param_string = ':'.join(f"{k}={v}" for k, v in sorted(parameters.items()))
            unique_string += f":{param_string}"
        # Use a constant namespace for deterministic UUIDs
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

    def initialize_prompts(self) -> None:
        """Initialize and cache all prompts from templates."""
        logger.info("Initializing prompts from templates...")
        prompt_count = 0

        for template in self.templates.values():
            try:
                if self.requires_parameters(template):
                    # Log warning for templates that need parameters
                    variables = self.get_template_variables(template)
                    logger.warning(
                        f"Template {template['id']} requires parameters: {', '.join(variables)}. "
                        "Skipping automatic initialization."
                    )
                    continue

                # For templates without parameters, we can generate and cache them
                generated_prompt_uuid = self._generate_prompt_uuid(template)
                cache_key = f"prompt:{template['id']}:{generated_prompt_uuid}"
                cached_prompt = self.redis_service.get_cached_response(cache_key)
                if cached_prompt:
                    logger.info(f"Prompt {template['id']} already cached. Skipping.")
                    continue

                prompt_data = {
                    'id': generated_prompt_uuid,
                    'prompt_template_id': template['id'],
                    'title': template['title'],
                    'topic': template['topic'],
                    'context_keys': template.get('context_keys', []),
                    'cache_key': template.get('cache_key', template['id']),
                    'ttl_seconds': template.get('ttl_seconds', 3600)
                }

                # Cache the prompt
                self.redis_service.set_cached_response(
                    cache_key,
                    json.dumps(prompt_data),
                    prompt_data['ttl_seconds']
                )
                prompt_count += 1

            except Exception as e:
                logger.error(f"Error initializing prompt for template {template['id']}: {e}")

        logger.info(f"Initialized {prompt_count} prompts from {len(self.templates)} templates")

    def get_prompt(self, template_id: str, parameters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get a prompt from a template, handling both parameterized and non-parameterized cases.
        
        Args:
            template_id: ID of the template to use
            parameters: Optional parameters to fill in template variables
            
        Returns:
            Dict[str, Any]: The processed prompt
            
        Raises:
            ValueError: If template not found or required parameters missing
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"No template found with id {template_id}")

        # Generate UUID for cache key lookup
        generated_prompt_uuid = self._generate_prompt_uuid(template, parameters)
        cache_key = f"prompt:{template_id}:{generated_prompt_uuid}"

        # For templates without parameters, try to get from cache
        if not self.requires_parameters(template):
            cached = self.redis_service.get_cached_response(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid cached prompt for {cache_key}, regenerating")

        # For templates with parameters, validate them
        variables = self.get_template_variables(template)
        if variables:
            if not parameters:
                raise ValueError(
                    f"Template {template_id} requires parameters: {', '.join(variables)}"
                )
            missing = variables - set(parameters.keys())
            if missing:
                raise ValueError(
                    f"Missing required parameters for template {template_id}: {', '.join(missing)}"
                )

        # Create the prompt data
        prompt_data = {
            'id': generated_prompt_uuid,
            'prompt_template_id': template['id'],
            'title': template['title'].format(**parameters) if parameters else template['title'],
            'topic': template['topic'],
            'context_keys': template.get('context_keys', []),
            'parameters': parameters,
            'cache_key': template.get('cache_key', template['id']),
            'ttl_seconds': template.get('ttl_seconds', 3600)
        }

        # Cache only if no parameters are required
        if not variables:
            self.redis_service.set_cached_response(
                cache_key,
                json.dumps(prompt_data),
                prompt_data['ttl_seconds']
            )

        return prompt_data

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available templates with their parameter requirements.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of templates with parameter info
        """
        result = {}
        for key, template in self.templates.items():
            vars = self.get_template_variables(template)
            result[key] = {
                **template,
                'requires_parameters': bool(vars),
                'required_parameters': list(vars) if vars else []
            }
        return result

    def list_cached_prompts(self) -> List[Dict[str, Any]]:
        """
        List all prompts currently cached in Redis.
        
        Returns:
            List[Dict[str, Any]]: List of cached prompts
        """
        cached_prompts = []
        for key in self.redis_service.get_keys("prompt:*"):
            cached = self.redis_service.get_cached_response(key)
            if cached:
                try:
                    prompt_data = json.loads(cached)
                    cached_prompts.append({
                        'cache_key': key,
                        **prompt_data
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Invalid cached prompt for {key}")
        return cached_prompts
