from flask import Flask, g, session
from flask_cors import CORS
from pathlib import Path
import os

from config.db import db
from config import load_env_and_config
from .erros import register_error_handlers
from .seeds import seed_db
import config.logger

cfg = load_env_and_config()

def create_app():
    app = Flask(
        __name__,
        template_folder=cfg["TEMPLATE_FOLDER_ABS"],
        static_folder=cfg["STATIC_FOLDER_ABS"],
        instance_relative_config=True,  # <- habilita a pasta instance/
    )
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Garante que a pasta instance/ existe
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Carrega configs básicas
    app.config["SECRET_KEY"] = cfg["SECRET_KEY"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = cfg["SQLALCHEMY_TRACK_MODIFICATIONS"]

    # Força o SQLite a ficar dentro de instance/gestor.db
    db_file = os.path.join(app.instance_path, "gestor.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"

    # Se você quiser respeitar o .env quando NÃO for sqlite, deixe assim:
    # uri_env = cfg["SQLALCHEMY_DATABASE_URI"]
    # if not uri_env.startswith("sqlite:"):
    #     app.config["SQLALCHEMY_DATABASE_URI"] = uri_env

    db.init_app(app)

    @app.before_request
    def load_user_from_session():
        g.user_id = session.get("user_id")

    register_error_handlers(app)

    from routes.cliente import cliente_bp
    from routes.veiculo import veiculo_bp
    from routes.servico import servico_bp
    from routes.venda import venda_bp
    from routes.caixa import caixa_bp
    from routes.routes_front import front_bp
    from routes.auth import auth_bp
    from routes.companie import companie_bp

    app.register_blueprint(cliente_bp)
    app.register_blueprint(veiculo_bp)
    app.register_blueprint(servico_bp)
    app.register_blueprint(venda_bp)
    app.register_blueprint(caixa_bp)
    app.register_blueprint(front_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(companie_bp)

    with app.app_context():
        import model
        db.create_all()
        app.logger.info(f"[DB] usando {app.config['SQLALCHEMY_DATABASE_URI']}")
        if cfg["SEED_ON_STARTUP"] is True:
            seed_db(cfg)

    return app
