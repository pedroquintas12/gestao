
from config.db import db
from model.mixins import TimestampMixin

class servico(db.Model,TimestampMixin):
    __tablename__ = "servico"
    
    id_servico = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome       = db.Column(db.Text, nullable=False)
    valor      = db.Column(db.Numeric(10,2), nullable=False)
    deleted    = db.Column(db.Integer, nullable=False, default=False)

    # Relaciona com os ITENS de venda
    itens = db.relationship(
        "VendaItem",
        back_populates="servico",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id_servico": self.id_servico,
            "nome": self.nome,
            "valor": float(self.valor),
        }
