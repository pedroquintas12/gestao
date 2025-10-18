from flask import Blueprint
from controller.clienteController import clienteController as AC

cliente_bp = Blueprint("cliente_bp", __name__, url_prefix="/api/clientes")


cliente_bp.post("")(AC.create)
cliente_bp.get("")(AC.get_all)
cliente_bp.get("/<int:id_cliente>")(AC.get_one)
cliente_bp.add_url_rule(
    "<int:id_cliente>",
    view_func=AC.update,
    methods=["PUT", "PATCH"]
)
cliente_bp.delete("<int:id_cliente>")(AC.delete)