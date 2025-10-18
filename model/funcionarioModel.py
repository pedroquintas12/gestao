
from config.db import db
from model.mixins import TimestampMixin

class funcionario(db.Model,TimestampMixin):

    __tablename__ = "funcionarios"

    id_func = db.Column(db.Integer, primary_key = True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(20), nullable=True)
    salario = db.Column(db.Numeric(10,2), nullable = False)
    is_active = db.Column(db.Boolean, default = True)

    deleted = db.Column(db.Integer, nullable=False, default=False)


    def to_dict(self):
        return{
            "id_func" : self.id_func,
            "role": self.role,
            "salario": self.salario
        }