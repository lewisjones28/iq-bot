"""Utility functions for IQ."""
import logging
import re
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)


def extract_context_params(prompt_id: str, prompt_contexts: dict) -> Dict[str, Any]:
    """
    Dynamically extract parameters from prompt contexts and enrich with mappings.
    Handles both single values and comparison contexts where values need to reference each other.

     Args:
        prompt_id: The ID of the prompt being processed
        prompt_contexts: Dictionary containing context values for the prompt

    Returns:
        dict: Parameters extracted from contexts, enriched with mapped values.
    """
    params = {'id': prompt_id}

    def add_mapping(key: str, value: str, params: dict) -> None:
        """
        Add mappings for a single value to the params dict.

        Args:
            key: Base key name to use for mapped values
            value: ID to look up in mapping service
            params: Dictionary to add mapped values to.
        """

    for context in prompt_contexts.get("promptContexts", []):
        param_key = context["name"].rstrip('s')
        values = context["values"]
        if not values:
            continue

        # Store the primary value
        value = values[0]
        params[param_key] = value
        add_mapping(param_key, value, params)

    return params


def find_param_in_dict(param_name: str, data_dict: Dict[str, Any], path: str = '') -> tuple[bool, Any]:
    """
    Recursively search for a parameter in a nested dictionary.

    Args:
        param_name: The name of the parameter to find
        data_dict: The dictionary to search in
        path: Current path in the nested structure (for debugging)

    Returns:
        tuple: (bool, Any) where bool indicates if parameter was found and Any is the value if found
    """
    if not isinstance(data_dict, dict):
        return False, None

    # Check direct key match
    if param_name in data_dict:
        # If the value is a dict and it has the same key name as a property, use that property
        if isinstance(data_dict[param_name], dict) and param_name in data_dict[param_name]:
            return True, data_dict[param_name][param_name]
        return True, data_dict[param_name]

    # Recursively check nested dictionaries
    for key, value in data_dict.items():
        new_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            found, result = find_param_in_dict(param_name, value, new_path)
            if found:
                return True, result
        # Check if value is a list of dictionaries
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    found, result = find_param_in_dict(param_name, item, f"{new_path}[{i}]")
                    if found:
                        return True, result

    return False, None


def format_template_with_nested_params(template_str: str, params: Dict[str, Any]) -> str:
    """
    Format a template string using parameters that may be nested in dictionaries.
    
    Args:
        template_str: The template string containing {param_name} placeholders
        params: Dictionary containing parameters for template formatting, possibly nested
        
    Returns:
        str: The formatted string with all parameters replaced
    """
    format_params = {}
    required_params = extract_template_params(template_str)
    
    for param in required_params:
        found, value = find_param_in_dict(param, params)
        if found:
            format_params[param] = value
    
    return template_str.format(**format_params)


def validate_template_params(template_str: str, params: Dict[str, Any]) -> bool:
    """
    Validate that all required template parameters are available in the params dictionary.
    Recursively searches through nested dictionaries and lists to find parameters.

    Args:
        template_str: The template string containing {param_name} placeholders
        params: Dictionary containing parameters for template formatting

    Returns:
        True if all required parameters are available, False otherwise
    """
    required_params = extract_template_params(template_str)

    for param in required_params:
        found, _ = find_param_in_dict(param, params)
        if not found:
            logger.warning(f"Missing required parameter '{param}' in template params")
            return False

    return True


def extract_template_params(template_str: str) -> Set[str]:
    """
    Extract parameter names from a template string.
    e.g., "prompt:{id}:team:{team}:season:{season}" -> {'id', 'team', 'season'}

    Args:
        template_str: The template string containing parameters in {param_name} format

    Returns:
        Set[str]: Set of unique parameter names found in the template
    """
    return set(re.findall(r'\{([^}]+)\}', template_str))


def generate_param_combinations(data_sources: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate all combinations of parameters based on data sources.

    Args:
        data_sources: Dictionary mapping parameter names to their possible values
            e.g., {'team': [team1, team2], 'season': [2023, 2024]}

    Returns:
        List[Dict[str, Any]]: List of parameter combinations
            e.g., [{'team': team1, 'season': 2023}, {'team': team1, 'season': 2024}, ...]
    """
    if not data_sources:
        return [{}]  # Return single empty combination if no parameters needed

    # Convert data sources into list of (key, values) pairs
    items = list(data_sources.items())
    if not items:
        return [{}]

    # Start with first parameter's values
    param_name, values = items[0]
    combinations = [{param_name: value} for value in values]

    # Add each additional parameter's values
    for param_name, values in items[1:]:
        new_combinations = []
        for combo in combinations:
            for value in values:
                new_combo = combo.copy()
                new_combo[param_name] = value
                new_combinations.append(new_combo)
        combinations = new_combinations

    return combinations if combinations else [{}]
