from flask import Blueprint
from config.decorators import login_required
from controller.clienteController import clienteController as AC

cliente_bp = Blueprint("cliente_bp", __name__, url_prefix="/api/clientes")


cliente_bp.post("")(login_required(AC.create))
cliente_bp.get("")(login_required(AC.get_all))
cliente_bp.get("/<int:id_cliente>")(login_required(AC.get_one))
cliente_bp.add_url_rule(
    "<int:id_cliente>",
    view_func=login_required(AC.update),
    methods=["PUT", "PATCH"]
)
cliente_bp.delete("<int:id_cliente>")(login_required(AC.delete))