from flask import Blueprint
from controller.vendaController import vendaController as VC

venda_bp = Blueprint("venda_bp", __name__, url_prefix='/api/vendas')


venda_bp.post("")(VC.create)
venda_bp.get("")(VC.get_all)
venda_bp.get("/<int:id_venda>")(VC.get_one)
venda_bp.add_url_rule(
    "/<int:id_venda>",
    view_func=(VC.update),
    methods=["PUT", "PATCH"],
)
venda_bp.post("/<int:id_venda>/itens")(VC.add_item)
venda_bp.delete("/<int:id_venda>/itens/<int:id_item>")(VC.del_item)
venda_bp.post("/<int:id_venda>/finalizar")(VC.finalizar)
venda_bp.post("/<int:id_venda>/cancelar")(VC.cancelar)

