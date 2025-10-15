"""Module for managing prompt-related configuration."""

import os
import pathlib

TEMPLATES_PATH = os.path.join(
    pathlib.Path(__file__).parent,
    'resources',
    'prompt-templates.yaml'
)
