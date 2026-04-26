from flask import Flask, g, session
from flask_cors import CORS
from config.db import db
from config import load_env_and_config
from config.business import current_type, is_module_enabled
from .erros import register_error_handlers
from .seeds import seed_db
import config.logger

cfg = load_env_and_config()


def _register_blueprints(app: Flask) -> None:
    """Core blueprints sempre + opcionais conforme o ramo ativo."""
    from routes.cliente import cliente_bp
    from routes.servico import servico_bp
    from routes.venda import venda_bp
    from routes.caixa import caixa_bp
    from routes.routes_front import front_bp
    from routes.auth import auth_bp
    from routes.companie import companie_bp

    app.register_blueprint(cliente_bp)
    app.register_blueprint(servico_bp)
    app.register_blueprint(venda_bp)
    app.register_blueprint(caixa_bp)
    app.register_blueprint(front_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(companie_bp)

    if is_module_enabled("veiculo"):
        from routes.veiculo import veiculo_bp
        app.register_blueprint(veiculo_bp)


def create_app():
    app = Flask(
        __name__,
        template_folder=cfg["TEMPLATE_FOLDER_ABS"],
        static_folder=cfg["STATIC_FOLDER_ABS"]
    )
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    app.config["SECRET_KEY"] = cfg["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = cfg["SQLALCHEMY_DATABASE_URI"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = cfg["SQLALCHEMY_TRACK_MODIFICATIONS"]
    app.config["BUSINESS_TYPE"] = current_type().value
    db.init_app(app)

    @app.before_request
    def load_user_from_session():
        g.user_id = session.get("user_id")  # None se não logado

    register_error_handlers(app)
    _register_blueprints(app)

    with app.app_context():
        import model
        db.create_all()
        if cfg["SEED_ON_STARTUP"]:
            seed_db(cfg)

    return app
