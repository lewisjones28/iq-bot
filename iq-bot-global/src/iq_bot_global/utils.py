"""Utility functions for IQ."""
import re
from typing import Dict, Any, List, Set


def build_comparison_context(
        base_context: Dict[str, Any],
        list_key: str,
        value1: Any,
        value2: Any
) -> Dict[str, Any]:
    """
    Build a context dictionary for comparing two values while preserving other contexts.
    This is used to set up comparisons between two items (e.g., teams, players).

    Args:
        base_context: Original context dictionary containing all context values
        list_key: Key of the list being compared (e.g., "teams", "players")
        value1: First value to compare (e.g., first team ID)
        value2: Second value to compare (e.g., second team ID)

    Returns:
        Dict[str, Any]: A new context dictionary with.
    """
    new_context = {k: v for k, v in base_context.items() if k != list_key}
    new_context[list_key] = value1
    new_context[f"compared_{list_key}"] = value2
    new_context[f"{list_key}_compare"] = True
    return new_context


def extract_context_params(prompt_id: str, prompt_contexts: dict) -> Dict[str, Any]:
    """
    Dynamically extract parameters from prompt contexts and enrich with mappings.
    Handles both single values and comparison contexts where values need to reference each other.

     Args:
        prompt_id: The ID of the prompt being processed
        prompt_contexts: Dictionary containing context values for the prompt

    Returns:
        dict: Parameters extracted from contexts, enriched with mapped values.
        For comparison contexts (compare=True), includes references to compared items.
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
        value = values[0]  # We always take the first value since _generate_responses handles iteration
        params[param_key] = value
        add_mapping(param_key, value, params)

        # If this is a comparison context and we have a compare_with value
        if context.get("compare", False) and "compare_with" in context:
            compare_value = context["compare_with"]
            compared_key = f"compared_{param_key}"
            params[compared_key] = compare_value
            add_mapping(compared_key, compare_value, params)

    return params


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
