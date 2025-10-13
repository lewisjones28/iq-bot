"""Service for loading and managing prompt templates."""
import logging
from typing import Dict, Any, Optional

import yaml

from nrl_iq_global.prompts import TEMPLATES_PATH

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """Service for managing prompt templates."""

    def __init__(self):
        """Initialize the template service with caching."""
        self._templates_cache = None

    def load_templates(self) -> Dict[str, Any]:
        """
        Load prompt templates from YAML file with caching.
        
        Returns:
            Dict[str, Any]: Dictionary containing prompt templates and their configurations.
        """
        if self._templates_cache is not None:
            return self._templates_cache

        try:
            with open(TEMPLATES_PATH, 'r') as file:
                self._templates_cache = yaml.safe_load(file)['prompts']
                return self._templates_cache
        except Exception as e:
            logger.error(f"Error loading prompt templates: {e}")
            return {}

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific prompt template configuration by its unique identifier.
        
        Args:
            template_id: Unique identifier of the template to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Prompt template configuration dictionary if found.
        """
        templates = self.load_templates()
        for template in templates.values():
            if template['id'] == template_id:
                return template
        return None

    def get_template(self, template_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a prompt template by its key.
        
        Args:
            template_key: Key of the template to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Template configuration if found
        """
        templates = self.load_templates()
        return templates.get(template_key)

    def clear_cache(self) -> None:
        """Clear the template cache to force reloading from file."""
        self._templates_cache = None
