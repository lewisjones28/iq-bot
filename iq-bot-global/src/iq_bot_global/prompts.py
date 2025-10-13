"""Module for handling prompt-contents loading and management."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

logger = logging.getLogger(__name__)

prompts_path = Path(__file__).parent / 'resources' / 'prompt-templates.yaml'

def load_prompts() -> Dict[str, Any]:
    """
    Load all prompts from the prompt-templates.yaml configuration file.
    
    Returns:
        Dict[str, Any]: Dictionary containing all prompts and their configurations.

    Raises:
        FileNotFoundError: If prompt-templates.yaml doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        KeyError: If required 'prompts' key is missing
    """
    try:
        with open(prompts_path, 'r') as file:
            return yaml.safe_load(file)['prompts']
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")
        return {}


def get_prompt_by_id(prompt_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific prompt configuration by its unique identifier.
    
    Args:
        prompt_id: Unique identifier of the prompt to retrieve
        
    Returns:
        Optional[Dict[str, Any]]: Prompt configuration dictionary if found.

    Raises:
        yaml.YAMLError: If there's an error reading the prompts file
    """
    prompts = load_prompts()
    for prompt in prompts.values():
        if prompt['id'] == prompt_id:
            return prompt
    return None
