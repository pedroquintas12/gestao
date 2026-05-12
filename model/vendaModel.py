from config.db import db
from enums.status import status               # mantém o teu enum existente
from enums.forma_pagamentoEnum import FormaPagamento
from model.mixins import TimestampMixin  # GARANTA que tenha NAO_PAGO

class venda(db.Model,TimestampMixin):
    __tablename__ = "vendas"

    id_venda   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("cliente.id_cliente"), nullable=False)
    id_veiculo = db.Column(db.Integer, db.ForeignKey("veiculo.id_veiculo"), nullable=True)

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
    """
    Item de venda. Cada linha é OU um serviço OU um produto do estoque
    (XOR garantido por CheckConstraint). Ao finalizar a venda, produtos
    têm sua quantidade abatida automaticamente.

    `parent_item_id` permite que um item-produto seja "filho" de um item-serviço:
    o filho não soma no total e aparece como subitem no PDF (consumo de
    insumo). Filho só pode ser produto; pai só pode ser serviço.
    """
    __tablename__ = "venda_itens"
    __table_args__ = (
        db.CheckConstraint(
            "(id_servico IS NULL) <> (id_produto IS NULL)",
            name="ck_venda_itens_xor"
        ),
        db.CheckConstraint(
            "(parent_item_id IS NULL) OR (id_produto IS NOT NULL)",
            name="ck_venda_itens_filho_e_produto"
        ),
    )

    id_item    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_venda   = db.Column(db.Integer, db.ForeignKey("vendas.id_venda"), nullable=False)
    id_servico = db.Column(db.Integer, db.ForeignKey("servico.id_servico"), nullable=True)
    id_produto = db.Column(db.Integer, db.ForeignKey("produto.id_produto"), nullable=True)
    parent_item_id = db.Column(
        db.Integer,
        db.ForeignKey("venda_itens.id_item", ondelete="CASCADE"),
        nullable=True,
    )

    # snapshot
    descricao  = db.Column(db.String(200), nullable=False)
    preco_unit = db.Column(db.Numeric(10,2), nullable=False)
    quantidade = db.Column(db.Integer, default=1, nullable=False)
    desconto   = db.Column(db.Numeric(10,2), default=0, nullable=False)

    venda   = db.relationship("venda", back_populates="itens")
    servico = db.relationship("servico")
    produto = db.relationship("Produto")
    filhos = db.relationship(
        "VendaItem",
        backref=db.backref("parent", remote_side="VendaItem.id_item"),
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )

    @property
    def subtotal(self):
        if self.parent_item_id is not None:
            return 0
        return (self.preco_unit * self.quantidade) - self.desconto

    @property
    def tipo(self):
        return "produto" if self.id_produto else "servico"

    def to_dict(self):
        return {
            "id_item": self.id_item,
            "id_venda": self.id_venda,
            "id_servico": self.id_servico,
            "id_produto": self.id_produto,
            "parent_item_id": self.parent_item_id,
            "tipo": self.tipo,
            "descricao": self.descricao,
            "preco_unit": float(self.preco_unit),
            "quantidade": self.quantidade,
            "desconto": float(self.desconto),
            "subtotal": float(self.subtotal),
        }
