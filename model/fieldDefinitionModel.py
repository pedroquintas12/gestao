from config.db import db
from model.mixins import TimestampMixin


class FieldDefinition(db.Model, TimestampMixin):
    """
    Define um campo customizado para uma entidade (hoje só 'produto').
    O valor é armazenado na coluna `extras` (JSON) da entidade-alvo.
    """
    __tablename__ = "field_definition"
    __table_args__ = (
        db.UniqueConstraint("entity", "nome", name="uq_field_definition_entity_nome"),
    )

    id_field = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity = db.Column(db.String(50), nullable=False, default="produto", index=True)
    nome = db.Column(db.String(50), nullable=False)        # slug usado como chave em extras
    label = db.Column(db.String(100), nullable=False)      # rótulo para UI
    tipo = db.Column(db.String(20), nullable=False)        # FieldType.value
    obrigatorio = db.Column(db.Boolean, nullable=False, default=False)
    opcoes = db.Column(db.JSON, nullable=True)             # lista de strings, só para SELECT
    ordem = db.Column(db.Integer, nullable=False, default=0)
    deleted = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id_field": self.id_field,
            "entity": self.entity,
            "nome": self.nome,
            "label": self.label,
            "tipo": self.tipo,
            "obrigatorio": bool(self.obrigatorio),
            "opcoes": self.opcoes or [],
            "ordem": self.ordem,
        }
