from flask import Flask
from flask_cors import CORS

from app.api.routes import api_bp
from app.config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health_check():
        return {"status": "ok", "service": app.config["APP_NAME"]}

    return app
