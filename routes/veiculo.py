from flask import Blueprint
from controller.veiculoController import veiculoController as VC

veiculo_bp = Blueprint("veiculo_bp", __name__, url_prefix='/car')


veiculo_bp.post("/api/create")(VC.create)