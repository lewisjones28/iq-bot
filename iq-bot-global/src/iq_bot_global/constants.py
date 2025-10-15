"""Global constants shared across IQ services."""

from dataclasses import dataclass
from typing import Final


# File paths and directories
@dataclass(frozen=True)
class FilePaths:
    """File paths and directory constants."""
    RESOURCES_DIR: str = "resources"
    MAPPINGS_DIR: str = "mappings"
    PROMPT_CONTENTS_DIR: str = "prompt-contents"
    STYLE_GUIDE_DIR: str = "style-guide"
    SYSTEM_DIR: str = "system"

    # Files
    STYLE_GUIDE_FILE: str = "guide.yaml"
    SYSTEM_FILE: str = "system.txt"
    TEMPLATES_FILE: str = "prompt-templates.yaml"


FILE_PATHS = FilePaths()

# Redis constants
REDIS_KEY_PREFIX: Final[str] = "iq:"
REDIS_PROMPT_KEY: Final[str] = f"{REDIS_KEY_PREFIX}prompt:"
REDIS_GENERATED_PROMPT_KEY: Final[str] = f"{REDIS_KEY_PREFIX}generated-prompt:"
REDIS_API_CACHE_KEY: Final[str] = f"{REDIS_KEY_PREFIX}api:"


# Cache TTL and timeframes
@dataclass(frozen=True)
class CacheTTL:
    """Cache time-to-live constants in seconds."""
    DEFAULT: int = 3600  # 1 hour
    HOUR: int = 3600
    DAY: int = 86400
    WEEK: int = 604800


CACHE_TTL = CacheTTL()


# Redis configuration
@dataclass(frozen=True)
class RedisConfig:
    """Redis connection configuration defaults."""
    DEFAULT_HOST: str = "localhost"
    DEFAULT_PORT: int = 6379
    DEFAULT_PASSWORD: str = ""


REDIS_CONFIG = RedisConfig()


# Flask configuration
@dataclass(frozen=True)
class FlaskConfig:
    """Flask application configuration defaults."""
    DEFAULT_HOST: str = "0.0.0.0"
    DEFAULT_PORT: int = 6000


FLASK_CONFIG = FlaskConfig()


# Redis key patterns
@dataclass(frozen=True)
class RedisKeys:
    """Redis key patterns and prefixes."""
    PREFIX: str = "iq:"
    PROMPT_PREFIX: str = f"{PREFIX}prompt-response"
    GENERATED_PROMPT_PREFIX: str = f"{PREFIX}generated-prompt"
    API_CACHE_PREFIX: str = f"{PREFIX}api"


REDIS_KEYS = RedisKeys()


# API configuration
@dataclass(frozen=True)
class OpenAIDefaults:
    """OpenAI configuration defaults."""
    MODEL: str = "gpt-4.1-nano"
    TEMPERATURE: float = 0.4


OPENAI_DEFAULTS = OpenAIDefaults()


# API response messages
@dataclass(frozen=True)
class APIResponseMessages:
    """API response message templates."""
    DEFAULT_ERROR: str = "Sorry, I am unable to assist with this query right now."
    PROMPT_NOT_FOUND: str = "Prompt not found"
    PROMPT_NOT_FOUND_WITH_ID: str = "No template or prompt found with ID: {prompt_id}"
    RESPONSE_NOT_FOUND_WITH_ID: str = "No response found for prompt ID: {prompt_id}"
    FAILED_TO_LOAD: str = "Failed to load prompts"


API_RESPONSE_MESSAGES = APIResponseMessages()
