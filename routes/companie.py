from flask import Blueprint
from controller.companieController import companieController as CC

companie_bp = Blueprint("companie_bp", __name__, url_prefix='/api/companias')


companie_bp.post("")(CC.create_companie)
companie_bp.get("<int:id_companie>")(CC.get_one)