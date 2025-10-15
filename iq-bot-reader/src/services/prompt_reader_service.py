"""Service for fetching prompts."""
import json
import logging
from typing import Dict, Any, List

from iq_bot_global.constants import REDIS_KEYS
from iq_bot_global.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class PromptReaderService:
    """Service for generating and managing prompts from templates."""

    def __init__(self):
        self.redis_service = RedisService()

    def get_all_generated_prompts(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available prompts from cache.
        
        Returns:
            List[Dict[str, Any]]: List of all cached prompts
        """
        # Get all prompt keys using Redis pattern matching
        prompt_keys = self.redis_service.get_keys(f"{REDIS_KEYS.GENERATED_PROMPT_PREFIX}:*")

        if not prompt_keys:
            logger.error("No prompts found")
            return []

        prompts = []
        for key in prompt_keys:
            cached_prompt = self.redis_service.get_cached_response(key)
            if cached_prompt:
                try:
                    prompts.append(json.loads(cached_prompt))
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode cached prompt for key {key}")
                    continue

        return prompts

    def get_generated_prompts_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """
        Get a list of prompts filtered by topic.
        Args:
            topic (str): The topic to filter prompts by
        Returns:
            List[Dict[str, Any]]: List of prompts matching the topic
        """
        prompt_keys = self.redis_service.get_keys(f"{REDIS_KEYS.GENERATED_PROMPT_PREFIX}:*")
        if not prompt_keys:
            logger.error("No prompts found")
            return []
        prompts = []
        for key in prompt_keys:
            cached_prompt = self.redis_service.get_cached_response(key)
            if cached_prompt:
                try:
                    prompt = json.loads(cached_prompt)
                    if prompt.get("topic") == topic:
                        prompts.append(prompt)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode cached prompt for key {key}")
                    continue
        return prompts
