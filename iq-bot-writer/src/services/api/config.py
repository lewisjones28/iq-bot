import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ApiConfig:
    """Configuration for the API."""
    base_url: str = "https://api.com/api"
    username: str = os.getenv('API_KEY', '')

    @property
    def auth(self) -> tuple[str, str]:
        """Return the authentication tuple for requests."""
        return (self.username, self.password)

    @property
    def is_configured(self) -> bool:
        """Check if the API is properly configured."""
        return bool(self.username and self.password)
