from datetime import datetime
from config.db import db

class servico(db.Model):

    __tablename__ = "servico"
    
    id_servico = db.Column(db.Integer, primary_key= True, autoincrement = True)
    nome = db.Column(db.Text, nullable= False)
    valor = db.Column(db.Numeric(10,2), nullable= False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Integer, nullable=False, default=False)

    veiculos = db.relationship("veiculo", back_populates="servico", lazy="selectin")

    vendas = db.relationship("venda", back_populates="servico", lazy="selectin")

    
    def to_dict(self):
        return{
            "id_servico": self.id_servico,
            "nome": self.nome,
            "valor": self.valor
        }