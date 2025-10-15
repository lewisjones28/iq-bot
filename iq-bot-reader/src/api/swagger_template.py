SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "IQ Reader API",
        "description": "API service for retrieving cached IQ prompts and responses from Redis.",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": ["http"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "definitions": {
        "Prompt": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "prompt_template_id": {"type": "string"},
                "title": {"type": "string"},
                "topic": {"type": "string"},
            }
        },
        "PromptListResponse": {
            "type": "object",
            "properties": {
                "prompts": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Prompt"}
                }
            }
        },
        "QueryResponse": {
            "type": "object",
            "properties": {
                "response": {"type": "string"}
            }
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            }
        }
    }
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "openapi",
            "route": "/openapi.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}
