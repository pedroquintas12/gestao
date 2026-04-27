from config.db import db
from model.mixins import TimestampMixin


class Produto(db.Model, TimestampMixin):
    """
    Item de estoque. Os campos `extras` (JSON) seguem as definições em
    FieldDefinition para entity='produto' — validados no service.
    """
    __tablename__ = "produto"

    id_produto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    extras = db.Column(db.JSON, nullable=False, default=dict)
    deleted = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id_produto": self.id_produto,
            "nome": self.nome,
            "preco": float(self.preco or 0),
            "quantidade": self.quantidade,
            "extras": self.extras or {},
        }
