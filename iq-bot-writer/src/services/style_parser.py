import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)
import yaml


class StyleParser:
    def __init__(self):
        self.style_guide_path = Path(__file__).parent.parent.parent / 'resources' / 'style-guide' / 'guide.yaml'

    def load_style_guide(self) -> Dict[str, Any]:
        """Load and parse the style guide YAML file."""
        try:
            with open(self.style_guide_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load style guide: {str(e)}")
            return {}

    def get_style_guide(self) -> str:
        """Get formatted style guide as a string."""
        style_guide = self.load_style_guide()
        return yaml.dump(style_guide, default_flow_style=False)
