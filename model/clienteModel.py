import datetime
from config.db import db

class cliente(db.Model):

    __tablename__ = "cliente"

    id_cliente = db.Column(db.Integer, primary_key= True, autoincrement=True)
    nome = db.Column(db.Sting(150), nullable= False)
    cpf = db.Column(db.String(30), nullable = True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return{
            "id_cliente": self.id_cliente,
            "nome": self.nome
        }