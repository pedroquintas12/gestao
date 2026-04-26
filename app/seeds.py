# seeds.py
from config.db import db
from config.business import current_type
from enums.business import BusinessType
from model.userModel import User
from model.servicoModel import servico as Servico
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

DEFAULT_SERVICOS_BY_TYPE: dict[BusinessType, list[tuple[str, float]]] = {
    BusinessType.LAVAJATO: [
        ("Lavagem Simples", 50.00),
        ("Lavagem Completa", 120.00),
        ("Polimento", 300.00),
    ],
    BusinessType.GENERICO: [],
}


def get_or_create(model, defaults=None, **filters):
    """Idempotente: busca por filtros; se não existir, cria com defaults."""
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance, False
    params = {**filters, **(defaults or {})}
    instance = model(**params)
    db.session.add(instance)
    return instance, True


def _seed_admin():
    admin = User.query.filter_by(username="Admin").first()
    if admin:
        return
    hashed = bcrypt.generate_password_hash("001305").decode("utf-8")
    db.session.add(User(username="Admin", password=hashed, nome="Admin", is_admin=True))


def _seed_servicos_padrao(business_type: BusinessType):
    """Só semeia se ainda não houver nenhum serviço cadastrado (instalação nova)."""
    if Servico.query.first() is not None:
        return
    for nome, valor in DEFAULT_SERVICOS_BY_TYPE.get(business_type, []):
        db.session.add(Servico(nome=nome, valor=valor))


def seed_db(config):
    _seed_admin()
    _seed_servicos_padrao(current_type())
    db.session.commit()
