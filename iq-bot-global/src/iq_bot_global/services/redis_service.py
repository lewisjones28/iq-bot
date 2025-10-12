"""Redis service for caching responses."""

import logging
import os
from typing import Optional

import redis
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class RedisService:
    """Service for handling Redis caching operations."""

    _instance = None

    def __new__(cls):
        """Implement singleton pattern to ensure only one Redis connection is created."""
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize Redis connection using environment variables."""
        if self._initialized:
            return

        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', ''),
            decode_responses=False
        )
        self._initialized = True

    def get_cached_response(self, cache_key: str) -> Optional[bytes]:
        """
        Get a cached response from Redis.
        
        Args:
            cache_key: The key to look up in Redis
            
        Returns:
            Optional[bytes]: The cached response if found, None otherwise
            
        Raises:
            redis.RedisError: If there's an error connecting to Redis
        """
        try:
            logger.debug(f"Fetching cache record from Redis for key {cache_key}")
            return self.redis_client.get(cache_key)
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            return None

    def set_cached_response(self, cache_key: str, response: str, ttl_seconds: int = 3600) -> bool:
        """
        Cache a response in Redis with TTL.
        
        Args:
            cache_key: The key to store the response under
            response: The response string or bytes to cache
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successfully cached, False if operation failed
            
        Raises:
            redis.RedisError: If there's an error connecting to Redis
            TypeError: If response cannot be encoded properly
        """
        try:
            logger.debug(f"Setting cache record to Redis for key {cache_key}")
            return self.redis_client.setex(
                cache_key,
                ttl_seconds,
                response.encode('utf-8') if isinstance(response, str) else response
            )
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            return False

    def delete_cached_response(self, cache_key: str) -> bool:
        """
        Delete a cached response from Redis.

        Args:
            cache_key: The key to delete from Redis

        Returns:
            bool: True if successfully deleted, False if operation failed

        Raises:
            redis.RedisError: If there's an error connecting to Redis
        """
        try:
            logger.debug(f"Deleting cache record from Redis for key {cache_key}")
            self.redis_client.delete(cache_key)
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            return False
