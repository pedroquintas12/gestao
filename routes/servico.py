from flask import Blueprint
from controller.servicoController import servicoController as SC

servico_bp = Blueprint("servico_bp", __name__, url_prefix='/api/servicos')


servico_bp.post("")(SC.create)
servico_bp.get("")(SC.get_all)
servico_bp.post("<int:id_servico>")(SC.get_one)
servico_bp.add_url_rule(
    "<int:id_servico>",
    view_func=SC.update,
    methods=["PUT", "PATCH"]
)
servico_bp.delete("<int:id_servico>")(SC.delete)