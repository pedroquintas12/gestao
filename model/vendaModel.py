from config.db import db
from enums.status import status               # mantém o teu enum existente
from enums.forma_pagamentoEnum import FormaPagamento
from model.mixins import TimestampMixin  # GARANTA que tenha NAO_PAGO

class venda(db.Model,TimestampMixin):
    __tablename__ = "vendas"

    id_venda   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("cliente.id_cliente"), nullable=False)
    id_veiculo = db.Column(db.Integer, db.ForeignKey("veiculo.id_veiculo"), nullable=False)

    # deixa o total persistido (mais simples p/ relatórios) e sempre recalculamos ao salvar
    total      = db.Column(db.Numeric(10,2), nullable=False, default=0)
    status     = db.Column(db.String(15), nullable=False, default=status.ATIVO.name)
    pagamento  = db.Column(db.String(20), nullable=False, default=FormaPagamento.NÃO_PAGO.name)
    descricao  = db.Column(db.String(200), nullable=True)

    # RELACIONAMENTOS
    cliente = db.relationship("cliente", back_populates="venda", lazy="joined")
    veiculo = db.relationship("veiculo", back_populates="vendas", lazy="joined")

    itens = db.relationship(
        "VendaItem",
        back_populates="venda",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def recalc_total(self):
        self.total = sum((i.preco_unit * i.quantidade) - i.desconto for i in self.itens)

    def to_dict(self, with_children: bool = False):
        data = {
            "id_venda": self.id_venda,
            "id_cliente": self.id_cliente,
            "id_veiculo": self.id_veiculo,
            "total": float(self.total or 0),
            "status": self.status,
            "pagamento": self.pagamento,
            "descricao": self.descricao,
            "create_at": self.created_at
        }
        if with_children:
            data["cliente"] = self.cliente.to_dict(with_children=False) if self.cliente else None
            data["veiculo"] = self.veiculo.to_dict(with_children=False) if self.veiculo else None
            data["itens"]   = [i.to_dict() for i in self.itens]
        return data


class VendaItem(db.Model):
    __tablename__ = "venda_itens"

    id_item    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_venda   = db.Column(db.Integer, db.ForeignKey("vendas.id_venda"), nullable=False)
    id_servico = db.Column(db.Integer, db.ForeignKey("servico.id_servico"), nullable=False)  

    # snapshot do serviço
    descricao  = db.Column(db.String(200), nullable=False)
    preco_unit = db.Column(db.Numeric(10,2), nullable=False)
    quantidade = db.Column(db.Integer, default=1, nullable=False)
    desconto   = db.Column(db.Numeric(10,2), default=0, nullable=False)

    venda   = db.relationship("venda", back_populates="itens")   
    servico = db.relationship("servico")                         

    @property
    def subtotal(self):
        return (self.preco_unit * self.quantidade) - self.desconto

    def to_dict(self):
        return {
            "id_item": self.id_item,
            "id_venda": self.id_venda,
            "id_servico": self.id_servico,
            "descricao": self.descricao,
            "preco_unit": float(self.preco_unit),
            "quantidade": self.quantidade,
            "desconto": float(self.desconto),
            "subtotal": float(self.subtotal),
        }
