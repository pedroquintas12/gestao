from sqlalchemy import UniqueConstraint
from config.db import db
from .mixins import TimestampMixin

class caixa_lancamento(db.Model,TimestampMixin):
    __tablename__ = "caixa_lancamento"

    id_caixa = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey("vendas.id_venda"), nullable=True, index=True)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.Enum("ENTRADA","SAIDA", name="tipo_caixa"), nullable=False, default="ENTRADA")
    origem = db.Column(db.Enum("FINALIZACAO_VENDA","AJUSTE","ESTORNO", name="origem_caixa"), nullable=False, default="FINALIZACAO_VENDA")
    cancelado = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("venda_id", "origem",
                         name="uix_caixa_venda_origem"), 
    )

    def to_dict(self):
        return {
            "id_lcto": self.id_caixa,
            "venda_id": self.venda_id,
            "valor": float(self.valor),
            "descricao": self.descricao,
            "created_at": self.created_at.isoformat(),
        }
