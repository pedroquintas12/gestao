
from config.db import db
from model.mixins import TimestampMixin

class User(db.Model,TimestampMixin):

    __tablename__ = 'users'

    id_user = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    deleted = db.Column(db.Boolean, default=False)
    



    def to_safe_dict(self):
        return{
            "id": self.id_user,
            "nome": self.nome,
            "username": self.username,
            "is_admin": self.is_admin,
        }

    def __repr__(self) -> str:  # debug 
        return f"<User id={self.id_user} username={self.username!r}>"
