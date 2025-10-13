"""API client for accessing team-related endpoints."""

import json
import logging
from typing import Optional, Dict

import requests

from iq_bot_global import RedisService
from .config import ApiConfig
from .endpoints import get_endpoint_path, get_endpoint_ttl

logger = logging.getLogger(__name__)


class ApiClient:
    """Simple client for interacting with the API."""

    def __init__(self, config: Optional[ApiConfig] = None):
        """Initialize the API client."""
        self.config = config or ApiConfig()
        self.session = requests.Session()
        self.redis_service = RedisService()

    def _generate_cache_key(self, endpoint_name: str, **kwargs) -> str:
        """
        Generate a deterministic cache key for the request based on endpoint and parameters.
        
        Args:
            endpoint_name: Name of the endpoint being called
            **kwargs: Parameters being passed to the endpoint, which will be
                     sorted and incorporated into the cache key
            
        Returns:
            str: A unique, deterministic cache key.
        """
        # Sort kwargs for consistent cache keys
        param_string = ':'.join(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return f"api:{endpoint_name}:{param_string}"

    def _make_request(self, endpoint_name: str, **kwargs) -> Dict:
        """
        Make a request to the API with caching support.
        Handles cache lookup, API calls, and cache storage with error handling.

        Args:
            endpoint_name: Name of the endpoint to call
            **kwargs: Parameters to pass to the endpoint, which will be formatted
                     into the endpoint URL and used in cache key generation

        Returns:
            Dict: API response data, either from cache or fresh API call

        Raises:
            requests.exceptions.RequestException: If API request fails
            requests.exceptions.HTTPError: If API returns non-200 status
            json.JSONDecodeError: If response is not valid JSON
            KeyError: If endpoint configuration is missing.
        """
        # Get endpoint path and TTL
        endpoint_path = get_endpoint_path(endpoint_name)
        ttl = get_endpoint_ttl(endpoint_name)

        # Generate cache key
        cache_key = self._generate_cache_key(endpoint_name, **kwargs)

        # Try to get from cache first
        cached_response = self.redis_service.get_cached_response(cache_key)
        if cached_response:
            logger.info(f"Cache hit for {endpoint_name}")
            try:
                return json.loads(cached_response)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode cached response for {endpoint_name}: {e}")

        # If not in cache or cache decode failed, make the API request
        url = str(self.config.base_url + endpoint_path.format(**kwargs))
        logger.info(f"Cache miss, performing API request to URL: {url}")

        response = self.session.get(url)
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = response.json()

        try:
            # Cache the response as JSON string
            cached_data = json.dumps(data)
            self.redis_service.set_cached_response(cache_key, cached_data, ttl)
            logger.info(f"Cached response for {endpoint_name} with TTL {ttl}s")
        except (TypeError, json.JSONEncodeError) as e:
            logger.error(f"Failed to cache response for {endpoint_name}: {e}")

        return data

    def get_characters(self, ) -> Dict:
        """
        Get a list of all available characters.

        Returns:
            Dict: Characters available data

        Raises:
            requests.exceptions.RequestException: If API request fails
            requests.exceptions.HTTPError: If API returns non-200 status
            ValueError: If team_id is invalid
            KeyError: If required fields are missing in response.
        """
        endpoint_key = 'get_characters'
        try:
            return self._make_request(
                endpoint_key,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {endpoint_key}:  {str(e)}")
            raise
