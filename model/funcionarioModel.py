import datetime
from config.db import db
from enums.ROLE import cargos

class funcionario(db.Model):

    __tablename__ = "funcionarios"

    id_func = db.Column(db.Integer, primary_key = True, autoincrement=True)
    role = db.Column(db.String(15), nullable=False, default = cargos.FUNC)
    nome = db.Column(db.String(100), nullable=False)
    salario = db.Column(db.Decimal, nullable = False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Integer, nullable=False, default=0)


    def to_dict(self):
        return{
            "id_func" : self.id_func,
            "role": self.role,
            "salario": self.salario
        }