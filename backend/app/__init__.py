import logging
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app.config import Config
from app.errors import ApiError

db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    # Keep safe timing events visible under Gunicorn without enabling SDK debug logs.
    app.logger.setLevel(logging.INFO)
    logging.getLogger("app.services.gemma_service").setLevel(logging.INFO)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_UPLOAD_MB"] * 1024 * 1024 + 65536
    db.init_app(app)
    CORS(
        app,
        resources={
            r"/api/v1/*": {
                "origins": app.config["FRONTEND_ORIGIN"],
                "allow_headers": ["Content-Type", "X-Document-Token"],
                "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            }
        },
    )

    from app.routes import api

    app.register_blueprint(api, url_prefix="/api/v1")

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        return jsonify({
            "error": {
                "code": "UPLOAD_TOO_LARGE",
                "message": "The PDF exceeds the configured upload limit.",
            }
        }), 413

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({
            "error": {
                "code": "HTTP_ERROR",
                "message": error.description or "The request could not be completed.",
            }
        }), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(_error):
        app.logger.error("Unhandled request error")
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "FomuWise could not complete the request. Please try again.",
            }
        }), 500

    with app.app_context():
        db.create_all()
    return app
