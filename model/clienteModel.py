

from config.db import db
from model.mixins import TimestampMixin

class cliente(db.Model,TimestampMixin):

    __tablename__ = "cliente"

    id_cliente = db.Column(db.Integer, primary_key= True, autoincrement=True)
    nome = db.Column(db.String(150), nullable= False)
    cpf = db.Column(db.String(30), nullable = True)
    numero = db.Column(db.String(30), nullable= True)
    deleted = db.Column(db.Integer, nullable=False, default=False)


    venda =  db.relationship(
        "venda",
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="selectin"
                )

    veiculos = db.relationship(
        "veiculo",
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self, with_children: bool = True):
        data = {
            "id_cliente": self.id_cliente,
            "nome": self.nome,
            "numero": self.numero
            }
        if with_children:
            data["veiculos"] =  [v.to_dict() for v in getattr(self, "veiculos", [])]
        return data
     