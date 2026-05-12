from flask import Blueprint

from config.decorators import login_required
from controller.produtoController import produtoController as PC

produto_bp = Blueprint("produto_bp", __name__, url_prefix="/api/produtos")

produto_bp.post("")(login_required(PC.create))
produto_bp.get("")(login_required(PC.get_all))
produto_bp.get("/by-codigo/<path:codigo>")(login_required(PC.get_by_codigo))
produto_bp.get("/<int:id_produto>")(login_required(PC.get_one))
produto_bp.add_url_rule(
    "/<int:id_produto>",
    view_func=login_required(PC.update),
    methods=["PUT", "PATCH"],
)
produto_bp.delete("/<int:id_produto>")(login_required(PC.delete))
produto_bp.post("/<int:id_produto>/ajustar")(login_required(PC.adjust_quantidade))
