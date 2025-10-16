


from flask import Blueprint
from controller.clienteController import clienteController as AC

cliente_bp = Blueprint("cliente_bp", __name__, url_prefix="/cliente")


cliente_bp.post("/api/create")(AC.create)
cliente_bp.get("/api/getall")(AC.get_all)