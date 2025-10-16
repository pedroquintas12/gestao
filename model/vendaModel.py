from datetime import datetime
from config.db import db

class venda(db.Model):
    
    __tablename__ = "vendas"

    id_venda = db.Column(db.Integer, primary_key = True, autoincrement = True)

    id_cliente = db.Column(db.Integer, db.ForeignKey("cliente.id_cliente"), nullable=False)
    id_servico = db.Column(db.Integer, db.ForeignKey("servico.id_servico"), nullable=False)
    id_veiculo = db.Column(db.Integer, db.ForeignKey("veiculo.id_veiculo"), nullable=False)

    total = db.Column(db.Numeric(10,2), nullable= False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = db.relationship("cliente", back_populates="vendas",  lazy="joined")
    servico = db.relationship("servico", back_populates="vendas",  lazy="joined")
    veiculo = db.relationship("veiculo", back_populates="vendas",  lazy="joined")


    def to_dict(self):
        return{

            "id_venda": self.id_venda,
            "total": self.total,
            "cliente": [c.to_dict() for c in self.cliente],
            "servico": [s.to_dict() for s in self.servico],   
            "veiculo": [v.to_dict() for v in self.veiculo]     

            }