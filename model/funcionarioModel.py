from datetime import datetime
from config.db import db
from enums.ROLE import cargos

class funcionario(db.Model):

    __tablename__ = "funcionarios"

    id_func = db.Column(db.Integer, primary_key = True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(20), nullable=True)
    salario = db.Column(db.Numeric(10,2), nullable = False)
    is_active = db.Column(db.Boolean, default = True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Integer, nullable=False, default=False)


    def to_dict(self):
        return{
            "id_func" : self.id_func,
            "role": self.role,
            "salario": self.salario
        }