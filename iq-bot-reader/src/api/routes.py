import json
import logging

from flask import Blueprint, jsonify, request
from services.prompt_reader_service import PromptReaderService

from iq_bot_global import (
    RedisService
)
from iq_bot_global.constants import (
    REDIS_KEYS,
    API_RESPONSE_MESSAGES
)

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)
prompt_reader_service = PromptReaderService()


@api.route('/api/v1/prompts', methods=['GET'])
def get_prompts():
    """
    List Available Prompts
    
    Retrieves all available prompts from the system, optionally filtered by topic.
    
    Args:
        topic (str, optional): Filter prompts by topic name (via query parameter)
        
    Returns:
        tuple: JSON response with prompts and status code
            success: ({'prompts': [...]}, 200)
            error: ({'error': 'error message'}, 500)
            
    Raises:
        Exception: If prompts cannot be loaded or processed
    ---
    tags:
      - Prompts
    parameters:
      - in: query
        name: topic
        type: string
        required: false
        description: Filter prompts by topic name (e.g., 'character_prompts')
    responses:
      200:
        description: A list of all cached prompts, optionally filtered by topic
        schema:
          $ref: "#/definitions/PromptListResponse"
      500:
        description: Failed to load prompts
        schema:
          $ref: "#/definitions/ErrorResponse"
    """
    topic = request.args.get('topic')
    try:
        if topic:
            prompts = prompt_reader_service.get_generated_prompts_by_topic(topic)
        else:
            prompts = prompt_reader_service.get_all_generated_prompts()
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
    """
    Get Prompt by ID
    ---
    tags:
      - Prompts
    parameters:
      - in: path
        name: prompt_id
        type: string
        required: true
        description: The prompt template or generated prompt identifier
    responses:
      200:
        description: The prompt details
        schema:
          $ref: "#/definitions/Prompt"
      404:
        description: Prompt not found
        schema:
          $ref: "#/definitions/ErrorResponse"
      500:
        description: Internal error
        schema:
          $ref: "#/definitions/ErrorResponse"
    """
    try:
        # Check Redis for the generated prompt
        redis_service = RedisService()
        cache_keys = redis_service.get_keys(f"{REDIS_KEYS.GENERATED_PROMPT_PREFIX}:*{prompt_id}")
        if not cache_keys:
            return jsonify({"error": API_RESPONSE_MESSAGES.PROMPT_NOT_FOUND_WITH_ID.format(prompt_id=prompt_id)}), 404

        cached_prompt = redis_service.get_cached_response(cache_keys[0])
        if cached_prompt:
            try:
                return jsonify(json.loads(cached_prompt)), 200
            except json.JSONDecodeError:
                logger.error("Failed to decode cached prompt")
                redis_service.delete_cached_response(f"{REDIS_KEYS.PROMPT_PREFIX}:{prompt_id}")

    except Exception as e:
        logger.error(f"Error retrieving prompt {prompt_id}: {e}")

    return jsonify({"error": API_RESPONSE_MESSAGES.PROMPT_NOT_FOUND}), 404


@api.route('/api/v1/query', methods=['GET'])
def query():
    """
    Query Response by Prompt ID
    ---
    tags:
      - Queries
    parameters:
      - in: query
        name: promptId
        type: string
        required: true
        description: The prompt identifier
    responses:
      200:
        description: Cached response for the given prompt
        schema:
          $ref: "#/definitions/QueryResponse"
      400:
        description: Missing or invalid parameters
        schema:
          $ref: "#/definitions/ErrorResponse"
      404:
        description: Response not found
        schema:
          $ref: "#/definitions/ErrorResponse"
      500:
        description: Internal error
        schema:
          $ref: "#/definitions/ErrorResponse"
    """
    prompt_id = request.args.get('promptId')
    if not prompt_id:
        return jsonify({"error": "promptId is required"}), 400

    try:
        # Check Redis for the generated response
        redis_service = RedisService()
        cache_keys = redis_service.get_keys(f"{REDIS_KEYS.PROMPT_PREFIX}:{prompt_id}:*")
        if not cache_keys:
            return jsonify({"error": API_RESPONSE_MESSAGES.RESPONSE_NOT_FOUND_WITH_ID.format(prompt_id=prompt_id)}), 404

        cached_response = redis_service.get_cached_response(cache_keys[0])
        if cached_response:
            try:
                return jsonify({"response": cached_response.decode('utf-8')}), 200
            except json.JSONDecodeError:
                logger.error("Failed to decode cached response")
                redis_service.delete_cached_response(cache_keys[0])
                return jsonify({"error": API_RESPONSE_MESSAGES.DEFAULT_ERROR}), 500

    except Exception as e:
        logger.error(f"Error retrieving response for prompt {prompt_id}: {e}")
        return jsonify({"error": API_RESPONSE_MESSAGES.DEFAULT_ERROR}), 500

    return jsonify({"error": API_RESPONSE_MESSAGES.DEFAULT_ERROR}), 404
