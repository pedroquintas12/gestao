from flask import Blueprint
from config.decorators import login_required
from controller.veiculoController import veiculoController as VC

veiculo_bp = Blueprint("veiculo_bp", __name__, url_prefix='/api/veiculos')


veiculo_bp.post("")(login_required(VC.create))
veiculo_bp.get("")(login_required(VC.get_all))
veiculo_bp.get("/<int:id_veiculo>")(login_required(VC.get_one))
veiculo_bp.add_url_rule(
    "/<int:id_veiculo>",
    view_func= login_required(VC.update),
    methods=["PUT", "PATCH"]
      )
veiculo_bp.delete("/<int:id_veiculo>")(login_required(VC.delete))


