from flask import Blueprint
from controller.veiculoController import veiculoController as VC

veiculo_bp = Blueprint("veiculo_bp", __name__, url_prefix='/api/veiculos')


veiculo_bp.post("")(VC.create)
veiculo_bp.get("")(VC.get_all)
veiculo_bp.get("/<int:id_veiculo>")(VC.get_one)
veiculo_bp.add_url_rule(
    "/<int:id_veiculo>",
    view_func= VC.update,
    methods=["PUT", "PATCH"]
      )
veiculo_bp.delete("/<int:id_veiculo>")(VC.delete)


