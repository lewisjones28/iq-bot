"""Utility functions for the IQ bot."""

from typing import Dict, Any


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
    for context in prompt_contexts.get("promptContexts", []):
        param_key = context["name"].rstrip('s')
        values = context["values"]
        if not values:
            continue

        # Store the primary value
        value = values[0]
        params[param_key] = value

    return params
