from flask import Blueprint

from app.routes.documents import documents_bp
from app.routes.health import health_bp

api = Blueprint("api", __name__)
api.register_blueprint(health_bp)
api.register_blueprint(documents_bp)
