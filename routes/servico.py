from flask import Blueprint
from config.decorators import login_required
from controller.servicoController import servicoController as SC

servico_bp = Blueprint("servico_bp", __name__, url_prefix='/api/servicos')


servico_bp.post("")(login_required(SC.create))
servico_bp.get("")(login_required(SC.get_all))
servico_bp.get("<int:id_servico>")(login_required(SC.get_one))
servico_bp.add_url_rule(
    "<int:id_servico>",
    view_func=login_required(SC.update),
    methods=["PUT", "PATCH"]
)
servico_bp.delete("<int:id_servico>")(SC.delete)