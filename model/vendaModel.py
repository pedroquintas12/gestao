import datetime
from config.db import db

class venda(db.Model):
    
    __tablename__ = "vendas"

    id_venda = db.Column(db.Integer, primary_key = True, autoincrement = True)
    id_cliente = db.Column(db.Integer, nullable = False)
    id_servico = db.Column(db.Integer, nullable = False)
    id_veiculo = db.Column(db.Integer, nullable = False)
    total = db.Column(db.Decimal, nullable= False)

    cliente = db.relationship(
        "clienteModel",
        back_populates="cliente",
        lazy="joined",
        foreign_keys=[id_cliente],
    )

    servico = db.relationship(
        "servicoModel",
        back_populates="servico",
        lazy="joined",
        foreign_keys=[id_servico],
    )
    veiculo = db.relationship(
        "veiculoModel",
        back_populates="veiculo",
        lazy="joined",
        foreign_keys=[id_veiculo],
    )

    def to_dict(self):
        return{

            "id_venda": self.id_venda,
            "cliente": [c.to_dict() for c in self.cliente],
            "servico": [s.to_dict() for s in self.servico],   
            "veiculo": [v.to_dict() for v in self.veiculo]     

            }