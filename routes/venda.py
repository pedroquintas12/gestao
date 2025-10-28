from flask import Blueprint
from config.decorators import login_required
from controller.vendaController import vendaController as VC

venda_bp = Blueprint("venda_bp", __name__, url_prefix='/api/vendas')


venda_bp.post("")(login_required(VC.create))
venda_bp.get("")(login_required(VC.get_all))
venda_bp.get("/<int:id_venda>")(VC.get_one)
venda_bp.add_url_rule(
    "/<int:id_venda>",
    view_func=login_required(VC.update),
    methods=["PUT", "PATCH"],
)
venda_bp.post("/<int:id_venda>/itens")(login_required(VC.add_item))
venda_bp.delete("/<int:id_venda>/itens/<int:id_item>")(login_required(VC.del_item))
venda_bp.post("/<int:id_venda>/finalizar")(login_required(VC.finalizar))
venda_bp.post("/<int:id_venda>/cancelar")(login_required(VC.cancelar))
venda_bp.get("/<int:orc_id>/orcamento/pdf")(login_required(VC.baixar_orcamento_pdf))
