from flask import Flask, g, session
from flask_cors import CORS
from config.db import db
from config import config
from .erros import register_error_handlers
from .seeds import seed_db

def create_app():
    app = Flask(
        __name__,
        template_folder=config.TEMPLATE_FOLDER,  # agora ABSOLUTO p/ ...\PetGo\views
        static_folder=config.STATIC_FOLDER       # ABSOLUTO p/ ...\PetGo\public (ou app\public se preferir)
    )
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    db.init_app(app)
    
    app.config["SECRET_KEY"] = config.SECRET_KEY
    
    @app.before_request
    def load_user_from_session():
        g.user_id = session.get("user_id")  # None se não logado

    register_error_handlers(app)

    from routes.cliente import cliente_bp
    from routes.veiculo import veiculo_bp

    app.register_blueprint(cliente_bp)
    app.register_blueprint(veiculo_bp)

    with app.app_context():
        import model
        db.create_all()
        if config.SEED_ON_STARTUP == True:
                    seed_db(config)



    return app
