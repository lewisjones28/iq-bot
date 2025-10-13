from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ApiConfig:
    """Configuration for the API."""
    base_url: str = "https://potterapi-fedeperin.vercel.app/en"
