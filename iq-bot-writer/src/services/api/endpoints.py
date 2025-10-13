"""Constants for the API endpoints."""

from typing import Final

# Cache duration constants
MINUTE: int = 60
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR
WEEK: int = 7 * DAY
MONTH: int = 30 * DAY

# Default TTL if not specified
DEFAULT_TTL_SECONDS: Final[int] = HOUR

# API Endpoints mapped to client methods
ENDPOINTS: Final[dict[str, dict[str, str | int]]] = {
    'get_characters': {
        'path': '/characters',
        'ttl_seconds': MONTH
    }
}


def get_endpoint_ttl(endpoint_name: str) -> int:
    """
    Get the cache Time-To-Live (TTL) duration for a specific API endpoint.
    
    Args:
        endpoint_name: Name of the endpoint to get TTL for (e.g., 'get_competition')
        
    Returns:
        int: TTL duration in seconds. Returns:
            - Configured TTL if endpoint exists in ENDPOINTS
            - DEFAULT_TTL_SECONDS (1 hour) if endpoint not found.
    """
    return ENDPOINTS.get(endpoint_name, {}).get('ttl_seconds', DEFAULT_TTL_SECONDS)


def get_endpoint_path(endpoint_name: str) -> str:
    """
    Get the URL path template for a specific API endpoint.
    
    Args:
        endpoint_name: Name of the endpoint to get path for (e.g., 'get_competition')
        
    Returns:
        str: URL path template with parameter placeholders.
        
    Raises:
        KeyError: If endpoint_name is not found in ENDPOINTS configuration
    """
    if endpoint_name not in ENDPOINTS:
        raise KeyError(f"Endpoint '{endpoint_name}' not found")
    return ENDPOINTS[endpoint_name]['path']
