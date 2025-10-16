from datetime import datetime
from config.db import db

class veiculo(db.Model):

    __tablename__ = "veiculo"

    id_veiculo = db.Column(db.Integer, primary_key= True, autoincrement= True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("cliente.id_cliente"), nullable=False)
    id_servico  = db.Column(db.Integer, db.ForeignKey("servico.id_servico"), nullable=True)
    kilometragem = db.Column(db.Integer, nullable = True)
    placa = db.Column(db.String(20), nullable= False)
    id_servico = db.Column(db.Integer, nullable= False)
    observacao = db.Column(db.Text, nullable= True)
    status = db.Column(db.String(20), nullable = False, default = "ativo")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Integer, nullable=False, default=False)

    cliente = db.relationship(
        "cliente",
        back_populates="veiculos",
        lazy="joined",
    )
    servico = db.relationship("servico", back_populates="veiculos", lazy="joined")  
    
    vendas  = db.relationship("venda",   back_populates="veiculo",  cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return{
        "id_veiculo": self.id_veiculo,
        "id_cliente": self.id_cliente,
        "km":self.kilometragem,
        "placa": self.placa,
        "id_servico": self.id_servico,
        "obs": self.observacao,
        "status": self.status,
        "cliente": [c.to_dict() for c in self.cliente],
        "servico": [s.to_dict() for s in self.servico]
        }


