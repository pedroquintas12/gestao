# seeds.py
from config.db import db
from model.userModel import User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def get_or_create(model, defaults=None, **filters):
    """Idempotente: busca por filtros; se não existir, cria com defaults."""
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance, False
    params = {**filters, **(defaults or {})}
    instance = model(**params)
    db.session.add(instance)
    return instance, True

def seed_db(config):

       # Admin (apenas se não existe)
    admin = User.query.filter_by(username="Admin").first()
    if not admin:
        hashed = bcrypt.generate_password_hash("001305").decode("utf-8")
        admin = User(username="Admin",password=hashed, nome="Admin", is_active=True, is_admin=True)
        db.session.add(admin)

    db.session.commit()
