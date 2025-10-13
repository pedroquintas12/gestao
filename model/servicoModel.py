import datetime
from config.db import db

class servico(db.Model):

    __tablename__ = "servico"
    
    id_servico = db.Column(db.Integer, primary_key= True, autoincrement = True)
    nome = db.Column(db.Text, nullable= False)
    valor = db.Column(db.Decimal, nullable= False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return{
            "id_servico": self.id_servico,
            "nome": self.nome,
            "valor": self.valor
        }