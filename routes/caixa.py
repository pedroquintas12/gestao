from flask import Blueprint
from controller.caixaController import caixaController as Cc
from config.decorators import login_required

caixa_bp = Blueprint("caixa", __name__, url_prefix="/api/caixa")

caixa_bp.get("")(login_required(Cc.get_all))
