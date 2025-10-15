import logging
import os

from flasgger import Swagger
from flask import Flask

from api.routes import api
from api.swagger_template import SWAGGER_TEMPLATE, SWAGGER_CONFIG
from iq_bot_global.constants import FLASK_CONFIG

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.register_blueprint(api)
    Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)
    return app


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = create_app()
    port = int(os.getenv('PORT', FLASK_CONFIG.DEFAULT_PORT))
    app.run(host=FLASK_CONFIG.DEFAULT_HOST, port=port, debug=True)
