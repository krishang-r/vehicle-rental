from flask import Flask


def create_app(config_object=None):
    """Application factory for the Flask app.

    Args:
        config_object: optional config object or path

    Returns:
        Flask app
    """
    app = Flask(__name__, instance_relative_config=False)

    if config_object:
        app.config.from_object(config_object)

    # simple route registration
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
