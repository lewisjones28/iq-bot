import json
import logging

from flask import Blueprint, jsonify, request

from iq_bot_global import (
    RedisService
)
from services.prompt_service import PromptService
from services.prompt_template_service import PromptTemplateService

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)
prompt_service = PromptService()
template_service = PromptTemplateService()


@api.route('/api/v1/prompts', methods=['GET'])
def get_prompts():
    """Get a list of all available generated prompts."""
    try:
        prompts = prompt_service.list_cached_prompts()
        return jsonify({
            "prompts": prompts
        }), 200
    except Exception as e:
        logger.error(f"Error getting prompts: {e}")
        return jsonify({
            "error": "Failed to load prompts"
        }), 500


@api.route('/api/v1/prompts/<prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    """Get details of a specific prompt by ID."""
    try:
        # Check Redis for the generated prompt
        redis_service = RedisService()
        cache_keys = redis_service.get_keys(f"prompt:*{prompt_id}")
        if not cache_keys:
            return jsonify({"error": f"No template or prompt found with ID: {prompt_id}"}), 404

        cached_prompt = redis_service.get_cached_response(cache_keys[0])
        if cached_prompt:
            try:
                return jsonify(json.loads(cached_prompt)), 200
            except json.JSONDecodeError:
                logger.error("Failed to decode cached prompt")
                redis_service.delete_cached_response(f"prompt:{prompt_id}")

    except Exception as e:
        logger.error(f"Error retrieving prompt {prompt_id}: {e}")

    return jsonify({"error": "Prompt not found"}), 404


@api.route('/api/v1/query', methods=['GET'])
def query():
    """Get a response for a specific prompt ID."""
    prompt_id = request.args.get('promptId')
    if not prompt_id:
        return jsonify({"error": "promptId is required"}), 400

    try:
        redis_service = RedisService()
        # Get the cache key from the template (TODO)
        # Check Redis for the generated response
        cache_keys = redis_service.get_keys(f"prompt-response:{prompt_id}:*")
        if not cache_keys:
            return jsonify({"error": f"No response found for prompt ID: {prompt_id}"}), 404

        cached_response = redis_service.get_cached_response(cache_keys[0])
        if cached_response:
            try:
                return jsonify({"response": cached_response.decode('utf-8')}), 200
            except json.JSONDecodeError:
                logger.error("Failed to decode cached response")
                redis_service.delete_cached_response(cache_keys[0])
                return jsonify({"error": "Invalid response data in cache"}), 500

    except Exception as e:
        logger.error(f"Error retrieving response for prompt {prompt_id}: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Response not found"}), 404
