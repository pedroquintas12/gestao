from config.db import db
from model.mixins import TimestampMixin

class veiculo(db.Model,TimestampMixin):

    __tablename__ = "veiculo"

    id_veiculo = db.Column(db.Integer, primary_key= True, autoincrement= True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("cliente.id_cliente"), nullable=False)
    kilometragem = db.Column(db.Integer, nullable = True)
    placa = db.Column(db.String(20), nullable= False, unique = True)
    observacao = db.Column(db.Text, nullable= True)
    deleted = db.Column(db.Integer, nullable=False, default=False)

    cliente = db.relationship(
        "cliente",
        back_populates="veiculos",
        lazy="joined",
    )
    
    vendas  = db.relationship("venda",   back_populates="veiculo",  cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self , with_children : bool = False):
        data ={
        "id_veiculo": self.id_veiculo,
        "id_cliente": self.id_cliente,
        "km":self.kilometragem,
        "placa": self.placa,
        "obs": self.observacao,
        }
        if with_children:
            data["cliente"] =  [c.to_dict() for c in getattr(self, "cliente", [])]
        return data

