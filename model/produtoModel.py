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
    codigo_barras = db.Column(db.String(64), nullable=True)
    extras = db.Column(db.JSON, nullable=False, default=dict)
    deleted = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        # Unicidade só quando o código existe (produtos podem não ter).
        db.Index(
            "ux_produto_codigo_barras",
            "codigo_barras",
            unique=True,
            sqlite_where=db.text("codigo_barras IS NOT NULL"),
        ),
    )

    def to_dict(self):
        return {
            "id_produto": self.id_produto,
            "nome": self.nome,
            "preco": float(self.preco or 0),
            "quantidade": self.quantidade,
            "codigo_barras": self.codigo_barras,
            "extras": self.extras or {},
        }
